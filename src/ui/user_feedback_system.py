"""
用户反馈系统
收集用户反馈，分析用户情感，基于反馈改进系统
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackType(str, Enum):
    """反馈类型"""

    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    GENERAL_FEEDBACK = "general_feedback"
    RATING = "rating"
    SURVEY = "survey"


class SentimentType(str, Enum):
    """情感类型"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class PriorityLevel(str, Enum):
    """优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class UserFeedback:
    """用户反馈"""

    feedback_id: str
    user_id: str
    feedback_type: FeedbackType
    title: str
    content: str
    rating: int  # 1-5星
    sentiment: SentimentType
    priority: PriorityLevel
    timestamp: datetime
    context: dict[str, Any]
    tags: list[str]
    status: str  # new, in_progress, resolved, closed
    response: str | None = None
    response_time: datetime | None = None


@dataclass
class SentimentAnalysis:
    """情感分析结果"""

    sentiment: SentimentType
    confidence: float
    positive_score: float
    negative_score: float
    neutral_score: float
    keywords: list[str]
    emotions: list[str]


@dataclass
class FeedbackTrend:
    """反馈趋势"""

    period: str
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    avg_rating: float
    common_issues: list[tuple[str, int]]
    sentiment_trend: float  # 情感趋势变化


class UserFeedbackSystem(QObject):
    """用户反馈系统"""

    # 信号
    feedback_received = Signal(str, dict)  # 反馈ID, 反馈数据
    sentiment_analyzed = Signal(str, SentimentType)  # 反馈ID, 情感类型
    trend_updated = Signal(dict)  # 趋势数据
    improvement_suggested = Signal(str, str)  # 组件, 建议

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 反馈数据
        self.feedbacks: dict[str, UserFeedback] = {}
        self.feedback_history: deque = deque(maxlen=1000)
        self.sentiment_cache: dict[str, SentimentAnalysis] = {}

        # 分析数据
        self.sentiment_keywords = {
            "positive": ["好", "棒", "优秀", "满意", "喜欢", "推荐", "完美", "流畅", "快速", "稳定"],
            "negative": ["差", "慢", "卡", "错误", "崩溃", "问题", "困难", "复杂", "bug", "失败"],
            "neutral": ["一般", "普通", "还行", "可以", "正常", "标准", "中等"],
        }

        self.emotion_keywords = {
            "anger": ["愤怒", "生气", "恼火", "烦躁", "不满"],
            "joy": ["高兴", "开心", "兴奋", "满意", "愉快"],
            "sadness": ["失望", "沮丧", "难过", "遗憾", "失落"],
            "fear": ["担心", "害怕", "焦虑", "紧张", "不安"],
            "surprise": ["惊讶", "意外", "惊喜", "震惊", "意外"],
        }

        # 设置
        self.auto_analysis_enabled = True
        self.trend_analysis_enabled = True
        self.improvement_suggestions_enabled = True

        # 定时器
        self.analysis_timer = QTimer()
        self.analysis_timer.timeout.connect(self.analyze_trends)
        self.analysis_timer.start(300000)  # 5分钟分析一次

        # 数据持久化
        self.data_file = Path("data/user_feedback.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        self.load_data()

        logger.info("用户反馈系统初始化完成")

    def submit_feedback(
        self,
        user_id: str,
        feedback_type: FeedbackType,
        title: str,
        content: str,
        rating: int = 3,
        context: dict[str, Any] = None,
        tags: list[str] = None,
    ) -> str:
        """提交反馈"""
        try:
            feedback_id = f"feedback_{int(time.time() * 1000)}"

            # 情感分析
            sentiment_analysis = self._analyze_sentiment(content)

            # 确定优先级
            priority = self._determine_priority(feedback_type, rating, sentiment_analysis)

            # 创建反馈对象
            feedback = UserFeedback(
                feedback_id=feedback_id,
                user_id=user_id,
                feedback_type=feedback_type,
                title=title,
                content=content,
                rating=rating,
                sentiment=sentiment_analysis.sentiment,
                priority=priority,
                timestamp=datetime.now(),
                context=context or {},
                tags=tags or [],
                status="new",
            )

            # 保存反馈
            self.feedbacks[feedback_id] = feedback
            self.feedback_history.append(feedback)

            # 缓存情感分析结果
            self.sentiment_cache[feedback_id] = sentiment_analysis

            # 发送信号
            self.feedback_received.emit(
                feedback_id,
                {
                    "title": title,
                    "type": feedback_type.value,
                    "rating": rating,
                    "sentiment": sentiment_analysis.sentiment.value,
                    "priority": priority.value,
                },
            )

            self.sentiment_analyzed.emit(feedback_id, sentiment_analysis.sentiment)

            logger.info(f"用户反馈已提交: {feedback_id} - {title}")

            return feedback_id

        except Exception as e:
            logger.error(f"提交反馈失败: {e}")
            return ""

    def _analyze_sentiment(self, text: str) -> SentimentAnalysis:
        """分析情感"""
        try:
            # 简单的基于关键词的情感分析
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            # 统计关键词
            for keyword in self.sentiment_keywords["positive"]:
                positive_count += len(re.findall(keyword, text, re.IGNORECASE))

            for keyword in self.sentiment_keywords["negative"]:
                negative_count += len(re.findall(keyword, text, re.IGNORECASE))

            for keyword in self.sentiment_keywords["neutral"]:
                neutral_count += len(re.findall(keyword, text, re.IGNORECASE))

            # 计算情感分数
            total_words = len(text.split())
            if total_words == 0:
                return SentimentAnalysis(
                    sentiment=SentimentType.NEUTRAL,
                    confidence=0.0,
                    positive_score=0.0,
                    negative_score=0.0,
                    neutral_score=1.0,
                    keywords=[],
                    emotions=[],
                )

            positive_score = positive_count / total_words
            negative_score = negative_count / total_words
            neutral_score = neutral_count / total_words

            # 确定主要情感
            if positive_score > negative_score and positive_score > neutral_score:
                sentiment = SentimentType.POSITIVE
                confidence = positive_score
            elif negative_score > positive_score and negative_score > neutral_score:
                sentiment = SentimentType.NEGATIVE
                confidence = negative_score
            elif positive_score > 0 and negative_score > 0:
                sentiment = SentimentType.MIXED
                confidence = min(positive_score, negative_score)
            else:
                sentiment = SentimentType.NEUTRAL
                confidence = neutral_score

            # 提取关键词
            keywords = []
            for _category, words in self.sentiment_keywords.items():
                for word in words:
                    if word in text:
                        keywords.append(word)

            # 检测情绪
            emotions = []
            for emotion, words in self.emotion_keywords.items():
                for word in words:
                    if word in text:
                        emotions.append(emotion)

            return SentimentAnalysis(
                sentiment=sentiment,
                confidence=confidence,
                positive_score=positive_score,
                negative_score=negative_score,
                neutral_score=neutral_score,
                keywords=keywords,
                emotions=emotions,
            )

        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return SentimentAnalysis(
                sentiment=SentimentType.NEUTRAL,
                confidence=0.0,
                positive_score=0.0,
                negative_score=0.0,
                neutral_score=1.0,
                keywords=[],
                emotions=[],
            )

    def _determine_priority(
        self, feedback_type: FeedbackType, rating: int, sentiment_analysis: SentimentAnalysis
    ) -> PriorityLevel:
        """确定优先级"""
        try:
            # 基于反馈类型
            type_priority = {
                FeedbackType.BUG_REPORT: 3,
                FeedbackType.PERFORMANCE_ISSUE: 3,
                FeedbackType.USABILITY_ISSUE: 2,
                FeedbackType.FEATURE_REQUEST: 1,
                FeedbackType.GENERAL_FEEDBACK: 1,
                FeedbackType.RATING: 0,
                FeedbackType.SURVEY: 0,
            }

            # 基于评分
            rating_priority = 5 - rating  # 评分越低，优先级越高

            # 基于情感
            sentiment_priority = {
                SentimentType.NEGATIVE: 2,
                SentimentType.MIXED: 1,
                SentimentType.NEUTRAL: 0,
                SentimentType.POSITIVE: 0,
            }

            # 计算总优先级
            total_priority = (
                type_priority.get(feedback_type, 0)
                + rating_priority
                + sentiment_priority.get(sentiment_analysis.sentiment, 0)
            )

            # 转换为优先级等级
            if total_priority >= 6:
                return PriorityLevel.CRITICAL
            elif total_priority >= 4:
                return PriorityLevel.HIGH
            elif total_priority >= 2:
                return PriorityLevel.MEDIUM
            else:
                return PriorityLevel.LOW

        except Exception as e:
            logger.error(f"确定优先级失败: {e}")
            return PriorityLevel.MEDIUM

    def analyze_trends(self) -> None:
        """分析反馈趋势"""
        if not self.trend_analysis_enabled:
            return

        try:
            logger.debug("开始分析反馈趋势")

            # 分析不同时间段的趋势
            trends = []

            # 最近24小时
            trends.append(self._analyze_period_trend("24h", timedelta(hours=24)))

            # 最近7天
            trends.append(self._analyze_period_trend("7d", timedelta(days=7)))

            # 最近30天
            trends.append(self._analyze_period_trend("30d", timedelta(days=30)))

            # 发送趋势更新信号
            trend_data = {"trends": [trend.__dict__ for trend in trends], "analysis_time": datetime.now().isoformat()}

            self.trend_updated.emit(trend_data)

            # 生成改进建议
            if self.improvement_suggestions_enabled:
                self._generate_improvement_suggestions(trends)

            logger.debug("反馈趋势分析完成")

        except Exception as e:
            logger.error(f"分析反馈趋势失败: {e}")

    def _analyze_period_trend(self, period: str, time_delta: timedelta) -> FeedbackTrend:
        """分析特定时间段的趋势"""
        try:
            cutoff_time = datetime.now() - time_delta
            period_feedbacks = [feedback for feedback in self.feedback_history if feedback.timestamp >= cutoff_time]

            if not period_feedbacks:
                return FeedbackTrend(
                    period=period,
                    total_feedback=0,
                    positive_feedback=0,
                    negative_feedback=0,
                    avg_rating=0.0,
                    common_issues=[],
                    sentiment_trend=0.0,
                )

            # 统计情感
            positive_count = sum(1 for f in period_feedbacks if f.sentiment == SentimentType.POSITIVE)
            negative_count = sum(1 for f in period_feedbacks if f.sentiment == SentimentType.NEGATIVE)

            # 计算平均评分
            avg_rating = sum(f.rating for f in period_feedbacks) / len(period_feedbacks)

            # 统计常见问题
            issue_counts = defaultdict(int)
            for feedback in period_feedbacks:
                for tag in feedback.tags:
                    issue_counts[tag] += 1

            common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # 计算情感趋势
            sentiment_trend = (positive_count - negative_count) / len(period_feedbacks)

            return FeedbackTrend(
                period=period,
                total_feedback=len(period_feedbacks),
                positive_feedback=positive_count,
                negative_feedback=negative_count,
                avg_rating=avg_rating,
                common_issues=common_issues,
                sentiment_trend=sentiment_trend,
            )

        except Exception as e:
            logger.error(f"分析时间段趋势失败: {e}")
            return FeedbackTrend(
                period=period,
                total_feedback=0,
                positive_feedback=0,
                negative_feedback=0,
                avg_rating=0.0,
                common_issues=[],
                sentiment_trend=0.0,
            )

    def _generate_improvement_suggestions(self, trends: list[FeedbackTrend]) -> None:
        """生成改进建议"""
        try:
            suggestions = []

            # 分析最近趋势
            recent_trend = trends[0]  # 24小时趋势

            if recent_trend.sentiment_trend < -0.3:
                suggestions.append(("system", "用户满意度下降，需要立即关注"))

            if recent_trend.avg_rating < 3.0:
                suggestions.append(("system", "平均评分较低，需要改进用户体验"))

            # 分析常见问题
            for issue, count in recent_trend.common_issues:
                if count > 3:  # 问题出现频率较高
                    suggestions.append((issue, f"问题 '{issue}' 出现频率较高，需要优先解决"))

            # 分析反馈类型分布
            feedback_types = defaultdict(int)
            for feedback in self.feedback_history:
                feedback_types[feedback.feedback_type] += 1

            if feedback_types[FeedbackType.BUG_REPORT] > feedback_types[FeedbackType.FEATURE_REQUEST]:
                suggestions.append(("system", "Bug报告较多，需要加强测试"))

            # 发送建议
            for component, suggestion in suggestions:
                self.improvement_suggested.emit(component, suggestion)

        except Exception as e:
            logger.error(f"生成改进建议失败: {e}")

    def get_feedback_summary(self, user_id: str = None) -> dict[str, Any]:
        """获取反馈摘要"""
        try:
            if user_id:
                user_feedbacks = [f for f in self.feedback_history if f.user_id == user_id]
            else:
                user_feedbacks = list(self.feedback_history)

            if not user_feedbacks:
                return {"total": 0, "avg_rating": 0.0, "sentiment_distribution": {}}

            # 计算统计信息
            total_feedback = len(user_feedbacks)
            avg_rating = sum(f.rating for f in user_feedbacks) / total_feedback

            # 情感分布
            sentiment_counts = defaultdict(int)
            for feedback in user_feedbacks:
                sentiment_counts[feedback.sentiment] += 1

            sentiment_distribution = {
                sentiment.value: count / total_feedback for sentiment, count in sentiment_counts.items()
            }

            # 反馈类型分布
            type_counts = defaultdict(int)
            for feedback in user_feedbacks:
                type_counts[feedback.feedback_type] += 1

            type_distribution = {
                feedback_type.value: count / total_feedback for feedback_type, count in type_counts.items()
            }

            # 优先级分布
            priority_counts = defaultdict(int)
            for feedback in user_feedbacks:
                priority_counts[feedback.priority] += 1

            priority_distribution = {
                priority.value: count / total_feedback for priority, count in priority_counts.items()
            }

            return {
                "total": total_feedback,
                "avg_rating": avg_rating,
                "sentiment_distribution": sentiment_distribution,
                "type_distribution": type_distribution,
                "priority_distribution": priority_distribution,
                "recent_feedback": [
                    {
                        "id": f.feedback_id,
                        "title": f.title,
                        "type": f.feedback_type.value,
                        "rating": f.rating,
                        "sentiment": f.sentiment.value,
                        "priority": f.priority.value,
                        "timestamp": f.timestamp.isoformat(),
                    }
                    for f in user_feedbacks[-10:]  # 最近10条
                ],
            }

        except Exception as e:
            logger.error(f"获取反馈摘要失败: {e}")
            return {"error": str(e)}

    def respond_to_feedback(self, feedback_id: str, response: str) -> bool:
        """回复反馈"""
        try:
            if feedback_id not in self.feedbacks:
                return False

            feedback = self.feedbacks[feedback_id]
            feedback.response = response
            feedback.response_time = datetime.now()
            feedback.status = "responded"

            logger.info(f"反馈已回复: {feedback_id}")
            return True

        except Exception as e:
            logger.error(f"回复反馈失败: {e}")
            return False

    def close_feedback(self, feedback_id: str) -> bool:
        """关闭反馈"""
        try:
            if feedback_id not in self.feedbacks:
                return False

            feedback = self.feedbacks[feedback_id]
            feedback.status = "closed"

            logger.info(f"反馈已关闭: {feedback_id}")
            return True

        except Exception as e:
            logger.error(f"关闭反馈失败: {e}")
            return False

    def get_high_priority_feedbacks(self) -> list[UserFeedback]:
        """获取高优先级反馈"""
        try:
            high_priority = [
                feedback
                for feedback in self.feedbacks.values()
                if feedback.priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]
                and feedback.status in ["new", "in_progress"]
            ]

            # 按优先级和时间排序
            high_priority.sort(key=lambda f: (f.priority.value, f.timestamp), reverse=True)

            return high_priority

        except Exception as e:
            logger.error(f"获取高优先级反馈失败: {e}")
            return []

    def save_data(self) -> None:
        """保存数据"""
        try:
            data = {
                "feedbacks": {
                    feedback_id: {
                        "feedback_id": feedback.feedback_id,
                        "user_id": feedback.user_id,
                        "feedback_type": feedback.feedback_type.value,
                        "title": feedback.title,
                        "content": feedback.content,
                        "rating": feedback.rating,
                        "sentiment": feedback.sentiment.value,
                        "priority": feedback.priority.value,
                        "timestamp": feedback.timestamp.isoformat(),
                        "context": feedback.context,
                        "tags": feedback.tags,
                        "status": feedback.status,
                        "response": feedback.response,
                        "response_time": feedback.response_time.isoformat() if feedback.response_time else None,
                    }
                    for feedback_id, feedback in self.feedbacks.items()
                },
                "sentiment_cache": {
                    feedback_id: {
                        "sentiment": analysis.sentiment.value,
                        "confidence": analysis.confidence,
                        "positive_score": analysis.positive_score,
                        "negative_score": analysis.negative_score,
                        "neutral_score": analysis.neutral_score,
                        "keywords": analysis.keywords,
                        "emotions": analysis.emotions,
                    }
                    for feedback_id, analysis in self.sentiment_cache.items()
                },
            }

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info("用户反馈数据已保存")

        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    def load_data(self) -> None:
        """加载数据"""
        try:
            if not self.data_file.exists():
                return

            with open(self.data_file, encoding="utf-8") as f:
                data = json.load(f)

            # 加载反馈数据
            for feedback_id, feedback_data in data.get("feedbacks", {}).items():
                feedback = UserFeedback(
                    feedback_id=feedback_data["feedback_id"],
                    user_id=feedback_data["user_id"],
                    feedback_type=FeedbackType(feedback_data["feedback_type"]),
                    title=feedback_data["title"],
                    content=feedback_data["content"],
                    rating=feedback_data["rating"],
                    sentiment=SentimentType(feedback_data["sentiment"]),
                    priority=PriorityLevel(feedback_data["priority"]),
                    timestamp=datetime.fromisoformat(feedback_data["timestamp"]),
                    context=feedback_data["context"],
                    tags=feedback_data["tags"],
                    status=feedback_data["status"],
                    response=feedback_data.get("response"),
                    response_time=(
                        datetime.fromisoformat(feedback_data["response_time"])
                        if feedback_data.get("response_time")
                        else None
                    ),
                )

                self.feedbacks[feedback_id] = feedback
                self.feedback_history.append(feedback)

            # 加载情感分析缓存
            for feedback_id, analysis_data in data.get("sentiment_cache", {}).items():
                analysis = SentimentAnalysis(
                    sentiment=SentimentType(analysis_data["sentiment"]),
                    confidence=analysis_data["confidence"],
                    positive_score=analysis_data["positive_score"],
                    negative_score=analysis_data["negative_score"],
                    neutral_score=analysis_data["neutral_score"],
                    keywords=analysis_data["keywords"],
                    emotions=analysis_data["emotions"],
                )

                self.sentiment_cache[feedback_id] = analysis

            logger.info("用户反馈数据已加载")

        except Exception as e:
            logger.error(f"加载数据失败: {e}")


class FeedbackDialog(QDialog):
    """反馈对话框"""

    feedback_submitted = Signal(str, str, str, int)  # 用户ID, 类型, 内容, 评分

    def __init__(self, user_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.user_id = user_id
        self.feedback_system = UserFeedbackSystem()

        self.setWindowTitle("用户反馈")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("请告诉我们您的想法")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 反馈类型
        type_label = QLabel("反馈类型:")
        layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Bug报告", "功能建议", "使用问题", "性能问题", "一般反馈", "评分"])
        layout.addWidget(self.type_combo)

        # 标题
        title_input_label = QLabel("标题:")
        layout.addWidget(title_input_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请简要描述您的问题或建议")
        layout.addWidget(self.title_input)

        # 内容
        content_label = QLabel("详细描述:")
        layout.addWidget(content_label)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("请详细描述您的问题、建议或体验...")
        self.content_input.setMinimumHeight(150)
        layout.addWidget(self.content_input)

        # 评分
        rating_label = QLabel("评分 (1-5星):")
        layout.addWidget(rating_label)

        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["1", "2", "3", "4", "5"])
        self.rating_combo.setCurrentText("3")
        layout.addWidget(self.rating_combo)

        # 按钮
        button_layout = QHBoxLayout()

        self.submit_btn = QPushButton("提交反馈")
        self.submit_btn.clicked.connect(self.submit_feedback)
        button_layout.addWidget(self.submit_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def submit_feedback(self):
        """提交反馈"""
        try:
            # 获取输入
            feedback_type = self.type_combo.currentText()
            title = self.title_input.text().strip()
            content = self.content_input.toPlainText().strip()
            rating = int(self.rating_combo.currentText())

            # 验证输入
            if not title or not content:
                QMessageBox.warning(self, "警告", "请填写标题和详细描述")
                return

            # 映射反馈类型
            type_mapping = {
                "Bug报告": FeedbackType.BUG_REPORT,
                "功能建议": FeedbackType.FEATURE_REQUEST,
                "使用问题": FeedbackType.USABILITY_ISSUE,
                "性能问题": FeedbackType.PERFORMANCE_ISSUE,
                "一般反馈": FeedbackType.GENERAL_FEEDBACK,
                "评分": FeedbackType.RATING,
            }

            feedback_type_enum = type_mapping.get(feedback_type, FeedbackType.GENERAL_FEEDBACK)

            # 提交反馈
            feedback_id = self.feedback_system.submit_feedback(
                user_id=self.user_id, feedback_type=feedback_type_enum, title=title, content=content, rating=rating
            )

            if feedback_id:
                QMessageBox.information(self, "成功", "反馈已提交，感谢您的反馈！")
                self.feedback_submitted.emit(self.user_id, feedback_type, content, rating)
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "提交失败，请稍后重试")

        except Exception as e:
            logger.error(f"提交反馈失败: {e}")
            QMessageBox.critical(self, "错误", f"提交失败: {e}")


# 全局用户反馈系统实例
user_feedback_system = UserFeedbackSystem()
