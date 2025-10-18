"""
用户操作流程管理器
统一管理用户的完整操作流程，确保交互逻辑清晰、流程完整

功能:
1. 启动流程管理 - 首次使用、老用户恢复
2. 用户身份管理 - 简化登录、角色切换
3. 实验流程管理 - 从选择到完成的全流程
4. 数据流转管理 - 状态保存和恢复
5. 引导系统集成 - 新手引导和帮助
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowStage(Enum):
    """流程阶段"""

    NOT_STARTED = "not_started"  # 未开始
    STARTUP = "startup"  # 启动阶段
    WELCOME = "welcome"  # 欢迎向导
    IDENTITY = "identity"  # 身份确认
    MAIN_INTERFACE = "main_interface"  # 主界面
    EXPERIMENT_SELECTION = "experiment_selection"  # 实验选择
    EXPERIMENT_RUNNING = "experiment_running"  # 实验进行中
    EXPERIMENT_COMPLETED = "experiment_completed"  # 实验完成
    REVIEW = "review"  # 复习回顾
    EXIT = "exit"  # 退出


class UserRole(Enum):
    """用户角色"""

    GUEST = "guest"  # 访客
    STUDENT = "student"  # 学生
    ADMIN = "admin"  # 管理员


@dataclass
class UserSession:
    """用户会话数据"""

    user_id: str
    role: UserRole
    display_name: str
    started_at: datetime
    last_active: datetime
    current_stage: WorkflowStage
    experiment_count: int = 0
    completed_experiments: int = 0
    total_score: float = 0.0
    preferences: dict[str, Any] | None = None
    state_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["last_active"] = self.last_active.isoformat()
        data["role"] = self.role.value
        data["current_stage"] = self.current_stage.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserSession:
        """从字典创建"""
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["last_active"] = datetime.fromisoformat(data["last_active"])
        data["role"] = UserRole(data["role"])
        data["current_stage"] = WorkflowStage(data["current_stage"])
        return cls(**data)


@dataclass
class WorkflowEvent:
    """流程事件"""

    stage: WorkflowStage
    action: str
    timestamp: datetime
    data: dict[str, Any] | None = None
    user_id: str | None = None


class UserWorkflowManager(QObject):
    """用户操作流程管理器"""

    # 信号定义
    stage_changed = Signal(WorkflowStage, WorkflowStage)  # 阶段变更 (旧阶段, 新阶段)
    workflow_event = Signal(WorkflowEvent)  # 流程事件
    session_started = Signal(UserSession)  # 会话开始
    session_ended = Signal(UserSession)  # 会话结束
    user_action = Signal(str, dict)  # 用户动作 (动作名, 数据)

    def __init__(self, data_dir: Path | None = None):
        super().__init__()

        # 数据目录
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(exist_ok=True)

        # 当前会话
        self.current_session: UserSession | None = None

        # 流程状态
        self.current_stage = WorkflowStage.NOT_STARTED
        self.stage_history: list[tuple[WorkflowStage, datetime]] = []

        # 流程配置
        self.auto_save_enabled = True
        self.show_welcome_wizard = True
        self.require_identity_confirmation = False

        # 事件监听器
        self.event_listeners: dict[str, list[Callable]] = {}

        # 加载配置
        self.load_workflow_config()

        logger.info("用户流程管理器初始化完成")

    # ==================== 启动流程 ====================

    def start_workflow(self, skip_welcome: bool = False) -> bool:
        """
        启动工作流程

        Args:
            skip_welcome: 是否跳过欢迎向导

        Returns:
            是否成功启动
        """
        try:
            logger.info("开始用户工作流程")
            self._change_stage(WorkflowStage.STARTUP)

            # 检查系统状态
            if not self._check_system_status():
                logger.error("系统状态检查失败")
                return False

            # 检查是否首次使用
            is_first_run = self._is_first_run()

            # 尝试恢复上次会话
            restored = self._try_restore_session()

            if is_first_run and not skip_welcome:
                # 首次使用，显示欢迎向导
                logger.info("检测到首次运行，准备显示欢迎向导")
                self._change_stage(WorkflowStage.WELCOME)
                return True

            if restored:
                # 恢复成功，直接进入主界面
                logger.info(f"恢复上次会话: {self.current_session.user_id}")
                self._change_stage(WorkflowStage.MAIN_INTERFACE)
                return True

            # 新会话，进入身份确认
            self._change_stage(WorkflowStage.IDENTITY)
            return True

        except Exception as e:
            logger.error(f"启动工作流程失败: {e}", exc_info=True)
            return False

    def complete_welcome_wizard(self, user_preferences: dict[str, Any] | None = None) -> None:
        """
        完成欢迎向导

        Args:
            user_preferences: 用户偏好设置
        """
        logger.info("欢迎向导完成")

        # 保存首次运行标记
        first_run_file = self.data_dir / ".first_run_completed"
        first_run_file.touch()

        # 保存用户偏好
        if user_preferences:
            self._save_user_preferences(user_preferences)

        # 进入身份确认
        self._change_stage(WorkflowStage.IDENTITY)

    def confirm_user_identity(
        self,
        user_id: str | None = None,
        role: UserRole = UserRole.STUDENT,
        display_name: str | None = None,
    ) -> UserSession:
        """
        确认用户身份

        Args:
            user_id: 用户ID（None则自动生成）
            role: 用户角色
            display_name: 显示名称

        Returns:
            用户会话
        """
        # 生成用户ID
        if not user_id:
            user_id = self._generate_user_id(role)

        # 显示名称
        if not display_name:
            display_name = self._get_default_display_name(role)

        # 创建会话
        now = datetime.now()
        self.current_session = UserSession(
            user_id=user_id,
            role=role,
            display_name=display_name,
            started_at=now,
            last_active=now,
            current_stage=WorkflowStage.IDENTITY,
            preferences=self._load_user_preferences(),
        )

        logger.info(f"用户身份确认: {user_id} ({role.value})")

        # 发送会话开始信号
        self.session_started.emit(self.current_session)

        # 进入主界面
        self._change_stage(WorkflowStage.MAIN_INTERFACE)

        # 保存会话
        self._save_session()

        return self.current_session

    # ==================== 实验流程 ====================

    def start_experiment_selection(self) -> None:
        """开始实验选择"""
        logger.info("进入实验选择阶段")
        self._change_stage(WorkflowStage.EXPERIMENT_SELECTION)
        self._emit_event("experiment_selection_started")

    def start_experiment(self, experiment_id: str, experiment_name: str) -> None:
        """
        开始实验

        Args:
            experiment_id: 实验ID
            experiment_name: 实验名称
        """
        if not self.current_session:
            logger.warning("未确认用户身份，无法开始实验")
            return

        logger.info(f"开始实验: {experiment_name} ({experiment_id})")

        self._change_stage(WorkflowStage.EXPERIMENT_RUNNING)

        # 更新会话数据
        self.current_session.experiment_count += 1
        self.current_session.last_active = datetime.now()

        # 发送事件
        self._emit_event(
            "experiment_started",
            {"experiment_id": experiment_id, "experiment_name": experiment_name},
        )

        # 自动保存
        if self.auto_save_enabled:
            self._save_session()

    def complete_experiment(
        self,
        experiment_id: str,
        score: float,
        duration_seconds: float,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        完成实验

        Args:
            experiment_id: 实验ID
            score: 得分
            duration_seconds: 用时（秒）
            data: 实验数据
        """
        if not self.current_session:
            logger.warning("未确认用户身份，无法记录实验完成")
            return

        logger.info(f"实验完成: {experiment_id}, 得分: {score}")

        self._change_stage(WorkflowStage.EXPERIMENT_COMPLETED)

        # 更新会话数据
        self.current_session.completed_experiments += 1
        self.current_session.total_score += score
        self.current_session.last_active = datetime.now()

        # 发送事件
        self._emit_event(
            "experiment_completed",
            {
                "experiment_id": experiment_id,
                "score": score,
                "duration": duration_seconds,
                "data": data or {},
            },
        )

        # 自动保存
        if self.auto_save_enabled:
            self._save_session()

    def return_to_main_interface(self) -> None:
        """返回主界面"""
        logger.info("返回主界面")
        self._change_stage(WorkflowStage.MAIN_INTERFACE)

    def pause_experiment(self, experiment_id: str) -> None:
        """
        暂停实验

        Args:
            experiment_id: 实验ID
        """
        logger.info(f"暂停实验: {experiment_id}")

        # 发送事件
        self._emit_event("experiment_paused", {"experiment_id": experiment_id})

        # 自动保存状态
        if self.auto_save_enabled:
            self._save_session()

    # ==================== 会话管理 ====================

    def get_current_session(self) -> UserSession | None:
        """获取当前会话"""
        return self.current_session

    def update_session(self, **kwargs: Any) -> None:
        """更新会话数据"""
        if not self.current_session:
            return

        for key, value in kwargs.items():
            if hasattr(self.current_session, key):
                setattr(self.current_session, key, value)

        self.current_session.last_active = datetime.now()

        # 自动保存
        if self.auto_save_enabled:
            self._save_session()

    def end_session(self) -> None:
        """结束会话"""
        if not self.current_session:
            return

        logger.info(f"结束用户会话: {self.current_session.user_id}")

        # 发送会话结束信号
        self.session_ended.emit(self.current_session)

        # 保存会话
        self._save_session()

        # 清除当前会话
        self.current_session = None

        # 进入退出阶段
        self._change_stage(WorkflowStage.EXIT)

    # ==================== 状态管理 ====================

    def get_current_stage(self) -> WorkflowStage:
        """获取当前阶段"""
        return self.current_stage

    def can_transition_to(self, target_stage: WorkflowStage) -> bool:
        """
        检查是否可以转换到目标阶段

        Args:
            target_stage: 目标阶段

        Returns:
            是否可以转换
        """
        # 定义允许的转换
        allowed_transitions = {
            WorkflowStage.NOT_STARTED: [WorkflowStage.STARTUP],
            WorkflowStage.STARTUP: [
                WorkflowStage.WELCOME,
                WorkflowStage.IDENTITY,
                WorkflowStage.MAIN_INTERFACE,
            ],
            WorkflowStage.WELCOME: [WorkflowStage.IDENTITY],
            WorkflowStage.IDENTITY: [WorkflowStage.MAIN_INTERFACE],
            WorkflowStage.MAIN_INTERFACE: [
                WorkflowStage.EXPERIMENT_SELECTION,
                WorkflowStage.REVIEW,
                WorkflowStage.EXIT,
            ],
            WorkflowStage.EXPERIMENT_SELECTION: [
                WorkflowStage.EXPERIMENT_RUNNING,
                WorkflowStage.MAIN_INTERFACE,
            ],
            WorkflowStage.EXPERIMENT_RUNNING: [
                WorkflowStage.EXPERIMENT_COMPLETED,
                WorkflowStage.MAIN_INTERFACE,
            ],
            WorkflowStage.EXPERIMENT_COMPLETED: [
                WorkflowStage.MAIN_INTERFACE,
                WorkflowStage.EXPERIMENT_SELECTION,
                WorkflowStage.REVIEW,
            ],
            WorkflowStage.REVIEW: [WorkflowStage.MAIN_INTERFACE],
        }

        return target_stage in allowed_transitions.get(self.current_stage, [])

    def get_stage_history(self) -> list[tuple[WorkflowStage, datetime]]:
        """获取阶段历史"""
        return self.stage_history.copy()

    # ==================== 事件系统 ====================

    def on_event(self, event_name: str, callback: Callable) -> None:
        """
        注册事件监听器

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []

        self.event_listeners[event_name].append(callback)
        logger.debug(f"注册事件监听器: {event_name}")

    def off_event(self, event_name: str, callback: Callable) -> None:
        """
        移除事件监听器

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self.event_listeners:
            with contextlib.suppress(ValueError):
                self.event_listeners[event_name].remove(callback)

    # ==================== 内部方法 ====================

    def _change_stage(self, new_stage: WorkflowStage) -> None:
        """改变流程阶段"""
        old_stage = self.current_stage

        if old_stage == new_stage:
            return

        # 检查是否允许转换
        if not self.can_transition_to(new_stage):
            logger.warning(f"不允许的阶段转换: {old_stage.value} -> {new_stage.value}")
            return

        logger.info(f"流程阶段转换: {old_stage.value} -> {new_stage.value}")

        self.current_stage = new_stage
        self.stage_history.append((new_stage, datetime.now()))

        # 更新会话
        if self.current_session:
            self.current_session.current_stage = new_stage

        # 发送信号
        self.stage_changed.emit(old_stage, new_stage)

    def _emit_event(self, event_name: str, data: dict[str, Any] | None = None) -> None:
        """触发事件"""
        event = WorkflowEvent(
            stage=self.current_stage,
            action=event_name,
            timestamp=datetime.now(),
            data=data,
            user_id=self.current_session.user_id if self.current_session else None,
        )

        # 发送信号
        self.workflow_event.emit(event)

        # 调用监听器
        if event_name in self.event_listeners:
            for callback in self.event_listeners[event_name]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"事件监听器执行失败: {e}", exc_info=True)

    def _check_system_status(self) -> bool:
        """检查系统状态"""
        # 检查数据目录
        required_dirs = ["users", "records", "experiments", "backups"]
        for dir_name in required_dirs:
            dir_path = self.data_dir / dir_name
            dir_path.mkdir(exist_ok=True)

        return True

    def _is_first_run(self) -> bool:
        """检查是否首次运行"""
        first_run_file = self.data_dir / ".first_run_completed"
        return not first_run_file.exists()

    def _try_restore_session(self) -> bool:
        """尝试恢复上次会话"""
        session_file = self.data_dir / "last_session.json"

        if not session_file.exists():
            return False

        try:
            with session_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            self.current_session = UserSession.from_dict(data)
            logger.info(f"恢复会话成功: {self.current_session.user_id}")
            return True

        except Exception as e:
            logger.warning(f"恢复会话失败: {e}")
            return False

    def _save_session(self) -> None:
        """保存会话"""
        if not self.current_session:
            return

        session_file = self.data_dir / "last_session.json"

        try:
            with session_file.open("w", encoding="utf-8") as f:
                json.dump(self.current_session.to_dict(), f, ensure_ascii=False, indent=2)

            logger.debug("会话保存成功")

        except Exception as e:
            logger.error(f"保存会话失败: {e}", exc_info=True)

    def _generate_user_id(self, role: UserRole) -> str:
        """生成用户ID"""
        prefix_map = {
            UserRole.GUEST: "guest",
            UserRole.STUDENT: "student",
            UserRole.ADMIN: "admin",
        }

        prefix = prefix_map.get(role, "user")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}"

    def _get_default_display_name(self, role: UserRole) -> str:
        """获取默认显示名称"""
        name_map = {
            UserRole.GUEST: "访客",
            UserRole.STUDENT: "学生",
            UserRole.ADMIN: "管理员",
        }

        return name_map.get(role, "用户")

    def _load_user_preferences(self) -> dict[str, Any]:
        """加载用户偏好"""
        prefs_file = self.data_dir / "user_preferences.json"

        if not prefs_file.exists():
            return {}

        try:
            with prefs_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载用户偏好失败: {e}")
            return {}

    def _save_user_preferences(self, preferences: dict[str, Any]) -> None:
        """保存用户偏好"""
        prefs_file = self.data_dir / "user_preferences.json"

        try:
            with prefs_file.open("w", encoding="utf-8") as f:
                json.dump(preferences, f, ensure_ascii=False, indent=2)

            logger.info("用户偏好保存成功")

        except Exception as e:
            logger.error(f"保存用户偏好失败: {e}", exc_info=True)

    def load_workflow_config(self) -> None:
        """加载流程配置"""
        config_file = self.data_dir / "workflow_config.json"

        if not config_file.exists():
            # 使用默认配置
            return

        try:
            with config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)

            self.auto_save_enabled = config.get("auto_save_enabled", True)
            self.show_welcome_wizard = config.get("show_welcome_wizard", True)
            self.require_identity_confirmation = config.get("require_identity_confirmation", False)

            logger.info("流程配置加载成功")

        except Exception as e:
            logger.warning(f"加载流程配置失败: {e}")


# 全局实例
_workflow_manager: UserWorkflowManager | None = None


def get_workflow_manager() -> UserWorkflowManager:
    """获取流程管理器实例（单例）"""
    global _workflow_manager

    if _workflow_manager is None:
        _workflow_manager = UserWorkflowManager()

    return _workflow_manager


# 修复导入
import contextlib
