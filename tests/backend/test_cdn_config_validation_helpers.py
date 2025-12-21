import json

import pytest


def _ensure_cov_target_module_name_loaded() -> None:
    """
    pytest-cov treats '--cov=src/backend/cdn_config' as a module name.
    Ensure that exact name exists in sys.modules so coverage is reported
    for src/backend/cdn_config.py under the requested target.
    """
    import importlib.util
    import sys
    from pathlib import Path

    name = "src/backend/cdn_config"
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "backend" / "cdn_config.py"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

def test_internal_hostname_detection():
    import src.backend.cdn_config as mod

    assert mod._is_internal_hostname("") is True
    assert mod._is_internal_hostname("   ") is True
    assert mod._is_internal_hostname("localhost") is True
    assert mod._is_internal_hostname("LOCALHOST.LOCALDOMAIN") is True
    assert mod._is_internal_hostname("svc.internal") is True
    assert mod._is_internal_hostname("dev.local") is True
    assert mod._is_internal_hostname("cdn.example.com") is False


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.1",  # private
        "192.168.1.1",  # private
        "172.16.0.1",  # private
        "169.254.1.1",  # link-local
        "0.0.0.0",  # unspecified
        "224.0.0.1",  # multicast
        "255.255.255.255",  # reserved/broadcast
        "::1",  # IPv6 loopback
        "fe80::1",  # IPv6 link-local
    ],
)
def test_internal_ip_detection(ip):
    import src.backend.cdn_config as mod

    assert mod._is_internal_ip(ip) is True


def test_internal_ip_detection_non_ip_and_public_ip():
    import src.backend.cdn_config as mod

    assert mod._is_internal_ip("not-an-ip") is False
    assert mod._is_internal_ip("8.8.8.8") is False


def test_validate_provider_strips_and_lowercases():
    import src.backend.cdn_config as mod

    mod._validate_provider(" CloudFlare ")
    with pytest.raises(ValueError, match="provider"):
        mod._validate_provider("not-supported")


def test_validate_base_url_rejects_empty_and_whitespace_relative():
    import src.backend.cdn_config as mod

    with pytest.raises(ValueError, match="base_url"):
        mod._validate_base_url("")

    with pytest.raises(ValueError, match="base_url"):
        mod._validate_base_url("/static\tbad")


def test_from_file_error_handling_missing_and_invalid_json(tmp_path):
    from src.backend.cdn_config import CDNConfigBuilder

    with pytest.raises(FileNotFoundError):
        CDNConfigBuilder.from_file(str(tmp_path / "missing.json"))

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        CDNConfigBuilder.from_file(str(bad))


def test_from_file_strips_provider_and_base_url(tmp_path):
    from src.backend.cdn_config import CDNConfigBuilder

    p = tmp_path / "cdn.json"
    p.write_text(
        json.dumps({"provider": " CloudFlare ", "base_url": " https://cdn.example.com "}),
        encoding="utf-8",
    )

    cfg = CDNConfigBuilder.from_file(str(p))
    assert cfg.provider == "cloudflare"
    assert cfg.base_url == "https://cdn.example.com"


def test_cdn_config_default_cache_rules_and_file_type_mapping():
    from src.backend.cdn_config import CDNConfig, CDNManager

    cfg = CDNConfig(provider="cloudflare", base_url="https://cdn.example.com")
    assert cfg.cache_rules is not None
    assert cfg.cache_rules["image"] > 0
    assert cfg.cache_rules["css"] > 0

    mgr = CDNManager(cfg)
    assert mgr._get_file_type(".woff2") == "font"
    assert mgr._get_file_type("GI") == "image"
    assert mgr._get_file_type("unknownext") == "other"
