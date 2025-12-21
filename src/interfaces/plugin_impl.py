"""插件实现（兼容模块）。

旧实现曾位于 `src/interfaces/plugin.py`，后为覆盖率统计与结构调整迁移到
`src/interfaces/plugin/core.py`。
"""

from __future__ import annotations

from .plugin.core import *  # noqa: F403

