"""EventBus 单元测试"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.core.event_bus import Event, EventBus, EventPriority


def test_publish_respects_priority_order() -> None:
    bus = EventBus()
    order: list[tuple[str, Any]] = []

    def handler_low(event: Event) -> str:
        order.append(("low", event.data["value"]))
        return "low"

    def handler_high(event: Event) -> str:
        order.append(("high", event.data["value"]))
        return "high"

    bus.subscribe("test.event", handler_low, priority=EventPriority.LOW)
    bus.subscribe("test.event", handler_high, priority=EventPriority.HIGH)

    results = bus.publish(Event(name="test.event", data={"value": 42}))

    assert order == [("high", 42), ("low", 42)]
    assert results == ["high", "low"]


@pytest.mark.asyncio()
async def test_publish_async_invokes_async_subscribers() -> None:
    bus = EventBus()

    async def handler(event: Event) -> int:
        await asyncio.sleep(0)
        return int(event.data["value"]) * 2

    bus.subscribe("async.event", handler)
    results = await bus.publish_async(Event(name="async.event", data={"value": 3}))

    assert results == [6]


def test_middleware_modifies_and_blocks_events() -> None:
    bus = EventBus()
    received: list[bool] = []

    def tag_middleware(event: Event) -> Event:
        event.data["tagged"] = True
        return event

    bus.use_middleware(tag_middleware)

    def handler(event: Event) -> None:
        received.append(bool(event.data.get("tagged")))

    bus.subscribe("demo.event", handler)
    bus.publish(Event(name="demo.event", data={}))
    assert received == [True]

    # 追加一个会拦截事件的中间件
    bus.use_middleware(lambda _event: None)
    received.clear()

    results = bus.publish(Event(name="demo.event", data={}))

    assert results == []
    assert received == []


def test_history_keeps_recent_events_only() -> None:
    bus = EventBus(max_history=2)
    bus.publish(Event(name="first"))
    bus.publish(Event(name="second"))
    bus.publish(Event(name="third"))

    history = bus.get_history()
    assert [event.name for event in history] == ["second", "third"]
