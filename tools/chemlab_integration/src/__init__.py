"""ChemLab 集成工具

本工具用于将 chemlab 开源库的数据集成到 VirtualChemLab 项目中。

许可证: BSD 3-Clause (与 chemlab 保持一致)
"""

__version__ = "1.0.0"
__author__ = "VirtualChemLab Team"
__license__ = "BSD-3-Clause"

from pathlib import Path

# 工具根目录
TOOL_ROOT = Path(__file__).parent.parent
CONFIG_PATH = TOOL_ROOT / "config.yaml"
