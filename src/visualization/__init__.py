"""数据可视化模块

3D分子可视化和高级交互式图表
"""

# 3D分子可视化
try:
    from .molecule_3d import PY3DMOL_AVAILABLE, Molecule3DViewer, quick_view

    __all__ = ["Molecule3DViewer", "quick_view", "PY3DMOL_AVAILABLE"]
except ImportError:
    PY3DMOL_AVAILABLE = False
    __all__ = ["PY3DMOL_AVAILABLE"]

# 高级图表
try:
    from .advanced_charts import (
        PLOTLY_AVAILABLE,
        AdvancedChartCreator,
        demo_charts,
        quick_titration_curve,
    )

    __all__.extend(
        [
            "AdvancedChartCreator",
            "quick_titration_curve",
            "demo_charts",
            "PLOTLY_AVAILABLE",
        ]
    )
except ImportError:
    PLOTLY_AVAILABLE = False
    __all__.append("PLOTLY_AVAILABLE")
