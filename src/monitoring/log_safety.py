"""Monitoring log safety helpers.

This module provides:
- sensitive data masking (`sanitize_log_data`)
- log injection protection (strip control chars/newlines)
- message length limiting
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping, Sequence
from typing import Any


_SENSITIVE_TOKENS = {"password", "token", "key", "secret", "email", "phone"}
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")
_CAMEL_SPLIT_RE = re.compile(r"([a-z0-9])([A-Z])")

# Keep logs readable but bounded; applies after control-char filtering.
DEFAULT_MAX_LOG_LEN = 2000


def _tokenize_field_name(name: str) -> set[str]:
    """Split a field name into lowercase tokens.

    Handles snake/kebab/camelCase in a lightweight way.
    """
    if not name:
        return set()
    normalized = _CAMEL_SPLIT_RE.sub(r"\1 \2", name)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", normalized)
    return {part.lower() for part in normalized.split() if part}


def _is_sensitive_field(field_name: str) -> bool:
    tokens = _tokenize_field_name(field_name)
    return any(token in _SENSITIVE_TOKENS for token in tokens)


def _mask_value(value: Any, field_name: str | None = None) -> str:
    # Minimal but explicit: never leak the original payload for sensitive fields.
    if field_name:
        tokens = _tokenize_field_name(field_name)
        if "email" in tokens:
            return "***@***"
        if "phone" in tokens:
            return "***"
    return "***"


def _sanitize_string(value: str, max_len: int) -> str:
    # Prevent log injection: remove newlines and control chars.
    cleaned = value.replace("\r", " ").replace("\n", " ")
    cleaned = _CONTROL_CHARS_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    if max_len > 0 and len(cleaned) > max_len:
        return cleaned[: max_len - 1] + "…"
    return cleaned


def sanitize_log_data(data: Any, *, max_len: int = DEFAULT_MAX_LOG_LEN) -> Any:
    """Return a sanitized copy of data safe to use in logs.

    - Masks sensitive fields: password/token/key/secret/email/phone
    - Strips newlines/control characters from strings (log injection defense)
    - Truncates long strings
    """
    if data is None:
        return None

    if isinstance(data, str):
        return _sanitize_string(data, max_len=max_len)

    if isinstance(data, bytes):
        try:
            return _sanitize_string(data.decode("utf-8", errors="replace"), max_len=max_len)
        except Exception:  # noqa: BLE001
            return "***"

    if isinstance(data, Mapping):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key)
            if _is_sensitive_field(key_str):
                sanitized[key_str] = _mask_value(value, field_name=key_str)
            else:
                sanitized[key_str] = sanitize_log_data(value, max_len=max_len)
        return sanitized

    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        # Convert dataclass -> dict, then sanitize.
        return sanitize_log_data(dataclasses.asdict(data), max_len=max_len)

    if isinstance(data, (list, tuple, set, frozenset)):
        sanitized_seq = [sanitize_log_data(item, max_len=max_len) for item in data]
        return type(data)(sanitized_seq) if not isinstance(data, list) else sanitized_seq

    # Avoid recursively walking arbitrary objects; represent them deterministically.
    try:
        text = str(data)
        cleaned = _sanitize_string(text, max_len=max_len)
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = _sanitize_string(cleaned[1:-1], max_len=max_len)
        return cleaned
    except Exception:  # noqa: BLE001
        return _sanitize_string(str(data), max_len=max_len)
