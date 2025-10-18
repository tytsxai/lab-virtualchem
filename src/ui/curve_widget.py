"""
曲线绘制组件
使用PyQtGraph绘制实验曲线
"""

try:
    import pyqtgraph as pg
    from pyqtgraph import PlotWidget

    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    PlotWidget = object


import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..core.curve_generator import CurveGenerator
from ..models.experiment import Curve
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CurveWidget(QWidget):
    """曲线绘制组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.curve_generator = CurveGenerator()

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        if not PYQTGRAPH_AVAILABLE:
            # PyQtGraph未安装,显示提示
            warning_label = QLabel("⚠️ PyQtGraph未安装,无法显示曲线\n请运行: pip install pyqtgraph")
            warning_label.setAlignment(Qt.AlignCenter)
            warning_label.setStyleSheet("color: red; font-size: 14px;")
            layout.addWidget(warning_label)
            return

        # 创建绘图区域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        layout.addWidget(self.plot_widget)

    def plot_titration_curve(self, curve: Curve, context: dict):
        """绘制滴定曲线"""
        if not PYQTGRAPH_AVAILABLE:
            logger.warning("PyQtGraph未安装,无法绘制曲线")
            return

        try:
            # 提取参数
            acid_type = curve.params.get("acid_type", "strong")
            acid_M = float(context.get("acid_M", 0.1))
            acid_V_ml = float(context.get("acid_V_ml", 25.0))
            base_M = float(context.get("base_M", 0.1))
            pKa = curve.params.get("pKa")

            # 生成曲线数据
            V_base, pH_values = self.curve_generator.generate_titration_curve(
                acid_type=acid_type, acid_M=acid_M, acid_V_ml=acid_V_ml, base_M=base_M, pKa=pKa
            )

            # 清除旧曲线
            self.plot_widget.clear()

            # 绘制曲线
            pen = pg.mkPen(color=(0, 0, 255), width=2)
            self.plot_widget.plot(V_base, pH_values, pen=pen, name="滴定曲线")

            # 设置标签
            self.plot_widget.setLabel("left", curve.y_label or "pH")
            self.plot_widget.setLabel("bottom", curve.x_label or "加入碱体积 (mL)")
            self.plot_widget.setTitle(curve.title or "滴定曲线")

            # 添加网格
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

            # 设置范围
            self.plot_widget.setXRange(0, np.max(V_base), padding=0.1)
            self.plot_widget.setYRange(0, 14, padding=0)

            # 添加参考线(pH=7)
            inf_line = pg.InfiniteLine(pos=7, angle=0, pen=pg.mkPen(color=(255, 0, 0), style=Qt.DashLine))
            self.plot_widget.addItem(inf_line)

            logger.info(f"成功绘制滴定曲线: {len(V_base)} 个数据点")

        except Exception as e:
            logger.error(f"绘制滴定曲线失败: {e}")

    def plot_temperature_curve(self, curve: Curve, context: dict):
        """绘制温度变化曲线"""
        if not PYQTGRAPH_AVAILABLE:
            logger.warning("PyQtGraph未安装,无法绘制曲线")
            return

        try:
            # 提取参数
            curve_type = curve.params.get("type", "heating")
            T0 = float(context.get("T0", 25.0))
            T_target = float(context.get("T_target", 100.0))
            k = curve.params.get("k", 0.1)
            duration_min = curve.params.get("duration_min", 10.0)

            # 生成曲线数据
            time_points, temp_values = self.curve_generator.generate_temperature_curve(
                curve_type=curve_type, T0=T0, T_target=T_target, k=k, duration_min=duration_min
            )

            # 清除旧曲线
            self.plot_widget.clear()

            # 绘制曲线
            pen = pg.mkPen(color=(255, 100, 0), width=2)
            self.plot_widget.plot(time_points, temp_values, pen=pen, name="温度曲线")

            # 设置标签
            self.plot_widget.setLabel("left", curve.y_label or "温度 (°C)")
            self.plot_widget.setLabel("bottom", curve.x_label or "时间 (min)")
            self.plot_widget.setTitle(curve.title or "温度变化曲线")

            # 添加网格
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

            logger.info(f"成功绘制温度曲线: {len(time_points)} 个数据点")

        except Exception as e:
            logger.error(f"绘制温度曲线失败: {e}")

    def plot_curve_from_data(
        self,
        x_data: list[float],
        y_data: list[float],
        title: str = "",
        x_label: str = "X",
        y_label: str = "Y",
        color: tuple[int, int, int] = (0, 0, 255),
    ):
        """从原始数据绘制曲线"""
        if not PYQTGRAPH_AVAILABLE:
            logger.warning("PyQtGraph未安装,无法绘制曲线")
            return

        try:
            # 清除旧曲线
            self.plot_widget.clear()

            # 绘制曲线
            pen = pg.mkPen(color=color, width=2)
            self.plot_widget.plot(x_data, y_data, pen=pen)

            # 设置标签
            self.plot_widget.setLabel("left", y_label)
            self.plot_widget.setLabel("bottom", x_label)
            if title:
                self.plot_widget.setTitle(title)

            # 添加网格
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

            logger.info(f"成功绘制自定义曲线: {len(x_data)} 个数据点")

        except Exception as e:
            logger.error(f"绘制自定义曲线失败: {e}")

    def clear_plot(self):
        """清除绘图"""
        if PYQTGRAPH_AVAILABLE:
            self.plot_widget.clear()

    def export_plot(self, filepath: str):
        """导出绘图为图片"""
        if not PYQTGRAPH_AVAILABLE:
            logger.warning("PyQtGraph未安装,无法导出曲线")
            return False

        try:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(filepath)
            logger.info(f"成功导出曲线至: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出曲线失败: {e}")
            return False
