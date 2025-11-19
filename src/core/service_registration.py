"""
服务注册配置
集中管理所有服务的DI容器注册
"""

import logging
import os
import threading
from pathlib import Path
from typing import Any

from src.contracts.experiment_service import ExperimentServiceConfig
from src.core.auth import (
    AuthService,
    IAuthService,
    JWTManager,
    PasswordHasher,
    RBACManager,
    Role,
    SimpleUserRepository,
    User,
    create_jwt_manager_from_config,
)

# 旧配置系统已弃用，使用新配置系统
# from src.core.config import CompositeConfig, JsonConfig
# 延迟导入以避免循环依赖
# from src.core.config_loader import Config, get_config
from src.core.curve_generator import CurveGenerator
from src.core.dev_auth import DeveloperAuth
from src.core.di_container import DIContainer
from src.core.event_bus import EventBus, get_event_bus
from src.core.experiment_controller import ExperimentController
from src.core.repository import FileRepository, IRepository
from src.core.rule_validator import RuleValidator
from src.core.template_engine import TemplateEngine
from src.interfaces.experiment import (
    ICurveGenerator,
    IExperimentEngine,
    IExperimentValidator,
)
from src.interfaces.storage import IConfig, ILogger, IStorage
from src.storage.json_store import JSONStore
from src.utils.i18n import I18n
from src.utils.logger import get_logger

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """服务注册表 - 管理所有服务的注册"""

    @staticmethod
    def register_all(container: DIContainer, config: Any | None = None) -> DIContainer:
        """注册所有服务

        Args:
            container: DI容器
            config: 配置对象（可选）

        Returns:
            配置好的DI容器
        """
        # 加载配置（如果未提供）
        if config is None:
            # 延迟导入以避免循环依赖
            from src.core.config_loader import get_config
            config = get_config()

        # 1. 注册核心配置
        ServiceRegistry.register_config(container, config)

        # 2. 注册日志服务
        ServiceRegistry.register_logging(container)

        # 3. 注册事件总线
        ServiceRegistry.register_event_bus(container)

        # 4. 注册存储服务
        ServiceRegistry.register_storage(container, config)

        # 5. 注册核心引擎
        ServiceRegistry.register_core_engines(container, config)

        # 6. 注册实验服务
        ServiceRegistry.register_experiment_services(container, config)

        # 7. 注册认证服务
        ServiceRegistry.register_auth_services(container, config)

        # 8. 注册UI辅助服务
        ServiceRegistry.register_ui_services(container, config)

        # 9. 设置事件通信
        ServiceRegistry.setup_event_communication(container)

        return container

    @staticmethod
    def register_config(container: DIContainer, config: Any) -> None:
        """注册配置服务"""
        # 新配置系统 - 延迟导入以避免循环依赖
        from src.core.config_loader import Config
        container.register_singleton(Config, instance=config)

        # 向后兼容 - 旧配置系统（已弃用，使用新配置系统）
        # 为了兼容性，创建一个适配器
        try:
            from src.core.config_loader import ConfigAdapter
            adapter = ConfigAdapter(config)
            container.register_singleton(IConfig, instance=adapter)
        except Exception:
            # 如果适配器创建失败，使用空配置
            pass

    @staticmethod
    def register_logging(container: DIContainer) -> None:
        """注册日志服务"""

        class ConsoleLogger(ILogger):
            """控制台日志实现"""

            def __init__(self) -> None:
                self.logger = get_logger("app")

            def log(self, level: str, message: str, **kwargs: Any) -> None:
                log_func = getattr(self.logger, level.lower(), self.logger.info)
                log_func(message, **kwargs)

            def debug(self, message: str, **kwargs: Any) -> None:
                self.logger.debug(message, **kwargs)

            def info(self, message: str, **kwargs: Any) -> None:
                self.logger.info(message, **kwargs)

            def warning(self, message: str, **kwargs: Any) -> None:
                self.logger.warning(message, **kwargs)

            def error(self, message: str, **kwargs: Any) -> None:
                self.logger.error(message, **kwargs)

            def critical(self, message: str, **kwargs: Any) -> None:
                self.logger.critical(message, **kwargs)

        container.register_singleton(ILogger, instance=ConsoleLogger())

    @staticmethod
    def register_event_bus(container: DIContainer) -> None:
        """注册事件总线"""
        # 使用全局单例
        event_bus = get_event_bus()
        container.register_singleton(EventBus, instance=event_bus)

    @staticmethod
    def register_storage(container: DIContainer, config: Any) -> None:
        """注册存储服务"""

        # JSONStore（默认存储）
        def create_json_store() -> JSONStore:
            user_data_dir = config.paths.user_data
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            return JSONStore(base_dir=user_data_dir)

        container.register_singleton(JSONStore, factory=create_json_store)
        # 同时注册 IStorage 和 IStorage[Any]
        container.register_singleton(IStorage, factory=create_json_store)
        container.register_singleton(IStorage[Any], factory=create_json_store)

        # 通用仓储
        def create_repository() -> FileRepository:
            data_dir = Path(config.paths.user_data) / "repositories"
            data_dir.mkdir(parents=True, exist_ok=True)
            return FileRepository(str(data_dir / "entities.json"))

        container.register_singleton(IRepository[Any], factory=create_repository)

    @staticmethod
    def register_core_engines(container: DIContainer, config: Any) -> None:
        """注册核心引擎"""

        # 模板引擎
        def create_template_engine() -> TemplateEngine:
            templates_dir = Path(config.paths.templates)
            return TemplateEngine(templates_dir)

        container.register_singleton(TemplateEngine, factory=create_template_engine)

        # 规则验证器
        container.register_singleton(RuleValidator, RuleValidator)

        # 曲线生成器
        container.register_singleton(CurveGenerator, CurveGenerator)

        # 实验控制器（瞬态 - 每个实验一个实例）
        def create_experiment_controller() -> ExperimentController:
            # 创建默认的实验模板和用户ID用于测试
            from src.models.experiment import (
                CheckPoint,
                CheckType,
                ExperimentTemplate,
                Step,
            )

            template = ExperimentTemplate(
                id="default_template",
                title="默认实验模板",
                description="用于测试的默认模板",
                level="basic",
                duration_min=30,
                steps=[
                    Step(
                        id="step_1",
                        text="第一步：准备实验",
                        check=CheckPoint(type=CheckType.CONFIRM, fail_hint="请确认已准备好实验器材"),
                    )
                ],
                score_rules=[],
            )
            return ExperimentController(template=template, user_id="test_user", enable_monitoring=False)

        container.register_transient(ExperimentController, factory=create_experiment_controller)

        # 注册实验引擎接口
        container.register_transient(IExperimentEngine, factory=create_experiment_controller)

        # 注册实验验证器接口
        container.register_singleton(IExperimentValidator, RuleValidator)

        # 注册曲线生成器接口
        container.register_singleton(ICurveGenerator, CurveGenerator)

    @staticmethod
    def register_experiment_services(container: DIContainer, _config: Any) -> None:
        """注册实验服务"""
        try:
            from src.contracts.experiment_service import ExperimentService
            from src.services.experiment_service_impl import ExperimentServiceImpl

            # 注册实验服务实现
            def create_experiment_service() -> ExperimentServiceImpl:
                template_engine = container.resolve(TemplateEngine)
                storage = container.resolve(IStorage[Any])
                record_store = container.resolve(JSONStore)

                def engine_factory() -> IExperimentEngine:
                    return container.resolve(IExperimentEngine)

                return ExperimentServiceImpl(
                    engine_factory=engine_factory,
                    storage=storage,
                    config=ExperimentServiceConfig(),
                    template_engine=template_engine,
                    record_store=record_store,
                )

            container.register_transient(ExperimentService, factory=create_experiment_service)

            logger.info("实验服务注册成功")
        except ImportError as e:
            logger.warning(f"实验服务注册失败: {e}")
            # 继续执行，不影响其他服务

    @staticmethod
    def register_auth_services(container: DIContainer, config: Any) -> None:
        """注册认证服务"""

        # 开发者认证
        def create_dev_auth() -> DeveloperAuth:
            try:
                # 创建开发者认证
                return DeveloperAuth()
            except Exception as e:
                # 如果创建失败，使用默认配置
                logger.warning(f"开发者认证初始化失败: {e}")
                return DeveloperAuth()

        container.register_singleton(DeveloperAuth, factory=create_dev_auth)

        # RBAC管理器
        container.register_singleton(RBACManager, RBACManager)

        # 用户仓储
        def create_user_repository() -> SimpleUserRepository:
            repo = SimpleUserRepository()
            ServiceRegistry._seed_default_users(repo)
            return repo

        container.register_singleton(SimpleUserRepository, factory=create_user_repository)

        # JWT管理器
        def create_jwt_manager() -> JWTManager:
            try:
                return create_jwt_manager_from_config(config)
            except Exception as exc:  # pragma: no cover - 配置错误时回退
                logger.error(f"JWT管理器初始化失败: {exc}")
                # 生成一个临时密钥，防止服务因配置缺失而崩溃
                os.environ.setdefault("JWT_SECRET_KEY", "temporary-development-secret-token-please-change")
                return create_jwt_manager_from_config(config)

        container.register_singleton(JWTManager, factory=create_jwt_manager)

        # 认证服务
        def create_auth_service() -> AuthService:
            jwt_manager = container.resolve(JWTManager)
            rbac_manager = container.resolve(RBACManager)
            user_repo = container.resolve(SimpleUserRepository)
            return AuthService(jwt_manager, rbac_manager, user_repo)

        container.register_singleton(IAuthService, factory=create_auth_service)

    @staticmethod
    def register_ui_services(container: DIContainer, config: Any) -> None:
        """注册UI辅助服务"""

        # 国际化
        def create_i18n():
            i18n_dir = config.paths.i18n
            return I18n(i18n_dir)

        container.register_singleton(I18n, factory=create_i18n)

    @staticmethod
    def setup_event_communication(container: DIContainer) -> None:
        """设置事件通信"""
        try:
            from src.core.event_setup import setup_event_communication

            setup_event_communication(container)
            logger.info("事件通信设置完成")
        except Exception as e:
            logger.warning(f"事件通信设置失败: {e}")

    @staticmethod
    def _seed_default_users(repo: SimpleUserRepository) -> None:
        """初始化默认管理员账户（通过环境变量配置）"""
        admin_password = os.getenv("VCL_ADMIN_PASSWORD")
        if not admin_password:
            logger.info("未设置 VCL_ADMIN_PASSWORD，跳过默认管理员初始化")
            return

        username = os.getenv("VCL_ADMIN_USERNAME", "admin")
        email = os.getenv("VCL_ADMIN_EMAIL", f"{username}@example.com")
        password_hash, salt = PasswordHasher.hash_password(admin_password)
        stored_hash = f"{password_hash}${salt}"

        existing_user = repo.find_by_username(username)
        if existing_user:
            logger.info("默认管理员已存在，跳过初始化: %s", username)
            return

        repo.add(
            User(
                id=f"{username}_admin",
                username=username,
                email=email,
                password_hash=stored_hash,
                roles=[Role.ADMIN],
            )
        )
        logger.info("默认管理员用户已初始化: %s", username)


