from src.core.config_loader import Config


def test_detect_environment_defaults_to_development_when_unset(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert Config._detect_environment(env=None) == "development"


def test_language_codes_normalized():
    config_data = {
        "app": {"language": "zh-CN"},
        "ui": {"language": "zh-CN"},
    }

    normalized = Config._normalize_language_codes(config_data)
    assert normalized["app"]["language"] == "zh_CN"
    assert normalized["ui"]["language"] == "zh_CN"

