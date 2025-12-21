"""
全局配置管理器
提供统一的配置访问接口和验证
"""

from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from src import __version__ as APP_VERSION

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误"""


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance: ConfigManager | None = None
    _config: dict[str, Any] = {}
    _config_file: Path | None = None
    _defaults: dict[str, Any] = {
        # 应用设置
        "app": {
            "name": "VirtualChemLab",
            "version": APP_VERSION,
            "language": "zh_CN",
            "theme": "auto",  # auto, light, dark
        },
        # UI设置
        "ui": {
            "window_width": 1280,
            "window_height": 800,
            "sidebar_width": 250,
            "font_size": 12,
            "enable_animations": True,
        },
        # 性能设置
        "performance": {
            "enable_virtual_list": True,
            "enable_lazy_loading": True,
            "debounce_delay": 300,
            "throttle_interval": 100,
            "memory_threshold_mb": 500,
        },
        # 开发者设置
        "developer": {
            "enable_console": False,
            "enable_debug_logs": False,
            "log_level": "INFO",
        },
        # 实验设置
        "experiment": {
            "auto_save": True,
            "auto_save_interval": 300,  # 秒
            "max_history": 50,
        },
    }

    def __new__(cls) -> ConfigManager:
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if not hasattr(self, "_initialized"):
            self._config = copy.deepcopy(self._defaults)
            self._max_config_bytes = int(
                os.environ.get("VCL_MAX_CONFIG_BYTES", "1048576")
            )
            self._initialized = True

    def load(self, config_file: str | Path) -> None:
        """
        加载配置文件

        Args:
            config_file: 配置文件路径
        """
        config_path = self._resolve_config_path(config_file)
        self._config_file = config_path

        try:
            if config_path.exists():
                self._enforce_file_size_limit(config_path)
                with open(config_path, encoding="utf-8") as f:
                    user_config = json.load(f)

                if not isinstance(user_config, dict):
                    raise ConfigError("配置文件内容必须为 JSON 对象")

                # 仅允许更新默认配置中存在的键，防止配置注入
                user_config = self._filter_by_whitelist(user_config, self._defaults)

                # 深度合并配置
                self._config = self._deep_merge(copy.deepcopy(self._defaults), user_config)

                # 强制验证配置
                errors = self.validate()
                if errors:
                    raise ConfigError("配置验证失败: " + "; ".join(errors))

                logger.info(f"配置加载成功: {config_path}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
                # 使用默认配置即可；避免在 load() 中强制写盘导致不必要的失败/副作用。
                try:
                    self.save()
                except ConfigError as exc:
                    logger.warning("默认配置写入失败，继续使用内存默认配置: %s", exc)
        except json.JSONDecodeError as e:
            msg = f"配置文件格式错误: {e}"
            logger.error(msg)
            raise ConfigError(msg) from e
        except Exception as e:
            msg = f"加载配置失败: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def save(self) -> None:
        """保存配置到文件"""
        if not self._config_file:
            logger.warning("未指定配置文件，无法保存")
            return

        try:
            # 强制验证配置
            errors = self.validate()
            if errors:
                raise ConfigError("配置验证失败: " + "; ".join(errors))

            # 强制路径限制到 user_data/ 目录
            self._config_file = self._resolve_config_path(self._config_file)

            # 确保目录存在
            self._config_file.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._config, indent=2, ensure_ascii=False)
            encoded = content.encode("utf-8")
            if len(encoded) > self._max_config_bytes:
                raise ConfigError(
                    f"配置内容过大（{len(encoded)} bytes），超过限制（{self._max_config_bytes} bytes）"
                )

            # 原子写入：临时文件 + os.replace（同目录）
            tmp_dir = str(self._config_file.parent)
            fd, tmp_path_str = tempfile.mkstemp(
                prefix=self._config_file.name + ".",
                suffix=".tmp",
                dir=tmp_dir,
            )
            tmp_path = Path(tmp_path_str)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(encoded)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self._config_file)
            finally:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass

            logger.info(f"配置保存成功: {self._config_file}")
        except Exception as e:
            msg = f"保存配置失败: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）

        Args:
            key: 配置键，支持 "app.name" 格式
            default: 默认值

        Returns:
            配置值
        """
        try:
            keys = key.split(".")
            value = self._config

            for k in keys:
                value = value[k]

            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        设置配置值（支持点号路径）

        Args:
            key: 配置键，支持 "app.name" 格式
            value: 配置值
            save: 是否立即保存到文件
        """
        try:
            if not self._is_key_allowed(key):
                raise ConfigError(f"不允许的配置键: {key}")

            candidate_config = copy.deepcopy(self._config)
            keys = key.split(".")
            config = candidate_config

            # 导航到最后一个键的父级
            for k in keys[:-1]:
                if k not in config or not isinstance(config[k], dict):
                    raise ConfigError(f"无效的配置路径: {key}")
                config = config[k]

            # 设置值
            config[keys[-1]] = value
            logger.debug(f"配置已更新: {key} = {value}")

            # 强制验证配置（不通过则不提交）
            previous_config = self._config
            self._config = candidate_config
            errors = self.validate()
            if errors:
                self._config = previous_config
                raise ConfigError("配置验证失败: " + "; ".join(errors))

            if save:
                self.save()
        except Exception as e:
            msg = f"设置配置失败: {key} = {value}, 错误: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def reset(self, key: str | None = None) -> None:
        """
        重置配置为默认值

        Args:
            key: 要重置的配置键，None表示重置全部
        """
        if key is None:
            self._config = copy.deepcopy(self._defaults)
            logger.info("所有配置已重置为默认值")
        else:
            default_value = self._get_from_defaults(key)
            if default_value is not None:
                self.set(key, default_value, save=False)
                logger.info(f"配置已重置: {key}")
            else:
                logger.warning(f"未找到默认配置: {key}")

    def validate(self) -> list[str]:
        """
        验证配置

        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []

        # 验证窗口尺寸
        width = self.get("ui.window_width")
        height = self.get("ui.window_height")
        if not isinstance(width, int) or width < 800:
            errors.append("ui.window_width 必须是大于等于800的整数")
        if not isinstance(height, int) or height < 600:
            errors.append("ui.window_height 必须是大于等于600的整数")

        # 验证主题
        theme = self.get("app.theme")
        if theme not in ["auto", "light", "dark"]:
            errors.append("app.theme 必须是 'auto', 'light' 或 'dark'")

        # 验证语言
        language = self.get("app.language")
        if not isinstance(language, str) or not language:
            errors.append("app.language 必须是非空字符串")

        # 验证性能参数
        memory_threshold = self.get("performance.memory_threshold_mb")
        if not isinstance(memory_threshold, (int, float)) or memory_threshold <= 0:
            errors.append("performance.memory_threshold_mb 必须是正数")

        debounce_delay = self.get("performance.debounce_delay")
        if not isinstance(debounce_delay, int) or debounce_delay < 0:
            errors.append("performance.debounce_delay 必须是非负整数")

        return errors

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """
        深度合并字典

        Args:
            base: 基础字典
            update: 更新字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_from_defaults(self, key: str) -> Any:
        """从默认配置中获取值"""
        try:
            keys = key.split(".")
            value = self._defaults

            for k in keys:
                value = value[k]

            return value
        except (KeyError, TypeError):
            return None

    def export(self) -> dict[str, Any]:
        """
        导出配置为字典

        Returns:
            配置字典
        """
        return copy.deepcopy(self._config)

    def import_config(self, config: dict[str, Any], merge: bool = True) -> None:
        """
        导入配置

        Args:
            config: 配置字典
            merge: 是否与现有配置合并
        """
        if not isinstance(config, dict):
            raise ConfigError("导入配置必须为字典")

        # 仅允许默认配置内的键（白名单），防止注入
        filtered = self._filter_by_whitelist(config, self._defaults)

        if merge:
            candidate_config = self._deep_merge(copy.deepcopy(self._config), filtered)
        else:
            # “替换”也必须保持默认配置结构，否则 validate() 会失败
            candidate_config = self._deep_merge(copy.deepcopy(self._defaults), filtered)

        previous_config = self._config
        self._config = candidate_config
        errors = self.validate()
        if errors:
            self._config = previous_config
            raise ConfigError("配置验证失败: " + "; ".join(errors))

        if merge:
            self._config = candidate_config
        else:
            self._config = candidate_config

        logger.info("配置已导入")

    def _get_user_data_dir(self) -> Path:
        override = os.environ.get("VCL_USER_DATA_DIR")
        if override:
            return Path(override).expanduser().resolve()
        project_root = Path(__file__).resolve().parents[2]
        return (project_root / "user_data").resolve()

    def _resolve_config_path(self, config_file: str | Path) -> Path:
        base_dir = self._get_user_data_dir()
        path = Path(config_file)
        if not path.is_absolute():
            path = base_dir / path
        resolved = path.expanduser().resolve()
        try:
            resolved.relative_to(base_dir)
        except ValueError as e:
            raise ConfigError(f"配置文件路径必须位于 {base_dir} 目录内") from e
        return resolved

    def _enforce_file_size_limit(self, config_path: Path) -> None:
        try:
            size = config_path.stat().st_size
        except OSError as e:
            raise ConfigError(f"无法读取配置文件大小: {e}") from e
        if size > self._max_config_bytes:
            raise ConfigError(
                f"配置文件过大（{size} bytes），超过限制（{self._max_config_bytes} bytes）"
            )

    def _filter_by_whitelist(self, incoming: dict[str, Any], whitelist: dict[str, Any]) -> dict[str, Any]:
        filtered: dict[str, Any] = {}
        for key, value in incoming.items():
            if key not in whitelist:
                logger.warning("忽略未允许的配置键: %s", key)
                continue
            allowed_value = whitelist[key]
            if isinstance(allowed_value, dict) and isinstance(value, dict):
                filtered[key] = self._filter_by_whitelist(value, allowed_value)
            else:
                filtered[key] = value
        return filtered

    def _is_key_allowed(self, dotted_key: str) -> bool:
        keys = dotted_key.split(".")
        node: Any = self._defaults
        for idx, key in enumerate(keys):
            if not isinstance(node, dict) or key not in node:
                return False
            node = node[key]
            if idx < len(keys) - 1 and not isinstance(node, dict):
                return False
        return True


# 全局单例
_config_manager: ConfigManager | None = None


def get_config() -> ConfigManager:
    """
    获取全局配置管理器实例

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便捷函数
def load_config(config_file: str | Path) -> None:
    """加载配置文件"""
    get_config().load(config_file)


def get_setting(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return get_config().get(key, default)


def set_setting(key: str, value: Any, save: bool = True) -> None:
    """设置配置值"""
    get_config().set(key, value, save)


if __name__ == "__main__":  # pragma: no cover
    """测试配置管理器"""
    import tempfile

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        test_config_file = f.name

    # 测试配置管理器
    config = get_config()
    config.load(test_config_file)

    # 测试获取配置
    print("App Name:", config.get("app.name"))
    print("Window Width:", config.get("ui.window_width"))

    # 测试设置配置
    config.set("app.theme", "dark", save=False)
    print("Theme after set:", config.get("app.theme"))

    # 测试验证
    errors = config.validate()
    print("Validation errors:", errors)

    # 保存配置
    config.save()
    logger.info(f"配置已保存到: {test_config_file}")

    # 清理
    import os

    os.unlink(test_config_file)
