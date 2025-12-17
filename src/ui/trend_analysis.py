"""
趋势分析功能模块

提供实验数据趋势分析、统计和预测功能
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
    PANDAS_AVAILABLE = False

try:
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,  # type: ignore
    )
    from matplotlib.figure import Figure  # type: ignore

    MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    try:
        from matplotlib.backends.backend_qtagg import (
            FigureCanvasQT as FigureCanvas,  # type: ignore
        )
        from matplotlib.figure import Figure  # type: ignore

        MATPLOTLIB_AVAILABLE = True
    except ImportError:
        MATPLOTLIB_AVAILABLE = False

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from scipy import stats

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
except ImportError:
    # 如果sklearn不可用，使用numpy实现简单版本
    LinearRegression = None
    PolynomialFeatures = None

logger = logging.getLogger(__name__)


@dataclass
class TrendData:
    """趋势数据"""

    date: str
    value: float
    experiment_id: str
    user_id: str
    category: str


@dataclass
class TrendAnalysis:
    """趋势分析结果"""

    analysis_id: str
    metric_name: str
    time_period: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1
    correlation_coefficient: float
    p_value: float
    confidence_level: float
    predictions: list[tuple[str, float]]  # (date, predicted_value)
    insights: list[str]
    recommendations: list[str]
    created_at: str


class TrendAnalyzer(QThread):
    """趋势分析线程"""

    analysis_completed = Signal(object)  # TrendAnalysis
    progress_updated = Signal(int)  # progress percentage
    error_occurred = Signal(str)  # error message

    def __init__(self, data: list[TrendData], metric_name: str, time_period: str):
        super().__init__()
        self.data = data
        self.metric_name = metric_name
        self.time_period = time_period

    def run(self):
        """执行趋势分析"""
        try:
            self.progress_updated.emit(10)

            # 数据预处理
            df = self._prepare_data()
            self.progress_updated.emit(30)

            # 计算趋势
            trend_direction, trend_strength = self._calculate_trend(df)
            self.progress_updated.emit(50)

            # 计算相关性
            correlation, p_value = self._calculate_correlation(df)
            self.progress_updated.emit(70)

            # 生成预测
            predictions = self._generate_predictions(df)
            self.progress_updated.emit(85)

            # 生成洞察和建议
            insights, recommendations = self._generate_insights(
                trend_direction, trend_strength, correlation, p_value
            )
            self.progress_updated.emit(95)

            # 创建分析结果
            analysis = TrendAnalysis(
                analysis_id=f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                metric_name=self.metric_name,
                time_period=self.time_period,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                correlation_coefficient=correlation,
                p_value=p_value,
                confidence_level=1 - p_value if p_value < 0.05 else 0.5,
                predictions=predictions,
                insights=insights,
                recommendations=recommendations,
                created_at=datetime.now().isoformat(),
            )

            self.progress_updated.emit(100)
            self.analysis_completed.emit(analysis)

        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            self.error_occurred.emit(str(e))

    def _prepare_data(self) -> pd.DataFrame:
        """准备数据"""
        try:
            if not PANDAS_AVAILABLE or pd is None:
                raise RuntimeError("趋势分析需要 pandas（打包构建可能已排除该依赖）")

            # 转换为DataFrame
            data_dict = {
                "date": [d.date for d in self.data],
                "value": [d.value for d in self.data],
                "experiment_id": [d.experiment_id for d in self.data],
                "user_id": [d.user_id for d in self.data],
                "category": [d.category for d in self.data],
            }

            df = pd.DataFrame(data_dict)

            # 转换日期
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            # 添加时间序列索引
            df["time_index"] = range(len(df))

            return df

        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            raise

    def _calculate_trend(self, df: pd.DataFrame) -> tuple[str, float]:
        """计算趋势"""
        try:
            if len(df) < 2:
                return "stable", 0.0

            x = df["time_index"].values.astype(float)
            y = df["value"].values.astype(float)

            if LinearRegression is not None:
                # sklearn 线性回归
                X = x.reshape(-1, 1)
                model = LinearRegression()
                model.fit(X, y)
                slope = float(model.coef_[0])
                strength = float(model.score(X, y))
            else:
                # numpy 回退实现：y = slope * x + intercept
                slope, intercept = np.polyfit(x, y, 1)
                y_pred = slope * x + intercept
                ss_res = float(np.sum((y - y_pred) ** 2))
                ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
                strength = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            # 判断趋势方向
            if slope > 0.1:
                direction = "increasing"
            elif slope < -0.1:
                direction = "decreasing"
            else:
                direction = "stable"

            return direction, max(0, min(1, strength))

        except Exception as e:
            logger.error(f"计算趋势失败: {e}")
            return "stable", 0.0

    def _calculate_correlation(self, df: pd.DataFrame) -> tuple[float, float]:
        """计算相关性"""
        try:
            if len(df) < 3:
                return 0.0, 1.0

            # 计算皮尔逊相关系数
            correlation, p_value = stats.pearsonr(df["time_index"], df["value"])

            return correlation, p_value

        except Exception as e:
            logger.error(f"计算相关性失败: {e}")
            return 0.0, 1.0

    def _generate_predictions(self, df: pd.DataFrame) -> list[tuple[str, float]]:
        """生成预测"""
        try:
            if len(df) < 3:
                return []

            x = df["time_index"].values.astype(float)
            y = df["value"].values.astype(float)

            if PolynomialFeatures is not None and LinearRegression is not None:
                # sklearn 多项式回归
                poly_features = PolynomialFeatures(degree=2)
                X_poly = poly_features.fit_transform(x.reshape(-1, 1))
                model = LinearRegression()
                model.fit(X_poly, y)

                def predict_value(index: float) -> float:
                    return float(model.predict(poly_features.transform([[index]]))[0])

            else:
                # numpy 回退实现：二次多项式拟合
                coeffs = np.polyfit(x, y, 2)

                def predict_value(index: float) -> float:
                    return float(np.polyval(coeffs, index))

            # 预测未来5个时间点
            predictions = []
            last_date = df["date"].iloc[-1]

            for i in range(1, 6):
                future_index = len(df) + i - 1
                predicted_value = predict_value(float(future_index))

                future_date = last_date + timedelta(days=i)
                predictions.append((future_date.strftime("%Y-%m-%d"), predicted_value))

            return predictions

        except Exception as e:
            logger.error(f"生成预测失败: {e}")
            return []

    def _generate_insights(
        self,
        trend_direction: str,
        trend_strength: float,
        correlation: float,
        p_value: float,
    ) -> tuple[list[str], list[str]]:
        """生成洞察和建议"""
        insights = []
        recommendations = []

        # 趋势洞察
        if trend_strength > 0.7:
            insights.append(f"趋势强度很高 ({trend_strength:.2f})，数据变化模式明显")
        elif trend_strength > 0.4:
            insights.append(f"趋势强度中等 ({trend_strength:.2f})，存在一定的变化模式")
        else:
            insights.append(f"趋势强度较低 ({trend_strength:.2f})，数据变化较为随机")

        # 相关性洞察
        if abs(correlation) > 0.7:
            insights.append(f"时间与数值高度相关 (r={correlation:.2f})")
        elif abs(correlation) > 0.4:
            insights.append(f"时间与数值中度相关 (r={correlation:.2f})")
        else:
            insights.append(f"时间与数值相关性较低 (r={correlation:.2f})")

        # 统计显著性
        if p_value < 0.05:
            insights.append("趋势具有统计显著性 (p < 0.05)")
        else:
            insights.append("趋势不具有统计显著性 (p >= 0.05)")

        # 建议
        if trend_direction == "increasing" and trend_strength > 0.5:
            recommendations.append("数据呈上升趋势，建议继续保持当前策略")
        elif trend_direction == "decreasing" and trend_strength > 0.5:
            recommendations.append("数据呈下降趋势，建议分析原因并采取改进措施")
        elif trend_strength < 0.3:
            recommendations.append("数据变化不够明显，建议收集更多数据或调整分析方法")

        if p_value >= 0.05:
            recommendations.append("由于统计显著性不足，建议谨慎解读趋势结果")

        return insights, recommendations


class TrendAnalysisWidget(QWidget):
    """趋势分析界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.trend_data: list[TrendData] = []
        self.analysis_results: list[TrendAnalysis] = []
        self.data_dir = Path("data")

        self._init_ui()
        self._load_trend_data()

        logger.info("趋势分析界面初始化完成")

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 顶部控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：数据选择
        left_panel = self._create_data_selection_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：分析结果
        right_panel = self._create_analysis_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([300, 700])
        layout.addWidget(main_splitter)

        # 底部状态栏
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QGroupBox("分析控制")
        layout = QHBoxLayout(panel)

        # 指标选择
        layout.addWidget(QLabel("分析指标:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(
            ["成功率", "完成时间", "数据质量", "用户满意度", "错误率"]
        )
        layout.addWidget(self.metric_combo)

        # 时间范围
        layout.addWidget(QLabel("时间范围:"))
        self.time_period_combo = QComboBox()
        self.time_period_combo.addItems(
            ["最近7天", "最近30天", "最近90天", "最近1年", "全部时间"]
        )
        layout.addWidget(self.time_period_combo)

        # 开始分析按钮
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self._start_analysis)
        layout.addWidget(self.analyze_btn)

        # 导出结果按钮
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self._export_results)
        layout.addWidget(self.export_btn)

        if not PANDAS_AVAILABLE:
            self.analyze_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            hint = QLabel("缺少依赖：pandas（趋势分析已禁用）")
            hint.setStyleSheet("color: #a33; padding-left: 8px;")
            layout.addWidget(hint)

        layout.addStretch()
        return panel

    def _create_data_selection_panel(self) -> QWidget:
        """创建数据选择面板"""
        panel = QGroupBox("数据选择")
        layout = QVBoxLayout(panel)

        # 数据预览表格
        layout.addWidget(QLabel("数据预览:"))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(
            ["日期", "数值", "实验ID", "用户", "类别"]
        )
        layout.addWidget(self.data_table)

        # 数据统计
        stats_layout = QHBoxLayout()

        self.data_count_label = QLabel("数据点: 0")
        stats_layout.addWidget(self.data_count_label)

        self.date_range_label = QLabel("日期范围: -")
        stats_layout.addWidget(self.date_range_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        return panel

    def _create_analysis_panel(self) -> QWidget:
        """创建分析面板"""
        panel = QTabWidget()

        # 趋势图表标签页
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout(self.chart_tab)

        # 图表画布
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(10, 6))
            self.canvas = FigureCanvas(self.figure)
            chart_layout.addWidget(self.canvas)
        else:
            self.figure = None
            self.canvas = None
            missing_label = QLabel(
                "趋势图表需要 matplotlib（打包构建可能已排除该依赖）。"
            )
            missing_label.setWordWrap(True)
            missing_label.setStyleSheet("color: #666; padding: 12px;")
            chart_layout.addWidget(missing_label)

        panel.addTab(self.chart_tab, "趋势图表")

        # 分析结果标签页
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)

        # 结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["指标", "数值", "说明", "状态"])
        results_layout.addWidget(self.results_table)

        panel.addTab(self.results_tab, "分析结果")

        # 预测标签页
        self.prediction_tab = QWidget()
        prediction_layout = QVBoxLayout(self.prediction_tab)

        self.prediction_table = QTableWidget()
        self.prediction_table.setColumnCount(3)
        self.prediction_table.setHorizontalHeaderLabels(["日期", "预测值", "置信度"])
        prediction_layout.addWidget(self.prediction_table)

        panel.addTab(self.prediction_tab, "趋势预测")

        # 洞察标签页
        self.insights_tab = QWidget()
        insights_layout = QVBoxLayout(self.insights_tab)

        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        insights_layout.addWidget(self.insights_text)

        panel.addTab(self.insights_tab, "洞察建议")

        return panel

    def _load_trend_data(self):
        """加载趋势数据"""
        try:
            # 扫描实验记录
            records_dir = self.data_dir / "records"
            if not records_dir.exists():
                self.status_label.setText("未找到实验记录")
                return

            trend_data = []
            for record_file in records_dir.glob("*.json"):
                try:
                    with open(record_file, encoding="utf-8") as f:
                        record_data = json.load(f)

                    # 提取趋势数据
                    experiment_id = record_data.get("experiment_id", "")
                    user_id = record_data.get("user_id", "")
                    completed_at = record_data.get("completed_at", "")

                    if completed_at:
                        # 成功率
                        steps_completed = len(record_data.get("step_records", []))
                        total_steps = record_data.get("total_steps", steps_completed)
                        success_rate = (
                            (steps_completed / total_steps) * 100
                            if total_steps > 0
                            else 0
                        )

                        trend_data.append(
                            TrendData(
                                date=completed_at,
                                value=success_rate,
                                experiment_id=experiment_id,
                                user_id=user_id,
                                category="成功率",
                            )
                        )

                        # 完成时间
                        started_at = record_data.get("started_at", "")
                        if started_at:
                            try:
                                start_time = datetime.fromisoformat(
                                    started_at.replace("Z", "+00:00")
                                )
                                end_time = datetime.fromisoformat(
                                    completed_at.replace("Z", "+00:00")
                                )
                                duration = (end_time - start_time).total_seconds()

                                trend_data.append(
                                    TrendData(
                                        date=completed_at,
                                        value=duration,
                                        experiment_id=experiment_id,
                                        user_id=user_id,
                                        category="完成时间",
                                    )
                                )
                            except Exception:
                                pass

                except Exception as e:
                    logger.error(f"读取实验记录失败: {e}")
                    continue

            self.trend_data = trend_data
            self._update_data_preview()

            self.status_label.setText(f"加载了 {len(trend_data)} 个数据点")

        except Exception as e:
            logger.error(f"加载趋势数据失败: {e}")
            self.status_label.setText(f"加载数据失败: {e}")

    def _update_data_preview(self):
        """更新数据预览"""
        try:
            # 过滤数据
            metric = self.metric_combo.currentText()
            filtered_data = [d for d in self.trend_data if d.category == metric]

            # 更新表格
            self.data_table.setRowCount(len(filtered_data))
            for i, data in enumerate(filtered_data):
                self.data_table.setItem(i, 0, QTableWidgetItem(data.date[:10]))
                self.data_table.setItem(i, 1, QTableWidgetItem(f"{data.value:.2f}"))
                self.data_table.setItem(i, 2, QTableWidgetItem(data.experiment_id))
                self.data_table.setItem(i, 3, QTableWidgetItem(data.user_id))
                self.data_table.setItem(i, 4, QTableWidgetItem(data.category))

            # 更新统计信息
            self.data_count_label.setText(f"数据点: {len(filtered_data)}")

            if filtered_data:
                dates = [d.date for d in filtered_data]
                min_date = min(dates)
                max_date = max(dates)
                self.date_range_label.setText(
                    f"日期范围: {min_date[:10]} 到 {max_date[:10]}"
                )
            else:
                self.date_range_label.setText("日期范围: -")

        except Exception as e:
            logger.error(f"更新数据预览失败: {e}")

    def _start_analysis(self):
        """开始分析"""
        try:
            if not PANDAS_AVAILABLE or pd is None:
                QMessageBox.warning(
                    self, "依赖缺失", "趋势分析需要 pandas，请安装后重试。"
                )
                return

            metric = self.metric_combo.currentText()
            time_period = self.time_period_combo.currentText()

            # 过滤数据
            filtered_data = [d for d in self.trend_data if d.category == metric]

            if len(filtered_data) < 3:
                QMessageBox.warning(self, "数据不足", "至少需要3个数据点进行趋势分析")
                return

            # 显示进度
            progress = QProgressDialog("正在分析趋势...", "取消", 0, 100, self)
            progress.setWindowTitle("正在分析趋势...")
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.show()

            # 创建分析线程
            analyzer = TrendAnalyzer(filtered_data, metric, time_period)

            def on_analysis_completed(analysis):
                progress.close()
                self.analysis_results.append(analysis)
                self._display_analysis_results(analysis)

            def on_progress_updated(value):
                progress.setValue(value)

            def on_error(error_msg):
                progress.close()
                QMessageBox.critical(
                    self, "分析失败", f"趋势分析时发生错误: {error_msg}"
                )

            analyzer.analysis_completed.connect(on_analysis_completed)
            analyzer.progress_updated.connect(on_progress_updated)
            analyzer.error_occurred.connect(on_error)

            analyzer.start()

        except Exception as e:
            logger.error(f"开始分析失败: {e}")
            QMessageBox.critical(self, "分析失败", f"开始分析时发生错误: {e}")

    def _display_analysis_results(self, analysis: TrendAnalysis):
        """显示分析结果"""
        try:
            # 更新结果表格
            self.results_table.setRowCount(6)

            results = [
                ("趋势方向", analysis.trend_direction, "数据变化的主要方向", "正常"),
                (
                    "趋势强度",
                    f"{analysis.trend_strength:.3f}",
                    "趋势的明显程度",
                    "正常",
                ),
                (
                    "相关系数",
                    f"{analysis.correlation_coefficient:.3f}",
                    "时间与数值的相关性",
                    "正常",
                ),
                ("P值", f"{analysis.p_value:.3f}", "统计显著性", "正常"),
                (
                    "置信度",
                    f"{analysis.confidence_level:.1%}",
                    "结果的可信程度",
                    "正常",
                ),
                ("数据点数", str(len(self.trend_data)), "用于分析的数据量", "正常"),
            ]

            for i, (metric, value, description, status) in enumerate(results):
                self.results_table.setItem(i, 0, QTableWidgetItem(metric))
                self.results_table.setItem(i, 1, QTableWidgetItem(value))
                self.results_table.setItem(i, 2, QTableWidgetItem(description))
                self.results_table.setItem(i, 3, QTableWidgetItem(status))

            # 更新预测表格
            self.prediction_table.setRowCount(len(analysis.predictions))
            for i, (date, predicted_value) in enumerate(analysis.predictions):
                self.prediction_table.setItem(i, 0, QTableWidgetItem(date))
                self.prediction_table.setItem(
                    i, 1, QTableWidgetItem(f"{predicted_value:.2f}")
                )
                self.prediction_table.setItem(
                    i, 2, QTableWidgetItem(f"{analysis.confidence_level:.1%}")
                )

            # 更新洞察文本
            insights_text = "洞察:\n" + "\n".join(
                f"• {insight}" for insight in analysis.insights
            )
            insights_text += "\n\n建议:\n" + "\n".join(
                f"• {rec}" for rec in analysis.recommendations
            )
            self.insights_text.setPlainText(insights_text)

            # 创建趋势图表
            self._create_trend_chart(analysis)

            self.status_label.setText(f"分析完成: {analysis.metric_name}")

        except Exception as e:
            logger.error(f"显示分析结果失败: {e}")
            QMessageBox.critical(self, "显示失败", f"显示分析结果时发生错误: {e}")

    def _create_trend_chart(self, analysis: TrendAnalysis):
        """创建趋势图表"""
        try:
            if not MATPLOTLIB_AVAILABLE or self.figure is None or self.canvas is None:
                return

            self.figure.clear()

            # 准备数据
            metric = analysis.metric_name
            filtered_data = [d for d in self.trend_data if d.category == metric]

            if not filtered_data:
                return

            # 转换数据
            dates = [
                datetime.fromisoformat(d.date.replace("Z", "+00:00"))
                for d in filtered_data
            ]
            values = [d.value for d in filtered_data]

            # 创建子图
            ax1 = self.figure.add_subplot(121)
            ax2 = self.figure.add_subplot(122)

            # 原始数据散点图
            ax1.scatter(dates, values, alpha=0.6, color="blue")
            ax1.set_title(f"{metric}趋势图")
            ax1.set_xlabel("日期")
            ax1.set_ylabel(metric)
            ax1.tick_params(axis="x", rotation=45)

            # 趋势线
            if len(dates) > 1:
                # 计算趋势线
                x_numeric = [(d - dates[0]).days for d in dates]
                z = np.polyfit(x_numeric, values, 1)
                p = np.poly1d(z)

                ax1.plot(
                    dates,
                    p(x_numeric),
                    "r--",
                    alpha=0.8,
                    label=f"趋势线 (斜率: {z[0]:.2f})",
                )
                ax1.legend()

            # 预测数据
            if analysis.predictions:
                pred_dates = [
                    datetime.fromisoformat(pred[0]) for pred in analysis.predictions
                ]
                pred_values = [pred[1] for pred in analysis.predictions]

                ax2.plot(pred_dates, pred_values, "g-", marker="o", label="预测值")
                ax2.set_title(f"{metric}预测")
                ax2.set_xlabel("日期")
                ax2.set_ylabel(metric)
                ax2.tick_params(axis="x", rotation=45)
                ax2.legend()

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"创建趋势图表失败: {e}")

    def _export_results(self):
        """导出分析结果"""
        try:
            from PySide6.QtWidgets import QFileDialog

            if not self.analysis_results:
                QMessageBox.warning(self, "无数据", "没有可导出的分析结果")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                f"trend_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json);;所有文件 (*)",
            )

            if file_path:
                # 准备导出数据
                export_data = {
                    "export_info": {
                        "export_time": datetime.now().isoformat(),
                        "analysis_count": len(self.analysis_results),
                    },
                    "trend_data": [asdict(d) for d in self.trend_data],
                    "analysis_results": [
                        asdict(result) for result in self.analysis_results
                    ],
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(
                    self, "导出成功", f"分析结果已导出到: {file_path}"
                )
                logger.info(f"分析结果导出成功: {file_path}")

        except Exception as e:
            logger.error(f"导出分析结果失败: {e}")
            QMessageBox.critical(self, "导出失败", f"导出分析结果时发生错误: {e}")


def create_trend_analysis_widget(parent=None) -> TrendAnalysisWidget:
    """创建趋势分析界面"""
    return TrendAnalysisWidget(parent)
