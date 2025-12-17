"""
告警系统模块

功能:
- 告警规则配置
- 多种告警渠道
- 告警聚合和抑制
- 告警历史记录
"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""

    FIRING = "firing"  # 触发中
    RESOLVED = "resolved"  # 已解决
    SUPPRESSED = "suppressed"  # 已抑制


@dataclass
class Alert:
    """告警"""

    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.FIRING
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    resolved_at: datetime | None = None

    def resolve(self) -> None:
        """解决告警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()

    def suppress(self) -> None:
        """抑制告警"""
        self.status = AlertStatus.SUPPRESSED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "labels": self.labels,
            "annotations": self.annotations,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    condition: Callable[[], bool]  # 条件函数
    severity: AlertSeverity
    message: str
    threshold: float | None = None
    duration_seconds: int = 60  # 持续时间
    cooldown_seconds: int = 300  # 冷却时间
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    # 内部状态
    _last_triggered: datetime | None = None
    _first_violation: datetime | None = None

    def should_trigger(self) -> bool:
        """判断是否应该触发"""
        if not self.enabled:
            return False

        # 检查冷却期
        if self._last_triggered:
            cooldown_end = self._last_triggered + timedelta(
                seconds=self.cooldown_seconds
            )
            if datetime.now() < cooldown_end:
                return False

        # 检查条件
        try:
            condition_met = self.condition()
        except Exception as e:
            logger.info(f"告警规则 {self.name} 条件检查失败: {e}")
            return False

        if condition_met:
            # 记录首次违反时间
            if self._first_violation is None:
                self._first_violation = datetime.now()

            # 检查持续时间
            duration = (datetime.now() - self._first_violation).total_seconds()
            if duration >= self.duration_seconds:
                self._last_triggered = datetime.now()
                self._first_violation = None
                return True
        else:
            # 条件不满足,重置
            self._first_violation = None

        return False


class AlertChannel(ABC):
    """告警渠道基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送告警

        Args:
            alert: 告警对象

        Returns:
            是否发送成功
        """
        pass


