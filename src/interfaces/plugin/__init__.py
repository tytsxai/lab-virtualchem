"""插件相关接口定义与轻量实现（包入口）。

说明：
- `src/interfaces/plugin.py` 仍然存在，但 Python 的导入规则会优先选择包目录；
- 将实现放入 `src/interfaces/plugin/` 下，确保 `pytest-cov --cov=src/interfaces/plugin`
  能正确统计覆盖率。
"""

from __future__ import annotations

from .core import *  # noqa: F403
