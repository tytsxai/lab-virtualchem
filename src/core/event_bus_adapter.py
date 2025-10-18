"""
事件总线适配器 - 将EventBus适配到IEventBus接口
"""

import uuid

from src.core.event_bus import Event, EventBus, EventPriority
from src.interfaces.event import IEventBus, IEventHandler


class EventBusAdapter(IEventBus):
    """EventBus适配器，实现IEventBus接口"""

    def __init__(self, event_bus: EventBus | None = None):
        self._bus = event_bus or EventBus()
        self._subscriptions = {}  # 订阅ID映射

    def subscribe(self, event_name: str, handler: IEventHandler, priority: EventPriority | None = None) -> str:
        """订阅事件"""
        # 生成订阅ID
        subscription_id = str(uuid.uuid4())

        # 包装处理器
        def wrapper(event: Event):
            if handler.can_handle(event):
                return handler.handle(event)

        # 订阅事件
        self._bus.subscribe(event_name, wrapper, priority or EventPriority.NORMAL)

        # 保存订阅映射
        self._subscriptions[subscription_id] = {"event_name": event_name, "handler": wrapper}

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        if subscription_id not in self._subscriptions:
            return False

        sub = self._subscriptions[subscription_id]
        success = self._bus.unsubscribe(sub["handler"])

        if success:
            del self._subscriptions[subscription_id]

        return success

    def publish(self, event: Event) -> None:
        """发布事件（同步）"""
        self._bus.publish(event)

    def publish_async(self, event: Event) -> None:
        """发布事件（异步）"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._bus.publish_async(event))
            else:
                loop.run_until_complete(self._bus.publish_async(event))
        except RuntimeError:
            # 如果没有运行的事件循环，使用同步发布
            self._bus.publish(event)

    def clear_handlers(self, event_name: str | None = None) -> None:
        """清除处理器"""
        if event_name is None:
            # 清除所有
            self._bus.clear()
            self._subscriptions.clear()
        else:
            # 清除特定事件的处理器
            to_remove = []
            for sub_id, sub in self._subscriptions.items():
                if sub["event_name"] == event_name:
                    self._bus.unsubscribe(sub["handler"])
                    to_remove.append(sub_id)

            for sub_id in to_remove:
                del self._subscriptions[sub_id]

    def get_handler_count(self, event_name: str) -> int:
        """获取处理器数量"""
        count = 0
        for sub in self._subscriptions.values():
            if sub["event_name"] == event_name:
                count += 1
        return count


class FunctionEventHandlerAdapter(IEventHandler):
    """函数事件处理器适配器"""

    def __init__(self, handler_func, event_pattern: str = "*", name: str = ""):
        self.handler_func = handler_func
        self.event_pattern = event_pattern
        self._name = name or f"Handler_{id(handler_func)}"

    def handle(self, event: Event):
        """处理事件"""
        return self.handler_func(event)

    def can_handle(self, event: Event) -> bool:
        """检查是否可以处理事件"""
        if self.event_pattern == "*":
            return True

        # 简单模式匹配
        if "*" in self.event_pattern:
            import re

            pattern = self.event_pattern.replace(".", r"\.").replace("*", ".*")
            return bool(re.match(f"^{pattern}$", event.name))

        return event.name == self.event_pattern

    @property
    def handler_name(self) -> str:
        """处理器名称"""
        return self._name
