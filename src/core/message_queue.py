"""
消息队列系统

支持异步任务处理、消息重试、死信队列等
"""

import asyncio
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import PriorityQueue
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MessagePriority(Enum):
    """消息优先级"""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class MessageStatus(Enum):
    """消息状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD = "dead"


@dataclass
class Message(Generic[T]):
    """消息"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    data: T = None
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    delay: int | None = None  # 延迟秒数
    scheduled_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """用于优先队列排序"""
        return self.priority.value < other.priority.value


class IMessageHandler(ABC, Generic[T]):
    """消息处理器接口"""

    @abstractmethod
    async def handle(self, message: Message[T]) -> None:
        """处理消息"""
        pass

    @abstractmethod
    async def on_error(self, message: Message[T], error: Exception) -> None:
        """错误处理"""
        pass


class BaseMessageHandler(IMessageHandler[T]):
    """基础消息处理器"""

    async def handle(self, message: Message[T]) -> None:
        """默认处理逻辑"""
        logger.info(f"处理消息: {message.id}, 主题: {message.topic}")

    async def on_error(self, message: Message[T], error: Exception) -> None:
        """默认错误处理"""
        logger.error(f"消息处理失败: {message.id}, 错误: {error}")


class IMessageQueue(ABC, Generic[T]):
    """消息队列接口"""

    @abstractmethod
    async def publish(self, message: Message[T]) -> str:
        """发布消息"""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: IMessageHandler[T]) -> None:
        """订阅主题"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动队列"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止队列"""
        pass


class InMemoryMessageQueue(IMessageQueue[T]):
    """内存消息队列实现"""

    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self._queue: PriorityQueue = PriorityQueue()
        self._handlers: dict[str, list[IMessageHandler[T]]] = defaultdict(list)
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._dead_letter_queue: list[Message[T]] = []
        self._delayed_messages: list[Message[T]] = []
        self._lock = threading.Lock()

    async def publish(self, message: Message[T]) -> str:
        """发布消息"""
        # 检查是否需要延迟
        if message.delay:
            message.scheduled_at = datetime.now() + timedelta(seconds=message.delay)
            self._delayed_messages.append(message)
            logger.info(f"消息已调度延迟: {message.id}, 延迟: {message.delay}秒")
        else:
            self._queue.put(message)
            logger.info(f"消息已发布: {message.id}, 主题: {message.topic}")

        return message.id

    async def subscribe(self, topic: str, handler: IMessageHandler[T]) -> None:
        """订阅主题"""
        self._handlers[topic].append(handler)
        logger.info(f"已订阅主题: {topic}")

    async def start(self) -> None:
        """启动队列"""
        if self._running:
            return

        self._running = True

        # 启动工作线程
        for i in range(self.worker_count):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)

        # 启动延迟消息处理器
        delay_task = asyncio.create_task(self._delayed_processor())
        self._workers.append(delay_task)

        logger.info(f"消息队列已启动，工作线程数: {self.worker_count}")

    async def stop(self) -> None:
        """停止队列"""
        self._running = False

        # 等待所有工作线程完成
        for task in self._workers:
            task.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("消息队列已停止")

    async def _worker(self, worker_id: int) -> None:
        """工作线程"""
        logger.info(f"工作线程 {worker_id} 已启动")

        while self._running:
            try:
                # 从队列获取消息（非阻塞）
                if self._queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                message = self._queue.get_nowait()
                await self._process_message(message)

            except Exception as e:
                logger.error(f"工作线程 {worker_id} 错误: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: Message[T]) -> None:
        """处理消息"""
        message.status = MessageStatus.PROCESSING

        try:
            # 获取处理器
            handlers = self._handlers.get(message.topic, [])

            if not handlers:
                logger.warning(f"没有找到主题的处理器: {message.topic}")
                return

            # 执行所有处理器
            for handler in handlers:
                try:
                    await handler.handle(message)
                except Exception as e:
                    await handler.on_error(message, e)
                    raise

            message.status = MessageStatus.COMPLETED
            logger.info(f"消息处理完成: {message.id}")

        except Exception as e:
            message.error = str(e)
            message.retry_count += 1

            # 检查是否需要重试
            if message.retry_count < message.max_retries:
                message.status = MessageStatus.RETRY
                # 重新入队
                await asyncio.sleep(2**message.retry_count)  # 指数退避
                self._queue.put(message)
                logger.info(f"消息重试: {message.id}, 重试次数: {message.retry_count}")
            else:
                # 移入死信队列
                message.status = MessageStatus.DEAD
                self._dead_letter_queue.append(message)
                logger.error(f"消息进入死信队列: {message.id}, 错误: {e}")

    async def _delayed_processor(self) -> None:
        """延迟消息处理器"""
        while self._running:
            try:
                now = datetime.now()
                # 检查延迟消息
                ready_messages = [
                    msg
                    for msg in self._delayed_messages
                    if msg.scheduled_at and msg.scheduled_at <= now
                ]

                for msg in ready_messages:
                    self._delayed_messages.remove(msg)
                    self._queue.put(msg)
                    logger.info(f"延迟消息已就绪: {msg.id}")

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"延迟处理器错误: {e}")

    def get_dead_letters(self) -> list[Message[T]]:
        """获取死信队列"""
        return self._dead_letter_queue.copy()

    def requeue_dead_letter(self, message_id: str) -> bool:
        """重新入队死信消息"""
        for msg in self._dead_letter_queue:
            if msg.id == message_id:
                msg.status = MessageStatus.PENDING
                msg.retry_count = 0
                self._queue.put(msg)
                self._dead_letter_queue.remove(msg)
                logger.info(f"死信消息已重新入队: {message_id}")
                return True
        return False