def configure_container(container: DIContainer | None = None, config: Any = None) -> DIContainer:
    """配置DI容器（快捷函数）

    Args:
        container: DI容器（如果为None则创建新容器）
        config: 配置对象（如果为None则加载默认配置）

    Returns:
        配置好的DI容器

    Examples:
        # 使用默认配置
        container = configure_container()

        # 使用自定义配置
        from src.core.config_loader import Config
        config = Config.load("production")
        container = configure_container(config=config)

        # 使用现有容器
        container = DIContainer()
        configure_container(container, config)
    """
    if container is None:
        container = DIContainer()

    if config is None:
        # 延迟导入以避免循环依赖
        from src.core.config_loader import get_config
        config = get_config()

    return ServiceRegistry.register_all(container, config)


# 全局容器单例（线程安全）
_global_configured_container: DIContainer | None = None
_configured_container_lock = threading.Lock()


def get_configured_container() -> DIContainer:
    """获取全局配置好的容器（线程安全）

    Returns:
        配置好的DI容器（单例）
    """
    global _global_configured_container
    if _global_configured_container is None:
        with _configured_container_lock:
            if _global_configured_container is None:  # 双重检查锁
                _global_configured_container = configure_container()
    return _global_configured_container


def reset_container() -> None:
    """重置全局容器（主要用于测试）"""
    global _global_configured_container
    _global_configured_container = None


