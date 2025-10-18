"""
事件总线扩展测试

测试EventBus的所有功能：
- 发布/订阅
- 同步和异步事件
- 事件过滤
- 优先级处理
- 事件历史
- 中间件
"""

import asyncio
from datetime import datetime

import pytest

from src.core.event_bus import (
    Event,
    EventBus,
    EventPriority,
    EventSubscriber,
    get_event_bus,
    on_event,
)


class TestEvent:
    """Event类测试"""

    def test_create_event(self):
        """测试创建事件"""
        event = Event(name="test.event", data={"key": "value"})
        assert event.name == "test.event"
        assert event.data == {"key": "value"}
        assert isinstance(event.timestamp, datetime)
        assert event.priority == EventPriority.NORMAL
        assert event.source is None

    def test_event_with_priority(self):
        """测试带优先级的事件"""
        event = Event(name="test.event", priority=EventPriority.HIGH)
        assert event.priority == EventPriority.HIGH

    def test_event_to_dict(self):
        """测试事件转字典"""
        event = Event(name="test.event", data={"key": "value"}, source="test")
        data = event.to_dict()

        assert data["name"] == "test.event"
        assert data["data"] == {"key": "value"}
        assert "timestamp" in data
        assert data["priority"] == EventPriority.NORMAL.value
        assert data["source"] == "test"

    def test_event_from_dict(self):
        """测试从字典创建事件"""
        data = {
            "name": "test.event",
            "data": {"key": "value"},
            "timestamp": datetime.now().isoformat(),
            "priority": EventPriority.HIGH.value,
            "source": "test",
        }
        event = Event.from_dict(data)

        assert event.name == "test.event"
        assert event.data == {"key": "value"}
        assert event.priority == EventPriority.HIGH
        assert event.source == "test"


class TestEventSubscriber:
    """EventSubscriber类测试"""

    def test_create_subscriber(self):
        """测试创建订阅者"""

        def handler(event):
            pass

        subscriber = EventSubscriber(handler=handler, event_name="test.event")
        assert subscriber.handler == handler
        assert subscriber.event_name == "test.event"
        assert subscriber.priority == EventPriority.NORMAL
        assert subscriber.filter_func is None
        assert subscriber.is_async is False

    def test_matches_exact(self):
        """测试精确匹配"""

        def handler(event):
            pass

        subscriber = EventSubscriber(handler=handler, event_name="test.event")
        event = Event(name="test.event")

        assert subscriber.matches(event) is True

    def test_matches_wildcard(self):
        """测试通配符匹配"""

        def handler(event):
            pass

        subscriber = EventSubscriber(handler=handler, event_name="test.*")
        event1 = Event(name="test.event")
        event2 = Event(name="test.another")
        event3 = Event(name="other.event")

        assert subscriber.matches(event1) is True
        assert subscriber.matches(event2) is True
        assert subscriber.matches(event3) is False

    def test_matches_all(self):
        """测试匹配所有事件"""

        def handler(event):
            pass

        subscriber = EventSubscriber(handler=handler, event_name="*")
        event1 = Event(name="test.event")
        event2 = Event(name="other.event")

        assert subscriber.matches(event1) is True
        assert subscriber.matches(event2) is True

    def test_matches_with_filter(self):
        """测试带过滤器的匹配"""

        def handler(event):
            pass

        def filter_func(event):
            return event.data.get("amount", 0) > 100

        subscriber = EventSubscriber(handler=handler, event_name="order.*", filter_func=filter_func)

        event1 = Event(name="order.created", data={"amount": 150})
        event2 = Event(name="order.created", data={"amount": 50})

        assert subscriber.matches(event1) is True
        assert subscriber.matches(event2) is False


