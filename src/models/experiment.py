"""实验模板数据模型"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CheckType(str, Enum):
    """检查点类型"""

    CONFIRM = "confirm"  # 确认操作
    INPUT = "input"  # 输入数值
    SELECT = "select"  # 选择选项
    SEQUENCE = "sequence"  # 依赖关系
    EXPRESSION = "expression"  # 表达式检查


class CurveType(str, Enum):
    """曲线类型"""

    TITRATION_PH = "titration_ph"  # 滴定pH曲线
    TEMP_TIME = "temp_time"  # 温度-时间曲线
    VOLUME_TIME = "volume_time"  # 体积-时间曲线
    PRESSURE_TEMP = "pressure_temp"  # 压强-温度曲线


class InputSpec(BaseModel):
    """输入规范"""

    key: str = Field(..., description="变量名")
    label: str = Field(..., description="显示标签")
    input_type: str = Field(default="float", description="输入类型: int/float/string/list")
    range: list[float] | None = Field(default=None, description="有效范围 [min, max]")
    unit: str | None = Field(default=None, description="单位")
    options: list[dict[str, Any]] | None = Field(default=None, description="选项列表(用于select)")
    multi_select: bool = Field(default=False, description="是否允许多选(用于select)")

    @field_validator("input_type")
    @classmethod
    def validate_input_type(cls, v: str) -> str:
        """验证输入类型"""
        allowed = ["int", "float", "string", "bool", "list"]
        if v not in allowed:
            raise ValueError(f"input_type 必须是 {allowed} 之一")
        return v


class CheckPoint(BaseModel):
    """检查点定义"""

    type: CheckType = Field(..., description="检查点类型")
    fail_hint: str = Field(default="", description="失败提示")
    input: InputSpec | None = Field(default=None, description="输入规范(用于input/select)")
    require: list[str] | None = Field(default=None, description="前置步骤ID列表(用于sequence)")
    correct_value: Any | None = Field(default=None, description="正确答案(用于验证)")
    expression: str | None = Field(default=None, description="表达式(用于expression类型)")
    interactive_check: dict[str, Any] | None = Field(default=None, description="交互式检查配置")

    @field_validator("input")
    @classmethod
    def validate_input_for_type(cls, v: InputSpec | None, info: Any) -> InputSpec | None:
        """验证输入规范与类型匹配"""
        check_type = info.data.get("type")
        if check_type in [CheckType.INPUT, CheckType.SELECT] and v is None:
            raise ValueError(f"{check_type} 类型必须提供 input 规范")
        return v

    @field_validator("require")
    @classmethod
    def validate_require_for_sequence(cls, v: list[str] | None, info: Any) -> list[str] | None:
        """验证依赖关系"""
        check_type = info.data.get("type")
        if check_type == CheckType.SEQUENCE and (v is None or len(v) == 0):
            raise ValueError("sequence 类型必须提供 require 列表")
        return v


class Hint(BaseModel):
    """提示信息"""

    text: str = Field(..., description="提示内容")
    trigger: str | None = Field(default=None, description="触发条件(表达式)")


class Step(BaseModel):
    """实验步骤"""

    id: str = Field(..., description="步骤唯一标识符")
    text: str = Field(..., description="步骤描述")
    media: dict[str, str] | None = Field(default=None, description="媒体资源: image/video路径")
    check: CheckPoint | None = Field(default=None, description="检查点")
    hints: list[Hint] = Field(default_factory=list, description="提示列表")
    safety_level: str = Field(default="info", description="安全等级: info/warning/severe/critical")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证ID格式"""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("id 必须是字母数字下划线组合")
        return v


class Curve(BaseModel):
    """曲线配置"""

    id: str = Field(..., description="曲线唯一标识符")
    type: CurveType = Field(..., description="曲线类型")
    params: dict[str, Any] = Field(..., description="曲线参数")
    x_label: str = Field(default="X", description="X轴标签")
    y_label: str = Field(default="Y", description="Y轴标签")
    x_unit: str | None = Field(default=None, description="X轴单位")
    y_unit: str | None = Field(default=None, description="Y轴单位")


