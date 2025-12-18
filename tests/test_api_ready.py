from pathlib import Path

from src.api.server import APIRequestHandler


class _DummyEngine:
    def list_available_experiments(self):
        return [{"id": "exp1"}, {"id": "exp2"}]


class _DummyStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir


def test_ready_check_ok(tmp_path):
    captured: dict = {}

    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()
    handler.server.template_engine = _DummyEngine()
    handler.server.storage = _DummyStore(tmp_path)

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]

    APIRequestHandler._handle_ready_check(handler, trace_id="trace")

    assert captured["status"] == 200
    assert captured["data"]["status"] == "ready"
    assert captured["data"]["checks"]["templates"]["ok"] is True
    assert captured["data"]["checks"]["templates"]["count"] == 2
    assert captured["data"]["checks"]["storage"]["ok"] is True


def test_ready_check_fails_when_template_engine_missing(tmp_path):
    captured: dict = {}

    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()
    handler.server.storage = _DummyStore(tmp_path)

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]

    APIRequestHandler._handle_ready_check(handler, trace_id="trace")

    assert captured["status"] == 503
    assert captured["data"]["status"] == "not_ready"
    assert captured["data"]["checks"]["templates"]["ok"] is False

