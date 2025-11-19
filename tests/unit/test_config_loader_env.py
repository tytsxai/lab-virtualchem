"""Config loader environment handling tests."""

import os

import pytest

from src.core.config_loader import Config


def _base_config(environment: str = "development") -> dict[str, dict]:
    """Helper to build minimal config structure for merging."""
    return {
        "app": {"environment": environment, "debug": False},
        "security": {},
        "developer": {},
        "database": {},
        "redis": {},
        "cache": {},
        "monitoring": {},
        "log": {},
        "paths": {},
    }


def test_merge_env_respects_custom_jwt_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When security.jwt_secret_env is provided, loader should honor it."""
    config_data = _base_config()
    config_data["security"]["jwt_secret_env"] = "CUSTOM_JWT_SECRET"

    monkeypatch.setenv("CUSTOM_JWT_SECRET", "A" * 40)
    # Ensure fallback envs don't interfere
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_ENV", raising=False)

    merged = Config._merge_env_vars(config_data)

    assert merged["security"]["jwt_secret_env"] == "CUSTOM_JWT_SECRET"
    assert merged["security"]["jwt_secret_key"] == "A" * 40


def test_merge_env_requires_admin_secret_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production environment should fail fast without admin secret."""
    config_data = _base_config(environment="production")

    # Provide JWT secret so the failure is specific to admin secret.
    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.delenv("VCL_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_SECRET_ENV", raising=False)

    with pytest.raises(ValueError, match="管理后台密钥环境变量"):
        Config._merge_env_vars(config_data)
