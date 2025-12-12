#!/usr/bin/env python3
"""
增强的高级分析系统
提供学习分析、行为分析、预测分析等功能
"""

import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .robustness_integration import enhance_robustness, log_operation

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型"""
    LEARNING_PROGRESS = "learning_progress"
    BEHAVIOR_PATTERN = "behavior_pattern"
    PERFORMANCE_TREND = "performance_trend"
    ENGAGEMENT_LEVEL = "engagement_level"
    DIFFICULTY_ADAPTATION = "difficulty_adaptation"
    COLLABORATION_EFFECTIVENESS = "collaboration_effectiveness"


class MetricType(Enum):
    """指标类型"""
    ACCURACY = "accuracy"
    SPEED = "speed"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"
    SATISFACTION = "satisfaction"
    EFFICIENCY = "efficiency"


class TrendDirection(Enum):
    """趋势方向"""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class DataPoint:
    """数据点"""
    timestamp: datetime
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """指标"""
    metric_id: str
    name: str
    type: MetricType
    data_points: list[DataPoint] = field(default_factory=list)
    current_value: float = 0.0
    average_value: float = 0.0
    trend: TrendDirection = TrendDirection.STABLE
    confidence: float = 0.0


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_id: str
    user_id: str
    analysis_type: AnalysisType
    timestamp: datetime
    summary: str
    insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metrics: dict[str, Metric] = field(default_factory=dict)
    confidence: float = 0.0
    actionable: bool = True


@dataclass
class Prediction:
    """预测"""
    prediction_id: str
    user_id: str
    prediction_type: str
    predicted_value: float
    confidence: float
    time_horizon: int  # 天数
    factors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningPath:
    """学习路径"""
    path_id: str
    user_id: str
    current_level: str
    target_level: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    estimated_duration: int = 0  # 天数
    success_probability: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class EnhancedAnalyticsSystem:
    """增强的高级分析系统"""

    def __init__(self):
        self.user_metrics: dict[str, dict[str, Metric]] = {}
        self.analysis_results: dict[str, list[AnalysisResult]] = {}
        self.predictions: dict[str, list[Prediction]] = {}
        self.learning_paths: dict[str, list[LearningPath]] = {}
        self.benchmarks: dict[str, dict[str, float]] = {}

        # 初始化系统
        self._initialize_benchmarks()
        self._initialize_analysis_models()

    def _initialize_benchmarks(self) -> None:
        """初始化基准数据"""
        self.benchmarks = {
            "accuracy": {
                "beginner": 0.6,
                "intermediate": 0.75,
                "advanced": 0.85,
                "expert": 0.95
            },
            "speed": {
                "beginner": 120,  # 秒/实验
                "intermediate": 90,
                "advanced": 60,
                "expert": 45
            },
            "engagement": {
                "low": 0.3,
                "medium": 0.6,
                "high": 0.8
            },
            "retention": {
                "daily": 0.7,
                "weekly": 0.5,
                "monthly": 0.3
            }
        }
        logger.info("分析基准已初始化")

    def _initialize_analysis_models(self) -> None:
        """初始化分析模型"""
        # 这里可以添加机器学习模型的初始化
        pass

    @enhance_robustness(
        operation_name="add_data_point",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="add_data")
    def add_data_point(
        self,
        user_id: str,
        metric_name: str,
        value: float,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        """添加数据点"""
        if user_id not in self.user_metrics:
            self.user_metrics[user_id] = {}

        if metric_name not in self.user_metrics[user_id]:
            # 创建新指标
            metric_type = self._infer_metric_type(metric_name)
            self.user_metrics[user_id][metric_name] = Metric(
                metric_id=f"{user_id}_{metric_name}",
                name=metric_name,
                type=metric_type
            )

        # 添加数据点
        data_point = DataPoint(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )

        self.user_metrics[user_id][metric_name].data_points.append(data_point)

        # 更新指标统计
        self._update_metric_statistics(user_id, metric_name)

        logger.debug(f"数据点已添加: {user_id} - {metric_name}: {value}")
        return True

    def _infer_metric_type(self, metric_name: str) -> MetricType:
        """推断指标类型"""
        name_lower = metric_name.lower()

        if "accuracy" in name_lower or "correct" in name_lower:
            return MetricType.ACCURACY
        elif "speed" in name_lower or "time" in name_lower or "duration" in name_lower:
            return MetricType.SPEED
        elif "engagement" in name_lower or "interest" in name_lower:
            return MetricType.ENGAGEMENT
        elif "retention" in name_lower or "memory" in name_lower:
            return MetricType.RETENTION
        elif "satisfaction" in name_lower or "happiness" in name_lower:
            return MetricType.SATISFACTION
        elif "efficiency" in name_lower or "productivity" in name_lower:
            return MetricType.EFFICIENCY
        else:
            return MetricType.ACCURACY  # 默认类型

    def _update_metric_statistics(self, user_id: str, metric_name: str) -> None:
        """更新指标统计"""
        if user_id not in self.user_metrics or metric_name not in self.user_metrics[user_id]:
            return

        metric = self.user_metrics[user_id][metric_name]
        data_points = metric.data_points

        if not data_points:
            return

        # 更新当前值
        metric.current_value = data_points[-1].value

        # 更新平均值
        values = [dp.value for dp in data_points]
        metric.average_value = statistics.mean(values)

        # 分析趋势
        metric.trend = self._analyze_trend(values)

        # 计算置信度
        metric.confidence = self._calculate_confidence(values)

    def _analyze_trend(self, values: list[float]) -> TrendDirection:
        """分析趋势"""
        if len(values) < 3:
            return TrendDirection.STABLE

        # 计算线性趋势
        n = len(values)
        x = list(range(n))

        # 简单线性回归
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.STABLE

        slope = numerator / denominator

        # 计算变异系数
        if y_mean == 0:
            cv = 0
        else:
            cv = statistics.stdev(values) / abs(y_mean)

        # 判断趋势
        if abs(slope) < 0.01:  # 斜率很小
            if cv > 0.2:  # 高变异
                return TrendDirection.VOLATILE
            else:
                return TrendDirection.STABLE
        elif slope > 0.01:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.DECLINING

    def _calculate_confidence(self, values: list[float]) -> float:
        """计算置信度"""
        if len(values) < 2:
            return 0.0

        # 基于数据点数量和变异系数计算置信度
        n = len(values)
        cv = statistics.stdev(values) / abs(statistics.mean(values)) if statistics.mean(values) != 0 else 1.0

        # 数据点越多，置信度越高
        n_factor = min(1.0, n / 20.0)

        # 变异越小，置信度越高
        cv_factor = max(0.0, 1.0 - cv)

        confidence = (n_factor + cv_factor) / 2.0
        return min(1.0, max(0.0, confidence))

    @enhance_robustness(
        operation_name="perform_learning_analysis",
        security_level="low",
        enable_caching=True
    )
    @log_operation(operation_name="learning_analysis")
    def perform_learning_analysis(self, user_id: str) -> AnalysisResult:
        """执行学习分析"""
        if user_id not in self.user_metrics:
            return self._create_empty_analysis(user_id, AnalysisType.LEARNING_PROGRESS)

        user_metrics = self.user_metrics[user_id]

        # 分析学习进度
        progress_insights = self._analyze_learning_progress(user_metrics)

        # 分析学习模式
        pattern_insights = self._analyze_learning_patterns(user_metrics)

        # 生成建议
        recommendations = self._generate_learning_recommendations(user_metrics)

        # 创建分析结果
        analysis_result = AnalysisResult(
            analysis_id=f"analysis_{user_id}_{int(time.time())}",
            user_id=user_id,
            analysis_type=AnalysisType.LEARNING_PROGRESS,
            timestamp=datetime.now(),
            summary=self._generate_learning_summary(user_metrics),
            insights=progress_insights + pattern_insights,
            recommendations=recommendations,
            metrics=user_metrics,
            confidence=self._calculate_overall_confidence(user_metrics),
            actionable=True
        )

        # 保存分析结果
        if user_id not in self.analysis_results:
            self.analysis_results[user_id] = []
        self.analysis_results[user_id].append(analysis_result)

        logger.info(f"学习分析已完成: {user_id}")
        return analysis_result

    def _analyze_learning_progress(self, metrics: dict[str, Metric]) -> list[str]:
        """分析学习进度"""
        insights = []

        # 分析准确率趋势
        if "accuracy" in metrics:
            accuracy_metric = metrics["accuracy"]
            if accuracy_metric.trend == TrendDirection.IMPROVING:
                insights.append("您的学习准确率正在稳步提升，这表明学习效果良好")
            elif accuracy_metric.trend == TrendDirection.DECLINING:
                insights.append("您的学习准确率有所下降，建议调整学习策略")
            elif accuracy_metric.trend == TrendDirection.VOLATILE:
                insights.append("您的学习准确率波动较大，建议保持稳定的学习节奏")

        # 分析学习速度
        if "speed" in metrics:
            speed_metric = metrics["speed"]
            if speed_metric.trend == TrendDirection.IMPROVING:
                insights.append("您的学习速度正在提升，效率不断提高")
            elif speed_metric.current_value < 60:  # 快速学习
                insights.append("您具有快速学习的能力，可以尝试更有挑战性的内容")

        # 分析参与度
        if "engagement" in metrics:
            engagement_metric = metrics["engagement"]
            if engagement_metric.current_value > 0.8:
                insights.append("您对学习内容表现出很高的参与度，这是学习成功的关键因素")
            elif engagement_metric.current_value < 0.5:
                insights.append("您的学习参与度较低，建议寻找更感兴趣的学习内容")

        return insights

    def _analyze_learning_patterns(self, metrics: dict[str, Metric]) -> list[str]:
        """分析学习模式"""
        insights = []

        # 分析学习时间模式
        time_patterns = self._analyze_time_patterns(metrics)
        insights.extend(time_patterns)

        # 分析难度适应性
        difficulty_patterns = self._analyze_difficulty_patterns(metrics)
        insights.extend(difficulty_patterns)

        # 分析学习偏好
        preference_patterns = self._analyze_preference_patterns(metrics)
        insights.extend(preference_patterns)

        return insights

    def _analyze_time_patterns(self, _metrics: dict[str, Metric]) -> list[str]:
        """分析时间模式"""
        insights = []

        # 这里可以添加时间模式分析逻辑
        # 例如：分析用户在不同时间段的学习效果

        return insights

    def _analyze_difficulty_patterns(self, metrics: dict[str, Metric]) -> list[str]:
        """分析难度模式"""
        insights = []

        # 分析用户对不同难度的适应性
        if "difficulty_adaptation" in metrics:
            adaptation_metric = metrics["difficulty_adaptation"]
            if adaptation_metric.current_value > 0.8:
                insights.append("您对难度变化适应能力很强，可以尝试更多挑战")
            elif adaptation_metric.current_value < 0.4:
                insights.append("建议循序渐进地增加学习难度，避免过度挑战")

        return insights

    def _analyze_preference_patterns(self, metrics: dict[str, Metric]) -> list[str]:
        """分析偏好模式"""
        insights = []

        # 分析用户的学习偏好
        if "learning_preference" in metrics:
            # 根据偏好类型生成洞察（占位，未来扩展）
            _preference_metric = metrics["learning_preference"]

        return insights

    def _generate_learning_recommendations(self, metrics: dict[str, Metric]) -> list[str]:
        """生成学习建议"""
        recommendations = []

        # 基于准确率生成建议
        if "accuracy" in metrics:
            accuracy_metric = metrics["accuracy"]
            if accuracy_metric.current_value < 0.7:
                recommendations.append("建议加强基础概念的学习，确保理解透彻")
            elif accuracy_metric.current_value > 0.9:
                recommendations.append("您的准确率很高，可以尝试更有挑战性的内容")

        # 基于速度生成建议
        if "speed" in metrics:
            speed_metric = metrics["speed"]
            if speed_metric.current_value > 120:  # 慢速学习
                recommendations.append("建议提高学习效率，可以尝试时间管理技巧")
            elif speed_metric.current_value < 30:  # 快速学习
                recommendations.append("您学习很快，建议确保学习质量，避免遗漏重要细节")

        # 基于参与度生成建议
        if "engagement" in metrics:
            engagement_metric = metrics["engagement"]
            if engagement_metric.current_value < 0.6:
                recommendations.append("建议寻找更感兴趣的学习内容，提高学习动机")

        return recommendations

    def _generate_learning_summary(self, metrics: dict[str, Metric]) -> str:
        """生成学习摘要"""
        if not metrics:
            return "暂无学习数据"

        # 分析整体表现
        accuracy = metrics.get("accuracy", Metric("", "", MetricType.ACCURACY))
        speed = metrics.get("speed", Metric("", "", MetricType.SPEED))
        engagement = metrics.get("engagement", Metric("", "", MetricType.ENGAGEMENT))

        summary_parts = []

        if accuracy.current_value > 0.8:
            summary_parts.append("学习准确率优秀")
        elif accuracy.current_value > 0.6:
            summary_parts.append("学习准确率良好")
        else:
            summary_parts.append("学习准确率需要提升")

        if speed.current_value < 60:
            summary_parts.append("学习效率很高")
        elif speed.current_value < 120:
            summary_parts.append("学习效率良好")
        else:
            summary_parts.append("学习效率有待提高")

        if engagement.current_value > 0.7:
            summary_parts.append("学习参与度很高")
        elif engagement.current_value > 0.5:
            summary_parts.append("学习参与度中等")
        else:
            summary_parts.append("学习参与度较低")

        return f"整体学习表现：{', '.join(summary_parts)}。"

    def _calculate_overall_confidence(self, metrics: dict[str, Metric]) -> float:
        """计算整体置信度"""
        if not metrics:
            return 0.0

        confidences = [metric.confidence for metric in metrics.values()]
        return statistics.mean(confidences) if confidences else 0.0

    def _create_empty_analysis(self, user_id: str, analysis_type: AnalysisType) -> AnalysisResult:
        """创建空分析结果"""
        return AnalysisResult(
            analysis_id=f"empty_{user_id}_{int(time.time())}",
            user_id=user_id,
            analysis_type=analysis_type,
            timestamp=datetime.now(),
            summary="暂无足够数据进行学习分析",
            insights=["需要更多学习数据才能生成有意义的分析"],
            recommendations=["建议多参与学习活动，积累更多数据"],
            confidence=0.0,
            actionable=False
        )

    @enhance_robustness(
        operation_name="generate_prediction",
        security_level="medium",
        enable_caching=True
    )
    @log_operation(operation_name="generate_prediction")
    def generate_prediction(
        self,
        user_id: str,
        prediction_type: str,
        time_horizon: int = 30
    ) -> Prediction:
        """生成预测"""
        if user_id not in self.user_metrics:
            return self._create_empty_prediction(user_id, prediction_type, time_horizon)

        user_metrics = self.user_metrics[user_id]

        # 基于历史数据生成预测
        predicted_value = self._predict_value(user_metrics, prediction_type, time_horizon)
        confidence = self._calculate_prediction_confidence(user_metrics, prediction_type)
        factors = self._identify_prediction_factors(user_metrics, prediction_type)

        prediction = Prediction(
            prediction_id=f"pred_{user_id}_{int(time.time())}",
            user_id=user_id,
            prediction_type=prediction_type,
            predicted_value=predicted_value,
            confidence=confidence,
            time_horizon=time_horizon,
            factors=factors
        )

        # 保存预测
        if user_id not in self.predictions:
            self.predictions[user_id] = []
        self.predictions[user_id].append(prediction)

        logger.info(f"预测已生成: {user_id} - {prediction_type}")
        return prediction

    def _predict_value(self, metrics: dict[str, Metric], prediction_type: str, _time_horizon: int) -> float:
        """预测数值"""
        # 简化的预测逻辑
        if prediction_type == "accuracy":
            if "accuracy" in metrics:
                accuracy_metric = metrics["accuracy"]
                # 基于趋势预测
                if accuracy_metric.trend == TrendDirection.IMPROVING:
                    return min(1.0, accuracy_metric.current_value + 0.1)
                elif accuracy_metric.trend == TrendDirection.DECLINING:
                    return max(0.0, accuracy_metric.current_value - 0.1)
                else:
                    return accuracy_metric.current_value
            return 0.7  # 默认值

        elif prediction_type == "speed":
            if "speed" in metrics:
                speed_metric = metrics["speed"]
                if speed_metric.trend == TrendDirection.IMPROVING:
                    return max(10.0, speed_metric.current_value - 10.0)
                elif speed_metric.trend == TrendDirection.DECLINING:
                    return speed_metric.current_value + 10.0
                else:
                    return speed_metric.current_value
            return 90.0  # 默认值

        return 0.0

    def _calculate_prediction_confidence(self, metrics: dict[str, Metric], prediction_type: str) -> float:
        """计算预测置信度"""
        if prediction_type in metrics:
            return metrics[prediction_type].confidence
        return 0.5  # 默认置信度

    def _identify_prediction_factors(self, metrics: dict[str, Metric], prediction_type: str) -> list[str]:
        """识别预测因素"""
        factors = []

        if prediction_type == "accuracy":
            if "engagement" in metrics:
                factors.append("学习参与度")
            if "speed" in metrics:
                factors.append("学习速度")
            if "difficulty_adaptation" in metrics:
                factors.append("难度适应性")

        elif prediction_type == "speed":
            if "accuracy" in metrics:
                factors.append("学习准确率")
            if "engagement" in metrics:
                factors.append("学习参与度")

        return factors

    def _create_empty_prediction(self, user_id: str, prediction_type: str, time_horizon: int) -> Prediction:
        """创建空预测"""
        return Prediction(
            prediction_id=f"empty_pred_{user_id}_{int(time.time())}",
            user_id=user_id,
            prediction_type=prediction_type,
            predicted_value=0.0,
            confidence=0.0,
            time_horizon=time_horizon,
            factors=["需要更多历史数据"]
        )

    @enhance_robustness(
        operation_name="get_learning_path",
        security_level="low",
        enable_caching=True
    )
    def get_learning_path(self, user_id: str, target_level: str) -> LearningPath:
        """获取学习路径"""
        if user_id not in self.user_metrics:
            return self._create_default_learning_path(user_id, target_level)

        user_metrics = self.user_metrics[user_id]
        current_level = self._assess_current_level(user_metrics)

        # 生成学习步骤
        steps = self._generate_learning_steps(current_level, target_level)

        # 估算持续时间
        estimated_duration = self._estimate_learning_duration(user_metrics, steps)

        # 计算成功概率
        success_probability = self._calculate_success_probability(user_metrics, steps)

        learning_path = LearningPath(
            path_id=f"path_{user_id}_{int(time.time())}",
            user_id=user_id,
            current_level=current_level,
            target_level=target_level,
            steps=steps,
            estimated_duration=estimated_duration,
            success_probability=success_probability
        )

        # 保存学习路径
        if user_id not in self.learning_paths:
            self.learning_paths[user_id] = []
        self.learning_paths[user_id].append(learning_path)

        return learning_path

    def _assess_current_level(self, metrics: dict[str, Metric]) -> str:
        """评估当前水平"""
        if "accuracy" in metrics:
            accuracy = metrics["accuracy"].current_value
            if accuracy >= 0.9:
                return "expert"
            elif accuracy >= 0.8:
                return "advanced"
            elif accuracy >= 0.7:
                return "intermediate"
            else:
                return "beginner"
        return "beginner"

    def _generate_learning_steps(self, current_level: str, target_level: str) -> list[dict[str, Any]]:
        """生成学习步骤"""
        steps = []

        level_hierarchy = ["beginner", "intermediate", "advanced", "expert"]

        try:
            current_idx = level_hierarchy.index(current_level)
            target_idx = level_hierarchy.index(target_level)
        except ValueError:
            return steps

        if current_idx >= target_idx:
            return steps

        for i in range(current_idx + 1, target_idx + 1):
            level = level_hierarchy[i]
            steps.append({
                "step": i - current_idx,
                "level": level,
                "description": f"达到{level}水平",
                "estimated_time": 30,  # 天
                "requirements": self._get_level_requirements(level)
            })

        return steps

    def _get_level_requirements(self, level: str) -> list[str]:
        """获取水平要求"""
        requirements = {
            "beginner": ["掌握基础概念", "完成基础实验"],
            "intermediate": ["理解复杂概念", "独立完成实验"],
            "advanced": ["深入理解原理", "设计实验方案"],
            "expert": ["创新性思维", "解决复杂问题"]
        }
        return requirements.get(level, [])

    def _estimate_learning_duration(self, metrics: dict[str, Metric], steps: list[dict[str, Any]]) -> int:
        """估算学习持续时间"""
        base_duration = len(steps) * 30  # 每步30天

        # 根据学习速度调整
        if "speed" in metrics:
            speed_metric = metrics["speed"]
            if speed_metric.current_value < 60:  # 快速学习
                base_duration = int(base_duration * 0.8)
            elif speed_metric.current_value > 120:  # 慢速学习
                base_duration = int(base_duration * 1.2)

        return base_duration

    def _calculate_success_probability(self, metrics: dict[str, Metric], _steps: list[dict[str, Any]]) -> float:
        """计算成功概率"""
        base_probability = 0.7  # 基础成功概率

        # 根据当前表现调整
        if "accuracy" in metrics:
            accuracy = metrics["accuracy"].current_value
            if accuracy > 0.8:
                base_probability += 0.2
            elif accuracy < 0.6:
                base_probability -= 0.2

        if "engagement" in metrics:
            engagement = metrics["engagement"].current_value
            if engagement > 0.7:
                base_probability += 0.1
            elif engagement < 0.5:
                base_probability -= 0.1

        return max(0.0, min(1.0, base_probability))

    def _create_default_learning_path(self, user_id: str, target_level: str) -> LearningPath:
        """创建默认学习路径"""
        return LearningPath(
            path_id=f"default_path_{user_id}_{int(time.time())}",
            user_id=user_id,
            current_level="beginner",
            target_level=target_level,
            steps=[{
                "step": 1,
                "level": target_level,
                "description": f"达到{target_level}水平",
                "estimated_time": 60,
                "requirements": self._get_level_requirements(target_level)
            }],
            estimated_duration=60,
            success_probability=0.5
        )

    @enhance_robustness(
        operation_name="get_analytics_dashboard",
        security_level="low",
        enable_caching=True
    )
    def get_analytics_dashboard(self, user_id: str) -> dict[str, Any]:
        """获取分析仪表板"""
        dashboard = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "analysis": {},
            "predictions": {},
            "learning_path": {},
            "recommendations": []
        }

        # 获取用户指标
        if user_id in self.user_metrics:
            dashboard["metrics"] = {
                name: {
                    "current_value": metric.current_value,
                    "average_value": metric.average_value,
                    "trend": metric.trend.value,
                    "confidence": metric.confidence,
                    "data_points_count": len(metric.data_points)
                }
                for name, metric in self.user_metrics[user_id].items()
            }

        # 获取最新分析结果
        if user_id in self.analysis_results:
            latest_analysis = self.analysis_results[user_id][-1] if self.analysis_results[user_id] else None
            if latest_analysis:
                dashboard["analysis"] = {
                    "summary": latest_analysis.summary,
                    "insights": latest_analysis.insights,
                    "confidence": latest_analysis.confidence,
                    "timestamp": latest_analysis.timestamp.isoformat()
                }

        # 获取最新预测
        if user_id in self.predictions:
            latest_predictions = self.predictions[user_id][-3:] if self.predictions[user_id] else []
            dashboard["predictions"] = [
                {
                    "type": pred.prediction_type,
                    "value": pred.predicted_value,
                    "confidence": pred.confidence,
                    "time_horizon": pred.time_horizon,
                    "factors": pred.factors
                }
                for pred in latest_predictions
            ]

        # 获取学习路径
        if user_id in self.learning_paths:
            latest_path = self.learning_paths[user_id][-1] if self.learning_paths[user_id] else None
            if latest_path:
                dashboard["learning_path"] = {
                    "current_level": latest_path.current_level,
                    "target_level": latest_path.target_level,
                    "steps": latest_path.steps,
                    "estimated_duration": latest_path.estimated_duration,
                    "success_probability": latest_path.success_probability
                }

        # 生成推荐
        dashboard["recommendations"] = self._generate_dashboard_recommendations(user_id)

        return dashboard

    def _generate_dashboard_recommendations(self, user_id: str) -> list[str]:
        """生成仪表板推荐"""
        recommendations = []

        if user_id in self.user_metrics:
            metrics = self.user_metrics[user_id]

            # 基于准确率推荐
            if "accuracy" in metrics:
                accuracy = metrics["accuracy"].current_value
                if accuracy < 0.7:
                    recommendations.append("建议加强基础概念学习，提高准确率")
                elif accuracy > 0.9:
                    recommendations.append("准确率很高，可以尝试更有挑战性的内容")

            # 基于速度推荐
            if "speed" in metrics:
                speed = metrics["speed"].current_value
                if speed > 120:
                    recommendations.append("建议提高学习效率，优化时间管理")
                elif speed < 30:
                    recommendations.append("学习速度很快，注意确保学习质量")

            # 基于参与度推荐
            if "engagement" in metrics:
                engagement = metrics["engagement"].current_value
                if engagement < 0.6:
                    recommendations.append("建议寻找更感兴趣的学习内容")

        return recommendations


# 全局实例
enhanced_analytics_system = EnhancedAnalyticsSystem()
