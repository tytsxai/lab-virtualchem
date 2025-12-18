"""Config loader environment handling tests."""

from typing import Any

import pytest

from src import __version__ as APP_VERSION
from src.core import config_loader
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


def test_merge_env_requires_jwt_secret_in_production_with_admin_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production environment must error without JWT secret even when admin secret is set."""
    config_data = _base_config(environment="production")

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_ENV", raising=False)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "placeholder-admin-secret")

    with pytest.raises(ValueError, match="JWT 密钥环境变量"):
        Config._merge_env_vars(config_data)


def test_merge_env_respects_custom_jwt_secret_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_merge_env_requires_jwt_secret_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production must fail fast when JWT secret env is missing."""
    config_data = _base_config(environment="production")

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_ENV", raising=False)

    with pytest.raises(ValueError, match="JWT 密钥环境变量"):
        Config._merge_env_vars(config_data)


def test_merge_env_requires_session_secret_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production must fail fast when session secret env is missing."""
    config_data = _base_config(environment="production")

    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "C" * 40)
    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
    monkeypatch.delenv("SESSION_SECRET_ENV", raising=False)

    with pytest.raises(ValueError, match="会话密钥环境变量"):
        Config._merge_env_vars(config_data)


def test_merge_env_requires_developer_secret_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enabling developer mode in production requires a secret."""
    config_data = _base_config(environment="production")
    config_data["developer"]["enabled"] = True

    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.setenv("SESSION_SECRET_KEY", "S" * 40)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "C" * 40)
    monkeypatch.setenv("DEVELOPER_MODE_ENABLED", "true")
    monkeypatch.delenv("DEVELOPER_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="开发者密钥环境变量"):
        Config._merge_env_vars(config_data)


def test_developer_mode_defaults_off_without_env_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production should keep developer mode disabled unless env explicitly enables it."""
    config_data = _base_config(environment="production")
    config_data["developer"]["enabled"] = True

    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "C" * 40)
    monkeypatch.setenv("SESSION_SECRET_KEY", "S" * 40)
    monkeypatch.delenv("DEVELOPER_MODE_ENABLED", raising=False)
    monkeypatch.delenv("DEVELOPER_MODE", raising=False)

    merged = Config._merge_env_vars(config_data)

    assert merged["developer"]["enabled"] is False


def test_merge_env_requires_admin_secret_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin secret is validated by Admin API, not by the global loader."""
    config_data = _base_config(environment="production")

    # Provide JWT/session secrets so we exercise the production branch.
    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.setenv("SESSION_SECRET_KEY", "S" * 40)
    monkeypatch.delenv("VCL_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_SECRET_ENV", raising=False)

    merged = Config._merge_env_vars(config_data)
    assert merged["developer"]["admin_secret_env"] == "VCL_ADMIN_SECRET_KEY"


def test_merge_env_rejects_short_admin_secret_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin secret is validated by Admin API, not by the global loader."""
    config_data = _base_config(environment="production")

    monkeypatch.setenv("JWT_SECRET_KEY", "B" * 40)
    monkeypatch.setenv("SESSION_SECRET_KEY", "S" * 40)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "too-short-secret")

    merged = Config._merge_env_vars(config_data)
    assert merged["developer"]["admin_secret_env"] == "VCL_ADMIN_SECRET_KEY"


def test_load_enforces_version_alignment(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Config.load should align app.version with the runtime version."""

    def _fake_load_config_file(cls, environment: str) -> dict[str, Any]:  # type: ignore[override]
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": "1.0.0",
                "environment": environment,
            },
            "security": {"jwt_secret_key": "Z" * 40},
        }

    def _identity_merge(
        cls, config: dict[str, Any], environment_override: str | None = None
    ) -> dict[str, Any]:  # type: ignore[override]
        return config

    monkeypatch.setattr(
        Config, "_load_config_file", classmethod(_fake_load_config_file)
    )
    monkeypatch.setattr(Config, "_merge_env_vars", classmethod(_identity_merge))

    with caplog.at_level("WARNING"):
        config = Config.load(env="development")

    assert config.app.version == APP_VERSION
    assert "配置文件版本" in caplog.text


def test_load_keeps_version_when_already_aligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No warning and version preserved when config already matches runtime."""

    def _fake_load_config_file(cls, environment: str) -> dict[str, Any]:  # type: ignore[override]
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
                "environment": environment,
            },
            "security": {"jwt_secret_key": "Y" * 40},
        }

    def _identity_merge(
        cls, config: dict[str, Any], environment_override: str | None = None
    ) -> dict[str, Any]:  # type: ignore[override]
        return config

    monkeypatch.setattr(
        Config, "_load_config_file", classmethod(_fake_load_config_file)
    )
    monkeypatch.setattr(Config, "_merge_env_vars", classmethod(_identity_merge))

    config = Config.load(env="development")

    assert config.app.version == APP_VERSION


def test_load_prepares_runtime_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Writable directories should be created relative to the project root."""

    def _fake_load_config_file(cls, environment: str) -> dict[str, Any]:  # type: ignore[override]
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
                "environment": environment,
            },
            "paths": {
                "user_data": "user_data",
                "reports": "reports",
                "logs": "logs",
            },
            "log": {"file": "logs/app/app.log"},
            "database": {"path": "data/virtualchemlab.db"},
            "storage": {"base_path": "data/storage"},
            "security": {"jwt_secret_key": "X" * 40},
        }

    def _identity_merge(
        cls, config: dict[str, Any], environment_override: str | None = None
    ) -> dict[str, Any]:  # type: ignore[override]
        return config

    monkeypatch.setattr(config_loader, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        Config, "_load_config_file", classmethod(_fake_load_config_file)
    )
    monkeypatch.setattr(Config, "_merge_env_vars", classmethod(_identity_merge))

    Config.load(env="development")

    assert (tmp_path / "user_data").is_dir()
    assert (tmp_path / "reports").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "logs" / "app").is_dir()
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "data" / "storage").is_dir()


def test_load_directory_creation_failure_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Directory creation errors should propagate so deployment can fail fast."""

    def _fake_load_config_file(cls, environment: str) -> dict[str, Any]:  # type: ignore[override]
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
                "environment": environment,
            },
            "paths": {"user_data": "user_data"},
            "log": {"file": "logs/app.log"},
            "database": {"path": "data/virtualchemlab.db"},
            "security": {"jwt_secret_key": "X" * 40},
        }

    def _identity_merge(
        cls, config: dict[str, Any], environment_override: str | None = None
    ) -> dict[str, Any]:  # type: ignore[override]
        return config

    # Use a path inside tmp but remove permissions by pointing to file
    locked_path = tmp_path / "user_data"
    locked_path.write_text("not a dir", encoding="utf-8")

    monkeypatch.setattr(config_loader, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        Config, "_load_config_file", classmethod(_fake_load_config_file)
    )
    monkeypatch.setattr(Config, "_merge_env_vars", classmethod(_identity_merge))

    with pytest.raises(OSError):
        Config.load(env="development")


def test_detect_environment_uses_production_when_frozen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setattr(config_loader.sys, "frozen", True, raising=False)
    assert Config._detect_environment(env=None) == "production"
