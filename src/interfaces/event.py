"""事件总线相关接口定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventPriority(int, Enum):
    """事件优先级"""

    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 0


@dataclass
class Event:
    """事件数据类"""

    name: str  # 事件名称
    data: dict[str, Any]  # 事件数据
    timestamp: datetime  # 时间戳
    source: str | None = None  # 事件源
    priority: EventPriority = EventPriority.NORMAL  # 优先级
    metadata: dict[str, Any] | None = None  # 元数据


class IEventHandler(ABC):
    """事件处理器接口"""

    @abstractmethod
    def handle(self, event: Event) -> None:
        """处理事件

        Args:
            event: 事件对象
        """
        ...

    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """判断是否能处理该事件

        Args:
            event: 事件对象

        Returns:
            是否能处理
        """
        pass

    @property
    @abstractmethod
    def handler_name(self) -> str:
        """处理器名称"""
        pass


class IEventBus(ABC):
    """事件总线接口"""

    @abstractmethod
    def subscribe(
        self,
        event_name: str,
        handler: IEventHandler,
        priority: EventPriority | None = None,
    ) -> str:
        """订阅事件

        Args:
            event_name: 事件名称
            handler: 事件处理器
            priority: 优先级(可选)

        Returns:
            订阅ID
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅

        Args:
            subscription_id: 订阅ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def publish(self, event: Event) -> None:
        """发布事件

        Args:
            event: 事件对象
        """
        pass

    @abstractmethod
    def publish_async(self, event: Event) -> None:
        """异步发布事件

        Args:
            event: 事件对象
        """
        pass

    @abstractmethod
    def clear_handlers(self, event_name: str | None = None) -> None:
        """清除处理器

        Args:
            event_name: 事件名称(可选,为None则清除所有)
        """
        pass

    @abstractmethod
    def get_handler_count(self, event_name: str) -> int:
        """获取处理器数量

        Args:
            event_name: 事件名称

        Returns:
            处理器数量
        """
        pass


class IEventLogger(ABC):
    """事件日志接口"""

    @abstractmethod
    def log_event(self, event: Event) -> None:
        """记录事件

        Args:
            event: 事件对象
        """
        ...

    @abstractmethod
    def get_events(
        self,
        event_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """获取事件历史

        Args:
            event_name: 事件名称(可选)
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)
            limit: 限制数量(可选)

        Returns:
            事件列表
        """
        pass

    @abstractmethod
    def clear_logs(self, before_time: datetime | None = None) -> int:
        """清除日志

        Args:
            before_time: 清除此时间之前的日志(可选,为None则清除所有)

        Returns:
            清除的数量
        """
        pass
