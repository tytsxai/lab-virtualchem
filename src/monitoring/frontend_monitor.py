"""
前端监控模块

功能:
- 错误追踪 (类似Sentry)
- 用户行为埋点
- 点击流分析
- 性能监控
"""

import hashlib
import json
import logging
import threading
import time
import traceback
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .log_safety import sanitize_log_data

logger = logging.getLogger(__name__)


class ErrorLevel(Enum):
    """错误级别"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class EventType(Enum):
    """事件类型"""

    CLICK = "click"
    VIEW = "view"
    INPUT = "input"
    SUBMIT = "submit"
    NAVIGATION = "navigation"
    CUSTOM = "custom"


@dataclass
class ErrorReport:
    """错误报告"""

    error_id: str
    level: ErrorLevel
    message: str
    exception_type: str
    stacktrace: str
    timestamp: datetime
    user_id: str | None = None
    session_id: str | None = None
    component: str | None = None
    action: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["level"] = self.level.value
        return data


@dataclass
class UserEvent:
    """用户事件"""

    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: str | None = None
    session_id: str | None = None
    component: str = ""
    action: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        return data


class FrontendMonitor:
    """前端监控器 - 错误追踪"""

    def __init__(
        self,
        app_name: str = "VirtualChemLab",
        log_dir: Path | None = None,
        max_errors: int = 1000,
    ):
        self.app_name = app_name
        self.log_dir = log_dir or Path("logs/frontend")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._error_handlers: list[Callable] = []

    def capture_exception(
        self,
        exception: Exception,
        level: ErrorLevel = ErrorLevel.ERROR,
        user_id: str | None = None,
        session_id: str | None = None,
        component: str | None = None,
        action: str | None = None,
        **context,
    ) -> str:
        """
        捕获异常

        Args:
            exception: 异常对象
            level: 错误级别
            user_id: 用户ID
            session_id: 会话ID
            component: 组件名称
            action: 操作名称
            **context: 额外上下文信息

        Returns:
            错误ID
        """
        error_id = self._generate_error_id(exception)

        error_report = ErrorReport(
            error_id=error_id,
            level=level,
            message=str(exception),
            exception_type=type(exception).__name__,
            stacktrace=traceback.format_exc(),
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            component=component,
            action=action,
            context=context,
        )

        with self._lock:
            self._errors.append(error_report)
            self._error_counts[error_id] = self._error_counts.get(error_id, 0) + 1

        # 写入日志文件
        self._write_error_log(error_report)

        # 触发错误处理器
        for handler in self._error_handlers:
            try:
                handler(error_report)
            except Exception as e:
                logger.info(sanitize_log_data(f"错误处理器失败: {e}"))

        return error_id

    def capture_message(
        self, message: str, level: ErrorLevel = ErrorLevel.INFO, **context
    ) -> None:
        """捕获消息"""
        try:
            # 创建一个临时异常来获取堆栈
            raise Exception(message)
        except Exception as e:
            self.capture_exception(e, level=level, **context)

    def add_error_handler(self, handler: Callable) -> None:
        """添加错误处理器"""
        self._error_handlers.append(handler)

    def get_errors(
        self, limit: int = 100, level: ErrorLevel | None = None
    ) -> list[ErrorReport]:
        """获取错误列表"""
        with self._lock:
            errors = list(self._errors)

        if level:
            errors = [e for e in errors if e.level == level]

        return errors[-limit:]

    def get_error_stats(self) -> dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            total_errors = len(self._errors)
            unique_errors = len(self._error_counts)

            # 按级别统计
            by_level = {}
            for error in self._errors:
                level = error.level.value
                by_level[level] = by_level.get(level, 0) + 1

            # 按组件统计
            by_component = {}
            for error in self._errors:
                if error.component:
                    by_component[error.component] = (
                        by_component.get(error.component, 0) + 1
                    )

            # 最常见错误
            top_errors = sorted(
                self._error_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]

        return {
            "total_errors": total_errors,
            "unique_errors": unique_errors,
            "by_level": by_level,
            "by_component": by_component,
            "top_errors": [
                {"error_id": eid, "count": count} for eid, count in top_errors
            ],
        }

    def clear_errors(self) -> None:
        """清除错误记录"""
        with self._lock:
            self._errors.clear()
            self._error_counts.clear()

    def _generate_error_id(self, exception: Exception) -> str:
        """生成错误ID"""
        # 使用异常类型和消息生成唯一ID
        content = f"{type(exception).__name__}:{str(exception)}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def _write_error_log(self, error: ErrorReport) -> None:
        """写入错误日志"""
        try:
            log_file = (
                self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.info(sanitize_log_data(f"写入错误日志失败: {e}"))


class UserBehaviorTracker:
    """用户行为跟踪器 - 点击流分析"""

    def __init__(self, log_dir: Path | None = None, max_events: int = 10000):
        self.log_dir = log_dir or Path("logs/behavior")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._events: deque = deque(maxlen=max_events)
        self._sessions: dict[str, list[UserEvent]] = {}
        self._lock = threading.Lock()

    def track_event(
        self,
        event_type: EventType,
        component: str,
        action: str,
        user_id: str | None = None,
        session_id: str | None = None,
        duration_ms: float | None = None,
        **properties,
    ) -> str:
        """
        追踪事件

        Args:
            event_type: 事件类型
            component: 组件名称
            action: 操作名称
            user_id: 用户ID
            session_id: 会话ID
            duration_ms: 持续时间(毫秒)
            **properties: 事件属性

        Returns:
            事件ID
        """
        event_id = self._generate_event_id()

        event = UserEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            component=component,
            action=action,
            properties=properties,
            duration_ms=duration_ms,
        )

        with self._lock:
            self._events.append(event)

            # 按会话分组
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                self._sessions[session_id].append(event)

        # 写入日志
        self._write_event_log(event)

        return event_id

    def track_click(self, component: str, element: str, **kwargs) -> str:
        """追踪点击事件"""
        return self.track_event(
            EventType.CLICK,
            component=component,
            action="click",
            element=element,
            **kwargs,
        )

    def track_view(
        self, component: str, duration_ms: float | None = None, **kwargs
    ) -> str:
        """追踪页面查看"""
        return self.track_event(
            EventType.VIEW,
            component=component,
            action="view",
            duration_ms=duration_ms,
            **kwargs,
        )

    def track_navigation(self, from_page: str, to_page: str, **kwargs) -> str:
        """追踪导航"""
        return self.track_event(
            EventType.NAVIGATION,
            component="navigation",
            action="navigate",
            from_page=from_page,
            to_page=to_page,
            **kwargs,
        )

    def get_session_events(self, session_id: str) -> list[UserEvent]:
        """获取会话事件"""
        with self._lock:
            return self._sessions.get(session_id, []).copy()

    def get_event_stats(self) -> dict[str, Any]:
        """获取事件统计"""
        with self._lock:
            total_events = len(self._events)

            # 按类型统计
            by_type = {}
            for event in self._events:
                event_type = event.event_type.value
                by_type[event_type] = by_type.get(event_type, 0) + 1

            # 按组件统计
            by_component = {}
            for event in self._events:
                by_component[event.component] = by_component.get(event.component, 0) + 1

            # 活跃会话
            active_sessions = len(self._sessions)

        return {
            "total_events": total_events,
            "by_type": by_type,
            "by_component": by_component,
            "active_sessions": active_sessions,
        }

    def analyze_clickstream(self, session_id: str | None = None) -> dict[str, Any]:
        """分析点击流"""
        if session_id:
            events = self.get_session_events(session_id)
        else:
            with self._lock:
                events = list(self._events)

        if not events:
            return {}

        # 构建点击流路径
        path = []
        for event in events:
            path.append(f"{event.component}/{event.action}")

        # 计算常见路径
        path_counts = {}
        for i in range(len(path) - 1):
            transition = f"{path[i]} -> {path[i + 1]}"
            path_counts[transition] = path_counts.get(transition, 0) + 1

        common_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        return {
            "total_steps": len(path),
            "unique_steps": len(set(path)),
            "path": path,
            "common_transitions": [{"path": p, "count": c} for p, c in common_paths],
        }

    def _generate_event_id(self) -> str:
        """生成事件ID"""
        return hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:16]

    def _write_event_log(self, event: UserEvent) -> None:
        """写入事件日志"""
        try:
            log_file = (
                self.log_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.info(sanitize_log_data(f"写入事件日志失败: {e}"))


# 全局监控实例
frontend_monitor = FrontendMonitor()
behavior_tracker = UserBehaviorTracker()
