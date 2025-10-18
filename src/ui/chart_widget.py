"""
图表组件
用于显示实验数据曲线和图表
支持触摸操作和响应式布局
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from matplotlib.figure import Figure

try:
    import matplotlib

    matplotlib.use("Qt5Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  # noqa: F401
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib未安装，图表功能不可用")

logger = logging.getLogger(__name__)

from .responsive import ResponsiveHelper, TouchHelper  # noqa: E402


class ChartWidget(QWidget):
    """图表组件（支持触摸操作）"""

    # 信号
    chart_tapped = Signal(QPoint)  # 图表点击
    chart_zoomed = Signal(float)  # 图表缩放

    def __init__(self, parent=None):
        super().__init__(parent)

        # 触摸相关
        self.is_touch_enabled = TouchHelper.is_touch_enabled()
        self.last_touch_pos = None
        self.pinch_start_distance = 0

        # 启用触摸事件
        if self.is_touch_enabled:
            self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        # 设置焦点策略以支持键盘操作
        self.setFocusPolicy(Qt.StrongFocus)

        # 无障碍支持
        self.setAccessibleName("图表组件")
        self.setAccessibleDescription("实验数据可视化图表，支持缩放和保存")

        if not MATPLOTLIB_AVAILABLE:
            self.init_fallback_ui()
        else:
            self.init_ui()

    def init_fallback_ui(self):
        """备用UI（matplotlib未安装时）"""
        layout = QVBoxLayout(self)

        label = QLabel("图表功能需要安装matplotlib库\n请运行: pip install matplotlib")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(label)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建matplotlib图表
        dpi = ResponsiveHelper.get_screen_info()["dpi"]
        self.figure = Figure(figsize=(8, 6), dpi=int(dpi))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        # 触摸友好的按钮大小
        btn_height = TouchHelper.get_touch_target_size() if self.is_touch_enabled else 32

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setMinimumHeight(btn_height)
        self.clear_btn.clicked.connect(self.clear_chart)
        toolbar_layout.addWidget(self.clear_btn)

        self.save_btn = QPushButton("保存图片")
        self.save_btn.setMinimumHeight(btn_height)
        self.save_btn.clicked.connect(self.save_chart)
        self.save_btn.setShortcut("Ctrl+S")  # 键盘快捷键
        self.save_btn.setToolTip("保存图表 (Ctrl+S)")
        toolbar_layout.addWidget(self.save_btn)

        # 添加缩放按钮（触摸设备）
        if self.is_touch_enabled:
            self.zoom_in_btn = QPushButton("🔍+")
            self.zoom_in_btn.setMinimumHeight(btn_height)
            self.zoom_in_btn.clicked.connect(lambda: self.zoom(1.2))
            toolbar_layout.addWidget(self.zoom_in_btn)

            self.zoom_out_btn = QPushButton("🔍-")
            self.zoom_out_btn.setMinimumHeight(btn_height)
            self.zoom_out_btn.clicked.connect(lambda: self.zoom(0.8))
            toolbar_layout.addWidget(self.zoom_out_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # 初始化空图表
        self.ax = None
        self.clear_chart()

    def keyPressEvent(self, event):
        """键盘事件处理 - 增强可访问性"""
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            # + 或 = 键放大
            self.zoom(1.2)
        elif event.key() == Qt.Key_Minus:
            # - 键缩小
            self.zoom(0.8)
        elif event.key() == Qt.Key_0:
            # 0 键重置
            if self.ax:
                self.ax.autoscale()
                self.canvas.draw()
        elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            # Ctrl+S 保存
            self.save_chart()
        else:
            super().keyPressEvent(event)

    def zoom(self, factor: float):
        """缩放图表"""
        if self.ax:
            # 获取当前坐标范围
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

            # 计算中心点
            x_center = (xlim[0] + xlim[1]) / 2
            y_center = (ylim[0] + ylim[1]) / 2

            # 计算新范围
            x_range = (xlim[1] - xlim[0]) / factor
            y_range = (ylim[1] - ylim[0]) / factor

            # 应用新范围
            self.ax.set_xlim(x_center - x_range / 2, x_center + x_range / 2)
            self.ax.set_ylim(y_center - y_range / 2, y_center + y_range / 2)

            self.canvas.draw()
            self.chart_zoomed.emit(factor)

    def plot_line_chart(
        self,
        x_data: list[float],
        y_data: list[float],
        title: str = "实验曲线",
        xlabel: str = "X轴",
        ylabel: str = "Y轴",
        label: str = "数据",
    ):
        """绘制折线图（带错误处理）"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib未安装，无法绘制图表")
            return

        try:
            # 验证数据
            if not x_data or not y_data:
                logger.warning("数据为空，无法绘制图表")
                return

            if len(x_data) != len(y_data):
                logger.error(f"数据长度不匹配: x={len(x_data)}, y={len(y_data)}")
                return

            self.figure.clear()
            self.ax = self.figure.add_subplot(111)

            self.ax.plot(x_data, y_data, "b-", marker="o", label=label, linewidth=2)
            self.ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
            self.ax.set_xlabel(xlabel, fontsize=12)
            self.ax.set_ylabel(ylabel, fontsize=12)
            self.ax.grid(True, alpha=0.3)
            self.ax.legend()

            self.figure.tight_layout()
            self.canvas.draw()

            # 更新无障碍描述
            self.setAccessibleDescription(f"{title}，包含{len(x_data)}个数据点")

        except Exception as e:
            logger.error(f"绘制折线图失败: {e}", exc_info=True)
            self.clear_chart()

    def plot_multi_line_chart(
        self,
        data_sets: list[dict[str, Any]],
        title: str = "实验曲线对比",
        xlabel: str = "X轴",
        ylabel: str = "Y轴",
    ):
        """
        绘制多条折线图

        Args:
            data_sets: 数据集列表，每个元素包含:
                - x: x数据
                - y: y数据
                - label: 标签
                - color: 颜色（可选）
        """
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        for data in data_sets:
            x_data = data.get("x", [])
            y_data = data.get("y", [])
            label = data.get("label", "数据")
            color = data.get("color", None)

            if color:
                self.ax.plot(x_data, y_data, marker="o", label=label, linewidth=2, color=color)
            else:
                self.ax.plot(x_data, y_data, marker="o", label=label, linewidth=2)

        self.ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
        self.ax.set_xlabel(xlabel, fontsize=12)
        self.ax.set_ylabel(ylabel, fontsize=12)
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_bar_chart(
        self,
        categories: list[str],
        values: list[float],
        title: str = "柱状图",
        xlabel: str = "类别",
        ylabel: str = "数值",
    ):
        """绘制柱状图"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        bars = self.ax.bar(categories, values, color="steelblue", alpha=0.7)

        # 在柱子上显示数值
        for bar in bars:
            height = bar.get_height()
            self.ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
            )

        self.ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
        self.ax.set_xlabel(xlabel, fontsize=12)
        self.ax.set_ylabel(ylabel, fontsize=12)
        self.ax.grid(True, alpha=0.3, axis="y")

        # 旋转x轴标签以避免重叠
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_scatter_chart(
        self,
        x_data: list[float],
        y_data: list[float],
        title: str = "散点图",
        xlabel: str = "X轴",
        ylabel: str = "Y轴",
        sizes: list[float] | None = None,
        colors: list[str] | None = None,
    ):
        """绘制散点图"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        scatter_args = {"alpha": 0.6}
        if sizes:
            scatter_args["s"] = sizes
        if colors:
            scatter_args["c"] = colors

        self.ax.scatter(x_data, y_data, **scatter_args)
        self.ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
        self.ax.set_xlabel(xlabel, fontsize=12)
        self.ax.set_ylabel(ylabel, fontsize=12)
        self.ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_pie_chart(self, labels: list[str], values: list[float], title: str = "饼图"):
        """绘制饼图"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        self.ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        self.ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_titration_curve(
        self, volumes: list[float], ph_values: list[float], equivalence_point: float | None = None
    ):
        """绘制滴定曲线"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        self.ax.plot(volumes, ph_values, "b-", linewidth=2, label="pH曲线")

        # 标记等当点
        if equivalence_point is not None:
            self.ax.axvline(
                x=equivalence_point,
                color="r",
                linestyle="--",
                linewidth=1,
                label=f"等当点 ({equivalence_point:.2f} mL)",
            )

        self.ax.set_title("酸碱滴定曲线", fontsize=14, fontweight="bold", pad=10)
        self.ax.set_xlabel("滴定液体积 (mL)", fontsize=12)
        self.ax.set_ylabel("pH", fontsize=12)
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()

        # pH范围通常是0-14
        self.ax.set_ylim(0, 14)

        self.figure.tight_layout()
        self.canvas.draw()

    def clear_chart(self):
        """清空图表"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.text(
            0.5,
            0.5,
            "暂无数据",
            ha="center",
            va="center",
            transform=self.ax.transAxes,
            fontsize=16,
            color="gray",
        )
        self.ax.axis("off")
        self.canvas.draw()

    def save_chart(self):
        """保存图表为图片（带错误处理）"""
        if not MATPLOTLIB_AVAILABLE:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "功能不可用",
                "matplotlib未安装，无法保存图表。\n请运行: pip install matplotlib",
            )
            return

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "保存图表",
                "chart.png",
                "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)",
            )

            if filename:
                try:
                    self.figure.savefig(filename, dpi=300, bbox_inches="tight")
                    logger.info(f"图表已保存: {filename}")
                    QMessageBox.information(self, "保存成功", f"图表已保存到:\n{filename}")
                except Exception as e:
                    logger.error(f"保存图表失败: {e}", exc_info=True)
                    QMessageBox.critical(self, "保存失败", f"保存图表时发生错误:\n{e}")
        except Exception as e:
            logger.error(f"打开保存对话框失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法打开保存对话框:\n{e}")


class TitrationCurveWidget(ChartWidget):
    """滴定曲线专用组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def update_curve(self, volume: float, ph: float):
        """实时更新滴定曲线"""
        if not MATPLOTLIB_AVAILABLE:
            return

        if not hasattr(self, "volumes"):
            self.volumes = []
            self.ph_values = []

        self.volumes.append(volume)
        self.ph_values.append(ph)

        self.plot_titration_curve(self.volumes, self.ph_values)

    def reset(self):
        """重置曲线"""
        self.volumes = []
        self.ph_values = []
        self.clear_chart()
