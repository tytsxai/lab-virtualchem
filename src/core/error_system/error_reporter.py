"""
错误报告和通知系统

提供错误报告、用户通知、邮件/API通知等功能
"""

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .exceptions import BaseAppException

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """通知级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """通知渠道"""

    LOG = "log"  # 日志
    UI = "ui"  # 界面通知
    EMAIL = "email"  # 邮件
    WEBHOOK = "webhook"  # Webhook
    CONSOLE = "console"  # 控制台


@dataclass
class ErrorReport:
    """错误报告"""

    report_id: str
    timestamp: datetime
    error_code: int
    error_type: str
    message: str
    user_message: str
    context: str
    user_id: str | None
    session_id: str | None
    severity: str
    recoverable: bool
    details: dict[str, Any]
    traceback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ErrorReporter:
    """错误报告器"""

    def __init__(self, report_dir: Path | None = None):
        """
        初始化错误报告器

        Args:
            report_dir: 报告目录
        """
        self.report_dir = report_dir or Path("logs/error_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self._notification_handlers: dict[NotificationChannel, list[Callable]] = {
            channel: [] for channel in NotificationChannel
        }
        self._report_history: list[ErrorReport] = []
        self.max_history = 1000

    def report_error(
        self,
        exception: BaseAppException,
        context: str = "",
        user_id: str | None = None,
        session_id: str | None = None,
        notify: bool = True,
        notification_channels: list[NotificationChannel] | None = None,
    ) -> ErrorReport:
        """
        报告错误

        Args:
            exception: 异常对象
            context: 上下文信息
            user_id: 用户ID
            session_id: 会话ID
            notify: 是否发送通知
            notification_channels: 通知渠道

        Returns:
            错误报告对象
        """
        # 生成报告ID
        report_id = self._generate_report_id()

        # 创建错误报告
        report = ErrorReport(
            report_id=report_id,
            timestamp=datetime.now(),
            error_code=exception.error_code.code,
            error_type=exception.error_code.name,
            message=exception.message,
            user_message=exception.user_message,
            context=context,
            user_id=user_id,
            session_id=session_id,
            severity=exception.error_code.severity,
            recoverable=exception.error_code.recoverable,
            details=exception.details,
            traceback=exception.traceback,
        )

        # 保存报告
        self._save_report(report)

        # 添加到历史
        self._report_history.append(report)
        if len(self._report_history) > self.max_history:
            self._report_history.pop(0)

        # 发送通知
        if notify:
            self._send_notifications(report, notification_channels)

        return report

    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import hashlib

        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:16]

    def _save_report(self, report: ErrorReport) -> None:
        """保存报告到文件"""
        try:
            # 按日期分组
            date_str = report.timestamp.strftime("%Y%m%d")
            report_file = self.report_dir / f"error_reports_{date_str}.jsonl"

            # 追加写入
            with open(report_file, "a", encoding="utf-8") as f:
                f.write(report.to_json() + "\n")

        except Exception as e:
            logger.error(f"Failed to save error report: {e}")

    def _send_notifications(
        self,
        report: ErrorReport,
        channels: list[NotificationChannel] | None = None,
    ) -> None:
        """
        发送通知

        Args:
            report: 错误报告
            channels: 通知渠道（如果为None，则使用所有已注册的渠道）
        """
        # 确定通知渠道
        if channels is None:
            channels = list(self._notification_handlers.keys())

        # 根据严重程度决定通知级别
        notification_level = self._get_notification_level(report.severity)

        # 发送通知
        for channel in channels:
            handlers = self._notification_handlers.get(channel, [])
            for handler in handlers:
                try:
                    handler(report, notification_level)
                except Exception as e:
                    logger.error(f"Notification handler failed ({channel}): {e}")

    def _get_notification_level(self, severity: str) -> NotificationLevel:
        """根据严重程度获取通知级别"""
        mapping = {
            "info": NotificationLevel.INFO,
            "warning": NotificationLevel.WARNING,
            "error": NotificationLevel.ERROR,
            "critical": NotificationLevel.CRITICAL,
        }
        return mapping.get(severity, NotificationLevel.ERROR)

    def register_notification_handler(
        self,
        channel: NotificationChannel,
        handler: Callable[[ErrorReport, NotificationLevel], None],
    ) -> None:
        """
        注册通知处理器

        Args:
            channel: 通知渠道
            handler: 处理器函数，签名为 (report, level) -> None
        """
        self._notification_handlers[channel].append(handler)

    def get_reports(
        self,
        limit: int = 100,
        severity: str | None = None,
        user_id: str | None = None,
    ) -> list[ErrorReport]:
        """
        获取错误报告

        Args:
            limit: 返回数量
            severity: 严重程度筛选
            user_id: 用户ID筛选

        Returns:
            错误报告列表
        """
        reports = self._report_history.copy()

        # 应用筛选
        if severity:
            reports = [r for r in reports if r.severity == severity]

        if user_id:
            reports = [r for r in reports if r.user_id == user_id]

        # 返回最近的记录
        return reports[-limit:]

    def get_report_stats(self) -> dict[str, Any]:
        """获取报告统计"""
        total_reports = len(self._report_history)

        # 按严重程度统计
        by_severity: dict[str, int] = {}
        for report in self._report_history:
            severity = report.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # 按错误码统计
        by_code: dict[int, int] = {}
        for report in self._report_history:
            code = report.error_code
            by_code[code] = by_code.get(code, 0) + 1

        # 按用户统计
        by_user: dict[str, int] = {}
        for report in self._report_history:
            if report.user_id:
                by_user[report.user_id] = by_user.get(report.user_id, 0) + 1

        return {
            "total_reports": total_reports,
            "by_severity": by_severity,
            "by_code": by_code,
            "by_user": by_user,
        }

    def export_reports(self, filepath: str, format: str = "json") -> None:
        """
        导出报告

        Args:
            filepath: 文件路径
            format: 导出格式 (json/csv/html)
        """
        try:
            if format == "json":
                self._export_json(filepath)
            elif format == "csv":
                self._export_csv(filepath)
            elif format == "html":
                self._export_html(filepath)
            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Failed to export reports: {e}")

    def _export_json(self, filepath: str) -> None:
        """导出为JSON"""
        data = {
            "export_time": datetime.now().isoformat(),
            "total_reports": len(self._report_history),
            "reports": [r.to_dict() for r in self._report_history],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _export_csv(self, filepath: str) -> None:
        """导出为CSV"""
        import csv

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            if not self._report_history:
                return

            # 写入表头
            fieldnames = [
                "report_id",
                "timestamp",
                "error_code",
                "error_type",
                "message",
                "severity",
                "user_id",
                "context",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # 写入数据
            for report in self._report_history:
                row = {
                    "report_id": report.report_id,
                    "timestamp": report.timestamp.isoformat(),
                    "error_code": report.error_code,
                    "error_type": report.error_type,
                    "message": report.message,
                    "severity": report.severity,
                    "user_id": report.user_id or "",
                    "context": report.context,
                }
                writer.writerow(row)

    def _export_html(self, filepath: str) -> None:
        """导出为HTML"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>错误报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .error {{ color: #f57c00; }}
        .warning {{ color: #fbc02d; }}
        .info {{ color: #1976d2; }}
    </style>
</head>
<body>
    <h1>错误报告</h1>
    <p>导出时间: {export_time}</p>
    <p>总报告数: {total_reports}</p>

    <table>
        <tr>
            <th>时间</th>
            <th>错误码</th>
            <th>错误类型</th>
            <th>消息</th>
            <th>严重程度</th>
            <th>用户ID</th>
            <th>上下文</th>
        </tr>
        {rows}
    </table>
</body>
</html>
"""

        rows_html = ""
        for _report in self._report_history:
            rows_html += """
        <tr>
            <td>{report.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</td>
            <td>{report.error_code}</td>
            <td>{report.error_type}</td>
            <td>{report.message}</td>
            <td class="{severity_class}">{report.severity}</td>
            <td>{report.user_id or "-"}</td>
            <td>{report.context}</td>
        </tr>
"""

        html_content = html_template.format(
            export_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_reports=len(self._report_history),
            rows=rows_html,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)


# 全局错误报告器实例
error_reporter = ErrorReporter()


# 便捷的通知处理器


def console_notification_handler(report: ErrorReport, level: NotificationLevel) -> None:
    """控制台通知处理器"""
    icon = {
        "info": "[INFO]",
        "warning": "[WARN]",
        "error": "[ERROR]",
        "critical": "[CRITICAL]",
    }.get(level.value, "[*]")

    try:
        print(f"\n{icon} [{report.error_type}] {report.user_message}")
        print(f"   时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.context:
            print(f"   上下文: {report.context}")
        if report.details:
            print(f"   详细: {report.details}")
        print()
    except UnicodeEncodeError:
        # Windows控制台编码问题，使用ASCII安全输出
        print(f"\n{icon} [{report.error_type}] {report.user_message.encode('ascii', 'ignore').decode('ascii')}")
        print(f"   Time: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")


def log_notification_handler(report: ErrorReport, level: NotificationLevel) -> None:
    """日志通知处理器"""
    log_message = f"[{report.error_type}] {report.message} " f"(context: {report.context}, user: {report.user_id})"

    if level == NotificationLevel.CRITICAL:
        logger.critical(log_message)
    elif level == NotificationLevel.ERROR:
        logger.error(log_message)
    elif level == NotificationLevel.WARNING:
        logger.warning(log_message)
    else:
        logger.info(log_message)


# 注册默认通知处理器
error_reporter.register_notification_handler(NotificationChannel.CONSOLE, console_notification_handler)
error_reporter.register_notification_handler(NotificationChannel.LOG, log_notification_handler)
