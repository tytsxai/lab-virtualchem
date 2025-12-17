#!/usr/bin/env python3
"""
增强的实验系统
提供智能实验管理、数据分析、学习建议等功能
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .robustness_integration import enhance_robustness, log_operation, validate_input

logger = logging.getLogger(__name__)


class ExperimentDifficulty(Enum):
    """实验难度级别"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ExperimentStatus(Enum):
    """实验状态"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class ExperimentMetrics:
    """实验指标"""

    experiment_id: str
    user_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    accuracy: float = 0.0
    efficiency: float = 0.0
    safety_score: float = 0.0
    learning_progress: float = 0.0
    mistakes_count: int = 0
    hints_used: int = 0
    retry_count: int = 0
    step_completion_times: list[float] = field(default_factory=list)
    error_patterns: list[str] = field(default_factory=list)
    performance_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningRecommendation:
    """学习建议"""

    type: str  # "improvement", "practice", "theory", "safety"
    priority: int  # 1-5, 5为最高优先级
    title: str
    description: str
    action_items: list[str]
    resources: list[str] = field(default_factory=list)
    estimated_time: int | None = None  # 分钟


@dataclass
class ExperimentAnalysis:
    """实验分析结果"""

    experiment_id: str
    user_id: str
    analysis_time: datetime
    overall_score: float
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[LearningRecommendation]
    progress_trend: dict[str, float]
    comparison_data: dict[str, Any] = field(default_factory=dict)


class EnhancedExperimentSystem:
    """增强的实验系统"""

    def __init__(self):
        self.experiments: dict[str, ExperimentMetrics] = {}
        self.analyses: dict[str, ExperimentAnalysis] = {}
        self.learning_history: dict[str, list[ExperimentAnalysis]] = {}
        self.performance_baselines: dict[str, dict[str, float]] = {}

    @enhance_robustness(
        operation_name="start_experiment", security_level="medium", enable_caching=True
    )
    @validate_input(
        validation_rules={
            "experiment_id": {"type": str, "required": True},
            "user_id": {"type": str, "required": True},
            "template": {"type": dict, "required": True},
        }
    )
    @log_operation(operation_name="start_experiment")
    def start_experiment(
        self, experiment_id: str, user_id: str, template: dict[str, Any]
    ) -> ExperimentMetrics:
        """开始实验"""
        logger.info(f"开始实验 {experiment_id}，用户 {user_id}")

        metrics = ExperimentMetrics(
            experiment_id=experiment_id, user_id=user_id, start_time=datetime.now()
        )

        self.experiments[experiment_id] = metrics

        # 记录实验开始事件
        self._log_experiment_event(
            experiment_id,
            "started",
            {
                "template_id": template.get("id"),
                "difficulty": template.get("difficulty", "beginner"),
                "estimated_duration": template.get("estimated_duration", 30),
            },
        )

        return metrics

    @enhance_robustness(
        operation_name="update_experiment_progress",
        security_level="low",
        enable_caching=False,
    )
    @log_operation(operation_name="update_progress")
    def update_experiment_progress(
        self,
        experiment_id: str,
        step_id: str,
        step_data: dict[str, Any],
        performance_data: dict[str, Any] | None = None,
    ) -> bool:
        """更新实验进度"""
        if experiment_id not in self.experiments:
            logger.warning(f"实验 {experiment_id} 不存在")
            return False

        metrics = self.experiments[experiment_id]

        # 记录步骤完成时间
        step_duration = step_data.get("duration", 0.0)
        metrics.step_completion_times.append(step_duration)

        # 更新性能数据
        if performance_data:
            metrics.performance_data.update(performance_data)

        # 记录错误模式
        if step_data.get("has_error", False):
            error_type = step_data.get("error_type", "unknown")
            metrics.error_patterns.append(error_type)
            metrics.mistakes_count += 1

        # 记录提示使用
        if step_data.get("hint_used", False):
            metrics.hints_used += 1

        # 记录实验事件
        self._log_experiment_event(
            experiment_id,
            "step_completed",
            {
                "step_id": step_id,
                "duration": step_duration,
                "has_error": step_data.get("has_error", False),
                "hint_used": step_data.get("hint_used", False),
            },
        )

        return True

    @enhance_robustness(
        operation_name="complete_experiment",
        security_level="medium",
        enable_caching=True,
    )
    @log_operation(operation_name="complete_experiment")
    def complete_experiment(
        self, experiment_id: str, final_data: dict[str, Any]
    ) -> ExperimentMetrics:
        """完成实验"""
        if experiment_id not in self.experiments:
            logger.warning(f"实验 {experiment_id} 不存在")
            return None

        metrics = self.experiments[experiment_id]
        metrics.end_time = datetime.now()
        metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()

        # 计算最终指标
        metrics.accuracy = final_data.get("accuracy", 0.0)
        metrics.efficiency = self._calculate_efficiency(metrics)
        metrics.safety_score = final_data.get("safety_score", 0.0)
        metrics.learning_progress = self._calculate_learning_progress(metrics)

        # 记录实验完成事件
        self._log_experiment_event(
            experiment_id,
            "completed",
            {
                "duration": metrics.duration,
                "accuracy": metrics.accuracy,
                "efficiency": metrics.efficiency,
                "safety_score": metrics.safety_score,
                "mistakes_count": metrics.mistakes_count,
            },
        )

        # 生成分析报告
        analysis = self._generate_experiment_analysis(metrics)
        self.analyses[experiment_id] = analysis

        # 更新学习历史
        if metrics.user_id not in self.learning_history:
            self.learning_history[metrics.user_id] = []
        self.learning_history[metrics.user_id].append(analysis)

        return metrics

    def _calculate_efficiency(self, metrics: ExperimentMetrics) -> float:
        """计算实验效率"""
        if not metrics.step_completion_times:
            return 0.0

        # 基于步骤完成时间和错误数量计算效率
        avg_step_time = sum(metrics.step_completion_times) / len(
            metrics.step_completion_times
        )
        error_penalty = metrics.mistakes_count * 0.1
        hint_penalty = metrics.hints_used * 0.05

        # 效率 = 1 - (平均时间惩罚 + 错误惩罚 + 提示惩罚)
        efficiency = max(
            0.0, 1.0 - (avg_step_time * 0.01 + error_penalty + hint_penalty)
        )
        return min(1.0, efficiency)

    def _calculate_learning_progress(self, metrics: ExperimentMetrics) -> float:
        """计算学习进度"""
        # 基于准确率、效率和安全性计算学习进度
        accuracy_weight = 0.4
        efficiency_weight = 0.3
        safety_weight = 0.3

        progress = (
            metrics.accuracy * accuracy_weight
            + metrics.efficiency * efficiency_weight
            + metrics.safety_score * safety_weight
        )

        return min(1.0, progress)

    def _generate_experiment_analysis(
        self, metrics: ExperimentMetrics
    ) -> ExperimentAnalysis:
        """生成实验分析"""
        analysis_time = datetime.now()

        # 计算总体得分
        overall_score = (
            metrics.accuracy + metrics.efficiency + metrics.safety_score
        ) / 3

        # 分析优势和劣势
        strengths = []
        weaknesses = []

        if metrics.accuracy >= 0.8:
            strengths.append("高准确率")
        elif metrics.accuracy < 0.6:
            weaknesses.append("准确率需要提升")

        if metrics.efficiency >= 0.7:
            strengths.append("高效操作")
        elif metrics.efficiency < 0.5:
            weaknesses.append("操作效率有待提高")

        if metrics.safety_score >= 0.9:
            strengths.append("安全意识强")
        elif metrics.safety_score < 0.7:
            weaknesses.append("需要加强安全操作")

        # 生成学习建议
        recommendations = self._generate_learning_recommendations(
            metrics, strengths, weaknesses
        )

        # 计算进度趋势
        progress_trend = self._calculate_progress_trend(metrics.user_id)

        return ExperimentAnalysis(
            experiment_id=metrics.experiment_id,
            user_id=metrics.user_id,
            analysis_time=analysis_time,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            progress_trend=progress_trend,
        )

    def _generate_learning_recommendations(
        self, metrics: ExperimentMetrics, strengths: list[str], _weaknesses: list[str]
    ) -> list[LearningRecommendation]:
        """生成学习建议"""
        recommendations = []

        # 基于错误模式生成建议
        if metrics.mistakes_count > 3:
            recommendations.append(
                LearningRecommendation(
                    type="improvement",
                    priority=4,
                    title="减少操作错误",
                    description=f"本次实验出现了 {metrics.mistakes_count} 次错误，建议加强基础操作练习",
                    action_items=["复习实验步骤", "练习基础操作", "注意操作细节"],
                    resources=["基础操作教程", "实验步骤详解"],
                    estimated_time=30,
                )
            )

        # 基于效率生成建议
        if metrics.efficiency < 0.6:
            recommendations.append(
                LearningRecommendation(
                    type="practice",
                    priority=3,
                    title="提高操作效率",
                    description="操作效率有待提高，建议多练习以提高熟练度",
                    action_items=[
                        "重复练习实验步骤",
                        "优化操作流程",
                        "减少不必要的停顿",
                    ],
                    estimated_time=45,
                )
            )

        # 基于安全性生成建议
        if metrics.safety_score < 0.8:
            recommendations.append(
                LearningRecommendation(
                    type="safety",
                    priority=5,
                    title="加强安全操作",
                    description="安全意识需要加强，安全操作是实验的基础",
                    action_items=[
                        "学习安全操作规程",
                        "练习安全操作技能",
                        "建立安全意识",
                    ],
                    resources=["安全操作手册", "安全视频教程"],
                    estimated_time=60,
                )
            )

        # 基于优势生成鼓励建议
        if strengths:
            recommendations.append(
                LearningRecommendation(
                    type="improvement",
                    priority=2,
                    title="保持优势",
                    description=f"在以下方面表现优秀：{', '.join(strengths)}",
                    action_items=[
                        "继续保持良好习惯",
                        "将优势应用到其他实验",
                        "分享经验给其他学习者",
                    ],
                    estimated_time=15,
                )
            )

        return recommendations

    def _calculate_progress_trend(self, user_id: str) -> dict[str, float]:
        """计算学习进度趋势"""
        if user_id not in self.learning_history:
            return {}

        history = self.learning_history[user_id]
        if len(history) < 2:
            return {}

        # 计算最近几次实验的趋势
        recent_analyses = history[-5:]  # 最近5次实验

        trends = {}
        for i in range(1, len(recent_analyses)):
            prev_score = recent_analyses[i - 1].overall_score
            curr_score = recent_analyses[i].overall_score
            improvement = curr_score - prev_score
            trends[f"experiment_{i}"] = improvement

        return trends

    def _log_experiment_event(
        self, experiment_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """记录实验事件"""
        logger.info(f"实验事件: {experiment_id} - {event_type}: {data}")

    @enhance_robustness(
        operation_name="get_experiment_analysis",
        security_level="low",
        enable_caching=True,
    )
    def get_experiment_analysis(self, experiment_id: str) -> ExperimentAnalysis | None:
        """获取实验分析"""
        return self.analyses.get(experiment_id)

    @enhance_robustness(
        operation_name="get_user_learning_history",
        security_level="low",
        enable_caching=True,
    )
    def get_user_learning_history(self, user_id: str) -> list[ExperimentAnalysis]:
        """获取用户学习历史"""
        return self.learning_history.get(user_id, [])

    @enhance_robustness(
        operation_name="get_learning_recommendations",
        security_level="low",
        enable_caching=True,
    )
    def get_learning_recommendations(
        self, user_id: str
    ) -> list[LearningRecommendation]:
        """获取学习建议"""
        if user_id not in self.learning_history:
            return []

        history = self.learning_history[user_id]
        if not history:
            return []

        # 获取最新的分析结果
        latest_analysis = history[-1]
        return latest_analysis.recommendations

    @enhance_robustness(
        operation_name="get_performance_statistics",
        security_level="low",
        enable_caching=True,
    )
    def get_performance_statistics(self, user_id: str) -> dict[str, Any]:
        """获取性能统计"""
        if user_id not in self.learning_history:
            return {}

        history = self.learning_history[user_id]
        if not history:
            return {}

        # 计算统计数据
        scores = [analysis.overall_score for analysis in history]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        # 计算趋势
        if len(scores) >= 2:
            recent_trend = scores[-1] - scores[-2]
        else:
            recent_trend = 0.0

        return {
            "total_experiments": len(history),
            "average_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "recent_trend": recent_trend,
            "improvement_rate": self._calculate_improvement_rate(scores),
        }

    def _calculate_improvement_rate(self, scores: list[float]) -> float:
        """计算改进率"""
        if len(scores) < 2:
            return 0.0

        improvements = 0
        for i in range(1, len(scores)):
            if scores[i] > scores[i - 1]:
                improvements += 1

        return improvements / (len(scores) - 1)

    @enhance_robustness(
        operation_name="export_experiment_data",
        security_level="medium",
        enable_caching=False,
    )
    def export_experiment_data(self, user_id: str, format: str = "json") -> str:
        """导出实验数据"""
        if user_id not in self.learning_history:
            return ""

        history = self.learning_history[user_id]

        if format == "json":
            data = {
                "user_id": user_id,
                "export_time": datetime.now().isoformat(),
                "total_experiments": len(history),
                "experiments": [],
            }

            for analysis in history:
                experiment_data = {
                    "experiment_id": analysis.experiment_id,
                    "analysis_time": analysis.analysis_time.isoformat(),
                    "overall_score": analysis.overall_score,
                    "strengths": analysis.strengths,
                    "weaknesses": analysis.weaknesses,
                    "recommendations": [
                        {
                            "type": rec.type,
                            "priority": rec.priority,
                            "title": rec.title,
                            "description": rec.description,
                            "action_items": rec.action_items,
                            "resources": rec.resources,
                            "estimated_time": rec.estimated_time,
                        }
                        for rec in analysis.recommendations
                    ],
                    "progress_trend": analysis.progress_trend,
                }
                data["experiments"].append(experiment_data)

            return json.dumps(data, ensure_ascii=False, indent=2)

        return ""


# 全局实例
enhanced_experiment_system = EnhancedExperimentSystem()
