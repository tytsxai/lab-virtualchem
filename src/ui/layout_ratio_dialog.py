"""
布局比例分析对话框
提供可视化的布局比例分析和优化界面
"""

import logging
import math
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .layout_ratio_analyzer import (
    analyze_layout_ratios,
    export_layout_analysis_report,
    get_layout_history,
    get_user_layout_preferences,
    set_user_layout_preference,
)

logger = logging.getLogger(__name__)


class LayoutRatioChartWidget(QWidget):
    """布局比例图表组件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self._chart_data: list[dict[str, Any]] = []
        self._chart_type = "bar"  # bar, pie, line

    def set_chart_data(self, data: list[dict[str, Any]]) -> None:
        """设置图表数据"""
        self._chart_data = data
        self.update()

    def set_chart_type(self, chart_type: str) -> None:
        """设置图表类型"""
        self._chart_type = chart_type
        self.update()

    def paintEvent(self, _event: Any) -> None:
        """绘制图表"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 绘制背景
            painter.fillRect(self.rect(), Qt.GlobalColor.white)

            if not self._chart_data:
                return

            # 绘制图表
            if self._chart_type == "bar":
                self._draw_bar_chart(painter)
            elif self._chart_type == "pie":
                self._draw_pie_chart(painter)
            elif self._chart_type == "line":
                self._draw_line_chart(painter)

        except Exception as e:
            logger.error(f"绘制图表失败: {e}", exc_info=True)

    def _draw_bar_chart(self, painter: QPainter) -> None:
        """绘制柱状图"""
        try:
            if not self._chart_data:
                return

            # 计算绘制区域
            margin = 50
            chart_rect = self.rect().adjusted(margin, margin, -margin, -margin)

            # 计算最大值
            max_value = max(item.get("value", 0) for item in self._chart_data)
            if max_value == 0:
                return

            # 绘制柱状图
            bar_width = chart_rect.width() // len(self._chart_data)
            colors = [
                Qt.GlobalColor.blue,
                Qt.GlobalColor.green,
                Qt.GlobalColor.red,
                Qt.GlobalColor.yellow,
            ]

            for i, item in enumerate(self._chart_data):
                value = item.get("value", 0)
                label = item.get("label", "")

                # 计算柱状图高度
                bar_height = int((value / max_value) * chart_rect.height())
                bar_rect = chart_rect.adjusted(
                    i * bar_width,
                    chart_rect.height() - bar_height,
                    (i + 1) * bar_width - 5,
                    chart_rect.height(),
                )

                # 绘制柱子
                color = colors[i % len(colors)]
                painter.fillRect(bar_rect, QBrush(color))
                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.drawRect(bar_rect)

                # 绘制标签
                painter.setPen(QPen(Qt.GlobalColor.black))
                painter.drawText(
                    bar_rect.adjusted(0, 5, 0, 5),
                    Qt.AlignmentFlag.AlignCenter,
                    f"{label}\n{value:.1f}",
                )

        except Exception as e:
            logger.error(f"绘制柱状图失败: {e}", exc_info=True)

    def _draw_pie_chart(self, painter: QPainter) -> None:
        """绘制饼图"""
        try:
            if not self._chart_data:
                return

            # 计算总和
            total = sum(item.get("value", 0) for item in self._chart_data)
            if total == 0:
                return

            # 计算绘制区域
            margin = 50
            chart_rect = self.rect().adjusted(margin, margin, -margin, -margin)
            center = chart_rect.center()
            radius = min(chart_rect.width(), chart_rect.height()) // 2 - 20

            # 绘制饼图
            start_angle = 0
            colors = [
                Qt.GlobalColor.blue,
                Qt.GlobalColor.green,
                Qt.GlobalColor.red,
                Qt.GlobalColor.yellow,
            ]

            for i, item in enumerate(self._chart_data):
                value = item.get("value", 0)
                label = item.get("label", "")

                # 计算角度
                angle = int((value / total) * 360 * 16)  # Qt使用1/16度

                # 绘制扇形
                color = colors[i % len(colors)]
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.drawPie(
                    center.x() - radius,
                    center.y() - radius,
                    radius * 2,
                    radius * 2,
                    start_angle,
                    angle,
                )

                # 绘制标签
                mid_angle = start_angle + angle // 2
                label_x = center.x() + int(
                    radius * 1.2 * math.cos(math.radians(mid_angle / 16))
                )
                label_y = center.y() + int(
                    radius * 1.2 * math.sin(math.radians(mid_angle / 16))
                )

                painter.setPen(QPen(Qt.GlobalColor.black))
                painter.drawText(label_x, label_y, f"{label}\n{value:.1f}")

                start_angle += angle

        except Exception as e:
            logger.error(f"绘制饼图失败: {e}", exc_info=True)

    def _draw_line_chart(self, painter: QPainter) -> None:
        """绘制折线图"""
        try:
            if len(self._chart_data) < 2:
                return

            # 计算绘制区域
            margin = 50
            chart_rect = self.rect().adjusted(margin, margin, -margin, -margin)

            # 计算数据范围
            values = [item.get("value", 0) for item in self._chart_data]
            min_val = min(values)
            max_val = max(values)
            val_range = max_val - min_val if max_val > min_val else 1

            # 绘制折线
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))

            points = []
            for i, item in enumerate(self._chart_data):
                value = item.get("value", 0)
                x = chart_rect.left() + (
                    chart_rect.width() * i / (len(self._chart_data) - 1)
                )
                y = chart_rect.bottom() - (
                    chart_rect.height() * (value - min_val) / val_range
                )
                points.append((x, y))

            for i in range(len(points) - 1):
                painter.drawLine(
                    int(points[i][0]),
                    int(points[i][1]),
                    int(points[i + 1][0]),
                    int(points[i + 1][1]),
                )

            # 绘制数据点
            painter.setBrush(QBrush(Qt.GlobalColor.red))
            for x, y in points:
                painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)

        except Exception as e:
            logger.error(f"绘制折线图失败: {e}", exc_info=True)


