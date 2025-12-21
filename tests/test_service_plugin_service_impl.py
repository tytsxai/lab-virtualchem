from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.plugin_service import (
    PluginExecuteRequest,
    PluginInstallRequest,
    PluginStatus,
    PluginType,
)
from src.interfaces.plugin import PluginPriority
from src.services.plugin_service_impl import PluginServiceImpl


@dataclass
class _FakePlugin:
    name: str = "p1"
    version: str = "1.0.0"
    plugin_type: PluginType = PluginType.CALCULATOR
    priority: PluginPriority = PluginPriority.NORMAL
    capabilities: list[str] = field(default_factory=lambda: ["cap"])
    available: bool = True
    initialized_with: list[dict[str, Any] | None] = field(default_factory=list)
    executed: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    shutdown_called: int = 0

    def is_available(self) -> bool:
        return self.available

    def initialize(self, config: dict[str, Any] | None = None) -> bool:
        self.available = True
        self.initialized_with.append(config)
        return True

    def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        self.executed.append((action, params))
        return {"action": action, "params": params}

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def shutdown(self) -> None:
        self.available = False
        self.shutdown_called += 1


class _Registry:
    def __init__(self) -> None:
        self._plugins: dict[str, _FakePlugin] = {}
        self.closed = False

    def register(self, plugin: _FakePlugin) -> bool:
        if plugin.name in self._plugins:
            return False
        self._plugins[plugin.name] = plugin
        return True

    def unregister(self, plugin_name: str) -> bool:
        return self._plugins.pop(plugin_name, None) is not None

    def get(self, plugin_name: str) -> _FakePlugin | None:
        return self._plugins.get(plugin_name)

    def find_by_type(self, plugin_type: PluginType) -> list[_FakePlugin]:
        return [p for p in self._plugins.values() if p.plugin_type == plugin_type]

    def find_by_capability(self, capability: str) -> list[_FakePlugin]:
        return [p for p in self._plugins.values() if capability in p.capabilities]

    def close(self) -> None:
        self.closed = True


class _Loader:
    def __init__(self, plugin: _FakePlugin | None = None) -> None:
        self._plugin = plugin
        self.unloaded: list[str] = []
        self.reloaded: list[str] = []
        self.closed = False

    def load_plugin(self, plugin_path: str) -> _FakePlugin | None:
        return self._plugin

    def unload_plugin(self, plugin_name: str) -> bool:
        self.unloaded.append(plugin_name)
        return True

    def reload_plugin(self, plugin_name: str) -> bool:
        self.reloaded.append(plugin_name)
        return True

    def get_plugin(self, plugin_name: str) -> _FakePlugin | None:
        if self._plugin and self._plugin.name == plugin_name:
            return self._plugin
        return None

    def close(self) -> None:
        self.closed = True


def test_plugin_service_execute_and_info_and_list_and_capability_filters():
    plugin = _FakePlugin(name="p1", plugin_type=PluginType.CALCULATOR, available=True)
    registry = _Registry()
    registry.register(plugin)
    service = PluginServiceImpl(loader=_Loader(plugin), registry=registry)

    ok = service.execute_plugin(PluginExecuteRequest(plugin_name="p1", action="run"))
    assert ok.success is True
    assert ok.result["action"] == "run"

    info = service.get_plugin_info("p1")
    assert info is not None
    assert info.name == "p1"
    assert info.priority == PluginPriority.NORMAL

    listed = service.list_plugins(plugin_type=PluginType.CALCULATOR)
    assert [p.name for p in listed] == ["p1"]

    enabled = service.list_plugins(status=PluginStatus.ENABLED)
    assert [p.name for p in enabled] == ["p1"]

    matches = service.find_plugins_by_capability("cap")
    assert [p.name for p in matches] == ["p1"]


def test_plugin_service_execute_handles_missing_and_unavailable_and_exceptions():
    registry = _Registry()
    service = PluginServiceImpl(loader=_Loader(None), registry=registry)

    missing = service.execute_plugin(PluginExecuteRequest(plugin_name="nope", action="x"))
    assert missing.success is False

    plugin = _FakePlugin(name="p1", available=False)
    registry.register(plugin)
    unavailable = service.execute_plugin(PluginExecuteRequest(plugin_name="p1", action="x"))
    assert unavailable.success is False

    class _BoomPlugin(_FakePlugin):
        def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:  # noqa: ARG002
            raise RuntimeError("boom")

    registry.unregister("p1")
    registry.register(_BoomPlugin(name="p2"))
    boom = service.execute_plugin(PluginExecuteRequest(plugin_name="p2", action="x"))
    assert boom.success is False
    assert "执行插件失败" in (boom.error or boom.message)


