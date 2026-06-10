from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_health_check_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("scripts_health_check", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


health_check_script = _load_health_check_module()


def test_check_imports_imports_required_modules(monkeypatch):
    imported: list[str] = []

    def fake_import_module(name: str):
        imported.append(name)
        return object()

    monkeypatch.setattr(
        health_check_script.importlib, "import_module", fake_import_module
    )

    assert health_check_script.check_imports() is True
    assert "src.core.service_registration" in imported
    assert "src.utils.logger" in imported


def test_check_imports_fails_when_required_module_is_missing(monkeypatch):
    def fake_import_module(name: str):
        if name == "src.core.service_registration":
            raise ModuleNotFoundError("No module named 'jwt'")
        return object()

    monkeypatch.setattr(
        health_check_script.importlib, "import_module", fake_import_module
    )

    assert health_check_script.check_imports() is False
