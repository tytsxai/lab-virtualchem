import os
import time

import pytest

from src.core.middleware import (
    AuthenticationMiddleware,
    CachingMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareContext,
    MiddlewarePipeline,
    PerformanceMiddleware,
    RateLimitMiddleware,
    TransformMiddleware,
    ValidationMiddleware,
)


@pytest.mark.asyncio
async def test_error_handling_middleware_default_handler_redacts_paths() -> None:
    context = MiddlewareContext(request={"id": 1})
    middleware = ErrorHandlingMiddleware()

    cwd = os.getcwd()
    exc_message = (
        f"boom at {cwd}/secrets.txt and /tmp/very/secret.txt and C:\\\\Users\\\\me\\\\pw.txt"
    )

    async def next_middleware():
        raise RuntimeError(exc_message)

    result = await middleware.invoke(context, next_middleware)

    assert result["success"] is False
    assert result["type"] == "RuntimeError"
    assert "<redacted-path>" in result["error"]
    assert cwd not in result["error"]
    assert "/tmp/very/secret.txt" not in result["error"]
    assert "C:\\\\Users\\\\me\\\\pw.txt" not in result["error"]
    assert context.has_errors() is True
    assert isinstance(context.errors[0], RuntimeError)


@pytest.mark.asyncio
async def test_error_handling_middleware_custom_handler_called() -> None:
    context = MiddlewareContext(request="req")
    called = {"count": 0}

    def handler(exc: Exception, ctx: MiddlewareContext):
        called["count"] += 1
        assert ctx is context
        assert isinstance(exc, ValueError)
        return {"custom": True, "msg": str(exc)}

    middleware = ErrorHandlingMiddleware(error_handler=handler)

    async def next_middleware():
        raise ValueError("bad input")

    result = await middleware.invoke(context, next_middleware)

    assert result == {"custom": True, "msg": "bad input"}
    assert called["count"] == 1
    assert context.has_errors() is True


@pytest.mark.asyncio
async def test_pipeline_executes_and_converts_exception_to_error_response() -> None:
    pipeline = MiddlewarePipeline().use(ErrorHandlingMiddleware())

    async def handler(_request):
        raise PermissionError(f"denied for {os.getcwd()}/private.key")

    result = await pipeline.execute({"op": "read"}, handler)

    assert result["success"] is False
    assert result["type"] == "PermissionError"
    assert "<redacted-path>" in result["error"]
    assert os.getcwd() not in result["error"]


def test_middleware_context_data_and_elapsed_time() -> None:
    context = MiddlewareContext(request="req")

    context.set("a", 1)
    assert context.get("a") == 1
    assert context.get("missing", 2) == 2
    assert context.has("a") is True
    assert context.has("missing") is False
    assert context.has_errors() is False

    context.add_error(RuntimeError("x"))
    assert context.has_errors() is True

    time.sleep(0.001)
    assert context.elapsed_time >= 0


@pytest.mark.asyncio
async def test_pipeline_supports_sync_final_handler() -> None:
    pipeline = MiddlewarePipeline()

    def handler(req):
        return {"ok": True, "req": req}

    result = await pipeline.execute({"x": 1}, handler)
    assert result == {"ok": True, "req": {"x": 1}}


@pytest.mark.asyncio
async def test_logging_middleware_success_and_failure_messages() -> None:
    messages: list[str] = []
    pipeline = MiddlewarePipeline().use(LoggingMiddleware(logger=messages.append))

    async def ok_handler(_req):
        return "ok"

    ok_result = await pipeline.execute("req", ok_handler)
    assert ok_result == "ok"
    assert any("Request started" in m for m in messages)
    assert any("Request completed" in m for m in messages)

    messages.clear()

    async def bad_handler(_req):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await pipeline.execute("req", bad_handler)

    assert any("Request failed" in m for m in messages)


