"""VirtualChemLab REST API

提供RESTful API接口用于外部系统集成

主要组件:
- APIServer: API服务器实现

注意:
- API路由在server.py中实现
- 数据模型使用src/models中的定义
"""

from .server import APIServer

__all__ = ["APIServer"]
