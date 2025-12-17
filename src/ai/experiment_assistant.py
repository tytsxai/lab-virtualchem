"""
智能实验助手
基于用户行为和实验数据提供个性化建议
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SuggestionType(Enum):
    """建议类型"""

    STEP_GUIDANCE = "step_guidance"  # 步骤指导
    SAFETY_REMINDER = "safety_reminder"  # 安全提醒
    EFFICIENCY_TIP = "efficiency_tip"  # 效率提示
    ERROR_PREVENTION = "error_prevention"  # 错误预防
    LEARNING_ENHANCEMENT = "learning_enhancement"  # 学习增强


class DifficultyLevel(Enum):
    """难度等级"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class ExperimentSuggestion:
    """实验建议"""

    suggestion_id: str
    type: SuggestionType
    title: str
    content: str
    priority: int  # 1-5，5为最高优先级
    applicable_steps: list[str]  # 适用的实验步骤
    conditions: dict[str, Any]  # 触发条件
    created_at: datetime
    expires_at: datetime | None = None


class UserProfile(BaseModel):
    """用户画像"""

    user_id: str = Field(..., description="用户ID")

    # 学习水平
    difficulty_level: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER)
    chemistry_knowledge: float = Field(default=0.0, ge=0.0, le=1.0)
    lab_skills: float = Field(default=0.0, ge=0.0, le=1.0)

    # 学习偏好
    preferred_learning_style: str = Field(default="visual")
    attention_span: int = Field(default=30, ge=5, le=120)  # 分钟

    # 实验习惯
    average_experiment_time: int = Field(default=45, ge=5, le=300)  # 分钟
    common_mistakes: list[str] = Field(default_factory=list)
    preferred_experiment_types: list[str] = Field(default_factory=list)

    # 进度跟踪
    experiments_completed: int = Field(default=0, ge=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    last_activity: datetime | None = Field(default=None)


class ExperimentAssistant:
    """智能实验助手"""

    def __init__(self, user_id: str):
        """初始化实验助手

        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.user_profile: UserProfile | None = None
        self.suggestion_history: list[ExperimentSuggestion] = []
        self.learning_patterns: dict[str, Any] = {}

        # 加载用户画像
        self._load_user_profile()

        logger.info(f"实验助手已初始化: {user_id}")

    def _load_user_profile(self) -> None:
        """加载用户画像"""
        try:
            # 这里应该从数据库或存储中加载用户画像
            # 暂时使用默认配置
            self.user_profile = UserProfile(user_id=self.user_id)
            logger.info(f"用户画像已加载: {self.user_id}")
        except Exception as e:
            logger.error(f"加载用户画像失败: {e}")
            self.user_profile = UserProfile(user_id=self.user_id)

    def save_user_profile(self) -> None:
        """保存用户画像"""
        try:
            # 这里应该保存到数据库或存储中
            logger.info(f"用户画像已保存: {self.user_id}")
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")

    def analyze_experiment_behavior(self, experiment_data: dict[str, Any]) -> None:
        """分析实验行为

        Args:
            experiment_data: 实验数据
        """
        if not self.user_profile:
            return

        try:
            # 更新实验完成数
            self.user_profile.experiments_completed += 1

            # 分析实验时间
            duration = experiment_data.get("duration", 0)
            if duration > 0:
                # 更新平均实验时间（使用指数移动平均）
                alpha = 0.1
                self.user_profile.average_experiment_time = int(
                    alpha * duration
                    + (1 - alpha) * self.user_profile.average_experiment_time
                )

            # 分析成功率
            success = experiment_data.get("success", False)
            if success:
                self.user_profile.success_rate = min(
                    1.0, self.user_profile.success_rate + 0.05
                )
            else:
                self.user_profile.success_rate = max(
                    0.0, self.user_profile.success_rate - 0.02
                )

            # 分析错误模式
            mistakes = experiment_data.get("mistakes", [])
            for mistake in mistakes:
                if mistake not in self.user_profile.common_mistakes:
                    self.user_profile.common_mistakes.append(mistake)

            # 更新最后活动时间
            self.user_profile.last_activity = datetime.now()

            # 保存更新
            self.save_user_profile()

            logger.info(f"实验行为分析完成: {self.user_id}")

        except Exception as e:
            logger.error(f"分析实验行为失败: {e}")

    def generate_suggestions(
        self, current_step: str, experiment_context: dict[str, Any]
    ) -> list[ExperimentSuggestion]:
        """生成实验建议

        Args:
            current_step: 当前实验步骤
            experiment_context: 实验上下文

        Returns:
            建议列表
        """
        suggestions: list[ExperimentSuggestion] = []

        if not self.user_profile:
            return suggestions

        try:
            # 基于用户画像生成个性化建议
            suggestions.extend(
                self._generate_step_guidance(current_step, experiment_context)
            )
            suggestions.extend(
                self._generate_safety_reminders(current_step, experiment_context)
            )
            suggestions.extend(
                self._generate_efficiency_tips(current_step, experiment_context)
            )
            suggestions.extend(
                self._generate_error_prevention(current_step, experiment_context)
            )

            # 按优先级排序
            suggestions.sort(key=lambda x: x.priority, reverse=True)

            # 记录建议历史
            self.suggestion_history.extend(suggestions)

            logger.info(f"生成了 {len(suggestions)} 个建议: {self.user_id}")

        except Exception as e:
            logger.error(f"生成建议失败: {e}")

        return suggestions

    def _generate_step_guidance(
        self, current_step: str, _context: dict[str, Any]
    ) -> list[ExperimentSuggestion]:
        """生成步骤指导建议"""
        suggestions: list[ExperimentSuggestion] = []

        # 基于用户难度等级提供不同深度的指导
        if (
            self.user_profile
            and self.user_profile.difficulty_level == DifficultyLevel.BEGINNER
        ):
            suggestion = ExperimentSuggestion(
                suggestion_id=f"step_guidance_{current_step}_{datetime.now().timestamp()}",
                type=SuggestionType.STEP_GUIDANCE,
                title="详细步骤指导",
                content=f"当前步骤 '{current_step}' 需要特别注意操作顺序，建议仔细阅读实验说明。",
                priority=4,
                applicable_steps=[current_step],
                conditions={"difficulty": "beginner"},
                created_at=datetime.now(),
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_safety_reminders(
        self, current_step: str, _context: dict[str, Any]
    ) -> list[ExperimentSuggestion]:
        """生成安全提醒"""
        suggestions = []

        # 检查是否需要安全提醒
        safety_keywords = ["acid", "base", "heat", "fire", "toxic"]
        step_lower = current_step.lower()

        for keyword in safety_keywords:
            if keyword in step_lower:
                suggestion = ExperimentSuggestion(
                    suggestion_id=f"safety_{keyword}_{datetime.now().timestamp()}",
                    type=SuggestionType.SAFETY_REMINDER,
                    title="安全提醒",
                    content=f"请注意 '{keyword}' 相关的安全操作，确保佩戴适当的防护设备。",
                    priority=5,
                    applicable_steps=[current_step],
                    conditions={"safety_keyword": keyword},
                    created_at=datetime.now(),
                )
                suggestions.append(suggestion)
                break

        return suggestions

    def _generate_efficiency_tips(
        self, current_step: str, _context: dict[str, Any]
    ) -> list[ExperimentSuggestion]:
        """生成效率提示"""
        suggestions = []

        # 基于用户实验时间提供效率建议
        if (
            self.user_profile and self.user_profile.average_experiment_time > 60
        ):  # 超过1小时
            suggestion = ExperimentSuggestion(
                suggestion_id=f"efficiency_{datetime.now().timestamp()}",
                type=SuggestionType.EFFICIENCY_TIP,
                title="效率提升建议",
                content="您的实验时间较长，建议提前准备所需器材，可以提高实验效率。",
                priority=2,
                applicable_steps=[current_step],
                conditions={"long_experiment_time": True},
                created_at=datetime.now(),
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_error_prevention(
        self, current_step: str, _context: dict[str, Any]
    ) -> list[ExperimentSuggestion]:
        """生成错误预防建议"""
        suggestions: list[ExperimentSuggestion] = []

        # 基于用户常见错误提供预防建议
        if self.user_profile and self.user_profile.common_mistakes:
            for mistake in self.user_profile.common_mistakes[:3]:  # 取前3个常见错误
                suggestion = ExperimentSuggestion(
                    suggestion_id=f"error_prevention_{mistake}_{datetime.now().timestamp()}",
                    type=SuggestionType.ERROR_PREVENTION,
                    title="错误预防",
                    content=f"根据您的实验历史，请注意避免 '{mistake}' 相关的错误。",
                    priority=3,
                    applicable_steps=[current_step],
                    conditions={"common_mistake": mistake},
                    created_at=datetime.now(),
                )
                suggestions.append(suggestion)

        return suggestions

    def get_learning_recommendations(self) -> list[str]:
        """获取学习推荐

        Returns:
            推荐列表
        """
        recommendations: list[str] = []

        if not self.user_profile:
            return recommendations

        try:
            # 基于用户画像推荐学习内容
            if self.user_profile.chemistry_knowledge < 0.3:
                recommendations.append("建议先学习基础化学概念")

            if self.user_profile.lab_skills < 0.3:
                recommendations.append("建议练习基础实验操作")

            if self.user_profile.success_rate < 0.7:
                recommendations.append("建议回顾实验步骤和注意事项")

            if self.user_profile.experiments_completed < 5:
                recommendations.append("建议多进行基础实验练习")

            logger.info(f"生成了 {len(recommendations)} 个学习推荐: {self.user_id}")

        except Exception as e:
            logger.error(f"生成学习推荐失败: {e}")

        return recommendations

    def update_learning_progress(self, topic: str, progress: float) -> None:
        """更新学习进度

        Args:
            topic: 学习主题
            progress: 进度 (0-1)
        """
        if not self.user_profile:
            return

        try:
            # 更新相关技能水平
            if "chemistry" in topic.lower():
                self.user_profile.chemistry_knowledge = min(
                    1.0, self.user_profile.chemistry_knowledge + progress * 0.1
                )
            elif "lab" in topic.lower():
                self.user_profile.lab_skills = min(
                    1.0, self.user_profile.lab_skills + progress * 0.1
                )

            # 保存更新
            self.save_user_profile()

            logger.info(f"学习进度已更新: {topic} -> {progress}")

        except Exception as e:
            logger.error(f"更新学习进度失败: {e}")

    def get_user_insights(self) -> dict[str, Any]:
        """获取用户洞察

        Returns:
            用户洞察数据
        """
        if not self.user_profile:
            return {}

        return {
            "user_id": self.user_profile.user_id,
            "difficulty_level": self.user_profile.difficulty_level.value,
            "chemistry_knowledge": self.user_profile.chemistry_knowledge,
            "lab_skills": self.user_profile.lab_skills,
            "experiments_completed": self.user_profile.experiments_completed,
            "success_rate": self.user_profile.success_rate,
            "average_experiment_time": self.user_profile.average_experiment_time,
            "common_mistakes": self.user_profile.common_mistakes,
            "learning_recommendations": self.get_learning_recommendations(),
            "last_activity": self.user_profile.last_activity.isoformat()
            if self.user_profile.last_activity
            else None,
        }