def test_plugin_service_install_uninstall_enable_disable_reload_and_close():
    plugin = _FakePlugin(name="p1")
    loader = _Loader(plugin)
    registry = _Registry()
    service = PluginServiceImpl(loader=loader, registry=registry)

    installed = service.install_plugin(PluginInstallRequest(plugin_path="any"))
    assert installed.success is True
    assert installed.plugin_name == "p1"

    assert service.enable_plugin("p1") is True
    assert service.disable_plugin("p1") is True

    assert service.reload_plugin("p1") is True
    assert loader.reloaded == ["p1"]

    assert service.uninstall_plugin("p1") is True
    assert "p1" in loader.unloaded

    service.close()
    assert registry.closed is True
    assert loader.closed is True


def test_plugin_service_install_failure_paths_and_reload_failures():
    plugin = _FakePlugin(name="p1")

    class _NoPluginLoader(_Loader):
        def load_plugin(self, plugin_path: str) -> _FakePlugin | None:  # noqa: ARG002
            return None

    service = PluginServiceImpl(loader=_NoPluginLoader(plugin), registry=_Registry())
    installed = service.install_plugin(PluginInstallRequest(plugin_path="missing"))
    assert installed.success is False

    class _RejectRegistry(_Registry):
        def register(self, plugin: _FakePlugin) -> bool:  # noqa: ARG002
            return False

    service2 = PluginServiceImpl(loader=_Loader(plugin), registry=_RejectRegistry())
    installed2 = service2.install_plugin(PluginInstallRequest(plugin_path="any"))
    assert installed2.success is False

    class _InitFailPlugin(_FakePlugin):
        def initialize(self, config: dict[str, Any] | None = None) -> bool:  # noqa: ARG002
            return False

    service3 = PluginServiceImpl(loader=_Loader(_InitFailPlugin(name="p2")), registry=_Registry())
    installed3 = service3.install_plugin(PluginInstallRequest(plugin_path="any"))
    assert installed3.success is False

    class _ReloadFailLoader(_Loader):
        def reload_plugin(self, plugin_name: str) -> bool:  # noqa: ARG002
            return False

    registry = _Registry()
    registry.register(plugin)
    service4 = PluginServiceImpl(loader=_ReloadFailLoader(plugin), registry=registry)
    assert service4.reload_plugin("p1") is False

    class _ReloadOkButNoPlugin(_Loader):
        def get_plugin(self, plugin_name: str) -> _FakePlugin | None:  # noqa: ARG002
            return None

    service5 = PluginServiceImpl(loader=_ReloadOkButNoPlugin(plugin), registry=registry)
    assert service5.reload_plugin("p1") is False


def test_plugin_service_misc_branches_uninstall_enable_disable_and_close_idempotent():
    plugin = _FakePlugin(name="p1")
    registry = _Registry()
    loader = _Loader(plugin)
    service = PluginServiceImpl(loader=loader, registry=registry)

    assert service.get_plugin_info("missing") is None
    assert service.enable_plugin("missing") is False
    assert service.disable_plugin("missing") is False

    class _RegistryBoom(_Registry):
        def find_by_capability(self, capability: str) -> list[_FakePlugin]:  # noqa: ARG002
            raise RuntimeError("boom")

    service2 = PluginServiceImpl(loader=loader, registry=_RegistryBoom())
    assert service2.find_plugins_by_capability("cap") == []

    class _LoaderBoom(_Loader):
        def unload_plugin(self, plugin_name: str) -> bool:  # noqa: ARG002
            raise RuntimeError("boom")

    registry.register(plugin)
    service3 = PluginServiceImpl(loader=_LoaderBoom(plugin), registry=registry)
    assert service3.uninstall_plugin("p1") is False

    service3.close()
    service3.close()


def test_plugin_service_context_manager_calls_close():
    plugin = _FakePlugin(name="p1")
    registry = _Registry()
    registry.register(plugin)
    loader = _Loader(plugin)
    with PluginServiceImpl(loader=loader, registry=registry) as service:
        assert service.list_plugins()
    assert registry.closed is True
    assert loader.closed is True
