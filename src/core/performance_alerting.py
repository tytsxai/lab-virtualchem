"""
性能告警系统
提供实时性能监控、阈值告警和自动优化建议
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .enhanced_event_bus import EventPriority, publish_event
from .error_handler import get_error_handler
from .unified_performance_monitor import MetricType, PerformanceMetric

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    duration: float = 0.0  # 持续时间（秒）
    cooldown: float = 300.0  # 冷却时间（秒）
    enabled: bool = True
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """告警对象"""
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    timestamp: float = field(default_factory=time.time)
    state: AlertState = AlertState.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_name": self.rule_name,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "state": self.state.value,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "description": self.description,
            "tags": self.tags
        }


@dataclass
class AlertAction:
    """告警动作"""
    name: str
    action_type: str  # "notification", "auto_fix", "escalation"
    action_function: Callable[[Alert], None]
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)


class PerformanceAlerting:
    """性能告警系统"""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._actions: Dict[str, AlertAction] = {}
        self._cooldowns: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._error_handler = get_error_handler()

        # 统计信息
        self._stats = {
            "total_alerts": 0,
            "active_alerts": 0,
            "resolved_alerts": 0,
            "suppressed_alerts": 0,
            "actions_triggered": 0
        }

        # 初始化默认规则
        self._setup_default_rules()

        # 初始化默认动作
        self._setup_default_actions()

    def _setup_default_rules(self) -> None:
        """设置默认告警规则"""
        # CPU使用率告警
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            metric_name=MetricType.CPU_USAGE.value,
            threshold=80.0,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            duration=30.0,
            description="CPU使用率过高"
        ))

        # 内存使用率告警
        self.add_rule(AlertRule(
            name="high_memory_usage",
            metric_name=MetricType.MEMORY_USAGE.value,
            threshold=85.0,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            duration=60.0,
            description="内存使用率过高"
        ))

        # 帧率告警
        self.add_rule(AlertRule(
            name="low_fps",
            metric_name=MetricType.FPS.value,
            threshold=30.0,
            comparison="lt",
            severity=AlertSeverity.ERROR,
            duration=10.0,
            description="帧率过低"
        ))

        # 磁盘使用率告警
        self.add_rule(AlertRule(
            name="high_disk_usage",
            metric_name=MetricType.DISK_USAGE.value,
            threshold=90.0,
            comparison="gt",
            severity=AlertSeverity.CRITICAL,
            duration=0.0,
            description="磁盘使用率过高"
        ))

    def _setup_default_actions(self) -> None:
        """设置默认告警动作"""
        # 通知动作
        self.add_action(AlertAction(
            name="notify_user",
            action_type="notification",
            action_function=self._notify_user,
            conditions={"severity": ["warning", "error", "critical"]}
        ))

        # 自动修复动作
        self.add_action(AlertAction(
            name="auto_optimize",
            action_type="auto_fix",
            action_function=self._auto_optimize,
            conditions={"severity": ["warning"], "metric_name": ["cpu_usage", "memory_usage"]}
        ))

        # 升级动作
        self.add_action(AlertAction(
            name="escalate_critical",
            action_type="escalation",
            action_function=self._escalate_critical,
            conditions={"severity": ["critical"]}
        ))

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self._rules[rule.name] = rule
            logger.debug(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> None:
        """移除告警规则"""
        with self._lock:
            if rule_name in self._rules:
                del self._rules[rule_name]
                logger.debug(f"Removed alert rule: {rule_name}")

    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """获取告警规则"""
        return self._rules.get(rule_name)

    def add_action(self, action: AlertAction) -> None:
        """添加告警动作"""
        with self._lock:
            self._actions[action.name] = action
            logger.debug(f"Added alert action: {action.name}")

    def remove_action(self, action_name: str) -> None:
        """移除告警动作"""
        with self._lock:
            if action_name in self._actions:
                del self._actions[action_name]
                logger.debug(f"Removed alert action: {action_name}")

    def get_action(self, action_name: str) -> Optional[AlertAction]:
        """获取告警动作"""
        return self._actions.get(action_name)

    def check_metric(self, metric: PerformanceMetric) -> None:
        """检查指标"""
        with self._lock:
            # 查找匹配的规则
            for rule_name, rule in self._rules.items():
                if not rule.enabled or rule.metric_name != metric.name:
                    continue

                # 检查冷却时间
                if rule_name in self._cooldowns:
                    if time.time() - self._cooldowns[rule_name] < rule.cooldown:
                        continue

                # 检查阈值
                if self._check_threshold(metric.value, rule.threshold, rule.comparison):
                    # 创建告警
                    alert = Alert(
                        rule_name=rule_name,
                        metric_name=metric.name,
                        current_value=metric.value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        description=rule.description,
                        tags=rule.tags
                    )

                    # 检查是否已存在相同告警
                    if rule_name in self._active_alerts:
                        existing_alert = self._active_alerts[rule_name]
                        if existing_alert.state == AlertState.ACTIVE:
                            continue

                    # 激活告警
                    self._activate_alert(alert)
                else:
                    # 检查是否需要解决告警
                    if rule_name in self._active_alerts:
                        alert = self._active_alerts[rule_name]
                        if alert.state == AlertState.ACTIVE:
                            self._resolve_alert(alert)

    def _check_threshold(self, value: float, threshold: float, comparison: str) -> bool:
        """检查阈值"""
        if comparison == "gt":
            return value > threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "eq":
            return abs(value - threshold) < 0.001
        elif comparison == "gte":
            return value >= threshold
        elif comparison == "lte":
            return value <= threshold
        else:
            return False

    def _activate_alert(self, alert: Alert) -> None:
        """激活告警"""
        self._active_alerts[alert.rule_name] = alert
        self._alert_history.append(alert)
        self._stats["total_alerts"] += 1
        self._stats["active_alerts"] += 1

        # 设置冷却时间
        self._cooldowns[alert.rule_name] = time.time()

        # 触发动作
        self._trigger_actions(alert)

        # 发布事件
        publish_event("performance_alert_activated", alert.to_dict(), priority=EventPriority.HIGH)

        logger.warning(f"Performance alert activated: {alert.rule_name} - {alert.description}")

    def _resolve_alert(self, alert: Alert) -> None:
        """解决告警"""
        alert.state = AlertState.RESOLVED
        alert.resolved_at = time.time()

        self._stats["active_alerts"] -= 1
        self._stats["resolved_alerts"] += 1

        # 发布事件
        publish_event("performance_alert_resolved", alert.to_dict(), priority=EventPriority.NORMAL)

        logger.info(f"Performance alert resolved: {alert.rule_name}")

    def _trigger_actions(self, alert: Alert) -> None:
        """触发告警动作"""
        for action_name, action in self._actions.items():
            if not action.enabled:
                continue

            # 检查条件
            if self._check_action_conditions(action, alert):
                try:
                    action.action_function(alert)
                    self._stats["actions_triggered"] += 1
                    logger.debug(f"Alert action triggered: {action_name}")
                except Exception as e:
                    logger.error(f"Alert action failed: {action_name} - {e}")

    def _check_action_conditions(self, action: AlertAction, alert: Alert) -> bool:
        """检查动作条件"""
        conditions = action.conditions

        # 检查严重程度
        if "severity" in conditions:
            if alert.severity.value not in conditions["severity"]:
                return False

        # 检查指标名称
        if "metric_name" in conditions:
            if alert.metric_name not in conditions["metric_name"]:
                return False

        # 检查标签
        if "tags" in conditions:
            for key, value in conditions["tags"].items():
                if alert.tags.get(key) != value:
                    return False

        return True

    def acknowledge_alert(self, rule_name: str, acknowledged_by: str) -> bool:
        """确认告警"""
        with self._lock:
            if rule_name in self._active_alerts:
                alert = self._active_alerts[rule_name]
                if alert.state == AlertState.ACTIVE:
                    alert.state = AlertState.ACKNOWLEDGED
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = time.time()

                    # 发布事件
                    publish_event("performance_alert_acknowledged", alert.to_dict())

                    logger.info(f"Alert acknowledged: {rule_name} by {acknowledged_by}")
                    return True
        return False

    def suppress_alert(self, rule_name: str, reason: str) -> bool:
        """抑制告警"""
        with self._lock:
            if rule_name in self._active_alerts:
                alert = self._active_alerts[rule_name]
                alert.state = AlertState.SUPPRESSED
                alert.description += f" (Suppressed: {reason})"

                self._stats["active_alerts"] -= 1
                self._stats["suppressed_alerts"] += 1

                # 发布事件
                publish_event("performance_alert_suppressed", alert.to_dict())

                logger.info(f"Alert suppressed: {rule_name} - {reason}")
                return True
        return False

    def _notify_user(self, alert: Alert) -> None:
        """通知用户（在测试环境中避免弹出 GUI）"""
        try:
            import os

            # 在 pytest 等非 GUI 环境中仅记录日志，避免 Qt 弹窗导致崩溃
            if os.environ.get("PYTEST_CURRENT_TEST"):
                logger.info(
                    "Performance alert (test mode): "
                    f"{alert.description} value={alert.current_value:.2f} "
                    f"threshold={alert.threshold:.2f} metric={alert.metric_name}"
                )
                return

            from PySide6.QtWidgets import QMessageBox

            severity_map = {
                AlertSeverity.INFO: QMessageBox.Information,
                AlertSeverity.WARNING: QMessageBox.Warning,
                AlertSeverity.ERROR: QMessageBox.Critical,
                AlertSeverity.CRITICAL: QMessageBox.Critical,
            }

            icon = severity_map.get(alert.severity, QMessageBox.Warning)

            QMessageBox(
                icon,
                "性能告警",
                f"{alert.description}\n\n"
                f"当前值: {alert.current_value:.2f}\n"
                f"阈值: {alert.threshold:.2f}\n"
                f"指标: {alert.metric_name}",
            ).exec()

        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

    def _auto_optimize(self, alert: Alert) -> None:
        """自动优化"""
        try:
            if alert.metric_name == MetricType.CPU_USAGE.value:
                # CPU优化
                import gc
                gc.collect()
                logger.info("Performed CPU optimization")

            elif alert.metric_name == MetricType.MEMORY_USAGE.value:
                # 内存优化
                import gc
                gc.collect()
                logger.info("Performed memory optimization")

        except Exception as e:
            logger.error(f"Auto optimization failed: {e}")

    def _escalate_critical(self, alert: Alert) -> None:
        """升级严重告警"""
        try:
            # 发布严重告警事件
            publish_event("critical_performance_alert", alert.to_dict(), priority=EventPriority.CRITICAL)

            # 记录到日志
            logger.critical(f"Critical performance alert escalated: {alert.rule_name}")

        except Exception as e:
            logger.error(f"Failed to escalate critical alert: {e}")

    def get_active_alerts(self) -> Dict[str, Alert]:
        """获取活跃告警"""
        with self._lock:
            return {name: alert for name, alert in self._active_alerts.items()
                   if alert.state == AlertState.ACTIVE}

    def get_alert_history(self, limit: Optional[int] = None) -> List[Alert]:
        """获取告警历史"""
        with self._lock:
            if limit:
                return self._alert_history[-limit:]
            return self._alert_history.copy()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return self._stats.copy()

    def clear_stats(self) -> None:
        """清除统计信息"""
        with self._lock:
            self._stats = {
                "total_alerts": 0,
                "active_alerts": 0,
                "resolved_alerts": 0,
                "suppressed_alerts": 0,
                "actions_triggered": 0
            }

    def get_rule_count(self) -> int:
        """获取规则数量"""
        return len(self._rules)

    def get_action_count(self) -> int:
        """获取动作数量"""
        return len(self._actions)


# 全局性能告警系统实例
_global_performance_alerting = PerformanceAlerting()


def get_performance_alerting() -> PerformanceAlerting:
    """获取全局性能告警系统"""
    return _global_performance_alerting


def check_performance_metric(metric: PerformanceMetric) -> None:
    """检查性能指标"""
    _global_performance_alerting.check_metric(metric)


def add_alert_rule(rule: AlertRule) -> None:
    """添加告警规则"""
    _global_performance_alerting.add_rule(rule)


def acknowledge_alert(rule_name: str, acknowledged_by: str) -> bool:
    """确认告警"""
    return _global_performance_alerting.acknowledge_alert(rule_name, acknowledged_by)
