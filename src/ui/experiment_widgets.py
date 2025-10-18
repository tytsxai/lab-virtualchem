"""
实验交互专用UI组件
为实验操作提供丰富的交互控件
"""

from __future__ import annotations

from PySide6.QtCore import (
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class ValueSlider(QWidget):
    """数值滑块 - 带数值显示和单位"""

    value_changed = Signal(float)

    def __init__(
        self,
        label: str = "",
        min_value: float = 0.0,
        max_value: float = 100.0,
        default_value: float = 50.0,
        unit: str = "",
        decimals: int = 1,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.unit = unit
        self.decimals = decimals
        self.min_value = min_value
        self.max_value = max_value

        self.init_ui(label, default_value)

    def init_ui(self, label: str, default_value: float) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标签和数值显示
        top_layout = QHBoxLayout()

        if label:
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; font-size: 11pt;")
            top_layout.addWidget(label_widget)

        top_layout.addStretch()

        # 数值显示
        self.value_label = QLabel(self._format_value(default_value))
        self.value_label.setStyleSheet(
            """
            QLabel {
                background-color: #e8f4f8;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                color: #0078d4;
                min-width: 80px;
            }
        """
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(self.value_label)

        layout.addLayout(top_layout)

        # 滑块
        self.slider = QSlider(Qt.Orientation.Horizontal)
        slider_range = int((self.max_value - self.min_value) * (10**self.decimals))
        self.slider.setMinimum(0)
        self.slider.setMaximum(slider_range)
        self.slider.setValue(int((default_value - self.min_value) * (10**self.decimals)))
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(slider_range // 10)
        self.slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 10px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                border: 2px solid white;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #106ebe, stop:1 #0078d4);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #00a2e8);
                border-radius: 5px;
            }
        """
        )
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        # 最小值和最大值标签
        range_layout = QHBoxLayout()
        min_label = QLabel(self._format_value(self.min_value))
        min_label.setStyleSheet("color: #666; font-size: 9pt;")
        max_label = QLabel(self._format_value(self.max_value))
        max_label.setStyleSheet("color: #666; font-size: 9pt;")
        range_layout.addWidget(min_label)
        range_layout.addStretch()
        range_layout.addWidget(max_label)
        layout.addLayout(range_layout)

    def _format_value(self, value: float) -> str:
        """格式化数值显示"""
        formatted = f"{value:.{self.decimals}f}"
        if self.unit:
            formatted += f" {self.unit}"
        return formatted

    def _on_slider_changed(self, slider_value: int):
        """滑块值改变"""
        actual_value = self.min_value + (slider_value / (10**self.decimals))
        self.value_label.setText(self._format_value(actual_value))
        self.value_changed.emit(actual_value)

    def value(self) -> float:
        """获取当前值"""
        slider_value = self.slider.value()
        return self.min_value + (slider_value / (10**self.decimals))

    def setValue(self, value: float):
        """设置当前值"""
        slider_value = int((value - self.min_value) * (10**self.decimals))
        self.slider.setValue(slider_value)


class NumericInput(QWidget):
    """数值输入器 - 带增减按钮"""

    value_changed = Signal(float)

    def __init__(
        self,
        label: str = "",
        min_value: float = 0.0,
        max_value: float = 100.0,
        default_value: float = 0.0,
        unit: str = "",
        decimals: int = 2,
        step: float = 1.0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.unit = unit

        self.init_ui(label, min_value, max_value, default_value, decimals, step)

    def init_ui(
        self, label: str, min_value: float, max_value: float, default_value: float, decimals: int, step: float
    ) -> None:
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 标签
        if label:
            label_widget = QLabel(label + ":")
            label_widget.setStyleSheet("font-weight: bold; font-size: 11pt;")
            layout.addWidget(label_widget)

        # 减少按钮
        self.decrease_btn = QPushButton("−")
        self.decrease_btn.setFixedSize(32, 32)
        self.decrease_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """
        )
        self.decrease_btn.clicked.connect(self._decrease_value)
        layout.addWidget(self.decrease_btn)

        # 数值输入框
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setMinimum(min_value)
        self.spinbox.setMaximum(max_value)
        self.spinbox.setValue(default_value)
        self.spinbox.setDecimals(decimals)
        self.spinbox.setSingleStep(step)
        self.spinbox.setSuffix(f" {self.unit}" if self.unit else "")
        self.spinbox.setStyleSheet(
            """
            QDoubleSpinBox {
                border: 2px solid #d1d8e0;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12pt;
                font-weight: bold;
                background-color: white;
                min-width: 120px;
            }
            QDoubleSpinBox:focus {
                border-color: #0078d4;
            }
        """
        )
        self.spinbox.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.spinbox)

        # 增加按钮
        self.increase_btn = QPushButton("+")
        self.increase_btn.setFixedSize(32, 32)
        self.increase_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """
        )
        self.increase_btn.clicked.connect(self._increase_value)
        layout.addWidget(self.increase_btn)

    def _decrease_value(self):
        """减少数值"""
        self.spinbox.stepDown()

    def _increase_value(self):
        """增加数值"""
        self.spinbox.stepUp()

    def _on_value_changed(self, value: float):
        """数值改变"""
        self.value_changed.emit(value)

    def value(self) -> float:
        """获取当前值"""
        return self.spinbox.value()

    def setValue(self, value: float):
        """设置当前值"""
        self.spinbox.setValue(value)


class ColorPicker(QWidget):
    """颜色选择器"""

    color_changed = Signal(QColor)

    def __init__(self, label: str = "颜色", default_color: QColor | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_color = default_color or QColor(255, 255, 255)

        self.init_ui(label)

    def init_ui(self, label: str) -> None:
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 标签
        if label:
            label_widget = QLabel(label + ":")
            label_widget.setStyleSheet("font-weight: bold; font-size: 11pt;")
            layout.addWidget(label_widget)

        # 颜色显示框
        self.color_display = QFrame()
        self.color_display.setFixedSize(80, 36)
        self.color_display.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.current_color.name()};
                border: 2px solid #d1d8e0;
                border-radius: 6px;
            }}
        """
        )
        layout.addWidget(self.color_display)

        # 颜色代码标签
        self.color_label = QLabel(self.current_color.name().upper())
        self.color_label.setStyleSheet(
            """
            QLabel {
                font-family: monospace;
                font-size: 10pt;
                color: #666;
                padding: 6px;
            }
        """
        )
        layout.addWidget(self.color_label)

        # 选择按钮
        self.pick_btn = QPushButton("选择颜色")
        self.pick_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
        )
        self.pick_btn.clicked.connect(self._pick_color)
        layout.addWidget(self.pick_btn)

        layout.addStretch()

    def _pick_color(self):
        """打开颜色选择对话框"""
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.set_color(color)
            self.color_changed.emit(color)

    def set_color(self, color: QColor):
        """设置颜色"""
        self.current_color = color
        self.color_display.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color.name()};
                border: 2px solid #d1d8e0;
                border-radius: 6px;
            }}
        """
        )
        self.color_label.setText(color.name().upper())

    def color(self) -> QColor:
        """获取当前颜色"""
        return self.current_color


class TemperatureGauge(QWidget):
    """温度计组件"""

    def __init__(self, min_temp: float = 0.0, max_temp: float = 100.0, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_temp = min_temp
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._target_temp = min_temp

        self.setMinimumSize(80, 300)
        self.setMaximumWidth(100)

        # 动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate_temp)

    def setTemperature(self, temp: float) -> None:
        """设置温度（带动画）"""
        self._target_temp = max(self._min_temp, min(temp, self._max_temp))
        if not self.animation_timer.isActive():
            self.animation_timer.start(50)  # 50ms更新一次

    def _animate_temp(self) -> None:
        """温度动画"""
        diff = self._target_temp - self._current_temp
        if abs(diff) < 0.1:
            self._current_temp = self._target_temp
            self.animation_timer.stop()
        else:
            self._current_temp += diff * 0.1

        self.update()

    def paintEvent(self, event: QPaintEvent):
        """绘制温度计"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 绘制温度计外壳
        bulb_radius = 15
        tube_width = 20
        tube_x = (width - tube_width) / 2
        tube_y = 30
        tube_height = height - 60 - bulb_radius

        # 外壳
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))

        # 绘制管子
        painter.drawRoundedRect(int(tube_x), tube_y, tube_width, int(tube_height), 10, 10)

        # 绘制球部
        bulb_center_y = tube_y + tube_height + bulb_radius
        painter.drawEllipse(
            int(width / 2 - bulb_radius), int(bulb_center_y - bulb_radius), bulb_radius * 2, bulb_radius * 2
        )

        # 绘制水银柱
        temp_ratio = (self._current_temp - self._min_temp) / (self._max_temp - self._min_temp)
        mercury_height = tube_height * temp_ratio

        # 渐变色（从蓝到红）
        gradient = QLinearGradient(0, tube_y + tube_height, 0, tube_y)
        if temp_ratio < 0.3:
            gradient.setColorAt(0, QColor(52, 152, 219))  # 蓝色
            gradient.setColorAt(1, QColor(41, 128, 185))
        elif temp_ratio < 0.7:
            gradient.setColorAt(0, QColor(241, 196, 15))  # 黄色
            gradient.setColorAt(1, QColor(243, 156, 18))
        else:
            gradient.setColorAt(0, QColor(231, 76, 60))  # 红色
            gradient.setColorAt(1, QColor(192, 57, 43))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))

        # 绘制水银柱
        mercury_y = tube_y + tube_height - mercury_height
        painter.drawRoundedRect(int(tube_x + 2), int(mercury_y), tube_width - 4, int(mercury_height), 8, 8)

        # 绘制球部的水银
        if temp_ratio < 0.3:
            bulb_color = QColor(52, 152, 219)
        elif temp_ratio < 0.7:
            bulb_color = QColor(241, 196, 15)
        else:
            bulb_color = QColor(231, 76, 60)

        painter.setBrush(QBrush(bulb_color))
        painter.drawEllipse(
            int(width / 2 - bulb_radius + 2),
            int(bulb_center_y - bulb_radius + 2),
            (bulb_radius - 2) * 2,
            (bulb_radius - 2) * 2,
        )

        # 绘制刻度
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        num_ticks = 10
        for i in range(num_ticks + 1):
            tick_y = tube_y + (tube_height / num_ticks) * i
            tick_temp = self._max_temp - (self._max_temp - self._min_temp) * i / num_ticks

            # 刻度线
            painter.drawLine(int(tube_x + tube_width + 2), int(tick_y), int(tube_x + tube_width + 8), int(tick_y))

            # 温度标签
            if i % 2 == 0:
                painter.drawText(
                    int(tube_x + tube_width + 12),
                    int(tick_y - 8),
                    30,
                    16,
                    Qt.AlignmentFlag.AlignLeft,
                    f"{tick_temp:.0f}°",
                )

        # 绘制当前温度值
        painter.setPen(QPen(QColor(0, 0, 0)))
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        temp_text = f"{self._current_temp:.1f}°C"
        painter.drawText(0, 0, width, 25, Qt.AlignmentFlag.AlignCenter, temp_text)


