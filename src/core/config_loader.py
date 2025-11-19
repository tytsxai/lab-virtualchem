"""
统一配置加载器
支持多环境配置和环境变量
"""

import json
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src import __version__ as APP_VERSION

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PathsConfig(BaseModel):
    """路径配置"""

    templates: str = Field(default="assets/templates")
    knowledge: str = Field(default="assets/knowledge")
    i18n: str = Field(default="assets/i18n")
    user_data: str = Field(default="user_data")
    reports: str = Field(default="reports")
    logs: str = Field(default="logs")

    @field_validator("*", mode="before")
    @classmethod
    def validate_path(cls, v: Any) -> str:
        """验证路径格式"""
        if not isinstance(v, str):
            raise ValueError(f"路径必须是字符串: {v}")
        return v


class DatabaseConfig(BaseModel):
    """数据库配置"""

    type: Literal["sqlite", "tinydb", "postgresql"] = "sqlite"
    path: str | None = "data/virtualchemlab.db"
    url: str | None = None
    pool_size: int = 10
    pool_max_overflow: int = 20

    @model_validator(mode="after")
    def set_url(self) -> "DatabaseConfig":
        """自动设置数据库URL"""
        if not self.url:
            self.url = f"{self.type}:///{self.path}"
        return self


class RedisConfig(BaseModel):
    """Redis配置"""

    enabled: bool = False
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None


class CacheConfig(BaseModel):
    """缓存配置"""

    enabled: bool = True
    default_ttl: int = 300
    max_size: int = 1000
    backend: Literal["memory", "redis"] = "memory"


class SecurityConfig(BaseModel):
    """安全配置"""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    developer_key_hash: str | None = None
    jwt_secret_env: str = "JWT_SECRET_KEY"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """验证JWT密钥"""
        if not v or v == "change-this-in-production":
            raise ValueError("JWT密钥未设置或使用默认值！请在环境变量中设置 JWT_SECRET_KEY")
        if len(v) < 32:
            raise ValueError("JWT密钥长度必须至少32个字符")
        return v


class MonitoringConfig(BaseModel):
    """监控配置"""

    enabled: bool = True
    performance_tracking: bool = True
    error_tracking: bool = True
    health_check_interval: int = 60


