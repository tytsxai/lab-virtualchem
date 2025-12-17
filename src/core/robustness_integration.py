#!/usr/bin/env python3
"""
代码健壮性集成系统
整合所有健壮性增强功能，提供统一的接口和使用方式
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .enhanced_error_recovery import EnhancedErrorRecovery
from .enhanced_logging import EnhancedLogger
from .enhanced_performance import EnhancedPerformanceManager
from .enhanced_security import EnhancedSecurityManager
from .enhanced_testing import EnhancedTestingFramework
from .enhanced_validation import EnhancedValidator
from .robustness_enhancer import RobustnessEnhancer

logger = logging.getLogger(__name__)


class IntegrationLevel(Enum):
    """集成级别"""

    BASIC = "basic"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


@dataclass
class RobustnessSettings:
    """健壮性设置"""

    integration_level: IntegrationLevel = IntegrationLevel.STANDARD
    enable_error_recovery: bool = True
    enable_validation: bool = True
    enable_logging: bool = True
    enable_performance_monitoring: bool = True
    enable_security: bool = True
    enable_testing: bool = True
    auto_optimization: bool = True
    auto_security_scan: bool = True
    detailed_reporting: bool = True


class RobustnessIntegrationManager:
    """健壮性集成管理器"""

    def __init__(self, settings: RobustnessSettings | None = None):
        self.settings = settings or RobustnessSettings()

        # 初始化各个组件
        self.robustness_enhancer = RobustnessEnhancer()
        self.error_recovery = EnhancedErrorRecovery()
        self.validator = EnhancedValidator()
        self.logger = EnhancedLogger()
        self.performance_manager = EnhancedPerformanceManager()
        self.security_manager = EnhancedSecurityManager()
        self.testing_framework = EnhancedTestingFramework()

        # 配置集成级别
        self._configure_integration_level()

        logger.info(
            f"健壮性集成管理器初始化完成，级别: {self.settings.integration_level.value}"
        )

    def _configure_integration_level(self) -> None:
        """配置集成级别"""
        if self.settings.integration_level == IntegrationLevel.BASIC:
            # 基础级别：只启用核心功能
            self.settings.enable_error_recovery = True
            self.settings.enable_validation = False
            self.settings.enable_logging = True
            self.settings.enable_performance_monitoring = False
            self.settings.enable_security = False
            self.settings.enable_testing = False
            self.settings.auto_optimization = False
            self.settings.auto_security_scan = False
            self.settings.detailed_reporting = False

        elif self.settings.integration_level == IntegrationLevel.STANDARD:
            # 标准级别：启用主要功能
            self.settings.enable_error_recovery = True
            self.settings.enable_validation = True
            self.settings.enable_logging = True
            self.settings.enable_performance_monitoring = True
            self.settings.enable_security = True
            self.settings.enable_testing = False
            self.settings.auto_optimization = True
            self.settings.auto_security_scan = False
            self.settings.detailed_reporting = True

        elif self.settings.integration_level == IntegrationLevel.ENHANCED:
            # 增强级别：启用所有功能
            self.settings.enable_error_recovery = True
            self.settings.enable_validation = True
            self.settings.enable_logging = True
            self.settings.enable_performance_monitoring = True
            self.settings.enable_security = True
            self.settings.enable_testing = True
            self.settings.auto_optimization = True
            self.settings.auto_security_scan = True
            self.settings.detailed_reporting = True

        elif self.settings.integration_level == IntegrationLevel.MAXIMUM:
            # 最大级别：启用所有功能，包括高级特性
            self.settings.enable_error_recovery = True
            self.settings.enable_validation = True
            self.settings.enable_logging = True
            self.settings.enable_performance_monitoring = True
            self.settings.enable_security = True
            self.settings.enable_testing = True
            self.settings.auto_optimization = True
            self.settings.auto_security_scan = True
            self.settings.detailed_reporting = True

    def enhance_function(
        self,
        func: Callable,
        operation_name: str | None = None,
        validation_rules: dict[str, Any] | None = None,
        security_level: str = "medium",
        enable_caching: bool = False,
        enable_retry: bool = True,
        timeout: float | None = None,
    ) -> Callable:
        """增强函数健壮性"""

        # 使用健壮性增强器
        enhanced_func = self.robustness_enhancer.enhance_function(
            func,
            operation_name,
            validation_rules,
            security_level,
            enable_caching,
            enable_retry,
            timeout,
        )

        # 添加错误恢复
        if self.settings.enable_error_recovery:
            enhanced_func = self._add_error_recovery(
                enhanced_func, operation_name or func.__name__
            )

        # 添加性能监控
        if self.settings.enable_performance_monitoring:
            enhanced_func = self._add_performance_monitoring(
                enhanced_func, operation_name or func.__name__
            )

        # 添加安全保护
        if self.settings.enable_security:
            enhanced_func = self._add_security_protection(enhanced_func)

        # 添加日志记录
        if self.settings.enable_logging:
            enhanced_func = self._add_logging(
                enhanced_func, operation_name or func.__name__
            )

        return enhanced_func

    def _add_error_recovery(self, func: Callable, operation_name: str) -> Callable:
        """添加错误恢复"""

        def wrapper(*args, **kwargs):
            return self.error_recovery.recover(operation_name, func, *args, **kwargs)

        return wrapper

    def _add_performance_monitoring(
        self, func: Callable, operation_name: str
    ) -> Callable:
        """添加性能监控"""

        def wrapper(*args, **kwargs):
            start_time = self.performance_manager.start_operation_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                self.performance_manager.end_operation_timer(
                    operation_name, start_time, success=True
                )
                return result
            except Exception:
                self.performance_manager.end_operation_timer(
                    operation_name, start_time, success=False
                )
                raise

        return wrapper

    def _add_security_protection(self, func: Callable) -> Callable:
        """添加安全保护"""

        def wrapper(*args, **kwargs):
            # 检查所有字符串参数
            for arg in args:
                if isinstance(arg, str):
                    if not self.security_manager.validate_input(arg):
                        raise ValueError(f"输入包含威胁: {arg[:50]}...")

            for _key, value in kwargs.items():
                if isinstance(value, str):
                    if not self.security_manager.validate_input(value):
                        raise ValueError(f"输入包含威胁: {value[:50]}...")

            return func(*args, **kwargs)

        return wrapper

    def _add_logging(self, func: Callable, operation_name: str) -> Callable:
        """添加日志记录"""

        def wrapper(*args, **kwargs):
            with self.logger.context(operation=operation_name):
                try:
                    result = func(*args, **kwargs)
                    self.logger.info(f"操作成功: {operation_name}")
                    return result
                except Exception as e:
                    self.logger.error(f"操作失败: {operation_name} - {e}")
                    raise

        return wrapper

    def validate_data(
        self, data: Any, validation_rules: dict[str, Any] | None = None
    ) -> bool:
        """验证数据"""
        if not self.settings.enable_validation:
            return True
        if validation_rules:
            logger.debug("收到自定义 validation_rules，但当前验证器尚未按规则解析")

        try:
            result = self.validator.validate(data)
            return result.is_valid
        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            return False

    def log_event(self, event_type: str, description: str, **kwargs) -> None:
        """记录事件"""
        if not self.settings.enable_logging:
            return

        self.logger.audit(event_type, description, **kwargs)

    def monitor_performance(self, operation_name: str) -> dict[str, Any]:
        """监控性能"""
        if not self.settings.enable_performance_monitoring:
            return {}

        return {
            "operation": operation_name,
            "report": self.performance_manager.get_performance_report(),
        }

    def check_security(self, input_data: str) -> bool:
        """检查安全性"""
        if not self.settings.enable_security:
            return True

        return self.security_manager.validate_input(input_data)

    def run_tests(self) -> dict[str, Any]:
        """运行测试"""
        if not self.settings.enable_testing:
            return {}

        return self.testing_framework.run_comprehensive_tests()

    def auto_optimize(self) -> list[dict[str, Any]]:
        """自动优化"""
        if not self.settings.auto_optimization:
            return []

        return self.performance_manager.optimizer.auto_optimize()

    def auto_security_scan(self) -> list[str]:
        """自动安全扫描"""
        if not self.settings.auto_security_scan:
            return []

        # 这里可以实现自动安全扫描逻辑
        vulnerabilities = []

        # 检查常见安全问题
        if (
            self.security_manager.security_auditor.get_security_summary()[
                "total_threat_detections"
            ]
            > 0
        ):
            vulnerabilities.append("检测到潜在安全威胁")

        return vulnerabilities

    def generate_comprehensive_report(self) -> str:
        """生成综合报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 代码健壮性综合报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"集成级别: {self.settings.integration_level.value}")
        report.append("")

        # 健壮性增强器报告
        if self.settings.enable_error_recovery:
            report.append("## 健壮性增强器")
            report.append(self.robustness_enhancer.generate_robustness_report())
            report.append("")

        # 性能报告
        if self.settings.enable_performance_monitoring:
            report.append("## 性能监控")
            report.append(self.performance_manager.get_performance_report())
            report.append("")

        # 安全报告
        if self.settings.enable_security:
            report.append("## 安全防护")
            report.append(self.security_manager.get_security_report())
            report.append("")

        # 测试报告
        if self.settings.enable_testing:
            report.append("## 测试覆盖")
            report.append(self.testing_framework.generate_test_report())
            report.append("")

        # 日志报告
        if self.settings.enable_logging:
            report.append("## 日志记录")
            report.append(self.logger.generate_logging_report())
            report.append("")

        # 自动优化结果
        if self.settings.auto_optimization:
            optimizations = self.auto_optimize()
            if optimizations:
                report.append("## 自动优化")
                for opt in optimizations:
                    report.append(
                        f"- {opt.get('strategy', 'unknown')}: {opt.get('actions_taken', [])}"
                    )
                report.append("")

        # 安全扫描结果
        if self.settings.auto_security_scan:
            vulnerabilities = self.auto_security_scan()
            if vulnerabilities:
                report.append("## 安全扫描")
                for vuln in vulnerabilities:
                    report.append(f"- {vuln}")
                report.append("")

        return "\n".join(report)

    def cleanup(self) -> None:
        """清理资源"""
        if self.settings.enable_performance_monitoring:
            self.performance_manager.cleanup()

        logger.info("健壮性集成管理器清理完成")