class TestEventBus:
    """EventBus类测试"""

    @pytest.fixture
    def bus(self):
        """创建测试用的事件总线"""
        bus = EventBus()
        yield bus
        bus.clear()  # 清理

    def test_create_bus(self, bus):
        """测试创建事件总线"""
        assert isinstance(bus, EventBus)
        assert bus.get_subscriber_count() == 0

    def test_subscribe(self, bus):
        """测试订阅事件"""
        call_count = 0

        def handler(event):
            nonlocal call_count
            call_count += 1

        bus.subscribe("test.event", handler)
        assert bus.get_subscriber_count() == 1

        # 发布事件
        event = Event(name="test.event")
        bus.publish(event)
        assert call_count == 1

    def test_subscribe_with_priority(self, bus):
        """测试带优先级的订阅"""
        call_order = []

        def handler1(event):
            call_order.append("handler1")

        def handler2(event):
            call_order.append("handler2")

        def handler3(event):
            call_order.append("handler3")

        bus.subscribe("test.event", handler1, priority=EventPriority.LOW)
        bus.subscribe("test.event", handler2, priority=EventPriority.HIGH)
        bus.subscribe("test.event", handler3, priority=EventPriority.NORMAL)

        event = Event(name="test.event")
        bus.publish(event)

        # 应该按优先级顺序调用：HIGH -> NORMAL -> LOW
        assert call_order == ["handler2", "handler3", "handler1"]

    def test_subscribe_with_wildcard(self, bus):
        """测试通配符订阅"""
        call_count = 0

        def handler(event):
            nonlocal call_count
            call_count += 1

        bus.subscribe("user.*", handler)

        bus.publish(Event(name="user.login"))
        bus.publish(Event(name="user.logout"))
        bus.publish(Event(name="order.created"))

        assert call_count == 2  # 只有user.*的事件被处理

    def test_subscribe_all(self, bus):
        """测试订阅所有事件"""
        call_count = 0

        def handler(event):
            nonlocal call_count
            call_count += 1

        bus.subscribe("*", handler)

        bus.publish(Event(name="user.login"))
        bus.publish(Event(name="order.created"))
        bus.publish(Event(name="data.processed"))

        assert call_count == 3

    def test_subscribe_with_filter(self, bus):
        """测试带过滤器的订阅"""
        high_value_orders = []

        def handler(event):
            high_value_orders.append(event.data["order_id"])

        bus.subscribe("order.created", handler, filter_func=lambda e: e.data.get("amount", 0) > 100)

        bus.publish(Event(name="order.created", data={"order_id": 1, "amount": 150}))
        bus.publish(Event(name="order.created", data={"order_id": 2, "amount": 50}))
        bus.publish(Event(name="order.created", data={"order_id": 3, "amount": 200}))

        assert high_value_orders == [1, 3]

    def test_unsubscribe(self, bus):
        """测试取消订阅"""

        def handler(event):
            pass

        bus.subscribe("test.event", handler)
        assert bus.get_subscriber_count() == 1

        result = bus.unsubscribe(handler)
        assert result is True
        assert bus.get_subscriber_count() == 0

    def test_unsubscribe_nonexistent(self, bus):
        """测试取消不存在的订阅"""

        def handler(event):
            pass

        result = bus.unsubscribe(handler)
        assert result is False

    def test_publish_sync(self, bus):
        """测试同步发布"""
        results = []

        def handler1(event):
            results.append("handler1")
            return "result1"

        def handler2(event):
            results.append("handler2")
            return "result2"

        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)

        event = Event(name="test.event")
        return_values = bus.publish(event)

        assert results == ["handler1", "handler2"]
        assert return_values == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_publish_async(self, bus):
        """测试异步发布"""
        results = []

        async def handler1(event):
            await asyncio.sleep(0.01)
            results.append("handler1")
            return "result1"

        async def handler2(event):
            await asyncio.sleep(0.01)
            results.append("handler2")
            return "result2"

        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)

        event = Event(name="test.event")
        return_values = await bus.publish_async(event)

        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results
        assert "result1" in return_values
        assert "result2" in return_values

    def test_middleware(self, bus):
        """测试中间件"""
        middleware_called = []

        def log_middleware(event):
            middleware_called.append(f"log:{event.name}")
            return event

        def enrich_middleware(event):
            middleware_called.append(f"enrich:{event.name}")
            event.data["enriched"] = True
            return event

        bus.use_middleware(log_middleware)
        bus.use_middleware(enrich_middleware)

        handler_called = False

        def handler(event):
            nonlocal handler_called
            handler_called = True
            assert event.data.get("enriched") is True

        bus.subscribe("test.event", handler)

        event = Event(name="test.event")
        bus.publish(event)

        assert middleware_called == ["log:test.event", "enrich:test.event"]
        assert handler_called is True

    def test_middleware_blocking(self, bus):
        """测试中间件拦截"""

        def blocking_middleware(event):
            if event.data.get("blocked"):
                return None  # 拦截事件
            return event

        bus.use_middleware(blocking_middleware)

        handler_called = False

        def handler(event):
            nonlocal handler_called
            handler_called = True

        bus.subscribe("test.event", handler)

        # 正常事件
        event1 = Event(name="test.event", data={"blocked": False})
        bus.publish(event1)
        assert handler_called is True

        # 被拦截的事件
        handler_called = False
        event2 = Event(name="test.event", data={"blocked": True})
        bus.publish(event2)
        assert handler_called is False

    def test_history(self, bus):
        """测试事件历史"""
        event1 = Event(name="test.event1")
        event2 = Event(name="test.event2")
        event3 = Event(name="test.event1")

        bus.publish(event1)
        bus.publish(event2)
        bus.publish(event3)

        # 获取所有历史
        history = bus.get_history()
        assert len(history) == 3

        # 获取特定事件的历史
        history_filtered = bus.get_history(event_name="test.event1")
        assert len(history_filtered) == 2

        # 限制数量
        history_limited = bus.get_history(limit=2)
        assert len(history_limited) == 2

    def test_history_limit(self):
        """测试历史记录大小限制"""
        bus = EventBus(max_history=10)

        for i in range(15):
            bus.publish(Event(name=f"event.{i}"))

        history = bus.get_history()
        assert len(history) == 10  # 只保留最近10条

    def test_clear_history(self, bus):
        """测试清空历史"""
        bus.publish(Event(name="test.event"))
        assert len(bus.get_history()) == 1

        bus.clear_history()
        assert len(bus.get_history()) == 0

    def test_get_subscriber_count(self, bus):
        """测试获取订阅者数量"""

        def handler1(event):
            pass

        def handler2(event):
            pass

        bus.subscribe("test.event1", handler1)
        bus.subscribe("test.event2", handler2)
        bus.subscribe("test.event1", handler2)

        assert bus.get_subscriber_count() == 3
        assert bus.get_subscriber_count("test.event1") == 2
        assert bus.get_subscriber_count("test.event2") == 1

    def test_chain_subscribe(self, bus):
        """测试链式订阅"""

        def handler1(event):
            pass

        def handler2(event):
            pass

        result = bus.subscribe("event1", handler1).subscribe("event2", handler2)

        assert result is bus
        assert bus.get_subscriber_count() == 2


