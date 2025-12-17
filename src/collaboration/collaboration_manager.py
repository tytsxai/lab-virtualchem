"""
协作管理器
管理多用户协作会话和实时同步
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(Enum):
    """会话状态"""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    WAITING = "waiting"


class UserRole(Enum):
    """用户角色"""

    LEADER = "leader"  # 组长
    MEMBER = "member"  # 成员
    OBSERVER = "observer"  # 观察者


@dataclass
class CollaborationUser:
    """协作用户"""

    user_id: str
    username: str
    role: UserRole
    joined_at: datetime
    last_activity: datetime
    is_online: bool = True
    permissions: set[str] = field(default_factory=set)


@dataclass
class CollaborationSession:
    """协作会话"""

    session_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    status: SessionStatus
    max_participants: int = 10
    participants: list[CollaborationUser] = field(default_factory=list)
    experiment_template_id: str | None = None
    shared_data: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)


class CollaborationEvent(BaseModel):
    """协作事件"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class CollaborationManager:
    """协作管理器"""

    def __init__(self) -> None:
        """初始化协作管理器"""
        self.active_sessions: dict[str, CollaborationSession] = {}
        self.user_sessions: dict[str, set[str]] = {}  # user_id -> session_ids
        self.event_history: dict[
            str, list[CollaborationEvent]
        ] = {}  # session_id -> events
        self.event_listeners: dict[
            str, list[Callable[..., None]]
        ] = {}  # event_type -> listeners

        # 会话清理任务
        self._cleanup_task: asyncio.Task[None] | None = None
        self._start_cleanup_task()

        logger.info("协作管理器已初始化")

    def _start_cleanup_task(self) -> None:
        """启动清理任务"""

        async def cleanup() -> None:
            while True:
                try:
                    await asyncio.sleep(300)  # 5分钟清理一次
                    self._cleanup_inactive_sessions()
                except Exception as e:
                    logger.error(f"清理任务错误: {e}")

        self._cleanup_task = asyncio.create_task(cleanup())

    def _cleanup_inactive_sessions(self) -> None:
        """清理非活跃会话"""
        current_time = datetime.now()
        inactive_threshold = timedelta(hours=2)

        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            # 检查最后活动时间
            last_activity = max(
                (p.last_activity for p in session.participants),
                default=session.created_at,
            )

            if current_time - last_activity > inactive_threshold:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            self.end_session(session_id, "系统清理")
            logger.info(f"清理非活跃会话: {session_id}")

    def create_session(
        self,
        name: str,
        description: str,
        created_by: str,
        experiment_template_id: str | None = None,
        max_participants: int = 10,
        settings: dict[str, Any] | None = None,
    ) -> CollaborationSession:
        """创建协作会话

        Args:
            name: 会话名称
            description: 会话描述
            created_by: 创建者ID
            experiment_template_id: 实验模板ID
            max_participants: 最大参与者数
            settings: 会话设置

        Returns:
            协作会话
        """
        session_id = str(uuid.uuid4())

        session = CollaborationSession(
            session_id=session_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(),
            status=SessionStatus.ACTIVE,
            max_participants=max_participants,
            experiment_template_id=experiment_template_id,
            settings=settings or {},
        )

        # 添加创建者为组长
        leader = CollaborationUser(
            user_id=created_by,
            username=f"User_{created_by}",
            role=UserRole.LEADER,
            joined_at=datetime.now(),
            last_activity=datetime.now(),
            permissions={"create", "edit", "delete", "invite", "manage"},
        )
        session.participants.append(leader)

        # 保存会话
        self.active_sessions[session_id] = session
        self.user_sessions[created_by] = self.user_sessions.get(created_by, set())
        self.user_sessions[created_by].add(session_id)
        self.event_history[session_id] = []

        # 发送创建事件
        self._emit_event(
            session_id,
            created_by,
            "session_created",
            {"session_id": session_id, "name": name, "description": description},
        )

        logger.info(f"协作会话已创建: {session_id} by {created_by}")
        return session

    def join_session(self, session_id: str, user_id: str, username: str) -> bool:
        """加入协作会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            username: 用户名

        Returns:
            是否成功加入
        """
        if session_id not in self.active_sessions:
            logger.warning(f"会话不存在: {session_id}")
            return False

        session = self.active_sessions[session_id]

        # 检查是否已满员
        if len(session.participants) >= session.max_participants:
            logger.warning(f"会话已满员: {session_id}")
            return False

        # 检查是否已在会话中
        for participant in session.participants:
            if participant.user_id == user_id:
                logger.warning(f"用户已在会话中: {user_id}")
                return False

        # 添加参与者
        member = CollaborationUser(
            user_id=user_id,
            username=username,
            role=UserRole.MEMBER,
            joined_at=datetime.now(),
            last_activity=datetime.now(),
            permissions={"view", "edit"},
        )
        session.participants.append(member)

        # 更新用户会话映射
        self.user_sessions[user_id] = self.user_sessions.get(user_id, set())
        self.user_sessions[user_id].add(session_id)

        # 发送加入事件
        self._emit_event(
            session_id,
            user_id,
            "user_joined",
            {"user_id": user_id, "username": username},
        )

        logger.info(f"用户加入会话: {user_id} -> {session_id}")
        return True

    def leave_session(self, session_id: str, user_id: str) -> bool:
        """离开协作会话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            是否成功离开
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # 移除参与者
        session.participants = [p for p in session.participants if p.user_id != user_id]

        # 更新用户会话映射
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]

        # 如果会话为空，结束会话
        if not session.participants:
            self.end_session(session_id, "所有用户离开")
            return True

        # 发送离开事件
        self._emit_event(session_id, user_id, "user_left", {"user_id": user_id})

        logger.info(f"用户离开会话: {user_id} -> {session_id}")
        return True

    def end_session(self, session_id: str, ended_by: str) -> bool:
        """结束协作会话

        Args:
            session_id: 会话ID
            ended_by: 结束者ID

        Returns:
            是否成功结束
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        session.status = SessionStatus.ENDED

        # 发送结束事件
        self._emit_event(
            session_id,
            ended_by,
            "session_ended",
            {"ended_by": ended_by, "reason": "会话结束"},
        )

        # 清理会话
        for participant in session.participants:
            if participant.user_id in self.user_sessions:
                self.user_sessions[participant.user_id].discard(session_id)
                if not self.user_sessions[participant.user_id]:
                    del self.user_sessions[participant.user_id]

        # 移除会话
        del self.active_sessions[session_id]

        logger.info(f"协作会话已结束: {session_id} by {ended_by}")
        return True

    def update_user_activity(self, session_id: str, user_id: str) -> None:
        """更新用户活动时间

        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        for participant in session.participants:
            if participant.user_id == user_id:
                participant.last_activity = datetime.now()
                break

    def get_session(self, session_id: str) -> CollaborationSession | None:
        """获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息
        """
        return self.active_sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> list[CollaborationSession]:
        """获取用户的会话列表

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        session_ids = self.user_sessions.get(user_id, set())
        return [
            self.active_sessions[sid]
            for sid in session_ids
            if sid in self.active_sessions
        ]

    def update_shared_data(
        self, session_id: str, user_id: str, data: dict[str, Any]
    ) -> bool:
        """更新共享数据

        Args:
            session_id: 会话ID
            user_id: 用户ID
            data: 数据

        Returns:
            是否成功更新
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # 检查权限
        user = next((p for p in session.participants if p.user_id == user_id), None)
        if not user or "edit" not in user.permissions:
            logger.warning(f"用户无编辑权限: {user_id}")
            return False

        # 更新数据
        session.shared_data.update(data)

        # 发送更新事件
        self._emit_event(
            session_id, user_id, "data_updated", {"data": data, "updated_by": user_id}
        )

        logger.info(f"共享数据已更新: {session_id} by {user_id}")
        return True

    def get_shared_data(self, session_id: str) -> dict[str, Any]:
        """获取共享数据

        Args:
            session_id: 会话ID

        Returns:
            共享数据
        """
        session = self.active_sessions.get(session_id)
        return session.shared_data if session else {}

    def add_event_listener(
        self, event_type: str, listener: Callable[..., None]
    ) -> None:
        """添加事件监听器

        Args:
            event_type: 事件类型
            listener: 监听器函数
        """
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(listener)

    def remove_event_listener(
        self, event_type: str, listener: Callable[..., None]
    ) -> None:
        """移除事件监听器

        Args:
            event_type: 事件类型
            listener: 监听器函数
        """
        if event_type in self.event_listeners:
            with contextlib.suppress(ValueError):
                self.event_listeners[event_type].remove(listener)

    def _emit_event(
        self, session_id: str, user_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """发送事件

        Args:
            session_id: 会话ID
            user_id: 用户ID
            event_type: 事件类型
            data: 事件数据
        """
        event = CollaborationEvent(
            session_id=session_id, user_id=user_id, event_type=event_type, data=data
        )

        # 添加到历史记录
        if session_id in self.event_history:
            self.event_history[session_id].append(event)

        # 通知监听器
        if event_type in self.event_listeners:
            for listener in self.event_listeners[event_type]:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"事件监听器错误: {e}")

        logger.debug(f"事件已发送: {event_type} in {session_id}")

    def get_session_events(
        self, session_id: str, limit: int = 100
    ) -> list[CollaborationEvent]:
        """获取会话事件历史

        Args:
            session_id: 会话ID
            limit: 限制数量

        Returns:
            事件列表
        """
        events = self.event_history.get(session_id, [])
        return events[-limit:] if limit > 0 else events

    def get_session_statistics(self, session_id: str) -> dict[str, Any]:
        """获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            统计信息
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {}

        events = self.event_history.get(session_id, [])

        return {
            "session_id": session_id,
            "name": session.name,
            "status": session.status.value,
            "participant_count": len(session.participants),
            "max_participants": session.max_participants,
            "created_at": session.created_at.isoformat(),
            "duration_minutes": (datetime.now() - session.created_at).total_seconds()
            / 60,
            "event_count": len(events),
            "online_users": sum(1 for p in session.participants if p.is_online),
            "shared_data_size": len(session.shared_data),
        }
