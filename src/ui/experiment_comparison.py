"""
实验对比功能模块

提供实验数据对比、分析和可视化功能
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qtagg import FigureCanvasQT as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


@dataclass
class ExperimentData:
    """实验数据"""

    experiment_id: str
    experiment_name: str
    user_id: str
    started_at: str
    completed_at: str
    duration: float
    steps_completed: int
    total_steps: int
    success_rate: float
    data_points: list[dict]
    parameters: dict
    results: dict


@dataclass
class ComparisonResult:
    """对比结果"""

    comparison_id: str
    experiment_ids: list[str]
    comparison_type: str
    metrics: dict
    differences: dict
    recommendations: list[str]
    created_at: str


class ExperimentDataLoader(QThread):
    """实验数据加载线程"""

    data_loaded = Signal(list)  # List[ExperimentData]
    progress_updated = Signal(int)  # progress percentage
    error_occurred = Signal(str)  # error message

    def __init__(self, experiment_ids: list[str], data_dir: Path):
        super().__init__()
        self.experiment_ids = experiment_ids
        self.data_dir = data_dir

    def run(self):
        """加载实验数据"""
        try:
            experiments = []
            total = len(self.experiment_ids)

            for i, exp_id in enumerate(self.experiment_ids):
                self.progress_updated.emit(int((i / total) * 100))

                # 加载实验数据
                exp_data = self._load_experiment_data(exp_id)
                if exp_data:
                    experiments.append(exp_data)

            self.progress_updated.emit(100)
            self.data_loaded.emit(experiments)

        except Exception as e:
            logger.error(f"加载实验数据失败: {e}")
            self.error_occurred.emit(str(e))

    def _load_experiment_data(self, experiment_id: str) -> ExperimentData | None:
        """加载单个实验数据"""
        try:
            # 查找实验记录文件
            records_dir = self.data_dir / "records"
            if not records_dir.exists():
                return None

            # 查找匹配的记录文件
            for record_file in records_dir.glob("*.json"):
                try:
                    with open(record_file, encoding="utf-8") as f:
                        record_data = json.load(f)

                    if record_data.get("experiment_id") == experiment_id:
                        return self._parse_experiment_data(record_data)

                except Exception as e:
                    logger.error(f"读取记录文件失败: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"加载实验数据失败: {e}")
            return None

    def _parse_experiment_data(self, record_data: dict) -> ExperimentData:
        """解析实验数据"""
        try:
            # 计算成功率
            steps_completed = len(record_data.get("step_records", []))
            total_steps = record_data.get("total_steps", steps_completed)
            success_rate = (steps_completed / total_steps) * 100 if total_steps > 0 else 0

            # 计算持续时间
            started_at = record_data.get("started_at", "")
            completed_at = record_data.get("completed_at", "")
            duration = 0

            if started_at and completed_at:
                try:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    duration = (end_time - start_time).total_seconds()
                except Exception:
                    duration = 0

            # 提取数据点
            data_points = []
            for step_record in record_data.get("step_records", []):
                if "data" in step_record:
                    data_points.extend(step_record["data"])

            # 提取参数
            parameters = record_data.get("parameters", {})

            # 提取结果
            results = record_data.get("results", {})

            return ExperimentData(
                experiment_id=record_data.get("experiment_id", ""),
                experiment_name=record_data.get("experiment_name", ""),
                user_id=record_data.get("user_id", ""),
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
                steps_completed=steps_completed,
                total_steps=total_steps,
                success_rate=success_rate,
                data_points=data_points,
                parameters=parameters,
                results=results,
            )

        except Exception as e:
            logger.error(f"解析实验数据失败: {e}")
            raise


class ExperimentComparisonWidget(QWidget):
    """实验对比界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.experiments: list[ExperimentData] = []
        self.comparison_results: list[ComparisonResult] = []
        self.data_dir = Path("data")

        self._init_ui()
        self._load_available_experiments()

        logger.info("实验对比界面初始化完成")

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 顶部控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：实验选择
        left_panel = self._create_experiment_selection_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：对比结果
        right_panel = self._create_comparison_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([300, 700])
        layout.addWidget(main_splitter)

        # 底部状态栏
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QGroupBox("对比控制")
        layout = QHBoxLayout(panel)

        # 对比类型选择
        layout.addWidget(QLabel("对比类型:"))
        self.comparison_type_combo = QComboBox()
        self.comparison_type_combo.addItems(["性能对比", "数据对比", "参数对比", "结果对比", "综合对比"])
        layout.addWidget(self.comparison_type_combo)

        # 开始对比按钮
        self.compare_btn = QPushButton("开始对比")
        self.compare_btn.clicked.connect(self._start_comparison)
        layout.addWidget(self.compare_btn)

        # 导出结果按钮
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self._export_results)
        layout.addWidget(self.export_btn)

        layout.addStretch()
        return panel

    def _create_experiment_selection_panel(self) -> QWidget:
        """创建实验选择面板"""
        panel = QGroupBox("选择实验")
        layout = QVBoxLayout(panel)

        # 可用实验列表
        layout.addWidget(QLabel("可用实验:"))
        self.experiment_table = QTableWidget()
        self.experiment_table.setColumnCount(4)
        self.experiment_table.setHorizontalHeaderLabels(["选择", "实验名称", "用户", "完成时间"])
        self.experiment_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.experiment_table)

        # 选择控制
        button_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all_experiments)
        button_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("清除选择")
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        button_layout.addWidget(self.clear_selection_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return panel

    def _create_comparison_panel(self) -> QWidget:
        """创建对比面板"""
        panel = QTabWidget()

        # 对比结果标签页
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)

        # 对比结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["指标", "实验1", "实验2", "差异", "百分比", "状态"])
        results_layout.addWidget(self.results_table)

        panel.addTab(self.results_tab, "对比结果")

        # 图表标签页
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout(self.chart_tab)

        # 图表画布
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        panel.addTab(self.chart_tab, "对比图表")

        # 建议标签页
        self.recommendations_tab = QWidget()
        rec_layout = QVBoxLayout(self.recommendations_tab)

        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        rec_layout.addWidget(self.recommendations_text)

        panel.addTab(self.recommendations_tab, "改进建议")

        return panel

    def _load_available_experiments(self):
        """加载可用实验"""
        try:
            # 扫描实验记录
            records_dir = self.data_dir / "records"
            if not records_dir.exists():
                self.status_label.setText("未找到实验记录")
                return

            experiments = []
            for record_file in records_dir.glob("*.json"):
                try:
                    with open(record_file, encoding="utf-8") as f:
                        record_data = json.load(f)

                    experiments.append(
                        {
                            "id": record_data.get("experiment_id", ""),
                            "name": record_data.get("experiment_name", "未知实验"),
                            "user": record_data.get("user_id", "未知用户"),
                            "completed": record_data.get("completed_at", ""),
                        }
                    )

                except Exception as e:
                    logger.error(f"读取实验记录失败: {e}")
                    continue

            # 更新表格
            self.experiment_table.setRowCount(len(experiments))
            for i, exp in enumerate(experiments):
                # 选择复选框
                checkbox = QCheckBox()
                self.experiment_table.setCellWidget(i, 0, checkbox)

                # 实验信息
                self.experiment_table.setItem(i, 1, QTableWidgetItem(exp["name"]))
                self.experiment_table.setItem(i, 2, QTableWidgetItem(exp["user"]))
                self.experiment_table.setItem(i, 3, QTableWidgetItem(exp["completed"]))

            self.status_label.setText(f"找到 {len(experiments)} 个实验")

        except Exception as e:
            logger.error(f"加载可用实验失败: {e}")
            self.status_label.setText(f"加载实验失败: {e}")

    def _select_all_experiments(self):
        """全选实验"""
        for i in range(self.experiment_table.rowCount()):
            checkbox = self.experiment_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)

    def _clear_selection(self):
        """清除选择"""
        for i in range(self.experiment_table.rowCount()):
            checkbox = self.experiment_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)

    def _get_selected_experiments(self) -> list[str]:
        """获取选中的实验ID"""
        selected = []
        for i in range(self.experiment_table.rowCount()):
            checkbox = self.experiment_table.cellWidget(i, 0)
            if checkbox and checkbox.isChecked():
                # 从实验名称推断ID（简化实现）
                name_item = self.experiment_table.item(i, 1)
                if name_item:
                    selected.append(name_item.text())
        return selected

    def _start_comparison(self):
        """开始对比"""
        selected = self._get_selected_experiments()
        if len(selected) < 2:
            QMessageBox.warning(self, "选择错误", "请至少选择2个实验进行对比")
            return

        comparison_type = self.comparison_type_combo.currentText()

        # 显示进度
        progress = QProgressBar()
        progress.setWindowTitle("正在对比实验...")
        progress.setModal(True)
        progress.show()

        # 创建加载线程
        loader = ExperimentDataLoader(selected, self.data_dir)

        def on_data_loaded(experiments):
            progress.close()
            self.experiments = experiments
            self._perform_comparison(comparison_type)

        def on_progress_updated(value):
            progress.setValue(value)

        def on_error(error_msg):
            progress.close()
            QMessageBox.critical(self, "对比失败", f"对比实验时发生错误: {error_msg}")

        loader.data_loaded.connect(on_data_loaded)
        loader.progress_updated.connect(on_progress_updated)
        loader.error_occurred.connect(on_error)

        loader.start()

    def _perform_comparison(self, comparison_type: str):
        """执行对比分析"""
        try:
            if len(self.experiments) < 2:
                QMessageBox.warning(self, "数据不足", "至少需要2个实验数据进行对比")
                return

            # 根据对比类型执行不同的分析
            if comparison_type == "性能对比":
                self._compare_performance()
            elif comparison_type == "数据对比":
                self._compare_data()
            elif comparison_type == "参数对比":
                self._compare_parameters()
            elif comparison_type == "结果对比":
                self._compare_results()
            else:  # 综合对比
                self._comprehensive_comparison()

            self.status_label.setText(f"对比完成: {comparison_type}")

        except Exception as e:
            logger.error(f"执行对比分析失败: {e}")
            QMessageBox.critical(self, "对比失败", f"对比分析时发生错误: {e}")

    def _compare_performance(self):
        """性能对比"""
        # 更新结果表格
        self.results_table.setRowCount(4)

        metrics = [
            ("完成时间", "duration", "秒"),
            ("成功率", "success_rate", "%"),
            ("完成步骤", "steps_completed", "步"),
            ("总步骤", "total_steps", "步"),
        ]

        for i, (metric_name, metric_key, unit) in enumerate(metrics):
            self.results_table.setItem(i, 0, QTableWidgetItem(metric_name))

            values = []
            for j, exp in enumerate(self.experiments):
                value = getattr(exp, metric_key, 0)
                values.append(value)
                self.results_table.setItem(i, j + 1, QTableWidgetItem(f"{value:.2f} {unit}"))

            # 计算差异
            if len(values) >= 2:
                diff = values[1] - values[0]
                percent = (diff / values[0] * 100) if values[0] != 0 else 0

                self.results_table.setItem(i, 4, QTableWidgetItem(f"{diff:.2f} {unit}"))
                self.results_table.setItem(i, 5, QTableWidgetItem(f"{percent:.1f}%"))

                # 设置颜色
                if percent > 10:
                    self.results_table.item(i, 5).setBackground(QColor(255, 200, 200))
                elif percent < -10:
                    self.results_table.item(i, 5).setBackground(QColor(200, 255, 200))

        # 生成图表
        self._create_performance_chart()

        # 生成建议
        self._generate_performance_recommendations()

    def _compare_data(self):
        """数据对比"""
        # 简化实现：对比数据点数量
        self.results_table.setRowCount(1)
        self.results_table.setItem(0, 0, QTableWidgetItem("数据点数量"))

        values = []
        for j, exp in enumerate(self.experiments):
            value = len(exp.data_points)
            values.append(value)
            self.results_table.setItem(0, j + 1, QTableWidgetItem(str(value)))

        if len(values) >= 2:
            diff = values[1] - values[0]
            percent = (diff / values[0] * 100) if values[0] != 0 else 0

            self.results_table.setItem(0, 4, QTableWidgetItem(str(diff)))
            self.results_table.setItem(0, 5, QTableWidgetItem(f"{percent:.1f}%"))

    def _compare_parameters(self):
        """参数对比"""
        # 简化实现：对比参数数量
        self.results_table.setRowCount(1)
        self.results_table.setItem(0, 0, QTableWidgetItem("参数数量"))

        values = []
        for j, exp in enumerate(self.experiments):
            value = len(exp.parameters)
            values.append(value)
            self.results_table.setItem(0, j + 1, QTableWidgetItem(str(value)))

        if len(values) >= 2:
            diff = values[1] - values[0]
            percent = (diff / values[0] * 100) if values[0] != 0 else 0

            self.results_table.setItem(0, 4, QTableWidgetItem(str(diff)))
            self.results_table.setItem(0, 5, QTableWidgetItem(f"{percent:.1f}%"))

    def _compare_results(self):
        """结果对比"""
        # 简化实现：对比结果数量
        self.results_table.setRowCount(1)
        self.results_table.setItem(0, 0, QTableWidgetItem("结果数量"))

        values = []
        for j, exp in enumerate(self.experiments):
            value = len(exp.results)
            values.append(value)
            self.results_table.setItem(0, j + 1, QTableWidgetItem(str(value)))

        if len(values) >= 2:
            diff = values[1] - values[0]
            percent = (diff / values[0] * 100) if values[0] != 0 else 0

            self.results_table.setItem(0, 4, QTableWidgetItem(str(diff)))
            self.results_table.setItem(0, 5, QTableWidgetItem(f"{percent:.1f}%"))

    def _comprehensive_comparison(self):
        """综合对比"""
        # 组合所有对比类型
        self._compare_performance()
        self._compare_data()
        self._compare_parameters()
        self._compare_results()

    def _create_performance_chart(self):
        """创建性能对比图表"""
        try:
            self.figure.clear()

            if len(self.experiments) < 2:
                return

            # 准备数据
            exp_names = [exp.experiment_name for exp in self.experiments]
            durations = [exp.duration for exp in self.experiments]
            success_rates = [exp.success_rate for exp in self.experiments]

            # 创建子图
            ax1 = self.figure.add_subplot(121)
            ax2 = self.figure.add_subplot(122)

            # 持续时间对比
            ax1.bar(exp_names, durations, color=["skyblue", "lightcoral"])
            ax1.set_title("实验持续时间对比")
            ax1.set_ylabel("时间 (秒)")
            ax1.tick_params(axis="x", rotation=45)

            # 成功率对比
            ax2.bar(exp_names, success_rates, color=["lightgreen", "orange"])
            ax2.set_title("实验成功率对比")
            ax2.set_ylabel("成功率 (%)")
            ax2.set_ylim(0, 100)
            ax2.tick_params(axis="x", rotation=45)

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"创建性能图表失败: {e}")

    def _generate_performance_recommendations(self):
        """生成性能改进建议"""
        try:
            recommendations = []

            if len(self.experiments) >= 2:
                exp1, exp2 = self.experiments[0], self.experiments[1]

                # 时间对比建议
                if exp2.duration > exp1.duration * 1.2:
                    recommendations.append(
                        f"实验2比实验1耗时多{(exp2.duration / exp1.duration - 1) * 100:.1f}%，建议优化实验流程"
                    )
                elif exp2.duration < exp1.duration * 0.8:
                    recommendations.append(
                        f"实验2比实验1效率高{(1 - exp2.duration / exp1.duration) * 100:.1f}%，可以学习其优化方法"
                    )

                # 成功率对比建议
                if exp2.success_rate < exp1.success_rate - 10:
                    recommendations.append("实验2成功率较低，建议检查实验步骤和参数设置")
                elif exp2.success_rate > exp1.success_rate + 10:
                    recommendations.append("实验2成功率较高，可以推广其成功经验")

                # 步骤对比建议
                if exp2.steps_completed < exp1.steps_completed:
                    recommendations.append("实验2完成步骤较少，建议检查是否有遗漏的步骤")

            # 显示建议
            self.recommendations_text.setPlainText("\n".join(recommendations) if recommendations else "暂无特殊建议")

        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            self.recommendations_text.setPlainText("生成建议时发生错误")

    def _export_results(self):
        """导出对比结果"""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出对比结果",
                f"experiment_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json);;所有文件 (*)",
            )

            if file_path:
                # 准备导出数据
                export_data = {
                    "export_info": {
                        "export_time": datetime.now().isoformat(),
                        "comparison_type": self.comparison_type_combo.currentText(),
                        "experiment_count": len(self.experiments),
                    },
                    "experiments": [asdict(exp) for exp in self.experiments],
                    "results": {
                        "table_data": self._get_table_data(),
                        "recommendations": self.recommendations_text.toPlainText(),
                    },
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "导出成功", f"对比结果已导出到: {file_path}")
                logger.info(f"对比结果导出成功: {file_path}")

        except Exception as e:
            logger.error(f"导出对比结果失败: {e}")
            QMessageBox.critical(self, "导出失败", f"导出对比结果时发生错误: {e}")

    def _get_table_data(self) -> list[list[str]]:
        """获取表格数据"""
        data = []
        for i in range(self.results_table.rowCount()):
            row = []
            for j in range(self.results_table.columnCount()):
                item = self.results_table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
        return data


def create_experiment_comparison_widget(parent=None) -> ExperimentComparisonWidget:
    """创建实验对比界面"""
    return ExperimentComparisonWidget(parent)
