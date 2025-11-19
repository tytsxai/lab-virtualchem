from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

from src.utils import smart_lazy_loader
from src.utils.smart_lazy_loader import SmartLazyLoader, lazy_import


@pytest.fixture
def loader():
    return SmartLazyLoader(enable_background_loading=False)


def test_register_and_load_with_dependencies(loader):
    loader.register("math", priority=1)
    loader.register("json", dependencies=["math"])

    module = loader.load("json")
    assert module is importlib.import_module("json")

    loaded = set(loader.get_loaded_modules())
    assert {"math", "json"}.issubset(loaded)
    assert loader.get_unloaded_modules() == []

    stats = loader.get_stats()
    assert stats["total_registered"] == 2
    assert stats["total_loaded"] >= 2


def test_load_uses_cache_and_force_reimports(monkeypatch, loader):
    module_name = "fake_cached_module"
    call_count = {"count": 0}

    def fake_import(name):
        call_count["count"] += 1
        module = ModuleType(name)
        sys.modules[name] = module
        return module

    monkeypatch.setattr(smart_lazy_loader.importlib, "import_module", fake_import)
    loader.register(module_name)

    first = loader.load(module_name)
    second = loader.load(module_name)
    assert first is second
    assert call_count["count"] == 1

    reloaded = loader.load(module_name, force=True)
    assert reloaded is not first
    assert call_count["count"] == 2


def test_load_many_handles_missing_module(monkeypatch, loader):
    real_import = importlib.import_module

    def fake_import(name):
        if name == "missing_mod":
            raise ModuleNotFoundError("missing_mod")
        return real_import(name)

    monkeypatch.setattr(smart_lazy_loader.importlib, "import_module", fake_import)

    loader.register("math")
    loader.register("missing_mod")

    result = loader.load_many(["math", "missing_mod"])
    assert "math" in result
    assert "missing_mod" not in result

    stats = loader.get_stats()
    assert stats["load_errors"] == 1


def test_background_loading_respects_priority(monkeypatch):
    loader = SmartLazyLoader(enable_background_loading=True)
    loader.register("module_low", priority=1)
    loader.register("module_high", priority=10)

    load_order: list[str] = []

    def fake_load(name, force=False):
        load_order.append(name)
        module = ModuleType(name)
        loader._loaded_modules[name] = module
        return module

    monkeypatch.setattr(loader, "load", fake_load)
    monkeypatch.setattr(smart_lazy_loader.time, "sleep", lambda *_args, **_kwargs: None)

    loader.start_background_loading()
    loader._background_thread.join(timeout=1)
    loader.stop_background_loading()

    assert load_order[:2] == ["module_high", "module_low"]
    assert loader.get_stats()["background_loaded"] == 2


def test_lazy_import_reuses_global_loader(monkeypatch):
    calls: list[str] = []

    class StubLoader:
        def __init__(self):
            self.loaded: list[str] = []

        def load(self, module_name, *args, **kwargs):
            self.loaded.append(module_name)
            calls.append(module_name)
            return f"loaded:{module_name}"

    monkeypatch.setattr(smart_lazy_loader, "_lazy_loader", None)
    monkeypatch.setattr(smart_lazy_loader, "SmartLazyLoader", StubLoader)

    assert lazy_import("json") == "loaded:json"
    assert lazy_import("math") == "loaded:math"
    assert calls == ["json", "math"]
