#!/usr/bin/env python3
"""
增强的协作系统
提供实时协作、团队管理、共享实验等功能
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .robustness_integration import enhance_robustness, log_operation, validate_input

logger = logging.getLogger(__name__)


class CollaborationRole(Enum):
    """协作角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"
    OBSERVER = "observer"


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    WAITING = "waiting"


class CollaborationType(Enum):
    """协作类型"""
    EXPERIMENT = "experiment"
    STUDY_GROUP = "study_group"
    PROJECT = "project"
    DISCUSSION = "discussion"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    avatar: str = ""
    status: str = "offline"
    last_seen: Optional[datetime] = None
    timezone: str = "UTC"


@dataclass
class CollaborationMember:
    """协作成员"""
    user: User
    role: CollaborationRole
    joined_at: datetime
    permissions: Set[str] = field(default_factory=set)
    is_active: bool = True


@dataclass
class CollaborationSession:
    """协作会话"""
    session_id: str
    name: str
    description: str
    type: CollaborationType
    owner_id: str
    created_at: datetime
    status: SessionStatus
    members: List[CollaborationMember] = field(default_factory=list)
    max_members: int = 10
    is_public: bool = False
    tags: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class CollaborationMessage:
    """协作消息"""
    message_id: str
    session_id: str
    sender_id: str
    content: str
    message_type: str = "text"  # text, image, file, system
    timestamp: datetime = field(default_factory=datetime.now)
    edited: bool = False
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # emoji -> user_ids
    attachments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SharedResource:
    """共享资源"""
    resource_id: str
    session_id: str
    name: str
    type: str  # experiment, document, image, video
    owner_id: str
    created_at: datetime
    size: int = 0
    url: str = ""
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    version: int = 1
    is_locked: bool = False
    locked_by: Optional[str] = None