@pytest.mark.asyncio
async def test_performance_middleware_sets_elapsed_ms_and_warns(capsys) -> None:
    pipeline = MiddlewarePipeline().use(PerformanceMiddleware(threshold_ms=0))

    async def handler(_req):
        import asyncio

        await asyncio.sleep(0)
        return "ok"

    result = await pipeline.execute("req", handler)
    assert result == "ok"

    out = capsys.readouterr().out
    assert "Performance warning" in out


@pytest.mark.asyncio
async def test_caching_middleware_hit_and_miss_sets_flag() -> None:
    cache = CachingMiddleware(cache_key_func=lambda req: str(req))

    async def handler(req):
        return {"v": req}

    def make_pipeline():
        pipeline = MiddlewarePipeline().use(cache)

        async def final(req):
            return await handler(req)

        return pipeline, final

    pipeline, final = make_pipeline()
    context = MiddlewareContext(request="1")

    async def next_middleware():
        return await final(context.request)

    miss = await cache.invoke(context, next_middleware)
    assert miss == {"v": "1"}
    assert context.get("cached") is False

    context2 = MiddlewareContext(request="1")

    async def next_middleware2():
        return await final(context2.request)

    hit = await cache.invoke(context2, next_middleware2)
    assert hit == {"v": "1"}
    assert context2.get("cached") is True

    cache.clear_cache()


@pytest.mark.asyncio
async def test_validation_middleware_blocks_invalid_request() -> None:
    pipeline = MiddlewarePipeline().use(ValidationMiddleware(validator=lambda req: req == "ok"))

    async def handler(req):
        return {"req": req}

    assert await pipeline.execute("ok", handler) == {"req": "ok"}
    with pytest.raises(ValueError, match="Validation failed"):
        await pipeline.execute("bad", handler)


@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_then_blocks(monkeypatch) -> None:
    now = 1000.0

    def fake_time():
        return now

    monkeypatch.setattr(time, "time", fake_time)

    limiter = RateLimitMiddleware(max_requests=2, time_window=60.0, key_func=lambda req: req)
    pipeline = MiddlewarePipeline().use(limiter)

    async def handler(req):
        return {"req": req}

    assert await pipeline.execute("k", handler) == {"req": "k"}
    now += 1.0
    assert await pipeline.execute("k", handler) == {"req": "k"}
    now += 1.0
    with pytest.raises(Exception, match="Rate limit exceeded"):
        await pipeline.execute("k", handler)

    now += 1000.0
    assert await pipeline.execute("k", handler) == {"req": "k"}


@pytest.mark.asyncio
async def test_authentication_middleware_sets_flag_and_blocks() -> None:
    authed = AuthenticationMiddleware(auth_func=lambda req: req == "token")
    pipeline = MiddlewarePipeline().use(authed)

    async def handler(req):
        return {"req": req}

    assert await pipeline.execute("token", handler) == {"req": "token"}

    pipeline2 = MiddlewarePipeline().use(AuthenticationMiddleware(auth_func=lambda _req: False))
    with pytest.raises(PermissionError, match="Authentication failed"):
        await pipeline2.execute("x", handler)


@pytest.mark.asyncio
async def test_transform_middleware_transforms_request_and_response() -> None:
    pipeline = MiddlewarePipeline().use(
        TransformMiddleware(
            request_transform=lambda req: {"wrapped": req},
            response_transform=lambda resp: {"transformed": resp},
        )
    )

    async def handler(req):
        assert req == {"wrapped": "x"}
        return {"raw": True}

    result = await pipeline.execute("x", handler)
    assert result == {"transformed": {"raw": True}}


@pytest.mark.asyncio
async def test_pipeline_clear_removes_middleware() -> None:
    pipeline = MiddlewarePipeline().use(LoggingMiddleware(logger=lambda _m: None))
    pipeline.clear()

    async def handler(req):
        return {"req": req}

    assert await pipeline.execute("x", handler) == {"req": "x"}
