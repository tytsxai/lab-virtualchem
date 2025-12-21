from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_readiness_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "scripts" / "readiness_check.py"
    spec = importlib.util.spec_from_file_location("readiness_check", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


readiness_check = _load_readiness_module()


def _make_config(*, env: str, log_file: str):
    return SimpleNamespace(
        app=SimpleNamespace(environment=env),
        monitoring=SimpleNamespace(enabled=True, health_check_interval=30),
        log=SimpleNamespace(file=log_file),
        paths=SimpleNamespace(
            templates="assets/templates",
            knowledge="assets/knowledge",
            i18n="assets/i18n",
            logs="logs",
            reports="reports",
            user_data="user_data",
        ),
        security=SimpleNamespace(jwt_secret_key="x" * 32),
    )


def test_environment_alignment_detected_env_mismatch(monkeypatch, tmp_path):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setattr(readiness_check.sys, "frozen", False, raising=False)
    config = _make_config(env="production", log_file=str(tmp_path / "logs" / "app.log"))
    result = readiness_check.check_environment_alignment(config)
    assert result.passed is False


def test_environment_alignment_env_var_mismatch(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    config = _make_config(env="development", log_file=str(tmp_path / "logs" / "app.log"))
    result = readiness_check.check_environment_alignment(config)
    assert result.passed is False


def test_check_monitoring_log_dir_writable(monkeypatch, tmp_path):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    config = _make_config(env="development", log_file=str(tmp_path / "logs" / "app.log"))
    results = readiness_check.check_monitoring(config)
    assert results[-1].passed is True
