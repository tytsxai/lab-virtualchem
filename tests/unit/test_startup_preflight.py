"""Tests for startup preflight checks."""

from __future__ import annotations

import pytest

from src.core.startup_preflight import ensure_secure_startup


def test_ensure_secure_startup_passes_with_valid_secrets(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    ensure_secure_startup()


def test_ensure_secure_startup_fails_on_short_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(SystemExit):
        ensure_secure_startup()
