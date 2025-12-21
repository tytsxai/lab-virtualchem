import json

import pytest


def test_cdn_from_file_rejects_invalid_provider(tmp_path):
    from src.backend.cdn_config import CDNConfigBuilder

    p = tmp_path / "cdn.json"
    p.write_text(json.dumps({"provider": "unknown", "base_url": "https://cdn.example.com"}))

    with pytest.raises(ValueError, match="provider"):
        CDNConfigBuilder.from_file(str(p))


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://cdn.example.com",
        "https://",
        "https://localhost/static",
        "https://intranet.local/static",
        "https://127.0.0.1/static",
        "http://10.0.0.1/static",
        "http://192.168.1.10/static",
        "http://172.16.0.5/static",
        "https://user:pass@cdn.example.com/static",
        "https://cdn.example.com/static?x=1",
        "https://cdn.example.com/static#frag",
        "/static with space",
    ],
)
def test_cdn_from_file_rejects_internal_or_invalid_base_url(tmp_path, base_url):
    from src.backend.cdn_config import CDNConfigBuilder

    p = tmp_path / "cdn.json"
    p.write_text(json.dumps({"provider": "cloudflare", "base_url": base_url}))

    with pytest.raises(ValueError, match="base_url"):
        CDNConfigBuilder.from_file(str(p))


def test_cdn_from_file_accepts_https_external_url(tmp_path):
    from src.backend.cdn_config import CDNConfigBuilder

    p = tmp_path / "cdn.json"
    p.write_text(json.dumps({"provider": "cloudflare", "base_url": "https://cdn.example.com"}))

    cfg = CDNConfigBuilder.from_file(str(p))
    assert cfg.provider == "cloudflare"
    assert cfg.base_url == "https://cdn.example.com"


def test_cdn_from_file_accepts_local_relative_base_url(tmp_path):
    from src.backend.cdn_config import CDNConfigBuilder

    p = tmp_path / "cdn.json"
    p.write_text(json.dumps({"provider": "local", "base_url": "/static"}))

    cfg = CDNConfigBuilder.from_file(str(p))
    assert cfg.provider == "local"
    assert cfg.base_url == "/static"


def test_cdn_builder_helpers_and_validation_helpers():
    import src.backend.cdn_config as mod

    with pytest.raises(ValueError, match="base_url"):
        mod._validate_base_url("")

    cfg = mod.CDNConfigBuilder.create_local_config()
    assert cfg.provider == "local"

    cfg2 = mod.CDNConfigBuilder.create_cloudflare_config(
        zone_id="z", api_key="k", base_url="https://cdn.example.com"
    )
    assert cfg2.provider == "cloudflare"
