#!/usr/bin/env python3
"""
VirtualChemLab 系统监控与告警系统
实时监控系统健康状态，及时发现问题并发送告警
"""

import time
import psutil
import threading
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# 项目导入
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """监控指标"""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    status: HealthStatus
    timestamp: datetime


@dataclass
class Alert:
    """告警信息"""
    id: str
    level: AlertLevel
    title: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.process = psutil.Process()
        self.metrics: Dict[str, Metric] = {}
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_history: List[Alert] = []

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def get_memory_metric(self) -> Metric:
        """获取内存使用指标"""
        memory = psutil.virtual_memory()
        usage_percent = memory.percent

        if usage_percent > 90:
            status = HealthStatus.CRITICAL
        elif usage_percent > 80:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return Metric(
            name="memory_usage",
            value=usage_percent,
            unit="%",
            threshold_warning=80.0,
            threshold_critical=90.0,
            status=status,
            timestamp=datetime.now()
        )

    def get_cpu_metric(self) -> Metric:
        """获取CPU使用指标"""
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 90:
            status = HealthStatus.CRITICAL
        elif cpu_percent > 80:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return Metric(
            name="cpu_usage",
            value=cpu_percent,
            unit="%",
            threshold_warning=80.0,
            threshold_critical=90.0,
            status=status,
            timestamp=datetime.now()
        )

    def get_disk_metric(self) -> Metric:
        """获取磁盘使用指标"""
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100

        if usage_percent > 95:
            status = HealthStatus.CRITICAL
        elif usage_percent > 85:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return Metric(
            name="disk_usage",
            value=usage_percent,
            unit="%",
            threshold_warning=85.0,
            threshold_critical=95.0,
            status=status,
            timestamp=datetime.now()
        )

    def get_process_memory_metric(self) -> Metric:
        """获取进程内存使用指标"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        # 进程内存阈值（相对宽松）
        if memory_mb > 1000:  # 1GB
            status = HealthStatus.CRITICAL
        elif memory_mb > 500:  # 500MB
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return Metric(
            name="process_memory",
            value=memory_mb,
            unit="MB",
            threshold_warning=500.0,
            threshold_critical=1000.0,
            status=status,
            timestamp=datetime.now()
        )

    def get_all_metrics(self) -> Dict[str, Metric]:
        """获取所有监控指标"""
        metrics = {
            "memory_usage": self.get_memory_metric(),
            "cpu_usage": self.get_cpu_metric(),
            "disk_usage": self.get_disk_metric(),
            "process_memory": self.get_process_memory_metric()
        }

        self.metrics.update(metrics)
        return metrics

    def check_alerts(self):
        """检查告警条件"""
        for metric_name, metric in self.metrics.items():
            # 检查是否需要生成告警
            if metric.status == HealthStatus.CRITICAL:
                self._create_alert(
                    level=AlertLevel.CRITICAL,
                    title=f"严重告警: {metric_name}",
                    message=f"{metric_name} 达到临界值: {metric.value}{metric.unit}",
                    metric_name=metric_name,
                    metric_value=metric.value,
                    threshold=metric.threshold_critical
                )
            elif metric.status == HealthStatus.WARNING:
                self._create_alert(
                    level=AlertLevel.WARNING,
                    title=f"警告: {metric_name}",
                    message=f"{metric_name} 超过警告阈值: {metric.value}{metric.unit}",
                    metric_name=metric_name,
                    metric_value=metric.value,
                    threshold=metric.threshold_warning
                )

    def _create_alert(self, level: AlertLevel, title: str, message: str,
                     metric_name: str, metric_value: float, threshold: float):
        """创建告警"""
        alert_id = f"{metric_name}_{int(time.time())}"

        # 检查是否已存在相同告警
        existing_alert = None
        for alert in self.alerts:
            if (alert.metric_name == metric_name and
                alert.level == level and
                not alert.resolved):
                existing_alert = alert
                break

        if existing_alert:
            # 更新现有告警
            existing_alert.message = message
            existing_alert.metric_value = metric_value
            existing_alert.timestamp = datetime.now()
        else:
            # 创建新告警
            alert = Alert(
                id=alert_id,
                level=level,
                title=title,
                message=message,
                metric_name=metric_name,
                metric_value=metric_value,
                threshold=threshold,
                timestamp=datetime.now()
            )

            self.alerts.append(alert)
            self.alert_history.append(alert)

            # 触发告警回调
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {e}")

            logger.warning(f"新告警: {title} - {message}")

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"告警已解决: {alert.title}")
                break

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康摘要"""
        metrics = self.get_all_metrics()

        critical_count = sum(1 for m in metrics.values() if m.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for m in metrics.values() if m.status == HealthStatus.WARNING)

        overall_status = HealthStatus.CRITICAL if critical_count > 0 else (
            HealthStatus.WARNING if warning_count > 0 else HealthStatus.HEALTHY
        )

        active_alerts = [a for a in self.alerts if not a.resolved]

        return {
            "overall_status": overall_status.value,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "active_alerts": len(active_alerts),
            "total_alerts": len(self.alerts),
            "timestamp": datetime.now().isoformat(),
            "metrics": {name: asdict(metric) for name, metric in metrics.items()}
        }

    def start_monitoring(self, interval: int = 60):
        """开始监控"""
        if self.monitoring:
            logger.warning("监控已在运行")
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"系统监控已启动，检查间隔: {interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("系统监控已停止")

    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取指标
                self.get_all_metrics()

                # 检查告警
                self.check_alerts()

                # 清理过期告警
                self._cleanup_expired_alerts()

                # 等待下次检查
                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(interval)

    def _cleanup_expired_alerts(self):
        """清理过期告警"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        # 移除24小时前的已解决告警
        self.alerts = [a for a in self.alerts if not a.resolved or a.timestamp > cutoff_time]

        # 限制告警历史数量
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

    def save_metrics(self, filename: str = "system_metrics.json"):
        """保存指标到文件"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {name: asdict(metric) for name, metric in self.metrics.items()},
            "alerts": [asdict(alert) for alert in self.alerts if not alert.resolved]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"指标已保存到: {filename}")


