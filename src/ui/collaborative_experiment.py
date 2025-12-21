"""
协作式实验系统
支持多用户实时协作进行虚拟实验
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .security_utils import apply_text_constraints

logger = get_logger(__name__)


class CollaboratorRole(Enum):
    """协作者角色"""

    OWNER = "owner"  # 实验所有者
    OPERATOR = "operator"  # 操作者
    OBSERVER = "observer"  # 观察者
    ASSISTANT = "assistant"  # 助手


class ActionType(Enum):
    """操作类型"""

    ADD_EQUIPMENT = "add_equipment"
    REMOVE_EQUIPMENT = "remove_equipment"
    MOVE_ITEM = "move_item"
    MEASURE = "measure"
    INPUT_DATA = "input_data"
    SUBMIT_STEP = "submit_step"
    CHAT = "chat"
    ANNOTATION = "annotation"


@dataclass
class Collaborator:
    """协作者信息"""

    id: str
    name: str
    role: CollaboratorRole
    color: str  # 用于区分不同用户的颜色
    is_online: bool = True
    cursor_position: tuple[float, float] = (0, 0)
    current_action: str = ""
    joined_at: datetime = field(default_factory=datetime.now)


@dataclass
class CollaborativeAction:
    """协作操作"""

    id: str
    user_id: str
    user_name: str
    action_type: ActionType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    synced: bool = False


@dataclass
class ChatMessage:
    """聊天消息"""

    id: str
    user_id: str
    user_name: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_system: bool = False


class CollaborativeSession(QObject):
    """协作会话"""

    # 信号
    collaborator_joined = Signal(str)  # 用户ID
    collaborator_left = Signal(str)
    action_received = Signal(CollaborativeAction)
    chat_received = Signal(ChatMessage)
    cursor_moved = Signal(str, float, float)  # 用户ID, x, y

    def __init__(
        self,
        session_id: str,
        owner_id: str,
        owner_name: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)

        self.session_id = session_id
        self.owner_id = owner_id

        # 协作者列表
        self.collaborators: dict[str, Collaborator] = {}

        # 添加所有者
        self.collaborators[owner_id] = Collaborator(
            id=owner_id, name=owner_name, role=CollaboratorRole.OWNER, color="#e74c3c"
        )

        # 操作历史
        self.action_history: list[CollaborativeAction] = []

        # 聊天历史
        self.chat_history: list[ChatMessage] = []

        # 权限配置
        self.permissions = {
            CollaboratorRole.OWNER: ["all"],
            CollaboratorRole.OPERATOR: [
                "add_equipment",
                "remove_equipment",
                "move_item",
                "measure",
                "input_data",
                "submit_step",
                "chat",
            ],
            CollaboratorRole.OBSERVER: ["chat"],
            CollaboratorRole.ASSISTANT: [
                "add_equipment",
                "move_item",
                "measure",
                "chat",
            ],
        }

        # 心跳检测
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._check_collaborators_status)
        self.heartbeat_timer.start(5000)  # 5秒检测一次

        logger.info(f"协作会话创建: {session_id}")

    def add_collaborator(
        self,
        user_id: str,
        user_name: str,
        role: CollaboratorRole = CollaboratorRole.OBSERVER,
    ) -> bool:
        """添加协作者"""
        if user_id in self.collaborators:
            logger.warning(f"用户 {user_id} 已在会话中")
            return False

        # 分配颜色
        colors = ["#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
        color = colors[len(self.collaborators) % len(colors)]

        collaborator = Collaborator(id=user_id, name=user_name, role=role, color=color)

        self.collaborators[user_id] = collaborator

        # 发送系统消息
        self._add_system_message(f"{user_name} 加入了实验")

        # 发送信号
        self.collaborator_joined.emit(user_id)

        logger.info(f"协作者加入: {user_name} ({role.value})")
        return True

    def remove_collaborator(self, user_id: str) -> bool:
        """移除协作者"""
        if user_id not in self.collaborators:
            return False

        if user_id == self.owner_id:
            logger.warning("无法移除会话所有者")
            return False

        collaborator = self.collaborators[user_id]
        del self.collaborators[user_id]

        # 发送系统消息
        self._add_system_message(f"{collaborator.name} 离开了实验")

        # 发送信号
        self.collaborator_left.emit(user_id)

        logger.info(f"协作者离开: {collaborator.name}")
        return True

    def update_collaborator_role(
        self, user_id: str, new_role: CollaboratorRole
    ) -> bool:
        """更新协作者角色"""
        if user_id not in self.collaborators:
            return False

        old_role = self.collaborators[user_id].role
        self.collaborators[user_id].role = new_role

        # 发送系统消息
        name = self.collaborators[user_id].name
        self._add_system_message(
            f"{name} 的角色已从 {old_role.value} 变更为 {new_role.value}"
        )

        logger.info(f"角色更新: {name} -> {new_role.value}")
        return True

    def submit_action(
        self, user_id: str, action_type: ActionType, data: dict[str, Any]
    ) -> bool:
        """提交操作"""
        if user_id not in self.collaborators:
            logger.warning(f"未知用户: {user_id}")
            return False

        collaborator = self.collaborators[user_id]

        # 检查权限
        if not self._has_permission(collaborator.role, action_type.value):
            logger.warning(
                f"权限不足: {collaborator.name} 无法执行 {action_type.value}"
            )
            return False

        # 创建操作记录
        action = CollaborativeAction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_name=collaborator.name,
            action_type=action_type,
            data=data,
        )

        self.action_history.append(action)

        # 发送信号
        self.action_received.emit(action)

        logger.debug(f"操作提交: {collaborator.name} - {action_type.value}")
        return True

    def send_chat_message(self, user_id: str, message: str) -> bool:
        """发送聊天消息"""
        if user_id not in self.collaborators:
            return False

        collaborator = self.collaborators[user_id]

        chat_msg = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_name=collaborator.name,
            message=message,
        )

        self.chat_history.append(chat_msg)

        # 发送信号
        self.chat_received.emit(chat_msg)

        logger.debug(f"聊天消息: {collaborator.name}: {message}")
        return True

    def update_cursor_position(self, user_id: str, x: float, y: float) -> None:
        """更新用户光标位置"""
        if user_id in self.collaborators:
            self.collaborators[user_id].cursor_position = (x, y)
            self.cursor_moved.emit(user_id, x, y)

    def _has_permission(self, role: CollaboratorRole, action: str) -> bool:
        """检查权限"""
        if role == CollaboratorRole.OWNER:
            return True

        allowed_actions = self.permissions.get(role, [])
        return action in allowed_actions or "all" in allowed_actions

    def _add_system_message(self, message: str) -> None:
        """添加系统消息"""
        chat_msg = ChatMessage(
            id=str(uuid.uuid4()),
            user_id="system",
            user_name="系统",
            message=message,
            is_system=True,
        )

        self.chat_history.append(chat_msg)
        self.chat_received.emit(chat_msg)

    def _check_collaborators_status(self) -> None:
        """检查协作者在线状态"""
        # 这里可以实现心跳检测逻辑
        # 如果某个用户长时间无响应，标记为离线
        pass

    def get_collaborators_list(self) -> list[Collaborator]:
        """获取协作者列表"""
        return list(self.collaborators.values())

    def export_session_data(self) -> dict[str, Any]:
        """导出会话数据"""
        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "collaborators": [
                {
                    "id": c.id,
                    "name": c.name,
                    "role": c.role.value,
                    "color": c.color,
                    "joined_at": c.joined_at.isoformat(),
                }
                for c in self.collaborators.values()
            ],
            "actions": [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "user_name": a.user_name,
                    "action_type": a.action_type.value,
                    "data": a.data,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.action_history
            ],
            "chat": [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "user_name": m.user_name,
                    "message": m.message,
                    "timestamp": m.timestamp.isoformat(),
                    "is_system": m.is_system,
                }
                for m in self.chat_history
            ],
        }


class CollaborativeExperimentWidget(QWidget):
    """协作实验界面组件"""

    def __init__(
        self,
        session: CollaborativeSession,
        current_user_id: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.session = session
        self.current_user_id = current_user_id

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QVBoxLayout(self)

        # 协作者列表
        collab_label = QLabel("协作者")
        collab_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(collab_label)

        self.collaborators_list = QListWidget()
        self.collaborators_list.setMaximumHeight(150)
        layout.addWidget(self.collaborators_list)

        # 聊天区域
        chat_label = QLabel("聊天")
        chat_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(chat_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)
        layout.addWidget(self.chat_display)

        # 输入区域
        input_layout = QHBoxLayout()

        self.chat_input = QTextEdit()
        self.chat_input.setMaximumHeight(60)
        self.chat_input.setPlaceholderText("输入消息...")
        apply_text_constraints(self.chat_input, max_length=500)
        input_layout.addWidget(self.chat_input)

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._send_chat)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # 应用样式
        self.setStyleSheet(
            """
            QWidget {
                background-color: white;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )

        # 初始化协作者列表
        self._update_collaborators_list()

    def _connect_signals(self) -> None:
        """连接信号"""
        self.session.collaborator_joined.connect(
            lambda _: self._update_collaborators_list()
        )
        self.session.collaborator_left.connect(
            lambda _: self._update_collaborators_list()
        )
        self.session.chat_received.connect(self._on_chat_received)

    def _update_collaborators_list(self) -> None:
        """更新协作者列表"""
        self.collaborators_list.clear()

        for collaborator in self.session.get_collaborators_list():
            status = "🟢" if collaborator.is_online else "🔴"
            role_icon = {
                CollaboratorRole.OWNER: "👑",
                CollaboratorRole.OPERATOR: "🔧",
                CollaboratorRole.OBSERVER: "👁",
                CollaboratorRole.ASSISTANT: "🤝",
            }.get(collaborator.role, "")

            item_text = f"{status} {role_icon} {collaborator.name}"
            item = QListWidgetItem(item_text)

            # 使用协作者的颜色
            from PySide6.QtGui import QColor

            item.setForeground(QColor(collaborator.color))

            self.collaborators_list.addItem(item)

    def _send_chat(self) -> None:
        """发送聊天消息"""
        message = self.chat_input.toPlainText().strip()
        if not message:
            return

        self.session.send_chat_message(self.current_user_id, message)
        self.chat_input.clear()

    def _on_chat_received(self, msg: ChatMessage) -> None:
        """处理接收到的聊天消息"""
        timestamp = msg.timestamp.strftime("%H:%M")

        if msg.is_system:
            html = f'<p style="color: #7f8c8d; font-style: italic;">[{timestamp}] {msg.message}</p>'
        else:
            # 获取用户颜色
            color = "#2c3e50"
            if msg.user_id in self.session.collaborators:
                color = self.session.collaborators[msg.user_id].color

            html = f'<p><span style="color: {color}; font-weight: bold;">[{timestamp}] {msg.user_name}:</span> {msg.message}</p>'

        self.chat_display.append(html)


