"""
弹性和容错系统

提供限流、熔断器、重试等弹性机制
"""

import asyncio
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 失败阈值
    success_threshold: int = 2  # 成功阈值（半开状态）
    timeout_seconds: int = 60  # 熔断超时
    window_size: int = 100  # 滑动窗口大小


@dataclass
class RateLimiterConfig:
    """限流器配置"""

    max_requests: int = 100  # 最大请求数
    window_seconds: int = 60  # 时间窗口（秒）


@dataclass
class RetryConfig:
    """重试配置"""

    max_attempts: int = 3  # 最大重试次数
    initial_delay: float = 1.0  # 初始延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加抖动


class CircuitBreakerException(Exception):
    """熔断器异常"""

    pass


class RateLimitException(Exception):
    """限流异常"""

    pass


class CircuitBreaker:
    """熔断器"""

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            # 检查是否应该从OPEN转换到HALF_OPEN
            if self._state == CircuitState.OPEN and self._last_failure_time:
                timeout = timedelta(seconds=self.config.timeout_seconds)
                if datetime.now() - self._last_failure_time > timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0

            return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """执行函数调用"""
        state = self.state

        if state == CircuitState.OPEN:
            raise CircuitBreakerException("熔断器开启，拒绝请求")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    async def async_call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """异步执行函数调用"""
        state = self.state

        if state == CircuitState.OPEN:
            raise CircuitBreakerException("熔断器开启，拒绝请求")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """成功回调"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _on_failure(self) -> None:
        """失败回调"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """重置熔断器"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


class RateLimiter:
    """限流器（令牌桶算法）"""

    def __init__(self, config: RateLimiterConfig | None = None):
        self.config = config or RateLimiterConfig()
        self._tokens = float(self.config.max_requests)
        self._last_update = time.time()
        self._lock = threading.Lock()

        # 计算令牌生成速率（每秒）
        self._rate = self.config.max_requests / self.config.window_seconds

    def acquire(self, tokens: int = 1) -> bool:
        """获取令牌"""
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def async_acquire(self, tokens: int = 1) -> bool:
        """异步获取令牌"""
        return self.acquire(tokens)

    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_update

        # 添加新令牌
        self._tokens = min(self.config.max_requests, self._tokens + elapsed * self._rate)

        self._last_update = now

    def wait_time(self) -> float:
        """获取需要等待的时间"""
        with self._lock:
            self._refill()

            if self._tokens >= 1:
                return 0.0

            # 计算需要等待的时间
            tokens_needed = 1 - self._tokens
            return tokens_needed / self._rate


class SlidingWindowRateLimiter:
    """滑动窗口限流器"""

    def __init__(self, config: RateLimiterConfig | None = None):
        self.config = config or RateLimiterConfig()
        self._requests: deque = deque()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """获取许可"""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.config.window_seconds)

            # 移除过期请求
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            # 检查是否超过限制
            if len(self._requests) < self.config.max_requests:
                self._requests.append(now)
                return True

            return False


class Retry:
    """重试机制"""

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()

    def execute(self, func: Callable[..., T], *args, retry_on: tuple = (Exception,), **kwargs) -> T:
        """执行带重试的函数"""
        last_exception = None
        delay = self.config.initial_delay

        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                last_exception = e

                if attempt < self.config.max_attempts - 1:
                    # 计算延迟
                    actual_delay = min(delay, self.config.max_delay)

                    # 添加抖动
                    if self.config.jitter:
                        import random

                        actual_delay *= 0.5 + random.random()

                    time.sleep(actual_delay)

                    # 指数退避
                    delay *= self.config.exponential_base

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("重试失败，没有异常信息")

    async def async_execute(self, func: Callable[..., T], *args, retry_on: tuple = (Exception,), **kwargs) -> Union[T, Any]:
        """异步执行带重试的函数"""
        last_exception = None
        delay = self.config.initial_delay

        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                    return result
                else:
                    result = func(*args, **kwargs)
                    return result
            except retry_on as e:
                last_exception = e

                if attempt < self.config.max_attempts - 1:
                    actual_delay = min(delay, self.config.max_delay)

                    if self.config.jitter:
                        import random

                        actual_delay *= 0.5 + random.random()

                    await asyncio.sleep(actual_delay)
                    delay *= self.config.exponential_base

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("异步重试失败，没有异常信息")


