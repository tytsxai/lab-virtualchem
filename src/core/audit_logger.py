"""
审计日志模块

用于记录和审计所有关键操作
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型"""

    # 许可证相关
    LICENSE_GENERATED = "license_generated"
    LICENSE_ACTIVATED = "license_activated"
    LICENSE_VALIDATED = "license_validated"
    LICENSE_REVOKED = "license_revoked"
    LICENSE_EXPIRED = "license_expired"

    # 设备相关
    DEVICE_REGISTERED = "device_registered"
    DEVICE_BLOCKED = "device_blocked"
    DEVICE_UNBLOCKED = "device_unblocked"
    DEVICE_VALIDATION_FAILED = "device_validation_failed"

    # 认证相关
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    AUTH_DENIED = "auth_denied"

    # 异常相关
    ANOMALY_DETECTED = "anomaly_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # 管理操作
    ADMIN_LOGIN = "admin_login"
    ADMIN_ACTION = "admin_action"

    # IP相关
    IP_TRACKED = "ip_tracked"
    IP_MARKED_SUSPICIOUS = "ip_marked_suspicious"


class AuditLevel(Enum):
    """审计级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""

    event_type: AuditEventType  # 事件类型
    timestamp: datetime  # 时间戳
    level: AuditLevel  # 级别
    license_key: str | None  # 许可证密钥
    device_id: str | None  # 设备ID
    ip_address: str | None  # IP地址
    user_info: dict[str, Any] | None  # 用户信息
    action: str  # 操作描述
    result: str  # 结果
    details: dict[str, Any] | None  # 详细信息

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["level"] = self.level.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEvent":
        """从字典创建"""
        data["event_type"] = AuditEventType(data["event_type"])
        data["level"] = AuditLevel(data["level"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, storage_path: Path | None = None):
        """初始化

        Args:
            storage_path: 存储路径
        """
        if storage_path is None:
            storage_path = Path("logs") / "audit"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 按日期分文件存储
        self._current_date = datetime.now().date()
        self._current_log_file = self._get_log_file()

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        result: str,
        level: AuditLevel = AuditLevel.INFO,
        license_key: str | None = None,
        device_id: str | None = None,
        ip_address: str | None = None,
        user_info: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录审计事件

        Args:
            event_type: 事件类型
            action: 操作描述
            result: 结果
            level: 级别
            license_key: 许可证密钥
            device_id: 设备ID
            ip_address: IP地址
            user_info: 用户信息
            details: 详细信息
        """
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            level=level,
            license_key=license_key,
            device_id=device_id,
            ip_address=ip_address,
            user_info=user_info,
            action=action,
            result=result,
            details=details,
        )

        # 写入日志文件
        self._write_event(event)

        # 同时写入系统日志
        log_message = f"[AUDIT] {event.action} - {event.result}"
        if level == AuditLevel.INFO:
            logger.info(log_message)
        elif level == AuditLevel.WARNING:
            logger.warning(log_message)
        elif level == AuditLevel.ERROR:
            logger.error(log_message)
        elif level == AuditLevel.CRITICAL:
            logger.critical(log_message)

    def log_license_generated(
        self, license_key: str, user_info: dict[str, Any], details: dict[str, Any]
    ) -> None:
        """记录许可证生成"""
        self.log_event(
            event_type=AuditEventType.LICENSE_GENERATED,
            action=f"生成许可证 {license_key}",
            result="成功",
            license_key=license_key,
            user_info=user_info,
            details=details,
        )

    def log_license_activated(
        self, license_key: str, device_id: str, ip_address: str | None = None
    ) -> None:
        """记录许可证激活"""
        self.log_event(
            event_type=AuditEventType.LICENSE_ACTIVATED,
            action=f"激活许可证 {license_key}",
            result="成功",
            license_key=license_key,
            device_id=device_id,
            ip_address=ip_address,
        )

    def log_license_validated(
        self,
        license_key: str,
        device_id: str,
        success: bool,
        reason: str = "",
        ip_address: str | None = None,
    ) -> None:
        """记录许可证验证"""
        self.log_event(
            event_type=AuditEventType.LICENSE_VALIDATED,
            action=f"验证许可证 {license_key}",
            result="成功" if success else f"失败: {reason}",
            level=AuditLevel.INFO if success else AuditLevel.WARNING,
            license_key=license_key,
            device_id=device_id,
            ip_address=ip_address,
        )

    def log_device_blocked(
        self, device_id: str, reason: str, operator: str | None = None
    ) -> None:
        """记录设备封控"""
        self.log_event(
            event_type=AuditEventType.DEVICE_BLOCKED,
            action=f"封控设备 {device_id}",
            result=f"原因: {reason}",
            level=AuditLevel.WARNING,
            device_id=device_id,
            details={"operator": operator} if operator else None,
        )

    def log_device_unblocked(self, device_id: str, operator: str | None = None) -> None:
        """记录设备解封"""
        self.log_event(
            event_type=AuditEventType.DEVICE_UNBLOCKED,
            action=f"解封设备 {device_id}",
            result="成功",
            device_id=device_id,
            details={"operator": operator} if operator else None,
        )

    def log_anomaly_detected(
        self,
        anomaly_type: str,
        severity: str,
        message: str,
        license_key: str | None = None,
        device_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录异常检测"""
        level_map = {
            "low": AuditLevel.INFO,
            "medium": AuditLevel.WARNING,
            "high": AuditLevel.ERROR,
            "critical": AuditLevel.CRITICAL,
        }

        self.log_event(
            event_type=AuditEventType.ANOMALY_DETECTED,
            action=f"检测到异常: {anomaly_type}",
            result=message,
            level=level_map.get(severity.lower(), AuditLevel.WARNING),
            license_key=license_key,
            device_id=device_id,
            details=details,
        )

    def log_admin_action(
        self,
        action: str,
        operator: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录管理员操作"""
        self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            action=f"管理员操作: {action}",
            result=result,
            user_info={"operator": operator},
            details=details,
        )

    def get_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_type: AuditEventType | None = None,
        level: AuditLevel | None = None,
        license_key: str | None = None,
        device_id: str | None = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """查询审计事件

        Args:
            start_date: 开始日期
            end_date: 结束日期
            event_type: 事件类型
            level: 级别
            license_key: 许可证密钥
            device_id: 设备ID
            limit: 限制数量

        Returns:
            事件列表
        """
        events = []

        # 如果没有指定日期范围，使用当前日志文件
        if start_date is None and end_date is None:
            log_files = [self._current_log_file]
        else:
            # 获取日期范围内的所有日志文件
            log_files = self._get_log_files_in_range(start_date, end_date)

        # 读取日志文件
        for log_file in log_files:
            if not log_file.exists():
                continue

            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event = AuditEvent.from_dict(event_data)

                            # 过滤
                            if event_type and event.event_type != event_type:
                                continue
                            if level and event.level != level:
                                continue
                            if license_key and event.license_key != license_key:
                                continue
                            if device_id and event.device_id != device_id:
                                continue

                            events.append(event)

                            if len(events) >= limit:
                                break
                        except Exception as e:
                            logger.debug(f"解析事件失败: {e}")
                            continue

                if len(events) >= limit:
                    break

            except Exception as e:
                logger.error(f"读取日志文件失败 {log_file}: {e}")

        return events[-limit:]

    def get_statistics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """获取统计信息

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计信息
        """
        events = self.get_events(start_date=start_date, end_date=end_date, limit=100000)

        # 按类型统计
        event_types: dict[str, int] = {}
        for event in events:
            event_type = event.event_type.value
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # 按级别统计
        levels: dict[str, int] = {}
        for event in events:
            level = event.level.value
            levels[level] = levels.get(level, 0) + 1

        # 活跃许可证
        active_licenses = {e.license_key for e in events if e.license_key}

        # 活跃设备
        active_devices = {e.device_id for e in events if e.device_id}

        return {
            "total_events": len(events),
            "event_types": event_types,
            "levels": levels,
            "active_licenses": len(active_licenses),
            "active_devices": len(active_devices),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    def _write_event(self, event: AuditEvent) -> None:
        """写入事件到日志文件"""
        # 检查是否需要轮转日志文件
        current_date = datetime.now().date()
        if current_date != self._current_date:
            self._current_date = current_date
            self._current_log_file = self._get_log_file()

        try:
            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"写入审计日志失败: {e}")

    def _get_log_file(self, date: datetime | None = None) -> Path:
        """获取日志文件路径"""
        if date is None:
            date = datetime.now()

        filename = f"audit_{date.strftime('%Y%m%d')}.jsonl"
        return self.storage_path / filename

    def _get_log_files_in_range(
        self, start_date: datetime | None, end_date: datetime | None
    ) -> list[Path]:
        """获取日期范围内的日志文件"""
        log_files = []

        if start_date is None:
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        if end_date is None:
            end_date = datetime.now()

        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            log_file = self._get_log_file(
                datetime.combine(current_date, datetime.min.time())
            )
            if log_file.exists():
                log_files.append(log_file)

            from datetime import timedelta

            current_date += timedelta(days=1)

        return log_files


# 全局实例
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