class LayoutRatioDialog(QDialog):
    """布局比例分析对话框"""

    # 信号
    layout_optimized = Signal(str, dict)  # 组件名, 优化结果

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("布局比例分析器")
        self.setMinimumSize(1000, 700)
        self.setModal(False)

        # 分析结果
        self._analysis_result: dict[str, Any] = {}

        # 图表组件
        self.ratio_chart = LayoutRatioChartWidget()
        self.performance_chart = LayoutRatioChartWidget()
        self.history_chart = LayoutRatioChartWidget()

        self.init_ui()
        self.connect_signals()
        self.load_analysis_data()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 概览标签页
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "概览")

        # 详细分析标签页
        self.analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "详细分析")

        # 性能监控标签页
        self.performance_tab = self.create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "性能监控")

        # 历史记录标签页
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "历史记录")

        # 用户偏好标签页
        self.preferences_tab = self.create_preferences_tab()
        self.tab_widget.addTab(self.preferences_tab, "用户偏好")

        # 底部按钮
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("刷新分析")
        self.refresh_button.clicked.connect(self.refresh_analysis)

        self.export_button = QPushButton("导出报告")
        self.export_button.clicked.connect(self.export_report)

        self.optimize_button = QPushButton("优化布局")
        self.optimize_button.clicked.connect(self.optimize_layouts)

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.optimize_button)
        button_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def create_overview_tab(self) -> QWidget:
        """创建概览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 综合评分
        scores_group = QGroupBox("综合评分")
        scores_layout = QFormLayout(scores_group)

        self.accessibility_score_bar = QProgressBar()
        self.accessibility_score_bar.setRange(0, 100)
        self.accessibility_score_label = QLabel("0.0")
        scores_layout.addRow("无障碍访问评分:", self.accessibility_score_bar)
        scores_layout.addRow("", self.accessibility_score_label)

        self.golden_ratio_bar = QProgressBar()
        self.golden_ratio_bar.setRange(0, 100)
        self.golden_ratio_label = QLabel("0.0%")
        scores_layout.addRow("黄金比例合规性:", self.golden_ratio_bar)
        scores_layout.addRow("", self.golden_ratio_label)

        self.responsive_score_bar = QProgressBar()
        self.responsive_score_bar.setRange(0, 100)
        self.responsive_score_label = QLabel("0.0")
        scores_layout.addRow("响应式设计评分:", self.responsive_score_bar)
        scores_layout.addRow("", self.responsive_score_label)

        layout.addWidget(scores_group)

        # 布局比例图表
        chart_group = QGroupBox("布局比例分布")
        chart_layout = QVBoxLayout(chart_group)

        self.ratio_chart.set_chart_type("bar")
        chart_layout.addWidget(self.ratio_chart)

        layout.addWidget(chart_group)

        return widget

    def create_analysis_tab(self) -> QWidget:
        """创建详细分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 分析结果
        analysis_group = QGroupBox("分析结果")
        analysis_layout = QVBoxLayout(analysis_group)

        self.analysis_scroll = QScrollArea()
        self.analysis_content = QWidget()
        self.analysis_layout = QVBoxLayout(self.analysis_content)
        self.analysis_scroll.setWidget(self.analysis_content)
        self.analysis_scroll.setWidgetResizable(True)

        analysis_layout.addWidget(self.analysis_scroll)
        layout.addWidget(analysis_group)

        return widget

    def create_performance_tab(self) -> QWidget:
        """创建性能监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 性能指标
        performance_group = QGroupBox("性能指标")
        performance_layout = QFormLayout(performance_group)

        self.memory_usage_bar = QProgressBar()
        self.memory_usage_bar.setRange(0, 100)
        self.memory_usage_label = QLabel("0%")
        performance_layout.addRow("内存使用率:", self.memory_usage_bar)
        performance_layout.addRow("", self.memory_usage_label)

        self.render_time_label = QLabel("0ms")
        performance_layout.addRow("渲染时间:", self.render_time_label)

        self.layout_time_label = QLabel("0ms")
        performance_layout.addRow("布局时间:", self.layout_time_label)

        layout.addWidget(performance_group)

        # 性能图表
        chart_group = QGroupBox("性能趋势")
        chart_layout = QVBoxLayout(chart_group)

        self.performance_chart.set_chart_type("line")
        chart_layout.addWidget(self.performance_chart)

        layout.addWidget(chart_group)

        return widget

    def create_history_tab(self) -> QWidget:
        """创建历史记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 历史记录
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout(history_group)

        self.history_scroll = QScrollArea()
        self.history_content = QWidget()
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_scroll.setWidget(self.history_content)
        self.history_scroll.setWidgetResizable(True)

        history_layout.addWidget(self.history_scroll)
        layout.addWidget(history_group)

        # 历史图表
        chart_group = QGroupBox("历史趋势")
        chart_layout = QVBoxLayout(chart_group)

        self.history_chart.set_chart_type("line")
        chart_layout.addWidget(self.history_chart)

        layout.addWidget(chart_group)

        return widget

    def create_preferences_tab(self) -> QWidget:
        """创建用户偏好标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 用户偏好设置
        preferences_group = QGroupBox("用户偏好设置")
        preferences_layout = QFormLayout(preferences_group)

        self.auto_optimize_checkbox = QCheckBox("自动优化布局")
        preferences_layout.addRow("自动优化:", self.auto_optimize_checkbox)

        self.golden_ratio_checkbox = QCheckBox("优先使用黄金比例")
        preferences_layout.addRow("黄金比例:", self.golden_ratio_checkbox)

        self.accessibility_checkbox = QCheckBox("无障碍访问优先")
        preferences_layout.addRow("无障碍访问:", self.accessibility_checkbox)

        layout.addWidget(preferences_group)

        # 保存按钮
        save_button = QPushButton("保存偏好")
        save_button.clicked.connect(self.save_preferences)
        layout.addWidget(save_button)

        layout.addStretch()

        return widget

    def connect_signals(self) -> None:
        """连接信号"""
        try:
            # 连接复选框的状态变化信号，实现实时预览
            if hasattr(self, "auto_optimize_checkbox"):
                self.auto_optimize_checkbox.stateChanged.connect(
                    self._on_preference_changed
                )
            if hasattr(self, "golden_ratio_checkbox"):
                self.golden_ratio_checkbox.stateChanged.connect(
                    self._on_preference_changed
                )
            if hasattr(self, "accessibility_checkbox"):
                self.accessibility_checkbox.stateChanged.connect(
                    self._on_preference_changed
                )

            logger.debug("布局比例对话框信号连接完成")
        except Exception as e:
            logger.warning(f"连接布局比例对话框信号失败: {e}")

    def _on_preference_changed(self, _state: int) -> None:
        """用户偏好改变时的处理（实时预览）"""
        try:
            # 这里可以添加实时预览逻辑
            # 例如：根据新的偏好设置更新布局显示
            logger.debug("用户偏好已更改，等待保存")
        except Exception as e:
            logger.warning(f"处理偏好更改失败: {e}")

    def load_analysis_data(self) -> None:
        """加载分析数据"""
        try:
            # 获取分析结果
            self._analysis_result = analyze_layout_ratios()

            # 更新UI
            self.update_overview_tab()
            self.update_analysis_tab()
            self.update_performance_tab()
            self.update_history_tab()
            self.update_preferences_tab()

        except Exception as e:
            logger.error(f"加载分析数据失败: {e}", exc_info=True)

    def update_overview_tab(self) -> None:
        """更新概览标签页"""
        try:
            if not self._analysis_result:
                return

            # 更新评分
            accessibility_score = self._analysis_result.get("accessibility_score", 0)
            self.accessibility_score_bar.setValue(int(accessibility_score * 10))
            self.accessibility_score_label.setText(f"{accessibility_score:.1f}")

            golden_ratio_compliance = self._analysis_result.get(
                "golden_ratio_compliance", 0
            )
            self.golden_ratio_bar.setValue(int(golden_ratio_compliance))
            self.golden_ratio_label.setText(f"{golden_ratio_compliance:.1f}%")

            responsive_score = self._analysis_result.get("responsive_score", 0)
            self.responsive_score_bar.setValue(int(responsive_score))
            self.responsive_score_label.setText(f"{responsive_score:.1f}")

            # 更新图表
            chart_data = []
            for component, ratio_info in self._analysis_result.get(
                "current_ratios", {}
            ).items():
                if "accessibility_score" in ratio_info:
                    chart_data.append(
                        {"label": component, "value": ratio_info["accessibility_score"]}
                    )

            self.ratio_chart.set_chart_data(chart_data)

        except Exception as e:
            logger.error(f"更新概览标签页失败: {e}", exc_info=True)

    def update_analysis_tab(self) -> None:
        """更新详细分析标签页"""
        try:
            # 清空现有内容
            for i in reversed(range(self.analysis_layout.count())):
                child = self.analysis_layout.itemAt(i).widget()
                if child:
                    child.deleteLater()

            # 添加分析结果
            if "recommendations" in self._analysis_result:
                for rec in self._analysis_result["recommendations"]:
                    label = QLabel(f"✅ {rec.get('message', '')}")
                    label.setWordWrap(True)
                    self.analysis_layout.addWidget(label)

            if "issues" in self._analysis_result:
                for issue in self._analysis_result["issues"]:
                    label = QLabel(f"⚠️ {issue.get('issue', '')}")
                    label.setWordWrap(True)
                    self.analysis_layout.addWidget(label)

            if "optimization_suggestions" in self._analysis_result:
                for suggestion in self._analysis_result["optimization_suggestions"]:
                    label = QLabel(f"💡 {suggestion.get('suggestion', '')}")
                    label.setWordWrap(True)
                    self.analysis_layout.addWidget(label)

        except Exception as e:
            logger.error(f"更新详细分析标签页失败: {e}", exc_info=True)

    def update_performance_tab(self) -> None:
        """更新性能监控标签页"""
        try:
            performance_metrics = self._analysis_result.get("performance_metrics", {})

            # 更新内存使用率
            memory_info = performance_metrics.get("memory_usage", {})
            if memory_info:
                current_memory = memory_info.get("current", 0)
                self.memory_usage_bar.setValue(int(current_memory))
                self.memory_usage_label.setText(f"{current_memory:.1f}%")

            # 更新渲染时间
            render_info = performance_metrics.get("render_time", {})
            if render_info:
                current_render = render_info.get("current", 0)
                self.render_time_label.setText(f"{current_render:.1f}ms")

            # 更新布局时间
            layout_info = performance_metrics.get("layout_time", {})
            if layout_info:
                current_layout = layout_info.get("current", 0)
                self.layout_time_label.setText(f"{current_layout:.1f}ms")

            # 更新性能图表
            chart_data = []
            if render_info:
                chart_data.append(
                    {"label": "渲染时间", "value": render_info.get("average", 0)}
                )
            if layout_info:
                chart_data.append(
                    {"label": "布局时间", "value": layout_info.get("average", 0)}
                )

            self.performance_chart.set_chart_data(chart_data)

        except Exception as e:
            logger.error(f"更新性能监控标签页失败: {e}", exc_info=True)

    def update_history_tab(self) -> None:
        """更新历史记录标签页"""
        try:
            # 获取历史记录
            history = get_layout_history()

            # 清空现有内容
            for i in reversed(range(self.history_layout.count())):
                child = self.history_layout.itemAt(i).widget()
                if child:
                    child.deleteLater()

            # 添加历史记录
            for entry in history[-10:]:  # 显示最近10条记录
                timestamp = entry.get("timestamp", "")
                screen_type = entry.get("screen_type", "")
                accessibility_score = entry.get("accessibility_score", 0)

                label = QLabel(
                    f"{timestamp} - {screen_type} - 无障碍评分: {accessibility_score:.1f}"
                )
                label.setWordWrap(True)
                self.history_layout.addWidget(label)

            # 更新历史图表
            chart_data = []
            for entry in history:
                chart_data.append(
                    {
                        "label": entry.get("screen_type", ""),
                        "value": entry.get("accessibility_score", 0),
                    }
                )

            self.history_chart.set_chart_data(chart_data)

        except Exception as e:
            logger.error(f"更新历史记录标签页失败: {e}", exc_info=True)

    def update_preferences_tab(self) -> None:
        """更新用户偏好标签页"""
        try:
            preferences = get_user_layout_preferences()

            # 更新复选框状态
            self.auto_optimize_checkbox.setChecked(
                preferences.get("auto_optimize", False)
            )
            self.golden_ratio_checkbox.setChecked(
                preferences.get("golden_ratio", False)
            )
            self.accessibility_checkbox.setChecked(
                preferences.get("accessibility", False)
            )

        except Exception as e:
            logger.error(f"更新用户偏好标签页失败: {e}", exc_info=True)

    def refresh_analysis(self) -> None:
        """刷新分析"""
        self.load_analysis_data()

    def export_report(self) -> None:
        """导出报告"""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出分析报告", "layout_analysis_report.json", "JSON文件 (*.json)"
            )

            if file_path:
                success = export_layout_analysis_report(file_path)
                if success:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.information(
                        self, "导出成功", f"报告已导出到: {file_path}"
                    )
                else:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(self, "导出失败", "报告导出失败")

        except Exception as e:
            logger.error(f"导出报告失败: {e}", exc_info=True)

    def optimize_layouts(self) -> None:
        """优化布局"""
        try:
            # 这里可以添加实际的布局优化逻辑
            logger.info("开始优化布局")

            # 发出优化信号
            self.layout_optimized.emit("all", {"status": "optimized"})

        except Exception as e:
            logger.error(f"优化布局失败: {e}", exc_info=True)

    def save_preferences(self) -> None:
        """保存偏好设置"""
        try:
            set_user_layout_preference(
                "auto_optimize", self.auto_optimize_checkbox.isChecked()
            )
            set_user_layout_preference(
                "golden_ratio", self.golden_ratio_checkbox.isChecked()
            )
            set_user_layout_preference(
                "accessibility", self.accessibility_checkbox.isChecked()
            )

            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "保存成功", "用户偏好已保存")

        except Exception as e:
            logger.error(f"保存偏好设置失败: {e}", exc_info=True)
