"""
学习分析模块
提供学习行为分析和学习模式识别功能
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LearningStyle(Enum):
    """学习风格"""

    VISUAL = "visual"  # 视觉型
    AUDITORY = "auditory"  # 听觉型
    KINESTHETIC = "kinesthetic"  # 动觉型
    READING_WRITING = "reading_writing"  # 读写型


class DifficultyLevel(Enum):
    """难度等级"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class LearningPattern:
    """学习模式"""

    pattern_id: str
    user_id: str
    learning_style: LearningStyle
    preferred_difficulty: DifficultyLevel
    average_completion_time: float  # 分钟
    success_rate: float  # 0-1
    common_mistakes: list[str] = field(default_factory=list)
    strong_topics: list[str] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "user_id": self.user_id,
            "learning_style": self.learning_style.value,
            "preferred_difficulty": self.preferred_difficulty.value,
            "average_completion_time": self.average_completion_time,
            "success_rate": self.success_rate,
            "common_mistakes": self.common_mistakes,
            "strong_topics": self.strong_topics,
            "weak_topics": self.weak_topics,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class LearningRecommendation:
    """学习推荐"""

    recommendation_id: str
    user_id: str
    recommended_topics: list[str]
    recommended_difficulty: DifficultyLevel
    reason: str
    priority: str = "medium"  # low, medium, high
    created_at: datetime = field(default_factory=datetime.now)