class LogConfig(BaseModel):
    """日志配置"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    file: str = "logs/app.log"
    max_size: int = 10485760  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class AppConfig(BaseModel):
    """应用配置"""

    name: str = "VirtualChemLab"
    version: str = "2.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    port: int = 8000

    @model_validator(mode="after")
    def set_debug(self) -> "AppConfig":
        """根据环境自动设置debug"""
        if self.environment == "production":
            self.debug = False
        # 保持用户显式设置的debug值，不自动覆盖
        return self


class Config(BaseModel):
    """主配置类"""

    app: AppConfig = Field(default_factory=AppConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig(jwt_secret_key=secrets.token_urlsafe(48)))
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    log: LogConfig = Field(default_factory=LogConfig)

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",  # 允许额外字段
    )

    @classmethod
    def load(cls, env: str | None = None) -> "Config":
        """加载配置

        Args:
            env: 环境名称 (development/staging/production)
                 如果不指定，从环境变量 ENVIRONMENT 读取

        Returns:
            Config: 配置对象
        """
        # 1. 确定环境
        environment = env if env is not None else os.getenv("ENVIRONMENT", "development") or "development"

        # 2. 加载环境变量 (优先级最高)
        load_env_file()

        # 3. 加载配置文件
        config_data = cls._load_config_file(environment)

        # 4. 合并环境变量
        config_data = cls._merge_env_vars(config_data, environment_override=environment)

        # 5. 对齐版本号
        config_data = cls._ensure_version_alignment(config_data)

        # 6. 准备运行环境（创建目录等）
        cls._prepare_runtime_environment(config_data)

        # 7. 验证并返回
        return cls(**config_data)

    @classmethod
    def _load_config_file(cls, environment: str) -> dict[str, Any]:
        """加载配置文件（简化版）"""
        config_dir = Path("config")

        # 配置加载优先级列表
        config_files = [
            config_dir / f"{environment}.json",  # 环境特定配置
            config_dir / "base.json",            # 基础配置
            Path("config.json"),                 # 旧配置文件
        ]

        for config_file in config_files:
            try:
                if config_file.exists():
                    with open(config_file, encoding="utf-8") as f:
                        config_data = json.load(f)
                        logger.info(f"加载配置文件: {config_file}")
                        return config_data
            except Exception as e:
                logger.warning(f"加载配置文件失败 {config_file}: {e}")
                continue

        # 所有配置文件都失败，返回默认配置
        logger.info("使用默认配置")
        return cls._get_default_config()

    @classmethod
    def _merge_env_vars(cls, config_data: dict[str, Any], environment_override: str | None = None) -> dict[str, Any]:
        """合并环境变量 (优先级高于配置文件)"""
        # 应用配置
        if not config_data.get("app"):
            config_data["app"] = {}
        if environment_override is not None:
            config_data["app"]["environment"] = environment_override
        elif "environment" not in config_data["app"]:
            env_override = os.getenv("ENVIRONMENT")
            if env_override:
                config_data["app"]["environment"] = env_override
            else:
                config_data["app"]["environment"] = "development"

        debug_override = os.getenv("DEBUG")
        if debug_override is not None:
            config_data["app"]["debug"] = debug_override.lower() in ("true", "1", "yes", "on")
        else:
            config_data["app"].setdefault("debug", False)

        # 安全配置
        security_cfg = config_data.setdefault("security", {})
        env_override = os.getenv("JWT_SECRET_ENV")
        secret_env_name = env_override or security_cfg.get("jwt_secret_env") or "JWT_SECRET_KEY"
        security_cfg["jwt_secret_env"] = secret_env_name

        jwt_secret = os.getenv(secret_env_name) or os.getenv("JWT_SECRET_KEY") or security_cfg.get("jwt_secret_key")
        if jwt_secret:
            security_cfg["jwt_secret_key"] = jwt_secret
        else:
            env = config_data["app"]["environment"]
            if env == "production":
                raise ValueError(f"生产环境必须设置 JWT 密钥环境变量 ({secret_env_name})")
            generated_secret = secrets.token_urlsafe(48)
            security_cfg["jwt_secret_key"] = generated_secret
            logger.warning("未配置JWT密钥，已为%s环境生成临时密钥，仅用于本次运行", env)

        # 开发者密钥
        dev_key = os.getenv("DEVELOPER_KEY_HASH")
        if dev_key:
            security_cfg["developer_key_hash"] = dev_key

        # 管理后台密钥环境变量校验
        developer_cfg = config_data.setdefault("developer", {})
        admin_env_override = os.getenv("ADMIN_SECRET_ENV")
        admin_secret_env = developer_cfg.get("admin_secret_env") or admin_env_override or "VCL_ADMIN_SECRET_KEY"
        developer_cfg["admin_secret_env"] = admin_secret_env
        if config_data["app"]["environment"] == "production" and not os.getenv(admin_secret_env):
            raise ValueError(f"生产环境必须设置管理后台密钥环境变量 ({admin_secret_env})")

        # 数据库配置
        if not config_data.get("database"):
            config_data["database"] = {}
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            config_data["database"]["url"] = db_url

        # Redis配置
        if not config_data.get("redis"):
            config_data["redis"] = {}
        config_data["redis"]["enabled"] = (
            os.getenv("REDIS_ENABLED", str(config_data["redis"].get("enabled", False))).lower() == "true"
        )

        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            config_data["redis"]["host"] = redis_host

        # 缓存配置
        if not config_data.get("cache"):
            config_data["cache"] = {}
        config_data["cache"]["enabled"] = (
            os.getenv("CACHE_ENABLED", str(config_data["cache"].get("enabled", True))).lower() == "true"
        )

        # 监控配置
        if not config_data.get("monitoring"):
            config_data["monitoring"] = {}
        config_data["monitoring"]["enabled"] = (
            os.getenv("MONITORING_ENABLED", str(config_data["monitoring"].get("enabled", True))).lower() == "true"
        )

        # 日志配置
        if not config_data.get("log"):
            config_data["log"] = {}
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            config_data["log"]["level"] = log_level.upper()

        # 路径配置
        if not config_data.get("paths"):
            config_data["paths"] = {}
        for path_key in ["templates", "knowledge", "user_data", "reports"]:
            env_key = f"{path_key.upper()}_DIR"
            env_value = os.getenv(env_key)
            if env_value:
                config_data["paths"][path_key] = env_value

        return config_data

    @classmethod
    def _ensure_version_alignment(cls, config_data: dict[str, Any]) -> dict[str, Any]:
        """确保配置版本与应用版本保持一致"""
        app_config = config_data.setdefault("app", {})
        file_version = app_config.get("version")

        if file_version and file_version != APP_VERSION:
            logger.warning(
                "配置文件版本(%s)与应用版本(%s)不一致，已自动对齐",
                file_version,
                APP_VERSION,
            )

        app_config["version"] = APP_VERSION
        return config_data

    @classmethod
    def _prepare_runtime_environment(cls, config_data: dict[str, Any]) -> None:
        """确保运行所需的目录存在"""
        root = PROJECT_ROOT
        paths_cfg = config_data.get("paths", {})

        # 仅为可写目录自动建目录
        writable_keys = ("user_data", "reports", "logs")
        for key in writable_keys:
            path_value = paths_cfg.get(key)
            if path_value:
                cls._ensure_directory(root / path_value, f"paths.{key}")

        # 日志文件所在目录
        log_cfg = config_data.get("log", {})
        log_file = log_cfg.get("file")
        if log_file:
            cls._ensure_directory((root / log_file).parent, "log.file")

        # 存储目录
        storage_cfg = config_data.get("storage", {})
        storage_base = storage_cfg.get("base_path")
        if storage_base:
            cls._ensure_directory(root / storage_base, "storage.base_path")

        # 数据库文件目录
        db_cfg = config_data.get("database", {})
        db_path = db_cfg.get("path")
        if db_path:
            cls._ensure_directory((root / db_path).parent, "database.path")

    @staticmethod
    def _ensure_directory(path: Path, source: str) -> None:
        """创建必需目录"""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("创建目录失败 [%s]: %s (%s)", source, path, exc)
            raise

    @classmethod
    def _get_default_config(cls) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": "2.0.0",
                "environment": "development",
                "debug": True,
            },
            "paths": {
                "templates": "assets/templates",
                "knowledge": "assets/knowledge",
                "i18n": "assets/i18n",
                "user_data": "user_data",
                "reports": "reports",
            },
            "database": {"type": "sqlite", "path": "data/virtualchemlab.db"},
            "redis": {"enabled": False, "host": "localhost", "port": 6379},
            "cache": {"enabled": True, "default_ttl": 300, "max_size": 1000},
            "security": {
                "jwt_algorithm": "HS256",
                "jwt_expiration": 3600,
            },
            "monitoring": {"enabled": True, "performance_tracking": True, "error_tracking": True},
            "log": {
                "level": "INFO",
                "file": "logs/app.log",
                "max_size": 10485760,
                "backup_count": 5,
            },
        }


def load_env_file(env_file: str = ".env") -> None:
    """加载环境变量文件

    Args:
        env_file: 环境变量文件路径
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 解析 KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                # 设置环境变量 (不覆盖已存在的)
                if key and key not in os.environ:
                    os.environ[key] = value


