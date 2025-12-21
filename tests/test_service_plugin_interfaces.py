from __future__ import annotations

from pathlib import Path

import pytest


def test_simple_plugin_executes_with_default_executor_and_params():
    from src.interfaces.plugin import PluginType, SimplePlugin

    plugin = SimplePlugin(name="p1", plugin_type=PluginType.CALCULATOR)
    assert plugin.is_available() is True
    assert plugin.initialize({"k": "v"}) is True
    assert plugin.is_available() is True
    assert plugin.execute("do") == {"action": "do", "params": {}}
    plugin.shutdown()
    assert plugin.is_available() is False


def test_simple_plugin_custom_executor_and_capabilities():
    from src.interfaces.plugin import PluginPriority, PluginType, SimplePlugin

    plugin = SimplePlugin(
        name="p2",
        plugin_type=PluginType.EXPORTER,
        version="2.0.0",
        priority=PluginPriority.HIGH,
        capabilities=["a", "b"],
        executor=lambda action, params=None: (action, params),
    )
    assert plugin.name == "p2"
    assert plugin.version == "2.0.0"
    assert plugin.plugin_type == PluginType.EXPORTER
    assert plugin.priority == PluginPriority.HIGH
    assert plugin.get_capabilities() == ["a", "b"]
    assert plugin.execute("x", {"y": 1}) == ("x", {"y": 1})


def test_in_memory_registry_registers_and_filters():
    from src.interfaces.plugin import InMemoryPluginRegistry, PluginType, SimplePlugin

    registry = InMemoryPluginRegistry()
    p_a = SimplePlugin(name="a", plugin_type=PluginType.RENDERER, capabilities=["cap"])
    p_b = SimplePlugin(name="b", plugin_type=PluginType.EXPORTER, capabilities=["x"])

    assert registry.register(p_a) is True
    assert registry.register(p_b) is True
    assert registry.get("a") is p_a
    assert registry.get("missing") is None
    assert registry.find_by_type(PluginType.RENDERER) == [p_a]
    assert registry.find_by_capability("cap") == [p_a]
    assert registry.find_by_capability("nope") == []
    assert registry.unregister("a") is True
    assert registry.unregister("a") is False


def test_in_memory_loader_loads_whitelisted_internal_plugin(tmp_path: Path):
    from src.interfaces.plugin import InMemoryPluginLoader

    loader = InMemoryPluginLoader()
    plugin = loader.load_plugin("src.plugins.internal_simple_plugin:InternalSimplePlugin")
    assert plugin is not None
    assert plugin.name == "internal_simple"
    assert loader.get_plugin("internal_simple") is plugin
    assert loader.unload_plugin("internal_simple") is True


def test_in_memory_loader_rejects_bad_plugin_paths():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError):
        loader.load_plugin("not_a_module_path")
    with pytest.raises(PluginLoadError):
        loader.load_plugin("os:path")
    with pytest.raises(PluginLoadError):
        loader.load_plugin("src.plugins.internal_simple_plugin:NotAllowed")


def test_in_memory_loader_rejects_invalid_module_name():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError):
        loader.load_plugin("src.plugins.:InternalSimplePlugin")
    with pytest.raises(PluginLoadError):
        loader.load_plugin("src.plugins.bad-name:InternalSimplePlugin")


def test_in_memory_loader_signature_verifier_can_block_loading():
    from src.interfaces.plugin import AllowAllSignatureVerifier, InMemoryPluginLoader, PluginLoadError

    class RejectAllVerifier(AllowAllSignatureVerifier):
        def verify(self, plugin_file: Path) -> bool:  # noqa: ARG002
            return False

    loader = InMemoryPluginLoader(signature_verifier=RejectAllVerifier())
    with pytest.raises(PluginLoadError):
        loader.load_plugin("src.plugins.internal_simple_plugin:InternalSimplePlugin")


def test_is_within_dir_behavior(tmp_path: Path):
    from src.interfaces.plugin import InMemoryPluginLoader

    base = tmp_path / "base"
    base.mkdir()
    inside = base / "a.py"
    inside.write_text("x=1", encoding="utf-8")

    outside = tmp_path / "outside.py"
    outside.write_text("x=1", encoding="utf-8")

    assert InMemoryPluginLoader._is_within_dir(inside, base) is True
    assert InMemoryPluginLoader._is_within_dir(outside, base) is False
