from __future__ import annotations

import builtins
import json
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest


def test_alert_lifecycle_and_to_dict() -> None:
    from src.monitoring.alerting import Alert, AlertSeverity

    now = datetime.now()
    alert = Alert(
        alert_id="a1",
        rule_name="r",
        severity=AlertSeverity.WARNING,
        message="m",
        timestamp=now,
        labels={"k": "v"},
    )
    alert.suppress()
    assert alert.status.value == "suppressed"
    alert.resolve()
    payload = alert.to_dict()
    assert payload["severity"] == "warning"
    assert payload["resolved_at"] is not None


def test_alert_rule_duration_cooldown_and_exception(monkeypatch) -> None:
    import src.monitoring.alerting as alerting

    base = datetime(2025, 1, 1, 0, 0, 0)
    # `should_trigger()` may call `datetime.now()` multiple times per invocation.
    times = iter(
        [
            base,  # first violation timestamp
            base,  # duration calculation (0s)
            base + timedelta(seconds=30),  # second call duration calculation (30s)
            base + timedelta(seconds=61),  # third call duration calculation (61s)
            base + timedelta(seconds=61),  # set _last_triggered
            base + timedelta(seconds=62),  # fourth call cooldown check
        ]
    )

    class FakeDateTime:
        @classmethod
        def now(cls):  # noqa: N805
            return next(times)

    monkeypatch.setattr(alerting, "datetime", FakeDateTime)

    rule = alerting.AlertRule(
        name="r",
        condition=lambda: True,
        severity=alerting.AlertSeverity.ERROR,
        message="x",
        duration_seconds=60,
        cooldown_seconds=300,
    )
    assert rule.should_trigger() is False  # first violation at t0
    assert rule.should_trigger() is False  # t+30
    assert rule.should_trigger() is True  # t+61 triggers
    assert rule.should_trigger() is False  # t+62 in cooldown

    def boom():
        raise RuntimeError("bad")

    rule2 = alerting.AlertRule(
        name="e",
        condition=boom,
        severity=alerting.AlertSeverity.WARNING,
        message="x",
    )
    assert rule2.should_trigger() is False


def test_threshold_rule_operator_validation_and_behavior() -> None:
    from src.monitoring.alerting import create_threshold_rule

    with pytest.raises(ValueError):
        create_threshold_rule("x", metric_getter=lambda: 1.0, threshold=2.0, operator="~")

    rule = create_threshold_rule("x", metric_getter=lambda: 5.0, threshold=2.0, operator=">")
    assert rule.condition() is True


def test_file_alert_channel_writes_jsonl(tmp_path) -> None:
    from src.monitoring.alerting import Alert, AlertSeverity, FileAlertChannel

    channel = FileAlertChannel(log_dir=tmp_path)
    alert = Alert(
        alert_id="a1",
        rule_name="r",
        severity=AlertSeverity.INFO,
        message="m",
        timestamp=datetime.now(),
    )
    assert channel.send(alert) is True
    written = list(tmp_path.glob("alerts_*.jsonl"))
    assert written
    line = written[0].read_text(encoding="utf-8").splitlines()[0]
    payload = json.loads(line)
    assert payload["alert_id"] == "a1"


def test_console_channel_and_file_channel_error(monkeypatch, tmp_path) -> None:
    from src.monitoring.alerting import Alert, AlertSeverity, ConsoleAlertChannel, FileAlertChannel

    alert = Alert(
        alert_id="a1",
        rule_name="r",
        severity=AlertSeverity.CRITICAL,
        message="m",
        timestamp=datetime.now(),
        labels={"k": "v"},
    )
    assert ConsoleAlertChannel().send(alert) is True

    channel = FileAlertChannel(log_dir=tmp_path)

    def boom_open(*args, **kwargs):  # noqa: ARG001,ARG002
        raise OSError("nope")

    monkeypatch.setattr(builtins, "open", boom_open)
    assert channel.send(alert) is False