# 全局配置实例 (懒加载，线程安全)
_config: Config | None = None
_config_lock = threading.Lock()


def get_config() -> Config:
    """获取全局配置实例（线程安全）

    Returns:
        Config: 配置对象
    """
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:  # 双重检查锁
                _config = Config.load()
    return _config


def reload_config(env: str | None = None) -> None:
    """重新加载配置

    Args:
        env: 环境名称
    """
    global _config
    _config = Config.load(env)


class ConfigAdapter:
    """配置适配器，将新Config适配到旧的IConfig接口

    用于向后兼容，使得旧代码可以无缝使用新配置系统
    """

    def __init__(self, _config: Config):
        self._config = _config

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）

        Examples:
            config.get("app.environment")
            config.get("database.host", "localhost")
        """
        parts = key.split(".")
        value = self._config

        try:
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            return value
        except (AttributeError, KeyError):
            return default

    def set(self, key: str, _value: Any) -> None:
        """设置配置值（新配置系统不支持运行时修改）"""
        logger.warning(f"ConfigAdapter.set() 不支持修改配置: {key}. 新配置系统是只读的，请在配置文件或环境变量中修改。")

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return self.get(key) is not None

    def get_section(self, _section: str) -> dict[str, Any]:
        """获取配置节"""
        value = self.get(_section)
        if value is None:
            return {}

        # 如果是Pydantic模型，转为字典
        if hasattr(value, "dict"):
            return value.dict()

        return value if isinstance(value, dict) else {}

    def reload(self) -> None:
        """重新加载配置"""
        reload_config()
        self._config = get_config()


def create_legacy_config() -> Any:
    """创建兼容旧接口的配置对象

    Returns:
        ConfigAdapter: 适配到IConfig接口的配置对象
    """
    config = get_config()
    return ConfigAdapter(config)


if __name__ == "__main__":
    # 测试配置加载
    try:
        config = Config.load()
        logger.info("✅ 配置加载成功！")
        logger.info(f"环境: {config.app.environment}")
        logger.info(f"调试模式: {config.app.debug}")
        logger.info(f"数据库: {config.database.url}")
        logger.info(f"Redis: {'启用' if config.redis.enabled else '禁用'}")
        logger.info(f"缓存: {'启用' if config.cache.enabled else '禁用'}")
        logger.info(f"日志级别: {config.log.level}")
    except Exception as e:
        logger.info(f"❌ 配置加载失败: {e}")
