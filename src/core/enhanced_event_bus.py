"""
增强事件总线
提供组件间的高效通信机制，支持事件订阅、发布和路由
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .error_handler import get_error_handler

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """事件对象"""

    name: str
    data: Any = None
    source: str | None = None
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "tags": self.tags,
        }


@dataclass
class EventSubscription:
    """事件订阅"""

    callback: Callable[[Event], None]
    event_name: str
    priority: EventPriority = EventPriority.NORMAL
    tags_filter: dict[str, str] | None = None
    once: bool = False
    subscriber_id: str | None = None

    def matches(self, event: Event) -> bool:
        """检查是否匹配事件"""
        # 检查事件名称
        if self.event_name != event.name:
            return False

        # 检查标签过滤
        if self.tags_filter:
            for key, value in self.tags_filter.items():
                if event.tags.get(key) != value:
                    return False

        return True


class EnhancedEventBus:
    """增强事件总线"""

    def __init__(self, max_queue_size: int = 10000):
        self._max_queue_size = max_queue_size
        self._subscriptions: dict[str, list[EventSubscription]] = defaultdict(list)
        self._global_subscriptions: list[EventSubscription] = []
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._worker_task: asyncio.Task | None = None
        self._lock = threading.RLock()
        self._error_handler = get_error_handler()

        # 统计信息
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "subscriptions_count": 0,
            "errors_count": 0,
        }

    def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return

        self._running = True

        # 创建事件循环
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            # 启动工作线程
            self._worker_task = self._event_loop.create_task(self._worker())

            logger.info("Enhanced event bus started")
        except Exception as e:
            self._running = False
            logger.error(f"Failed to start event bus: {e}")
            raise

    def stop(self) -> None:
        """停止事件总线"""
        if not self._running:
            return

        self._running = False

        # 停止工作线程
        if self._worker_task:
            self._worker_task.cancel()

        # 关闭事件循环
        if self._event_loop:
            self._event_loop.close()

        logger.info("Enhanced event bus stopped")

    async def _worker(self) -> None:
        """事件处理工作线程"""
        while self._running:
            try:
                # 等待事件
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                # 处理事件
                await self._process_event(event)

                # 更新统计
                self._stats["events_processed"] += 1

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._stats["errors_count"] += 1
                logger.error(f"Error in event worker: {e}")

    async def _process_event(self, event: Event) -> None:
        """处理事件"""
        try:
            # 获取订阅者
            subscriptions = self._get_subscriptions(event)

            # 按优先级排序
            subscriptions.sort(key=lambda s: s.priority.value, reverse=True)

            # 执行回调
            for subscription in subscriptions:
                try:
                    if asyncio.iscoroutinefunction(subscription.callback):
                        await subscription.callback(event)
                    else:
                        subscription.callback(event)

                    # 一次性订阅
                    if subscription.once:
                        self._remove_subscription(subscription)

                except Exception as e:
                    self._stats["errors_count"] += 1
                    logger.error(f"Error in event callback: {e}")

        except Exception as e:
            self._stats["errors_count"] += 1
            logger.error(f"Error processing event: {e}")

    def _get_subscriptions(self, event: Event) -> list[EventSubscription]:
        """获取事件订阅"""
        subscriptions = []

        # 获取特定事件订阅
        if event.name in self._subscriptions:
            for subscription in self._subscriptions[event.name]:
                if subscription.matches(event):
                    subscriptions.append(subscription)

        # 获取全局订阅
        for subscription in self._global_subscriptions:
            if subscription.matches(event):
                subscriptions.append(subscription)

        return subscriptions

    def _remove_subscription(self, subscription: EventSubscription) -> None:
        """移除订阅"""
        with self._lock:
            # 从特定事件订阅中移除
            if subscription.event_name in self._subscriptions:
                try:
                    self._subscriptions[subscription.event_name].remove(subscription)
                except ValueError:
                    pass

            # 从全局订阅中移除
            try:
                self._global_subscriptions.remove(subscription)
            except ValueError:
                pass

            self._stats["subscriptions_count"] = len(self._subscriptions) + len(
                self._global_subscriptions
            )

    def subscribe(
        self,
        event_name: str,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL,
        tags_filter: dict[str, str] | None = None,
        once: bool = False,
        subscriber_id: str | None = None,
    ) -> EventSubscription:
        """订阅事件"""
        subscription = EventSubscription(
            callback=callback,
            event_name=event_name,
            priority=priority,
            tags_filter=tags_filter,
            once=once,
            subscriber_id=subscriber_id,
        )

        with self._lock:
            self._subscriptions[event_name].append(subscription)
            self._stats["subscriptions_count"] = len(self._subscriptions) + len(
                self._global_subscriptions
            )

        logger.debug(f"Subscribed to event: {event_name}")
        return subscription

    def subscribe_global(
        self,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL,
        tags_filter: dict[str, str] | None = None,
        once: bool = False,
        subscriber_id: str | None = None,
    ) -> EventSubscription:
        """订阅所有事件"""
        subscription = EventSubscription(
            callback=callback,
            event_name="*",  # 通配符
            priority=priority,
            tags_filter=tags_filter,
            once=once,
            subscriber_id=subscriber_id,
        )

        with self._lock:
            self._global_subscriptions.append(subscription)
            self._stats["subscriptions_count"] = len(self._subscriptions) + len(
                self._global_subscriptions
            )

        logger.debug("Subscribed to all events")
        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> None:
        """取消订阅"""
        self._remove_subscription(subscription)
        logger.debug(f"Unsubscribed from event: {subscription.event_name}")

    def publish(
        self,
        event_name: str,
        data: Any = None,
        source: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        tags: dict[str, str] | None = None,
    ) -> None:
        """发布事件"""
        if not self._running:
            logger.warning("Event bus not running, event discarded")
            return

        event = Event(
            name=event_name,
            data=data,
            source=source,
            priority=priority,
            tags=tags or {},
        )

        try:
            # 添加到队列
            if self._event_loop:
                self._event_loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self._event_queue.put(event))
                )

            self._stats["events_published"] += 1
            logger.debug(f"Published event: {event_name}")

        except Exception as e:
            self._stats["errors_count"] += 1
            logger.error(f"Failed to publish event: {e}")

    def publish_sync(
        self,
        event_name: str,
        data: Any = None,
        source: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        tags: dict[str, str] | None = None,
    ) -> None:
        """同步发布事件"""
        event = Event(
            name=event_name,
            data=data,
            source=source,
            priority=priority,
            tags=tags or {},
        )

        try:
            # 直接处理事件
            subscriptions = self._get_subscriptions(event)
            subscriptions.sort(key=lambda s: s.priority.value, reverse=True)

            for subscription in subscriptions:
                try:
                    subscription.callback(event)
                    if subscription.once:
                        self._remove_subscription(subscription)
                except Exception as e:
                    self._stats["errors_count"] += 1
                    logger.error(f"Error in sync event callback: {e}")

            self._stats["events_published"] += 1
            self._stats["events_processed"] += 1

        except Exception as e:
            self._stats["errors_count"] += 1
            logger.error(f"Failed to publish sync event: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def clear_stats(self) -> None:
        """清除统计信息"""
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "subscriptions_count": 0,
            "errors_count": 0,
        }

    def get_subscription_count(self, event_name: str | None = None) -> int:
        """获取订阅数量"""
        if event_name:
            return len(self._subscriptions.get(event_name, []))
        else:
            return len(self._subscriptions) + len(self._global_subscriptions)

    def is_running(self) -> bool:
        """检查是否运行中"""
        return self._running


# 全局事件总线实例
_global_event_bus = EnhancedEventBus()


def get_event_bus() -> EnhancedEventBus:
    """获取全局事件总线"""
    return _global_event_bus


def subscribe_event(
    event_name: str,
    callback: Callable[[Event], None],
    priority: EventPriority = EventPriority.NORMAL,
    tags_filter: dict[str, str] | None = None,
    once: bool = False,
    subscriber_id: str | None = None,
) -> EventSubscription:
    """订阅事件"""
    return _global_event_bus.subscribe(
        event_name, callback, priority, tags_filter, once, subscriber_id
    )


def publish_event(
    event_name: str,
    data: Any = None,
    source: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    tags: dict[str, str] | None = None,
) -> None:
    """发布事件"""
    _global_event_bus.publish(event_name, data, source, priority, tags)


def publish_event_sync(
    event_name: str,
    data: Any = None,
    source: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    tags: dict[str, str] | None = None,
) -> None:
    """同步发布事件"""
    _global_event_bus.publish_sync(event_name, data, source, priority, tags)
