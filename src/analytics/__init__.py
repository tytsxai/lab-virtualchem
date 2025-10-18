"""分析模块"""

from .feedback_analytics import (
    FeedbackAnalytics,
    FeedbackTrend,
    Insight,
    InsightType,
    NPSAnalysis,
    TrendDirection,
    UserSegment,
)
from .feedback_processor import (
    AutoResponseType,
    FeedbackPattern,
    FeedbackProcessor,
    ProcessedFeedback,
)

__all__ = [
    "FeedbackAnalytics",
    "FeedbackProcessor",
    "FeedbackTrend",
    "UserSegment",
    "Insight",
    "InsightType",
    "NPSAnalysis",
    "TrendDirection",
    "AutoResponseType",
    "FeedbackPattern",
    "ProcessedFeedback",
]