class ConsoleAlertChannel(AlertChannel):
    """控制台告警渠道"""

    def send(self, alert: Alert) -> bool:
        """输出到控制台"""
        severity_icon = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }

        icon = severity_icon.get(alert.severity, "📢")
        logger.info(f"\n{icon} 【告警】{alert.rule_name}")
        logger.info(f"   级别: {alert.severity.value}")
        logger.info(f"   消息: {alert.message}")
        logger.info(f"   时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if alert.labels:
            logger.info(f"   标签: {alert.labels}")
        print()

        return True


class FileAlertChannel(AlertChannel):
    """文件告警渠道"""

    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path("logs/alerts")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def send(self, alert: Alert) -> bool:
        """写入文件"""
        try:
            log_file = (
                self.log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            logger.info(f"文件告警渠道发送失败: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Webhook告警渠道"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alert: Alert) -> bool:
        """发送到Webhook"""
        try:
            import requests

            payload = alert.to_dict()
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except ImportError:
            logger.info("需要安装 requests 库来使用 Webhook 渠道")
            return False
        except Exception as e:
            logger.info(f"Webhook告警渠道发送失败: {e}")
            return False


class EmailAlertChannel(AlertChannel):
    """邮件告警渠道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, alert: Alert) -> bool:
        """发送邮件"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.rule_name}"

            body = """
告警规则: {alert.rule_name}
严重级别: {alert.severity.value}
告警消息: {alert.message}
触发时间: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

标签: {alert.labels}
注释: {alert.annotations}
            """

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True
        except ImportError:
            logger.info("需要安装 smtplib 来使用邮件告警")
            return False
        except Exception as e:
            logger.info(f"邮件告警渠道发送失败: {e}")
            return False


class AlertManager:
    """告警管理器"""

    def __init__(self, enable_auto_check: bool = True):
        self._rules: dict[str, AlertRule] = {}
        self._channels: list[AlertChannel] = []
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

        # 自动检查线程
        self._check_thread: threading.Thread | None = None
        self._check_running = False

        # 默认添加控制台和文件渠道
        self.add_channel(ConsoleAlertChannel())
        self.add_channel(FileAlertChannel())

        if enable_auto_check:
            self.start_auto_check()

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self._rules[rule.name] = rule

    def remove_rule(self, rule_name: str) -> None:
        """移除告警规则"""
        with self._lock:
            if rule_name in self._rules:
                del self._rules[rule_name]

    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警渠道"""
        self._channels.append(channel)

    def check_rules(self) -> list[Alert]:
        """检查所有规则"""
        triggered_alerts = []

        with self._lock:
            for rule in self._rules.values():
                if rule.should_trigger():
                    alert = self._create_alert(rule)
                    triggered_alerts.append(alert)

        # 发送告警
        for alert in triggered_alerts:
            self._send_alert(alert)

        return triggered_alerts

    def fire_alert(
        self, rule_name: str, severity: AlertSeverity, message: str, **labels
    ) -> Alert:
        """手动触发告警"""
        alert_id = f"{rule_name}_{int(time.time() * 1000)}"

        alert = Alert(
            alert_id=alert_id,
            rule_name=rule_name,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            labels=labels,
        )

        self._send_alert(alert)
        return alert

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.resolve()
                del self._active_alerts[alert_id]
                self._alert_history.append(alert)
                return True
        return False

    def get_active_alerts(self, severity: AlertSeverity | None = None) -> list[Alert]:
        """获取活跃告警"""
        with self._lock:
            alerts = list(self._active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_alert_stats(self) -> dict[str, Any]:
        """获取告警统计"""
        with self._lock:
            active_count = len(self._active_alerts)

            by_severity = defaultdict(int)
            for alert in self._active_alerts.values():
                by_severity[alert.severity.value] += 1

            by_rule = defaultdict(int)
            for alert in self._alert_history:
                by_rule[alert.rule_name] += 1

        return {
            "active_alerts": active_count,
            "by_severity": dict(by_severity),
            "top_rules": dict(
                sorted(by_rule.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

    def start_auto_check(self, interval_seconds: int = 60) -> None:
        """启动自动检查"""
        if self._check_running:
            return

        self._check_running = True
        self._check_thread = threading.Thread(
            target=self._auto_check_loop, args=(interval_seconds,), daemon=True
        )
        self._check_thread.start()

    def stop_auto_check(self) -> None:
        """停止自动检查"""
        self._check_running = False
        if self._check_thread:
            self._check_thread.join(timeout=5)

    def _auto_check_loop(self, interval: int) -> None:
        """自动检查循环"""
        while self._check_running:
            try:
                self.check_rules()
            except Exception as e:
                logger.info(f"告警检查错误: {e}")

            time.sleep(interval)

    def _create_alert(self, rule: AlertRule) -> Alert:
        """创建告警"""
        alert_id = f"{rule.name}_{int(time.time() * 1000)}"

        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=rule.message,
            timestamp=datetime.now(),
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy(),
        )

        with self._lock:
            self._active_alerts[alert_id] = alert
            self._alert_history.append(alert)

        return alert

    def _send_alert(self, alert: Alert) -> None:
        """发送告警到所有渠道"""
        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as e:
                logger.info(f"告警渠道发送失败: {e}")


# 全局告警管理器
alert_manager = AlertManager()


# 便捷函数
def create_threshold_rule(
    name: str,
    metric_getter: Callable[[], float],
    threshold: float,
    operator: str = ">",
    severity: AlertSeverity = AlertSeverity.WARNING,
    message: str | None = None,
) -> AlertRule:
    """创建阈值告警规则"""
    operators = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    if operator not in operators:
        raise ValueError(f"不支持的操作符: {operator}")

    def condition():
        value = metric_getter()
        return operators[operator](value, threshold)

    msg = message or f"{name} {operator} {threshold}"

    return AlertRule(
        name=name,
        condition=condition,
        severity=severity,
        message=msg,
        threshold=threshold,
    )
