"""
AI智能辅助模块
提供智能实验建议、错误诊断、个性化学习等功能
"""

from .error_diagnosis import ErrorDiagnosis, ErrorPattern
from .experiment_assistant import ExperimentAssistant, ExperimentSuggestion
from .learning_analytics import LearningAnalytics, LearningPattern
from .smart_hints import HintType, SmartHints

__all__ = [
    # 实验助手
    "ExperimentAssistant",
    "ExperimentSuggestion",
    # 错误诊断
    "ErrorDiagnosis",
    "ErrorPattern",
    # 学习分析
    "LearningAnalytics",
    "LearningPattern",
    # 智能提示
    "SmartHints",
    "HintType",
]
