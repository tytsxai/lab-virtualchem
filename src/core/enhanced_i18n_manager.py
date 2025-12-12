"""
增强国际化管理器
提供多语言支持、动态语言切换、翻译缓存和本地化资源管理
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .enhanced_event_bus import Event, EventPriority, publish_event, subscribe_event
from .enhanced_observability import LogLevel, get_observability
from .error_handler import get_error_handler
from .smart_cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class LanguageCode(Enum):
    """语言代码"""
    EN = "en"  # 英语
    ZH_CN = "zh-cn"  # 简体中文
    ZH_TW = "zh-tw"  # 繁体中文
    JA = "ja"  # 日语
    KO = "ko"  # 韩语
    FR = "fr"  # 法语
    DE = "de"  # 德语
    ES = "es"  # 西班牙语
    RU = "ru"  # 俄语
    AR = "ar"  # 阿拉伯语


@dataclass
class LanguageInfo:
    """语言信息"""
    code: LanguageCode
    name: str
    native_name: str
    region: str
    script: str = ""
    direction: str = "ltr"  # ltr 或 rtl
    plural_forms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code.value,
            "name": self.name,
            "native_name": self.native_name,
            "region": self.region,
            "script": self.script,
            "direction": self.direction,
            "plural_forms": self.plural_forms
        }


@dataclass
class TranslationEntry:
    """翻译条目"""
    key: str
    value: str
    context: str = ""
    plural_key: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "context": self.context,
            "plural_key": self.plural_key,
            "tags": self.tags
        }


@dataclass
class LocalizationResource:
    """本地化资源"""
    language: LanguageCode
    namespace: str
    entries: dict[str, TranslationEntry] = field(default_factory=dict)
    last_modified: float = 0.0
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "language": self.language.value,
            "namespace": self.namespace,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "last_modified": self.last_modified,
            "version": self.version
        }


class EnhancedI18nManager:
    """增强国际化管理器"""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._error_handler = get_error_handler()
        self._observability = get_observability()
        self._cache_manager = get_cache_manager()

        # 语言信息
        self._languages: dict[LanguageCode, LanguageInfo] = {}
        self._current_language: LanguageCode = LanguageCode.EN
        self._fallback_language: LanguageCode = LanguageCode.EN

        # 翻译资源
        self._resources: dict[str, LocalizationResource] = {}
        self._namespaces: dict[str, dict[LanguageCode, str]] = {}

        # 翻译缓存
        self._translation_cache: dict[str, str] = {}
        self._cache_enabled = self._config.get("cache_enabled", True)

        # 统计信息
        self._stats = {
            "total_translations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "language_switches": 0,
            "resource_loads": 0
        }

        # 线程安全
        self._lock = threading.RLock()

        # 事件订阅
        self._setup_event_subscriptions()

        # 初始化
        self._initialize_languages()
        self._load_default_resources()

    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        subscribe_event("language_change_request", self._handle_language_change)
        subscribe_event("translation_request", self._handle_translation_request)
        subscribe_event("resource_reload_request", self._handle_resource_reload)

    def _initialize_languages(self) -> None:
        """初始化语言信息"""
        self._languages = {
            LanguageCode.EN: LanguageInfo(
                code=LanguageCode.EN,
                name="English",
                native_name="English",
                region="US",
                script="Latn",
                direction="ltr",
                plural_forms=["one", "other"]
            ),
            LanguageCode.ZH_CN: LanguageInfo(
                code=LanguageCode.ZH_CN,
                name="Chinese (Simplified)",
                native_name="简体中文",
                region="CN",
                script="Hans",
                direction="ltr",
                plural_forms=["other"]
            ),
            LanguageCode.ZH_TW: LanguageInfo(
                code=LanguageCode.ZH_TW,
                name="Chinese (Traditional)",
                native_name="繁體中文",
                region="TW",
                script="Hant",
                direction="ltr",
                plural_forms=["other"]
            ),
            LanguageCode.JA: LanguageInfo(
                code=LanguageCode.JA,
                name="Japanese",
                native_name="日本語",
                region="JP",
                script="Hira",
                direction="ltr",
                plural_forms=["other"]
            ),
            LanguageCode.KO: LanguageInfo(
                code=LanguageCode.KO,
                name="Korean",
                native_name="한국어",
                region="KR",
                script="Hang",
                direction="ltr",
                plural_forms=["other"]
            ),
            LanguageCode.FR: LanguageInfo(
                code=LanguageCode.FR,
                name="French",
                native_name="Français",
                region="FR",
                script="Latn",
                direction="ltr",
                plural_forms=["one", "other"]
            ),
            LanguageCode.DE: LanguageInfo(
                code=LanguageCode.DE,
                name="German",
                native_name="Deutsch",
                region="DE",
                script="Latn",
                direction="ltr",
                plural_forms=["one", "other"]
            ),
            LanguageCode.ES: LanguageInfo(
                code=LanguageCode.ES,
                name="Spanish",
                native_name="Español",
                region="ES",
                script="Latn",
                direction="ltr",
                plural_forms=["one", "other"]
            ),
            LanguageCode.RU: LanguageInfo(
                code=LanguageCode.RU,
                name="Russian",
                native_name="Русский",
                region="RU",
                script="Cyrl",
                direction="ltr",
                plural_forms=["one", "few", "many", "other"]
            ),
            LanguageCode.AR: LanguageInfo(
                code=LanguageCode.AR,
                name="Arabic",
                native_name="العربية",
                region="SA",
                script="Arab",
                direction="rtl",
                plural_forms=["zero", "one", "two", "few", "many", "other"]
            )
        }

    def _load_default_resources(self) -> None:
        """加载默认资源"""
        # 加载默认的英文资源
        self._load_resource_from_file(
            Path("assets/i18n/en.json"),
            LanguageCode.EN,
            "default"
        )

        # 加载默认的中文资源
        self._load_resource_from_file(
            Path("assets/i18n/zh-cn.json"),
            LanguageCode.ZH_CN,
            "default"
        )

    def _load_resource_from_file(
        self,
        file_path: Path,
        language: LanguageCode,
        namespace: str
    ) -> bool:
        """从文件加载资源"""
        if not file_path.exists():
            return False

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            resource = LocalizationResource(
                language=language,
                namespace=namespace,
                last_modified=file_path.stat().st_mtime,
                version=data.get("version", "1.0.0")
            )

            # 解析翻译条目
            for key, value in data.get("translations", {}).items():
                if isinstance(value, dict):
                    entry = TranslationEntry(
                        key=key,
                        value=value.get("value", ""),
                        context=value.get("context", ""),
                        plural_key=value.get("plural_key", ""),
                        tags=value.get("tags", {})
                    )
                else:
                    entry = TranslationEntry(key=key, value=str(value))

                resource.entries[key] = entry

            # 存储资源
            resource_key = f"{language.value}:{namespace}"
            self._resources[resource_key] = resource

            # 更新命名空间映射
            if namespace not in self._namespaces:
                self._namespaces[namespace] = {}
            self._namespaces[namespace][language] = resource_key

            self._stats["resource_loads"] += 1

            # 记录日志
            self._observability.log(
                LogLevel.INFO,
                f"Loaded resource: {resource_key}",
                module="EnhancedI18nManager",
                function="_load_resource_from_file"
            )

            return True
        except Exception as e:
            logger.error(f"Failed to load resource from {file_path}: {e}")
            return False

    def load_resource_directory(self, directory: Path) -> None:
        """加载资源目录"""
        if not directory.exists():
            return

        # 扫描目录中的JSON文件
        for file_path in directory.glob("*.json"):
            # 从文件名推断语言
            language_code = self._infer_language_from_filename(file_path.stem)
            if language_code:
                self._load_resource_from_file(file_path, language_code, "default")

        # 扫描子目录
        for subdir in directory.iterdir():
            if subdir.is_dir():
                self.load_resource_directory(subdir)

    def _infer_language_from_filename(self, filename: str) -> LanguageCode | None:
        """从文件名推断语言"""
        for lang_code in LanguageCode:
            if filename.lower() == lang_code.value.lower():
                return lang_code
        return None

    def set_current_language(self, language: LanguageCode) -> bool:
        """设置当前语言"""
        if language not in self._languages:
            logger.error(f"Unsupported language: {language}")
            return False

        with self._lock:
            old_language = self._current_language
            self._current_language = language
            self._stats["language_switches"] += 1

            # 清空翻译缓存
            if self._cache_enabled:
                self._translation_cache.clear()

            # 发布语言变更事件
            publish_event(
                "language_changed",
                {
                    "old_language": old_language.value,
                    "new_language": language.value
                },
                priority=EventPriority.HIGH
            )

            # 记录日志
            self._observability.log(
                LogLevel.INFO,
                f"Language changed: {old_language.value} -> {language.value}",
                module="EnhancedI18nManager",
                function="set_current_language"
            )

            return True

    def get_current_language(self) -> LanguageCode:
        """获取当前语言"""
        return self._current_language

    def get_language_info(self, language: LanguageCode) -> LanguageInfo | None:
        """获取语言信息"""
        return self._languages.get(language)

    def get_supported_languages(self) -> list[LanguageInfo]:
        """获取支持的语言列表"""
        return list(self._languages.values())

    def translate(
        self,
        key: str,
        namespace: str = "default",
        language: LanguageCode | None = None,
        **kwargs
    ) -> str:
        """翻译文本"""
        if language is None:
            language = self._current_language

        # 构建缓存键
        cache_key = f"{language.value}:{namespace}:{key}"

        # 检查缓存
        if self._cache_enabled and cache_key in self._translation_cache:
            self._stats["cache_hits"] += 1
            return self._translation_cache[cache_key]

        # 查找翻译
        translation = self._find_translation(key, namespace, language)

        # 如果未找到，尝试回退语言
        if not translation and language != self._fallback_language:
            translation = self._find_translation(key, namespace, self._fallback_language)

        # 如果仍未找到，返回键名
        if not translation:
            translation = key
            self._stats["cache_misses"] += 1

            # 记录日志
            self._observability.log(
                LogLevel.WARNING,
                f"Translation not found: {key}",
                module="EnhancedI18nManager",
                function="translate"
            )
        else:
            self._stats["cache_misses"] += 1

        # 格式化翻译
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except Exception as e:
                logger.error(f"Failed to format translation: {e}")

        # 缓存翻译
        if self._cache_enabled:
            self._translation_cache[cache_key] = translation

        return translation

    def _find_translation(
        self,
        key: str,
        namespace: str,
        language: LanguageCode
    ) -> str | None:
        """查找翻译"""
        resource_key = f"{language.value}:{namespace}"
        resource = self._resources.get(resource_key)

        if resource and key in resource.entries:
            return resource.entries[key].value

        return None

    def translate_plural(
        self,
        key: str,
        count: int,
        namespace: str = "default",
        language: LanguageCode | None = None,
        **kwargs
    ) -> str:
        """翻译复数形式"""
        if language is None:
            language = self._current_language

        # 获取语言信息
        lang_info = self._languages.get(language)
        if not lang_info:
            return self.translate(key, namespace, language, **kwargs)

        # 确定复数形式
        plural_form = self._get_plural_form(count, lang_info.plural_forms)

        # 构建复数键
        plural_key = f"{key}:{plural_form}"

        # 查找复数翻译
        translation = self._find_translation(plural_key, namespace, language)

        # 如果未找到，尝试单数形式
        if not translation:
            translation = self._find_translation(key, namespace, language)

        # 如果仍未找到，返回键名
        if not translation:
            translation = key

        # 格式化翻译
        if kwargs:
            kwargs["count"] = count
            try:
                translation = translation.format(**kwargs)
            except Exception as e:
                logger.error(f"Failed to format plural translation: {e}")

        return translation

    def _get_plural_form(self, count: int, plural_forms: list[str]) -> str:
        """获取复数形式"""
        if not plural_forms:
            return "other"

        # 简单的复数规则（可以根据需要扩展）
        if count == 0 and "zero" in plural_forms:
            return "zero"
        elif count == 1 and "one" in plural_forms:
            return "one"
        elif count == 2 and "two" in plural_forms:
            return "two"
        elif 2 < count < 5 and "few" in plural_forms:
            return "few"
        elif count >= 5 and "many" in plural_forms:
            return "many"
        else:
            return "other"

    def add_translation(
        self,
        key: str,
        value: str,
        language: LanguageCode,
        namespace: str = "default",
        context: str = "",
        **tags
    ) -> None:
        """添加翻译"""
        resource_key = f"{language.value}:{namespace}"

        if resource_key not in self._resources:
            self._resources[resource_key] = LocalizationResource(
                language=language,
                namespace=namespace
            )

        entry = TranslationEntry(
            key=key,
            value=value,
            context=context,
            tags=tags
        )

        self._resources[resource_key].entries[key] = entry
        self._stats["total_translations"] += 1

        # 清空相关缓存
        if self._cache_enabled:
            cache_key = f"{language.value}:{namespace}:{key}"
            if cache_key in self._translation_cache:
                del self._translation_cache[cache_key]

    def remove_translation(
        self,
        key: str,
        language: LanguageCode,
        namespace: str = "default"
    ) -> bool:
        """删除翻译"""
        resource_key = f"{language.value}:{namespace}"
        resource = self._resources.get(resource_key)

        if resource and key in resource.entries:
            del resource.entries[key]

            # 清空相关缓存
            if self._cache_enabled:
                cache_key = f"{language.value}:{namespace}:{key}"
                if cache_key in self._translation_cache:
                    del self._translation_cache[cache_key]

            return True

        return False

    def get_translations(
        self,
        language: LanguageCode,
        namespace: str = "default"
    ) -> dict[str, str]:
        """获取所有翻译"""
        resource_key = f"{language.value}:{namespace}"
        resource = self._resources.get(resource_key)

        if resource:
            return {key: entry.value for key, entry in resource.entries.items()}

        return {}

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "current_language": self._current_language.value,
            "supported_languages": len(self._languages),
            "loaded_resources": len(self._resources),
            "cache_size": len(self._translation_cache)
        }

    def _handle_language_change(self, event: Event) -> None:
        """处理语言变更请求"""
        language_code = event.data.get("language")
        if language_code:
            try:
                language = LanguageCode(language_code)
                self.set_current_language(language)
            except ValueError:
                logger.error(f"Invalid language code: {language_code}")

    def _handle_translation_request(self, event: Event) -> None:
        """处理翻译请求"""
        key = event.data.get("key")
        namespace = event.data.get("namespace", "default")
        language = event.data.get("language")

        if key:
            if language:
                try:
                    lang = LanguageCode(language)
                    translation = self.translate(key, namespace, lang)
                except ValueError:
                    translation = self.translate(key, namespace)
            else:
                translation = self.translate(key, namespace)

            # 发布翻译结果
            publish_event(
                "translation_result",
                {"key": key, "translation": translation},
                priority=EventPriority.NORMAL
            )

    def _handle_resource_reload(self, event: Event) -> None:
        """处理资源重载请求"""
        directory = event.data.get("directory")
        if directory:
            self.load_resource_directory(Path(directory))

    def export_translations(self, output_dir: Path) -> None:
        """导出翻译"""
        output_dir.mkdir(exist_ok=True)

        # 导出所有资源
        for _resource_key, resource in self._resources.items():
            filename = f"{resource.language.value}_{resource.namespace}.json"
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(resource.to_dict(), f, indent=2, ensure_ascii=False)

        # 导出统计信息
        stats_file = output_dir / "i18n_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)


# 全局国际化管理器实例
_global_i18n_manager = EnhancedI18nManager()


def get_i18n_manager() -> EnhancedI18nManager:
    """获取全局国际化管理器"""
    return _global_i18n_manager


def t(key: str, namespace: str = "default", **kwargs) -> str:
    """翻译文本"""
    return _global_i18n_manager.translate(key, namespace, **kwargs)


def tp(key: str, count: int, namespace: str = "default", **kwargs) -> str:
    """翻译复数形式"""
    return _global_i18n_manager.translate_plural(key, count, namespace, **kwargs)


def set_language(language: LanguageCode) -> bool:
    """设置语言"""
    return _global_i18n_manager.set_current_language(language)


def get_current_language() -> LanguageCode:
    """获取当前语言"""
    return _global_i18n_manager.get_current_language()