class Goal(BaseModel):
    """实验目标"""

    name: str = Field(..., description="目标名称")
    metric: str = Field(..., description="度量指标(变量名)")
    lte: float | None = Field(default=None, description="小于等于")
    gte: float | None = Field(default=None, description="大于等于")
    eq: float | None = Field(default=None, description="等于")

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        """验证度量指标"""
        if not v.replace("_", "").isalnum():
            raise ValueError("metric 必须是字母数字下划线组合")
        return v


class ScoreRule(BaseModel):
    """评分规则"""

    when: str = Field(..., description="条件表达式")
    then: int = Field(..., description="得分", ge=0, le=100)


class Reagent(BaseModel):
    """试剂信息"""

    id: str = Field(..., description="试剂唯一标识符")
    name: str = Field(..., description="试剂名称")
    amount: str = Field(..., description="用量")
    hazard_level: str = Field(default="info", description="危害等级")


class ExperimentTemplate(BaseModel):
    """实验模板"""

    id: str = Field(..., description="实验唯一标识符")
    title: str = Field(..., description="实验名称")
    title_en: str | None = Field(default=None, description="英文名称")
    description: str = Field(default="", description="实验描述")
    category: str = Field(default="", description="实验分类")
    level: str = Field(default="basic", description="难度等级: basic/intermediate/advanced")
    difficulty: str | None = Field(default=None, description="难度等级(兼容字段)")
    duration_min: int = Field(default=45, description="预计时长(分钟)", gt=0)
    duration_minutes: int | None = Field(default=None, description="预计时长(兼容字段)")
    goals: list[Goal] = Field(default_factory=list, description="实验目标")
    prerequisites: list[str] = Field(default_factory=list, description="前置实验ID")
    reagents: list[Reagent] = Field(default_factory=list, description="试剂列表")
    steps: list[Step] = Field(..., description="实验步骤", min_length=1)
    curves: list[Curve] = Field(default_factory=list, description="曲线配置")
    score_rules: list[ScoreRule] = Field(default_factory=list, description="评分规则")
    version: str = Field(default="1.0.0", description="模板版本")

    def __init__(self, **data: Any):
        """初始化,处理兼容性字段"""
        # 兼容difficulty字段
        if "difficulty" in data and "level" not in data:
            data["level"] = data["difficulty"]
        elif "difficulty" not in data and "level" in data:
            data["difficulty"] = data["level"]

        # 兼容duration_minutes字段
        if "duration_minutes" in data and "duration_min" not in data:
            data["duration_min"] = data["duration_minutes"]
        elif "duration_minutes" not in data and "duration_min" in data:
            data["duration_minutes"] = data["duration_min"]

        super().__init__(**data)

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """验证难度等级"""
        allowed = ["basic", "intermediate", "advanced"]
        if v not in allowed:
            raise ValueError(f"level 必须是 {allowed} 之一")
        return v

    @field_validator("steps")
    @classmethod
    def validate_step_ids_unique(cls, v: list[Step]) -> list[Step]:
        """验证步骤ID唯一性"""
        ids = [step.id for step in v]
        if len(ids) != len(set(ids)):
            raise ValueError("步骤ID必须唯一")
        return v

    def get_step_by_id(self, step_id: str) -> Step | None:
        """根据ID获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def validate_dependencies(self) -> list[str]:
        """验证步骤依赖关系是否有效"""
        errors = []
        step_ids = {step.id for step in self.steps}

        for step in self.steps:
            if step.check and step.check.type == CheckType.SEQUENCE and step.check.require:
                for required_id in step.check.require:
                    if required_id not in step_ids:
                        errors.append(f"步骤 {step.id} 依赖的步骤 {required_id} 不存在")

        return errors
