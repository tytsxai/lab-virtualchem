"""
实时图表组件
用于实验数据的实时可视化显示
"""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RealtimeLineChart(QWidget):
    """实时折线图"""

    def __init__(
        self,
        title: str = "数据监测",
        y_label: str = "数值",
        max_points: int = 50,
        y_min: float = 0.0,
        y_max: float = 100.0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.title = title
        self.y_label = y_label
        self.max_points = max_points
        self.y_min = y_min
        self.y_max = y_max

        # 数据存储
        self.data_points = deque(maxlen=max_points)
        self.time_labels = deque(maxlen=max_points)

        # 颜色设置
        self.line_color = QColor(0, 120, 212)
        self.fill_color = QColor(0, 120, 212, 50)
        self.grid_color = QColor(200, 200, 200)
        self.text_color = QColor(50, 50, 50)

        self.setMinimumSize(400, 300)

        logger.info(f"创建实时折线图: {title}")

    def add_data_point(self, value: float, time_label: str = ""):
        """添加数据点"""
        self.data_points.append(value)
        self.time_labels.append(time_label if time_label else str(len(self.data_points)))
        self.update()

    def clear_data(self):
        """清空数据"""
        self.data_points.clear()
        self.time_labels.clear()
        self.update()

    def set_y_range(self, y_min: float, y_max: float):
        """设置Y轴范围"""
        self.y_min = y_min
        self.y_max = y_max
        self.update()

    def paintEvent(self, _event):
        """绘制图表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 边距
        margin_left = 60
        margin_right = 20
        margin_top = 50
        margin_bottom = 50

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        # 背景
        painter.fillRect(0, 0, width, height, QColor(255, 255, 255))

        # 标题
        painter.setPen(QPen(self.text_color))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, width, margin_top, Qt.AlignmentFlag.AlignCenter, self.title)

        # 绘制坐标轴
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        # Y轴
        painter.drawLine(margin_left, margin_top, margin_left, height - margin_bottom)
        # X轴
        painter.drawLine(margin_left, height - margin_bottom, width - margin_right, height - margin_bottom)

        # Y轴标签
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)

        num_y_ticks = 5
        for i in range(num_y_ticks + 1):
            y_value = self.y_min + (self.y_max - self.y_min) * i / num_y_ticks
            y_pos = height - margin_bottom - (chart_height * i / num_y_ticks)

            # 网格线
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, int(y_pos), width - margin_right, int(y_pos))

            # 标签
            painter.setPen(QPen(self.text_color))
            painter.drawText(0, int(y_pos - 10), margin_left - 5, 20, Qt.AlignmentFlag.AlignRight, f"{y_value:.1f}")

        # Y轴标题
        painter.save()
        painter.translate(15, height / 2)
        painter.rotate(-90)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(-50, -5, 100, 20, Qt.AlignmentFlag.AlignCenter, self.y_label)
        painter.restore()

        # 绘制数据
        if len(self.data_points) > 1:
            # 计算点位置
            points = []
            for i, value in enumerate(self.data_points):
                x = margin_left + (chart_width * i / (self.max_points - 1))
                # 限制值在范围内
                clamped_value = max(self.y_min, min(value, self.y_max))
                y_ratio = (clamped_value - self.y_min) / (self.y_max - self.y_min) if self.y_max > self.y_min else 0
                y = height - margin_bottom - (chart_height * y_ratio)
                points.append(QPointF(x, y))

            # 绘制填充区域
            if len(points) > 0:
                from PySide6.QtGui import QPainterPath

                path = QPainterPath()
                path.moveTo(points[0].x(), height - margin_bottom)
                for point in points:
                    path.lineTo(point)
                path.lineTo(points[-1].x(), height - margin_bottom)
                path.closeSubpath()

                # 渐变填充
                gradient = QLinearGradient(0, margin_top, 0, height - margin_bottom)
                gradient.setColorAt(0, self.fill_color)
                gradient.setColorAt(
                    1, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 10)
                )

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawPath(path)

            # 绘制折线
            painter.setPen(QPen(self.line_color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

            # 绘制数据点
            painter.setPen(QPen(self.line_color, 2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            for point in points:
                painter.drawEllipse(point, 4, 4)

            # 显示最新值
            if len(self.data_points) > 0:
                latest_value = self.data_points[-1]
                value_text = f"当前: {latest_value:.2f}"

                painter.setPen(QPen(self.text_color))
                font.setBold(True)
                font.setPointSize(11)
                painter.setFont(font)

                # 背景框
                text_rect = painter.fontMetrics().boundingRect(value_text)
                text_x = width - margin_right - text_rect.width() - 20
                text_y = margin_top + 10

                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
                painter.setPen(QPen(self.line_color, 2))
                painter.drawRoundedRect(text_x - 5, text_y - 5, text_rect.width() + 10, text_rect.height() + 10, 5, 5)

                painter.setPen(QPen(self.line_color))
                painter.drawText(text_x, text_y + text_rect.height(), value_text)


class RealtimeBarChart(QWidget):
    """实时柱状图"""

    def __init__(
        self,
        title: str = "数据对比",
        max_bars: int = 10,
        y_max: float = 100.0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.title = title
        self.max_bars = max_bars
        self.y_max = y_max

        # 数据存储：{标签: 值}
        self.data: dict[str, float] = {}
        self.bar_colors: dict[str, QColor] = {}

        # 默认颜色
        self.default_colors = [
            QColor(0, 120, 212),
            QColor(46, 204, 113),
            QColor(241, 196, 15),
            QColor(231, 76, 60),
            QColor(155, 89, 182),
            QColor(52, 152, 219),
            QColor(230, 126, 34),
            QColor(26, 188, 156),
        ]

        self.setMinimumSize(400, 300)

        logger.info(f"创建实时柱状图: {title}")

    def set_data(self, label: str, value: float, color: QColor | None = None):
        """设置数据"""
        self.data[label] = value
        if color:
            self.bar_colors[label] = color
        elif label not in self.bar_colors:
            # 分配默认颜色
            color_index = len(self.bar_colors) % len(self.default_colors)
            self.bar_colors[label] = self.default_colors[color_index]

        self.update()

    def clear_data(self):
        """清空数据"""
        self.data.clear()
        self.bar_colors.clear()
        self.update()

    def paintEvent(self, _event):
        """绘制图表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 边距
        margin_left = 60
        margin_right = 20
        margin_top = 50
        margin_bottom = 60

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        # 背景
        painter.fillRect(0, 0, width, height, QColor(255, 255, 255))

        # 标题
        painter.setPen(QPen(QColor(50, 50, 50)))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, width, margin_top, Qt.AlignmentFlag.AlignCenter, self.title)

        # 绘制坐标轴
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        # Y轴
        painter.drawLine(margin_left, margin_top, margin_left, height - margin_bottom)
        # X轴
        painter.drawLine(margin_left, height - margin_bottom, width - margin_right, height - margin_bottom)

        # Y轴刻度
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)

        num_y_ticks = 5
        for i in range(num_y_ticks + 1):
            y_value = self.y_max * i / num_y_ticks
            y_pos = height - margin_bottom - (chart_height * i / num_y_ticks)

            # 网格线
            painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, int(y_pos), width - margin_right, int(y_pos))

            # 标签
            painter.setPen(QPen(QColor(50, 50, 50)))
            painter.drawText(5, int(y_pos - 10), margin_left - 10, 20, Qt.AlignmentFlag.AlignRight, f"{y_value:.0f}")

        # 绘制柱状图
        if self.data:
            num_bars = len(self.data)
            bar_spacing = 10
            bar_width = (chart_width - bar_spacing * (num_bars + 1)) / num_bars

            for i, (label, value) in enumerate(self.data.items()):
                x = margin_left + bar_spacing + i * (bar_width + bar_spacing)
                bar_height = (value / self.y_max) * chart_height if self.y_max > 0 else 0
                y = height - margin_bottom - bar_height

                # 柱子颜色
                color = self.bar_colors.get(label, self.default_colors[0])

                # 渐变填充
                gradient = QLinearGradient(0, y, 0, height - margin_bottom)
                gradient.setColorAt(0, color)
                gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 150))

                painter.setPen(QPen(color.darker(120), 2))
                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 4, 4)

                # 数值标签
                painter.setPen(QPen(QColor(50, 50, 50)))
                font.setBold(True)
                painter.setFont(font)
                value_text = f"{value:.1f}"
                painter.drawText(
                    int(x),
                    int(y - 5),
                    int(bar_width),
                    20,
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                    value_text,
                )

                # X轴标签
                font.setBold(False)
                painter.setFont(font)
                painter.save()
                painter.translate(x + bar_width / 2, height - margin_bottom + 10)
                painter.rotate(-45)
                painter.drawText(0, 0, 100, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
                painter.restore()


class DataMonitorPanel(QFrame):
    """数据监控面板 - 集成多个实时图表"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.charts: dict[str, RealtimeLineChart | RealtimeBarChart] = {}

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
            }
        """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题栏
        title_layout = QHBoxLayout()

        title_label = QLabel("📊 实时数据监控")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
            }
        """
        )
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 控制按钮
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """
        )
        title_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """
        )
        self.clear_btn.clicked.connect(self.clear_all_data)
        title_layout.addWidget(self.clear_btn)

        main_layout.addLayout(title_layout)

        # 图表容器
        self.charts_layout = QVBoxLayout()
        self.charts_layout.setSpacing(10)
        main_layout.addLayout(self.charts_layout)

    def add_line_chart(
        self,
        chart_id: str,
        title: str,
        y_label: str = "数值",
        max_points: int = 50,
        y_min: float = 0.0,
        y_max: float = 100.0,
    ) -> RealtimeLineChart:
        """添加折线图"""
        chart = RealtimeLineChart(title, y_label, max_points, y_min, y_max)
        self.charts[chart_id] = chart
        self.charts_layout.addWidget(chart)

        logger.info(f"添加折线图: {chart_id} - {title}")
        return chart

    def add_bar_chart(self, chart_id: str, title: str, max_bars: int = 10, y_max: float = 100.0) -> RealtimeBarChart:
        """添加柱状图"""
        chart = RealtimeBarChart(title, max_bars, y_max)
        self.charts[chart_id] = chart
        self.charts_layout.addWidget(chart)

        logger.info(f"添加柱状图: {chart_id} - {title}")
        return chart

    def get_chart(self, chart_id: str) -> RealtimeLineChart | RealtimeBarChart | None:
        """获取图表"""
        return self.charts.get(chart_id)

    def clear_all_data(self):
        """清空所有图表数据"""
        for chart in self.charts.values():
            if hasattr(chart, "clear_data"):
                chart.clear_data()

        logger.info("清空所有图表数据")


class GaugeWidget(QWidget):
    """仪表盘组件"""

    def __init__(
        self,
        title: str = "温度",
        min_value: float = 0.0,
        max_value: float = 100.0,
        unit: str = "°C",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self._current_value = min_value

        self.setMinimumSize(200, 200)

    def setValue(self, value: float):
        """设置值"""
        self._current_value = max(self.min_value, min(value, self.max_value))
        self.update()

    def value(self) -> float:
        """获取当前值"""
        return self._current_value

    def paintEvent(self, _event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height)

        # 中心点
        center_x = width / 2
        center_y = height / 2
        radius = size * 0.4

        # 绘制标题
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(50, 50, 50)))
        painter.drawText(0, 10, width, 30, Qt.AlignmentFlag.AlignCenter, self.title)

        # 绘制外圈
        painter.setPen(QPen(QColor(200, 200, 200), 8))
        painter.drawArc(
            int(center_x - radius),
            int(center_y - radius),
            int(radius * 2),
            int(radius * 2),
            30 * 16,  # 起始角度（从右下开始）
            300 * 16,  # 跨度角度
        )

        # 绘制进度圈
        ratio = (
            (self._current_value - self.min_value) / (self.max_value - self.min_value)
            if self.max_value > self.min_value
            else 0
        )

        # 根据值选择颜色
        if ratio < 0.3:
            color = QColor(52, 152, 219)  # 蓝色
        elif ratio < 0.7:
            color = QColor(241, 196, 15)  # 黄色
        else:
            color = QColor(231, 76, 60)  # 红色

        painter.setPen(QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        span_angle = int(300 * ratio * 16)
        painter.drawArc(
            int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2), 30 * 16, span_angle
        )

        # 绘制数值
        font.setPointSize(18)
        painter.setFont(font)
        value_text = f"{self._current_value:.1f}"
        painter.drawText(0, int(center_y - 10), width, 30, Qt.AlignmentFlag.AlignCenter, value_text)

        # 绘制单位
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(0, int(center_y + 20), width, 20, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 绘制范围标签
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(100, 100, 100)))

        # 最小值
        painter.drawText(
            int(center_x - radius - 20),
            int(center_y + radius - 10),
            40,
            20,
            Qt.AlignmentFlag.AlignCenter,
            f"{self.min_value:.0f}",
        )

        # 最大值
        painter.drawText(
            int(center_x + radius - 20),
            int(center_y + radius - 10),
            40,
            20,
            Qt.AlignmentFlag.AlignCenter,
            f"{self.max_value:.0f}",
        )
