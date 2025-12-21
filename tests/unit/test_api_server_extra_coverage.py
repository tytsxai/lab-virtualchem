"""Extra unit tests to drive src.api.server coverage above 90%.

These tests avoid binding sockets (sandbox restriction) and instead call
handler helpers directly on a partially constructed instance.
"""

from __future__ import annotations

import io
import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.api.middleware import AuthMiddleware
from src.api.server import APIRequestHandler, APIVersion, APIServer, CacheStrategy
from http.server import BaseHTTPRequestHandler
import contextlib


pytestmark = pytest.mark.api


def _make_handler(tmp_path: Path) -> APIRequestHandler:
    handler = object.__new__(APIRequestHandler)
    handler.api_version = APIVersion.V2
    handler.cache_enabled = True
    handler.websocket_enabled = False
    handler.server = type("S", (), {})()
    handler.server.request_cache = {}
    handler.server.api_metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "rate_limited_total": 0,
        "auth_failed_total": 0,
        "cache_hits_total": 0,
        "cache_misses_total": 0,
        "endpoints": {},
    }
    handler.server.request_durations_ms = deque(maxlen=50)
    handler.server.sessions = {}
    handler.server.storage = type("St", (), {"base_dir": tmp_path / "data"})()
    handler.server.storage.base_dir.mkdir(parents=True, exist_ok=True)
    handler.server.template_engine = type(
        "E", (), {"templates_dir": tmp_path / "templates"}
    )()
    Path(handler.server.template_engine.templates_dir).mkdir(parents=True, exist_ok=True)

    handler.client_address = ("127.0.0.1", 12345)
    handler.headers = {}
    handler.path = "/"
    handler.command = "GET"
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()

    captured = {"status": 0, "headers": {}}

    def _send_response(code: int, message: str | None = None):  # noqa: ARG001
        captured["status"] = code

    def _send_header(k: str, v: str):
        captured["headers"][k] = v

    handler.send_response = _send_response  # type: ignore[assignment]
    handler.send_header = _send_header  # type: ignore[assignment]
    handler.end_headers = lambda: None  # type: ignore[assignment]
    handler._captured = captured  # type: ignore[attr-defined]
    return handler


def _read_json(handler: APIRequestHandler) -> Any:
    return json.loads(handler.wfile.getvalue().decode("utf-8"))


