import dataclasses

import pytest

from src.monitoring.log_safety import DEFAULT_MAX_LOG_LEN, sanitize_log_data


@dataclasses.dataclass
class DemoData:
    password: str
    normal: str


def test_sanitize_log_data_string_control_chars_and_newlines() -> None:
    raw = "hello\nworld\r\n\t\x00!\x7f end"
    sanitized = sanitize_log_data(raw, max_len=1000)
    assert isinstance(sanitized, str)
    assert "\n" not in sanitized
    assert "\r" not in sanitized
    assert "\x00" not in sanitized
    assert "\x7f" not in sanitized
    assert sanitized.startswith("hello world ! end")


def test_sanitize_log_data_string_truncation() -> None:
    raw = "a" * (DEFAULT_MAX_LOG_LEN + 10)
    sanitized = sanitize_log_data(raw)
    assert len(sanitized) == DEFAULT_MAX_LOG_LEN
    assert sanitized.endswith("…")


def test_sanitize_log_data_masks_sensitive_mapping_keys() -> None:
    payload = {
        "password": "p@ss",
        "apiToken": "token",
        "secret_key": "secret",
        "email": "user@example.com",
        "phone": "123456",
        "nested": {"userPassword": "x"},
        "safe": "ok",
    }
    sanitized = sanitize_log_data(payload, max_len=1000)
    assert sanitized["password"] == "***"
    assert sanitized["apiToken"] == "***"
    assert sanitized["secret_key"] == "***"
    assert sanitized["email"] == "***@***"
    assert sanitized["phone"] == "***"
    assert sanitized["nested"]["userPassword"] == "***"
    assert sanitized["safe"] == "ok"


def test_sanitize_log_data_handles_dataclass_bytes_and_sequences() -> None:
    data = {
        "dataclass": DemoData(password="123", normal="hey\nthere"),
        "bytes": b"hi\n\x00",
        "seq": ["ok", {"token": "abc"}],
    }
    sanitized = sanitize_log_data(data, max_len=1000)
    assert sanitized["dataclass"]["password"] == "***"
    assert sanitized["dataclass"]["normal"] == "hey there"
    assert sanitized["bytes"] == "hi"
    assert sanitized["seq"][1]["token"] == "***"


def test_sanitize_log_data_fallback_object_repr_is_sanitized() -> None:
    class Weird:
        def __str__(self) -> str:
            return "line1\nline2"

    sanitized = sanitize_log_data(Weird(), max_len=1000)
    assert sanitized == "line1 line2"


@pytest.mark.parametrize("value", [None, "", "ok"])
def test_sanitize_log_data_passthrough_basics(value) -> None:
    assert sanitize_log_data(value) == value

