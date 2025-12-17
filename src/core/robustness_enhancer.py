#!/usr/bin/env python3
"""
VirtualChemLab 代码健壮性增强器
统一处理错误处理、数据验证、日志记录、性能优化和安全防护
"""

import asyncio
import functools
import logging
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .error_system.error_handler import GlobalErrorHandler
from .error_system.exceptions import BaseAppException
from .security.input_validator import InputValidator
from .validation import ValidatorChain

logger = logging.getLogger(__name__)


class RobustnessLevel(Enum):
    """健壮性级别"""

    BASIC = "basic"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


@dataclass
class RobustnessConfig:
    """健壮性配置"""

    level: RobustnessLevel = RobustnessLevel.ENHANCED
    enable_error_recovery: bool = True
    enable_input_validation: bool = True
    enable_performance_monitoring: bool = True
    enable_security_checks: bool = True
    enable_detailed_logging: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout_seconds: float = 30.0
    cache_size: int = 1000
    log_level: str = "INFO"


@dataclass
class OperationMetrics:
    """操作指标"""

    operation_name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    success: bool = False
    error_count: int = 0
    retry_count: int = 0
    memory_usage: float | None = None
    cpu_usage: float | None = None
    validation_errors: list[str] = field(default_factory=list)
    security_warnings: list[str] = field(default_factory=list)


