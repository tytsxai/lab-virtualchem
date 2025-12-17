"""
懒加载器
提供组件懒加载功能
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)

# 全局懒加载注册表
_lazy_components: dict[str, dict[str, Any]] = {}


def register_lazy_component(
    name: str, loader_func: Callable, priority: int = 5
) -> None:
    """注册懒加载组件

    Args:
        name: 组件名称
        loader_func: 加载函数
        priority: 优先级（数字越小优先级越高）
    """
    _lazy_components[name] = {
        "loader": loader_func,
        "priority": priority,
        "loaded": False,
        "instance": None,
    }
    logger.debug(f"注册懒加载组件: {name} (优先级: {priority})")


def load_component(name: str) -> Any:
    """加载指定组件

    Args:
        name: 组件名称

    Returns:
        组件实例
    """
    if name not in _lazy_components:
        raise ValueError(f"未找到组件: {name}")

    component_info = _lazy_components[name]

    if component_info["loaded"]:
        return component_info["instance"]

    logger.info(f"正在加载组件: {name}")
    try:
        instance = component_info["loader"]()
        component_info["instance"] = instance
        component_info["loaded"] = True
        logger.info(f"组件加载成功: {name}")
        return instance
    except Exception as e:
        logger.error(f"组件加载失败: {name}, 错误: {e}")
        raise


def get_component_status(name: str) -> dict[str, Any]:
    """获取组件状态

    Args:
        name: 组件名称

    Returns:
        组件状态信息
    """
    if name not in _lazy_components:
        return {"exists": False}

    component_info = _lazy_components[name]
    return {
        "exists": True,
        "loaded": component_info["loaded"],
        "priority": component_info["priority"],
    }


def list_components() -> list[str]:
    """列出所有注册的组件

    Returns:
        组件名称列表
    """
    return list(_lazy_components.keys())


def preload_components(priority_threshold: int = 3) -> None:
    """预加载高优先级组件

    Args:
        priority_threshold: 优先级阈值
    """
    components_to_load = [
        (name, info)
        for name, info in _lazy_components.items()
        if not info["loaded"] and info["priority"] <= priority_threshold
    ]

    # 按优先级排序
    components_to_load.sort(key=lambda x: x[1]["priority"])

    for name, _ in components_to_load:
        try:
            load_component(name)
        except Exception as e:
            logger.warning(f"预加载组件失败: {name}, 错误: {e}")


def cleanup_component(name: str) -> None:
    """清理组件

    Args:
        name: 组件名称
    """
    if name in _lazy_components:
        component_info = _lazy_components[name]
        if component_info["loaded"] and hasattr(component_info["instance"], "cleanup"):
            try:
                component_info["instance"].cleanup()
            except Exception as e:
                logger.warning(f"清理组件失败: {name}, 错误: {e}")

        component_info["loaded"] = False
        component_info["instance"] = None
        logger.debug(f"组件已清理: {name}")
