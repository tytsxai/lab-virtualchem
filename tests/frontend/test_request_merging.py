"""
请求合并与批处理机制测试
"""

import asyncio

import pytest

import src.frontend.request_merger as request_merger_module
from src.frontend.request_merger import (
    DataLoader,
    RequestDeduplicator,
    RequestMerger,
    RequestQueue,
    get_data_loader,
    register_data_loader,
)


@pytest.mark.asyncio
async def test_request_merger_batches_by_size():
    calls = []

    async def executor(endpoint, requests):
        calls.append((endpoint, len(requests)))
        return [{"success": True, "data": request.id} for request in requests]

    merger = RequestMerger(batch_size=3, batch_timeout=1, executor=executor)
    received = []

    for i in range(3):
        await merger.add_request(
            f"req_{i}",
            "/api/data",
            {"idx": i},
            lambda data, bucket=received: bucket.append(data),
        )

    assert calls == [("/api/data", 3)]
    assert sorted(received) == ["req_0", "req_1", "req_2"]


@pytest.mark.asyncio
async def test_request_merger_flushes_on_timeout():
    batches = []

    async def executor(endpoint, requests):
        batches.append(len(requests))
        return [{"success": True, "data": r.id} for r in requests]

    merger = RequestMerger(batch_size=5, batch_timeout=0.01, executor=executor)
    received = []

    await merger.add_request("req_a", "/api/info", {}, lambda data: received.append(data))
    await merger.add_request("req_b", "/api/info", {}, lambda data: received.append(data))

    await asyncio.sleep(0.05)

    assert batches == [2]
    assert set(received) == {"req_a", "req_b"}


@pytest.mark.asyncio
async def test_data_loader_batches_and_caches():
    loads = []

    async def batch_loader(keys):
        loads.append(tuple(keys))
        await asyncio.sleep(0)
        return {key: f"value_{key}" for key in keys}

    loader = DataLoader(batch_loader)
    values = await asyncio.gather(loader.load("a"), loader.load("b"))

    assert len(loads) == 1
    assert values == ["value_a", "value_b"]
    assert await loader.load("a") == "value_a"

    loader.prime("prefetched", "value_prefetched")
    cached = await loader.load_many(["prefetched", "a"])
    assert cached["prefetched"] == "value_prefetched"
    assert cached["a"] == "value_a"


@pytest.mark.asyncio
async def test_request_deduplicator_avoids_duplicate_execution():
    deduplicator = RequestDeduplicator()
    call_count = 0

    async def executor():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return "done"

    result1, result2 = await asyncio.gather(
        deduplicator.request("key", executor),
        deduplicator.request("key", executor),
    )

    assert call_count == 1
    assert result1 == result2 == "done"


@pytest.mark.asyncio
async def test_request_queue_limits_concurrency():
    queue = RequestQueue(max_concurrent=2)
    running = 0
    peak = 0

    async def job(delay):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(delay)
        running -= 1
        return delay

    tasks = [
        asyncio.create_task(queue.enqueue(lambda d=delay: job(d)))
        for delay in (0.02, 0.02, 0.02, 0.02)
    ]

    results = await asyncio.gather(*tasks)

    assert peak <= 2
    assert results == [0.02, 0.02, 0.02, 0.02]


def test_register_and_get_data_loader():
    async def dummy_loader(keys):
        return {key: key for key in keys}

    loader = DataLoader(dummy_loader)
    name = "test_frontend_loader"

    register_data_loader(name, loader)
    try:
        assert get_data_loader(name) is loader
    finally:
        request_merger_module._data_loader_registry.pop(name, None)