class EnhancedCollaborationSystem:
    """增强的协作系统"""

    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.messages: Dict[str, List[CollaborationMessage]] = {}
        self.shared_resources: Dict[str, List[SharedResource]] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.active_users: Dict[str, datetime] = {}  # user_id -> last_activity

        # 权限系统
        self.role_permissions = {
            CollaborationRole.OWNER: {
                "manage_session", "invite_members", "remove_members", "edit_settings",
                "share_resources", "manage_resources", "moderate_chat", "end_session"
            },
            CollaborationRole.ADMIN: {
                "invite_members", "remove_members", "edit_settings", "share_resources",
                "manage_resources", "moderate_chat"
            },
            CollaborationRole.MODERATOR: {
                "moderate_chat", "share_resources", "manage_resources"
            },
            CollaborationRole.MEMBER: {
                "share_resources", "send_messages", "view_resources"
            },
            CollaborationRole.OBSERVER: {
                "view_resources", "send_messages"
            }
        }

        # 初始化系统
        self._initialize_system()

    def _initialize_system(self) -> None:
        """初始化系统"""
        logger.info("协作系统已初始化")

    @enhance_robustness(
        operation_name="create_collaboration_session",
        security_level="medium",
        enable_caching=True
    )
    @validate_input(validation_rules={
        "name": {"type": str, "required": True},
        "description": {"type": str, "required": True},
        "type": {"type": str, "required": True},
        "owner_id": {"type": str, "required": True}
    })
    @log_operation(operation_name="create_session")
    def create_collaboration_session(
        self,
        name: str,
        description: str,
        collaboration_type: str,
        owner_id: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> CollaborationSession:
        """创建协作会话"""
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        try:
            collab_type = CollaborationType(collaboration_type)
        except ValueError:
            collab_type = CollaborationType.EXPERIMENT

        # 创建会话
        session = CollaborationSession(
            session_id=session_id,
            name=name,
            description=description,
            type=collab_type,
            owner_id=owner_id,
            created_at=datetime.now(),
            status=SessionStatus.ACTIVE,
            settings=settings or {}
        )

        # 添加创建者为所有者
        owner_member = CollaborationMember(
            user=User(user_id=owner_id, username=f"user_{owner_id}", email=""),
            role=CollaborationRole.OWNER,
            joined_at=datetime.now(),
            permissions=self.role_permissions[CollaborationRole.OWNER]
        )
        session.members.append(owner_member)

        # 保存会话
        self.sessions[session_id] = session
        self.messages[session_id] = []
        self.shared_resources[session_id] = []

        # 更新用户会话映射
        if owner_id not in self.user_sessions:
            self.user_sessions[owner_id] = set()
        self.user_sessions[owner_id].add(session_id)

        # 记录系统消息
        self._add_system_message(
            session_id,
            f"会话 '{name}' 已创建",
            "system"
        )

        logger.info(f"协作会话已创建: {session_id} - {name}")
        return session

    @enhance_robustness(
        operation_name="invite_user_to_session",
        security_level="medium",
        enable_caching=False
    )
    @log_operation(operation_name="invite_user")
    def invite_user_to_session(
        self,
        session_id: str,
        inviter_id: str,
        user_id: str,
        username: str,
        email: str,
        role: str = "member"
    ) -> bool:
        """邀请用户加入会话"""
        if session_id not in self.sessions:
            logger.warning(f"会话 {session_id} 不存在")
            return False

        session = self.sessions[session_id]

        # 检查邀请者权限
        if not self._has_permission(session_id, inviter_id, "invite_members"):
            logger.warning(f"用户 {inviter_id} 没有邀请权限")
            return False

        # 检查会话是否已满
        if len(session.members) >= session.max_members:
            logger.warning(f"会话 {session_id} 已满")
            return False

        # 检查用户是否已在会话中
        if any(member.user.user_id == user_id for member in session.members):
            logger.warning(f"用户 {user_id} 已在会话中")
            return False

        # 解析角色
        try:
            member_role = CollaborationRole(role)
        except ValueError:
            member_role = CollaborationRole.MEMBER

        # 创建新成员
        new_user = User(
            user_id=user_id,
            username=username,
            email=email
        )

        new_member = CollaborationMember(
            user=new_user,
            role=member_role,
            joined_at=datetime.now(),
            permissions=self.role_permissions[member_role]
        )

        # 添加成员
        session.members.append(new_member)
        session.last_activity = datetime.now()

        # 更新用户会话映射
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)

        # 记录系统消息
        self._add_system_message(
            session_id,
            f"{username} 已加入会话",
            "system"
        )

        logger.info(f"用户 {user_id} 已加入会话 {session_id}")
        return True

    @enhance_robustness(
        operation_name="send_message",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="send_message")
    def send_message(
        self,
        session_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[CollaborationMessage]:
        """发送消息"""
        if session_id not in self.sessions:
            logger.warning(f"会话 {session_id} 不存在")
            return None

        # 检查发送者权限
        if not self._has_permission(session_id, sender_id, "send_messages"):
            logger.warning(f"用户 {sender_id} 没有发送消息权限")
            return None

        # 创建消息
        message = CollaborationMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            attachments=attachments or []
        )

        # 保存消息
        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append(message)

        # 更新会话活动时间
        self.sessions[session_id].last_activity = datetime.now()

        # 更新用户活动时间
        self.active_users[sender_id] = datetime.now()

        logger.info(f"消息已发送: {message.message_id}")
        return message

    @enhance_robustness(
        operation_name="share_resource",
        security_level="medium",
        enable_caching=False
    )
    @log_operation(operation_name="share_resource")
    def share_resource(
        self,
        session_id: str,
        owner_id: str,
        name: str,
        resource_type: str,
        url: str = "",
        size: int = 0,
        permissions: Optional[Dict[str, List[str]]] = None
    ) -> Optional[SharedResource]:
        """共享资源"""
        if session_id not in self.sessions:
            logger.warning(f"会话 {session_id} 不存在")
            return None

        # 检查共享者权限
        if not self._has_permission(session_id, owner_id, "share_resources"):
            logger.warning(f"用户 {owner_id} 没有共享资源权限")
            return None

        # 创建共享资源
        resource = SharedResource(
            resource_id=f"res_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            name=name,
            type=resource_type,
            owner_id=owner_id,
            created_at=datetime.now(),
            size=size,
            url=url,
            permissions=permissions or {}
        )

        # 保存资源
        if session_id not in self.shared_resources:
            self.shared_resources[session_id] = []
        self.shared_resources[session_id].append(resource)

        # 更新会话活动时间
        self.sessions[session_id].last_activity = datetime.now()

        # 记录系统消息
        self._add_system_message(
            session_id,
            f"资源 '{name}' 已共享",
            "system"
        )

        logger.info(f"资源已共享: {resource.resource_id}")
        return resource

    @enhance_robustness(
        operation_name="get_session_messages",
        security_level="low",
        enable_caching=True
    )
    def get_session_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[CollaborationMessage]:
        """获取会话消息"""
        if session_id not in self.sessions:
            return []

        # 检查用户是否在会话中
        if not self._is_user_in_session(session_id, user_id):
            logger.warning(f"用户 {user_id} 不在会话 {session_id} 中")
            return []

        messages = self.messages.get(session_id, [])

        # 分页返回消息
        start_idx = max(0, len(messages) - limit - offset)
        end_idx = len(messages) - offset

        return messages[start_idx:end_idx]

    @enhance_robustness(
        operation_name="get_session_resources",
        security_level="low",
        enable_caching=True
    )
    def get_session_resources(
        self,
        session_id: str,
        user_id: str,
        resource_type: Optional[str] = None
    ) -> List[SharedResource]:
        """获取会话资源"""
        if session_id not in self.sessions:
            return []

        # 检查用户是否在会话中
        if not self._is_user_in_session(session_id, user_id):
            logger.warning(f"用户 {user_id} 不在会话 {session_id} 中")
            return []

        resources = self.shared_resources.get(session_id, [])

        if resource_type:
            resources = [r for r in resources if r.type == resource_type]

        return resources

    @enhance_robustness(
        operation_name="get_user_sessions",
        security_level="low",
        enable_caching=True
    )
    def get_user_sessions(self, user_id: str) -> List[CollaborationSession]:
        """获取用户的会话列表"""
        if user_id not in self.user_sessions:
            return []

        session_ids = self.user_sessions[user_id]
        sessions = []

        for session_id in session_ids:
            if session_id in self.sessions:
                sessions.append(self.sessions[session_id])

        # 按最后活动时间排序
        sessions.sort(key=lambda x: x.last_activity, reverse=True)

        return sessions

    @enhance_robustness(
        operation_name="update_user_status",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="update_status")
    def update_user_status(self, user_id: str, status: str) -> bool:
        """更新用户状态"""
        self.active_users[user_id] = datetime.now()

        # 更新所有会话中的用户状态
        for session in self.sessions.values():
            for member in session.members:
                if member.user.user_id == user_id:
                    member.user.status = status
                    member.user.last_seen = datetime.now()
                    break

        logger.info(f"用户 {user_id} 状态已更新: {status}")
        return True

    @enhance_robustness(
        operation_name="get_session_analytics",
        security_level="low",
        enable_caching=True
    )
    def get_session_analytics(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """获取会话分析"""
        if session_id not in self.sessions:
            return {}

        # 检查用户权限
        if not self._is_user_in_session(session_id, user_id):
            return {}

        session = self.sessions[session_id]
        messages = self.messages.get(session_id, [])
        resources = self.shared_resources.get(session_id, [])

        # 计算消息统计
        message_stats = {}
        for message in messages:
            msg_type = message.message_type
            if msg_type not in message_stats:
                message_stats[msg_type] = 0
            message_stats[msg_type] += 1

        # 计算用户活跃度
        user_activity = {}
        for message in messages:
            sender_id = message.sender_id
            if sender_id not in user_activity:
                user_activity[sender_id] = 0
            user_activity[sender_id] += 1

        # 计算资源统计
        resource_stats = {}
        for resource in resources:
            res_type = resource.type
            if res_type not in resource_stats:
                resource_stats[res_type] = 0
            resource_stats[res_type] += 1

        return {
            "session_info": {
                "session_id": session_id,
                "name": session.members,
                "type": session.type.value,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "member_count": len(session.members)
            },
            "message_stats": message_stats,
            "user_activity": user_activity,
            "resource_stats": resource_stats,
            "total_messages": len(messages),
            "total_resources": len(resources),
            "active_members": len([m for m in session.members if m.is_active])
        }

    def _has_permission(
        self,
        session_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """检查用户权限"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        for member in session.members:
            if member.user.user_id == user_id:
                return permission in member.permissions

        return False

    def _is_user_in_session(self, session_id: str, user_id: str) -> bool:
        """检查用户是否在会话中"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        return any(member.user.user_id == user_id for member in session.members)

    def _add_system_message(
        self,
        session_id: str,
        content: str,
        message_type: str = "system"
    ) -> None:
        """添加系统消息"""
        message = CollaborationMessage(
            message_id=f"sys_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id="system",
            content=content,
            message_type=message_type
        )

        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append(message)

    @enhance_robustness(
        operation_name="search_sessions",
        security_level="low",
        enable_caching=True
    )
    def search_sessions(
        self,
        query: str,
        user_id: str,
        session_type: Optional[str] = None
    ) -> List[CollaborationSession]:
        """搜索会话"""
        user_session_ids = self.user_sessions.get(user_id, set())
        matching_sessions = []

        for session_id in user_session_ids:
            if session_id not in self.sessions:
                continue

            session = self.sessions[session_id]

            # 检查类型过滤
            if session_type and session.type.value != session_type:
                continue

            # 检查查询匹配
            if (query.lower() in session.name.lower() or
                query.lower() in session.description.lower() or
                any(query.lower() in tag.lower() for tag in session.tags)):
                matching_sessions.append(session)

        # 按相关性排序（简单实现）
        matching_sessions.sort(key=lambda x: x.last_activity, reverse=True)

        return matching_sessions


# 全局实例
enhanced_collaboration_system = EnhancedCollaborationSystem()