def test_webhook_alert_channel_import_error(monkeypatch) -> None:
    from src.monitoring.alerting import Alert, AlertSeverity, WebhookAlertChannel

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("requests")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    channel = WebhookAlertChannel("http://example.invalid")
    alert = Alert(
        alert_id="a1",
        rule_name="r",
        severity=AlertSeverity.INFO,
        message="m",
        timestamp=datetime.now(),
    )
    assert channel.send(alert) is False


def test_webhook_alert_channel_success(monkeypatch) -> None:
    from src.monitoring.alerting import Alert, AlertSeverity, WebhookAlertChannel

    class FakeRequests:
        @staticmethod
        def post(url, json=None, timeout=0):  # noqa: A002,ARG002
            return SimpleNamespace(status_code=200)

    sys.modules["requests"] = FakeRequests
    try:
        channel = WebhookAlertChannel("http://example.invalid")
        alert = Alert(
            alert_id="a1",
            rule_name="r",
            severity=AlertSeverity.INFO,
            message="m",
            timestamp=datetime.now(),
        )
        assert channel.send(alert) is True
    finally:
        sys.modules.pop("requests", None)


def test_email_alert_channel_success_and_failure(monkeypatch) -> None:
    import smtplib
    import src.monitoring.alerting as alerting

    class FakeSMTP:
        def __init__(self, host, port):  # noqa: ARG002
            self.started = False
            self.logged_in = False
            self.sent = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

        def starttls(self):
            self.started = True

        def login(self, username, password):  # noqa: ARG002
            self.logged_in = True

        def send_message(self, msg):  # noqa: ARG002
            self.sent = True

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    channel = alerting.EmailAlertChannel(
        smtp_host="h",
        smtp_port=25,
        username="u",
        password="p",
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
    )
    alert = alerting.Alert(
        alert_id="a1",
        rule_name="r",
        severity=alerting.AlertSeverity.ERROR,
        message="m",
        timestamp=datetime.now(),
    )
    assert channel.send(alert) is True

    def boom_smtp(*args, **kwargs):  # noqa: ARG001,ARG002
        raise RuntimeError("fail")

    monkeypatch.setattr(smtplib, "SMTP", boom_smtp)
    assert channel.send(alert) is False


def test_alert_manager_basic_flow() -> None:
    from src.monitoring.alerting import AlertManager, AlertRule, AlertSeverity

    manager = AlertManager(enable_auto_check=False)
    manager._channels = []  # isolate from console/file side effects

    fired: list[str] = []

    class StubChannel:
        def send(self, alert):  # noqa: ANN001
            fired.append(alert.alert_id)
            return True

    manager.add_channel(StubChannel())
    rule = AlertRule(
        name="r",
        condition=lambda: True,
        severity=AlertSeverity.WARNING,
        message="m",
        duration_seconds=0,
        cooldown_seconds=0,
    )
    manager.add_rule(rule)
    alerts = manager.check_rules()
    assert len(alerts) == 1
    assert manager.get_active_alerts()

    alert_id = alerts[0].alert_id
    assert manager.resolve_alert(alert_id) is True
    assert manager.resolve_alert(alert_id) is False
    # exercise manual fire + severity filtering
    manual = manager.fire_alert("manual", AlertSeverity.ERROR, "x", user="u")
    assert manager.get_active_alerts(severity=AlertSeverity.ERROR) == []
    assert manual.rule_name == "manual"
    stats = manager.get_alert_stats()
    assert stats["active_alerts"] == 0


def test_alert_manager_start_stop_autocheck_without_real_thread(monkeypatch) -> None:
    import src.monitoring.alerting as alerting

    created: list[object] = []

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=False):  # noqa: ARG002
            self.started = False
            self.joined = False
            created.append(self)

        def start(self):
            self.started = True

        def join(self, timeout=None):  # noqa: ARG002
            self.joined = True

    monkeypatch.setattr(alerting.threading, "Thread", FakeThread)

    manager = alerting.AlertManager(enable_auto_check=False)
    manager.start_auto_check(interval_seconds=1)
    assert manager._check_running is True
    assert created and created[0].started is True
    manager.stop_auto_check()
    assert created[0].joined is True
