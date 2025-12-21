"""
插件加载器安全性测试（RCE 防护）
"""

import pytest


def test_simple_plugin_behaviour():
    from src.interfaces.plugin import PluginPriority, PluginType, SimplePlugin

    plugin = SimplePlugin(
        name="p1",
        plugin_type=PluginType.INTEGRATION,
        version="0.1",
        priority=PluginPriority.LOW,
        capabilities=["a", "b"],
        executor=lambda action, params=None: {"ok": True, "action": action, "params": params},
    )

    assert plugin.name == "p1"
    assert plugin.version == "0.1"
    assert plugin.plugin_type == PluginType.INTEGRATION
    assert plugin.priority == PluginPriority.LOW
    assert plugin.get_capabilities() == ["a", "b"]

    assert plugin.initialize({"x": 1}) is True
    assert plugin.is_available() is True
    assert plugin.execute("do", {"k": "v"})["ok"] is True

    plugin.shutdown()
    assert plugin.is_available() is False


def test_registry_find_by_capability():
    from src.interfaces.plugin import InMemoryPluginRegistry, SimplePlugin

    registry = InMemoryPluginRegistry()
    p1 = SimplePlugin(name="p1", capabilities=["cap1", "cap2"])
    p2 = SimplePlugin(name="p2", capabilities=["cap2"])
    registry.register(p1)
    registry.register(p2)

    found = registry.find_by_capability("cap1")
    assert [p.name for p in found] == ["p1"]


def test_loader_allows_only_registered_plugins():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginType

    loader = InMemoryPluginLoader()
    plugin = loader.load_plugin(
        "src.plugins.internal_simple_plugin:InternalSimplePlugin"
    )
    assert plugin is not None
    assert plugin.name == "internal_simple"
    assert loader.get_plugin("internal_simple") is plugin
    assert any(p.name == "internal_simple" for p in loader.list_plugins())
    assert any(
        p.name == "internal_simple"
        for p in loader.list_plugins(plugin_type=PluginType.INTEGRATION)
    )

    assert loader.unload_plugin("internal_simple") is True
    assert loader.get_plugin("internal_simple") is None


def test_loader_signature_verification_can_block():
    from pathlib import Path

    from src.interfaces.plugin import (
        IPluginSignatureVerifier,
        InMemoryPluginLoader,
        PluginLoadError,
    )

    class RejectAll(IPluginSignatureVerifier):
        def verify(self, plugin_file: Path) -> bool:  # noqa: ARG002
            return False

    loader = InMemoryPluginLoader(signature_verifier=RejectAll())
    with pytest.raises(PluginLoadError, match="签名"):
        loader.load_plugin("src.plugins.internal_simple_plugin:InternalSimplePlugin")


def test_loader_accepts_dot_syntax():
    from src.interfaces.plugin import InMemoryPluginLoader

    loader = InMemoryPluginLoader()
    plugin = loader.load_plugin(
        "src.plugins.internal_simple_plugin.InternalSimplePlugin"
    )
    assert plugin is not None


def test_loader_rejects_invalid_format():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError):
        loader.load_plugin("badformat")


def test_loader_reload_unregisters():
    from src.interfaces.plugin import InMemoryPluginLoader

    loader = InMemoryPluginLoader()
    loader.load_plugin("src.plugins.internal_simple_plugin:InternalSimplePlugin")
    assert loader.reload_plugin("internal_simple") is False
    assert loader.get_plugin("internal_simple") is None


def test_loader_rejects_empty_module_or_attr():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError):
        loader.load_plugin(":")


@pytest.mark.parametrize(
    "plugin_path",
    [
        "os:system",  # 任意标准库导入（RCE）
        "subprocess:Popen",  # 任意模块导入（RCE）
        "src.interfaces.plugin:SimplePlugin",  # 非 src/plugins 目录
        "src.plugins.internal_simple_plugin:DoesNotExist",  # 属性不存在
        "src.plugins.not_registered:Whatever",  # 未注册模块
    ],
)
def test_loader_blocks_rce_and_unregistered_modules(plugin_path: str):
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError):
        loader.load_plugin(plugin_path)


def test_loader_blocks_non_whitelist_prefix():
    from src.interfaces.plugin import InMemoryPluginLoader, PluginLoadError

    loader = InMemoryPluginLoader()
    with pytest.raises(PluginLoadError, match="白名单前缀"):
        loader.load_plugin("src.pluginsX.internal_simple_plugin:InternalSimplePlugin")
