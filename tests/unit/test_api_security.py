"""Tests for REST API hardening (CORS + API keys)."""

from __future__ import annotations

import json
from pathlib import Path

from src.api.middleware import AuthMiddleware
from src.api.server import _is_allowed_origin, _parse_cors_origins


def test_cors_allows_loopback_origins_by_default():
    assert _is_allowed_origin("http://localhost:3000", [])
    assert _is_allowed_origin("http://127.0.0.1:8000", [])
    assert _is_allowed_origin("http://[::1]:5173", [])
    assert _is_allowed_origin("https://localhost", [])


def test_cors_rejects_prefix_tricks():
    assert not _is_allowed_origin("http://localhost.evil.com", [])
    assert not _is_allowed_origin("http://127.0.0.1.evil.com", [])


def test_cors_allows_explicit_allowlist():
    allowlist = _parse_cors_origins("https://example.com, https://app.example.com")
    assert _is_allowed_origin("https://example.com", allowlist)
    assert not _is_allowed_origin("https://evil.example.com", allowlist)


def test_auth_middleware_loads_keys_from_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VCL_API_KEYS", "k1, k2")

    auth = AuthMiddleware(enabled=True)
    assert auth.verify_api_key("k1")
    assert auth.verify_api_key("k2")
    assert auth.verify_api_key("nope") is None

    # When env keys are provided, we should not auto-create per-user key material.
    config_path = tmp_path / ".virtualchemlab" / "config.json"
    assert not config_path.exists()


def test_auth_middleware_generates_key_when_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("VCL_API_KEYS", raising=False)

    auth = AuthMiddleware(enabled=True)

    config_path = tmp_path / ".virtualchemlab" / "config.json"
    assert config_path.exists()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    generated = data["security"]["api_key"]

    assert isinstance(generated, str)
    assert generated
    assert auth.verify_api_key(generated)


def test_auth_middleware_disabled_has_no_side_effects(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("VCL_API_KEYS", raising=False)

    auth = AuthMiddleware(enabled=False)
    assert auth.verify_api_key("anything")["name"] == "Anonymous"

    config_path = tmp_path / ".virtualchemlab" / "config.json"
    assert not config_path.exists()


def test_auth_middleware_requires_explicit_keys_in_production(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("VCL_API_KEYS", raising=False)

    try:
        AuthMiddleware(enabled=True)
    except RuntimeError as exc:
        assert "VCL_API_KEYS" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected RuntimeError in production when keys are missing")

    config_path = tmp_path / ".virtualchemlab" / "config.json"
    assert not config_path.exists()
