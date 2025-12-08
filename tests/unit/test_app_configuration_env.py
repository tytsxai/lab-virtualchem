"""AppConfiguration environment handling tests."""

import pytest

from config.schemas.app_config import AppConfiguration, AppConfig, DeveloperConfig


def test_production_requires_env_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """生产环境缺少密钥时应立即失败。"""
    for key in ("JWT_SECRET_KEY", "SESSION_SECRET_KEY", "DEVELOPER_SECRET_KEY", "DEVELOPER_MODE_ENABLED"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="缺少必需的密钥"):
        AppConfiguration(app=AppConfig(environment="production"))


def test_developer_mode_forced_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """生产环境默认关闭开发者模式，并强制关闭debug。"""
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 48)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 48)
    monkeypatch.delenv("DEVELOPER_MODE_ENABLED", raising=False)
    monkeypatch.delenv("DEVELOPER_SECRET_KEY", raising=False)

    config = AppConfiguration(
        app=AppConfig(environment="production"),
        developer=DeveloperConfig(enabled=True, debug_mode=True),
    )

    assert config.developer.enabled is False
    assert config.developer.debug_mode is False
    assert config.app.debug is False


def test_production_dev_mode_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """启用生产开发者模式时必须提供开发者密钥。"""
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 48)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 48)
    monkeypatch.setenv("DEVELOPER_MODE_ENABLED", "true")
    monkeypatch.delenv("DEVELOPER_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="DEVELOPER_SECRET_KEY"):
        AppConfiguration(app=AppConfig(environment="production"))
