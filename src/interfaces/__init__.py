"""
接口定义模块 - 定义核心业务接口
遵循依赖倒置原则(DIP)和接口隔离原则(ISP)
"""

from .event import IEventBus, IEventHandler
from .experiment import ICurveGenerator, IExperimentEngine, IExperimentValidator
from .plugin import IPlugin, IPluginLoader
from .report import IReportExporter, IReportGenerator
from .storage import IRepository, IStorage

__all__ = [
    # 存储接口
    "IStorage",
    "IRepository",
    # 实验接口
    "IExperimentEngine",
    "IExperimentValidator",
    "ICurveGenerator",
    # 报告接口
    "IReportGenerator",
    "IReportExporter",
    # 插件接口
    "IPlugin",
    "IPluginLoader",
    # 事件接口
    "IEventBus",
    "IEventHandler",
]
