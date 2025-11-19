from __future__ import annotations

from types import SimpleNamespace

import os
import pytest

from src.utils import health_check
from src.utils.health_check import HealthChecker, PerformanceMonitor, time_operation


@pytest.fixture
def checker():
    return HealthChecker()


@pytest.fixture
def fresh_performance_monitor(monkeypatch):
    monitor = PerformanceMonitor(max_metrics=5)
    monkeypatch.setattr(health_check, "performance_monitor", monitor)
    return monitor


def test_check_disk_space_thresholds(monkeypatch, checker):
    usage = {"free_percent": 50.0}

    def fake_disk_usage(path):
        total = 100
        free = total * usage["free_percent"] / 100
        used = total - free
        return SimpleNamespace(total=total, free=free, used=used)

    monkeypatch.setattr(health_check.psutil, "disk_usage", fake_disk_usage)

    assert checker.check_disk_space()["status"] == "healthy"
    usage["free_percent"] = 15.0
    assert checker.check_disk_space()["status"] == "warning"
    usage["free_percent"] = 5.0
    assert checker.check_disk_space()["status"] == "critical"


def test_check_memory_and_cpu(monkeypatch, checker):
    memory = {"percent": 50.0}

    def fake_virtual_memory():
        return SimpleNamespace(
            percent=memory["percent"],
            total=8 * 1024**3,
            used=4 * 1024**3,
            available=4 * 1024**3,
        )

    monkeypatch.setattr(health_check.psutil, "virtual_memory", fake_virtual_memory)

    assert checker.check_memory()["status"] == "healthy"
    memory["percent"] = 95.0
    assert checker.check_memory()["status"] == "critical"

    cpu_percent = {"value": 50.0}
    monkeypatch.setattr(health_check.psutil, "cpu_percent", lambda interval=0.5: cpu_percent["value"])
    monkeypatch.setattr(health_check.psutil, "cpu_count", lambda: 8)

    assert checker.check_cpu()["status"] == "healthy"
    cpu_percent["value"] = 90.0
    assert checker.check_cpu()["status"] == "critical"


def test_check_directories_and_files(monkeypatch, tmp_path, checker):
    existing = tmp_path / "data"
    existing.mkdir()
    missing = tmp_path / "missing"

    def fake_access(path, mode):
        path_str = os.fspath(path)
        if path_str == str(existing):
            return mode == os.R_OK
        return False

    monkeypatch.setattr(health_check.os, "access", fake_access)

    dir_result = checker.check_directories([str(existing), str(missing)])
    assert dir_result["status"] == "critical"
    assert dir_result["directories"][0]["readable"] is True
    assert dir_result["directories"][0]["writable"] is False

    file_ok = tmp_path / "file.txt"
    file_ok.write_text("chemistry", encoding="utf-8")

    monkeypatch.setattr(health_check.os, "access", lambda path, mode: True)
    file_result = checker.check_files([str(file_ok), str(tmp_path / "absent.txt")])
    assert file_result["status"] == "warning"
    assert file_result["files"][0]["size_kb"] > 0
    assert file_result["files"][1]["exists"] is False


def test_run_all_checks_summary(monkeypatch, checker):
    monkeypatch.setattr(checker, "check_disk_space", lambda: {"check": "disk", "status": "healthy"})
    monkeypatch.setattr(checker, "check_memory", lambda: {"check": "mem", "status": "warning"})
    monkeypatch.setattr(checker, "check_cpu", lambda: {"check": "cpu", "status": "healthy"})
    monkeypatch.setattr(checker, "check_directories", lambda dirs: {"check": "dir", "status": "critical"})
    monkeypatch.setattr(checker, "check_files", lambda files: {"check": "files", "status": "healthy"})

    report = checker.run_all_checks(["/data"], ["config.yaml"])
    assert report["overall_status"] == "critical"
    assert report["summary"]["total_checks"] == 5
    assert report["summary"]["critical"] == 1
    assert report["summary"]["warnings"] == 1


def test_performance_monitor_stats_and_clear(fresh_performance_monitor):
    monitor = fresh_performance_monitor
    monitor.record_metric("load_data", 10.0, True)
    monitor.record_metric("load_data", 30.0, False)

    stats = monitor.get_stats("load_data")
    assert stats["count"] == 2
    assert stats["total_successes"] == 1
    assert stats["total_failures"] == 1
    assert stats["avg_duration_ms"] == 20.0

    # get_recent_metrics should respect ordering
    recent = monitor.get_recent_metrics("load_data", 1)
    assert recent[0]["duration_ms"] == 30.0

    monitor.clear_metrics("load_data")
    assert monitor.get_stats("load_data")["count"] == 0


def test_time_operation_records_success_and_failure(fresh_performance_monitor):
    @time_operation("success_op")
    def successful_task(value):
        return value * 2

    assert successful_task(3) == 6

    @time_operation("failure_op")
    def failing_task():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        failing_task()

    success_stats = fresh_performance_monitor.get_stats("success_op")
    assert success_stats["total_successes"] == 1

    failure_stats = fresh_performance_monitor.get_stats("failure_op")
    assert failure_stats["total_failures"] == 1
    recent_failure = fresh_performance_monitor.get_recent_metrics("failure_op")[0]
    assert recent_failure["metadata"]["error"] == "boom"