class Bulkhead:
    """舱壁隔离（资源隔离）"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._async_semaphore = asyncio.Semaphore(max_concurrent)

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """执行函数（资源隔离）"""
        with self._semaphore:
            return func(*args, **kwargs)

    async def async_execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """异步执行函数（资源隔离）"""
        async with self._async_semaphore:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)


# 装饰器
def circuit_breaker(config: CircuitBreakerConfig | None = None):
    """熔断器装饰器"""
    breaker = CircuitBreaker(config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.async_call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def rate_limit(config: RateLimiterConfig | None = None):
    """限流装饰器"""
    limiter = RateLimiter(config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not await limiter.async_acquire():
                raise RateLimitException("请求频率超过限制")
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not limiter.acquire():
                raise RateLimitException("请求频率超过限制")
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry(config: RetryConfig | None = None, retry_on: tuple = (Exception,)):
    """重试装饰器"""
    retry_handler = Retry(config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_handler.async_execute(func, *args, retry_on=retry_on, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return retry_handler.execute(func, *args, retry_on=retry_on, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def demo():
    """演示"""
    logger.info("=== 弹性和容错系统演示 ===\n")

    # 1. 熔断器
    logger.info("1. 熔断器演示:")
    breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, timeout_seconds=2))

    def unreliable_service():
        import random

        if random.random() < 0.7:  # 70% 失败率
            raise Exception("服务异常")
        return "成功"

    for i in range(10):
        try:
            result = breaker.call(unreliable_service)
            logger.info(f"  请求 {i + 1}: {result}, 状态: {breaker.state.value}")
        except CircuitBreakerException:
            logger.info(f"  请求 {i + 1}: 熔断拒绝, 状态: {breaker.state.value}")
        except Exception:
            logger.info(f"  请求 {i + 1}: 失败, 状态: {breaker.state.value}")

        await asyncio.sleep(0.1)

    # 2. 限流器
    logger.info("\n2. 限流器演示:")
    limiter = RateLimiter(RateLimiterConfig(max_requests=5, window_seconds=2))

    for i in range(10):
        if limiter.acquire():
            logger.info(f"  请求 {i + 1}: ✅ 允许")
        else:
            wait = limiter.wait_time()
            logger.info(f"  请求 {i + 1}: ❌ 限流 (需要等待 {wait:.2f}秒)")

        await asyncio.sleep(0.1)

    # 3. 重试机制
    logger.info("\n3. 重试机制演示:")
    retry_handler = Retry(RetryConfig(max_attempts=3, initial_delay=0.5))

    attempt_count = 0

    def flaky_service():
        nonlocal attempt_count
        attempt_count += 1
        logger.info(f"  尝试 {attempt_count}")

        if attempt_count < 3:
            raise Exception("暂时失败")
        return "最终成功"

    try:
        result = retry_handler.execute(flaky_service)
        logger.info(f"  结果: {result}")
    except Exception as e:
        logger.info(f"  失败: {e}")

    # 4. 装饰器使用
    logger.info("\n4. 装饰器演示:")

    @circuit_breaker(CircuitBreakerConfig(failure_threshold=2))
    @rate_limit(RateLimiterConfig(max_requests=3, window_seconds=1))
    @retry(RetryConfig(max_attempts=2))
    async def protected_function(x: int):
        if x % 3 == 0:
            raise Exception("业务异常")
        return f"处理: {x}"

    for i in range(5):
        try:
            result = await protected_function(i)
            logger.info(f"  {result}")
        except Exception as e:
            logger.info(f"  错误: {type(e).__name__}")

        await asyncio.sleep(0.3)

    logger.info("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(demo())
