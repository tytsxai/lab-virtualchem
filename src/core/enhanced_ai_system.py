#!/usr/bin/env python3
"""
增强的AI智能系统
提供智能实验助手、学习分析、个性化推荐等功能
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .robustness_integration import enhance_robustness, log_operation, validate_input

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI提供商"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LearningStyle(Enum):
    """学习风格"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING = "reading"


class DifficultyPreference(Enum):
    """难度偏好"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class UserProfile:
    """用户AI档案"""
    user_id: str
    learning_style: LearningStyle
    difficulty_preference: DifficultyPreference
    interests: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    learning_goals: List[str] = field(default_factory=list)
    preferred_topics: List[str] = field(default_factory=list)
    study_time_preference: str = "morning"
    session_duration_preference: int = 30  # 分钟
    feedback_frequency: str = "immediate"


@dataclass
class LearningSession:
    """学习会话"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    topics_covered: List[str] = field(default_factory=list)
    exercises_completed: int = 0
    accuracy_score: float = 0.0
    engagement_level: float = 0.0
    difficulty_level: str = "beginner"
    ai_interactions: int = 0
    hints_requested: int = 0
    concepts_mastered: List[str] = field(default_factory=list)
    concepts_struggled: List[str] = field(default_factory=list)


@dataclass
class AIRecommendation:
    """AI推荐"""
    type: str  # "experiment", "study", "practice", "review"
    priority: int  # 1-5
    title: str
    description: str
    estimated_time: int  # 分钟
    difficulty_level: str
    learning_objectives: List[str]
    prerequisites: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    ai_reasoning: str = ""
    confidence_score: float = 0.0


@dataclass
class LearningInsight:
    """学习洞察"""
    insight_type: str  # "strength", "weakness", "pattern", "recommendation"
    title: str
    description: str
    data_points: List[Dict[str, Any]]
    confidence: float
    actionable: bool
    suggested_actions: List[str] = field(default_factory=list)


