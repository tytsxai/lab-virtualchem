from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.monitoring.health_monitor import HealthMonitor, HealthStatus, get_health_monitor


def test_check_storage_creates_data_dir_and_reports_healthy(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    import src.monitoring.health_monitor as hm

    def fake_disk_usage(_path: str):
        # 10GB free of 100GB
        return SimpleNamespace(free=10 * 1024**3, total=100 * 1024**3)

    monkeypatch.setattr(hm.psutil, "disk_usage", fake_disk_usage)

    monitor = HealthMonitor()
    status = monitor.check_storage()
    assert status.status == "healthy"
    assert (tmp_path / "data").exists()


@pytest.mark.parametrize(
    ("free_gb", "expected"),
    [
        (0.5, "unhealthy"),
        (2.0, "degraded"),
        (10.0, "healthy"),
    ],
)
def test_check_storage_thresholds(tmp_path, monkeypatch, free_gb: float, expected: str) -> None:
    monkeypatch.chdir(tmp_path)
    import src.monitoring.health_monitor as hm

    def fake_disk_usage(_path: str):
        return SimpleNamespace(free=free_gb * 1024**3, total=100 * 1024**3)

    monkeypatch.setattr(hm.psutil, "disk_usage", fake_disk_usage)
    status = HealthMonitor().check_storage()
    assert status.status == expected
    assert "free_gb" in status.details


def test_check_memory_thresholds(monkeypatch) -> None:
    import src.monitoring.health_monitor as hm

    monkeypatch.setattr(
        hm.psutil, "virtual_memory", lambda: SimpleNamespace(percent=12.3)
    )

    class FakeProcess:
        def __init__(self, rss_bytes: int):
            self._rss = rss_bytes

        def memory_info(self):
            return SimpleNamespace(rss=self._rss)

    # limit=100MB
    monitor = HealthMonitor(config={"performance": {"memory": {"max_usage_mb": 100}}})
    monkeypatch.setattr(hm.psutil, "Process", lambda: FakeProcess(200 * 1024**2))
    assert monitor.check_memory().status == "unhealthy"

    monkeypatch.setattr(hm.psutil, "Process", lambda: FakeProcess(120 * 1024**2))
    assert monitor.check_memory().status == "degraded"

    monkeypatch.setattr(hm.psutil, "Process", lambda: FakeProcess(80 * 1024**2))
    assert monitor.check_memory().status == "healthy"


def test_check_dependencies_reports_missing_core_and_optional(monkeypatch) -> None:
    import builtins
    import types

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        # Make this test independent from the actual environment by faking
        # presence/absence of the modules checked by HealthMonitor.
        if name in {"PySide6", "pydantic", "yaml", "pandas", "numba"}:
            return types.ModuleType(name)
        if name in {"numpy", "matplotlib"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    status = HealthMonitor().check_dependencies()
    assert status.status == "unhealthy"
    assert "missing_core" in status.details
    assert "numpy" in status.details["missing_core"]
    assert "matplotlib" in status.details["missing_optional"]


def test_check_dependencies_degraded_when_optional_missing(monkeypatch) -> None:
    import builtins
    import types

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"PySide6", "numpy", "pydantic", "yaml", "matplotlib", "numba"}:
            return types.ModuleType(name)
        if name in {"pandas"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    status = HealthMonitor().check_dependencies()
    assert status.status == "degraded"
    assert "pandas" in status.details["missing_optional"]


def test_check_configuration_missing_and_present(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monitor = HealthMonitor()
    missing = monitor.check_configuration()
    assert missing.status == "degraded"
    assert "missing" in missing.details

    # Create required paths
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "default.yaml").write_text("x: 1\n", encoding="utf-8")
    (tmp_path / "config" / "experiments").mkdir()
    (tmp_path / "config" / "equipment").mkdir()

    present = monitor.check_configuration()
    assert present.status == "healthy"
    assert present.details["checked"] == 3


def test_run_all_checks_handles_exceptions(monkeypatch) -> None:
    monitor = HealthMonitor()

    def check_ok() -> HealthStatus:
        return HealthStatus(
            status="healthy", message="ok", timestamp=hm_datetime(), details={}
        )

    def check_fail() -> HealthStatus:
        raise RuntimeError("boom")

    import src.monitoring.health_monitor as hm

    hm_datetime = hm.datetime.now  # stable callable for this test
    monitor.checks = [check_ok, check_fail]

    results = monitor.run_all_checks()
    assert results["ok"].status == "healthy"
    assert results["fail"].status == "unhealthy"


def test_get_overall_status_prioritizes_unhealthy(monkeypatch) -> None:
    monitor = HealthMonitor()

    def fake_results():
        now = None
        return {
            "a": HealthStatus(status="healthy", message="a", timestamp=now, details={}),
            "b": HealthStatus(status="unhealthy", message="b", timestamp=now, details={}),
        }

    monkeypatch.setattr(monitor, "run_all_checks", fake_results)
    overall = monitor.get_overall_status()
    assert overall.status == "unhealthy"
    assert overall.details["summary"]["unhealthy"] == 1


def test_get_health_monitor_singleton() -> None:
    a = get_health_monitor({"x": 1})
    b = get_health_monitor({"x": 2})
    assert a is b
