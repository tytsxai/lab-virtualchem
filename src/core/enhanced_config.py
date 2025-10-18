"""
增强配置管理
统一管理新增功能的配置项
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceConfig:
    """性能监控配置"""

    enabled: bool = True
    update_interval_ms: int = 1000
    max_history_size: int = 300
    adaptive_sampling: bool = True
    gpu_monitoring: bool = True
    network_monitoring: bool = True
    disk_monitoring: bool = True
    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "fps": 30.0,
            "frame_time_ms": 33.33,
            "gpu_usage": 90.0,
            "memory_fragmentation": 50.0,
        }
    )


@dataclass
class ErrorHandlingConfig:
    """错误处理配置"""

    enabled: bool = True
    global_handler: bool = True
    log_errors: bool = True
    show_user_notifications: bool = True
    auto_recovery: bool = True
    thresholds: dict[str, int] = field(
        default_factory=lambda: {
            "system": 5,
            "network": 10,
            "file_io": 15,
            "user_input": 20,
            "configuration": 3,
            "performance": 8,
            "security": 1,
            "unknown": 25,
        }
    )


@dataclass
class TutorialConfig:
    """教程系统配置"""

    enabled: bool = True
    auto_start: bool = False
    progress_saving: bool = True
    personalized_content: bool = True
    difficulty_adaptation: bool = True
    progress_file: str = "data/tutorial_progress.json"
    default_difficulty: str = "medium"
    default_learning_style: str = "visual"


@dataclass
class HelpSystemConfig:
    """帮助系统配置"""

    enabled: bool = True
    search_enabled: bool = True
    fuzzy_search: bool = True
    multimedia_support: bool = True
    offline_mode: bool = True
    cache_enabled: bool = True
    cache_size_mb: int = 50


@dataclass
class EnhancedConfig:
    """增强配置主类"""

    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    tutorial: TutorialConfig = field(default_factory=TutorialConfig)
    help_system: HelpSystemConfig = field(default_factory=HelpSystemConfig)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "performance": {
                "enabled": self.performance.enabled,
                "update_interval_ms": self.performance.update_interval_ms,
                "max_history_size": self.performance.max_history_size,
                "adaptive_sampling": self.performance.adaptive_sampling,
                "gpu_monitoring": self.performance.gpu_monitoring,
                "network_monitoring": self.performance.network_monitoring,
                "disk_monitoring": self.performance.disk_monitoring,
                "thresholds": self.performance.thresholds,
            },
            "error_handling": {
                "enabled": self.error_handling.enabled,
                "global_handler": self.error_handling.global_handler,
                "log_errors": self.error_handling.log_errors,
                "show_user_notifications": self.error_handling.show_user_notifications,
                "auto_recovery": self.error_handling.auto_recovery,
                "thresholds": self.error_handling.thresholds,
            },
            "tutorial": {
                "enabled": self.tutorial.enabled,
                "auto_start": self.tutorial.auto_start,
                "progress_saving": self.tutorial.progress_saving,
                "personalized_content": self.tutorial.personalized_content,
                "difficulty_adaptation": self.tutorial.difficulty_adaptation,
                "progress_file": self.tutorial.progress_file,
                "default_difficulty": self.tutorial.default_difficulty,
                "default_learning_style": self.tutorial.default_learning_style,
            },
            "help_system": {
                "enabled": self.help_system.enabled,
                "search_enabled": self.help_system.search_enabled,
                "fuzzy_search": self.help_system.fuzzy_search,
                "multimedia_support": self.help_system.multimedia_support,
                "offline_mode": self.help_system.offline_mode,
                "cache_enabled": self.help_system.cache_enabled,
                "cache_size_mb": self.help_system.cache_size_mb,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnhancedConfig":
        """从字典创建"""
        config = cls()

        # 性能配置
        if "performance" in data:
            perf_data = data["performance"]
            config.performance.enabled = perf_data.get("enabled", True)
            config.performance.update_interval_ms = perf_data.get("update_interval_ms", 1000)
            config.performance.max_history_size = perf_data.get("max_history_size", 300)
            config.performance.adaptive_sampling = perf_data.get("adaptive_sampling", True)
            config.performance.gpu_monitoring = perf_data.get("gpu_monitoring", True)
            config.performance.network_monitoring = perf_data.get("network_monitoring", True)
            config.performance.disk_monitoring = perf_data.get("disk_monitoring", True)
            config.performance.thresholds = perf_data.get("thresholds", config.performance.thresholds)

        # 错误处理配置
        if "error_handling" in data:
            error_data = data["error_handling"]
            config.error_handling.enabled = error_data.get("enabled", True)
            config.error_handling.global_handler = error_data.get("global_handler", True)
            config.error_handling.log_errors = error_data.get("log_errors", True)
            config.error_handling.show_user_notifications = error_data.get("show_user_notifications", True)
            config.error_handling.auto_recovery = error_data.get("auto_recovery", True)
            config.error_handling.thresholds = error_data.get("thresholds", config.error_handling.thresholds)

        # 教程配置
        if "tutorial" in data:
            tutorial_data = data["tutorial"]
            config.tutorial.enabled = tutorial_data.get("enabled", True)
            config.tutorial.auto_start = tutorial_data.get("auto_start", False)
            config.tutorial.progress_saving = tutorial_data.get("progress_saving", True)
            config.tutorial.personalized_content = tutorial_data.get("personalized_content", True)
            config.tutorial.difficulty_adaptation = tutorial_data.get("difficulty_adaptation", True)
            config.tutorial.progress_file = tutorial_data.get("progress_file", "data/tutorial_progress.json")
            config.tutorial.default_difficulty = tutorial_data.get("default_difficulty", "medium")
            config.tutorial.default_learning_style = tutorial_data.get("default_learning_style", "visual")

        # 帮助系统配置
        if "help_system" in data:
            help_data = data["help_system"]
            config.help_system.enabled = help_data.get("enabled", True)
            config.help_system.search_enabled = help_data.get("search_enabled", True)
            config.help_system.fuzzy_search = help_data.get("fuzzy_search", True)
            config.help_system.multimedia_support = help_data.get("multimedia_support", True)
            config.help_system.offline_mode = help_data.get("offline_mode", True)
            config.help_system.cache_enabled = help_data.get("cache_enabled", True)
            config.help_system.cache_size_mb = help_data.get("cache_size_mb", 50)

        return config


class EnhancedConfigManager:
    """增强配置管理器"""

    def __init__(self, config_file: str = "data/enhanced_config.json"):
        self.config_file = Path(config_file)
        self.config = EnhancedConfig()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置"""
        try:
            if self.config_file.exists():
                import json

                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = EnhancedConfig.from_dict(data)
                logger.info("增强配置已加载")
            else:
                self._save_config()
                logger.info("创建默认增强配置")
        except Exception as e:
            logger.error(f"加载增强配置失败: {e}")

    def _save_config(self) -> None:
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            import json

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("增强配置已保存")
        except Exception as e:
            logger.error(f"保存增强配置失败: {e}")

    def get_config(self) -> EnhancedConfig:
        """获取配置"""
        return self.config

    def update_config(self, config: EnhancedConfig) -> None:
        """更新配置"""
        self.config = config
        self._save_config()

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = EnhancedConfig()
        self._save_config()
        logger.info("配置已重置为默认值")


# 全局配置管理器实例
_config_manager: EnhancedConfigManager | None = None


def get_enhanced_config_manager() -> EnhancedConfigManager:
    """获取全局增强配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = EnhancedConfigManager()
    return _config_manager
