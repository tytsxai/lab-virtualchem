"""
插件系统 - 可选依赖管理
优化版：支持依赖冲突检测、健康检查、性能监控
"""

import importlib
import logging
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """插件状态"""

    AVAILABLE = "available"  # 已安装且可用
    NOT_INSTALLED = "not_installed"  # 未安装
    ERROR = "error"  # 加载错误
    DISABLED = "disabled"  # 已禁用


@dataclass
class PluginInfo:
    """插件信息"""

    name: str
    description: str
    module_name: str
    license: str
    status: PluginStatus
    version: str | None = None
    error_msg: str | None = None
    load_time: datetime | None = None
    dependencies: list[str] = field(default_factory=list)
    conflicts_with: list[str] = field(default_factory=list)


class PluginRegistry:
    """插件注册表 - 优化版"""

    def __init__(self):
        self._plugins: dict[str, PluginInfo] = {}
        self._loaded_modules: dict[str, Any] = {}
        self._fallbacks: dict[str, Callable] = {}
        self._health_check_enabled = True
        self._conflict_warnings: list[str] = []

    def register(
        self,
        name: str,
        description: str,
        module_name: str,
        license: str,
        fallback: Callable | None = None,
        dependencies: list[str] | None = None,
        conflicts_with: list[str] | None = None,
    ):
        """注册插件

        Args:
            name: 插件名称
            description: 插件描述
            module_name: Python模块名
            license: 许可证类型
            fallback: 回退函数（插件不可用时）
            dependencies: 依赖的其他插件
            conflicts_with: 与之冲突的插件
        """
        plugin = PluginInfo(
            name=name,
            description=description,
            module_name=module_name,
            license=license,
            status=PluginStatus.NOT_INSTALLED,
            dependencies=dependencies or [],
            conflicts_with=conflicts_with or [],
        )

        self._plugins[name] = plugin
        if fallback:
            self._fallbacks[name] = fallback

        # 尝试加载
        self._try_load(name)

        # 检查冲突
        if self._health_check_enabled:
            self._check_conflicts(name)

    def _try_load(self, name: str) -> bool:
        """尝试加载插件"""
        plugin = self._plugins[name]
        start_time = datetime.now()

        try:
            # 检查依赖
            if plugin.dependencies:
                missing_deps = [dep for dep in plugin.dependencies if not self.is_available(dep)]
                if missing_deps:
                    plugin.status = PluginStatus.ERROR
                    plugin.error_msg = f"缺少依赖: {', '.join(missing_deps)}"
                    logger.warning(f"插件 {name} 缺少依赖: {missing_deps}")
                    return False

            module = importlib.import_module(plugin.module_name)
            plugin.status = PluginStatus.AVAILABLE
            plugin.load_time = datetime.now()

            # 获取版本信息
            if hasattr(module, "__version__"):
                plugin.version = module.__version__

            self._loaded_modules[name] = module

            load_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 插件 {name} 加载成功 (版本: {plugin.version}, 耗时: {load_duration:.2f}s)")
            return True

        except ImportError as e:
            plugin.status = PluginStatus.NOT_INSTALLED
            plugin.error_msg = f"未安装: {str(e)}"
            logger.debug(f"⚪ 插件 {name} 未安装: {str(e)}")
            return False

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error_msg = str(e)
            logger.error(f"❌ 插件 {name} 加载错误: {str(e)}")
            return False

    def is_available(self, name: str) -> bool:
        """检查插件是否可用"""
        plugin = self._plugins.get(name)
        return plugin and plugin.status == PluginStatus.AVAILABLE

    def get_module(self, name: str) -> Any | None:
        """获取已加载的模块"""
        return self._loaded_modules.get(name)

    def get_fallback(self, name: str) -> Callable | None:
        """获取回退函数"""
        return self._fallbacks.get(name)

    def list_plugins(self) -> dict[str, PluginInfo]:
        """列出所有插件"""
        return self._plugins.copy()

    def get_info(self, name: str) -> PluginInfo | None:
        """获取插件信息"""
        return self._plugins.get(name)

    def _check_conflicts(self, name: str):
        """检查插件冲突"""
        plugin = self._plugins[name]

        if not plugin.conflicts_with:
            return

        for conflict_name in plugin.conflicts_with:
            if self.is_available(conflict_name):
                warning_msg = f"⚠️  检测到潜在冲突: {name} 与 {conflict_name} 可能不兼容。建议通过插件系统隔离使用。"
                self._conflict_warnings.append(warning_msg)
                logger.warning(warning_msg)

    def get_health_report(self) -> dict[str, Any]:
        """获取插件系统健康报告"""
        available = sum(1 for p in self._plugins.values() if p.status == PluginStatus.AVAILABLE)
        total = len(self._plugins)

        return {
            "total_plugins": total,
            "available": available,
            "missing": sum(1 for p in self._plugins.values() if p.status == PluginStatus.NOT_INSTALLED),
            "errors": sum(1 for p in self._plugins.values() if p.status == PluginStatus.ERROR),
            "health_percentage": (available / total * 100) if total > 0 else 0,
            "conflicts_detected": len(self._conflict_warnings),
            "conflict_warnings": self._conflict_warnings,
            "plugins": {
                name: {
                    "status": plugin.status.value,
                    "version": plugin.version,
                    "license": plugin.license,
                    "error": plugin.error_msg,
                }
                for name, plugin in self._plugins.items()
            },
        }

    def print_health_report(self):
        """打印健康报告"""
        report = self.get_health_report()

        print("\n" + "=" * 60)
        logger.info("插件系统健康报告")
        print("=" * 60 + "\n")

        logger.info(f"总插件数: {report['total_plugins']}")
        logger.info(f"可用插件: {report['available']} ({report['health_percentage']:.1f}%)")
        logger.info(f"未安装: {report['missing']}")
        logger.info(f"加载错误: {report['errors']}")

        if report["conflict_warnings"]:
            logger.info(f"\n⚠️  检测到 {len(report['conflict_warnings'])} 个潜在冲突:")
            for warning in report["conflict_warnings"]:
                logger.info(f"  {warning}")

        logger.info("\n插件详情:")
        for name, info in report["plugins"].items():
            status_icon = {
                "available": "✅",
                "not_installed": "⚪",
                "error": "❌",
                "disabled": "🔒",
            }.get(info["status"], "❓")

            version_str = f"v{info['version']}" if info["version"] else "未知版本"
            logger.info(f"  {status_icon} {name}: {version_str} ({info['license']})")
            if info["error"]:
                logger.info(f"      错误: {info['error']}")

        print("\n" + "=" * 60 + "\n")


# 全局插件注册表
registry = PluginRegistry()


def require_plugin(name: str):
    """装饰器：标记函数需要特定插件

    如果插件不可用，会尝试使用回退实现
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if registry.is_available(name):
                return func(*args, **kwargs)
            else:
                fallback = registry.get_fallback(name)
                if fallback:
                    logger.warning(f"插件 {name} 不可用，使用回退实现")
                    return fallback(*args, **kwargs)
                else:
                    plugin = registry.get_info(name)
                    raise RuntimeError(
                        f"插件 {name} 不可用且无回退实现。"
                        f"状态: {plugin.status.value if plugin else 'unknown'}。"
                        f"错误: {plugin.error_msg if plugin else 'N/A'}"
                    )

        return wrapper

    return decorator


# 导入所有插件适配层以触发注册
# 这些导入会自动注册插件到 registry
from . import (  # noqa: E402
    advanced_plots,  # noqa: F401
    chem_render,  # noqa: F401
    molecule_animator,  # noqa: F401
    pdf_export,  # noqa: F401
    thermo_kinetics,  # noqa: F401
)
