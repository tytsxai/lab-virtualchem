import json
from unittest.mock import Mock

import pytest
import requests

from src.services.http_client import (
    HttpClientService,
    InvalidResponseSchemaError,
    ResponseTooLargeError,
    RetryConfig,
)


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object | None = None,
        headers: dict[str, str] | None = None,
        encoding: str = "utf-8",
        http_error: requests.HTTPError | None = None,
    ):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.encoding = encoding
        self._http_error = http_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self) -> None:
        return None

    def raise_for_status(self) -> None:
        if self._http_error is not None:
            raise self._http_error
        if 400 <= self.status_code:
            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self  # type: ignore[attr-defined]
            raise err

    def iter_content(self, chunk_size: int = 8192):
        data = json.dumps(self._payload).encode(self.encoding)
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]


def test_http_client_sets_default_timeout_and_stream():
    session = Mock(spec=requests.Session)
    session.request.return_value = _FakeResponse(payload={"ok": True})

    client = HttpClientService(session=session, timeout=30.0)
    assert client.request_json("GET", "http://example.test") == {"ok": True}

    session.request.assert_called_once()
    _method, _url = session.request.call_args.args
    kwargs = session.request.call_args.kwargs
    assert _method == "GET"
    assert _url == "http://example.test"
    assert kwargs["timeout"] == 30.0
    assert kwargs["stream"] is True


def test_http_client_retries_with_exponential_backoff():
    session = Mock(spec=requests.Session)
    session.request.side_effect = [
        requests.exceptions.Timeout("t1"),
        requests.exceptions.Timeout("t2"),
        _FakeResponse(payload={"ok": True}),
    ]
    sleep = Mock()

    client = HttpClientService(
        session=session,
        retry=RetryConfig(max_retries=3, initial_delay=0.5, backoff_factor=2.0),
        sleep_fn=sleep,
    )
    assert client.request_json("GET", "http://example.test") == {"ok": True}
    assert session.request.call_count == 3
    sleep.assert_any_call(0.5)
    sleep.assert_any_call(1.0)
    assert sleep.call_count == 2


def test_http_client_gives_up_after_max_retries():
    session = Mock(spec=requests.Session)
    session.request.side_effect = requests.exceptions.Timeout("boom")
    sleep = Mock()

    client = HttpClientService(
        session=session, retry=RetryConfig(max_retries=2, initial_delay=0.1), sleep_fn=sleep
    )
    with pytest.raises(requests.exceptions.Timeout):
        client.request_json("GET", "http://example.test")

    assert session.request.call_count == 3  # 1 + max_retries
    assert sleep.call_count == 2


def test_http_client_does_not_retry_on_4xx():
    session = Mock(spec=requests.Session)
    session.request.return_value = _FakeResponse(status_code=400, payload={"err": "bad"})
    sleep = Mock()

    client = HttpClientService(session=session, sleep_fn=sleep)
    with pytest.raises(requests.exceptions.HTTPError):
        client.request_json("GET", "http://example.test")

    assert session.request.call_count == 1
    sleep.assert_not_called()


def test_http_client_validates_json_schema():
    session = Mock(spec=requests.Session)
    session.request.return_value = _FakeResponse(payload={"ok": "yes"})

    client = HttpClientService(session=session)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    with pytest.raises(InvalidResponseSchemaError):
        client.request_json("GET", "http://example.test", schema=schema)


def test_http_client_limits_response_size_via_content_length_header():
    session = Mock(spec=requests.Session)
    session.request.return_value = _FakeResponse(
        payload={"big": "x" * 1000}, headers={"Content-Length": "999999"}
    )

    client = HttpClientService(session=session, max_response_bytes=1024)
    with pytest.raises(ResponseTooLargeError):
        client.request_json("GET", "http://example.test")


def test_http_client_closes_session_with_context_manager():
    session = Mock(spec=requests.Session)
    session.request.return_value = _FakeResponse(payload={"ok": True})

    with HttpClientService(session=session) as client:
        assert client.request_json("GET", "http://example.test") == {"ok": True}
    session.close.assert_called_once()