class TestGlobalEventBus:
    """全局事件总线测试"""

    def test_get_event_bus(self):
        """测试获取全局事件总线"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert isinstance(bus1, EventBus)
        assert bus1 is bus2  # 应该是单例

    def test_decorator(self):
        """测试装饰器"""
        bus = get_event_bus()
        bus.clear()  # 清理之前的订阅

        call_count = 0

        @on_event("test.decorator")
        def handler(event):
            nonlocal call_count
            call_count += 1

        event = Event(name="test.decorator")
        bus.publish(event)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_async(self):
        """测试异步装饰器"""
        bus = get_event_bus()
        bus.clear()

        call_count = 0

        @on_event("test.async.decorator")
        async def handler(event):
            nonlocal call_count
            await asyncio.sleep(0.01)
            call_count += 1

        event = Event(name="test.async.decorator")
        await bus.publish_async(event)

        assert call_count == 1


class TestEventBusIntegration:
    """事件总线集成测试"""

    def test_complex_workflow(self):
        """测试复杂工作流"""
        bus = EventBus()
        results = {"login": 0, "audit": 0, "notification": 0}

        # 登录处理器
        def on_login(event):
            results["login"] += 1

        # 审计处理器（高优先级）
        def on_audit(event):
            results["audit"] += 1

        # 通知处理器（低优先级）
        def on_notification(event):
            results["notification"] += 1

        bus.subscribe("user.login", on_login)
        bus.subscribe("user.*", on_audit, priority=EventPriority.HIGH)
        bus.subscribe("user.*", on_notification, priority=EventPriority.LOW)

        # 发布登录事件
        event = Event(name="user.login", data={"user_id": 123})
        bus.publish(event)

        # 所有处理器都应该被调用
        assert results["login"] == 1
        assert results["audit"] == 1
        assert results["notification"] == 1

        # 检查历史
        history = bus.get_history()
        assert len(history) == 1
        assert history[0].name == "user.login"

    @pytest.mark.asyncio
    async def test_mixed_sync_async(self):
        """测试混合同步和异步订阅"""
        bus = EventBus()
        results = []

        def sync_handler(event):
            results.append("sync")

        async def async_handler(event):
            await asyncio.sleep(0.01)
            results.append("async")

        bus.subscribe("test.event", sync_handler)
        bus.subscribe("test.event", async_handler)

        # 异步发布会调用所有处理器
        event = Event(name="test.event")
        await bus.publish_async(event)

        assert len(results) == 2
        assert "sync" in results
        assert "async" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


