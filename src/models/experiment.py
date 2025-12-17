"""实验模板数据模型"""

from __future__ import annotations

import json
import statistics
import warnings
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic_core import InitErrorDetails, PydanticCustomError


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
    input_type: str = Field(
        default="float", description="输入类型: int/float/string/list"
    )
    range: list[float] | None = Field(default=None, description="有效范围 [min, max]")
    unit: str | None = Field(default=None, description="单位")
    options: list[dict[str, Any]] | None = Field(
        default=None, description="选项列表(用于select)"
    )
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
    input: InputSpec | None = Field(
        default=None, description="输入规范(用于input/select)"
    )
    require: list[str] | None = Field(
        default=None, description="前置步骤ID列表(用于sequence)"
    )
    correct_value: Any | None = Field(default=None, description="正确答案(用于验证)")
    expression: str | None = Field(
        default=None, description="表达式(用于expression类型)"
    )
    interactive_check: dict[str, Any] | None = Field(
        default=None, description="交互式检查配置"
    )

    @field_validator("input")
    @classmethod
    def validate_input_for_type(
        cls, v: InputSpec | None, info: Any
    ) -> InputSpec | None:
        """验证输入规范与类型匹配"""
        check_type = info.data.get("type")
        if check_type in [CheckType.INPUT, CheckType.SELECT] and v is None:
            raise ValueError(f"{check_type} 类型必须提供 input 规范")
        return v

    @field_validator("require")
    @classmethod
    def validate_require_for_sequence(
        cls, v: list[str] | None, info: Any
    ) -> list[str] | None:
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
    media: dict[str, str] | None = Field(
        default=None, description="媒体资源: image/video路径"
    )
    check: CheckPoint | None = Field(default=None, description="检查点")
    hints: list[Hint] = Field(default_factory=list, description="提示列表")
    safety_level: str = Field(
        default="info", description="安全等级: info/warning/severe/critical"
    )

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

    model_config = ConfigDict(validate_assignment=True, extra="allow")
    allow_empty_steps: ClassVar[bool] = False

    id: str = Field(
        default_factory=lambda: f"exp_{uuid4().hex[:8]}", description="实验唯一标识符"
    )
    title: str = Field(default="实验", description="实验名称")
    title_en: str | None = Field(default=None, description="英文名称")
    description: str = Field(default="", description="实验描述")
    category: str = Field(default="", description="实验分类")
    experiment_type: str = Field(default="general", description="实验类型")
    level: str = Field(
        default="basic", description="难度等级: basic/intermediate/advanced"
    )
    difficulty: str | None = Field(default=None, description="难度等级(兼容字段)")
    duration_min: int = Field(default=45, description="预计时长(分钟)", gt=0)
    duration_minutes: int | None = Field(default=None, description="预计时长(兼容字段)")
    goals: list[Goal] = Field(default_factory=list, description="实验目标")
    prerequisites: list[str] = Field(default_factory=list, description="前置实验ID")
    reagents: list[Reagent] = Field(default_factory=list, description="试剂列表")
    steps: list[Step] = Field(
        default_factory=list, description="实验步骤", min_length=0
    )
    curves: list[Curve] = Field(default_factory=list, description="曲线配置")
    score_rules: list[ScoreRule] = Field(default_factory=list, description="评分规则")
    version: str = Field(default="1.0.0", description="模板版本")
    # 运行态字段
    data_points: dict[str, Any] = Field(
        default_factory=dict, description="实验数据记录"
    )
    observations: list[str] = Field(default_factory=list, description="观察记录")
    titration_curve: dict[str, list[float]] = Field(
        default_factory=lambda: {"volume": [], "ph": []}, description="滴定曲线数据"
    )
    state: str = Field(default="initialized", description="实验状态")
    start_time: datetime | None = Field(default=None, description="实验开始时间")
    end_time: datetime | None = Field(default=None, description="实验结束时间")
    equipment_checked: bool = Field(default=True, description="是否已完成设备检查")
    required_protection: set[str] = Field(
        default_factory=lambda: {"goggles", "gloves", "lab_coat"}
    )
    protection_worn: set[str] = Field(
        default_factory=set, description="已佩戴的防护装备"
    )
    safety_alerts: list[str] = Field(default_factory=list, description="安全警报")
    safety_log: list[dict[str, Any]] = Field(
        default_factory=list, description="安全事件记录"
    )
    warnings_log: list[str] = Field(default_factory=list, description="警告记录")
    current_temperature: float | None = Field(default=None, description="当前温度")
    heating: bool = Field(default=False, description="是否正在加热")
    cooling_required: bool = Field(default=False, description="是否需要冷却后继续操作")
    ventilation_status: str | None = Field(default=None, description="通风状态")
    reagents_used: list[str] = Field(default_factory=list, description="已使用试剂")
    waste_generated: bool = Field(default=False, description="是否产生废液")

    def __init__(self, **data: Any):
        """初始化,处理兼容性字段"""
        if "id" not in data:
            data["id"] = f"exp_{uuid4().hex[:8]}"
        if "title" not in data:
            data["title"] = "实验"
        if "experiment_type" not in data and "category" in data:
            data["experiment_type"] = data.get("category", "general")

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

        if (
            not getattr(self.__class__, "allow_empty_steps", False)
            and "steps" in self.model_fields_set
            and len(self.steps) == 0
        ):
            error = InitErrorDetails(
                type=PydanticCustomError("value_error", "steps 至少需要一个步骤"),
                loc=("steps",),
                input=self.steps,
            )
            raise ValidationError.from_exception_data(self.__class__.__name__, [error])

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
            if (
                step.check
                and step.check.type == CheckType.SEQUENCE
                and step.check.require
            ):
                for required_id in step.check.require:
                    if required_id not in step_ids:
                        errors.append(f"步骤 {step.id} 依赖的步骤 {required_id} 不存在")

        return errors

    # --------- 运行与报告相关方法 ---------
    def prepare(self) -> bool:
        """准备实验"""
        self.state = "prepared"
        self._log_safety("实验准备完成", level="info")
        return True

    def start(self) -> bool:
        """开始实验"""
        if not self.equipment_checked:
            raise RuntimeError("设备检查未通过，无法开始实验")
        self.state = "running"
        if self.start_time is None:
            self.start_time = datetime.now()
        self._log_safety("实验开始", level="info")
        return True

    def abort(self) -> None:
        """中止实验"""
        self.state = "aborted"
        self.heating = False
        self._log_safety("实验已中止", level="warning")

    def complete(self) -> bool:
        """完成实验"""
        self.state = "completed"
        self.end_time = datetime.now()
        self.cooling_required = False
        self.heating = False
        if self.waste_generated:
            self._add_warning("请按规定处理废液和固体废弃物")
        self._log_safety("实验完成", level="info")
        return True

    def record_data(self, key: str, value: Any) -> None:
        """记录实验数据"""
        self.data_points[key] = value

    def record_observation(self, observation: str) -> None:
        """记录观察"""
        self.observations.append(observation)

    def record_titration_point(self, volume: float, ph: float) -> None:
        """记录滴定曲线数据点"""
        self.titration_curve.setdefault("volume", []).append(volume)
        self.titration_curve.setdefault("ph", []).append(ph)

    def get_chart_data(self) -> dict[str, list[Any]]:
        """获取图表数据"""
        numeric_items = [
            (k, v) for k, v in self.data_points.items() if isinstance(v, (int, float))
        ]
        labels = [k for k, _ in numeric_items]
        values = [v for _, v in numeric_items]
        return {"labels": labels, "values": values}

    def get_curve_data(self) -> dict[str, list[float]]:
        """获取曲线数据"""
        return {
            "volume": list(self.titration_curve.get("volume", [])),
            "ph": list(self.titration_curve.get("ph", [])),
        }

    def _calculate_average_volume(self) -> float | None:
        """计算平均体积"""
        values = [
            v
            for k, v in self.data_points.items()
            if k.lower().startswith("v") and isinstance(v, (int, float))
        ]
        if values:
            return statistics.mean(values)
        return None

    def _build_calculations(self) -> dict[str, Any]:
        """生成计算结果"""
        calculations: dict[str, Any] = {}
        avg = self._calculate_average_volume()
        if avg is not None:
            calculations["average_volume"] = avg
        return calculations

    def _filtered_data(
        self, include_fields: list[str] | None, anonymous: bool
    ) -> dict[str, Any]:
        data = dict(self.data_points)
        if include_fields is not None:
            data = {k: v for k, v in data.items() if k in include_fields}
        if anonymous:
            for sensitive in ["student_id", "student_name", "user_id"]:
                data.pop(sensitive, None)
        return data

    def generate_report(
        self,
        template: str | None = None,
        include_fields: list[str] | None = None,
        sections_order: list[str] | None = None,
        anonymous: bool = False,
        watermark: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """生成实验报告"""
        report: dict[str, Any] = {
            "experiment_type": self.experiment_type,
            "title": self.title,
            "state": self.state,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "data": self._filtered_data(include_fields, anonymous),
            "observations": list(self.observations),
            "template": template or "standard",
        }
        calculations = self._build_calculations()
        if calculations:
            report["calculations"] = calculations

        if watermark:
            report["watermark"] = watermark

        if sections_order:
            sections: list[dict[str, Any]] = []
            section_content = {
                "data": report["data"],
                "observations": report.get("observations", []),
                "calculations": report.get("calculations", {}),
                "conclusion": "实验完成" if self.state == "completed" else "进行中",
            }
            for name in sections_order:
                sections.append(
                    {"name": name, "content": section_content.get(name, {})}
                )
            report["sections"] = sections

        if options:
            report["options"] = options
        return report

    def _to_text_report(self, report: dict[str, Any]) -> str:
        lines = [
            "实验报告",
            f"实验名称: {report.get('title', '')}",
            f"实验类型: {report.get('experiment_type', '')}",
            f"状态: {report.get('state', '')}",
        ]
        if report.get("start_time"):
            lines.append(f"开始时间: {report['start_time']}")
        if report.get("end_time"):
            lines.append(f"结束时间: {report['end_time']}")
        lines.append("数据:")
        for k, v in report.get("data", {}).items():
            lines.append(f"  - {k}: {v}")
        if report.get("observations"):
            lines.append("观察:")
            for obs in report["observations"]:
                lines.append(f"  * {obs}")
        if report.get("calculations"):
            lines.append("计算结果:")
            for k, v in report["calculations"].items():
                lines.append(f"  - {k}: {v}")
        if watermark := report.get("watermark"):
            lines.append(f"水印: {watermark}")
        return "\n".join(lines)

    def _to_html_report(self, report: dict[str, Any]) -> str:
        rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>"
            for k, v in report.get("data", {}).items()
        )
        observations = "".join(
            f"<li>{obs}</li>" for obs in report.get("observations", [])
        )
        return f"""
<html>
  <body>
    <h1>{report.get("title", "")} - 实验报告</h1>
    <p>状态: {report.get("state", "")}</p>
    <table><thead><tr><th>字段</th><th>值</th></tr></thead><tbody>{rows}</tbody></table>
    <h2>观察</h2>
    <ul>{observations}</ul>
  </body>
</html>
""".strip()

    def _to_markdown_report(self, report: dict[str, Any]) -> str:
        header = "# 实验报告\n\n"
        info = f"- 实验名称: {report.get('title', '')}\n- 实验类型: {report.get('experiment_type', '')}\n"
        table = "| 字段 | 值 |\n| --- | --- |\n"
        for k, v in report.get("data", {}).items():
            table += f"| {k} | {v} |\n"
        return header + info + "\n" + table

    def export_report(self, format: str = "json", **kwargs: Any) -> str:
        """导出报告为字符串"""
        format_lower = (format or "json").lower()
        report = self.generate_report(**kwargs)
        if format_lower == "json":
            return json.dumps(report, ensure_ascii=False)
        if format_lower in {"text", "txt"}:
            return self._to_text_report(report)
        if format_lower == "html":
            return self._to_html_report(report)
        if format_lower == "markdown":
            return self._to_markdown_report(report)
        # 默认返回JSON
        return json.dumps(report, ensure_ascii=False)

    def save_report(
        self, output_path: Path | str, format: str = "json", version: int | None = None
    ) -> Path:
        """保存报告到文件"""
        report = self.generate_report()
        if version is not None:
            report["version"] = version
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if format.lower() == "json":
            path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            formatter = {
                "text": self._to_text_report,
                "txt": self._to_text_report,
                "html": self._to_html_report,
                "markdown": self._to_markdown_report,
            }.get(format.lower(), lambda r: json.dumps(r, ensure_ascii=False))
            path.write_text(formatter(report), encoding="utf-8")
        return path

    def validate_report(self, report: dict[str, Any]) -> tuple[bool, list[str]]:
        """验证报告有效性"""
        errors: list[str] = []
        for field in ["experiment_type", "state", "data"]:
            if field not in report:
                errors.append(f"缺少必需字段: {field}")
        if not report.get("data"):
            errors.append("报告缺少必要的实验数据")
        if not report.get("start_time"):
            errors.append("缺少开始时间")
        if not report.get("end_time"):
            errors.append("缺少结束时间")
        return (len(errors) == 0, errors)

    # --------- 安全相关方法 ---------
    def heat(
        self, temperature: float, duration: int = 0, ventilation: bool = True
    ) -> bool:
        """加热操作"""
        if temperature > 200:
            self._log_safety("温度超出安全阈值", level="error")
            raise ValueError("温度超过安全范围，无法继续加热")
        self.current_temperature = temperature
        self.heating = True
        self.cooling_required = True
        if temperature >= 90:
            self._add_alert("温度接近上限，请注意安全")
        if not ventilation:
            self.ventilation_status = "required"
            self._add_warning("需要保持良好通风后再继续操作")
            warnings.warn("通风不足，存在安全风险", UserWarning)
        self._log_safety(f"加热至 {temperature}℃, 持续 {duration} 分钟", level="info")
        return True

    def get_current_temperature(self) -> float | None:
        """获取当前温度"""
        return self.current_temperature

    def set_temperature(self, temperature: float) -> None:
        """设置当前温度(监控用)"""
        self.current_temperature = temperature
        if temperature >= 90:
            self._add_alert("温度接近或超过安全阈值，请降温")
        self._log_safety(f"温度更新为 {temperature}℃", level="info")

    def cool_down(self) -> None:
        """执行冷却"""
        self.current_temperature = 25.0
        self.heating = False
        self.cooling_required = False
        self._log_safety("冷却完成，温度恢复安全范围", level="info")

    def add_reagent(
        self, name: str, amount: float | None = None, protection: bool = True
    ) -> bool:
        """添加试剂，带简单安全检查"""
        if self.cooling_required:
            self._add_warning("冷却尚未完成，请注意潜在风险")
            warnings.warn("冷却未完成，添加试剂可能不安全", UserWarning)
        if amount is not None and amount > 300:
            self._log_safety("试剂用量超出安全范围", level="error")
            raise ValueError("试剂用量超出安全范围")
        incompatible_pairs = {
            ("concentrated_hcl", "concentrated_naoh"),
            ("hcl", "naoh"),
        }
        normalized = name.lower()
        for added in self.reagents_used:
            if (normalized, added.lower()) in incompatible_pairs or (
                added.lower(),
                normalized,
            ) in incompatible_pairs:
                self._add_warning("试剂兼容性存在风险，请确认操作顺序")
                warnings.warn("试剂可能不兼容", UserWarning)
        if "h2so4" in (r.lower() for r in self.reagents_used) and normalized == "kmno4":
            self._log_safety("危险的氧化还原组合被阻止", level="error")
            raise ValueError("危险试剂组合，禁止继续")
        if normalized in {"mercury_compound", "toxic_reagent"}:
            self._add_warning("使用有毒试剂，请加强通风和个人防护")
            warnings.warn("有毒试剂，注意防护", UserWarning)
        if normalized == "volatile_solvent":
            self.ventilation_status = "required"
            warnings.warn("使用挥发性试剂，请开启通风", UserWarning)
        if not protection and normalized.startswith("concentrated"):
            warnings.warn("未佩戴防护装备处理高危试剂", UserWarning)
        self.reagents_used.append(name)
        if {"hcl", "naoh"} <= {r.lower() for r in self.reagents_used}:
            self.waste_generated = True
        self._log_safety(f"添加试剂: {name}, 量: {amount or '未指定'}", level="info")
        return True

    def get_safety_tips(self) -> list[str]:
        """获取安全提示"""
        tips = [
            "保持良好通风",
            "佩戴护目镜和手套",
            "熟悉紧急停机流程",
        ]
        if self.ventilation_status == "required":
            tips.append("当前实验需要开启通风柜或加强通风")
        if any(r.lower().startswith("mercury") for r in self.reagents_used):
            tips.append("处理汞化合物时确保佩戴合适的防护装备并远离加热源")
        return tips

    def get_required_protection(self) -> set[str]:
        """返回必需的防护装备"""
        return set(self.required_protection)

    def emergency_stop(self) -> None:
        """紧急停止实验"""
        self.state = "emergency_stopped"
        self.heating = False
        self._log_safety("触发紧急停止", level="critical")

    def report_incident(self, incident_type: str, details: str | None = None) -> None:
        """报告安全事件"""
        message = f"事故报告: {incident_type}"
        if details:
            message += f" - {details}"
        self._add_alert(message)
        self._log_safety(message, level="warning")

    def get_emergency_response(self, incident_type: str) -> str | None:
        """获取应急指导"""
        responses = {
            "spill": "立即中和/吸附溢出物，使用大量水稀释，按照废液流程处理",
            "fire": "使用灭火器扑灭火源，切断电源并撤离区域",
            "skin_contact": "立即用流动清水冲洗15分钟以上，并脱去污染衣物",
        }
        return responses.get(incident_type, "遵循实验室应急预案行事")

    def use_burette(self, rinse: bool = True) -> bool:
        """使用滴定管，检查是否已润洗"""
        if not rinse:
            self._add_warning("滴定管未润洗，可能影响结果")
            warnings.warn("使用滴定管前应润洗，注意操作顺序", UserWarning)
        return True

    def neutralize(self) -> bool:
        """中和处理"""
        self.waste_generated = True
        self._log_safety("已执行中和步骤", level="info")
        return True

    def get_completion_reminders(self) -> list[str]:
        """获取完成后的提醒"""
        reminders = ["整理实验台，关闭设备"]
        if self.waste_generated:
            reminders.append("请按照规范收集并处理废液")
        return reminders

    def get_equipment_checklist(self) -> list[str]:
        """设备检查清单"""
        return ["burette", "flask", "pipette", "balance"]

    def check_equipment(self) -> None:
        """标记设备检查通过"""
        self.equipment_checked = True
        self._log_safety("设备检查完成", level="info")

    def wear_protection(self, items: list[str]) -> None:
        """佩戴防护装备"""
        self.protection_worn.update(items)
        missing = self.required_protection - self.protection_worn
        if missing:
            self._add_warning(f"仍缺少防护装备: {', '.join(missing)}")
        else:
            self._log_safety("防护装备已全部到位", level="info")

    def get_all_warnings(self) -> list[str]:
        """获取所有警告信息"""
        return list(self.warnings_log)

    def get_safety_log(self) -> list[dict[str, Any]]:
        """获取安全日志"""
        return list(self.safety_log)

    def get_safety_alerts(self) -> list[str]:
        """获取安全警报"""
        # 去重保序
        seen = set()
        alerts: list[str] = []
        for alert in self.safety_alerts:
            if alert not in seen:
                seen.add(alert)
                alerts.append(alert)
        return alerts

    def calculate_safety_score(self) -> int:
        """计算安全评分"""
        score = 100
        score -= min(30, len(self.warnings_log) * 10)
        score -= min(20, len(self.safety_alerts) * 5)
        if not self.equipment_checked:
            score -= 30
        missing_protection = self.required_protection - self.protection_worn
        if missing_protection:
            score -= 20
        return max(0, min(100, score))

    def handle_emergency(self, emergency_type: str, **_kwargs: Any) -> str:
        """应急处理入口"""
        self.emergency_stop()
        responses = {
            "fire": "启动灭火器，切断气源/电源并疏散人员",
            "skin_contact": "立即用大量清水冲洗15分钟以上并就医",
            "chemical_exposure": "移至通风处，移除污染物并监控生命体征",
        }
        return responses.get(emergency_type, "按应急预案处理并通知负责人")

    def report_malfunction(self, equipment: str, issue: str | None = None) -> None:
        """报告设备故障"""
        message = f"设备故障: {equipment}"
        if issue:
            message += f" - {issue}"
        self.state = "paused"
        self._add_alert(message)
        self._log_safety(message, level="warning")
        if issue and "过热" in issue:
            self.state = "emergency_stopped"

    def get_malfunction_guidance(self, equipment: str) -> str:
        """获取设备故障处理指导"""
        guidance = {
            "heating_mantle": "立即断电，检查温度探头，待冷却后联系设备员",
            "burette": "检查是否漏液，确保阀门关闭且润洗到位",
        }
        return guidance.get(equipment, "请根据设备手册进行故障排查")

    # --------- 内部工具方法 ---------
    def _log_safety(self, message: str, level: str = "info") -> None:
        """记录安全日志"""
        self.safety_log.append(
            {
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _add_warning(self, message: str) -> None:
        """添加警告并记录"""
        self.warnings_log.append(message)

    def _add_alert(self, message: str) -> None:
        """添加安全警报"""
        self.safety_alerts.append(message)
        self._add_warning(message)


class Experiment(ExperimentTemplate):
    """简化的实验类，提供默认参数方便快速创建"""

    allow_empty_steps: ClassVar[bool] = True

    def __init__(self, **data: Any):
        data.setdefault("title", data.get("id", "实验"))
        data.setdefault("steps", [])
        data.setdefault("experiment_type", data.get("experiment_type", "general"))
        super().__init__(**data)
