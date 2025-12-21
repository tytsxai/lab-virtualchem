"""用户记录数据模型"""

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

_SAFE_KEY_MAX_LEN = 64


def _is_json_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validate_json_value(value: Any, *, depth: int = 0, max_depth: int = 5) -> None:
    if depth > max_depth:
        raise ValueError("嵌套层级过深")
    if _is_json_primitive(value):
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1, max_depth=max_depth)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("字典 key 必须为字符串")
            _validate_record_key(k)
            _validate_json_value(v, depth=depth + 1, max_depth=max_depth)
        return
    raise ValueError(f"不支持的值类型: {type(value).__name__}")


def _validate_record_key(key: str) -> None:
    if not isinstance(key, str):
        raise ValueError("字典 key 必须为字符串")
    if not key or len(key) > _SAFE_KEY_MAX_LEN:
        raise ValueError("key 长度不合法")
    if not key.replace("_", "").replace("-", "").isalnum():
        raise ValueError("key 只能包含字母数字、下划线或连字符")


def _validate_record_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("必须是对象(dict)")
    for k, v in value.items():
        if not isinstance(k, str):
            raise ValueError("字典 key 必须为字符串")
        _validate_record_key(k)
        _validate_json_value(v)
    return value


class Mistake(BaseModel):
    """错误记录"""

    step_id: str = Field(..., description="步骤ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    error_type: str = Field(..., description="错误类型")
    description: str = Field(..., description="错误描述")
    hint: str = Field(default="", description="提示信息")
    severity: str = Field(
        default="warning", description="严重程度: info/warning/severe/critical"
    )


class StepRecord(BaseModel):
    """步骤记录"""

    model_config = ConfigDict(validate_assignment=True)

    step_id: str = Field(..., description="步骤ID")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    passed: bool = Field(default=False, description="是否通过")
    user_input: dict[str, Any] = Field(default_factory=dict, description="用户输入")
    mistakes: list[Mistake] = Field(default_factory=list, description="错误列表")
    attempts: int = Field(default=1, description="尝试次数")
    score: int = Field(default=0, description="步骤得分")

    @field_validator("user_input", mode="before")
    @classmethod
    def validate_user_input(cls, v: Any) -> dict[str, Any]:
        return _validate_record_mapping(v)

    @property
    def duration_seconds(self) -> float | None:
        """计算步骤耗时(秒)"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class ExperimentScore(BaseModel):
    """实验评分"""

    model_config = ConfigDict(validate_assignment=True)

    total: int = Field(default=0, description="总分", ge=0, le=100)
    scientific: int = Field(default=0, description="科学性得分", ge=0, le=100)
    procedural: int = Field(default=0, description="流程性得分", ge=0, le=100)
    safety: int = Field(default=0, description="安全性得分", ge=0, le=100)
    details: dict[str, Any] = Field(default_factory=dict, description="评分详情")

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, v: Any) -> dict[str, Any]:
        return _validate_record_mapping(v)


class CurvePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: list[float] | None = None
    y: list[float] | None = None
    volume: list[float] | None = None
    ph: list[float] | None = None
    x_label: str | None = None
    y_label: str | None = None
    x_unit: str | None = None
    y_unit: str | None = None

    @field_validator("x", "y", "volume", "ph", mode="before")
    @classmethod
    def validate_numeric_series(cls, v: Any) -> list[float] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("必须是数组(list)")
        try:
            return [float(item) for item in v]
        except (TypeError, ValueError) as exc:
            raise ValueError("数组元素必须为数字") from exc

    @field_validator("y")
    @classmethod
    def validate_xy_lengths(cls, y: list[float] | None, info) -> list[float] | None:
        x = info.data.get("x")
        if x is not None and y is not None and len(x) != len(y):
            raise ValueError("x 与 y 长度必须一致")
        return y

    @field_validator("ph")
    @classmethod
    def validate_volume_ph_lengths(
        cls, ph: list[float] | None, info
    ) -> list[float] | None:
        volume = info.data.get("volume")
        if volume is not None and ph is not None and len(volume) != len(ph):
            raise ValueError("volume 与 ph 长度必须一致")
        return ph

    @field_validator("y_unit")
    @classmethod
    def validate_payload_has_series(cls, v: str | None, info) -> str | None:
        return v

    @model_validator(mode="after")
    def validate_has_series(self) -> "CurvePayload":
        has_xy = self.x is not None or self.y is not None
        has_vph = self.volume is not None or self.ph is not None
        if not (has_xy or has_vph):
            raise ValueError("曲线数据必须包含 (x,y) 或 (volume,ph)")
        return self


class UserRecord(BaseModel):
    """用户实验记录"""

    model_config = ConfigDict(validate_assignment=True)

    record_id: str = Field(..., description="记录唯一标识符")
    user_id: str = Field(..., description="用户ID")
    experiment_id: str = Field(..., description="实验ID")
    experiment_title: str = Field(default="", description="实验名称")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    status: str = Field(
        default="in_progress", description="状态: in_progress/completed/abandoned"
    )
    current_step_index: int = Field(default=0, description="当前步骤索引")
    step_records: list[StepRecord] = Field(
        default_factory=list, description="步骤记录列表"
    )
    score: ExperimentScore = Field(default_factory=ExperimentScore, description="评分")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文变量")
    curve_data: dict[str, Any] = Field(default_factory=dict, description="曲线数据")
    mistakes_summary: list[Mistake] = Field(
        default_factory=list, description="错误汇总"
    )
    version: str = Field(default="1.0.0", description="记录格式版本")

    @field_validator("context", mode="before")
    @classmethod
    def validate_context(cls, v: Any) -> dict[str, Any]:
        return _validate_record_mapping(v)

    @field_validator("curve_data", mode="before")
    @classmethod
    def validate_curve_data(cls, v: Any) -> dict[str, Any]:
        mapping = _validate_record_mapping(v)
        errors: list[Exception] = []
        normalized: dict[str, Any] = {}
        for key, payload in mapping.items():
            try:
                validated = CurvePayload.model_validate(payload)
                normalized[key] = validated.model_dump(exclude_none=True)
            except ValidationError as exc:
                errors.append(exc)
        if errors:
            raise ValueError("curve_data 不符合 schema") from errors[0]
        return normalized

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
