"""用户记录数据模型"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Mistake(BaseModel):
    """错误记录"""

    step_id: str = Field(..., description="步骤ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    error_type: str = Field(..., description="错误类型")
    description: str = Field(..., description="错误描述")
    hint: str = Field(default="", description="提示信息")
    severity: str = Field(default="warning", description="严重程度: info/warning/severe/critical")


class StepRecord(BaseModel):
    """步骤记录"""

    step_id: str = Field(..., description="步骤ID")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    passed: bool = Field(default=False, description="是否通过")
    user_input: dict[str, Any] = Field(default_factory=dict, description="用户输入")
    mistakes: list[Mistake] = Field(default_factory=list, description="错误列表")
    attempts: int = Field(default=1, description="尝试次数")
    score: int = Field(default=0, description="步骤得分")

    @property
    def duration_seconds(self) -> float | None:
        """计算步骤耗时(秒)"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class ExperimentScore(BaseModel):
    """实验评分"""

    total: int = Field(default=0, description="总分", ge=0, le=100)
    scientific: int = Field(default=0, description="科学性得分", ge=0, le=100)
    procedural: int = Field(default=0, description="流程性得分", ge=0, le=100)
    safety: int = Field(default=0, description="安全性得分", ge=0, le=100)
    details: dict[str, Any] = Field(default_factory=dict, description="评分详情")


class UserRecord(BaseModel):
    """用户实验记录"""

    record_id: str = Field(..., description="记录唯一标识符")
    user_id: str = Field(..., description="用户ID")
    experiment_id: str = Field(..., description="实验ID")
    experiment_title: str = Field(..., description="实验名称")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    status: str = Field(default="in_progress", description="状态: in_progress/completed/abandoned")
    current_step_index: int = Field(default=0, description="当前步骤索引")
    step_records: list[StepRecord] = Field(default_factory=list, description="步骤记录列表")
    score: ExperimentScore = Field(default_factory=ExperimentScore, description="评分")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文变量")
    curve_data: dict[str, Any] = Field(default_factory=dict, description="曲线数据")
    mistakes_summary: list[Mistake] = Field(default_factory=list, description="错误汇总")
    version: str = Field(default="1.0.0", description="记录格式版本")

    @property
    def total_duration_seconds(self) -> float | None:
        """计算总耗时(秒)"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def total_mistakes(self) -> int:
        """统计总错误数"""
        return sum(len(record.mistakes) for record in self.step_records)

    @property
    def completion_rate(self) -> float:
        """计算完成率"""
        if not self.step_records:
            return 0.0
        passed_steps = sum(1 for record in self.step_records if record.passed)
        return passed_steps / len(self.step_records) * 100

    def add_step_record(self, step_id: str) -> StepRecord:
        """添加步骤记录"""
        record = StepRecord(step_id=step_id)
        self.step_records.append(record)
        return record

    def get_current_step_record(self) -> StepRecord | None:
        """获取当前步骤记录"""
        if 0 <= self.current_step_index < len(self.step_records):
            return self.step_records[self.current_step_index]
        return None

    def add_mistake(self, mistake: Mistake) -> None:
        """添加错误到当前步骤"""
        current_record = self.get_current_step_record()
        if current_record:
            current_record.mistakes.append(mistake)
        self.mistakes_summary.append(mistake)

    def complete_experiment(self) -> None:
        """标记实验完成"""
        self.status = "completed"
        self.completed_at = datetime.now()

    @property
    def start_time(self) -> datetime:
        """兼容旧字段名称"""
        return self.started_at

    @start_time.setter
    def start_time(self, value: datetime) -> None:
        self.started_at = value

    @property
    def end_time(self) -> datetime | None:
        """兼容旧字段名称"""
        return self.completed_at

    @end_time.setter
    def end_time(self, value: datetime | None) -> None:
        self.completed_at = value

    @property
    def final_score(self) -> int:
        """最终得分(与score.total保持一致)"""
        return int(self.score.total)

    @final_score.setter
    def final_score(self, value: int) -> None:
        self.score.total = int(value)
