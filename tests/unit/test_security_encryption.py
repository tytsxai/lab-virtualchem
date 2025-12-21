import pytest

from src.core.common_exceptions import SecurityError
from src.security.encryption import ENV_SECRET_KEY, MIN_SECRET_KEY_LENGTH, get_secret_key


def test_get_secret_key_missing_env_raises_security_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(ENV_SECRET_KEY, raising=False)
    with pytest.raises(SecurityError) as exc_info:
        get_secret_key()
    assert ENV_SECRET_KEY in str(exc_info.value)
    assert exc_info.value.details.get("threat_type") == "missing_secret_key"
    assert exc_info.value.details.get("env_var") == ENV_SECRET_KEY


def test_get_secret_key_too_short_raises_security_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(ENV_SECRET_KEY, "a" * (MIN_SECRET_KEY_LENGTH - 1))
    with pytest.raises(SecurityError) as exc_info:
        get_secret_key()
    assert exc_info.value.details.get("threat_type") == "weak_secret_key"
    assert exc_info.value.details.get("env_var") == ENV_SECRET_KEY
    assert exc_info.value.details.get("min_length") == MIN_SECRET_KEY_LENGTH


def test_get_secret_key_valid_returns_value(monkeypatch: pytest.MonkeyPatch):
    expected = "x" * MIN_SECRET_KEY_LENGTH
    monkeypatch.setenv(ENV_SECRET_KEY, expected)
    assert get_secret_key() == expected


def test_get_secret_key_trims_whitespace(monkeypatch: pytest.MonkeyPatch):
    expected = "y" * MIN_SECRET_KEY_LENGTH
    monkeypatch.setenv(ENV_SECRET_KEY, f"  {expected} \n")
    assert get_secret_key() == expected


def test_get_secret_key_blank_string_raises_security_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(ENV_SECRET_KEY, "   \n\t")
    with pytest.raises(SecurityError) as exc_info:
        get_secret_key()
    assert exc_info.value.details.get("threat_type") == "missing_secret_key"
