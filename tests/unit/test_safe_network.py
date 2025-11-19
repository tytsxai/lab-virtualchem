from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.utils import enhanced_error_handler, safe_network
from src.utils.safe_network import NetworkHealthMonitor, RetryStrategy, SafeNetworkClient


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        if callable(self._json_data):
            return self._json_data()
        return self._json_data

    def iter_content(self, chunk_size=8192):
        yield from ()


@pytest.fixture(autouse=True)
def disable_error_dialogs(monkeypatch):
    """Avoid GUI side effects caused by EnhancedErrorHandler."""
    handler = enhanced_error_handler.EnhancedErrorHandler()
    previous = handler.show_dialogs
    handler.show_dialogs = False
    monkeypatch.setattr(safe_network, "HAS_REQUESTS", True)
    try:
        yield
    finally:
        handler.show_dialogs = previous


def test_request_builds_url_and_parses_json(monkeypatch):
    client = SafeNetworkClient(base_url="https://api.example.com", timeout=5)
    calls = {}

    def fake_request(method, url, **kwargs):
        calls["method"] = method
        calls["url"] = url
        calls["timeout"] = kwargs.get("timeout")
        return DummyResponse(json_data={"status": "ok"})

    monkeypatch.setattr(safe_network.requests, "request", fake_request)

    result = client.request("GET", "/status?verbose=1")
    assert result == {"status": "ok"}
    assert calls == {
        "method": "GET",
        "url": "https://api.example.com/status?verbose=1",
        "timeout": 5,
    }


def test_request_returns_text_when_json_invalid(monkeypatch):
    client = SafeNetworkClient(base_url="https://api.example.com")

    def fake_request(*_args, **_kwargs):
        def bad_json():
            raise ValueError("invalid json")

        return DummyResponse(json_data=bad_json, text="plain-text response")

    monkeypatch.setattr(safe_network.requests, "request", fake_request)

    result = client.request("GET", "/text")
    assert result == {"text": "plain-text response"}


def test_request_http_client_error_converted(monkeypatch):
    client = SafeNetworkClient(base_url="https://api.example.com")

    def fake_request(*_args, **_kwargs):
        class Response:
            def raise_for_status(self):
                error = safe_network.requests.exceptions.HTTPError("boom")
                error.response = SimpleNamespace(status_code=404)
                raise error

            def json(self):
                return {}

        return Response()

    monkeypatch.setattr(safe_network.requests, "request", fake_request)

    with pytest.raises(ValueError) as excinfo:
        SafeNetworkClient.request.__wrapped__(client, "GET", "/missing")

    assert "资源不存在" in str(excinfo.value)


def test_request_retries_connection_errors(monkeypatch):
    client = SafeNetworkClient(
        base_url="https://api.example.com",
        retry_strategy=RetryStrategy(max_retries=3, initial_delay=0.1, backoff_factor=1),
    )
    attempts = {"count": 0}

    def fake_request(*_args, **_kwargs):
        attempts["count"] += 1
        raise safe_network.requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(safe_network.requests, "request", fake_request)
    sleep_calls: list[float] = []
    monkeypatch.setattr(safe_network.time, "sleep", sleep_calls.append)

    with pytest.raises(ConnectionError) as excinfo:
        SafeNetworkClient.request.__wrapped__(client, "GET", "/status")

    assert attempts["count"] == 3
    assert sleep_calls == [0.1, 0.1]
    assert "无法连接到服务器" in str(excinfo.value)


def test_check_connection_handles_missing_requests(monkeypatch):
    client = SafeNetworkClient()
    monkeypatch.setattr(safe_network, "HAS_REQUESTS", False)
    assert client.check_connection("https://example.com") is False


def test_check_connection_success(monkeypatch):
    client = SafeNetworkClient()
    response = SimpleNamespace(status_code=200)
    monkeypatch.setattr(safe_network.requests, "get", lambda *_args, **_kwargs: response)
    assert client.check_connection("https://example.com") is True


def test_download_file_streams_chunks(tmp_path, monkeypatch):
    client = SafeNetworkClient()
    chunks = [b"abc", b"12345"]
    total_size = sum(len(c) for c in chunks)

    class StreamResponse(DummyResponse):
        def __init__(self):
            super().__init__(headers={"content-length": str(total_size)})

        def iter_content(self, chunk_size=8192):
            for chunk in chunks:
                yield chunk

    monkeypatch.setattr(safe_network.requests, "get", lambda *_args, **_kwargs: StreamResponse())

    progress_updates: list[tuple[int, int]] = []

    def callback(downloaded, total):
        progress_updates.append((downloaded, total))

    destination = tmp_path / "file.bin"
    assert client.download_file("https://example.com/file.bin", destination, progress_callback=callback)

    assert destination.read_bytes() == b"abc12345"
    assert progress_updates[-1] == (total_size, total_size)


def test_network_health_monitor_caches_checks(monkeypatch):
    calls = {"count": 0}

    class DummyClient:
        def check_connection(self):
            calls["count"] += 1
            return calls["count"] % 2 == 1

    monkeypatch.setattr(safe_network, "SafeNetworkClient", DummyClient)
    time_values = iter([100.0, 120.0, 200.0])
    monkeypatch.setattr(safe_network.time, "time", lambda: next(time_values))

    monitor = NetworkHealthMonitor(check_interval=60)
    monitor.last_check_time = 0

    assert monitor.is_network_available() is True  # performs check
    assert monitor.is_network_available() is True  # cached, no new check
    assert monitor.is_network_available() is False  # second check, toggled result
    assert calls["count"] == 2


def test_wait_for_network_returns_when_available(monkeypatch):
    monitor = NetworkHealthMonitor(check_interval=0)
    availability = iter([False, False, True])
    monkeypatch.setattr(monitor, "is_network_available", lambda: next(availability))

    time_values = iter([0.0, 2.0, 4.0, 6.0, 8.0])

    def fake_time():
        try:
            return next(time_values)
        except StopIteration:
            return 8.0

    monkeypatch.setattr(safe_network.time, "time", fake_time)
    sleep_durations: list[int] = []
    monkeypatch.setattr(safe_network.time, "sleep", sleep_durations.append)

    assert monitor.wait_for_network(timeout=10, check_interval=2) is True
    assert sleep_durations == [2, 2]
