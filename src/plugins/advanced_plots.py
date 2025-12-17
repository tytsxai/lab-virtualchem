"""
高级图表模块 - PyQtGraph 适配层
用于交互式科学图表绘制
"""

import logging

import numpy as np

from . import registry, require_plugin

logger = logging.getLogger(__name__)


class AdvancedPlotter:
    """高级图表绘制器"""

    def __init__(self):
        self.pyqtgraph = registry.get_module("pyqtgraph")
        self._plot_widget = None

    @require_plugin("pyqtgraph")
    def create_interactive_plot(
        self, parent=None, title: str = "", x_label: str = "X", y_label: str = "Y"
    ):
        """创建交互式图表控件

        Args:
            parent: Qt父控件
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签

        Returns:
            PlotWidget实例
        """
        import pyqtgraph as pg

        plot_widget = pg.PlotWidget(parent=parent)
        plot_widget.setTitle(title)
        plot_widget.setLabel("bottom", x_label)
        plot_widget.setLabel("left", y_label)
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.addLegend()

        return plot_widget

    @require_plugin("pyqtgraph")
    def plot_curve(
        self,
        plot_widget,
        x_data: np.ndarray,
        y_data: np.ndarray,
        name: str = "",
        color: str = "b",
        width: int = 2,
        symbol: str | None = None,
    ):
        """在图表上绘制曲线

        Args:
            plot_widget: PlotWidget实例
            x_data: X轴数据
            y_data: Y轴数据
            name: 曲线名称
            color: 颜色
            width: 线宽
            symbol: 数据点符号 ('o', 's', 't', 'd', '+')
        """
        import pyqtgraph as pg

        pen = pg.mkPen(color=color, width=width)

        if symbol:
            plot_widget.plot(
                x_data,
                y_data,
                name=name,
                pen=pen,
                symbol=symbol,
                symbolSize=8,
                symbolBrush=color,
            )
        else:
            plot_widget.plot(x_data, y_data, name=name, pen=pen)

    @require_plugin("pyqtgraph")
    def create_multi_curve_plot(
        self,
        data_sets: list[tuple[np.ndarray, np.ndarray, str]],
        title: str = "",
        x_label: str = "X",
        y_label: str = "Y",
        parent=None,
    ):
        """创建多条曲线的图表

        Args:
            data_sets: [(x_data, y_data, name), ...]
            title: 标题
            x_label: X轴标签
            y_label: Y轴标签
            parent: 父控件

        Returns:
            PlotWidget实例
        """
        plot_widget = self.create_interactive_plot(
            parent=parent, title=title, x_label=x_label, y_label=y_label
        )

        colors = ["b", "r", "g", "c", "m", "y", "k"]

        for i, (x_data, y_data, name) in enumerate(data_sets):
            color = colors[i % len(colors)]
            self.plot_curve(plot_widget, x_data, y_data, name, color)

        return plot_widget

    @require_plugin("pyqtgraph")
    def create_realtime_plot(self, max_points: int = 100, parent=None):
        """创建实时更新图表

        Args:
            max_points: 最大显示点数
            parent: 父控件

        Returns:
            (PlotWidget, PlotDataItem, data_buffer)
        """
        from collections import deque

        import pyqtgraph as pg

        plot_widget = pg.PlotWidget(parent=parent)
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        curve = plot_widget.plot(pen="y", width=2)

        data_buffer = {"x": deque(maxlen=max_points), "y": deque(maxlen=max_points)}

        return plot_widget, curve, data_buffer

    @require_plugin("pyqtgraph")
    def update_realtime_plot(
        self, curve, data_buffer: dict, x_value: float, y_value: float
    ):
        """更新实时图表数据

        Args:
            curve: PlotDataItem
            data_buffer: 数据缓冲区
            x_value: 新X值
            y_value: 新Y值
        """
        data_buffer["x"].append(x_value)
        data_buffer["y"].append(y_value)

        curve.setData(list(data_buffer["x"]), list(data_buffer["y"]))

    @require_plugin("pyqtgraph")
    def create_heatmap(
        self,
        data: np.ndarray,
        _x_labels: list[str] | None = None,
        _y_labels: list[str] | None = None,
        title: str = "",
        parent=None,
    ):
        """创建热力图

        Args:
            data: 2D数组数据
            x_labels: X轴标签列表
            y_labels: Y轴标签列表
            title: 标题
            parent: 父控件

        Returns:
            ImageView实例
        """
        import pyqtgraph as pg

        img_view = pg.ImageView(parent=parent)
        img_view.setImage(data)

        if title:
            img_view.setWindowTitle(title)

        return img_view


# 回退实现：使用matplotlib基础绘图
def _fallback_create_plot(*_args, **_kwargs):
    """回退：使用matplotlib创建静态图表"""
    logger.warning("PyQtGraph未安装，使用matplotlib基础绘图")

    # 返回None表示使用项目原有的matplotlib绘图
    return None


# 注册插件
registry.register(
    name="pyqtgraph",
    description="交互式科学图表绘制",
    module_name="pyqtgraph",
    license="MIT",
    fallback=_fallback_create_plot,
)


def get_plotter() -> AdvancedPlotter:
    """获取绘图器实例"""
    return AdvancedPlotter()


def is_available() -> bool:
    """检查PyQtGraph是否可用"""
    return registry.is_available("pyqtgraph")