class PHIndicator(QWidget):
    """pH指示器"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._ph_value = 7.0
        self.setMinimumSize(400, 80)

    def setPH(self, ph: float) -> None:
        """设置pH值"""
        self._ph_value = max(0.0, min(ph, 14.0))
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """绘制pH指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # pH颜色映射（0-14）
        ph_colors = [
            (0, QColor(139, 0, 0)),  # 深红色（强酸）
            (2, QColor(255, 0, 0)),  # 红色
            (4, QColor(255, 165, 0)),  # 橙色
            (6, QColor(255, 255, 0)),  # 黄色
            (7, QColor(0, 255, 0)),  # 绿色（中性）
            (8, QColor(0, 255, 255)),  # 青色
            (10, QColor(0, 0, 255)),  # 蓝色
            (12, QColor(75, 0, 130)),  # 靛蓝
            (14, QColor(139, 0, 139)),  # 紫色（强碱）
        ]

        # 绘制pH条
        bar_height = 40
        bar_y = (height - bar_height) / 2
        segment_width = width / 14

        for i in range(14):
            # 插值颜色
            color = self._interpolate_color(i, ph_colors)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(i * segment_width), int(bar_y), int(segment_width), bar_height)

        # 绘制刻度
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        for i in range(15):
            x = i * segment_width
            painter.drawLine(int(x), int(bar_y), int(x), int(bar_y + bar_height))

            # 标签
            if i % 2 == 0:
                painter.drawText(int(x - 10), int(bar_y + bar_height + 5), 20, 20, Qt.AlignmentFlag.AlignCenter, str(i))

        # 绘制当前pH指示器
        indicator_x = self._ph_value * segment_width
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.setBrush(QBrush(QColor(255, 255, 255)))

        # 三角形指示器
        points = [
            (int(indicator_x), int(bar_y - 10)),
            (int(indicator_x - 8), int(bar_y - 2)),
            (int(indicator_x + 8), int(bar_y - 2)),
        ]
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QPolygon

        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.drawPolygon(polygon)

        # pH值文本
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        ph_text = f"pH: {self._ph_value:.1f}"
        painter.drawText(int(indicator_x - 30), int(bar_y - 25), 60, 20, Qt.AlignmentFlag.AlignCenter, ph_text)

    def _interpolate_color(self, ph: float, color_map: list[tuple[float, QColor]]) -> QColor:
        """插值颜色"""
        for i in range(len(color_map) - 1):
            ph1, color1 = color_map[i]
            ph2, color2 = color_map[i + 1]

            if ph1 <= ph <= ph2:
                ratio = (ph - ph1) / (ph2 - ph1)
                r = int(color1.red() + (color2.red() - color1.red()) * ratio)
                g = int(color1.green() + (color2.green() - color1.green()) * ratio)
                b = int(color1.blue() + (color2.blue() - color1.blue()) * ratio)
                return QColor(r, g, b)

        return color_map[-1][1]