# 全局实例
robustness_integration = RobustnessIntegrationManager()


def enhance_robustness(
    operation_name: str | None = None,
    validation_rules: dict[str, Any] | None = None,
    security_level: str = "medium",
    enable_caching: bool = False,
    enable_retry: bool = True,
    timeout: float | None = None,
):
    """健壮性增强装饰器"""

    def decorator(func: Callable) -> Callable:
        return robustness_integration.enhance_function(
            func,
            operation_name,
            validation_rules,
            security_level,
            enable_caching,
            enable_retry,
            timeout,
        )

    return decorator


def validate_input(validation_rules: dict[str, Any] | None = None):
    """输入验证装饰器"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 验证所有参数
            for arg in args:
                if not robustness_integration.validate_data(arg, validation_rules):
                    raise ValueError(f"参数验证失败: {arg}")

            for _key, value in kwargs.items():
                if not robustness_integration.validate_data(value, validation_rules):
                    raise ValueError(f"参数验证失败: {_key}={value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def secure_operation(security_level: str = "medium"):
    """安全操作装饰器"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            logger.debug(f"执行安全操作: {func.__name__} (级别: {security_level})")
            # 检查所有字符串参数
            for arg in args:
                if isinstance(arg, str):
                    if not robustness_integration.check_security(arg):
                        raise ValueError(f"安全检查失败: {arg[:50]}...")

            for _key, value in kwargs.items():
                if isinstance(value, str):
                    if not robustness_integration.check_security(value):
                        raise ValueError(f"安全检查失败: {_key}={value[:50]}...")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_operation(operation_name: str | None = None):
    """操作日志装饰器"""

    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        def wrapper(*args, **kwargs):
            robustness_integration.log_event("operation_start", f"开始操作: {name}")
            try:
                result = func(*args, **kwargs)
                robustness_integration.log_event(
                    "operation_success", f"操作成功: {name}"
                )
                return result
            except Exception as e:
                robustness_integration.log_event(
                    "operation_error", f"操作失败: {name} - {e}"
                )
                raise

        return wrapper

    return decorator


def get_robustness_integration() -> RobustnessIntegrationManager:
    """获取健壮性集成管理器实例"""
    return robustness_integration
