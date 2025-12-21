"""Unit tests for APIRequestHandler routing/auth/error/CORS without sockets.

The sandbox used by this repo disallows binding TCP sockets during tests, so we
exercise the stdlib-based handler by instantiating it without __init__ and
calling do_GET/do_POST/do_OPTIONS directly with in-memory streams.
"""

from __future__ import annotations

import io
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

api_server = pytest.importorskip("src.api.server")
api_middleware = pytest.importorskip("src.api.middleware")

AuthMiddleware = api_middleware.AuthMiddleware
APIRequestHandler = api_server.APIRequestHandler

pytestmark = pytest.mark.api


@dataclass
class _HandlerResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class _FakeTemplate:
    def __init__(self, exp_id: str):
        self.id = exp_id
        self.title = "T"
        self.description = "D"
        self.category = "C"
        self.level = "L"
        self.steps = [type("Step", (), {"id": "s1", "text": "do", "check": None})()]
        self.score_rules: list[Any] = []


class _FakeTemplateEngine:
    templates_dir = "."

    def list_available_experiments(self):
        return [{"id": "exp-1", "title": "One"}]

    def load_experiment_by_id(self, exp_id: str):
        if exp_id == "missing":
            raise FileNotFoundError(exp_id)
        return _FakeTemplate(exp_id)


class _FakeSubmitResult:
    def __init__(self, valid: bool):
        self.is_valid = valid
        self.message = "ok" if valid else "bad"
        self.errors = [] if valid else ["e"]
        self.warnings: list[str] = []
        self.mistake = type(
            "Mistake",
            (),
            {
                "step_id": "s1",
                "error_type": "wrong",
                "description": "nope",
                "hint": "try again",
                "severity": "low",
            },
        )()


class _FakeRecord:
    def __init__(self, user_id: str, record_id: str, exp_id: str):
        self.user_id = user_id
        self.record_id = record_id
        self.experiment_id = exp_id
        self.final_score = 100
        self.total_mistakes = 0
        self.total_duration_seconds = 1

    def model_dump(self, mode: str = "json"):  # noqa: ARG002
        return {
            "user_id": self.user_id,
            "record_id": self.record_id,
            "experiment_id": self.experiment_id,
            "final_score": self.final_score,
        }


class _FakeExperimentController:
    def __init__(self, template, user_id: str, storage=None):  # noqa: ANN001,ARG002
        self.template = template
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self.current_step_index = 0
        self._completed = False
        self._record = _FakeRecord(user_id=user_id, record_id="r1", exp_id=template.id)

    def start_experiment(self) -> None:
        return

    def get_current_step(self):
        if self._completed:
            return None
        return self.template.steps[self.current_step_index]

    def get_progress(self):
        return {"current": self.current_step_index, "total": len(self.template.steps)}

    def submit_step(self, _user_data: dict[str, Any]):
        self.current_step_index += 1
        if self.current_step_index >= len(self.template.steps):
            self._completed = True
        return _FakeSubmitResult(valid=True)

    def is_completed(self) -> bool:
        return self._completed

    def complete_experiment(self):
        self._completed = True
        return self._record


class _FakeStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._records: dict[tuple[str, str], Any] = {}

    def save_record(self, record: _FakeRecord) -> bool:
        self._records[(record.user_id, record.record_id)] = record
        return True

    def list_records(self, user_id: str | None = None):
        items = []
        for (uid, rid), record in self._records.items():
            if user_id is not None and uid != user_id:
                continue
            items.append(
                {
                    "record_id": rid,
                    "user_id": uid,
                    "experiment_id": record.experiment_id,
                    "experiment_title": "T",
                    "final_score": record.final_score,
                    "started_at": None,
                    "finished_at": None,
                    "status": "done",
                }
            )
        return items

    def load_record(self, user_id: str, record_id: str):
        return self._records.get((user_id, record_id))


def _build_server(tmp_path: Path, *, auth_enabled: bool = True, limiter=None):
    server = type("S", (), {})()
    server.template_engine = _FakeTemplateEngine()
    server.storage = _FakeStore(tmp_path / "data")
    server.storage.base_dir.mkdir(parents=True, exist_ok=True)
    server.sessions = {}
    server.request_cache = {}
    server.api_metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "rate_limited_total": 0,
        "auth_failed_total": 0,
        "cache_hits_total": 0,
        "cache_misses_total": 0,
        "endpoints": {},
    }
    server.request_durations_ms = deque(maxlen=2000)
    server.rate_limiter = limiter
    if auth_enabled:
        server.auth_middleware = AuthMiddleware(enabled=True)
    else:
        server.auth_middleware = type("A", (), {"enabled": False})()
    return server


