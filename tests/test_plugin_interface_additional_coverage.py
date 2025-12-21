from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_loader_raises_when_attribute_missing_but_whitelisted(monkeypatch: pytest.MonkeyPatch):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    monkeypatch.setitem(
        loader.ALLOWED_PLUGINS,
        "src.plugins.internal_simple_plugin",
        {"InternalSimplePlugin", "MissingAttr"},
    )

    with pytest.raises(PluginLoadError, match="无法在模块中找到 MissingAttr"):
        loader.load_plugin("src.plugins.internal_simple_plugin:MissingAttr")


def test_loader_raises_when_loaded_object_is_not_iplugin(monkeypatch: pytest.MonkeyPatch):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()

    class DummyModule:
        NotAPlugin = object()

    monkeypatch.setattr(loader, "_validate_plugin_path", lambda **_kwargs: None)
    monkeypatch.setattr(loader, "_resolve_plugin_module_file", lambda _module_name: Path(__file__))
    monkeypatch.setattr(loader, "_load_module_from_file", lambda _module_name, _module_file: DummyModule)

    with pytest.raises(PluginLoadError, match="不是 IPlugin"):
        loader.load_plugin("src.plugins.anything:NotAPlugin")


def test_reload_plugin_returns_false_when_missing():
    from src.interfaces.plugin import InMemoryPluginLoader

    loader = InMemoryPluginLoader()
    assert loader.reload_plugin("does_not_exist") is False


def test_resolve_plugin_module_file_rejects_empty_relative():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError, match="模块名无效"):
        loader._resolve_plugin_module_file("src.plugins.")


def test_resolve_plugin_module_file_rejects_non_identifier_parts():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError, match="模块名无效"):
        loader._resolve_plugin_module_file("src.plugins.bad-name")


def test_resolve_plugin_module_file_raises_when_file_missing(tmp_path: Path):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    loader.PLUGIN_ROOT_DIR = tmp_path.resolve()

    with pytest.raises(PluginLoadError, match="文件不存在"):
        loader._resolve_plugin_module_file("src.plugins.missing_plugin")


def test_resolve_plugin_module_file_blocks_loading_outside_plugin_root(tmp_path: Path):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text("x = 1\n", encoding="utf-8")

    link = plugin_root / "evil.py"
    os.symlink(outside, link)

    loader = InMemoryPluginLoader()
    loader.PLUGIN_ROOT_DIR = plugin_root.resolve()

    with pytest.raises(PluginLoadError, match="目录外"):
        loader._resolve_plugin_module_file("src.plugins.evil")


def test_load_module_from_file_raises_when_spec_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    module_file = tmp_path / "a.py"
    module_file.write_text("x = 1\n", encoding="utf-8")

    loader = InMemoryPluginLoader()

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(PluginLoadError, match="无法创建插件模块加载器"):
        loader._load_module_from_file("src.plugins.any", module_file)

