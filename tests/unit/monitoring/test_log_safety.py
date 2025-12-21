from __future__ import annotations

from src.monitoring.log_safety import sanitize_log_data


def test_sanitize_log_data_masks_sensitive_fields() -> None:
    payload = {
        "password": "p@ssw0rd",
        "token": "abcd",
        "api_key": "k123",
        "secret_key": "s456",
        "email": "user@example.com",
        "phone": "1234567890",
        "nested": {"accessToken": "t789", "normal": "ok"},
        "monkey": "banana",
    }

    sanitized = sanitize_log_data(payload)

    assert sanitized["password"] == "***"
    assert sanitized["token"] == "***"
    assert sanitized["api_key"] == "***"
    assert sanitized["secret_key"] == "***"
    assert sanitized["email"] == "***@***"
    assert sanitized["phone"] == "***"
    assert sanitized["nested"]["accessToken"] == "***"
    assert sanitized["nested"]["normal"] == "ok"
    assert sanitized["monkey"] == "banana"


def test_sanitize_log_data_filters_newlines_and_control_chars() -> None:
    msg = "line1\nline2\r\nline3\x00\x1f\x7fEND"
    sanitized = sanitize_log_data(msg)
    assert "\n" not in sanitized
    assert "\r" not in sanitized
    assert "\x00" not in sanitized
    assert "\x1f" not in sanitized
    assert "\x7f" not in sanitized
    assert "line1" in sanitized
    assert "line2" in sanitized
    assert "line3" in sanitized


def test_sanitize_log_data_truncates_long_strings() -> None:
    long_msg = "a" * 50
    sanitized = sanitize_log_data(long_msg, max_len=10)
    assert len(sanitized) <= 10


def test_sanitize_log_data_sanitizes_sequences() -> None:
    data = [
        {"email": "user@example.com"},
        "hello\nworld",
    ]
    sanitized = sanitize_log_data(data, max_len=100)
    assert sanitized[0]["email"] == "***@***"
    assert "\n" not in sanitized[1]