class EnhancedAISystem:
    """增强的AI智能系统"""

    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.learning_sessions: Dict[str, LearningSession] = {}
        self.ai_recommendations: Dict[str, List[AIRecommendation]] = {}
        self.learning_insights: Dict[str, List[LearningInsight]] = {}
        self.knowledge_base: Dict[str, Any] = {}
        self.ai_provider: AIProvider = AIProvider.OLLAMA

        # 初始化系统
        self._initialize_knowledge_base()
        self._initialize_ai_provider()

    def _initialize_knowledge_base(self) -> None:
        """初始化知识库"""
        self.knowledge_base = {
            "chemistry_concepts": {
                "basic": ["原子结构", "化学键", "化学反应", "酸碱理论"],
                "intermediate": ["有机化学", "无机化学", "物理化学", "分析化学"],
                "advanced": ["量子化学", "生物化学", "材料化学", "环境化学"]
            },
            "experiment_types": {
                "titration": ["酸碱滴定", "氧化还原滴定", "络合滴定"],
                "synthesis": ["有机合成", "无机合成", "纳米材料合成"],
                "analysis": ["定性分析", "定量分析", "仪器分析"],
                "physical": ["热力学", "动力学", "电化学"]
            },
            "learning_resources": {
                "videos": ["基础化学视频", "实验操作视频", "理论讲解视频"],
                "simulations": ["分子模拟", "反应模拟", "仪器模拟"],
                "exercises": ["选择题", "计算题", "实验题", "综合题"],
                "interactive": ["虚拟实验", "3D分子模型", "交互式图表"]
            }
        }
        logger.info("AI知识库已初始化")

    def _initialize_ai_provider(self) -> None:
        """初始化AI提供商"""
        try:
            # 尝试连接Ollama
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                self.ai_provider = AIProvider.OLLAMA
                logger.info("Ollama AI提供商已连接")
            else:
                self.ai_provider = AIProvider.LOCAL
                logger.info("使用本地AI提供商")
        except Exception as e:
            self.ai_provider = AIProvider.LOCAL
            logger.warning(f"AI提供商初始化失败，使用本地模式: {e}")

    @enhance_robustness(
        operation_name="create_user_profile",
        security_level="medium",
        enable_caching=True
    )
    @validate_input(validation_rules={
        "user_id": {"type": str, "required": True},
        "learning_style": {"type": str, "required": True},
        "difficulty_preference": {"type": str, "required": True}
    })
    @log_operation(operation_name="create_ai_profile")
    def create_user_profile(
        self,
        user_id: str,
        learning_style: str,
        difficulty_preference: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> UserProfile:
        """创建用户AI档案"""
        logger.info(f"创建用户AI档案: {user_id}")

        # 解析学习风格和难度偏好
        try:
            learning_style_enum = LearningStyle(learning_style)
            difficulty_enum = DifficultyPreference(difficulty_preference)
        except ValueError as e:
            logger.warning(f"无效的学习风格或难度偏好: {e}")
            learning_style_enum = LearningStyle.VISUAL
            difficulty_enum = DifficultyPreference.BEGINNER

        profile = UserProfile(
            user_id=user_id,
            learning_style=learning_style_enum,
            difficulty_preference=difficulty_enum
        )

        # 添加额外信息
        if additional_info:
            profile.interests = additional_info.get("interests", [])
            profile.learning_goals = additional_info.get("learning_goals", [])
            profile.preferred_topics = additional_info.get("preferred_topics", [])
            profile.study_time_preference = additional_info.get("study_time_preference", "morning")
            profile.session_duration_preference = additional_info.get("session_duration_preference", 30)
            profile.feedback_frequency = additional_info.get("feedback_frequency", "immediate")

        self.user_profiles[user_id] = profile

        # 生成初始推荐
        self._generate_initial_recommendations(user_id)

        return profile

    def _generate_initial_recommendations(self, user_id: str) -> None:
        """生成初始推荐"""
        if user_id not in self.user_profiles:
            return

        profile = self.user_profiles[user_id]
        recommendations = []

        # 基于学习风格生成推荐
        if profile.learning_style == LearningStyle.VISUAL:
            recommendations.append(AIRecommendation(
                type="study",
                priority=4,
                title="视觉学习资源",
                description="基于您的视觉学习偏好，推荐观看化学概念视频和3D分子模型",
                estimated_time=30,
                difficulty_level=profile.difficulty_preference.value,
                learning_objectives=["理解分子结构", "掌握化学键理论"],
                resources=["3D分子模型", "化学概念视频", "交互式图表"],
                ai_reasoning="视觉学习者更容易通过图表和模型理解抽象概念",
                confidence_score=0.85
            ))

        # 基于难度偏好生成推荐
        difficulty_topics = self.knowledge_base["chemistry_concepts"].get(
            profile.difficulty_preference.value, []
        )

        if difficulty_topics:
            recommendations.append(AIRecommendation(
                type="experiment",
                priority=3,
                title=f"{profile.difficulty_preference.value.title()}级实验",
                description=f"适合您当前水平的{profile.difficulty_preference.value}级化学实验",
                estimated_time=45,
                difficulty_level=profile.difficulty_preference.value,
                learning_objectives=difficulty_topics[:3],
                ai_reasoning=f"基于您的{profile.difficulty_preference.value}难度偏好",
                confidence_score=0.80
            ))

        self.ai_recommendations[user_id] = recommendations

    @enhance_robustness(
        operation_name="start_learning_session",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="start_session")
    def start_learning_session(
        self,
        user_id: str,
        session_type: str = "general",
        topics: Optional[List[str]] = None
    ) -> LearningSession:
        """开始学习会话"""
        session_id = f"session_{user_id}_{int(time.time())}"

        session = LearningSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(),
            topics_covered=topics or []
        )

        self.learning_sessions[session_id] = session

        logger.info(f"学习会话已开始: {session_id}")
        return session

    @enhance_robustness(
        operation_name="update_learning_session",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="update_session")
    def update_learning_session(
        self,
        session_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """更新学习会话"""
        if session_id not in self.learning_sessions:
            logger.warning(f"学习会话 {session_id} 不存在")
            return False

        session = self.learning_sessions[session_id]

        # 更新会话数据
        if "topics_covered" in update_data:
            session.topics_covered.extend(update_data["topics_covered"])

        if "exercises_completed" in update_data:
            session.exercises_completed += update_data["exercises_completed"]

        if "accuracy_score" in update_data:
            session.accuracy_score = update_data["accuracy_score"]

        if "engagement_level" in update_data:
            session.engagement_level = update_data["engagement_level"]

        if "ai_interactions" in update_data:
            session.ai_interactions += update_data["ai_interactions"]

        if "hints_requested" in update_data:
            session.hints_requested += update_data["hints_requested"]

        if "concepts_mastered" in update_data:
            session.concepts_mastered.extend(update_data["concepts_mastered"])

        if "concepts_struggled" in update_data:
            session.concepts_struggled.extend(update_data["concepts_struggled"])

        return True

    @enhance_robustness(
        operation_name="end_learning_session",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="end_session")
    def end_learning_session(self, session_id: str) -> Optional[LearningSession]:
        """结束学习会话"""
        if session_id not in self.learning_sessions:
            logger.warning(f"学习会话 {session_id} 不存在")
            return None

        session = self.learning_sessions[session_id]
        session.end_time = datetime.now()
        session.duration = (session.end_time - session.start_time).total_seconds() / 60  # 分钟

        # 生成学习洞察
        self._generate_learning_insights(session)

        logger.info(f"学习会话已结束: {session_id}, 持续时间: {session.duration:.1f}分钟")
        return session

    def _generate_learning_insights(self, session: LearningSession) -> None:
        """生成学习洞察"""
        insights = []

        # 分析学习模式
        if session.accuracy_score > 0.8:
            insights.append(LearningInsight(
                insight_type="strength",
                title="高准确率表现",
                description=f"您在本次学习中达到了{session.accuracy_score:.1%}的准确率，表现优秀",
                data_points=[{"metric": "accuracy", "value": session.accuracy_score}],
                confidence=0.9,
                actionable=True,
                suggested_actions=["继续保持当前学习节奏", "尝试更高难度的内容"]
            ))

        # 分析参与度
        if session.engagement_level > 0.7:
            insights.append(LearningInsight(
                insight_type="strength",
                title="高参与度",
                description="您在学习过程中表现出很高的参与度",
                data_points=[{"metric": "engagement", "value": session.engagement_level}],
                confidence=0.8,
                actionable=True,
                suggested_actions=["利用高参与度学习更多内容", "分享学习经验"]
            ))

        # 分析困难概念
        if session.concepts_struggled:
            insights.append(LearningInsight(
                insight_type="weakness",
                title="需要加强的概念",
                description=f"您在以下概念上遇到了困难: {', '.join(session.concepts_struggled)}",
                data_points=[{"concepts": session.concepts_struggled}],
                confidence=0.85,
                actionable=True,
                suggested_actions=[
                    "复习相关基础概念",
                    "寻求额外练习机会",
                    "观看相关教学视频"
                ]
            ))

        # 分析AI交互模式
        if session.ai_interactions > 5:
            insights.append(LearningInsight(
                insight_type="pattern",
                title="积极使用AI助手",
                description="您在学习过程中积极使用AI助手，这是一个很好的学习策略",
                data_points=[{"metric": "ai_interactions", "value": session.ai_interactions}],
                confidence=0.75,
                actionable=True,
                suggested_actions=["继续利用AI助手解决问题", "尝试更多AI功能"]
            ))

        self.learning_insights[session.user_id] = insights

    @enhance_robustness(
        operation_name="get_ai_recommendations",
        security_level="low",
        enable_caching=True
    )
    def get_ai_recommendations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[AIRecommendation]:
        """获取AI推荐"""
        if user_id not in self.ai_recommendations:
            return []

        recommendations = self.ai_recommendations[user_id]

        # 按优先级排序
        recommendations.sort(key=lambda x: x.priority, reverse=True)

        return recommendations[:limit]

    @enhance_robustness(
        operation_name="get_learning_insights",
        security_level="low",
        enable_caching=True
    )
    def get_learning_insights(
        self,
        user_id: str,
        insight_type: Optional[str] = None
    ) -> List[LearningInsight]:
        """获取学习洞察"""
        if user_id not in self.learning_insights:
            return []

        insights = self.learning_insights[user_id]

        if insight_type:
            insights = [insight for insight in insights if insight.insight_type == insight_type]

        return insights

    @enhance_robustness(
        operation_name="ask_ai_question",
        security_level="medium",
        enable_caching=True
    )
    @log_operation(operation_name="ai_question")
    def ask_ai_question(
        self,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """向AI提问"""
        try:
            # 获取用户档案
            profile = self.user_profiles.get(user_id)

            # 构建提示词
            prompt = self._build_question_prompt(question, profile, context)

            # 调用AI服务
            response = self._call_ai_service(prompt)

            # 记录AI交互
            if user_id in self.learning_sessions:
                session = self.learning_sessions[user_id]
                session.ai_interactions += 1

            return {
                "answer": response,
                "confidence": 0.8,
                "sources": ["知识库", "学习记录"],
                "follow_up_questions": self._generate_follow_up_questions(question),
                "related_topics": self._find_related_topics(question)
            }

        except Exception as e:
            logger.error(f"AI问答失败: {e}")
            return {
                "answer": "抱歉，我暂时无法回答您的问题。请稍后再试。",
                "confidence": 0.0,
                "error": str(e)
            }

    def _build_question_prompt(
        self,
        question: str,
        profile: Optional[UserProfile],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建问题提示词"""
        prompt = f"问题: {question}\n\n"

        if profile:
            prompt += "用户信息:\n"
            prompt += f"- 学习风格: {profile.learning_style.value}\n"
            prompt += f"- 难度偏好: {profile.difficulty_preference.value}\n"
            prompt += f"- 兴趣领域: {', '.join(profile.interests)}\n\n"

        if context:
            prompt += "上下文信息:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += "请提供准确、详细的回答，并考虑用户的学习背景。"

        return prompt

    def _call_ai_service(self, prompt: str) -> str:
        """调用AI服务"""
        if self.ai_provider == AIProvider.OLLAMA:
            return self._call_ollama(prompt)
        elif self.ai_provider == AIProvider.LOCAL:
            return self._call_local_ai(prompt)
        else:
            return "AI服务暂不可用"

    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama服务"""
        try:
            import requests

            data = {
                "model": "llama2",
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(
                "http://localhost:11434/api/generate",
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "无法生成回答")
            else:
                return "Ollama服务不可用"

        except Exception as e:
            logger.error(f"Ollama调用失败: {e}")
            return "AI服务调用失败"

    def _call_local_ai(self, prompt: str) -> str:
        """调用本地AI服务"""
        # 简化的本地AI实现
        if "化学" in prompt or "实验" in prompt:
            return "这是一个化学相关的问题。建议您查阅相关教材或咨询老师获取详细解答。"
        elif "学习" in prompt or "方法" in prompt:
            return "建议您采用多种学习方法结合，包括理论学习、实践操作和定期复习。"
        else:
            return "这是一个很好的问题。建议您继续深入学习相关概念。"

    def _generate_follow_up_questions(self, question: str) -> List[str]:
        """生成后续问题"""
        follow_ups = []

        if "实验" in question:
            follow_ups.extend([
                "这个实验的原理是什么？",
                "实验过程中需要注意什么？",
                "如何分析实验结果？"
            ])

        if "化学" in question:
            follow_ups.extend([
                "这个概念在实际生活中有哪些应用？",
                "相关的化学方程式是什么？",
                "如何验证这个化学现象？"
            ])

        return follow_ups[:3]  # 返回最多3个后续问题

    def _find_related_topics(self, question: str) -> List[str]:
        """查找相关主题"""
        related_topics = []

        # 基于关键词匹配
        for _difficulty, topics in self.knowledge_base["chemistry_concepts"].items():
            for topic in topics:
                if topic in question:
                    related_topics.extend(topics)
                    break

        return list(set(related_topics))[:5]  # 返回最多5个相关主题

    @enhance_robustness(
        operation_name="get_learning_analytics",
        security_level="low",
        enable_caching=True
    )
    def get_learning_analytics(self, user_id: str) -> Dict[str, Any]:
        """获取学习分析"""
        if user_id not in self.user_profiles:
            return {}

        profile = self.user_profiles[user_id]

        # 获取用户的所有学习会话
        user_sessions = [
            session for session in self.learning_sessions.values()
            if session.user_id == user_id
        ]

        if not user_sessions:
            return {
                "total_sessions": 0,
                "total_time": 0,
                "average_accuracy": 0.0,
                "learning_trend": "stable"
            }

        # 计算统计数据
        total_sessions = len(user_sessions)
        total_time = sum(session.duration or 0 for session in user_sessions)
        average_accuracy = sum(session.accuracy_score for session in user_sessions) / total_sessions

        # 分析学习趋势
        recent_sessions = user_sessions[-5:] if len(user_sessions) >= 5 else user_sessions
        recent_accuracy = sum(session.accuracy_score for session in recent_sessions) / len(recent_sessions)

        if recent_accuracy > average_accuracy:
            learning_trend = "improving"
        elif recent_accuracy < average_accuracy:
            learning_trend = "declining"
        else:
            learning_trend = "stable"

        return {
            "total_sessions": total_sessions,
            "total_time": total_time,
            "average_accuracy": average_accuracy,
            "recent_accuracy": recent_accuracy,
            "learning_trend": learning_trend,
            "preferred_topics": profile.preferred_topics,
            "learning_style": profile.learning_style.value,
            "difficulty_preference": profile.difficulty_preference.value,
            "ai_interactions": sum(session.ai_interactions for session in user_sessions),
            "concepts_mastered": list(set(
                concept for session in user_sessions
                for concept in session.concepts_mastered
            )),
            "concepts_struggled": list(set(
                concept for session in user_sessions
                for concept in session.concepts_struggled
            ))
        }


# 全局实例
enhanced_ai_system = EnhancedAISystem()