def _run_handler(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    raw_body: bytes | None = None,
    server=None,
) -> _HandlerResult:
    if headers is None:
        headers = {}
    if server is None:
        server = _build_server(tmp_path)

    import src.api.server as server_module

    monkeypatch.setattr(server_module, "ExperimentController", _FakeExperimentController)

    class _FakeHTMLGenerator:
        def generate(self, record, template, output_path: Path):  # noqa: ANN001
            output_path.write_text("<html>ok</html>", encoding="utf-8")
            return "<html>ok</html>"

    monkeypatch.setattr(server_module, "HTMLGenerator", _FakeHTMLGenerator)

    handler = object.__new__(APIRequestHandler)
    handler.server = server
    handler.client_address = ("127.0.0.1", 12345)
    handler.command = method
    handler.path = path
    handler.headers = headers

    payload = raw_body
    if payload is None and body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    if payload is None:
        payload = b""

    headers.setdefault("Content-Length", str(len(payload)))
    handler.rfile = io.BytesIO(payload)
    handler.wfile = io.BytesIO()

    captured = {"status": 0, "headers": {}}

    def _send_response(code: int, message: str | None = None):  # noqa: ARG001
        captured["status"] = code

    def _send_header(key: str, value: str):
        captured["headers"][key] = value

    handler.send_response = _send_response  # type: ignore[assignment]
    handler.send_header = _send_header  # type: ignore[assignment]
    handler.end_headers = lambda: None  # type: ignore[assignment]

    if method == "GET":
        APIRequestHandler.do_GET(handler)  # type: ignore[arg-type]
    elif method == "POST":
        APIRequestHandler.do_POST(handler)  # type: ignore[arg-type]
    elif method == "OPTIONS":
        APIRequestHandler.do_OPTIONS(handler)  # type: ignore[arg-type]
    else:  # pragma: no cover
        raise ValueError(method)

    return _HandlerResult(
        status=int(captured["status"]),
        headers={str(k): str(v) for k, v in captured["headers"].items()},
        body=handler.wfile.getvalue(),
    )


@pytest.fixture()
def api_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VCL_API_KEYS", "user-key,admin-key")
    monkeypatch.setenv("VCL_API_ADMIN_KEYS", "admin-key")
    monkeypatch.delenv("VCL_API_CORS_ORIGINS", raising=False)
    return tmp_path


def test_api_options_cors_preflight_includes_allow_headers(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "OPTIONS",
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert resp.status == 204
    assert resp.headers["Access-Control-Allow-Methods"]
    assert resp.headers["Access-Control-Allow-Headers"]
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_api_cors_disallowed_origin_not_echoed(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/health",
        headers={"Origin": "http://evil.example.com"},
    )
    assert resp.status == 200
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_api_health_no_auth_required(monkeypatch, api_env: Path):
    resp = _run_handler(monkeypatch, api_env, "GET", "/api/health")
    assert resp.status == 200
    assert resp.json()["status"] == "healthy"


def test_api_list_experiments_requires_api_key(monkeypatch, api_env: Path):
    resp = _run_handler(monkeypatch, api_env, "GET", "/api/experiments")
    assert resp.status == 401
    payload = resp.json()
    assert payload["success"] is False


def test_api_list_experiments_rejects_invalid_key(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/experiments",
        headers={"X-API-Key": "nope"},
    )
    assert resp.status == 401


def test_api_list_experiments_ok(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/experiments",
        headers={"X-API-Key": "user-key"},
    )
    assert resp.status == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["data"]["count"] == 1


def test_api_get_experiment_not_found_returns_404(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/experiments/missing",
        headers={"X-API-Key": "user-key"},
    )
    assert resp.status == 404
    assert resp.json()["success"] is False


def test_api_unknown_path_returns_structured_404(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/nope",
        headers={"X-API-Key": "user-key"},
    )
    assert resp.status == 404
    payload = resp.json()
    assert payload["success"] is False
    # BaseAppException.to_dict shape uses `code/type/message/...` (not HTTP status).
    assert payload["error"]["type"]
    assert payload["error"].get("trace_id")


def test_api_auth_middleware_disabled_is_503(monkeypatch, api_env: Path):
    server = _build_server(api_env, auth_enabled=False)
    resp = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/experiments",
        headers={"X-API-Key": "user-key"},
        server=server,
    )
    assert resp.status == 503


