"""VirtualChemLab REST API

提供RESTful API接口用于外部系统集成

主要组件:
- APIServer: API服务器实现

注意:
- API路由在server.py中实现
- 数据模型使用src/models中的定义
"""

try:
    from .server import APIServer
except Exception:  # pragma: no cover  # noqa: BLE001
    # Some optional dependencies/modules may be absent in certain test sandboxes.
    # Importing `src.api` should not fail hard; consumers can import `src.api.server`
    # explicitly when the full API stack is available.
    APIServer = None  # type: ignore[assignment]

__all__ = ["APIServer"]
