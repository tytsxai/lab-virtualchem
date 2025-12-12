"""错误恢复系统"""

import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# 全局恢复管理器实例 - 将在文件末尾定义

class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    IGNORE = "ignore"
    ESCALATE = "escalate"
    RESTART = "restart"

@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: str
    error_message: str
    stack_trace: str
    timestamp: float
    component: str
    operation: str
    user_id: str | None = None
    session_id: str | None = None
    additional_data: dict[str, Any] | None = None

@dataclass
class RecoveryAction:
    """恢复动作"""
    strategy: RecoveryStrategy
    action: Callable[[], Any]
    max_attempts: int = 3
    delay: float = 1.0
    backoff_factor: float = 2.0
    timeout: float = 30.0

class ErrorRecoverySystem:
    """错误恢复系统"""

    def __init__(self):
        """初始化恢复系统"""
        self.recovery_rules: dict[str, list[RecoveryAction]] = {}
        self.error_history: list[ErrorContext] = []
        self.max_history = 1000
        self.is_enabled = True

        # 默认恢复规则
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """初始化默认恢复规则"""
        # 网络错误恢复规则
        self.add_recovery_rule(
            "NetworkError",
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                action=self._retry_network_operation,
                max_attempts=3,
                delay=1.0,
                backoff_factor=2.0
            )
        )

        # 数据库错误恢复规则
        self.add_recovery_rule(
            "DatabaseError",
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                action=self._retry_database_operation,
                max_attempts=2,
                delay=2.0
            )
        )

        # 文件系统错误恢复规则
        self.add_recovery_rule(
            "FileSystemError",
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                action=self._fallback_file_operation,
                max_attempts=1
            )
        )

        # 内存错误恢复规则
        self.add_recovery_rule(
            "MemoryError",
            RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                action=self._escalate_memory_error,
                max_attempts=1
            )
        )

    def add_recovery_rule(self, error_type: str, action: RecoveryAction):
        """添加恢复规则"""
        if error_type not in self.recovery_rules:
            self.recovery_rules[error_type] = []

        self.recovery_rules[error_type].append(action)

    def remove_recovery_rule(self, error_type: str, strategy: RecoveryStrategy):
        """移除恢复规则"""
        if error_type in self.recovery_rules:
            self.recovery_rules[error_type] = [
                rule for rule in self.recovery_rules[error_type]
                if rule.strategy != strategy
            ]

    def handle_error(self, error: Exception, context: ErrorContext) -> Any:
        """处理错误"""
        if not self.is_enabled:
            raise error

        # 记录错误历史
        self._record_error(context)

        # 查找恢复规则
        recovery_actions = self._find_recovery_actions(error, context)

        if not recovery_actions:
            logger.warning(f"没有找到恢复规则: {error.__class__.__name__}")
            raise error

        # 执行恢复动作
        for action in recovery_actions:
            try:
                result = self._execute_recovery_action(action, context)
                if result is not None:
                    return result
            except Exception as recovery_error:
                logger.error(f"恢复动作失败: {recovery_error}")
                continue

        # 所有恢复动作都失败，重新抛出原始错误
        raise error

    def _record_error(self, context: ErrorContext):
        """记录错误历史"""
        self.error_history.append(context)

        # 保持历史记录大小
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]

    def _find_recovery_actions(self, error: Exception, _context: ErrorContext) -> list[RecoveryAction]:
        """查找恢复动作"""
        error_type = error.__class__.__name__
        actions = []

        # 查找精确匹配
        if error_type in self.recovery_rules:
            actions.extend(self.recovery_rules[error_type])

        # 查找基类匹配
        for base_class in error.__class__.__mro__:
            base_name = base_class.__name__
            if base_name in self.recovery_rules:
                actions.extend(self.recovery_rules[base_name])

        return actions

    def _execute_recovery_action(self, action: RecoveryAction, context: ErrorContext) -> Any:
        """执行恢复动作"""
        logger.info(f"执行恢复动作: {action.strategy.value}")

        if action.strategy == RecoveryStrategy.RETRY:
            return self._execute_retry(action, context)
        elif action.strategy == RecoveryStrategy.FALLBACK:
            return self._execute_fallback(action, context)
        elif action.strategy == RecoveryStrategy.IGNORE:
            return self._execute_ignore(action, context)
        elif action.strategy == RecoveryStrategy.ESCALATE:
            return self._execute_escalate(action, context)
        elif action.strategy == RecoveryStrategy.RESTART:
            return self._execute_restart(action, context)
        else:
            raise ValueError(f"未知的恢复策略: {action.strategy}")

    def _execute_retry(self, action: RecoveryAction, _context: ErrorContext) -> Any:
        """执行重试策略"""
        for attempt in range(action.max_attempts):
            try:
                logger.info(f"重试尝试 {attempt + 1}/{action.max_attempts}")
                return action.action()
            except Exception as e:
                if attempt == action.max_attempts - 1:
                    raise e

                # 计算延迟时间
                delay = action.delay * (action.backoff_factor ** attempt)
                logger.info(f"重试延迟: {delay}秒")
                time.sleep(delay)

        return None

    def _execute_fallback(self, action: RecoveryAction, _context: ErrorContext) -> Any:
        """执行回退策略"""
        try:
            return action.action()
        except Exception as e:
            logger.error(f"回退策略失败: {e}")
            raise e

    def _execute_ignore(self, _action: RecoveryAction, context: ErrorContext) -> Any:
        """执行忽略策略"""
        logger.warning(f"忽略错误: {context.error_message}")
        return None

    def _execute_escalate(self, action: RecoveryAction, context: ErrorContext) -> Any:
        """执行升级策略"""
        logger.critical(f"错误升级: {context.error_message}")
        # 这里可以发送通知、记录日志等
        return action.action()

    def _execute_restart(self, action: RecoveryAction, context: ErrorContext) -> Any:
        """执行重启策略"""
        logger.critical(f"执行重启: {context.error_message}")
        # 这里可以实现重启逻辑
        return action.action()

    # 默认恢复动作实现
    def _retry_network_operation(self):
        """重试网络操作"""
        # 实现网络操作重试逻辑
        pass

    def _retry_database_operation(self):
        """重试数据库操作"""
        # 实现数据库操作重试逻辑
        pass

    def _fallback_file_operation(self):
        """回退文件操作"""
        # 实现文件操作回退逻辑
        pass

    def _escalate_memory_error(self):
        """升级内存错误"""
        # 实现内存错误升级逻辑
        pass

    def get_error_statistics(self) -> dict[str, Any]:
        """获取错误统计"""
        if not self.error_history:
            return {}

        # 按错误类型统计
        error_types = {}
        for context in self.error_history:
            error_type = context.error_type
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1

        # 按组件统计
        components = {}
        for context in self.error_history:
            component = context.component
            if component not in components:
                components[component] = 0
            components[component] += 1

        # 按时间统计
        recent_errors = [
            context for context in self.error_history
            if time.time() - context.timestamp < 3600  # 最近1小时
        ]

        return {
            'total_errors': len(self.error_history),
            'recent_errors': len(recent_errors),
            'error_types': error_types,
            'components': components,
            'recovery_rules': len(self.recovery_rules),
            'is_enabled': self.is_enabled
        }

    def clear_error_history(self):
        """清空错误历史"""
        self.error_history.clear()

    def enable(self):
        """启用恢复系统"""
        self.is_enabled = True

    def disable(self):
        """禁用恢复系统"""
        self.is_enabled = False

    def create_error_context(self, error: Exception, component: str, operation: str, **kwargs) -> ErrorContext:
        """创建错误上下文"""
        return ErrorContext(
            error_type=error.__class__.__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            timestamp=time.time(),
            component=component,
            operation=operation,
            **kwargs
        )

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type is not None:
            context = self.create_error_context(
                exc_val, "ErrorRecoverySystem", "__exit__"
            )
            try:
                self.handle_error(exc_val, context)
            except Exception:
                pass  # 避免在清理时抛出异常


# 全局恢复管理器实例
recovery_manager = ErrorRecoverySystem()


# 便捷函数
def auto_recover(func):
    """自动恢复装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = recovery_manager.create_error_context(e, func.__name__, "auto_recover")
            recovery_manager.handle_error(e, context)
            return None
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def fallback(default_value=None):
    """回退装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return default_value
        return wrapper
    return decorator
