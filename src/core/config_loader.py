"""Unified application configuration loader (source-of-truth for GUI startup).

This module provides a single, validated configuration object (`Config`) for
the GUI entrypoints and DI container wiring.

Key behaviors (maintenance-safety):
- Loads `.env` (if present) so local development can be configured without
  exporting shell variables.
- Merges config files in order: defaults → `config/base.json` → root `config.json`
  → `config/<environment>.json` → environment variables.
- Resolves a per-user runtime directory (default `~/.virtualchemlab`) so packaged
  apps can persist mutable data even when install locations are not writable.
- Secret handling:
  - Strict production (`ENVIRONMENT=production` and **not** `sys.frozen`) requires
    strong secrets (>=32 chars) and fails fast if missing/weak. Environment
    variables are the recommended delivery mechanism; config-file secrets are
    accepted but emit warnings (to discourage committing/persisting secrets in
    plaintext files).
  - Packaged builds (`sys.frozen`) default to production but are allowed to
    generate per-machine secrets and persist them under the runtime directory.
  - Admin API secret (`VCL_ADMIN_SECRET_KEY`) is validated by `src/api/admin_api.py`
    at Admin API startup, not here, to avoid blocking the GUI.

Note: the repository also contains lightweight/legacy config readers (e.g.
`src/utils/config.py`) used by some tools and the REST API; do not confuse them
with this module's security baseline.
"""

import json
import logging
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src import __version__ as APP_VERSION

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def _default_runtime_home() -> Path:
    """Default per-user writable runtime directory.

    Desktop packaged apps often run from non-writable install locations; keep
    mutable data under a stable per-user directory by default.
    """
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA") or str(Path.home())
        return Path(base) / ".virtualchemlab"
    return Path.home() / ".virtualchemlab"


DEFAULT_RUNTIME_HOME = _default_runtime_home()


