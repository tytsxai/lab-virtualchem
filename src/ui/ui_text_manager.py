"""
UI文案管理器
统一管理UI中的所有文案,确保国际化和可控性
"""

import logging
from typing import Any

from ..utils.i18n import I18n

logger = logging.getLogger(__name__)


class UITextManager:
    """UI文案管理器"""

    def __init__(self, i18n: I18n | None = None):
        """
        初始化UI文案管理器

        Args:
            i18n: 国际化实例,如果为None则创建新实例
        """
        self.i18n = i18n or I18n()

    def get_welcome_texts(self) -> dict[str, str]:
        """获取欢迎页面文案"""
        return {
            "title": self.i18n.t("ui.welcome"),
            "version": self.i18n.t("app.version"),
            "select_hint": self.i18n.t("ui.select_experiment_hint"),
            "features": self.i18n.t("ui.features_list"),
        }

    def get_wizard_texts(self) -> dict[str, str]:
        """获取向导文案"""
        return {
            "welcome_title": self.i18n.t("wizard.welcome_title"),
            "version": self.i18n.t("wizard.version"),
            "intro": self.i18n.t("wizard.intro"),
            "dont_show_again": self.i18n.t("wizard.dont_show_again"),
            "skip": self.i18n.t("wizard.skip"),
            "previous": self.i18n.t("wizard.previous"),
            "next": self.i18n.t("wizard.next"),
            "finish": self.i18n.t("wizard.finish"),
            "features_title": self.i18n.t("wizard.features_title"),
            "features_desc": self.i18n.t("wizard.features_desc"),
            "quick_start_title": self.i18n.t("wizard.quick_start_title"),
            "quick_start_desc": self.i18n.t("wizard.quick_start_desc"),
        }

    def get_error_texts(self) -> dict[str, str]:
        """获取错误边界文案"""
        return {
            "component_failed": self.i18n.t("ui.component_failed"),
            "retry": self.i18n.t("ui.retry"),
            "error_details": self.i18n.t("ui.error_details"),
        }

    def get_progress_texts(self) -> dict[str, str]:
        """获取进度条文案"""
        return {
            "progress_format": self.i18n.t("ui.progress_format"),
        }

    def format_text(self, key: str, **kwargs: Any) -> str:
        """
        格式化文案

        Args:
            key: 文案键
            **kwargs: 格式化参数

        Returns:
            格式化后的文案
        """
        return self.i18n.translate(key, **kwargs)

    def get_feature_list(self) -> list[str]:
        """获取特性列表"""
        return [
            self.i18n.t("features.interactive_operation"),
            self.i18n.t("features.real_time_feedback"),
            self.i18n.t("features.safety_tips"),
            self.i18n.t("features.report_generation"),
        ]

    def get_formatted_features(self) -> str:
        """获取格式化的特性列表字符串"""
        features = self.get_feature_list()
        return "\n".join([f"✓ {feature}" for feature in features])
