"""DeveloperAuth 行为测试"""

import json

from src.core.dev_auth import DeveloperAuth


def _write_config(tmp_path, enabled=True):
    config = {
        "app": {"environment": "development"},
        "developer": {"enabled": enabled, "session_timeout_hours": 1},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


def test_authenticate_requires_configured_key(tmp_path, monkeypatch):
    """未配置密钥时应拒绝启用开发者模式"""
    config_path = _write_config(tmp_path, enabled=True)
    monkeypatch.delenv("DEVELOPER_KEY_HASH", raising=False)

    auth = DeveloperAuth(str(config_path))

    assert auth.authenticate("any-secret") is False


def test_authenticate_with_env_hash(tmp_path, monkeypatch):
    """通过环境变量提供密钥哈希时应认证成功"""
    config_path = _write_config(tmp_path, enabled=True)
    plaintext = "my-secure-dev-key"
    key_hash = DeveloperAuth._hash_key(plaintext)
    monkeypatch.setenv("DEVELOPER_KEY_HASH", key_hash)

    auth = DeveloperAuth(str(config_path))

    assert auth.authenticate(plaintext) is True