class EmailAlertHandler:
    """邮件告警处理器"""

    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str, recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients

    def send_alert(self, alert: Alert):
        """发送告警邮件"""
        try:
            # 创建邮件
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[VirtualChemLab] {alert.title}"

            # 邮件内容
            body = f"""
告警详情:
- 级别: {alert.level.value.upper()}
- 指标: {alert.metric_name}
- 当前值: {alert.metric_value}
- 阈值: {alert.threshold}
- 时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- 消息: {alert.message}

请及时处理此告警。

VirtualChemLab 监控系统
            """

            msg.attach(MimeText(body, 'plain', 'utf-8'))

            # 发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"告警邮件已发送: {alert.title}")

        except Exception as e:
            logger.error(f"发送告警邮件失败: {e}")


class LogAlertHandler:
    """日志告警处理器"""

    def __init__(self, log_file: str = "alerts.log"):
        self.log_file = log_file

    def send_alert(self, alert: Alert):
        """记录告警到日志文件"""
        try:
            log_entry = {
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold
            }

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            logger.info(f"告警已记录到日志: {alert.title}")

        except Exception as e:
            logger.error(f"记录告警日志失败: {e}")


class WebhookAlertHandler:
    """Webhook告警处理器"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, alert: Alert):
        """发送告警到Webhook"""
        try:
            import requests

            payload = {
                "text": f"🚨 {alert.title}",
                "attachments": [
                    {
                        "color": "danger" if alert.level == AlertLevel.CRITICAL else "warning",
                        "fields": [
                            {"title": "级别", "value": alert.level.value.upper(), "short": True},
                            {"title": "指标", "value": alert.metric_name, "short": True},
                            {"title": "当前值", "value": f"{alert.metric_value}", "short": True},
                            {"title": "阈值", "value": f"{alert.threshold}", "short": True},
                            {"title": "时间", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True},
                            {"title": "消息", "value": alert.message, "short": False}
                        ]
                    }
                ]
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"告警已发送到Webhook: {alert.title}")

        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")


def main():
    """主函数"""
    print("VirtualChemLab 系统监控与告警系统")
    print("=" * 60)

    # 创建系统监控器
    monitor = SystemMonitor()

    # 添加告警处理器
    log_handler = LogAlertHandler()
    monitor.add_alert_callback(log_handler.send_alert)

    # 可选：添加邮件告警处理器
    # email_handler = EmailAlertHandler(
    #     smtp_server="smtp.gmail.com",
    #     smtp_port=587,
    #     username="your_email@gmail.com",
    #     password="your_password",
    #     recipients=["admin@example.com"]
    # )
    # monitor.add_alert_callback(email_handler.send_alert)

    # 可选：添加Webhook告警处理器
    # webhook_handler = WebhookAlertHandler("https://hooks.slack.com/services/...")
    # monitor.add_alert_callback(webhook_handler.send_alert)

    # 启动监控
    monitor.start_monitoring(interval=30)  # 30秒检查一次

    try:
        # 运行监控
        while True:
            # 获取健康摘要
            summary = monitor.get_health_summary()
            print(f"系统状态: {summary['overall_status']}")
            print(f"活跃告警: {summary['active_alerts']}")

            # 保存指标
            monitor.save_metrics()

            # 等待5分钟
            time.sleep(300)

    except KeyboardInterrupt:
        print("\n正在停止监控...")
        monitor.stop_monitoring()
        print("监控已停止")


if __name__ == "__main__":
    main()
