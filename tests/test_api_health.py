from src import __version__ as APP_VERSION
from src.api.server import APIRequestHandler


def test_health_check_reports_app_version():
    captured: dict = {}

    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]

    APIRequestHandler._handle_health_check(handler, trace_id="trace")

    assert captured["status"] == 200
    assert captured["data"]["status"] == "healthy"
    assert captured["data"]["version"] == APP_VERSION
