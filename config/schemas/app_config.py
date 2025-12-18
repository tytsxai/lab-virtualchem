"""
应用配置数据模型（历史/兼容）。

重要说明（维护安全）：
- 运行时“主配置系统”的事实来源是 `src/core/config_loader.py`，并由
  `src/core/startup_preflight.py` 负责生产环境 fail-fast 的安全校验。
- 本模块位于 `config/schemas/`，主要用于历史脚本/示例/测试中的配置模型或迁移尝试；
  **不应** 被当作当前运行时的权威配置加载器。

如果你想验证本机/部署环境的配置是否完整，请使用：
    `python tools/validate_config.py`
"""

import json
import os
from pathlib import Path
from typing import Any, Literal

from src import __version__ as APP_VERSION

# 允许测试覆盖 Path.__file__，用于模拟不同的配置根目录
if not hasattr(Path, "__file__"):
    Path.__file__ = __file__

try:
    # Pydantic v2
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1
    from pydantic import BaseModel, Field, root_validator, validator
    ConfigDict = None  # type: ignore[assignment]
    PYDANTIC_V2 = False


def _env_flag(name: str, default: bool = False) -> bool:
    """读取环境变量布尔值，支持常见真值字符串"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_secret_env(names: list[str]) -> str | None:
    """按优先级读取环境变量中的密钥"""
    for env_name in names:
        if not env_name:
            continue
        value = os.getenv(env_name)
        if value:
            return value
    return None


DEFAULT_SECRET_ENV_NAMES = {
    "jwt_secret_key": "JWT_SECRET_KEY",
    "developer_secret_key": "DEVELOPER_SECRET_KEY",
    "session_secret_key": "SESSION_SECRET_KEY",
}


class PathConfig(BaseModel):
    """路径配置"""
    templates_dir: str = Field(default="assets/templates", description="实验模板目录")
    knowledge_dir: str = Field(default="assets/knowledge", description="知识库目录")
    i18n_dir: str = Field(default="assets/i18n", description="国际化目录")
    logs_dir: str = Field(default="logs", description="日志目录")
    reports_dir: str = Field(default="reports", description="报告目录")
    data_dir: str = Field(default="data", description="数据目录")
    backups_dir: str = Field(default="backups", description="备份目录")

    if PYDANTIC_V2:
        @field_validator('*')
        @classmethod
        def validate_path(cls, v):
            """验证路径格式"""
            if v:
                return v.replace('\\', '/')
            return v
    else:
        @validator('*')
        def validate_path(cls, v):
            """验证路径格式"""
            if v:
                return v.replace('\\', '/')
            return v


class DatabaseConfig(BaseModel):
    """数据库配置"""
    type: Literal["sqlite", "json"] = Field(default="json", description="数据库类型")
    path: str = Field(default="data/", description="数据库路径")
    backup_enabled: bool = Field(default=True, description="是否启用备份")
    backup_interval: int = Field(default=3600, description="备份间隔(秒)")

    if PYDANTIC_V2:
        @field_validator('path')
        @classmethod
        def validate_db_path(cls, v):
            """验证数据库路径"""
            return v.replace('\\', '/')
    else:
        @validator('path')
        def validate_db_path(cls, v):
            """验证数据库路径"""
            return v.replace('\\', '/')


class SecurityConfig(BaseModel):
    """安全配置"""
    jwt_secret_env: str = Field(default="JWT_SECRET_KEY", description="JWT密钥环境变量名")
    developer_secret_env: str = Field(default="DEVELOPER_SECRET_KEY", description="开发者模式密钥环境变量名")
    session_secret_env: str = Field(default="SESSION_SECRET_KEY", description="会话密钥环境变量名")
    jwt_secret_key: str | None = Field(default=None, description="JWT密钥")
    developer_secret_key: str | None = Field(default=None, description="开发者模式密钥")
    session_secret_key: str | None = Field(default=None, description="会话密钥")
    password_min_length: int = Field(default=8, description="密码最小长度")
    session_timeout: int = Field(default=3600, description="会话超时(秒)")

    if PYDANTIC_V2:
        @model_validator(mode='after')
        def validate_secrets(self):
            """从环境变量加载密钥"""
            self.jwt_secret_key = self.jwt_secret_key or _read_secret_env(
                [self.jwt_secret_env, DEFAULT_SECRET_ENV_NAMES["jwt_secret_key"]]
            )
            self.developer_secret_key = (
                self.developer_secret_key
                or _read_secret_env([self.developer_secret_env, DEFAULT_SECRET_ENV_NAMES["developer_secret_key"]])
            )
            self.session_secret_key = self.session_secret_key or _read_secret_env(
                [self.session_secret_env, DEFAULT_SECRET_ENV_NAMES["session_secret_key"]]
            )
            return self
    else:
        @root_validator
        def validate_secrets(cls, values):
            """从环境变量加载密钥"""
            values["jwt_secret_env"] = values.get("jwt_secret_env") or "JWT_SECRET_KEY"
            values["developer_secret_env"] = values.get("developer_secret_env") or "DEVELOPER_SECRET_KEY"
            values["session_secret_env"] = values.get("session_secret_env") or "SESSION_SECRET_KEY"

            values["jwt_secret_key"] = values.get("jwt_secret_key") or _read_secret_env(
                [values["jwt_secret_env"], DEFAULT_SECRET_ENV_NAMES["jwt_secret_key"]]
            )
            values["developer_secret_key"] = values.get("developer_secret_key") or _read_secret_env(
                [values["developer_secret_env"], DEFAULT_SECRET_ENV_NAMES["developer_secret_key"]]
            )
            values["session_secret_key"] = values.get("session_secret_key") or _read_secret_env(
                [values["session_secret_env"], DEFAULT_SECRET_ENV_NAMES["session_secret_key"]]
            )
            return values


class DeveloperConfig(BaseModel):
    """开发者模式配置"""
    enabled: bool = Field(default=False, description="是否启用开发者模式")
    enabled_env: str = Field(default="DEVELOPER_MODE_ENABLED", description="开发者模式开关环境变量")
    debug_mode: bool = Field(default=False, description="开发者调试开关")
    debug_env: str = Field(default="DEVELOPER_DEBUG", description="开发者调试开关环境变量")
    console_enabled: bool = Field(default=False, description="开发者控制台开关")
    console_env: str = Field(default="DEVELOPER_CONSOLE_ENABLED", description="开发者控制台环境变量")

    if PYDANTIC_V2:
        @model_validator(mode="after")
        def apply_env_overrides(self):
            """应用环境变量开关"""
            self.enabled = _env_flag(self.enabled_env, self.enabled)
            self.debug_mode = _env_flag(self.debug_env, self.debug_mode)
            self.console_enabled = _env_flag(self.console_env, self.console_enabled)
            return self
    else:
        @root_validator
        def apply_env_overrides(cls, values):
            """应用环境变量开关"""
            enabled_env = values.get("enabled_env") or "DEVELOPER_MODE_ENABLED"
            debug_env = values.get("debug_env") or "DEVELOPER_DEBUG"
            console_env = values.get("console_env") or "DEVELOPER_CONSOLE_ENABLED"

            values["enabled_env"] = enabled_env
            values["debug_env"] = debug_env
            values["console_env"] = console_env

            values["enabled"] = _env_flag(enabled_env, values.get("enabled", False))
            values["debug_mode"] = _env_flag(debug_env, values.get("debug_mode", False))
            values["console_enabled"] = _env_flag(console_env, values.get("console_enabled", False))
            return values


class PerformanceConfig(BaseModel):
    """性能配置"""
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_type: Literal["memory", "redis", "multi"] = Field(default="memory", description="缓存类型")
    cache_ttl: int = Field(default=300, description="缓存TTL(秒)")
    max_workers: int = Field(default=4, description="最大工作线程数")
    request_timeout: int = Field(default=30, description="请求超时(秒)")


class MonitoringConfig(BaseModel):
    """监控配置"""
    enabled: bool = Field(default=True, description="是否启用监控")
    metrics_enabled: bool = Field(default=True, description="是否启用指标收集")
    health_check_interval: int = Field(default=60, description="健康检查间隔(秒)")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="日志级别"
    )


class AppConfig(BaseModel):
    """应用配置"""
    name: str = Field(default="VirtualChemLab", description="应用名称")
    version: str = Field(default=APP_VERSION, description="应用版本")
    environment: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="运行环境"
    )
    debug: bool = Field(default=False, description="调试模式")
    host: str = Field(default="127.0.0.1", description="主机地址")
    port: int = Field(default=8000, description="端口")

    if PYDANTIC_V2:
        @field_validator('environment', mode='before')
        @classmethod
        def validate_environment(cls, v):
            """从环境变量加载"""
            return os.getenv('ENVIRONMENT', v or 'development')
    else:
        @validator('environment', pre=True)
        def validate_environment(cls, v):
            """从环境变量加载"""
            return os.getenv('ENVIRONMENT', v or 'development')


class AppConfiguration(BaseModel):
    """主配置类"""
    app: AppConfig = Field(default_factory=AppConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    developer: DeveloperConfig = Field(default_factory=DeveloperConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    if PYDANTIC_V2:
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            validate_assignment=True,
        )
    else:
        class Config:
            """Pydantic配置"""
            arbitrary_types_allowed = True
            validate_assignment = True

    if PYDANTIC_V2:
        @model_validator(mode="after")
        def validate_environment_requirements(self):
            """生产环境安全校验与开关控制"""
            env = self.app.environment

            if env == "production":
                # 生产环境强制关闭调试与开发者模式，除非显式开关
                self.developer.enabled = _env_flag(self.developer.enabled_env, False)
                self.developer.debug_mode = _env_flag(self.developer.debug_env, False)
                self.developer.console_enabled = _env_flag(
                    self.developer.console_env, self.developer.console_enabled
                )
                self.app.debug = False
            else:
                self.developer.enabled = _env_flag(self.developer.enabled_env, self.developer.enabled)
                self.developer.debug_mode = _env_flag(self.developer.debug_env, self.developer.debug_mode)
                self.developer.console_enabled = _env_flag(
                    self.developer.console_env, self.developer.console_enabled
                )

            if env == "production":
                missing_secrets: list[str] = []
                if not self.security.jwt_secret_key:
                    missing_secrets.append(self.security.jwt_secret_env or DEFAULT_SECRET_ENV_NAMES["jwt_secret_key"])
                if not self.security.session_secret_key:
                    missing_secrets.append(
                        self.security.session_secret_env or DEFAULT_SECRET_ENV_NAMES["session_secret_key"]
                    )
                if self.developer.enabled and not self.security.developer_secret_key:
                    missing_secrets.append(
                        self.security.developer_secret_env or DEFAULT_SECRET_ENV_NAMES["developer_secret_key"]
                    )

                if missing_secrets:
                    missing_list = ", ".join(sorted(set(missing_secrets)))
                    raise ValueError(f"生产环境缺少必需的密钥: {missing_list}")

            return self
    else:
        @root_validator
        def validate_environment_requirements(cls, values):
            """生产环境安全校验与开关控制"""
            app_cfg: AppConfig = values.get("app", AppConfig())
            env = getattr(app_cfg, "environment", os.getenv("ENVIRONMENT", "development"))
            developer_cfg: DeveloperConfig = values.get("developer", DeveloperConfig())

            if env == "production":
                developer_cfg.enabled = _env_flag(developer_cfg.enabled_env, False)
                developer_cfg.debug_mode = _env_flag(developer_cfg.debug_env, False)
                developer_cfg.console_enabled = _env_flag(developer_cfg.console_env, developer_cfg.console_enabled)
                app_cfg.debug = False
            else:
                developer_cfg.enabled = _env_flag(developer_cfg.enabled_env, developer_cfg.enabled)
                developer_cfg.debug_mode = _env_flag(developer_cfg.debug_env, developer_cfg.debug_mode)
                developer_cfg.console_enabled = _env_flag(
                    developer_cfg.console_env, developer_cfg.console_enabled
                )

            values["developer"] = developer_cfg
            values["app"] = app_cfg

            if env == "production":
                security_cfg: SecurityConfig = values.get("security", SecurityConfig())
                missing_secrets: list[str] = []
                if not security_cfg.jwt_secret_key:
                    missing_secrets.append(
                        getattr(security_cfg, "jwt_secret_env", None) or DEFAULT_SECRET_ENV_NAMES["jwt_secret_key"]
                    )
                if not security_cfg.session_secret_key:
                    missing_secrets.append(
                        getattr(security_cfg, "session_secret_env", None) or DEFAULT_SECRET_ENV_NAMES["session_secret_key"]
                    )
                if developer_cfg.enabled and not security_cfg.developer_secret_key:
                    missing_secrets.append(
                        getattr(security_cfg, "developer_secret_env", None)
                        or DEFAULT_SECRET_ENV_NAMES["developer_secret_key"]
                    )

                if missing_secrets:
                    missing_list = ", ".join(sorted(set(missing_secrets)))
                    raise ValueError(f"生产环境缺少必需的密钥: {missing_list}")

            return values

    @classmethod
    def load(cls, env: str | None = None) -> "AppConfiguration":
        """
        加载配置

        Args:
            env: 环境名称 (development/staging/production/test)

        Returns:
            Config实例
        """
        # 确定环境
        env = env or os.getenv('ENVIRONMENT', 'development')

        # 配置文件路径
        config_dir = Path(__file__).parent.parent
        base_file = config_dir / "base.json"
        env_file = config_dir / f"{env}.json"

        # 加载基础配置
        config_data = {}
        if base_file.exists():
            with open(base_file, encoding='utf-8') as f:
                config_data = json.load(f)

        # 加载环境配置并合并
        if env_file.exists():
            with open(env_file, encoding='utf-8') as f:
                env_config = json.load(f)
                config_data = cls._deep_merge(config_data, env_config)

        # 验证并创建配置对象
        return cls(**config_data)

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self, env: str | None = None):
        """保存配置到文件"""
        env = env or self.app.environment
        config_dir = Path(__file__).parent.parent
        env_file = config_dir / f"{env}.json"

        with open(env_file, 'w', encoding='utf-8') as f:
            json.dump(self.dict(), f, indent=2, ensure_ascii=False)

    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent.parent

    def get_absolute_path(self, relative_path: str) -> Path:
        """获取绝对路径"""
        return self.get_project_root() / relative_path

    def validate_paths(self) -> dict[str, bool]:
        """验证所有路径是否存在"""
        results = {}
        root = self.get_project_root()

        for field, value in self.paths.dict().items():
            path = root / value
            results[field] = path.exists()

        return results

    def create_directories(self):
        """创建必要的目录"""
        root = self.get_project_root()

        for _field, value in self.paths.dict().items():
            path = root / value
            path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {path}")


# 兼容旧代码的别名
Config = AppConfiguration


# 全局配置实例
_config_instance: Config | None = None


def get_config(reload: bool = False) -> Config:
    """
    获取配置实例 (单例模式)

    Args:
        reload: 是否重新加载配置

    Returns:
        Config实例
    """
    global _config_instance

    if _config_instance is None or reload:
        _config_instance = Config.load()

    return _config_instance


def main():
    """测试配置加载"""
    print("=" * 60)
    print("VirtualChemLab 配置管理")
    print("=" * 60)

    # 加载配置
    print("\n加载配置...")
    config = get_config()

    print(f"\n应用: {config.app.name} v{config.app.version}")
    print(f"环境: {config.app.environment}")
    print(f"调试: {config.app.debug}")

    # 验证路径
    print("\n验证路径:")
    results = config.validate_paths()
    for field, exists in results.items():
        icon = "✅" if exists else "❌"
        print(f"  {icon} {field}: {getattr(config.paths, field)}")

    # 创建缺失的目录
    missing = [k for k, v in results.items() if not v]
    if missing:
        print("\n创建缺失的目录:")
        config.create_directories()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
