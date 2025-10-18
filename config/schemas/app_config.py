"""
应用配置数据模型
使用Pydantic进行配置验证和管理
"""

import json
import os
from pathlib import Path
from typing import Any, Literal

try:
    # Pydantic v2
    from pydantic import BaseModel, Field, field_validator, model_validator
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1
    from pydantic import BaseModel, Field, root_validator, validator
    PYDANTIC_V2 = False


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
    jwt_secret_key: str | None = Field(default=None, description="JWT密钥")
    developer_secret_key: str | None = Field(default=None, description="开发者模式密钥")
    session_secret_key: str | None = Field(default=None, description="会话密钥")
    password_min_length: int = Field(default=8, description="密码最小长度")
    session_timeout: int = Field(default=3600, description="会话超时(秒)")

    if PYDANTIC_V2:
        @model_validator(mode='after')
        def validate_secrets(self):
            """验证密钥配置"""
            # 从环境变量加载
            if not self.jwt_secret_key:
                self.jwt_secret_key = os.getenv('JWT_SECRET_KEY')
            if not self.developer_secret_key:
                self.developer_secret_key = os.getenv('DEVELOPER_SECRET_KEY')
            if not self.session_secret_key:
                self.session_secret_key = os.getenv('SESSION_SECRET_KEY')

            # 生产环境必须配置密钥
            env = os.getenv('ENVIRONMENT', 'development')
            if env == 'production' and not self.jwt_secret_key:
                raise ValueError("生产环境必须配置JWT_SECRET_KEY")

            return self
    else:
        @root_validator
        def validate_secrets(cls, values):
            """验证密钥配置"""
            # 从环境变量加载
            values['jwt_secret_key'] = values.get('jwt_secret_key') or os.getenv('JWT_SECRET_KEY')
            values['developer_secret_key'] = values.get('developer_secret_key') or os.getenv('DEVELOPER_SECRET_KEY')
            values['session_secret_key'] = values.get('session_secret_key') or os.getenv('SESSION_SECRET_KEY')

            # 生产环境必须配置密钥
            env = os.getenv('ENVIRONMENT', 'development')
            if env == 'production' and not values.get('jwt_secret_key'):
                raise ValueError("生产环境必须配置JWT_SECRET_KEY")

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
    version: str = Field(default="2.0.0", description="应用版本")
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


class Config(BaseModel):
    """主配置类"""
    app: AppConfig = Field(default_factory=AppConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
        validate_assignment = True

    @classmethod
    def load(cls, env: str | None = None) -> "Config":
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
