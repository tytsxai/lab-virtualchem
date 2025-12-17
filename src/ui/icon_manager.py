"""图标管理模块

使用QtAwesome提供Font Awesome和Material Design图标。
"""

import logging
from typing import Any

try:
    import qtawesome as qta
    from PySide6.QtGui import QColor, QIcon

    QTAWESOME_AVAILABLE = True
except ImportError:
    QTAWESOME_AVAILABLE = False
    qta = None
    QIcon = None
    QColor = None

logger = logging.getLogger(__name__)


class IconManager:
    """图标管理器"""

    # 预定义图标映射
    ICONS = {
        # 实验相关
        "experiment": "fa5s.flask",
        "chemistry": "mdi.flask-outline",
        "beaker": "fa5s.vial",
        "test_tube": "mdi.test-tube",
        # 操作
        "play": "fa5s.play-circle",
        "pause": "fa5s.pause-circle",
        "stop": "fa5s.stop-circle",
        "reset": "fa5s.undo",
        "next": "fa5s.arrow-right",
        "previous": "fa5s.arrow-left",
        # 文件
        "save": "fa5s.save",
        "open": "fa5s.folder-open",
        "export": "fa5s.file-export",
        "import": "fa5s.file-import",
        "print": "fa5s.print",
        # 状态
        "success": "mdi.check-circle",
        "error": "mdi.alert-circle",
        "warning": "mdi.alert",
        "info": "mdi.information",
        "loading": "fa5s.spinner",
        # 数据
        "chart": "fa5s.chart-line",
        "graph": "mdi.chart-bell-curve",
        "table": "fa5s.table",
        "report": "fa5s.file-alt",
        # 设置
        "settings": "fa5s.cog",
        "help": "fa5s.question-circle",
        "about": "mdi.information-outline",
        # 用户
        "user": "fa5s.user",
        "student": "fa5s.user-graduate",
        "admin": "fa5s.user-shield",
        # 知识库
        "book": "fa5s.book",
        "database": "fa5s.database",
        "search": "fa5s.search",
        # 安全
        "safety": "mdi.shield-alert",
        "hazard": "mdi.biohazard",
        "fire": "fa5s.fire",
        "toxic": "mdi.skull-crossbones",
        # 仪器
        "thermometer": "fa5s.thermometer-half",
        "scale": "fa5s.balance-scale",
        "timer": "fa5s.clock",
        "microscope": "fa5s.microscope",
        # 分子
        "molecule": "mdi.molecule",
        "atom": "mdi.atom",
        # UI
        "close": "fa5s.times",
        "minimize": "fa5s.window-minimize",
        "maximize": "fa5s.window-maximize",
        "menu": "fa5s.bars",
        "more": "fa5s.ellipsis-v",
        # 方向
        "up": "fa5s.arrow-up",
        "down": "fa5s.arrow-down",
        "left": "fa5s.arrow-left",
        "right": "fa5s.arrow-right",
        # 编辑
        "edit": "fa5s.edit",
        "delete": "fa5s.trash",
        "copy": "fa5s.copy",
        "paste": "fa5s.paste",
        "add": "fa5s.plus-circle",
        "remove": "fa5s.minus-circle",
    }

    # 预定义颜色方案
    COLORS = {
        "primary": "#1976D2",  # 蓝色
        "success": "#4CAF50",  # 绿色
        "warning": "#FF9800",  # 橙色
        "error": "#F44336",  # 红色
        "info": "#2196F3",  # 浅蓝
        "danger": "#E91E63",  # 粉红
        "neutral": "#757575",  # 灰色
        "chemistry": "#00BCD4",  # 青色
        "fire": "#FF5722",  # 深橙
        "toxic": "#9C27B0",  # 紫色
    }

    def __init__(self) -> None:
        """初始化图标管理器"""
        self.available = QTAWESOME_AVAILABLE

        if not self.available:
            logger.warning(
                "QtAwesome未安装,图标功能不可用. 安装: pip install qtawesome"
            )

    def get_icon(
        self,
        name: str,
        color: str | None = None,
        scale_factor: float = 1.0,
        **kwargs: Any,
    ) -> Any | None:
        """获取图标

        Args:
            name: 图标名称(来自ICONS字典)或qtawesome图标名
            color: 颜色(十六进制或颜色名)
            scale_factor: 缩放因子
            **kwargs: 其他qtawesome参数

        Returns:
            QIcon对象,如果不可用返回None
        """
        if not self.available:
            return None

        # 从预定义图标获取
        icon_name = self.ICONS.get(name, name)

        # 颜色处理
        if color:
            if color in self.COLORS:
                color = self.COLORS[color]
        else:
            color = self.COLORS["neutral"]

        try:
            return qta.icon(icon_name, color=color, scale_factor=scale_factor, **kwargs)
        except Exception as e:
            logger.error(f"获取图标失败 {name}: {e}")
            return None

    def get_colored_icon(
        self, name: str, color_name: str = "primary", scale_factor: float = 1.0
    ) -> Any | None:
        """获取彩色图标(便捷方法)

        Args:
            name: 图标名称
            color_name: 颜色方案名称
            scale_factor: 缩放因子

        Returns:
            QIcon对象
        """
        color = self.COLORS.get(color_name, self.COLORS["neutral"])
        return self.get_icon(name, color=color, scale_factor=scale_factor)

    def get_status_icon(self, status: str) -> Any | None:
        """获取状态图标

        Args:
            status: 状态 ('success', 'error', 'warning', 'info')

        Returns:
            QIcon对象
        """
        icon_map = {
            "success": ("success", "success"),
            "error": ("error", "error"),
            "warning": ("warning", "warning"),
            "info": ("info", "info"),
        }

        icon_name, color_name = icon_map.get(status, ("info", "neutral"))
        return self.get_colored_icon(icon_name, color_name)

    def get_experiment_icon(self, _experiment_type: str = "chemistry") -> Any | None:
        """获取实验图标"""
        return self.get_colored_icon("experiment", "chemistry")

    def get_safety_icon(self, hazard_type: str = "general") -> Any | None:
        """获取安全图标

        Args:
            hazard_type: 危险类型 ('fire', 'toxic', 'general')

        Returns:
            QIcon对象
        """
        icon_map = {
            "fire": ("fire", "fire"),
            "toxic": ("toxic", "toxic"),
            "general": ("safety", "warning"),
        }

        icon_name, color_name = icon_map.get(hazard_type, ("safety", "warning"))
        return self.get_colored_icon(icon_name, color_name)

    def get_animated_icon(self, name: str, **kwargs: Any) -> Any | None:
        """获取动画图标

        Args:
            name: 图标名称
            **kwargs: qtawesome动画参数

        Returns:
            动画QIcon对象
        """
        if not self.available:
            return None

        icon_name = self.ICONS.get(name, name)

        try:
            # 添加动画效果
            return qta.icon(icon_name, animation=qta.Spin(icon_name), **kwargs)
        except Exception as e:
            logger.error(f"获取动画图标失败 {name}: {e}")
            return self.get_icon(name)

    def get_spin_icon(
        self, name: str = "loading", color: str = "primary"
    ) -> Any | None:
        """获取旋转图标(用于加载状态)"""
        return self.get_animated_icon(name, color=self.COLORS.get(color, color))

    @staticmethod
    def list_available_icons() -> dict[str, str]:
        """列出所有可用图标"""
        return IconManager.ICONS.copy()

    @staticmethod
    def list_color_schemes() -> dict[str, str]:
        """列出所有颜色方案"""
        return IconManager.COLORS.copy()


# 全局实例
icon_manager = IconManager()


# 便捷函数
def get_icon(name: str, color: str | None = None, **kwargs: Any) -> Any | None:
    """便捷函数: 获取图标"""
    return icon_manager.get_icon(name, color, **kwargs)


def get_status_icon(status: str) -> Any | None:
    """便捷函数: 获取状态图标"""
    return icon_manager.get_status_icon(status)


def get_experiment_icon() -> Any | None:
    """便捷函数: 获取实验图标"""
    return icon_manager.get_experiment_icon()
