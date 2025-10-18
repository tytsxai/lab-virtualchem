"""
中间件管道 (Middleware Pipeline)

提供类似ASP.NET Core的中间件管道系统：
- 责任链模式
- 异步中间件支持
- 上下文传递
- 错误处理
- 性能监控
"""

import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class MiddlewareContext:
    """中间件上下文"""

    request: Any
    response: Any | None = None
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_time(self) -> float:
        """获取已消耗时间（秒）"""
        return time.time() - self.start_time

    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """检查上下文数据是否存在"""
        return key in self.data

    def add_error(self, error: Exception):
        """添加错误"""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0


class Middleware(ABC):
    """中间件基类"""

    @abstractmethod
    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        """
        调用中间件

        Args:
            context: 中间件上下文
            next_middleware: 下一个中间件

        Returns:
            处理结果
        """
        pass


class MiddlewarePipeline:
    """中间件管道"""

    def __init__(self):
        self._middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> "MiddlewarePipeline":
        """
        添加中间件

        Args:
            middleware: 中间件实例

        Returns:
            self（支持链式调用）

        Examples:
            pipeline = MiddlewarePipeline()
            pipeline.use(LoggingMiddleware())
            pipeline.use(AuthenticationMiddleware())
            pipeline.use(ValidationMiddleware())
        """
        self._middleware.append(middleware)
        return self

    async def execute(self, request: Any, final_handler: Callable[[Any], Any]) -> Any:
        """
        执行管道

        Args:
            request: 请求对象
            final_handler: 最终处理器

        Returns:
            处理结果

        Examples:
            async def handler(req):
                return {"result": "success"}

            result = await pipeline.execute(request, handler)
        """
        context = MiddlewareContext(request=request)

        # 构建中间件链
        async def build_chain(index: int):
            if index >= len(self._middleware):
                # 到达链的末端，调用最终处理器
                if asyncio.iscoroutinefunction(final_handler):
                    return await final_handler(context.request)
                else:
                    return final_handler(context.request)
            else:
                # 调用当前中间件
                middleware = self._middleware[index]

                def next_func():
                    return build_chain(index + 1)

                return await middleware.invoke(context, next_func)

        result = await build_chain(0)
        context.response = result

        return result

    def clear(self):
        """清空管道"""
        self._middleware.clear()


# 内置中间件


class LoggingMiddleware(Middleware):
    """日志中间件"""

    def __init__(self, logger: Callable | None = None):
        self.logger = logger or print

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        start_time = time.time()

        self.logger(f"[Middleware] Request started: {context.request}")

        try:
            result = await next_middleware()
            elapsed = time.time() - start_time
            self.logger(f"[Middleware] Request completed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger(f"[Middleware] Request failed in {elapsed:.3f}s: {str(e)}")
            raise


class ErrorHandlingMiddleware(Middleware):
    """错误处理中间件"""

    def __init__(self, error_handler: Callable | None = None):
        self.error_handler = error_handler

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        try:
            return await next_middleware()
        except Exception as e:
            context.add_error(e)

            if self.error_handler:
                return self.error_handler(e, context)
            else:
                # 默认错误处理
                return {
                    "success": False,
                    "error": str(e),
                    "type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }


class PerformanceMiddleware(Middleware):
    """性能监控中间件"""

    def __init__(self, threshold_ms: float = 1000):
        self.threshold_ms = threshold_ms

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        start_time = time.time()

        result = await next_middleware()

        elapsed_ms = (time.time() - start_time) * 1000
        context.set("elapsed_ms", elapsed_ms)

        if elapsed_ms > self.threshold_ms:
            print(f"⚠️ Performance warning: Request took {elapsed_ms:.2f}ms (threshold: {self.threshold_ms}ms)")

        return result


class CachingMiddleware(Middleware):
    """缓存中间件"""

    def __init__(self, cache_key_func: Callable[[Any], str]):
        self.cache_key_func = cache_key_func
        self.cache: dict[str, Any] = {}

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        cache_key = self.cache_key_func(context.request)

        # 检查缓存
        if cache_key in self.cache:
            context.set("cached", True)
            return self.cache[cache_key]

        # 执行并缓存
        result = await next_middleware()
        self.cache[cache_key] = result
        context.set("cached", False)

        return result

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()


class ValidationMiddleware(Middleware):
    """验证中间件"""

    def __init__(self, validator: Callable[[Any], bool]):
        self.validator = validator

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        if not self.validator(context.request):
            raise ValueError("Validation failed")

        return await next_middleware()


class RateLimitMiddleware(Middleware):
    """限流中间件"""

    def __init__(
        self,
        max_requests: int = 100,
        time_window: float = 60.0,  # 秒
        key_func: Callable[[Any], str] | None = None,
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.key_func = key_func or (lambda _req: "global")
        self.requests: dict[str, list[float]] = {}

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        key = self.key_func(context.request)
        now = time.time()

        # 获取该键的请求记录
        if key not in self.requests:
            self.requests[key] = []

        # 清理过期记录
        cutoff = now - self.time_window
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

        # 检查限流
        if len(self.requests[key]) >= self.max_requests:
            raise Exception(
                f"Rate limit exceeded: {len(self.requests[key])} requests "
                f"in {self.time_window}s (max: {self.max_requests})"
            )

        # 记录请求
        self.requests[key].append(now)

        return await next_middleware()


class AuthenticationMiddleware(Middleware):
    """认证中间件"""

    def __init__(self, auth_func: Callable[[Any], bool]):
        self.auth_func = auth_func

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        if not self.auth_func(context.request):
            raise PermissionError("Authentication failed")

        context.set("authenticated", True)
        return await next_middleware()


class TransformMiddleware(Middleware):
    """转换中间件"""

    def __init__(self, request_transform: Callable | None = None, response_transform: Callable | None = None):
        self.request_transform = request_transform
        self.response_transform = response_transform

    async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
        # 转换请求
        if self.request_transform:
            context.request = self.request_transform(context.request)

        # 执行下一个中间件
        result = await next_middleware()

        # 转换响应
        if self.response_transform:
            result = self.response_transform(result)

        return result


# 示例用法
if __name__ == "__main__":
    # 自定义中间件
    class CustomMiddleware(Middleware):
        async def invoke(self, context: MiddlewareContext, next_middleware: Callable) -> Any:
            logger.info(f"Before: {context.request}")
            result = await next_middleware()
            logger.info(f"After: {result}")
            return result

    # 创建管道
    async def example():
        pipeline = MiddlewarePipeline()

        # 添加中间件（执行顺序）
        pipeline.use(LoggingMiddleware())
        pipeline.use(ErrorHandlingMiddleware())
        pipeline.use(PerformanceMiddleware(threshold_ms=100))
        pipeline.use(CustomMiddleware())

        # 最终处理器
        async def handler(request):
            await asyncio.sleep(0.05)  # 模拟处理
            return {"result": f"Processed: {request}"}

        # 执行
        result = await pipeline.execute("test request", handler)
        logger.info(f"Result: {result}")

    # 运行示例
    asyncio.run(example())
