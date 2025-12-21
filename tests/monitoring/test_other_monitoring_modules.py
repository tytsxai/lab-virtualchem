from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_monitoring_config_load_and_to_dict(tmp_path) -> None:
    from src.monitoring.config import MonitoringConfig, load_monitoring_config

    cfg_path = tmp_path / "monitoring.json"
    cfg_path.write_text(
        json.dumps(
            {
                "monitoring": {
                    "enabled": False,
                    "app_name": "X",
                    "frontend": {
                        "error_tracking": {"enabled": False, "max_errors": 12},
                        "behavior_tracking": {"max_events": 34},
                    },
                    "backend": {
                        "apm": {"enabled": False},
                        "resource_monitoring": {
                            "enabled": False,
                            "interval_seconds": 10,
                        },
                        "health_check": {
                            "thresholds": {
                                "cpu_warning": 1,
                                "cpu_critical": 2,
                                "memory_warning": 3,
                                "memory_critical": 4,
                                "disk_warning": 5,
                                "disk_critical": 6,
                            }
                        },
                    },
                    "tracing": {"enabled": False, "sample_rate": 0.1},
                    "alerting": {
                        "enabled": False,
                        "auto_check": False,
                        "check_interval_seconds": 7,
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    loaded = MonitoringConfig.from_file(cfg_path)
    assert loaded.enabled is False
    assert loaded.frontend_enabled is False
    assert loaded.frontend_max_errors == 12
    assert loaded.frontend_max_events == 34
    assert loaded.resource_monitoring_interval == 10
    assert loaded.alerting_check_interval == 7

    as_dict = loaded.to_dict()
    assert as_dict["app_name"] == "X"
    assert as_dict["thresholds"]["disk_critical"] == 6

    missing = load_monitoring_config(tmp_path / "missing.json")
    assert isinstance(missing, MonitoringConfig)


def test_load_monitoring_config_default_path(tmp_path, monkeypatch) -> None:
    from src.monitoring.config import load_monitoring_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "monitoring_config.json").write_text(
        json.dumps({"monitoring": {"enabled": True}}, ensure_ascii=False),
        encoding="utf-8",
    )

    cfg = load_monitoring_config()
    assert cfg.enabled is True


def test_metrics_collector_basic_and_singleton(monkeypatch) -> None:
    from src.monitoring.metrics_collector import MetricsCollector, get_metrics_collector

    collector = MetricsCollector()
    collector.counter("hits")
    collector.counter("hits", 2)
    collector.gauge("temp", 3.5, tags={"unit": "c"})
    assert collector.get_counter_value("hits") == 3
    assert collector.get_gauge_value("temp") == 3.5

    since = datetime.now() - timedelta(seconds=1)
    filtered = collector.get_metrics(name="hits", since=since)
    assert filtered and all(m.name == "hits" for m in filtered)

    # Force old timestamps to exercise clear_old_metrics
    collector.metrics[0].timestamp = datetime.now() - timedelta(hours=2)
    cleared = collector.clear_old_metrics(older_than=timedelta(hours=1))
    assert cleared == 1

    summary = collector.get_summary()
    assert summary["total_metrics"] == len(collector.metrics)

    a = get_metrics_collector()
    b = get_metrics_collector()
    assert a is b


def test_distributed_tracing_core_flow(tmp_path) -> None:
    import src.monitoring.distributed_tracing as dt

    tm = dt.TraceManager(service_name="svc")
    tm.log_dir = tmp_path

    ctx = tm.start_trace("root", user="u")
    assert ctx.trace_id
    tm.log_event("evt1", context=ctx, x=1)
    tm.set_tag("k", "v", context=ctx)
    tm.finish_span(ctx, status="ok")

    spans = tm.get_trace(ctx.trace_id)
    assert spans and spans[0].operation_name == "root"
    tree = tm.get_trace_tree(ctx.trace_id)
    assert tree["trace_id"] == ctx.trace_id

    stats = tm.get_statistics(since_minutes=60)
    assert stats["total_spans"] >= 1

    headers = ctx.to_headers()
    parsed = dt.TracingContext.from_headers(headers)
    assert parsed is not None
    assert dt.TracingContext.from_headers({}) is None

    child = ctx.fork_child()
    assert child.parent_span_id == ctx.span_id

    # Contextmanager error path
    with pytest.raises(RuntimeError):
        with tm.trace("boom"):
            raise RuntimeError("x")


def test_trace_function_decorator_uses_global_manager(tmp_path, monkeypatch) -> None:
    import src.monitoring.distributed_tracing as dt

    mgr = dt.TraceManager()
    mgr.log_dir = tmp_path
    monkeypatch.setattr(dt, "_trace_manager", mgr)

    @dt.trace_function("op")
    def f(x: int) -> int:
        return x + 1

    assert f(1) == 2


def test_backend_monitoring_apm_and_health(tmp_path, monkeypatch) -> None:
    import src.monitoring.backend_monitor as bm

    # Ensure `_should_start_background_threads` can return True in a controlled way.
    monkeypatch.delenv("VCL_DISABLE_BACKGROUND_THREADS", raising=False)
    monkeypatch.delenv("VCL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(bm, "sys", SimpleNamespace(modules={}), raising=False)
    assert bm._should_start_background_threads() is True

    monkeypatch.setenv("VCL_DISABLE_BACKGROUND_THREADS", "1")
    assert bm._should_start_background_threads() is False

    apm = bm.APMCollector(app_name="x", log_dir=tmp_path)
    apm.increment_counter("c", 2, k="v")
    apm.set_gauge("g", 1.5)
    apm.record_histogram("h", 3.0)
    stats = apm.get_metric_stats("c")
    assert stats["count"] >= 1

    @apm.time_operation("op", tag="t")
    def ok() -> int:
        return 1

    assert ok() == 1

    @apm.time_operation("op2")
    def boom() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        boom()

    # BackendMonitor health/perf with mocked psutil
    monkeypatch.setattr(bm.psutil, "cpu_percent", lambda interval=None: 10.0)  # noqa: ARG005
    monkeypatch.setattr(
        bm.psutil, "virtual_memory", lambda: SimpleNamespace(percent=10.0, used=1, available=2)
    )
    monkeypatch.setattr(bm.psutil, "disk_usage", lambda _p: SimpleNamespace(percent=10.0, used=1, free=2))

    monitor = bm.BackendMonitor(app_name="x", enable_resource_monitoring=False)
    monitor.apm = apm
    health = monitor.get_health_status()
    assert health["status"] == "healthy"
    perf = monitor.get_performance_summary()
    assert "total_metrics" in perf


def test_frontend_monitor_and_behavior_tracker(tmp_path) -> None:
    from src.monitoring.frontend_monitor import (
        ErrorLevel,
        EventType,
        FrontendMonitor,
        UserBehaviorTracker,
    )

    fm = FrontendMonitor(log_dir=tmp_path / "frontend", max_errors=10)
    seen: list[str] = []

    def handler(report):  # noqa: ANN001
        seen.append(report.error_id)
        raise RuntimeError("handler fail")

    fm.add_error_handler(handler)
    try:
        raise ValueError("bad\npassword=123")
    except Exception as exc:  # noqa: BLE001
        error_id = fm.capture_exception(
            exc, level=ErrorLevel.ERROR, user_id="u", component="c", token="secret"
        )

    assert error_id in fm.get_error_stats()["top_errors"][0]["error_id"]
    assert seen  # handler invoked even if it fails

    fm.capture_message("hello", level=ErrorLevel.INFO)
    assert fm.get_errors(level=ErrorLevel.ERROR)
    fm.clear_errors()
    assert fm.get_error_stats()["total_errors"] == 0

    bt = UserBehaviorTracker(log_dir=tmp_path / "behavior", max_events=10)
    session = "s1"
    bt.track_event(EventType.CUSTOM, "comp", "act", session_id=session, foo=1)
    bt.track_click("comp", "btn", session_id=session)
    bt.track_view("page", duration_ms=12.3, session_id=session)
    bt.track_navigation("a", "b", session_id=session)

    stats = bt.get_event_stats()
    assert stats["active_sessions"] == 1
    assert bt.get_session_events(session)
    clickstream = bt.analyze_clickstream(session_id=session)
    assert clickstream["total_steps"] >= 1


def test_experiment_metrics_collector_end_to_end(monkeypatch) -> None:
    from src.monitoring.experiment_metrics import ExperimentMetricsCollector

    collector = ExperimentMetricsCollector()
    now = datetime.now()

    collector.record_experiment_run(
        experiment_id="e1",
        experiment_title="t1",
        experiment_type="type",
        user_id="u1",
        record_data={
            "status": "completed",
            "duration_seconds": 10,
            "score": {"total": 85},
            "mistakes_summary": [{"error_type": "x"}],
            "step_records": [{"step_id": "s1", "passed": True, "attempts": 1}],
        },
    )
    collector.record_experiment_run(
        experiment_id="e1",
        experiment_title="t1",
        experiment_type="type",
        user_id="u2",
        record_data={"status": "abandoned", "timestamp": now - timedelta(days=100)},
    )

    metrics = collector.get_experiment_metrics("e1", use_cache=False)
    assert metrics.total_runs == 2
    assert metrics.completed_runs == 1
    assert metrics.score_distribution["80-89"] == 1
    assert metrics.mistake_types["x"] == 1
    assert metrics.step_pass_rates["s1"] == 100.0
    assert metrics.to_dict()["execution"]["completion_rate"] == 50.0

    # Cache path
    cached = collector.get_experiment_metrics("e1", use_cache=True)
    assert cached.total_runs == 2

    summary = collector.get_all_experiments_summary()
    assert summary and summary[0]["experiment_id"] == "e1"

    history = collector.get_user_experiment_history("u1", limit=5)
    assert history and history[0]["user_id"] == "u1"

    popular = collector.get_popular_experiments(limit=1)
    assert popular[0]["total_runs"] == 2

    # Clear old data should remove the old abandoned run.
    cleared = collector.clear_old_data(days=30)
    assert cleared >= 1


def test_dashboard_generate_html_report(tmp_path, monkeypatch) -> None:
    from src.monitoring.dashboard import MonitoringDashboard
    from src.monitoring.alerting import Alert, AlertSeverity

    class StubBackend:
        def get_health_status(self):
            return {"status": "healthy", "uptime_seconds": 1.0, "issues": [], "metrics": {}}

        def get_performance_summary(self):
            return {"total_metrics": 0, "by_type": {}, "health": self.get_health_status()}

    class StubAlerts:
        def get_active_alerts(self, severity=None):  # noqa: ARG002
            return [
                Alert(
                    alert_id="a1",
                    rule_name="r",
                    severity=AlertSeverity.INFO,
                    message="m",
                    timestamp=datetime.now(),
                )
            ]

        def get_alert_stats(self):
            return {"active_alerts": 1, "by_severity": {"info": 1}, "top_rules": {}}

    class StubFrontend:
        def get_error_stats(self):
            return {"total_errors": 0, "by_level": {}}

        def get_errors(self, limit=100, level=None):  # noqa: ARG002
            return []

    class StubBehavior:
        def get_event_stats(self):
            return {"total_events": 0, "by_type": {}, "by_component": {}, "active_sessions": 0}

    class StubTrace:
        def get_statistics(self, since_minutes=60):  # noqa: ARG002
            return {"total_traces": 0, "total_spans": 0}

    # Avoid 1s delay from psutil.cpu_percent(interval=1) by shadowing the imported module.
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            cpu_percent=lambda interval=1: 0.0,  # noqa: ARG005
            cpu_count=lambda: 4,
            virtual_memory=lambda: SimpleNamespace(
                total=1, used=1, available=1, percent=1.0
            ),
            disk_usage=lambda _p: SimpleNamespace(total=1, used=1, free=1, percent=1.0),
        ),
    )

    board = MonitoringDashboard(
        frontend_monitor=StubFrontend(),
        behavior_tracker=StubBehavior(),
        backend_monitor=StubBackend(),
        trace_manager=StubTrace(),
        alert_manager=StubAlerts(),
    )
    out = tmp_path / "report.html"
    board.generate_html_report(out)
    assert out.exists()
    assert "VirtualChemLab" in out.read_text(encoding="utf-8")


def test_dashboard_export_json_and_singleton(tmp_path, monkeypatch) -> None:
    import src.monitoring.dashboard as dash

    RealDashboard = dash.MonitoringDashboard

    class StubDashboard:
        def __init__(self):
            self.called = 0

        def get_overview(self):
            return {"ok": True}

        def get_system_metrics(self):
            return {"cpu": {"percent": 0}}

        def get_error_summary(self):
            return {}

        def get_trace_summary(self):
            return {}

        def get_alert_summary(self):
            return {}

    dash._dashboard = None
    monkeypatch.setattr(dash, "MonitoringDashboard", StubDashboard)

    instance = dash.get_dashboard()
    assert isinstance(instance, StubDashboard)

    # Cover `export_json_report` on the real class using a lightweight stub wiring.
    class MiniBoard(RealDashboard):
        def __init__(self):  # avoid importing heavy globals
            pass

        def get_overview(self):
            return {"health": {"status": "healthy"}, "timestamp": "t", "alerts": {}, "errors": {}, "events": {}, "performance": {}}

        def get_system_metrics(self):
            return {"cpu": {"percent": 0}, "memory": {"percent": 0}, "disk": {"percent": 0}}

        def get_error_summary(self, limit: int = 100):  # noqa: ARG002
            return {"stats": {}, "recent_errors": []}

        def get_trace_summary(self, since_minutes: int = 60):  # noqa: ARG002
            return {}

        def get_alert_summary(self):
            return {"stats": {}, "active_alerts": []}

    json_out = tmp_path / "report.json"
    MiniBoard().export_json_report(json_out)
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["overview"]["health"]["status"] == "healthy"
