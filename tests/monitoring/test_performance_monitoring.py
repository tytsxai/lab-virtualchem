from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.monitoring.performance_monitor import (
    PerformanceMonitor,
    PerformanceTimer,
    get_performance_monitor,
)


class FakeProcess:
    def __init__(self, cpu_values: list[float], rss_bytes: int = 100 * 1024**2):
        self._cpu_values = list(cpu_values)
        self._rss_bytes = rss_bytes

    def cpu_percent(self, interval: float = 0.0) -> float:  # noqa: ARG002
        return self._cpu_values.pop(0) if self._cpu_values else 0.0

    def memory_info(self):
        return SimpleNamespace(rss=self._rss_bytes, vms=self._rss_bytes * 2)


def test_record_metrics_and_summary(monkeypatch) -> None:
    import src.monitoring.performance_monitor as pm

    monkeypatch.setattr(pm.psutil, "Process", lambda: FakeProcess([10.0, 30.0], 200 * 1024**2))
    monitor = PerformanceMonitor(window_size=5)

    cpu = monitor.record_cpu_usage()
    mem = monitor.record_memory_usage()
    rt = monitor.record_response_time("op", 123.4)

    assert cpu.name == "cpu_usage"
    assert mem.metadata["rss"] == 200 * 1024**2
    assert rt.metadata["operation"] == "op"

    summary = monitor.get_summary()
    assert summary["cpu"]["samples"] == 1
    assert summary["memory"]["samples"] == 1
    assert summary["response_time"]["samples"] == 1


def test_averages_peaks_and_thresholds(monkeypatch) -> None:
    import src.monitoring.performance_monitor as pm

    monkeypatch.setattr(pm.psutil, "Process", lambda: FakeProcess([90.0, 95.0], 800 * 1024**2))
    monitor = PerformanceMonitor(window_size=10)

    monitor.record_cpu_usage()
    monitor.record_cpu_usage()
    monitor.record_memory_usage()
    monitor.record_response_time("op", 2000)

    warnings = monitor.check_thresholds({"cpu": 80, "memory": 500, "response_time": 1000})
    assert any("CPU使用率过高" in w for w in warnings)
    assert any("内存使用过高" in w for w in warnings)
    assert any("响应时间过长" in w for w in warnings)


def test_timer_records_response_time(monkeypatch) -> None:
    monitor = PerformanceMonitor(window_size=5)
    recorded: list[float] = []

    def fake_record(operation: str, duration_ms: float):
        recorded.append(duration_ms)
        return None

    monitor.record_response_time = fake_record  # type: ignore[assignment]

    times = iter([1000.0, 1000.2])
    monkeypatch.setattr("src.monitoring.performance_monitor.time.time", lambda: next(times))

    with PerformanceTimer(monitor, "x"):
        pass
    assert pytest.approx(recorded[0], rel=1e-6) == 200.0


def test_record_cpu_and_memory_exception_paths(monkeypatch) -> None:
    import src.monitoring.performance_monitor as pm

    class BoomProcess:
        def cpu_percent(self, interval: float = 0.0) -> float:  # noqa: ARG002
            raise RuntimeError("cpu boom")

        def memory_info(self):
            raise RuntimeError("mem boom")

    monkeypatch.setattr(pm.psutil, "Process", lambda: BoomProcess())
    monitor = PerformanceMonitor(window_size=3)
    with pytest.raises(RuntimeError):
        monitor.record_cpu_usage()
    with pytest.raises(RuntimeError):
        monitor.record_memory_usage()


def test_clear_and_singleton(monkeypatch) -> None:
    import src.monitoring.performance_monitor as pm

    monkeypatch.setattr(pm.psutil, "Process", lambda: FakeProcess([1.0], 10 * 1024**2))
    monitor = PerformanceMonitor(window_size=3)
    monitor.record_cpu_usage()
    monitor.clear()
    assert monitor.get_average_cpu() == 0.0

    a = get_performance_monitor()
    b = get_performance_monitor()
    assert a is b
