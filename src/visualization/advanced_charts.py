"""高级数据可视化模块

使用Plotly实现交互式化学数据可视化:
- 3D数据图表
- 交互式实验曲线
- 动画化学过程
- 实时数据流
- 科研级图表导出
"""

import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import plotly.express as px  # noqa: F401
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots  # noqa: F401

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly未安装，高级可视化功能不可用")


class AdvancedChartCreator:
    """高级图表创建器"""

    # 化学主题颜色
    CHEM_COLORS = {
        "acid": "#FF6B6B",  # 酸性-红色
        "base": "#4ECDC4",  # 碱性-青色
        "neutral": "#95E1D3",  # 中性-绿色
        "primary": "#1A535C",  # 主色
        "secondary": "#FFE66D",  # 次色
    }

    def __init__(self):
        """初始化图表创建器"""
        if not PLOTLY_AVAILABLE:
            raise ImportError("Plotly未安装，请运行: pip install plotly kaleido")

    def create_titration_curve(
        self,
        volumes: list[float],
        ph_values: list[float],
        title: str = "酸碱滴定曲线",
        save_path: Path | None = None,
    ) -> go.Figure:
        """创建滴定曲线

        Args:
            volumes: 滴定体积列表
            ph_values: pH值列表
            title: 图表标题
            save_path: 保存路径

        Returns:
            Plotly图表对象
        """
        fig = go.Figure()

        # 添加滴定曲线
        fig.add_trace(
            go.Scatter(
                x=volumes,
                y=ph_values,
                mode="lines+markers",
                name="滴定曲线",
                line={"color": self.CHEM_COLORS["primary"], "width": 3},
                marker={"size": 8, "color": self.CHEM_COLORS["secondary"]},
            )
        )

        # 添加等当点线 (pH=7)
        if ph_values:
            fig.add_hline(
                y=7,
                line_dash="dash",
                line_color=self.CHEM_COLORS["neutral"],
                annotation_text="等当点 (pH=7)",
            )

        # 样式设置
        fig.update_layout(
            title={"text": title, "font": {"size": 20}},
            xaxis_title="滴定体积 (mL)",
            yaxis_title="pH值",
            hovermode="x unified",
            template="plotly_white",
            height=600,
            font={"family": "Microsoft YaHei, Arial", "size": 14},
        )

        # 保存
        if save_path:
            fig.write_html(str(save_path))
            logger.info(f"滴定曲线已保存: {save_path}")

        return fig

    def create_3d_molecular_surface(
        self,
        x: np.ndarray,
        y: np.ndarray,
        _z: np.ndarray,
        values: np.ndarray,
        title: str = "分子势能面",
    ) -> go.Figure:
        """创建3D分子势能面

        Args:
            x, y, z: 3D坐标网格
            values: 势能值
            title: 图表标题

        Returns:
            Plotly 3D图表
        """
        fig = go.Figure(
            data=[
                go.Surface(
                    x=x,
                    y=y,
                    z=values,
                    colorscale="Viridis",
                    contours={
                        "z": {
                            "show": True,
                            "usecolormap": True,
                            "highlightcolor": "limegreen",
                            "project": {"z": True},
                        }
                    },
                )
            ]
        )

        fig.update_layout(
            title=title,
            scene={
                "xaxis_title": "X坐标 (Å)",
                "yaxis_title": "Y坐标 (Å)",
                "zaxis_title": "能量 (kJ/mol)",
            },
            height=700,
            template="plotly_dark",
        )

        return fig

    def create_reaction_animation(
        self,
        time_points: list[float],
        concentrations: dict[str, list[float]],
        title: str = "反应动力学",
    ) -> go.Figure:
        """创建反应动画

        Args:
            time_points: 时间点列表
            concentrations: 物质浓度字典 {物质名: [浓度列表]}
            title: 图表标题

        Returns:
            带动画的Plotly图表
        """
        fig = go.Figure()

        # 为每个物质添加轨迹
        for substance, conc in concentrations.items():
            fig.add_trace(
                go.Scatter(
                    x=time_points,
                    y=conc,
                    mode="lines+markers",
                    name=substance,
                    line={"width": 3},
                )
            )

        # 添加动画帧
        frames = []
        for i in range(len(time_points)):
            frame_data = []
            for _substance, conc in concentrations.items():
                frame_data.append(
                    go.Scatter(
                        x=time_points[: i + 1], y=conc[: i + 1], mode="lines+markers"
                    )
                )
            frames.append(go.Frame(data=frame_data, name=str(i)))

        fig.frames = frames

        # 添加播放按钮
        fig.update_layout(
            updatemenus=[
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "label": "▶ 播放",
                            "method": "animate",
                            "args": [
                                None,
                                {
                                    "frame": {"duration": 100, "redraw": True},
                                    "fromcurrent": True,
                                },
                            ],
                        },
                        {
                            "label": "⏸ 暂停",
                            "method": "animate",
                            "args": [
                                [None],
                                {
                                    "frame": {"duration": 0, "redraw": False},
                                    "mode": "immediate",
                                    "transition": {"duration": 0},
                                },
                            ],
                        },
                    ],
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "x": 0.1,
                    "xanchor": "left",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
            title=title,
            xaxis_title="时间 (s)",
            yaxis_title="浓度 (M)",
            template="plotly_white",
            height=600,
        )

        return fig

    def create_periodic_table_heatmap(
        self, element_data: dict[str, float], property_name: str = "属性值"
    ) -> go.Figure:
        """创建元素周期表热图

        Args:
            element_data: 元素数据 {元素符号: 值}
            property_name: 属性名称

        Returns:
            Plotly热图
        """
        # 简化的元素周期表位置 (部分主族元素)
        elements_pos = {
            "H": (1, 1),
            "He": (1, 18),
            "Li": (2, 1),
            "Be": (2, 2),
            "B": (2, 13),
            "C": (2, 14),
            "N": (2, 15),
            "O": (2, 16),
            "F": (2, 17),
            "Ne": (2, 18),
            "Na": (3, 1),
            "Mg": (3, 2),
            "Al": (3, 13),
            "Si": (3, 14),
            "P": (3, 15),
            "S": (3, 16),
            "Cl": (3, 17),
            "Ar": (3, 18),
        }

        # 创建网格
        grid = np.zeros((7, 18))
        text_grid = [["" for _ in range(18)] for _ in range(7)]

        for element, value in element_data.items():
            if element in elements_pos:
                row, col = elements_pos[element]
                grid[row - 1][col - 1] = value
                text_grid[row - 1][col - 1] = f"{element}<br>{value:.2f}"

        fig = go.Figure(
            data=go.Heatmap(
                z=grid,
                text=text_grid,
                texttemplate="%{text}",
                colorscale="RdYlBu_r",
                showscale=True,
            )
        )

        fig.update_layout(
            title=f"元素周期表 - {property_name}",
            xaxis_title="族",
            yaxis_title="周期",
            height=500,
            template="plotly_white",
        )

        return fig

    def create_realtime_chart(
        self, max_points: int = 100
    ) -> tuple[go.Figure, callable]:
        """创建实时数据图表

        Args:
            max_points: 最大数据点数

        Returns:
            (图表对象, 更新函数)
        """
        fig = go.Figure()

        # 初始化空数据
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                mode="lines",
                name="实时数据",
                line={"color": self.CHEM_COLORS["primary"], "width": 2},
            )
        )

        fig.update_layout(
            title="实时数据监控",
            xaxis_title="时间",
            yaxis_title="数值",
            template="plotly_white",
            height=500,
        )

        # 数据缓存
        data_cache = {"x": [], "y": []}

        def update_data(new_x: float, new_y: float):
            """更新数据点"""
            data_cache["x"].append(new_x)
            data_cache["y"].append(new_y)

            # 限制数据点数量
            if len(data_cache["x"]) > max_points:
                data_cache["x"] = data_cache["x"][-max_points:]
                data_cache["y"] = data_cache["y"][-max_points:]

            # 更新图表
            fig.data[0].x = data_cache["x"]
            fig.data[0].y = data_cache["y"]

        return fig, update_data

    def create_comparison_chart(
        self, experiments: list[dict[str, Any]], metric: str = "结果"
    ) -> go.Figure:
        """创建实验对比图

        Args:
            experiments: 实验数据列表
            metric: 对比指标

        Returns:
            Plotly柱状图
        """
        names = [exp.get("name", f"实验{i}") for i, exp in enumerate(experiments)]
        values = [exp.get(metric, 0) for exp in experiments]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=names,
                    y=values,
                    marker_color=self.CHEM_COLORS["primary"],
                    text=values,
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title=f"实验对比 - {metric}",
            xaxis_title="实验名称",
            yaxis_title=metric,
            template="plotly_white",
            height=500,
        )

        return fig

    def export_publication_quality(
        self,
        fig: go.Figure,
        output_path: Path,
        format: str = "png",
        width: int = 1200,
        height: int = 800,
        scale: float = 3.0,
    ):
        """导出出版级质量图表

        Args:
            fig: Plotly图表对象
            output_path: 输出路径
            format: 格式 (png/pdf/svg)
            width: 宽度
            height: 高度
            scale: 缩放比例 (提高分辨率)
        """
        try:
            if format == "html":
                fig.write_html(str(output_path))
            else:
                fig.write_image(
                    str(output_path),
                    format=format,
                    width=width,
                    height=height,
                    scale=scale,
                )

            logger.info(f"图表已导出: {output_path}")

        except Exception as e:
            logger.error(f"导出图表失败: {e}")
            logger.info("提示: 导出静态图像需要安装 kaleido")


