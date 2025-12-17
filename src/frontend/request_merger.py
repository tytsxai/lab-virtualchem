"""
请求合并器
将多个API请求合并为批量请求，减少网络开销
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PendingRequest:
    """待处理请求"""

    id: str
    endpoint: str
    params: dict[str, Any]
    callback: Callable
    error_callback: Callable | None = None
    timestamp: datetime = field(default_factory=datetime.now)


class RequestMerger:
    """请求合并器 - 批量处理相似请求"""

    def __init__(
        self,
        batch_size: int = 10,
        batch_timeout: float = 0.1,  # 秒
        executor: Callable | None = None,
    ):
        """
        初始化请求合并器

        Args:
            batch_size: 批次大小
            batch_timeout: 批次超时(秒)
            executor: 批量执行器函数
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.executor = executor

        # 按端点分组的待处理请求
        self._pending: dict[str, list[PendingRequest]] = defaultdict(list)

        # 定时器
        self._timers: dict[str, asyncio.Task] = {}

    async def add_request(
        self,
        request_id: str,
        endpoint: str,
        params: dict[str, Any],
        callback: Callable,
        error_callback: Callable | None = None,
    ) -> None:
        """
        添加请求到批次

        Args:
            request_id: 请求ID
            endpoint: API端点
            params: 请求参数
            callback: 成功回调
            error_callback: 错误回调
        """
        request = PendingRequest(
            id=request_id,
            endpoint=endpoint,
            params=params,
            callback=callback,
            error_callback=error_callback,
        )

        self._pending[endpoint].append(request)

        # 检查是否达到批次大小
        if len(self._pending[endpoint]) >= self.batch_size:
            await self._flush_endpoint(endpoint)
        else:
            # 设置超时定时器
            if endpoint not in self._timers:
                self._timers[endpoint] = asyncio.create_task(
                    self._schedule_flush(endpoint)
                )

        logger.debug(
            f"添加请求到批次: {endpoint}, 当前: {len(self._pending[endpoint])}"
        )

    async def _schedule_flush(self, endpoint: str) -> None:
        """
        调度刷新

        Args:
            endpoint: 端点
        """
        await asyncio.sleep(self.batch_timeout)
        await self._flush_endpoint(endpoint)

    async def _flush_endpoint(self, endpoint: str) -> None:
        """
        刷新端点的所有待处理请求

        Args:
            endpoint: 端点
        """
        if endpoint not in self._pending or not self._pending[endpoint]:
            return

        # 获取并清空待处理请求
        requests = self._pending[endpoint]
        self._pending[endpoint] = []

        # 取消定时器
        if endpoint in self._timers:
            self._timers[endpoint].cancel()
            del self._timers[endpoint]

        logger.info(f"刷新批次: {endpoint}, 数量: {len(requests)}")

        try:
            # 执行批量请求
            if self.executor:
                results = await self.executor(endpoint, requests)

                # 分发结果
                for request, result in zip(requests, results, strict=False):
                    if result.get("success"):
                        request.callback(result.get("data"))
                    else:
                        if request.error_callback:
                            request.error_callback(result.get("error"))

        except Exception as e:
            logger.error(f"批量请求执行失败: {e}", exc_info=True)

            # 错误回调
            for request in requests:
                if request.error_callback:
                    request.error_callback(str(e))

    async def flush_all(self) -> None:
        """刷新所有待处理请求"""
        endpoints = list(self._pending.keys())
        for endpoint in endpoints:
            await self._flush_endpoint(endpoint)