def test_api_rate_limited_returns_429(monkeypatch, api_env: Path):
    class _Limiter:
        @staticmethod
        def is_allowed(_client: str) -> bool:
            return False

    server = _build_server(api_env, limiter=_Limiter())
    resp = _run_handler(monkeypatch, api_env, "GET", "/api/health", server=server)
    assert resp.status == 429


def test_api_metrics_requires_admin_permission(monkeypatch, api_env: Path):
    non_admin = _run_handler(
        monkeypatch, api_env, "GET", "/metrics", headers={"X-API-Key": "user-key"}
    )
    assert non_admin.status == 403

    admin = _run_handler(
        monkeypatch, api_env, "GET", "/metrics", headers={"X-API-Key": "admin-key"}
    )
    assert admin.status == 200
    assert b"vcl_api_requests_total" in admin.body
    assert "text/plain" in admin.headers.get("Content-type", "")


def test_api_post_requires_json_content_type(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/start",
        headers={"X-API-Key": "user-key", "Content-Type": "text/plain"},
        raw_body=b"{}",
    )
    assert resp.status == 415


def test_api_post_missing_auth_middleware_returns_503(monkeypatch, api_env: Path):
    server = _build_server(api_env, auth_enabled=False)
    resp = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/start",
        headers={"Content-Type": "application/json"},
        raw_body=b"{}",
        server=server,
    )
    assert resp.status == 503


def test_api_post_invalid_json_returns_400(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/start",
        headers={"X-API-Key": "user-key", "Content-Type": "application/json"},
        raw_body=b"{not-json}",
    )
    assert resp.status == 400


def test_api_start_experiment_validation_error(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/start",
        headers={"X-API-Key": "user-key"},
        body={"user_id": "u1"},
    )
    assert resp.status in {400, 422}
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"].get("details", {}).get("errors")


def test_api_start_submit_finish_and_records_flow(monkeypatch, api_env: Path):
    # Keep file writes (reports/) inside the temp directory, without changing the
    # process working directory for the entire module (coverage uses CWD).
    monkeypatch.chdir(api_env)
    server = _build_server(api_env)
    start = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/start",
        headers={"X-API-Key": "user-key"},
        body={"experiment_id": "exp-1", "user_id": "u1"},
        server=server,
    )
    assert start.status == 201
    session_id = start.json()["session_id"]

    submit = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/submit",
        headers={"X-API-Key": "user-key"},
        body={"session_id": session_id, "data": {"a": 1}},
        server=server,
    )
    assert submit.status == 200
    assert submit.json()["passed"] is True

    finish = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/finish",
        headers={"X-API-Key": "user-key"},
        body={"session_id": session_id},
        server=server,
    )
    assert finish.status == 200
    record_id = finish.json()["record_id"]

    records = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        "/api/records?user_id=u1",
        headers={"X-API-Key": "user-key"},
        server=server,
    )
    assert records.status == 200
    assert records.json()["count"] == 1

    record = _run_handler(
        monkeypatch,
        api_env,
        "GET",
        f"/api/records/{record_id}?user_id=u1",
        headers={"X-API-Key": "user-key"},
        server=server,
    )
    assert record.status == 200
    assert record.json()["record"]["record_id"] == record_id

    report = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/reports/generate",
        headers={"X-API-Key": "user-key"},
        body={"record_id": record_id, "format": "html"},
        server=server,
    )
    assert report.status == 200
    payload = report.json()
    assert payload["record_id"] == record_id
    assert payload["content"]
    assert (api_env / "reports" / f"{record_id}.html").exists()


def test_api_submit_step_session_not_found(monkeypatch, api_env: Path):
    resp = _run_handler(
        monkeypatch,
        api_env,
        "POST",
        "/api/experiments/submit",
        headers={"X-API-Key": "user-key"},
        body={"session_id": "missing", "data": {}},
    )
    assert resp.status == 404