class CollaborationManager(QObject):
    """协作管理器"""

    # 信号
    session_created = Signal(str)  # 会话ID
    session_closed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.sessions: dict[str, CollaborativeSession] = {}

        logger.info("协作管理器初始化完成")

    def create_session(self, owner_id: str, owner_name: str, experiment_id: str) -> str:
        """创建协作会话"""
        session_id = f"{experiment_id}_{uuid.uuid4().hex[:8]}"

        session = CollaborativeSession(session_id, owner_id, owner_name, self)
        self.sessions[session_id] = session

        self.session_created.emit(session_id)

        logger.info(f"创建协作会话: {session_id}")
        return session_id

    def close_session(self, session_id: str) -> bool:
        """关闭协作会话"""
        if session_id not in self.sessions:
            return False

        del self.sessions[session_id]

        self.session_closed.emit(session_id)

        logger.info(f"关闭协作会话: {session_id}")
        return True

    def get_session(self, session_id: str) -> CollaborativeSession | None:
        """获取协作会话"""
        return self.sessions.get(session_id)

    def join_session(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
        role: CollaboratorRole = CollaboratorRole.OBSERVER,
    ) -> bool:
        """加入协作会话"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"会话不存在: {session_id}")
            return False

        return session.add_collaborator(user_id, user_name, role)

    def leave_session(self, session_id: str, user_id: str) -> bool:
        """离开协作会话"""
        session = self.get_session(session_id)
        if not session:
            return False

        return session.remove_collaborator(user_id)

    def get_active_sessions(self) -> list[str]:
        """获取所有活跃会话"""
        return list(self.sessions.keys())
