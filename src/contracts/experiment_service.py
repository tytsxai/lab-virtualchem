"""实验服务契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..models.experiment import ExperimentTemplate
from ..models.user_record import Mistake, UserRecord


class ExperimentStatus(str, Enum):
    """实验状态"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExperimentServiceConfig:
    """实验服务配置"""

    enable_validation: bool = True  # 是否启用验证
    enable_auto_save: bool = True  # 是否自动保存
    auto_save_interval: int = 60  # 自动保存间隔(秒)
    enable_safety_check: bool = True  # 是否启用安全检查
    max_retry_attempts: int = 3  # 最大重试次数
    enable_hints: bool = True  # 是否启用提示
    strict_mode: bool = False  # 是否严格模式


@dataclass
class ExperimentRequest:
    """实验请求DTO"""

    user_id: str  # 用户ID
    template_id: str  # 模板ID
    options: dict[str, Any] = field(default_factory=dict)  # 额外选项


@dataclass
class ExperimentResponse:
    """实验响应DTO"""

    success: bool  # 是否成功
    experiment_id: str  # 实验ID
    record_id: str | None = None  # 记录ID
    status: ExperimentStatus | None = None  # 状态
    message: str = ""  # 消息
    data: dict[str, Any] = field(default_factory=dict)  # 额外数据


@dataclass
class StepSubmissionRequest:
    """步骤提交请求DTO"""

    experiment_id: str  # 实验ID
    step_id: str  # 步骤ID
    user_input: dict[str, Any]  # 用户输入
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳


@dataclass
class StepSubmissionResponse:
    """步骤提交响应DTO"""

    success: bool  # 是否成功
    passed: bool  # 是否通过
    message: str  # 提示信息
    mistake: Mistake | None = None  # 错误对象
    hints: list[str] = field(default_factory=list)  # 提示列表
    next_step_id: str | None = None  # 下一步骤ID


@dataclass
class ProgressInfo:
    """进度信息DTO"""

    experiment_id: str  # 实验ID
    experiment_title: str  # 实验标题
    current_step: int  # 当前步骤索引
    total_steps: int  # 总步骤数
    completion_rate: float  # 完成率(%)
    total_mistakes: int  # 错误总数
    status: ExperimentStatus  # 状态
    elapsed_time: int | None = None  # 已用时间(秒)


class ExperimentService(ABC):
    """实验服务抽象类"""

    @abstractmethod
    def create_experiment(self, request: ExperimentRequest) -> ExperimentResponse:
        """创建实验

        Args:
            request: 实验请求

        Returns:
            实验响应
        """
        pass

    @abstractmethod
    def start_experiment(self, experiment_id: str) -> ExperimentResponse:
        """开始实验

        Args:
            experiment_id: 实验ID

        Returns:
            实验响应
        """
        pass

    @abstractmethod
    def submit_step(self, request: StepSubmissionRequest) -> StepSubmissionResponse:
        """提交步骤

        Args:
            request: 步骤提交请求

        Returns:
            步骤提交响应
        """
        pass

    @abstractmethod
    def get_current_step(self, experiment_id: str) -> dict[str, Any] | None:
        """获取当前步骤

        Args:
            experiment_id: 实验ID

        Returns:
            步骤信息字典
        """
        pass

    @abstractmethod
    def get_progress(self, experiment_id: str) -> ProgressInfo | None:
        """获取实验进度

        Args:
            experiment_id: 实验ID

        Returns:
            进度信息
        """
        pass

    @abstractmethod
    def complete_experiment(self, experiment_id: str) -> ExperimentResponse:
        """完成实验

        Args:
            experiment_id: 实验ID

        Returns:
            实验响应
        """
        pass

    @abstractmethod
    def pause_experiment(self, experiment_id: str) -> ExperimentResponse:
        """暂停实验

        Args:
            experiment_id: 实验ID

        Returns:
            实验响应
        """
        pass

    @abstractmethod
    def resume_experiment(self, experiment_id: str) -> ExperimentResponse:
        """恢复实验

        Args:
            experiment_id: 实验ID

        Returns:
            实验响应
        """
        pass

    @abstractmethod
    def get_record(self, experiment_id: str) -> UserRecord | None:
        """获取实验记录

        Args:
            experiment_id: 实验ID

        Returns:
            用户记录
        """
        pass

    @abstractmethod
    def validate_experiment(self, template: ExperimentTemplate) -> tuple[bool, list[str]]:
        """验证实验模板

        Args:
            template: 实验模板

        Returns:
            (是否有效, 错误列表)
        """
        pass
