"""
UI配置管理
自适应配置系统，支持不同平台和设备
"""

import json
import logging
from pathlib import Path
from typing import Any

from .responsive import ResponsiveHelper, ScreenSize
from .themes import ThemeType

logger = logging.getLogger(__name__)


class UIConfig:
    """UI配置类"""

    # 默认配置
    DEFAULT_CONFIG = {
        # 主题设置
        "theme": {
            "type": "auto",  # auto, light, dark, high_contrast
            "follow_system": True,
            "auto_switch": False,  # 根据时间自动切换
        },
        # 布局设置
        "layout": {
            "responsive": True,
            "adaptive_font": True,
            "adaptive_spacing": True,
            "show_sidebar": True,
            "sidebar_width": 250,
        },
        # Windows特定设置
        "windows": {
            "enable_acrylic": False,  # 亚克力效果（Win10+）
            "enable_shadow": True,
            "taskbar_integration": True,
            "jump_list": True,
        },
        # Android特定设置
        "android": {
            "enable_gestures": True,
            "bottom_navigation": True,
            "floating_action_button": True,
            "immersive_mode": False,
        },
        # 触摸设置
        "touch": {
            "enabled": "auto",  # auto, enabled, disabled
            "target_size": 48,  # 触摸目标最小尺寸（px）
            "gesture_threshold": 10,  # 手势识别阈值
        },
        # 动画设置
        "animation": {
            "enabled": True,
            "duration": 300,  # 动画时长（ms）
            "easing": "ease_out",
            "reduce_motion": False,  # 减少动画（辅助功能）
        },
        # 性能设置
        "performance": {
            "hardware_acceleration": True,
            "render_quality": "medium",  # low, medium, high
            "fps_limit": 60,
            "cache_size_mb": 100,
        },
        # 辅助功能
        "accessibility": {
            "high_contrast": False,
            "large_text": False,
            "screen_reader": False,
            "keyboard_navigation": True,
        },
        # 实验功能
        "experimental": {
            "new_chart_engine": False,
            "webgl_rendering": False,
            "ar_mode": False,
        },
    }

    def __init__(self, config_file: str = "config/ui_config.json"):
        self.config_file = Path(config_file)
        self.config: dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self.load()
        self.apply_auto_config()

    def load(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, encoding="utf-8") as f:
                    user_config = json.load(f)
                    self._merge_config(user_config)
        except Exception as e:
            logger.info(f"加载UI配置失败: {e}")

    def save(self):
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.info(f"保存UI配置失败: {e}")

    def _merge_config(self, user_config: dict):
        """合并用户配置"""
        for key, value in user_config.items():
            if key in self.config and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value

    def apply_auto_config(self):
        """应用自动配置"""
        screen_info = ResponsiveHelper.get_screen_info()

        # 移动设备自动配置
        if screen_info["size_type"] == ScreenSize.MOBILE:
            self.config["layout"]["show_sidebar"] = False
            self.config["android"]["bottom_navigation"] = True
            self.config["touch"]["enabled"] = True

        # 平板自动配置
        elif screen_info["size_type"] == ScreenSize.TABLET:
            self.config["layout"]["sidebar_width"] = 200
            self.config["touch"]["enabled"] = True

        # 高DPI屏幕
        if screen_info["dpi"] > 144:
            self.config["layout"]["adaptive_font"] = True
            self.config["performance"]["render_quality"] = "high"

    def get(self, path: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            path: 配置路径，如 "theme.type" 或 "layout.responsive"
            default: 默认值
        """
        keys = path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, path: str, value: Any):
        """
        设置配置项

        Args:
            path: 配置路径
            value: 值
        """
        keys = path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_theme_type(self) -> ThemeType:
        """获取主题类型"""
        theme_str = self.get("theme.type", "light")

        if theme_str == "auto":
            from .themes import ThemeManager

            return ThemeManager.get_system_theme()

        theme_map = {
            "light": ThemeType.LIGHT,
            "dark": ThemeType.DARK,
            "high_contrast": ThemeType.HIGH_CONTRAST,
        }

        return theme_map.get(theme_str, ThemeType.LIGHT)

    def is_mobile_layout(self) -> bool:
        """是否使用移动布局"""
        return ResponsiveHelper.is_mobile() or not self.get("layout.show_sidebar", True)

    def is_touch_enabled(self) -> bool:
        """是否启用触摸"""
        touch_setting = self.get("touch.enabled", "auto")

        if touch_setting == "auto":
            from .responsive import TouchHelper

            return TouchHelper.is_touch_enabled()

        return touch_setting == "enabled"

    def get_animation_duration(self) -> int:
        """获取动画时长"""
        if not self.get("animation.enabled", True):
            return 0

        if self.get("accessibility.reduce_motion", False):
            return self.get("animation.duration", 300) // 2

        return self.get("animation.duration", 300)

    def export_stylesheet_vars(self) -> dict[str, str]:
        """导出样式表变量"""
        return {
            "animation_duration": f"{self.get_animation_duration()}ms",
            "border_radius": "4px" if self.get("theme.type") != "high_contrast" else "0px",
            "shadow_enabled": "true" if self.get("windows.enable_shadow", True) else "false",
        }


class PlatformDetector:
    """平台检测器"""

    @staticmethod
    def is_windows() -> bool:
        """是否为Windows"""
        import sys

        return sys.platform == "win32"

    @staticmethod
    def is_windows_10_or_later() -> bool:
        """是否为Windows 10或更新版本"""
        if not PlatformDetector.is_windows():
            return False

        try:
            import platform

            version = platform.version()
            # Windows 10是版本10.0
            major = int(version.split(".")[0])
            return major >= 10
        except Exception:
            return False

    @staticmethod
    def is_android() -> bool:
        """是否为Android（通过环境检测）"""
        try:
            import os

            # 检测Android特征
            return "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ
        except Exception:
            return False

    @staticmethod
    def is_touch_device() -> bool:
        """是否为触摸设备"""
        from .responsive import TouchHelper

        return TouchHelper.is_touch_enabled()

    @staticmethod
    def get_platform_info() -> dict[str, Any]:
        """获取平台信息"""
        import platform
        import sys

        screen_info = ResponsiveHelper.get_screen_info()

        return {
            "os": sys.platform,
            "os_version": platform.version(),
            "python_version": sys.version,
            "is_windows": PlatformDetector.is_windows(),
            "is_windows_10": PlatformDetector.is_windows_10_or_later(),
            "is_android": PlatformDetector.is_android(),
            "is_touch": PlatformDetector.is_touch_device(),
            "screen_width": screen_info["width"],
            "screen_height": screen_info["height"],
            "screen_dpi": screen_info["dpi"],
            "screen_type": screen_info["size_type"].value,
        }


# 全局UI配置实例
_ui_config_instance = None


def get_ui_config() -> UIConfig:
    """获取全局UI配置实例"""
    global _ui_config_instance
    if _ui_config_instance is None:
        _ui_config_instance = UIConfig()
    return _ui_config_instance
