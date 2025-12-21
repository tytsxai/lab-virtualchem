import pytest


def test_cdn_manager_get_url_caches_result():
    from src.backend.cdn_config import CDNConfig, CDNManager

    cfg = CDNConfig(provider="cloudflare", base_url="https://cdn.example.com")
    mgr = CDNManager(cfg)

    assert mgr.get_url("a.png") == "https://cdn.example.com/a.png"
    # second call hits internal cache
    assert mgr.get_url("a.png") == "https://cdn.example.com/a.png"


def test_cdn_manager_local_provider_uses_static_prefix():
    from src.backend.cdn_config import CDNConfig, CDNManager

    cfg = CDNConfig(provider="local", base_url="/static")
    mgr = CDNManager(cfg)
    assert mgr.get_url("x.css") == "/static/x.css"


def test_cdn_cache_control_uses_rules_and_fallback():
    from src.backend.cdn_config import CDNConfig, CDNManager

    cfg = CDNConfig(
        provider="cloudflare",
        base_url="https://cdn.example.com",
        cache_rules={"image": 10},
    )
    mgr = CDNManager(cfg)
    assert mgr.get_cache_control("png") == "public, max-age=10"
    assert mgr.get_cache_control("unknown") == "public, max-age=3600"


@pytest.mark.parametrize("provider", ["cloudflare", "aws", "aliyun"])
def test_cdn_purge_cache_supported_providers(provider):
    from src.backend.cdn_config import CDNConfig, CDNManager

    cfg = CDNConfig(provider=provider, base_url="https://cdn.example.com", api_key="k")
    mgr = CDNManager(cfg)
    assert mgr.purge_cache(paths=["/a.js"]) is True


def test_cdn_purge_cache_local_and_unknown_provider_and_exception(monkeypatch):
    from src.backend.cdn_config import CDNConfig, CDNManager

    local = CDNManager(CDNConfig(provider="local", base_url="/static"))
    assert local.purge_cache(paths=["/a.js"]) is True

    unknown = CDNManager(CDNConfig(provider="unknown", base_url="https://cdn.example.com"))
    assert unknown.purge_cache(paths=["/a.js"]) is False

    mgr = CDNManager(CDNConfig(provider="cloudflare", base_url="https://cdn.example.com"))
    monkeypatch.setattr(mgr, "_purge_cloudflare", lambda _paths: (_ for _ in ()).throw(RuntimeError("boom")))
    assert mgr.purge_cache(paths=["/a.js"]) is False


def test_static_resource_optimizer_rewrites_html():
    from src.backend.cdn_config import CDNConfig, CDNManager, StaticResourceOptimizer

    cfg = CDNConfig(provider="cloudflare", base_url="https://cdn.example.com")
    optimizer = StaticResourceOptimizer(CDNManager(cfg))

    html = '<img src="img/a.png"><link href="css/app.css"><script src="js/app.js"></script>'
    out = optimizer.optimize_html(html)
    assert 'src="https://cdn.example.com/img/a.png"' in out
    assert 'href="https://cdn.example.com/css/app.css"' in out
    assert 'src="https://cdn.example.com/js/app.js"' in out


def test_static_resource_optimizer_manifest_and_version_and_preload(tmp_path):
    from src.backend.cdn_config import (
        CDNConfig,
        CDNManager,
        ResourcePreloader,
        StaticResourceOptimizer,
        init_cdn,
        get_cdn_manager,
    )

    cfg = CDNConfig(provider="cloudflare", base_url="https://cdn.example.com")
    mgr = init_cdn(cfg)
    assert get_cdn_manager() is mgr

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "a.css").write_text("body{}", encoding="utf-8")
    (static_dir / "img").mkdir()
    (static_dir / "img" / "a.png").write_text("x", encoding="utf-8")

    optimizer = StaticResourceOptimizer(mgr)
    manifest = optimizer.generate_manifest(static_dir)
    assert manifest["a.css"] == "https://cdn.example.com/a.css"
    assert manifest["img/a.png"] == "https://cdn.example.com/img/a.png"

    assert optimizer.add_version_hash("https://cdn.example.com/a.css", "deadbeef") == (
        "https://cdn.example.com/a.css?v=deadbeef"
    )
    assert optimizer.add_version_hash(
        "https://cdn.example.com/a.css?x=1", "deadbeef"
    ) == "https://cdn.example.com/a.css?x=1&v=deadbeef"

    preload = ResourcePreloader.generate_preload_links(
        [
            {"url": "u1", "type": "font"},
            {"url": "u2", "type": "image"},
            {"url": "u3", "type": "script"},
            {"url": "u4", "type": "style"},
        ]
    )
    assert 'as="font"' in preload
    assert 'as="image"' in preload
    assert 'as="script"' in preload
    assert 'as="style"' in preload

    dns = ResourcePreloader.generate_dns_prefetch(["example.com", "cdn.example.com"])
    assert '<link rel="dns-prefetch" href="//example.com">' in dns
