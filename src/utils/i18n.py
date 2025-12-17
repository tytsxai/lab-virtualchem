"""国际化支持 - 增强版

支持特性:
- 多语言动态加载和切换
- 嵌套键查找（支持点号分隔）
- 格式化参数替换
- 回退机制（找不到翻译时回退到默认语言）
- 复数形式处理
- 语言元数据管理
- 翻译缺失检测
"""

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class I18n:
    """国际化管理器"""

    # 语言元数据映射
    LANGUAGE_METADATA = {
        "zh_CN": {"name": "简体中文", "native_name": "简体中文", "direction": "ltr"},
        "zh_TW": {"name": "繁體中文", "native_name": "繁體中文", "direction": "ltr"},
        "en_US": {"name": "English", "native_name": "English", "direction": "ltr"},
        "ja_JP": {"name": "日本語", "native_name": "日本語", "direction": "ltr"},
        "ko_KR": {"name": "한국어", "native_name": "한국어", "direction": "ltr"},
        "fr_FR": {"name": "Français", "native_name": "Français", "direction": "ltr"},
        "de_DE": {"name": "Deutsch", "native_name": "Deutsch", "direction": "ltr"},
        "es_ES": {"name": "Español", "native_name": "Español", "direction": "ltr"},
        "ru_RU": {"name": "Русский", "native_name": "Русский", "direction": "ltr"},
        "ar_SA": {"name": "العربية", "native_name": "العربية", "direction": "rtl"},
    }

    def __init__(
        self,
        i18n_dir: Path | str | None = None,
        default_language: str = "zh_CN",
        fallback_language: str = "en_US",
    ) -> None:
        """初始化国际化

        Args:
            i18n_dir: 翻译文件目录(可选,默认为assets/i18n)
            default_language: 默认语言
            fallback_language: 回退语言（当翻译缺失时使用）
        """
        if i18n_dir is None:
            i18n_dir = Path("assets/i18n")
        self.i18n_dir = Path(i18n_dir)
        self.current_language = default_language
        self.fallback_language = fallback_language
        self._translations: dict[str, dict[str, Any]] = {}
        self._missing_keys: set[str] = set()  # 记录缺失的翻译键

        # 加载默认语言
        if self.i18n_dir.exists():
            self.load_language(default_language)
            # 预加载回退语言
            if fallback_language != default_language:
                self.load_language(fallback_language)

    def load_language(self, language: str) -> bool:
        """加载语言文件

        Args:
            language: 语言代码(如 "zh_CN", "en_US")

        Returns:
            是否成功加载
        """
        lang_file = self.i18n_dir / f"{language}.json"

        if not lang_file.exists():
            logger.warning(f"语言文件不存在: {lang_file}")
            return False

        try:
            with open(lang_file, encoding="utf-8") as f:
                self._translations[language] = json.load(f)

            self.current_language = language
            logger.info(f"已加载语言: {language}")
            return True

        except Exception as e:
            logger.error(f"加载语言文件失败 {lang_file}: {e}")
            return False

    def translate(
        self,
        key: str,
        language: str | None = None,
        count: int | None = None,
        **kwargs: Any,
    ) -> str:
        """翻译文本

        Args:
            key: 翻译键（支持点号分隔的嵌套键，如 "ui.welcome"）
            language: 语言代码(可选,默认使用当前语言)
            count: 数量（用于复数形式处理）
            **kwargs: 格式化参数

        Returns:
            翻译后的文本
        """
        lang = language or self.current_language

        # 确保语言已加载
        if lang not in self._translations and not self.load_language(lang):
            lang = self.fallback_language
            if lang not in self._translations and not self.load_language(lang):
                return key

        # 查找翻译
        translation = self._get_nested_value(self._translations[lang], key)

        # 如果在当前语言中找不到，尝试回退语言
        if translation is None and lang != self.fallback_language:
            translation = self._get_nested_value(
                self._translations.get(self.fallback_language, {}), key
            )
            if translation is None:
                self._missing_keys.add(key)
                logger.warning(f"翻译缺失: {key} (language: {lang})")
                return key

        # 处理复数形式
        if count is not None and isinstance(translation, dict):
            translation = self._get_plural_form(translation, count)

        # 确保最终结果是字符串
        if not isinstance(translation, str):
            return key

        # 格式化参数
        if kwargs or count is not None:
            format_args = {k: str(v) for k, v in kwargs.items()}
            if count is not None:
                format_args["count"] = str(count)
            with contextlib.suppress(KeyError):
                translation = translation.format(**format_args)

        return translation

    def _get_nested_value(self, data: dict[str, Any], key: str) -> Any | None:
        """获取嵌套字典中的值

        Args:
            data: 字典数据
            key: 键（支持点号分隔，如 "ui.welcome"）

        Returns:
            找到的值，如果不存在则返回None
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def _get_plural_form(self, translation: dict[str, str], count: int) -> str:
        """获取复数形式

        支持的键：
        - zero: count == 0
        - one: count == 1
        - two: count == 2
        - few: count in (3, 4)
        - many: count >= 5
        - other: 默认

        Args:
            translation: 包含复数形式的字典
            count: 数量

        Returns:
            对应的复数形式文本
        """
        if count == 0 and "zero" in translation:
            return translation["zero"]
        elif count == 1 and "one" in translation:
            return translation["one"]
        elif count == 2 and "two" in translation:
            return translation["two"]
        elif 3 <= count <= 4 and "few" in translation:
            return translation["few"]
        elif count >= 5 and "many" in translation:
            return translation["many"]
        elif "other" in translation:
            return translation["other"]
        else:
            return str(translation)

    def t(self, key: str, **kwargs: Any) -> str:
        """translate的简写"""
        return self.translate(key, **kwargs)

    def set_language(self, language: str) -> bool:
        """设置当前语言

        Args:
            language: 语言代码

        Returns:
            是否成功设置
        """
        if language in self._translations or self.load_language(language):
            self.current_language = language
            return True
        return False

    def get_available_languages(self) -> list[str]:
        """获取可用语言列表

        Returns:
            语言代码列表
        """
        if not self.i18n_dir.exists():
            return []

        languages = []
        for lang_file in self.i18n_dir.glob("*.json"):
            languages.append(lang_file.stem)

        return sorted(languages)

    def get_language_name(self, language_code: str, native: bool = False) -> str:
        """获取语言的显示名称

        Args:
            language_code: 语言代码
            native: 是否返回本地语言名称

        Returns:
            语言名称
        """
        metadata = self.LANGUAGE_METADATA.get(language_code)
        if metadata:
            return metadata["native_name"] if native else metadata["name"]
        return language_code

    def get_language_direction(self, language_code: str | None = None) -> str:
        """获取语言的文字方向

        Args:
            language_code: 语言代码，默认为当前语言

        Returns:
            "ltr" (从左到右) 或 "rtl" (从右到左)
        """
        lang = language_code or self.current_language
        metadata = self.LANGUAGE_METADATA.get(lang)
        return metadata["direction"] if metadata else "ltr"

    def get_missing_keys(self) -> set[str]:
        """获取缺失的翻译键

        Returns:
            缺失翻译键的集合
        """
        return self._missing_keys.copy()

    def clear_missing_keys(self) -> None:
        """清空缺失翻译键记录"""
        self._missing_keys.clear()

    def has_translation(self, key: str, language: str | None = None) -> bool:
        """检查是否存在某个翻译

        Args:
            key: 翻译键
            language: 语言代码，默认为当前语言

        Returns:
            是否存在该翻译
        """
        lang = language or self.current_language
        if lang not in self._translations:
            return False

        return self._get_nested_value(self._translations[lang], key) is not None

    def get_all_keys(self, language: str | None = None, prefix: str = "") -> list[str]:
        """获取所有翻译键

        Args:
            language: 语言代码，默认为当前语言
            prefix: 键前缀过滤

        Returns:
            翻译键列表
        """
        lang = language or self.current_language
        if lang not in self._translations:
            return []

        def extract_keys(data: dict[str, Any], parent_key: str = "") -> list[str]:
            keys = []
            for k, v in data.items():
                full_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    keys.extend(extract_keys(v, full_key))
                else:
                    keys.append(full_key)
            return keys

        all_keys = extract_keys(self._translations[lang])

        if prefix:
            return [k for k in all_keys if k.startswith(prefix)]
        return all_keys