class DataLoader:
    """数据加载器 - 支持批量加载和缓存"""

    def __init__(self, batch_loader: Callable):
        """
        初始化数据加载器

        Args:
            batch_loader: 批量加载函数 (keys) -> Dict[key, value]
        """
        self.batch_loader = batch_loader
        self._cache: dict[str, Any] = {}
        self._pending: dict[str, list[Callable]] = defaultdict(list)
        self._batch_task: asyncio.Task | None = None

    async def load(self, key: str) -> Any:
        """
        加载数据

        Args:
            key: 数据键

        Returns:
            数据值
        """
        # 从缓存获取
        if key in self._cache:
            return self._cache[key]

        # 创建Future
        future = asyncio.Future()
        self._pending[key].append(future.set_result)

        # 调度批量加载
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._load_batch())

        return await future

    async def load_many(self, keys: list[str]) -> dict[str, Any]:
        """
        批量加载多个数据

        Args:
            keys: 数据键列表

        Returns:
            键值对字典
        """
        results = {}
        tasks = [self.load(key) for key in keys]
        values = await asyncio.gather(*tasks)

        for key, value in zip(keys, values, strict=False):
            results[key] = value

        return results

    async def _load_batch(self) -> None:
        """执行批量加载"""
        # 等待一小段时间，收集更多请求
        await asyncio.sleep(0.01)

        # 获取待加载的键
        keys = list(self._pending.keys())
        if not keys:
            return

        try:
            # 批量加载
            results = await self.batch_loader(keys)

            # 更新缓存并触发回调
            for key in keys:
                value = results.get(key)
                self._cache[key] = value

                # 触发所有等待的回调
                for callback in self._pending[key]:
                    callback(value)

                del self._pending[key]

        except Exception as e:
            logger.error(f"批量加载失败: {e}", exc_info=True)

            # 错误处理
            for key in keys:
                for callback in self._pending[key]:
                    callback(None)
                del self._pending[key]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def prime(self, key: str, value: Any) -> None:
        """
        预填充缓存

        Args:
            key: 键
            value: 值
        """
        self._cache[key] = value


class RequestDeduplicator:
    """请求去重器 - 避免重复请求"""

    def __init__(self):
        self._in_flight: dict[str, asyncio.Task] = {}

    async def request(self, key: str, executor: Callable) -> Any:
        """
        发起请求（自动去重）

        Args:
            key: 请求标识
            executor: 执行函数

        Returns:
            请求结果
        """
        # 如果请求正在进行中，等待结果
        if key in self._in_flight:
            logger.debug(f"请求去重: {key}")
            return await self._in_flight[key]

        # 创建新请求
        task = asyncio.create_task(executor())
        self._in_flight[key] = task

        try:
            result = await task
            return result
        finally:
            # 清理
            if key in self._in_flight:
                del self._in_flight[key]


class RequestQueue:
    """请求队列 - 控制并发请求数"""

    def __init__(self, max_concurrent: int = 6):
        """
        初始化请求队列

        Args:
            max_concurrent: 最大并发请求数
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: list[Callable] = []

    async def enqueue(self, executor: Callable) -> Any:
        """
        将请求加入队列

        Args:
            executor: 执行函数

        Returns:
            执行结果
        """
        async with self._semaphore:
            return await executor()


# 全局实例
_request_merger: RequestMerger | None = None
_data_loader_registry: dict[str, DataLoader] = {}


def get_request_merger() -> RequestMerger:
    """获取全局请求合并器"""
    global _request_merger
    if _request_merger is None:
        _request_merger = RequestMerger()
    return _request_merger


def register_data_loader(name: str, loader: DataLoader) -> None:
    """
    注册数据加载器

    Args:
        name: 加载器名称
        loader: 加载器实例
    """
    _data_loader_registry[name] = loader


def get_data_loader(name: str) -> DataLoader | None:
    """
    获取数据加载器

    Args:
        name: 加载器名称

    Returns:
        加载器实例或None
    """
    return _data_loader_registry.get(name)


if __name__ == "__main__":
    # 演示使用
    async def demo():
        logger.info("=== 请求合并演示 ===\n")

        # 1. 批量执行器
        async def batch_executor(endpoint, requests):
            logger.info(f"执行批量请求: {endpoint}, 数量: {len(requests)}")
            # 模拟API调用
            await asyncio.sleep(0.1)
            return [{"success": True, "data": f"Result {r.id}"} for r in requests]

        # 2. 创建合并器
        merger = RequestMerger(batch_size=5, batch_timeout=0.2, executor=batch_executor)

        # 3. 添加请求
        results = []

        def callback(data):
            results.append(data)
            logger.info(f"收到结果: {data}")

        for i in range(12):
            await merger.add_request(f"req_{i}", "/api/data", {"id": i}, callback)

        # 等待处理完成
        await asyncio.sleep(0.5)

        logger.info(f"\n总共收到 {len(results)} 个结果")

    # 运行演示
    asyncio.run(demo())