class RobustnessEnhancer:
    """代码健壮性增强器"""

    _instance: Optional["RobustnessEnhancer"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "RobustnessEnhancer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.config = RobustnessConfig()
        self.error_handler = GlobalErrorHandler()
        self.input_validator = InputValidator()
        self.metrics: dict[str, OperationMetrics] = {}
        self.operation_cache: dict[str, Any] = {}
        self._metrics_lock = threading.RLock()

        # 性能监控
        self.performance_monitor = PerformanceMonitor()

        # 安全监控
        self.security_monitor = SecurityMonitor()

        self._initialized = True
        logger.info("代码健壮性增强器初始化完成")

    def configure(self, config: RobustnessConfig) -> None:
        """配置增强器"""
        self.config = config
        logger.info(f"健壮性增强器配置更新: {config.level.value}")

    def enhance_function(
        self,
        func: Callable,
        operation_name: str | None = None,
        validation_rules: dict[str, ValidatorChain] | None = None,
        security_level: str = "medium",
        enable_caching: bool = False,
        enable_retry: bool = True,
        timeout: float | None = None,
    ) -> Callable:
        """增强函数健壮性"""

        operation_name = operation_name or func.__name__

        @functools.wraps(func)
        def enhanced_wrapper(*args, **kwargs):
            return self._execute_with_enhancement(
                func,
                args,
                kwargs,
                operation_name,
                validation_rules,
                security_level,
                enable_caching,
                enable_retry,
                timeout,
            )

        return enhanced_wrapper

    def _execute_with_enhancement(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        operation_name: str,
        validation_rules: dict[str, ValidatorChain] | None = None,
        security_level: str = "medium",
        enable_caching: bool = False,
        enable_retry: bool = True,
        timeout: float | None = None,
    ) -> Any:
        """执行增强的操作"""

        # 开始指标收集
        metrics = self._start_operation(operation_name)

        try:
            # 输入验证
            if self.config.enable_input_validation and validation_rules:
                self._validate_inputs(args, kwargs, validation_rules, metrics)

            # 安全检查
            if self.config.enable_security_checks:
                self._perform_security_checks(args, kwargs, security_level, metrics)

            # 缓存检查
            cache_key = None
            if enable_caching:
                cache_key = self._generate_cache_key(func, args, kwargs)
                if cache_key in self.operation_cache:
                    logger.debug(f"缓存命中: {operation_name}")
                    return self.operation_cache[cache_key]

            # 执行操作（带重试）
            result = self._execute_with_retry(
                func, args, kwargs, operation_name, enable_retry, timeout, metrics
            )

            # 缓存结果
            if enable_caching and cache_key:
                self.operation_cache[cache_key] = result
                # 限制缓存大小
                if len(self.operation_cache) > self.config.cache_size:
                    # 移除最旧的条目
                    oldest_key = next(iter(self.operation_cache))
                    del self.operation_cache[oldest_key]

            # 标记成功
            metrics.success = True

            return result

        except Exception as e:
            # 错误处理
            metrics.error_count += 1
            self._handle_operation_error(e, operation_name, metrics)
            raise

        finally:
            # 完成指标收集
            self._finish_operation(metrics)

    def _start_operation(self, operation_name: str) -> OperationMetrics:
        """开始操作指标收集"""
        metrics = OperationMetrics(
            operation_name=operation_name, start_time=time.time()
        )

        with self._metrics_lock:
            self.metrics[operation_name] = metrics

        logger.debug(f"开始操作: {operation_name}")
        return metrics

    def _finish_operation(self, metrics: OperationMetrics) -> None:
        """完成操作指标收集"""
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time

        # 记录性能指标
        if self.config.enable_performance_monitoring:
            self.performance_monitor.record_operation(metrics)

        # 记录日志
        if self.config.enable_detailed_logging:
            self._log_operation_completion(metrics)

    def _validate_inputs(
        self,
        args: tuple,
        kwargs: dict,
        validation_rules: dict[str, ValidatorChain],
        metrics: OperationMetrics,
    ) -> None:
        """验证输入"""
        try:
            # 验证位置参数
            for i, arg in enumerate(args):
                param_name = f"arg_{i}"
                if param_name in validation_rules:
                    result = validation_rules[param_name].validate(arg)
                if not result.is_valid:
                    metrics.validation_errors.extend(
                        [str(error) for error in result.errors]
                    )

            # 验证关键字参数
            for param_name, value in kwargs.items():
                if param_name in validation_rules:
                    result = validation_rules[param_name].validate(value)
                if not result.is_valid:
                    metrics.validation_errors.extend(
                        [str(error) for error in result.errors]
                    )

            # 如果有验证错误，抛出异常
            if metrics.validation_errors:
                raise ValueError(
                    f"输入验证失败: {'; '.join(metrics.validation_errors)}"
                )

        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            raise

    def _perform_security_checks(
        self, args: tuple, kwargs: dict, security_level: str, metrics: OperationMetrics
    ) -> None:
        """执行安全检查"""
        try:
            # 检查所有字符串输入
            all_inputs = list(args) + list(kwargs.values())

            for input_value in all_inputs:
                if isinstance(input_value, str):
                    # 基本安全检查
                    try:
                        is_valid, error_msg = (
                            self.input_validator.validate_experiment_name(input_value)
                        )
                        if not is_valid:
                            warning = f"检测到潜在危险内容: {input_value[:50]}... - {error_msg}"
                            metrics.security_warnings.append(warning)
                            logger.warning(warning)
                    except Exception:
                        pass

                    # 高级安全检查
                    if security_level == "high":
                        try:
                            is_valid, error_msg = (
                                self.input_validator.validate_experiment_name(
                                    input_value
                                )
                            )
                            if not is_valid:
                                raise SecurityError(
                                    f"检测到安全威胁: {input_value} - {error_msg}"
                                )
                        except Exception:
                            pass

        except Exception as e:
            logger.error(f"安全检查失败: {e}")
            raise

    def _execute_with_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        operation_name: str,
        enable_retry: bool,
        timeout: float | None,
        metrics: OperationMetrics,
    ) -> Any:
        """执行操作（带重试）"""
        max_attempts = self.config.max_retry_attempts if enable_retry else 1
        timeout_value = timeout or self.config.timeout_seconds

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    metrics.retry_count = attempt
                    logger.info(f"重试操作 {operation_name} (第 {attempt + 1} 次)")
                    time.sleep(self.config.retry_delay * attempt)

                # 执行操作
                if asyncio.iscoroutinefunction(func):
                    # 异步函数
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(
                        asyncio.wait_for(func(*args, **kwargs), timeout=timeout_value)
                    )
                else:
                    # 同步函数
                    return func(*args, **kwargs)

            except Exception as e:
                if attempt == max_attempts - 1:
                    # 最后一次尝试失败
                    raise
                else:
                    # 记录错误但继续重试
                    logger.warning(
                        f"操作 {operation_name} 第 {attempt + 1} 次尝试失败: {e}"
                    )
                    continue

    def _handle_operation_error(
        self, error: Exception, operation_name: str, metrics: OperationMetrics
    ) -> None:
        """处理操作错误"""
        # 转换为应用异常
        if not isinstance(error, BaseAppException):
            app_error = BaseAppException(
                message=str(error),
                original_exception=error,
                user_message=f"操作 {operation_name} 失败",
            )
        else:
            app_error = error

        # 使用全局错误处理器
        self.error_handler.handle_exception(app_error, operation_name)

        # 记录错误指标
        metrics.error_count += 1

    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        import hashlib

        # 创建函数的唯一标识
        func_id = f"{func.__module__}.{func.__name__}"

        # 序列化参数
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))

        # 生成哈希
        content = f"{func_id}:{args_str}:{kwargs_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _log_operation_completion(self, metrics: OperationMetrics) -> None:
        """记录操作完成日志"""
        status = "成功" if metrics.success else "失败"

        log_data = {
            "operation": metrics.operation_name,
            "duration": metrics.duration,
            "status": status,
            "retry_count": metrics.retry_count,
            "error_count": metrics.error_count,
        }

        if metrics.validation_errors:
            log_data["validation_errors"] = metrics.validation_errors

        if metrics.security_warnings:
            log_data["security_warnings"] = metrics.security_warnings

        if metrics.success:
            logger.info(f"操作完成: {log_data}")
        else:
            logger.error(f"操作失败: {log_data}")

    def get_operation_metrics(self, operation_name: str) -> OperationMetrics | None:
        """获取操作指标"""
        with self._metrics_lock:
            return self.metrics.get(operation_name)

    def get_all_metrics(self) -> dict[str, OperationMetrics]:
        """获取所有操作指标"""
        with self._metrics_lock:
            return self.metrics.copy()

    def clear_metrics(self) -> None:
        """清除指标"""
        with self._metrics_lock:
            self.metrics.clear()

    def generate_robustness_report(self) -> str:
        """生成健壮性报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 代码健壮性报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"配置级别: {self.config.level.value}")
        report.append("")

        # 操作统计
        total_operations = len(self.metrics)
        successful_operations = sum(1 for m in self.metrics.values() if m.success)
        failed_operations = total_operations - successful_operations

        report.append("## 操作统计")
        report.append(f"总操作数: {total_operations}")
        report.append(f"成功操作: {successful_operations}")
        report.append(f"失败操作: {failed_operations}")
        report.append(
            f"成功率: {(successful_operations / total_operations * 100):.1f}%"
            if total_operations > 0
            else "N/A"
        )
        report.append("")

        # 性能统计
        if self.metrics:
            durations = [
                m.duration for m in self.metrics.values() if m.duration is not None
            ]
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)

                report.append("## 性能统计")
                report.append(f"平均执行时间: {avg_duration:.3f}秒")
                report.append(f"最长执行时间: {max_duration:.3f}秒")
                report.append(f"最短执行时间: {min_duration:.3f}秒")
                report.append("")

        # 错误统计
        total_errors = sum(m.error_count for m in self.metrics.values())
        total_retries = sum(m.retry_count for m in self.metrics.values())

        report.append("## 错误统计")
        report.append(f"总错误数: {total_errors}")
        report.append(f"总重试数: {total_retries}")
        report.append("")

        # 安全统计
        total_security_warnings = sum(
            len(m.security_warnings) for m in self.metrics.values()
        )
        report.append("## 安全统计")
        report.append(f"安全警告数: {total_security_warnings}")
        report.append("")

        return "\n".join(report)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.operation_times: dict[str, list[float]] = {}
        self.memory_usage: list[float] = []
        self.cpu_usage: list[float] = []

    def record_operation(self, metrics: OperationMetrics) -> None:
        """记录操作性能"""
        if metrics.duration is not None:
            if metrics.operation_name not in self.operation_times:
                self.operation_times[metrics.operation_name] = []
            self.operation_times[metrics.operation_name].append(metrics.duration)

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        summary = {}

        for operation, times in self.operation_times.items():
            if times:
                summary[operation] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                }

        return summary


class SecurityMonitor:
    """安全监控器"""

    def __init__(self):
        self.security_events: list[dict[str, Any]] = []
        self.threat_detections: list[dict[str, Any]] = []

    def record_security_event(self, event_type: str, details: dict[str, Any]) -> None:
        """记录安全事件"""
        event = {"timestamp": time.time(), "type": event_type, "details": details}
        self.security_events.append(event)

    def get_security_summary(self) -> dict[str, Any]:
        """获取安全摘要"""
        return {
            "total_events": len(self.security_events),
            "recent_events": self.security_events[-10:] if self.security_events else [],
        }


class SecurityError(Exception):
    """安全错误"""

    pass


# 全局实例
robustness_enhancer = RobustnessEnhancer()


def enhance_function(
    operation_name: str | None = None,
    validation_rules: dict[str, ValidatorChain] | None = None,
    security_level: str = "medium",
    enable_caching: bool = False,
    enable_retry: bool = True,
    timeout: float | None = None,
):
    """函数增强装饰器"""

    def decorator(func: Callable) -> Callable:
        return robustness_enhancer.enhance_function(
            func,
            operation_name,
            validation_rules,
            security_level,
            enable_caching,
            enable_retry,
            timeout,
        )

    return decorator


@contextmanager
def robustness_context(operation_name: str, **_kwargs):
    """健壮性上下文管理器"""
    metrics = robustness_enhancer._start_operation(operation_name)
    try:
        yield metrics
    except Exception as e:
        robustness_enhancer._handle_operation_error(e, operation_name, metrics)
        raise
    finally:
        robustness_enhancer._finish_operation(metrics)


def get_robustness_enhancer() -> RobustnessEnhancer:
    """获取健壮性增强器实例"""
    return robustness_enhancer