class MessageRouter:
    """消息路由器"""

    def __init__(self):
        self._routes: dict[str, str] = {}  # pattern -> topic

    def add_route(self, pattern: str, topic: str) -> None:
        """添加路由"""
        self._routes[pattern] = topic

    def route(self, message: Message) -> str:
        """路由消息"""
        # 简单的模式匹配
        for pattern, topic in self._routes.items():
            if pattern in message.topic or pattern == "*":
                return topic
        return message.topic


class MessageFilter:
    """消息过滤器"""

    def __init__(self):
        self._filters: list[Callable[[Message], bool]] = []

    def add_filter(self, filter_func: Callable[[Message], bool]) -> None:
        """添加过滤器"""
        self._filters.append(filter_func)

    def should_process(self, message: Message) -> bool:
        """检查是否应该处理消息"""
        return all(f(message) for f in self._filters)


class TaskQueue:
    """任务队列（基于消息队列的简化接口）"""

    def __init__(self, queue: IMessageQueue):
        self.queue = queue

    async def enqueue(
        self,
        func: Callable,
        *args,
        priority: MessagePriority = MessagePriority.NORMAL,
        delay: int | None = None,
        **kwargs,
    ) -> str:
        """入队任务"""
        task_data = {"func": func.__name__, "args": args, "kwargs": kwargs}

        message = Message(topic="task", data=task_data, priority=priority, delay=delay)

        return await self.queue.publish(message)

    async def process_task(self, message: Message) -> None:
        """处理任务"""
        task_data = message.data
        # 这里需要一个函数注册表来查找实际的函数
        logger.info(f"处理任务: {task_data['func']}")


class BulkMessagePublisher:
    """批量消息发布器"""

    def __init__(self, queue: IMessageQueue, batch_size: int = 100):
        self.queue = queue
        self.batch_size = batch_size
        self._buffer: list[Message] = []
        self._lock = threading.Lock()

    async def add(self, message: Message) -> None:
        """添加消息到批次"""
        with self._lock:
            self._buffer.append(message)

            if len(self._buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self) -> None:
        """刷新缓冲区"""
        if not self._buffer:
            return

        messages = self._buffer.copy()
        self._buffer.clear()

        # 批量发布
        tasks = [self.queue.publish(msg) for msg in messages]
        await asyncio.gather(*tasks)

        logger.info(f"批量发布了 {len(messages)} 条消息")

    async def close(self) -> None:
        """关闭并刷新剩余消息"""
        await self._flush()


# 示例处理器
class ExperimentTaskHandler(BaseMessageHandler[dict[str, Any]]):
    """实验任务处理器"""

    async def handle(self, message: Message[dict[str, Any]]) -> None:
        """处理实验任务"""
        logger.info(f"开始处理实验: {message.data.get('experiment_id')}")

        # 模拟实验处理
        await asyncio.sleep(1)

        logger.info(f"实验处理完成: {message.data.get('experiment_id')}")


class ReportGenerationHandler(BaseMessageHandler[dict[str, Any]]):
    """报告生成处理器"""

    async def handle(self, message: Message[dict[str, Any]]) -> None:
        """生成报告"""
        logger.info(f"开始生成报告: {message.data.get('report_id')}")

        # 模拟报告生成
        await asyncio.sleep(2)

        logger.info(f"报告生成完成: {message.data.get('report_id')}")


async def demo():
    """演示"""
    logger.info("=== 消息队列系统演示 ===\n")

    # 创建队列
    queue = InMemoryMessageQueue[dict[str, Any]](worker_count=2)

    # 订阅主题
    await queue.subscribe("experiment.run", ExperimentTaskHandler())
    await queue.subscribe("report.generate", ReportGenerationHandler())

    # 启动队列
    await queue.start()

    # 发布消息
    logger.info("1. 发布普通消息:")
    msg1 = Message(
        topic="experiment.run",
        data={"experiment_id": "exp_001", "type": "titration"},
        priority=MessagePriority.HIGH,
    )
    await queue.publish(msg1)

    logger.info("\n2. 发布延迟消息:")
    msg2 = Message(topic="report.generate", data={"report_id": "rep_001"}, delay=3)
    await queue.publish(msg2)

    # 等待处理
    await asyncio.sleep(5)

    # 停止队列
    await queue.stop()

    logger.info("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(demo())
