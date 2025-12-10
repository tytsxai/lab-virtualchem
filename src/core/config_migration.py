"""
配置迁移系统
提供配置版本管理、自动迁移和兼容性处理
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src import __version__ as APP_VERSION
from .common_exceptions import ConfigurationError
from .error_handler import get_error_handler
from .unified_config_manager import UnifiedConfigManager

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """迁移步骤"""
    from_version: str
    to_version: str
    description: str
    migration_function: callable
    rollback_function: Optional[callable] = None
    required: bool = True


@dataclass
class ConfigVersion:
    """配置版本"""
    version: str
    schema: Dict[str, Any]
    migration_steps: List[MigrationStep] = field(default_factory=list)
    deprecated_keys: List[str] = field(default_factory=list)
    new_keys: List[str] = field(default_factory=list)


class ConfigMigrationManager:
    """配置迁移管理器"""

    def __init__(self, config_manager: UnifiedConfigManager):
        self._config_manager = config_manager
        self._versions: Dict[str, ConfigVersion] = {}
        self._current_version = APP_VERSION
        self._error_handler = get_error_handler()

        # 迁移统计
        self._stats = {
            "migrations_performed": 0,
            "migrations_failed": 0,
            "rollbacks_performed": 0,
            "rollbacks_failed": 0
        }

        # 初始化默认版本
        self._setup_default_versions()

    def _setup_default_versions(self) -> None:
        """设置默认版本"""
        # 版本 1.0.0 - 基础版本
        v1_schema = {
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "environment": {"type": "string"}
                    },
                    "required": ["name", "version", "environment"]
                }
            },
            "required": ["app"]
        }

        self._versions["1.0.0"] = ConfigVersion(
            version="1.0.0",
            schema=v1_schema
        )

        # 版本 2.0.0 - 增强版本
        v2_schema = {
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "environment": {"type": "string"},
                        "debug": {"type": "boolean"},
                        "log_level": {"type": "string"}
                    },
                    "required": ["name", "version", "environment"]
                },
                "ui": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string"},
                        "language": {"type": "string"},
                        "font_size": {"type": "integer"}
                    }
                },
                "performance": {
                    "type": "object",
                    "properties": {
                        "enable_caching": {"type": "boolean"},
                        "cache_size": {"type": "integer"}
                    }
                }
            },
            "required": ["app"]
        }

        # 迁移步骤：1.0.0 -> 2.0.0
        migration_step = MigrationStep(
            from_version="1.0.0",
            to_version="2.0.0",
            description="添加UI和性能配置",
            migration_function=self._migrate_1_0_to_2_0,
            rollback_function=self._rollback_2_0_to_1_0
        )

        self._versions["2.0.0"] = ConfigVersion(
            version="2.0.0",
            schema=v2_schema,
            migration_steps=[migration_step],
            new_keys=["ui", "performance"]
        )

        if APP_VERSION != "2.0.0":
            migrate_to_current = MigrationStep(
                from_version="2.0.0",
                to_version=APP_VERSION,
                description=f"同步配置版本到 {APP_VERSION}",
                migration_function=self._migrate_2_0_to_current,
                rollback_function=self._rollback_current_to_2_0,
                required=False,
            )
            self._versions[APP_VERSION] = ConfigVersion(
                version=APP_VERSION,
                schema=v2_schema,
                migration_steps=[migrate_to_current],
                new_keys=["ui", "performance"],
            )

    def _migrate_1_0_to_2_0(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """迁移 1.0.0 -> 2.0.0"""
        logger.info("Migrating config from 1.0.0 to 2.0.0")

        # 添加默认UI配置
        if "ui" not in config_data:
            config_data["ui"] = {
                "theme": "auto",
                "language": "zh_CN",
                "font_size": 12
            }

        # 添加默认性能配置
        if "performance" not in config_data:
            config_data["performance"] = {
                "enable_caching": True,
                "cache_size": 1000
            }

        # 添加调试配置
        if "app" in config_data and "debug" not in config_data["app"]:
            config_data["app"]["debug"] = False

        if "app" in config_data and "log_level" not in config_data["app"]:
            config_data["app"]["log_level"] = "INFO"

        return config_data

    def _rollback_2_0_to_1_0(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """回滚 2.0.0 -> 1.0.0"""
        logger.info("Rolling back config from 2.0.0 to 1.0.0")

        # 移除新增的配置节
        config_data.pop("ui", None)
        config_data.pop("performance", None)

        # 移除新增的app配置
        if "app" in config_data:
            config_data["app"].pop("debug", None)
            config_data["app"].pop("log_level", None)

        return config_data

    def _migrate_2_0_to_current(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """迁移 2.0.0 -> 当前应用版本（占位迁移）"""
        logger.info("Migrating config from 2.0.0 to %s", APP_VERSION)
        config_data.setdefault("app", {})
        config_data["app"]["version"] = APP_VERSION
        return config_data

    def _rollback_current_to_2_0(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """回滚 当前版本 -> 2.0.0（占位回滚）"""
        logger.info("Rolling back config from %s to 2.0.0", APP_VERSION)
        config_data.setdefault("app", {})
        config_data["app"]["version"] = "2.0.0"
        return config_data

    def register_version(self, version: ConfigVersion) -> None:
        """注册配置版本"""
        self._versions[version.version] = version
        logger.debug(f"Registered config version: {version.version}")

    def get_version(self, version: str) -> Optional[ConfigVersion]:
        """获取配置版本"""
        return self._versions.get(version)

    def get_current_version(self) -> str:
        """获取当前版本"""
        return self._current_version

    def set_current_version(self, version: str) -> None:
        """设置当前版本"""
        if version not in self._versions:
            raise ConfigurationError(f"Unknown config version: {version}")
        self._current_version = version

    def detect_config_version(self, config_data: Dict[str, Any]) -> str:
        """检测配置版本"""
        # 检查是否有版本信息
        if "app" in config_data and "version" in config_data["app"]:
            return config_data["app"]["version"]

        # 根据配置结构推断版本
        if "ui" in config_data or "performance" in config_data:
            return "2.0.0"
        else:
            return "1.0.0"

    def migrate_config(
        self,
        config_data: Dict[str, Any],
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """迁移配置"""
        if target_version is None:
            target_version = self._current_version

        current_version = self.detect_config_version(config_data)

        if current_version == target_version:
            logger.debug(f"Config already at target version {target_version}")
            return config_data

        logger.info(f"Migrating config from {current_version} to {target_version}")

        # 获取迁移路径
        migration_path = self._get_migration_path(current_version, target_version)

        if not migration_path:
            raise ConfigurationError(f"No migration path from {current_version} to {target_version}")

        # 执行迁移步骤
        migrated_data = config_data.copy()
        for step in migration_path:
            try:
                migrated_data = step.migration_function(migrated_data)
                self._stats["migrations_performed"] += 1
                logger.info(f"Migration step completed: {step.description}")
            except Exception as e:
                self._stats["migrations_failed"] += 1
                logger.error(f"Migration step failed: {step.description} - {e}")
                raise ConfigurationError(f"Migration failed: {e}") from e

        # 更新版本信息
        if "app" in migrated_data:
            migrated_data["app"]["version"] = target_version

        return migrated_data

    def _get_migration_path(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """获取迁移路径"""
        if from_version == to_version:
            return []

        # 简单的版本比较（假设版本号递增）
        from_ver = tuple(map(int, from_version.split('.')))
        to_ver = tuple(map(int, to_version.split('.')))

        if from_ver >= to_ver:
            # 需要回滚
            return self._get_rollback_path(from_version, to_version)
        else:
            # 需要升级
            return self._get_upgrade_path(from_version, to_version)

    def _get_upgrade_path(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """获取升级路径"""
        path = []
        current_version = from_version

        while current_version != to_version:
            # 查找下一个版本
            next_version = self._find_next_version(current_version)
            if not next_version:
                break

            # 获取迁移步骤
            version_info = self._versions.get(next_version)
            if version_info:
                for step in version_info.migration_steps:
                    if step.from_version == current_version:
                        path.append(step)
                        break

            current_version = next_version

        return path

    def _get_rollback_path(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """获取回滚路径"""
        path = []
        current_version = from_version

        while current_version != to_version:
            # 查找上一个版本
            prev_version = self._find_previous_version(current_version)
            if not prev_version:
                break

            # 获取回滚步骤
            version_info = self._versions.get(current_version)
            if version_info:
                for step in version_info.migration_steps:
                    if step.to_version == current_version and step.rollback_function:
                        path.append(step)
                        break

            current_version = prev_version

        return path

    def _find_next_version(self, current_version: str) -> Optional[str]:
        """查找下一个版本"""
        versions = sorted(self._versions.keys())
        try:
            current_index = versions.index(current_version)
            if current_index < len(versions) - 1:
                return versions[current_index + 1]
        except ValueError:
            pass
        return None

    def _find_previous_version(self, current_version: str) -> Optional[str]:
        """查找上一个版本"""
        versions = sorted(self._versions.keys())
        try:
            current_index = versions.index(current_version)
            if current_index > 0:
                return versions[current_index - 1]
        except ValueError:
            pass
        return None

    def validate_config_version(self, config_data: Dict[str, Any]) -> bool:
        """验证配置版本"""
        version = self.detect_config_version(config_data)
        version_info = self._versions.get(version)

        if not version_info:
            return False

        try:
            import jsonschema
            jsonschema.validate(config_data, version_info.schema)
            return True
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return False

    def backup_config(self, config_data: Dict[str, Any], backup_path: Path) -> None:
        """备份配置"""
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Config backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            raise

    def restore_config(self, backup_path: Path) -> Dict[str, Any]:
        """恢复配置"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            logger.info(f"Config restored from {backup_path}")
            return config_data
        except Exception as e:
            logger.error(f"Failed to restore config: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def clear_stats(self) -> None:
        """清除统计信息"""
        self._stats = {
            "migrations_performed": 0,
            "migrations_failed": 0,
            "rollbacks_performed": 0,
            "rollbacks_failed": 0
        }

    def get_version_history(self) -> List[str]:
        """获取版本历史"""
        return sorted(self._versions.keys())

    def get_migration_info(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """获取迁移信息"""
        path = self._get_migration_path(from_version, to_version)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "steps_count": len(path),
            "steps": [
                {
                    "description": step.description,
                    "required": step.required
                }
                for step in path
            ]
        }


# 全局配置迁移管理器实例
_global_config_migration = None


def get_config_migration_manager() -> ConfigMigrationManager:
    """获取全局配置迁移管理器"""
    global _global_config_migration
    if _global_config_migration is None:
        from .unified_config_manager import get_config_manager
        config_manager = get_config_manager()
        _global_config_migration = ConfigMigrationManager(config_manager)
    return _global_config_migration


def migrate_config(config_data: Dict[str, Any], target_version: Optional[str] = None) -> Dict[str, Any]:
    """迁移配置"""
    migration_manager = get_config_migration_manager()
    return migration_manager.migrate_config(config_data, target_version)


def detect_config_version(config_data: Dict[str, Any]) -> str:
    """检测配置版本"""
    migration_manager = get_config_migration_manager()
    return migration_manager.detect_config_version(config_data)