class ReactionProgressBar(QWidget):
    """反应进度条 - 带动画效果"""

    def __init__(self, label: str = "反应进度", parent: QWidget | None = None):
        super().__init__(parent)
        self._progress = 0.0
        self._label = label

        self.setMinimumHeight(80)

    def setProgress(self, progress: float) -> None:
        """设置进度（0-100）"""
        self._progress = max(0.0, min(progress, 100.0))
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """绘制进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()

        # 标签
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawText(0, 0, width, 25, Qt.AlignmentFlag.AlignLeft, self._label)

        # 进度条背景
        bar_y = 30
        bar_height = 30
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRoundedRect(0, bar_y, width, bar_height, 15, 15)

        # 进度条前景
        if self._progress > 0:
            progress_width = int(width * self._progress / 100)

            # 渐变色
            gradient = QLinearGradient(0, 0, progress_width, 0)
            if self._progress < 30:
                gradient.setColorAt(0, QColor(231, 76, 60))
                gradient.setColorAt(1, QColor(192, 57, 43))
            elif self._progress < 70:
                gradient.setColorAt(0, QColor(241, 196, 15))
                gradient.setColorAt(1, QColor(243, 156, 18))
            else:
                gradient.setColorAt(0, QColor(46, 204, 113))
                gradient.setColorAt(1, QColor(39, 174, 96))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(2, bar_y + 2, progress_width - 4, bar_height - 4, 13, 13)

        # 进度文本
        painter.setPen(QPen(QColor(0, 0, 0)))
        font.setPointSize(10)
        painter.setFont(font)
        progress_text = f"{self._progress:.1f}%"
        painter.drawText(0, bar_y + bar_height + 5, width, 20, Qt.AlignmentFlag.AlignCenter, progress_text)


class Timer(QWidget):
    """计时器组件"""

    time_updated = Signal(int)  # 秒数

    def __init__(self, label: str = "计时", parent: QWidget | None = None):
        super().__init__(parent)
        self._elapsed_seconds = 0
        self._is_running = False
        self._label = label

        self.init_ui()

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 标签
        label_widget = QLabel(self._label)
        label_widget.setStyleSheet("font-weight: bold; font-size: 11pt;")
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_widget)

        # 时间显示
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet(
            """
            QLabel {
                background-color: #2c3e50;
                color: #0f0;
                font-family: 'Courier New', monospace;
                font-size: 24pt;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #34495e;
            }
        """
        )
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始")
        self.start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """
        )
        self.start_btn.clicked.connect(self.start)
        btn_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e67e22; }
        """
        )
        self.pause_btn.clicked.connect(self.pause)
        self.pause_btn.setEnabled(False)
        btn_layout.addWidget(self.pause_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """
        )
        self.reset_btn.clicked.connect(self.reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)

    def start(self) -> None:
        """开始计时"""
        if not self._is_running:
            self._is_running = True
            self.timer.start(1000)  # 每秒更新
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)

    def pause(self) -> None:
        """暂停计时"""
        if self._is_running:
            self._is_running = False
            self.timer.stop()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)

    def reset(self) -> None:
        """重置计时"""
        self._is_running = False
        self.timer.stop()
        self._elapsed_seconds = 0
        self._update_display()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)

    def _update_time(self) -> None:
        """更新时间"""
        self._elapsed_seconds += 1
        self._update_display()
        self.time_updated.emit(self._elapsed_seconds)

    def _update_display(self) -> None:
        """更新显示"""
        hours = self._elapsed_seconds // 3600
        minutes = (self._elapsed_seconds % 3600) // 60
        seconds = self._elapsed_seconds % 60
        self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def elapsed_seconds(self) -> int:
        """获取已用时间（秒）"""
        return self._elapsed_seconds
