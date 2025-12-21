"""HTTP 客户端服务（安全增强版）。

提供统一的外部 HTTP 调用入口：
- 默认超时
- 有上限的重试 + 指数退避
- 响应大小限制
- JSON schema 校验
- 资源清理（Session.close）与 context manager
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


class ResponseTooLargeError(Exception):
    """响应体过大。"""


class InvalidResponseSchemaError(ValueError):
    """外部响应不符合预期 schema。"""


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 0.5
    backoff_factor: float = 2.0
    max_delay: float = 10.0

    def delay_for_attempt(self, attempt_index: int) -> float:
        delay = self.initial_delay * (self.backoff_factor**attempt_index)
        return min(delay, self.max_delay)


class HttpClientService:
    """用于 services 层的安全 HTTP 客户端。"""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
        max_response_bytes: int = 2 * 1024 * 1024,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._session = session or requests.Session()
        self._timeout = timeout
        self._retry = retry or RetryConfig()
        self._max_response_bytes = max_response_bytes
        self._sleep_fn = sleep_fn
        self._closed = False

    def __enter__(self) -> "HttpClientService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._session.close()
        self._closed = True

    def request_json(
        self,
        method: str,
        url: str,
        *,
        schema: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_response_bytes: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """发送 HTTP 请求并返回 JSON（含重试/退避、schema 校验、大小限制）。"""
        if self._closed:
            raise RuntimeError("HttpClientService 已关闭")

        effective_timeout = self._timeout if timeout is None else timeout
        limit = self._max_response_bytes if max_response_bytes is None else max_response_bytes

        kwargs.setdefault("timeout", effective_timeout)
        kwargs.setdefault("stream", True)

        last_error: BaseException | None = None
        attempts = self._retry.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._session.request(method, url, **kwargs)
                with response:
                    response.raise_for_status()
                    data = self._read_json_limited(response, limit)
                self._validate_schema(data, schema)
                return data
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                last_error = exc
            except requests.exceptions.HTTPError as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if isinstance(status, int) and 400 <= status <= 499 and status != 429:
                    raise
                last_error = exc
            except (ResponseTooLargeError, InvalidResponseSchemaError, ValueError) as exc:
                raise

            if attempt >= attempts - 1:
                break
            self._sleep_fn(self._retry.delay_for_attempt(attempt))

        if last_error is not None:
            raise last_error
        raise RuntimeError("请求失败：未知错误")

    def _read_json_limited(self, response: requests.Response, limit: int) -> Any:
        """流式读取并限制最大字节数，然后解析为 JSON。"""
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > limit:
                    raise ResponseTooLargeError(
                        f"响应过大: {content_length} bytes (limit={limit})"
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > limit:
                raise ResponseTooLargeError(f"响应过大: {total} bytes (limit={limit})")
            chunks.append(chunk)

        raw = b"".join(chunks).decode(response.encoding or "utf-8")
        return json.loads(raw)

    def _validate_schema(
        self, data: Any, schema: Mapping[str, Any] | None
    ) -> None:
        if schema is None:
            return
        try:
            Draft202012Validator(schema).validate(data)
        except ValidationError as exc:
            raise InvalidResponseSchemaError(str(exc)) from exc