def _user_config_path(runtime_root: Path | None = None) -> Path:
    """Resolve the user config.json path for desktop/runtime secrets."""
    explicit = (os.getenv("VCL_CONFIG_PATH") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    root = runtime_root or DEFAULT_RUNTIME_HOME
    return root / "config.json"


def _read_json_file(path: Path) -> dict[str, Any]:
    """Best-effort JSON loader for config merge.

    Returns an empty dict when the file is missing or invalid. This keeps config
    loading robust in end-user environments (packaged apps, first-run, etc.).
    """
    try:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON to disk (best-effort permission hardening)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
            suffix=".tmp",
        ) as f:
            tmp_path = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
        # Best-effort tighten permissions for secrets on POSIX.
        if os.name == "posix":
            try:
                os.chmod(str(path), 0o600)
            except Exception:  # noqa: BLE001
                pass
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:  # noqa: BLE001
                pass


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
            raise ValueError(
                "JWT密钥未设置或使用默认值！请在环境变量中设置 JWT_SECRET_KEY"
            )
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
    max_size: int = 10485760  # 10MB (bytes)
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class AppConfig(BaseModel):
    """应用配置"""

    name: str = "VirtualChemLab"
    version: str = APP_VERSION
    environment: Literal["development", "staging", "production"] = "development"
    language: str = "zh_CN"
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
    security: SecurityConfig = Field(
        default_factory=lambda: SecurityConfig(jwt_secret_key=secrets.token_urlsafe(48))
    )
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
        # 1. 加载环境变量 (优先级最高，允许 .env 中的 ENVIRONMENT 生效)
        load_env_file()

        # 2. 确定环境（尊重显式传参/环境变量，其次读取配置文件声明）
        environment = cls._detect_environment(env)

        # 3. 加载配置文件
        config_data = cls._load_config_file(environment)

        # 4. 合并环境变量
        config_data = cls._merge_env_vars(config_data, environment_override=environment)

        # 5. 对齐版本号
        config_data = cls._ensure_version_alignment(config_data)

        # 6. 统一语言代码格式（zh-CN -> zh_CN）
        config_data = cls._normalize_language_codes(config_data)

        # 7. 解析运行时数据目录（打包/不可写目录时自动落到用户目录）
        config_data = cls._apply_runtime_data_root(config_data)

        # 8. 准备运行环境（创建目录等）
        cls._prepare_runtime_environment(config_data)

        # 9. 验证并返回
        return cls(**config_data)

    @classmethod
    def _load_config_file(cls, environment: str) -> dict[str, Any]:
        """加载配置文件并深度合并（基础 -> 兼容配置 -> 环境覆盖）"""
        config_dir = CONFIG_DIR

        merged_config: dict[str, Any] = cls._get_default_config()
        found_any = False

        # 读取顺序：基础配置 -> 兼容旧版 config.json -> 环境特定配置
        config_files = [
            config_dir / "base.json",
            PROJECT_ROOT / "config.json",
            config_dir / f"{environment}.json",
        ]

        for config_file in config_files:
            if not config_file.exists():
                continue

            try:
                with open(config_file, encoding="utf-8") as f:
                    config_data = json.load(f)
                merged_config = cls._deep_merge(merged_config, config_data)
                found_any = True
                logger.info("加载配置文件: %s", config_file)
            except Exception as e:  # pragma: no cover - 防御性容错
                logger.warning("加载配置文件失败 %s: %s", config_file, e)

        if not found_any:
            logger.info("使用默认配置")

        return merged_config

    @classmethod
    def _merge_env_vars(
        cls, config_data: dict[str, Any], environment_override: str | None = None
    ) -> dict[str, Any]:
        """合并环境变量 (优先级高于配置文件)"""

        def _parse_bool(value: str | bool | None) -> bool:
            """将环境变量值解析为布尔值"""
            if isinstance(value, bool):
                return value
            if value is None:
                return False
            return str(value).lower() in ("true", "1", "yes", "on")

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
            config_data["app"]["debug"] = debug_override.lower() in (
                "true",
                "1",
                "yes",
                "on",
            )
        else:
            config_data["app"].setdefault("debug", False)

        env_name = config_data["app"]["environment"]
        is_prod = env_name == "production"
        is_frozen = bool(getattr(sys, "frozen", False))

        runtime_env = (os.getenv("VCL_DATA_DIR") or "").strip()
        runtime_root = Path(runtime_env).expanduser() if runtime_env else DEFAULT_RUNTIME_HOME
        user_cfg_path = _user_config_path(runtime_root)
        user_cfg = _read_json_file(user_cfg_path)

        def _persist_secret(path_key: str, value: str) -> None:
            if not value:
                return
            current = user_cfg.setdefault("security", {})
            if not isinstance(current, dict):
                user_cfg["security"] = {}
                current = user_cfg["security"]
            if not current.get(path_key):
                current[path_key] = value
                _atomic_write_json(user_cfg_path, user_cfg)

        # 安全配置
        security_cfg = config_data.setdefault("security", {})
        env_override = os.getenv("JWT_SECRET_ENV")
        secret_env_name = (
            env_override or security_cfg.get("jwt_secret_env") or "JWT_SECRET_KEY"
        )
        security_cfg["jwt_secret_env"] = secret_env_name

        jwt_secret = (
            os.getenv(secret_env_name)
            or os.getenv("JWT_SECRET_KEY")
            or (user_cfg.get("security", {}) or {}).get("jwt_secret_key")
        )
        config_secret = security_cfg.get("jwt_secret_key")
        jwt_secret_value: str | None = None
        if jwt_secret:
            if len(jwt_secret) < 32:
                if is_prod and not is_frozen:
                    raise ValueError("生产环境 JWT 密钥长度必须>=32")
                logger.warning(
                    "检测到 JWT_SECRET_KEY 长度不足，已为%s环境生成临时密钥", env_name
                )
                jwt_secret_value = secrets.token_urlsafe(48)
            else:
                jwt_secret_value = jwt_secret
        elif config_secret:
            if len(config_secret) < 32:
                if is_prod:
                    raise ValueError("生产环境 JWT 密钥长度必须>=32")
                logger.warning(
                    "配置文件中的JWT密钥长度不足，已为%s环境生成临时密钥", env_name
                )
                jwt_secret_value = secrets.token_urlsafe(48)
            else:
                jwt_secret_value = config_secret
                logger.warning(
                    "检测到JWT密钥来自配置文件，建议改用环境变量 %s", secret_env_name
                )
        else:
            if is_prod and not is_frozen:
                raise ValueError(
                    f"生产环境必须设置 JWT 密钥环境变量 ({secret_env_name}) 且长度>=32"
                )
            jwt_secret_value = secrets.token_urlsafe(48)
            logger.warning(
                "未配置JWT密钥，已为%s环境生成临时密钥，仅用于本次运行", env_name
            )

        if jwt_secret_value:
            security_cfg["jwt_secret_key"] = jwt_secret_value
            if not is_prod or is_frozen:
                os.environ.setdefault(secret_env_name, jwt_secret_value)
            if is_frozen:
                _persist_secret("jwt_secret_key", jwt_secret_value)

        # 开发者密钥
        dev_key = os.getenv("DEVELOPER_KEY_HASH")
        if dev_key:
            security_cfg["developer_key_hash"] = dev_key

        developer_cfg = config_data.setdefault("developer", {})
        admin_env_override = os.getenv("ADMIN_SECRET_ENV")
        admin_secret_env = (
            developer_cfg.get("admin_secret_env")
            or admin_env_override
            or "VCL_ADMIN_SECRET_KEY"
        )
        developer_cfg["admin_secret_env"] = admin_secret_env
        dev_mode_flag = os.getenv("DEVELOPER_MODE_ENABLED") or os.getenv(
            "DEVELOPER_MODE"
        )
        if dev_mode_flag is not None:
            developer_cfg["enabled"] = _parse_bool(dev_mode_flag)
        else:
            developer_cfg["enabled"] = _parse_bool(developer_cfg.get("enabled"))
            if env_name == "production" and developer_cfg["enabled"]:
                logger.warning(
                    "生产环境默认禁用开发者模式。如需启用，请设置环境变量 DEVELOPER_MODE_ENABLED=true。"
                )
                developer_cfg["enabled"] = False

        session_secret_env = (
            os.getenv("SESSION_SECRET_ENV")
            or security_cfg.get("session_secret_env")
            or "SESSION_SECRET_KEY"
        )
        security_cfg["session_secret_env"] = session_secret_env
        session_secret = (
            os.getenv(session_secret_env)
            or security_cfg.get("session_secret_key")
            or (user_cfg.get("security", {}) or {}).get("session_secret_key")
        )
        if session_secret:
            if len(session_secret) < 32:
                if is_prod and not is_frozen:
                    raise ValueError(
                        f"生产环境必须设置会话密钥环境变量 ({session_secret_env}) 且长度>=32"
                    )
                logger.warning("会话密钥长度不足，已为%s环境生成临时密钥", env_name)
                session_secret = secrets.token_urlsafe(48)
            else:
                security_cfg["session_secret_key"] = session_secret
        elif is_prod and not is_frozen:
            raise ValueError(
                f"生产环境必须设置会话密钥环境变量 ({session_secret_env}) 且长度>=32"
            )
        else:
            session_secret = secrets.token_urlsafe(48)
            logger.warning(
                "未配置会话密钥，已为%s环境生成临时密钥，仅用于本次运行", env_name
            )
        if session_secret:
            security_cfg["session_secret_key"] = session_secret
            if not is_prod or is_frozen:
                os.environ.setdefault(session_secret_env, session_secret)
            if is_frozen:
                _persist_secret("session_secret_key", session_secret)

        developer_secret_env = (
            os.getenv("DEVELOPER_SECRET_ENV")
            or security_cfg.get("developer_secret_env")
            or "DEVELOPER_SECRET_KEY"
        )
        security_cfg["developer_secret_env"] = developer_secret_env
        developer_secret = os.getenv(developer_secret_env) or security_cfg.get(
            "developer_secret_key"
        )
        if developer_cfg["enabled"]:
            if developer_secret:
                if len(developer_secret) < 32:
                    if is_prod and not is_frozen:
                        raise ValueError(
                            f"生产环境启用开发者模式时必须设置开发者密钥环境变量 ({developer_secret_env}) 且长度>=32"
                        )
                    logger.warning(
                        "开发者密钥长度不足，已为%s环境生成临时密钥", env_name
                    )
                    developer_secret = secrets.token_urlsafe(48)
                else:
                    security_cfg["developer_secret_key"] = developer_secret
            elif is_prod:
                raise ValueError(
                    f"生产环境启用开发者模式时必须设置开发者密钥环境变量 ({developer_secret_env}) 且长度>=32"
                )
            else:
                developer_secret = secrets.token_urlsafe(48)
                logger.warning(
                    "未配置开发者密钥，已为%s环境生成临时密钥，仅用于本次运行", env_name
                )
            if developer_secret:
                security_cfg["developer_secret_key"] = developer_secret
                if not is_prod or is_frozen:
                    os.environ.setdefault(developer_secret_env, developer_secret)

        # 管理后台密钥：不在全局配置加载阶段强制要求，避免阻断主应用启动。
        # Admin API 自身（src/api/admin_api.py）启动时会强校验该密钥。

        # 数据库配置
        if not config_data.get("database"):
            config_data["database"] = {}
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            config_data["database"]["url"] = db_url

        # Redis配置
        if not config_data.get("redis"):
            config_data["redis"] = {}
        redis_enabled = os.getenv("REDIS_ENABLED")
        config_data["redis"]["enabled"] = _parse_bool(
            redis_enabled
            if redis_enabled is not None
            else config_data["redis"].get("enabled", False)
        )

        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            config_data["redis"]["host"] = redis_host

        # 缓存配置
        if not config_data.get("cache"):
            config_data["cache"] = {}
        cache_enabled = os.getenv("CACHE_ENABLED")
        config_data["cache"]["enabled"] = _parse_bool(
            cache_enabled
            if cache_enabled is not None
            else config_data["cache"].get("enabled", True)
        )

        # 监控配置
        if not config_data.get("monitoring"):
            config_data["monitoring"] = {}
        monitoring_enabled = os.getenv("MONITORING_ENABLED")
        config_data["monitoring"]["enabled"] = _parse_bool(
            monitoring_enabled
            if monitoring_enabled is not None
            else config_data["monitoring"].get("enabled", True)
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
        for path_key in ["templates", "knowledge", "user_data", "reports", "i18n"]:
            env_key = f"{path_key.upper()}_DIR"
            env_value = os.getenv(env_key)
            if env_value:
                config_data["paths"][path_key] = env_value

        return config_data

    @classmethod
    def _detect_environment(cls, env: str | None) -> str:
        """按优先级确定运行环境"""
        # 1) 显式传参
        if env:
            return str(env).strip().lower() or "development"

        # 2) 环境变量
        env_var = os.getenv("ENVIRONMENT")
        if env_var:
            return str(env_var).strip().lower() or "development"

        # 3) 桌面打包默认进入 production（但会通过用户目录持久化生成的密钥）
        if bool(getattr(sys, "frozen", False)):
            return "production"

        # 4) 默认：必须由部署方显式设置 ENVIRONMENT=production 才进入严格模式
        return "development"

    @classmethod
    def _normalize_language_codes(cls, config_data: dict[str, Any]) -> dict[str, Any]:
        """规范语言代码（例如 zh-CN -> zh_CN）"""

        def _norm(value: str | None) -> str | None:
            if not value:
                return value
            normalized = value.replace("-", "_")
            parts = normalized.split("_")
            if len(parts) == 2:
                return f"{parts[0].lower()}_{parts[1].upper()}"
            return normalized

        app_cfg = config_data.setdefault("app", {})
        lang = _norm(app_cfg.get("language"))
        if lang:
            app_cfg["language"] = lang

        ui_cfg = config_data.get("ui")
        if isinstance(ui_cfg, dict):
            ui_lang = _norm(ui_cfg.get("language"))
            if ui_lang:
                ui_cfg["language"] = ui_lang

        return config_data

    @classmethod
    def _apply_runtime_data_root(cls, config_data: dict[str, Any]) -> dict[str, Any]:
        """在打包或不可写目录环境下，将可写路径落到用户目录。

        目标：避免 macOS .app / Windows Program Files 等不可写目录导致
        日志/数据库/报告无法写入，从而造成运行时不稳定。
        """

        runtime_env = (os.getenv("VCL_DATA_DIR") or "").strip()
        runtime_root = Path(runtime_env).expanduser() if runtime_env else DEFAULT_RUNTIME_HOME

        # 触发条件：显式强制、PyInstaller 打包、或项目根目录不可写
        force_user_dir = str(os.getenv("VCL_FORCE_USER_DATA_DIR", "")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        is_frozen = bool(getattr(sys, "frozen", False))
        project_writable = cls._is_directory_writable(PROJECT_ROOT)
        should_redirect = force_user_dir or is_frozen or not project_writable

        if not should_redirect:
            return config_data

        logger.warning(
            "检测到运行目录不可写或为打包环境，已将可写数据目录重定向到: %s",
            runtime_root,
        )

        paths_cfg = config_data.setdefault("paths", {})
        paths_cfg["logs"] = str(runtime_root / "logs")
        paths_cfg["reports"] = str(runtime_root / "reports")
        paths_cfg["user_data"] = str(runtime_root / "user_data")

        log_cfg = config_data.setdefault("log", {})
        log_cfg["file"] = str(runtime_root / "logs" / "app.log")

        storage_cfg = config_data.setdefault("storage", {})
        storage_cfg["base_path"] = str(runtime_root / "storage")

        db_cfg = config_data.setdefault("database", {})
        db_cfg["path"] = str(runtime_root / "data" / "virtualchemlab.db")

        # 若未通过环境变量显式提供 DATABASE_URL，则保持 url 与 path 一致，避免重定向后仍指向旧路径。
        # 注意：DatabaseConfig.set_url 仅在 url 为空时生成，因此这里需要显式修正。
        if not (os.getenv("DATABASE_URL") or "").strip():
            db_type = str(db_cfg.get("type") or "sqlite").strip().lower()
            url = db_cfg.get("url")
            if db_type == "sqlite" and isinstance(url, str) and url.startswith("sqlite:///"):
                db_cfg["url"] = f"sqlite:///{db_cfg['path']}"

        return config_data

    @staticmethod
    def _is_directory_writable(path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path, delete=True):
                return True
        except Exception:
            return False

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

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """深度合并配置字典（不会修改输入）"""
        merged = dict(base)
        for key, value in override.items():
            if isinstance(merged.get(key), dict) and isinstance(value, dict):
                merged[key] = Config._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    @classmethod
    def _get_default_config(cls) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
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
            "monitoring": {
                "enabled": True,
                "performance_tracking": True,
                "error_tracking": True,
            },
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
    if not env_path.is_absolute() and not env_path.exists():
        candidate = PROJECT_ROOT / env_file
        env_path = candidate if candidate.exists() else env_path
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
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
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
        logger.warning(
            f"ConfigAdapter.set() 不支持修改配置: {key}. 新配置系统是只读的，请在配置文件或环境变量中修改。"
        )

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
