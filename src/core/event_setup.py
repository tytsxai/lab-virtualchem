"""
事件系统初始化配置
建立模块间的事件通信机制
"""

import logging

from src.core.di_container import DIContainer
from src.core.event_bus import Event, EventBus, EventPriority

logger = logging.getLogger(__name__)


def setup_event_system(container: DIContainer) -> None:
    """设置事件系统

    Args:
        container: DI容器
    """
    EventSetup.setup_event_handlers(container)


class EventSetup:
    """事件系统初始化器"""

    @staticmethod
    def setup_event_handlers(container: DIContainer) -> None:
        """设置事件处理器

        Args:
            container: DI容器
        """
        try:
            event_bus = container.resolve(EventBus)

            # 设置实验相关事件处理器
            EventSetup._setup_experiment_handlers(event_bus, container)

            # 设置系统事件处理器
            EventSetup._setup_system_handlers(event_bus, container)

            # 设置用户事件处理器
            EventSetup._setup_user_handlers(event_bus, container)

            logger.info("事件处理器设置完成")

        except Exception as e:
            logger.error(f"事件处理器设置失败: {e}")

    @staticmethod
    def _setup_experiment_handlers(event_bus: EventBus, _container: DIContainer) -> None:
        """设置实验相关事件处理器"""

        def on_experiment_started(event: Event) -> None:
            """实验开始事件处理"""
            try:
                experiment_id = event.data.get("experiment_id")
                user_id = event.data.get("user_id")
                logger.info(f"实验开始: {experiment_id}, 用户: {user_id}")

                # 可以在这里添加实验开始后的逻辑
                # 例如：记录日志、发送通知等

            except Exception as e:
                logger.error(f"处理实验开始事件失败: {e}")

        def on_experiment_completed(event: Event) -> None:
            """实验完成事件处理"""
            try:
                experiment_id = event.data.get("experiment_id")
                user_id = event.data.get("user_id")
                score = event.data.get("score", 0)
                logger.info(f"实验完成: {experiment_id}, 用户: {user_id}, 得分: {score}")

                # 可以在这里添加实验完成后的逻辑
                # 例如：保存记录、计算统计等

            except Exception as e:
                logger.error(f"处理实验完成事件失败: {e}")

        def on_step_submitted(event: Event) -> None:
            """步骤提交事件处理"""
            try:
                experiment_id = event.data.get("experiment_id")
                step_id = event.data.get("step_id")
                success = event.data.get("success", False)
                logger.debug(f"步骤提交: {experiment_id}/{step_id}, 成功: {success}")

            except Exception as e:
                logger.error(f"处理步骤提交事件失败: {e}")

        def on_experiment_error(event: Event) -> None:
            """实验错误事件处理"""
            try:
                experiment_id = event.data.get("experiment_id")
                error_message = event.data.get("error", "未知错误")
                logger.error(f"实验错误: {experiment_id}, 错误: {error_message}")

            except Exception as e:
                logger.error(f"处理实验错误事件失败: {e}")

        # 注册事件处理器
        event_bus.subscribe("experiment.started", on_experiment_started, EventPriority.HIGH)
        event_bus.subscribe("experiment.completed", on_experiment_completed, EventPriority.HIGH)
        event_bus.subscribe("experiment.step_submitted", on_step_submitted, EventPriority.NORMAL)
        event_bus.subscribe("experiment.error", on_experiment_error, EventPriority.HIGH)

    @staticmethod
    def _setup_system_handlers(event_bus: EventBus, _container: DIContainer) -> None:
        """设置系统事件处理器"""

        def on_system_startup(_event: Event) -> None:
            """系统启动事件处理"""
            try:
                logger.info("系统启动完成")

                # 可以在这里添加系统启动后的初始化逻辑

            except Exception as e:
                logger.error(f"处理系统启动事件失败: {e}")

        def on_system_shutdown(_event: Event) -> None:
            """系统关闭事件处理"""
            try:
                logger.info("系统正在关闭")

                # 可以在这里添加系统关闭前的清理逻辑

            except Exception as e:
                logger.error(f"处理系统关闭事件失败: {e}")

        def on_system_error(event: Event) -> None:
            """系统错误事件处理"""
            try:
                error_message = event.data.get("error", "未知系统错误")
                logger.error(f"系统错误: {error_message}")

            except Exception as e:
                logger.error(f"处理系统错误事件失败: {e}")

        # 注册系统事件处理器
        event_bus.subscribe("system.startup", on_system_startup, EventPriority.CRITICAL)
        event_bus.subscribe("system.shutdown", on_system_shutdown, EventPriority.CRITICAL)
        event_bus.subscribe("system.error", on_system_error, EventPriority.HIGH)

    @staticmethod
    def _setup_user_handlers(event_bus: EventBus, _container: DIContainer) -> None:
        """设置用户事件处理器"""

        def on_user_login(event: Event) -> None:
            """用户登录事件处理"""
            try:
                user_id = event.data.get("user_id")
                logger.info(f"用户登录: {user_id}")

            except Exception as e:
                logger.error(f"处理用户登录事件失败: {e}")

        def on_user_logout(event: Event) -> None:
            """用户登出事件处理"""
            try:
                user_id = event.data.get("user_id")
                logger.info(f"用户登出: {user_id}")

            except Exception as e:
                logger.error(f"处理用户登出事件失败: {e}")

        # 注册用户事件处理器
        event_bus.subscribe("user.login", on_user_login, EventPriority.NORMAL)
        event_bus.subscribe("user.logout", on_user_logout, EventPriority.NORMAL)


def setup_event_communication(container: DIContainer) -> None:
    """设置事件通信（快捷函数）

    Args:
        container: DI容器
    """
    EventSetup.setup_event_handlers(container)