class LearningAnalytics:
    """学习分析器"""

    def __init__(self):
        """初始化学习分析器"""
        self.patterns: dict[str, LearningPattern] = {}

    def analyze_user_behavior(self, user_id: str, activity_data: list[dict[str, Any]]) -> LearningPattern:
        """分析用户学习行为

        Args:
            user_id: 用户ID
            activity_data: 活动数据列表

        Returns:
            学习模式
        """
        if not activity_data:
            # 返回默认模式
            return LearningPattern(
                pattern_id=f"pattern_{user_id}",
                user_id=user_id,
                learning_style=LearningStyle.VISUAL,
                preferred_difficulty=DifficultyLevel.BEGINNER,
                average_completion_time=30.0,
                success_rate=0.5,
            )

        # 分析学习风格
        learning_style = self._detect_learning_style(activity_data)

        # 分析偏好难度
        preferred_difficulty = self._detect_preferred_difficulty(activity_data)

        # 计算平均完成时间
        completion_times = [a.get("completion_time", 30) for a in activity_data if "completion_time" in a]
        avg_time = sum(completion_times) / len(completion_times) if completion_times else 30.0

        # 计算成功率
        successes = sum(1 for a in activity_data if a.get("success", False))
        success_rate = successes / len(activity_data) if activity_data else 0.5

        # 识别常见错误
        common_mistakes = self._identify_common_mistakes(activity_data)

        # 识别强项和弱项
        strong_topics, weak_topics = self._identify_strengths_weaknesses(activity_data)

        pattern = LearningPattern(
            pattern_id=f"pattern_{user_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            learning_style=learning_style,
            preferred_difficulty=preferred_difficulty,
            average_completion_time=avg_time,
            success_rate=success_rate,
            common_mistakes=common_mistakes,
            strong_topics=strong_topics,
            weak_topics=weak_topics,
        )

        self.patterns[user_id] = pattern
        return pattern

    def _detect_learning_style(self, activity_data: list[dict[str, Any]]) -> LearningStyle:
        """检测学习风格"""
        # 简单实现：基于用户交互类型
        visual_count = sum(1 for a in activity_data if a.get("interaction_type") == "visual")
        kinesthetic_count = sum(1 for a in activity_data if a.get("interaction_type") == "interactive")

        if visual_count > kinesthetic_count:
            return LearningStyle.VISUAL
        else:
            return LearningStyle.KINESTHETIC

    def _detect_preferred_difficulty(self, activity_data: list[dict[str, Any]]) -> DifficultyLevel:
        """检测偏好难度"""
        # 基于用户选择的实验难度
        difficulties = [a.get("difficulty", "beginner") for a in activity_data if "difficulty" in a]

        if not difficulties:
            return DifficultyLevel.BEGINNER

        # 找出最常选择的难度
        difficulty_counts = {}
        for diff in difficulties:
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        most_common = max(difficulty_counts, key=difficulty_counts.get)

        difficulty_map = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
            "expert": DifficultyLevel.EXPERT,
        }

        return difficulty_map.get(most_common, DifficultyLevel.BEGINNER)

    def _identify_common_mistakes(self, activity_data: list[dict[str, Any]]) -> list[str]:
        """识别常见错误"""
        mistakes = []
        for activity in activity_data:
            if "mistakes" in activity:
                mistakes.extend(activity["mistakes"])

        # 统计频率并返回前5个
        mistake_counts = {}
        for mistake in mistakes:
            mistake_counts[mistake] = mistake_counts.get(mistake, 0) + 1

        sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)
        return [m[0] for m in sorted_mistakes[:5]]

    def _identify_strengths_weaknesses(self, activity_data: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        """识别强项和弱项"""
        topic_performance = {}

        for activity in activity_data:
            topic = activity.get("topic")
            success = activity.get("success", False)

            if topic:
                if topic not in topic_performance:
                    topic_performance[topic] = {"success": 0, "total": 0}

                topic_performance[topic]["total"] += 1
                if success:
                    topic_performance[topic]["success"] += 1

        # 计算成功率
        topic_rates = {}
        for topic, data in topic_performance.items():
            topic_rates[topic] = data["success"] / data["total"] if data["total"] > 0 else 0

        # 排序
        sorted_topics = sorted(topic_rates.items(), key=lambda x: x[1], reverse=True)

        # 强项：成功率 > 0.7
        strong_topics = [t[0] for t in sorted_topics if t[1] > 0.7][:5]

        # 弱项：成功率 < 0.4
        weak_topics = [t[0] for t in sorted_topics if t[1] < 0.4][:5]

        return strong_topics, weak_topics

    def generate_recommendations(self, user_id: str) -> list[LearningRecommendation]:
        """生成学习推荐"""
        pattern = self.patterns.get(user_id)

        if not pattern:
            return []

        recommendations = []

        # 基于弱项推荐练习
        if pattern.weak_topics:
            recommendations.append(
                LearningRecommendation(
                    recommendation_id=f"rec_{user_id}_weak",
                    user_id=user_id,
                    recommended_topics=pattern.weak_topics,
                    recommended_difficulty=DifficultyLevel.BEGINNER,
                    reason="这些是您的薄弱环节，建议加强练习",
                    priority="high",
                )
            )

        # 基于强项推荐挑战
        if pattern.strong_topics and pattern.success_rate > 0.7:
            next_difficulty = self._get_next_difficulty(pattern.preferred_difficulty)
            recommendations.append(
                LearningRecommendation(
                    recommendation_id=f"rec_{user_id}_challenge",
                    user_id=user_id,
                    recommended_topics=pattern.strong_topics,
                    recommended_difficulty=next_difficulty,
                    reason="您在这些主题表现优秀，可以尝试更高难度",
                    priority="medium",
                )
            )

        return recommendations

    def _get_next_difficulty(self, current: DifficultyLevel) -> DifficultyLevel:
        """获取下一个难度等级"""
        difficulty_order = [
            DifficultyLevel.BEGINNER,
            DifficultyLevel.INTERMEDIATE,
            DifficultyLevel.ADVANCED,
            DifficultyLevel.EXPERT,
        ]

        try:
            current_index = difficulty_order.index(current)
            if current_index < len(difficulty_order) - 1:
                return difficulty_order[current_index + 1]
        except ValueError:
            pass

        return current

    def get_pattern(self, user_id: str) -> LearningPattern | None:
        """获取用户学习模式"""
        return self.patterns.get(user_id)


if __name__ == "__main__":
    # 示例使用
    analytics = LearningAnalytics()

    # 模拟用户活动数据
    activity_data = [
        {
            "topic": "acid_base",
            "difficulty": "beginner",
            "success": True,
            "completion_time": 25,
            "interaction_type": "visual",
        },
        {
            "topic": "acid_base",
            "difficulty": "beginner",
            "success": True,
            "completion_time": 20,
            "interaction_type": "interactive",
            "mistakes": ["wrong_reagent"],
        },
        {
            "topic": "titration",
            "difficulty": "intermediate",
            "success": False,
            "completion_time": 45,
            "mistakes": ["calculation_error", "reading_error"],
        },
    ]

    # 分析用户行为
    pattern = analytics.analyze_user_behavior("user_123", activity_data)

    print("学习模式分析结果:")
    print(f"学习风格: {pattern.learning_style.value}")
    print(f"偏好难度: {pattern.preferred_difficulty.value}")
    print(f"平均完成时间: {pattern.average_completion_time} 分钟")
    print(f"成功率: {pattern.success_rate * 100}%")
    print(f"常见错误: {pattern.common_mistakes}")
    print(f"强项: {pattern.strong_topics}")
    print(f"弱项: {pattern.weak_topics}")

    # 生成推荐
    recommendations = analytics.generate_recommendations("user_123")
    print(f"\n学习推荐 ({len(recommendations)} 条):")
    for rec in recommendations:
        print(f"- {rec.reason}")
        print(f"  推荐主题: {rec.recommended_topics}")
        print(f"  推荐难度: {rec.recommended_difficulty.value}")