def test_send_error_masks_5xx_details(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    APIRequestHandler._send_error(  # type: ignore[arg-type]
        handler,
        500,
        "boom",
        details={"secret": "x"},
        trace_id="t",
    )
    payload = _read_json(handler)
    assert payload["success"] is False
    assert payload["error"]["message"] == "服务器内部错误"
    assert "details" not in payload["error"]


def test_parse_body_rejects_oversized_payload(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    handler.headers = {"Content-Length": str(10 * 1024 * 1024 + 1)}
    handler.rfile = io.BytesIO(b"x" * 10)
    assert APIRequestHandler._parse_body(handler) is None  # type: ignore[arg-type]


def test_cache_roundtrip_and_expiry_updates_metrics(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    key = handler._get_cache_key("/api/health", "GET", {"a": 1})

    handler._cache_response(key, {"ok": True}, CacheStrategy.SHORT_TERM)
    cached = handler._get_cached_response(key)
    assert cached == {"ok": True}
    assert handler.server.api_metrics["cache_hits_total"] == 1

    # Force expiry and ensure miss counter increments.
    handler.server.request_cache[key]["expires_at"] = datetime.now() - timedelta(seconds=1)
    assert handler._get_cached_response(key) is None
    assert handler.server.api_metrics["cache_misses_total"] == 1


def test_update_metrics_tracks_endpoint_and_p95(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    handler._update_metrics("/api/x", "GET", 12.3, success=True)
    handler._update_metrics("/api/x", "GET", 50.0, success=False)

    metrics = handler.server.api_metrics
    assert metrics["total_requests"] == 2
    assert metrics["successful_requests"] == 1
    assert metrics["failed_requests"] == 1
    assert metrics["endpoints"]["GET:/api/x"]["requests"] == 2
    assert list(handler.server.request_durations_ms)
    assert handler._p95([1, 2, 3, 4, 5]) >= 4.0


def test_authenticate_request_extracts_key_from_headers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VCL_API_KEYS", "k1")
    handler = _make_handler(tmp_path)
    handler.server.auth_middleware = AuthMiddleware(enabled=True)

    handler.headers = {}
    assert handler._authenticate_request() is None

    handler.headers = {"X-API-Key": "k1"}
    assert handler._authenticate_request()

    handler.headers = {"Authorization": "Bearer k1"}
    assert handler._authenticate_request()


def test_api_docs_route_returns_openapi_json(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    handler.path = "/api/docs"
    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    payload = _read_json(handler)
    assert payload["openapi"] == "3.0.0"
    assert "/api/health" in payload["paths"]


def test_readyz_db_check_reports_not_ready_when_sqlite_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VCL_READY_CHECK_DB", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.sqlite'}")
    monkeypatch.delenv("REDIS_ENABLED", raising=False)

    captured: dict[str, Any] = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_readyz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 503
    assert captured["data"]["checks"]["db"]["ok"] is False


def test_readyz_db_non_sqlite_is_skipped_as_ok(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VCL_READY_CHECK_DB", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/db")
    monkeypatch.delenv("REDIS_ENABLED", raising=False)

    captured: dict[str, Any] = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_readyz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 200
    assert captured["data"]["checks"]["db"]["ok"] is True
    assert captured["data"]["checks"]["db"]["detail"] == "skipped_non_sqlite"


def test_readyz_redis_check_can_be_forced_without_real_socket(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VCL_READY_CHECK_DB", raising=False)
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")

    import socket

    monkeypatch.setattr(socket, "create_connection", lambda *_a, **_k: contextlib.nullcontext())

    captured: dict[str, Any] = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_readyz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 200
    assert captured["data"]["checks"]["cache"]["ok"] is True


def test_handler_init_and_setup_cover_timeout_paths(monkeypatch, tmp_path: Path) -> None:
    # Cover APIRequestHandler.__init__ defaults without running the real base __init__.
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda *_a, **_k: None)

    handler = APIRequestHandler()  # type: ignore[call-arg]
    assert handler.api_version == APIVersion.V2
    assert handler.cache_enabled is True
    assert handler.websocket_enabled is False

    # Cover setup timeout behavior without real sockets/streams.
    called: dict[str, float] = {}

    class _Conn:
        def settimeout(self, value: float) -> None:
            called["timeout"] = value

    handler.connection = _Conn()  # type: ignore[attr-defined]
    monkeypatch.setattr(BaseHTTPRequestHandler, "setup", lambda *_a, **_k: None)

    monkeypatch.setenv("VCL_API_CONN_TIMEOUT", "0")
    APIRequestHandler.setup(handler)
    assert called["timeout"] == 10.0


def test_list_records_returns_500_when_storage_missing_method(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VCL_API_KEYS", "k1")

    server = type("S", (), {})()
    server.template_engine = type("E", (), {"list_available_experiments": lambda self: []})()
    server.storage = object()  # no list_records
    server.sessions = {}
    server.request_cache = {}
    server.api_metrics = {}
    server.request_durations_ms = deque(maxlen=10)
    server.auth_middleware = AuthMiddleware(enabled=True)
    server.rate_limiter = None

    handler = object.__new__(APIRequestHandler)
    handler.server = server
    handler.client_address = ("127.0.0.1", 1)
    handler.headers = {"X-API-Key": "k1"}
    handler.path = "/api/records"
    handler.wfile = io.BytesIO()

    captured = {"status": 0, "headers": {}}
    handler.send_response = lambda code, message=None: captured.__setitem__("status", code)  # type: ignore[assignment]  # noqa: ARG005
    handler.send_header = lambda k, v: captured["headers"].__setitem__(k, v)  # type: ignore[assignment]
    handler.end_headers = lambda: None  # type: ignore[assignment]

    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert captured["status"] == 500
    assert payload["success"] is False


def test_apiserver_start_stop_and_is_running_without_binding_socket(monkeypatch, tmp_path: Path) -> None:
    class _FakeHTTPServer:
        def __init__(self, addr, handler_cls):  # noqa: ANN001
            self.server_address = addr
            self.handler_cls = handler_cls

        def serve_forever(self) -> None:
            return

        def shutdown(self) -> None:
            return

        def server_close(self) -> None:
            return

    class _FakeThread:
        def __init__(self, target=None, daemon=None):  # noqa: ANN001
            self._alive = False
            self._target = target
            self.daemon = daemon

        def start(self) -> None:
            self._alive = True
            if callable(self._target):
                self._target()

        def is_alive(self) -> bool:
            return self._alive

    import src.api.server as server_module

    monkeypatch.setattr(server_module, "HTTPServer", _FakeHTTPServer)
    monkeypatch.setattr(server_module.threading, "Thread", _FakeThread)

    api = APIServer(host="127.0.0.1", port=0, enable_auth=False, enable_rate_limit=False)
    assert api.is_running() is False

    api.start()
    assert api.server is not None
    assert api.thread is not None
    assert api.is_running() is True
    assert hasattr(api.server, "api_metrics")

    api.stop()
    assert api.server is None
    assert api.is_running() is False


def test_graphql_and_websocket_placeholders_are_covered(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    payload = handler._handle_graphql_query("query { experiments { id } }", {})
    assert "data" in payload

    # Websocket disabled -> 400
    handler.wfile = io.BytesIO()
    APIRequestHandler._handle_websocket_upgrade(handler)  # type: ignore[arg-type]
    assert _read_json(handler)["error"]["status"] == 400

    # Websocket enabled but not implemented -> 501
    handler.websocket_enabled = True
    handler.wfile = io.BytesIO()
    APIRequestHandler._handle_websocket_upgrade(handler)  # type: ignore[arg-type]
    assert _read_json(handler)["error"]["status"] == 501


def test_healthz_requires_admin_secret_when_enabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("VCL_HEALTHZ_REQUIRE_ADMIN_SECRET", "true")
    monkeypatch.delenv("VCL_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.setenv("VCL_HEALTH_DIR", str(tmp_path / "health"))

    handler = _make_handler(tmp_path)
    captured: dict[str, Any] = {}

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_healthz(handler, trace_id="t")  # type: ignore[arg-type]
    assert captured["status"] == 503
    assert captured["data"]["checks"]["secrets"]["admin"]["ok"] is False


def test_do_get_converts_unexpected_exception_to_system_error(monkeypatch, tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)
    handler.path = "/api/health"

    def _boom(_trace: str) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(handler, "_handle_health_check", _boom)
    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]

    payload = _read_json(handler)
    assert payload["success"] is False
    assert payload["error"]["type"] == "SYS_INTERNAL_ERROR"


def test_do_get_metrics_update_failure_is_swallowed(tmp_path: Path, monkeypatch) -> None:
    handler = _make_handler(tmp_path)
    handler.path = "/api/health"

    monkeypatch.setattr(handler, "_update_metrics", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("m")))  # type: ignore[arg-type]
    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 200  # type: ignore[attr-defined]


def test_do_post_missing_and_invalid_api_key_and_rate_limit(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(key: str):
            return {"permissions": ["read"]} if key == "good" else None

    handler.server.auth_middleware = _Auth()
    handler.server.rate_limiter = None
    handler.client_address = ("127.0.0.1", 1)

    handler.path = "/api/experiments/start"
    handler.headers = {"Content-Type": "application/json"}
    handler.rfile = io.BytesIO(b"{}")
    handler.wfile = io.BytesIO()
    handler.headers["Content-Length"] = "2"

    # Missing key
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 401  # type: ignore[attr-defined]

    # Invalid key
    handler.wfile = io.BytesIO()
    handler.headers["X-API-Key"] = "bad"
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 401  # type: ignore[attr-defined]

    # Rate limited
    class _Limiter:
        @staticmethod
        def is_allowed(_client: str) -> bool:
            return False

    handler.server.rate_limiter = _Limiter()
    handler.wfile = io.BytesIO()
    handler.headers["X-API-Key"] = "good"
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 429  # type: ignore[attr-defined]


def test_do_post_unknown_path_and_unexpected_exception(tmp_path: Path, monkeypatch) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read", "write"]}

    handler.server.auth_middleware = _Auth()
    handler.server.rate_limiter = None
    handler.client_address = ("127.0.0.1", 1)

    handler.headers = {"Content-Type": "application/json", "X-API-Key": "k", "Content-Length": "2"}
    handler.rfile = io.BytesIO(b"{}")

    # Unknown POST path -> 404
    handler.path = "/api/unknown"
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 404  # type: ignore[attr-defined]

    # Unexpected exception in handler -> 500
    handler.path = "/api/experiments/start"
    handler.wfile = io.BytesIO()
    handler.rfile = io.BytesIO(b"{}")
    handler.headers["Content-Length"] = "2"
    monkeypatch.setattr(handler, "_handle_start_experiment", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]


def test_is_writable_directory_exception_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "mkdir", lambda *_a, **_k: (_ for _ in ()).throw(OSError("nope")))
    assert APIRequestHandler._is_writable_directory(tmp_path / "x") is False


def test_list_experiments_internal_error_becomes_500(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read"]}

    class _Engine:
        def list_available_experiments(self):
            raise RuntimeError("boom")

    handler.server.auth_middleware = _Auth()
    handler.server.template_engine = _Engine()
    handler.headers = {"X-API-Key": "k"}
    handler.path = "/api/experiments"
    handler.wfile = io.BytesIO()

    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]


def test_start_submit_finish_internal_exceptions_are_caught(tmp_path: Path, monkeypatch) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read", "write"]}

    handler.server.auth_middleware = _Auth()
    handler.server.rate_limiter = None
    handler.client_address = ("127.0.0.1", 1)
    handler.headers = {"Content-Type": "application/json", "X-API-Key": "k"}

    import src.api.server as server_module

    class _BoomController:
        def __init__(self, *args, **kwargs):  # noqa: ANN001,ARG002
            raise RuntimeError("controller init failed")

    monkeypatch.setattr(server_module, "ExperimentController", _BoomController)

    handler.path = "/api/experiments/start"
    handler.rfile = io.BytesIO(b'{"experiment_id":"exp-1","user_id":"u"}')
    handler.headers["Content-Length"] = str(len(handler.rfile.getvalue()))
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]

    # Now create a session with a controller that raises on submit/finish.
    class _Controller:
        current_step_index = 0

        def submit_step(self, _data):  # noqa: ANN001
            raise RuntimeError("submit failed")

        def get_progress(self):
            return {}

        def is_completed(self) -> bool:
            return False

        def get_current_step(self):
            return None

        def complete_experiment(self):
            raise RuntimeError("finish failed")

    handler.server.sessions["s"] = _Controller()

    handler.path = "/api/experiments/submit"
    handler.rfile = io.BytesIO(b'{"session_id":"s","data":{}}')
    handler.headers["Content-Length"] = str(len(handler.rfile.getvalue()))
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]

    handler.path = "/api/experiments/finish"
    handler.rfile = io.BytesIO(b'{"session_id":"s"}')
    handler.headers["Content-Length"] = str(len(handler.rfile.getvalue()))
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]


def test_post_metrics_update_failure_is_swallowed(tmp_path: Path, monkeypatch) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read", "write"]}

    handler.server.auth_middleware = _Auth()
    handler.headers = {"Content-Type": "application/json", "X-API-Key": "k"}
    handler.client_address = ("127.0.0.1", 1)
    handler.path = "/api/unknown"
    handler.rfile = io.BytesIO(b"{}")
    handler.headers["Content-Length"] = "2"
    handler.wfile = io.BytesIO()

    monkeypatch.setattr(handler, "_update_metrics", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("m")))  # type: ignore[arg-type]
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 404  # type: ignore[attr-defined]


def test_finish_experiment_session_not_found_and_save_fallback(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read", "write"]}

    handler.server.auth_middleware = _Auth()
    handler.client_address = ("127.0.0.1", 1)
    handler.headers = {"Content-Type": "application/json", "X-API-Key": "k"}

    # Session missing -> 404
    handler.path = "/api/experiments/finish"
    handler.rfile = io.BytesIO(b'{"session_id":"missing"}')
    handler.headers["Content-Length"] = str(len(handler.rfile.getvalue()))
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 404  # type: ignore[attr-defined]

    # Save fallback path: store has `save` but no `save_record`
    class _Record:
        user_id = "u"
        record_id = "r"
        final_score = 1
        total_mistakes = 0
        total_duration_seconds = 1

    class _Controller:
        def complete_experiment(self):
            return _Record()

    class _Store:
        def save(self, _key: str, _record: Any) -> bool:
            return False

    handler.server.sessions["s"] = _Controller()
    handler.server.storage = _Store()

    handler.path = "/api/experiments/finish"
    handler.rfile = io.BytesIO(b'{"session_id":"s"}')
    handler.headers["Content-Length"] = str(len(handler.rfile.getvalue()))
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 200  # type: ignore[attr-defined]
    assert "s" not in handler.server.sessions


def test_records_list_and_get_error_paths_are_covered(tmp_path: Path) -> None:
    handler = _make_handler(tmp_path)

    class _Auth:
        enabled = True

        @staticmethod
        def verify_api_key(_key: str):
            return {"permissions": ["read"]}

    handler.server.auth_middleware = _Auth()
    handler.headers = {"X-API-Key": "k"}

    class _BadListStore:
        def list_records(self, user_id=None):  # noqa: ANN001
            raise RuntimeError("list failed")

    handler.server.storage = _BadListStore()
    handler.path = "/api/records?user_id=u"
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]

    class _BadLoadStore:
        def list_records(self, user_id=None):  # noqa: ANN001
            return [{"record_id": "r", "user_id": "u"}]

        def load_record(self, _user_id: str, _record_id: str):  # noqa: ARG002
            raise RuntimeError("load failed")

    handler.server.storage = _BadLoadStore()
    handler.path = "/api/records/r"
    handler.wfile = io.BytesIO()
    APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    assert handler._captured["status"] == 500  # type: ignore[attr-defined]