if __name__ == "__main__":
    # 测试服务注册
    print("=" * 60)
    logger.info("测试服务注册")
    print("=" * 60)

    try:
        # 创建并配置容器
        container = configure_container()

        logger.info("\n✅ 容器配置成功！")
        logger.info(f"已注册 {len(container.get_all_services())} 个服务：\n")

        # 列出所有注册的服务
        for service in container.get_all_services():
            logger.info(f"  - {service.__name__}")

        # 测试解析几个关键服务
        print("\n" + "=" * 60)
        logger.info("测试服务解析")
        print("=" * 60)

        logger.info("\n1. 解析Config...")
        # 延迟导入以避免循环依赖
        from src.core.config_loader import Config
        config = container.resolve(Config)
        logger.info(f"   ✅ 应用名称: {config.app.name}")

        logger.info("\n2. 解析EventBus...")
        event_bus = container.resolve(EventBus)
        logger.info(f"   ✅ 事件总线: {type(event_bus).__name__}")

        logger.info("\n3. 解析TemplateEngine...")
        template_engine = container.resolve(TemplateEngine)
        logger.info(f"   ✅ 模板引擎: {type(template_engine).__name__}")

        logger.info("\n4. 解析IStorage...")
        storage = container.resolve(IStorage[Any])
        logger.info(f"   ✅ 存储服务: {type(storage).__name__}")

        logger.info("\n5. 解析I18n...")
        i18n = container.resolve(I18n)
        logger.info(f"   ✅ 国际化服务: {type(i18n).__name__}")

        print("\n" + "=" * 60)
        logger.info("✅ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        logger.info(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