# 便捷函数
def quick_titration_curve(volumes: list[float], ph_values: list[float]) -> go.Figure:
    """快速创建滴定曲线"""
    creator = AdvancedChartCreator()
    return creator.create_titration_curve(volumes, ph_values)


def demo_charts():
    """演示各种图表"""
    creator = AdvancedChartCreator()

    # 1. 滴定曲线
    volumes = np.linspace(0, 50, 100)
    ph_values = 3 + 10 / (1 + np.exp(-0.5 * (volumes - 25)))

    creator.create_titration_curve(
        volumes.tolist(), ph_values.tolist(), save_path=Path("demo_titration.html")
    )

    # 2. 反应动画
    time = np.linspace(0, 10, 50)
    concentrations = {
        "反应物A": (1 - np.exp(-0.5 * time)).tolist(),
        "反应物B": (1 - np.exp(-0.5 * time)).tolist(),
        "产物C": (1.5 * (1 - np.exp(-0.5 * time))).tolist(),
    }

    fig2 = creator.create_reaction_animation(time.tolist(), concentrations)
    fig2.write_html("demo_reaction_animation.html")

    # 3. 周期表热图
    element_data = {
        "H": 1.008,
        "He": 4.003,
        "Li": 6.941,
        "Be": 9.012,
        "B": 10.811,
        "C": 12.011,
        "N": 14.007,
        "O": 15.999,
        "F": 18.998,
        "Ne": 20.180,
    }

    fig3 = creator.create_periodic_table_heatmap(element_data, "原子质量")
    fig3.write_html("demo_periodic_table.html")

    logger.info("✅ 演示图表已生成:")
    logger.info("  - demo_titration.html")
    logger.info("  - demo_reaction_animation.html")
    logger.info("  - demo_periodic_table.html")


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    if not PLOTLY_AVAILABLE:
        logger.info("❌ Plotly未安装")
        logger.info("请运行: pip install plotly kaleido")
        sys.exit(1)

    logger.info("✅ Plotly可用\n")

    # 生成演示图表
    logger.info("生成演示图表...")
    demo_charts()
