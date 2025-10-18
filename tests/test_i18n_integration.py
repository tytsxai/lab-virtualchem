#!/usr/bin/env python3
"""
国际化集成测试
测试多语言切换和翻译功能
"""

from pathlib import Path

import pytest

from src.utils.i18n import I18n


class TestI18nIntegration:
    """国际化集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.i18n = I18n()

    def test_all_languages_available(self):
        """测试所有语言都可用"""
        available = self.i18n.get_available_languages()
        expected = ["de_DE", "en_US", "es_ES", "fr_FR", "ja_JP", "ko_KR", "zh_CN"]

        for lang in expected:
            assert lang in available, f"语言 {lang} 应该可用"

    def test_button_texts_all_languages(self):
        """测试所有语言的按钮文本"""
        button_keys = [
            "ui.confirm",
            "ui.cancel",
            "ui.close",
            "step.next",
            "step.previous",
            "step.submit",
            "settings.save",
        ]

        languages = self.i18n.get_available_languages()

        for lang in languages:
            self.i18n.set_language(lang)
            for key in button_keys:
                translation = self.i18n.t(key)
                assert translation != key, f"键 {key} 在语言 {lang} 中应该有翻译"
                assert len(translation) > 0, f"键 {key} 在语言 {lang} 中不应该为空"

    def test_message_prompts_all_languages(self):
        """测试所有语言的消息提示"""
        message_keys = [
            "message.confirm_exit",
            "message.confirm_restart",
            "message.loading",
            "ui.info",
            "ui.warning",
            "ui.error",
            "ui.success",
        ]

        languages = self.i18n.get_available_languages()

        for lang in languages:
            self.i18n.set_language(lang)
            for key in message_keys:
                translation = self.i18n.t(key)
                assert translation != key, f"键 {key} 在语言 {lang} 中应该有翻译"
                assert len(translation) > 0, f"键 {key} 在语言 {lang} 中不应该为空"

    def test_language_switching(self):
        """测试语言切换"""
        # 切换到英文
        self.i18n.set_language("en_US")
        assert self.i18n.t("ui.welcome") == "Welcome to VirtualChemLab"

        # 切换到中文
        self.i18n.set_language("zh_CN")
        assert self.i18n.t("ui.welcome") == "欢迎使用 VirtualChemLab"

        # 切换到日文
        self.i18n.set_language("ja_JP")
        welcome_ja = self.i18n.t("ui.welcome")
        assert welcome_ja != "Welcome to VirtualChemLab"
        assert len(welcome_ja) > 0

    def test_parameter_formatting(self):
        """测试参数格式化"""
        languages = ["zh_CN", "en_US", "ja_JP"]

        for lang in languages:
            self.i18n.set_language(lang)

            # 测试带参数的翻译
            score_msg = self.i18n.t("ui.final_score_message", score=95)
            assert "95" in score_msg, f"语言 {lang} 的得分消息应包含分数"

            # 测试进度格式化
            progress = self.i18n.t("ui.progress_format", percent=75, current=3, total=4)
            assert "75" in progress, f"语言 {lang} 的进度应包含百分比"
            assert "3" in progress, f"语言 {lang} 的进度应包含当前值"
            assert "4" in progress, f"语言 {lang} 的进度应包含总数"

    def test_nested_keys(self):
        """测试嵌套键"""
        languages = self.i18n.get_available_languages()

        nested_keys = [
            "menu.file",
            "experiment.start",
            "settings.general",
            "error.file_not_found",
            "wizard.welcome_title",
        ]

        for lang in languages:
            self.i18n.set_language(lang)
            for key in nested_keys:
                translation = self.i18n.t(key)
                assert translation != key, f"嵌套键 {key} 在语言 {lang} 中应该有翻译"
                assert len(translation) > 0

    def test_fallback_mechanism(self):
        """测试回退机制"""
        # 测试不存在的键
        result = self.i18n.t("nonexistent.key")
        assert result == "nonexistent.key", "不存在的键应该返回键本身"

        # 测试不存在的语言
        self.i18n.set_language("invalid_lang")
        # 应该回退到默认语言
        result = self.i18n.t("ui.welcome")
        assert len(result) > 0, "即使语言无效也应该有翻译"

    def test_language_metadata(self):
        """测试语言元数据"""
        # 测试语言名称
        assert self.i18n.get_language_name("zh_CN") == "简体中文"
        assert self.i18n.get_language_name("en_US") == "English"
        assert self.i18n.get_language_name("ja_JP") == "日本語"

        # 测试文字方向
        assert self.i18n.get_language_direction("zh_CN") == "ltr"
        assert self.i18n.get_language_direction("en_US") == "ltr"

    def test_error_messages_completeness(self):
        """测试错误消息的完整性"""
        error_keys = [
            "error.file_not_found",
            "error.permission_denied",
            "error.network_error",
            "error.timeout_error",
            "error.invalid_data",
            "error.disk_full",
            "error.config_error",
        ]

        languages = self.i18n.get_available_languages()

        for lang in languages:
            self.i18n.set_language(lang)
            for key in error_keys:
                # 错误消息
                error_msg = self.i18n.t(key, error="test error")
                assert len(error_msg) > 0, f"错误键 {key} 在语言 {lang} 中应该有翻译"

                # 错误提示
                hint_key = f"{key}_hint"
                hint_msg = self.i18n.t(hint_key)
                assert len(hint_msg) > 0, f"错误提示 {hint_key} 在语言 {lang} 中应该有翻译"

    def test_ui_text_manager_integration(self):
        """测试UI文案管理器集成"""
        from src.ui.ui_text_manager import UITextManager

        # 测试中文
        self.i18n.set_language("zh_CN")
        ui_mgr = UITextManager(self.i18n)

        welcome_texts = ui_mgr.get_welcome_texts()
        assert "title" in welcome_texts
        assert len(welcome_texts["title"]) > 0

        # 测试英文
        self.i18n.set_language("en_US")
        ui_mgr = UITextManager(self.i18n)

        wizard_texts = ui_mgr.get_wizard_texts()
        assert "welcome_title" in wizard_texts
        assert "Welcome" in wizard_texts["welcome_title"]

    def test_special_characters(self):
        """测试特殊字符处理"""
        languages = ["zh_CN", "en_US", "ja_JP", "de_DE"]

        for lang in languages:
            self.i18n.set_language(lang)

            # 测试包含特殊字符的翻译
            wizard_title = self.i18n.t("wizard.welcome_title")
            assert len(wizard_title) > 0

            # 测试emoji
            if "🧪" in wizard_title or "Welcome" in wizard_title:
                assert True
            else:
                # 确保至少有内容
                assert len(wizard_title) > 5


def test_i18n_files_exist():
    """测试所有i18n文件存在"""
    i18n_dir = Path("assets/i18n")
    required_files = [
        "zh_CN.json",
        "en_US.json",
        "ja_JP.json",
        "ko_KR.json",
        "fr_FR.json",
        "de_DE.json",
        "es_ES.json",
        "languages.json",
    ]

    for filename in required_files:
        file_path = i18n_dir / filename
        assert file_path.exists(), f"i18n文件 {filename} 应该存在"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

