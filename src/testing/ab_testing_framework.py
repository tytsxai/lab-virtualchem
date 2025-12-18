"""A/B 测试框架（轻量实现）。

说明：
- 本模块为应用内 A/B 测试提供最小可用能力：创建实验、保存实验、发射完成信号。
- 该实现偏“内存态 + 可扩展”，用于支撑集成层与演示流程，避免导入缺失导致运行失败。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal


class ExperimentType(Enum):
    """实验类型"""

    FEATURE = "feature"
    UI_DESIGN = "ui_design"
    WORKFLOW = "workflow"
    PERFORMANCE = "performance"


class ExperimentStatus(Enum):
    """实验状态"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(Enum):
    """变体类型"""

    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass(frozen=True)
class Variant:
    """实验变体"""

    variant_id: str
    name: str
    variant_type: VariantType
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    traffic_allocation: float = 0.5


@dataclass
class ExperimentMetrics:
    """实验指标（简化）"""

    total_participants: int = 0
    conversions: dict[str, int] = field(default_factory=dict)
    custom_metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class UserAssignment:
    """用户分流结果（简化）"""

    user_id: str
    experiment_id: str
    variant_id: str


@dataclass
class ABExperiment:
    """A/B 实验对象（简化）"""

    experiment_id: str
    name: str
    experiment_type: ExperimentType
    description: str = ""
    hypothesis: str = ""
    variants: list[Variant] = field(default_factory=list)
    success_criteria: dict[str, Any] = field(default_factory=dict)
    target_audience: dict[str, Any] = field(default_factory=dict)
    created_by: str = "system"
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metrics: ExperimentMetrics = field(default_factory=ExperimentMetrics)


class ABTestingFramework(QObject):
    """A/B 测试框架（最小实现）"""

    experiment_completed = Signal(str, dict)  # experiment_id, results

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.experiments: dict[str, ABExperiment] = {}
        self.active_experiments: set[str] = set()

    def create_experiment(
        self,
        *,
        name: str,
        experiment_type: ExperimentType,
        description: str = "",
        hypothesis: str = "",
        variants: list[Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        target_audience: dict[str, Any] | None = None,
        created_by: str = "system",
    ) -> str:
        """创建实验并立即标记为 RUNNING（简化策略）。"""

        experiment_id = f"ab_{len(self.experiments) + 1:06d}"
        normalized_variants: list[Variant] = []

        for idx, raw in enumerate(variants or []):
            if isinstance(raw, Variant):
                normalized_variants.append(raw)
                continue

            if not isinstance(raw, dict):
                continue

            variant_type = VariantType.TREATMENT
            raw_type = str(raw.get("type", "treatment")).lower()
            if raw_type == "control":
                variant_type = VariantType.CONTROL

            normalized_variants.append(
                Variant(
                    variant_id=str(raw.get("id") or f"v{idx+1}"),
                    name=str(raw.get("name") or f"Variant {idx+1}"),
                    variant_type=variant_type,
                    description=str(raw.get("description") or ""),
                    config=dict(raw.get("config") or {}),
                    traffic_allocation=float(raw.get("traffic_allocation") or 0.5),
                )
            )

        experiment = ABExperiment(
            experiment_id=experiment_id,
            name=name,
            experiment_type=experiment_type,
            description=description,
            hypothesis=hypothesis,
            variants=normalized_variants,
            success_criteria=success_criteria or {},
            target_audience=target_audience or {},
            created_by=created_by,
            status=ExperimentStatus.RUNNING,
        )

        self.experiments[experiment_id] = experiment
        self.active_experiments.add(experiment_id)
        return experiment_id

    def complete_experiment(self, experiment_id: str, results: dict[str, Any]) -> bool:
        """标记实验完成并发射信号。"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False

        experiment.status = ExperimentStatus.COMPLETED
        self.active_experiments.discard(experiment_id)
        self.experiment_completed.emit(experiment_id, dict(results))
        return True

