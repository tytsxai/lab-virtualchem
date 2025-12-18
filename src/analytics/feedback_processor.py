"""
自动化反馈处理系统
提供智能的反馈分类、优先级排序和自动响应
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AutoResponseType(str, Enum):
    """自动响应类型"""

    ACKNOWLEDGMENT = "acknowledgment"  # 确认收到
    SOLUTION = "solution"  # 提供解决方案
    ESCALATION = "escalation"  # 升级处理
    FEEDBACK_REQUEST = "feedback_request"  # 请求更多信息


@dataclass
class FeedbackPattern:
    """反馈模式"""

    pattern_id: str
    name: str
    keywords: list[str]
    regex_patterns: list[str]
    category: str
    priority: str
    auto_response: str | None = None
    solution_steps: list[str] | None = None


@dataclass
class ProcessedFeedback:
    """处理后的反馈"""

    feedback_id: str
    original_feedback: dict[str, Any]
    detected_patterns: list[str]
    auto_category: str
    auto_priority: str
    extracted_entities: dict[str, Any]
    sentiment_score: float
    urgency_score: float
    suggested_response: str | None
    requires_human_review: bool
    processing_timestamp: datetime


class FeedbackProcessor(QObject):
    """反馈处理器"""

    # 信号
    feedback_processed = Signal(str, dict)  # 反馈ID, 处理结果
    pattern_detected = Signal(str, str)  # 反馈ID, 模式名称
    auto_response_generated = Signal(str, str)  # 反馈ID, 响应内容
    escalation_required = Signal(str, dict)  # 反馈ID, 详情

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 模式库
        self.patterns: dict[str, FeedbackPattern] = {}
        self.load_patterns()

        # 实体提取规则
        self.entity_patterns = {
            "experiment_name": r"实验[：:]\s*([^\s，,。.]+)",
            "feature_name": r"功能[：:]\s*([^\s，,。.]+)",
            "error_code": r"错误[代]?码[：:]?\s*([A-Z0-9-]+)",
            "version": r"版本[：:]?\s*([\d.]+)",
            "device": r"(Windows|Mac|Linux|iOS|Android)\s*([\d.]*)",
        }

        # 优先级规则
        self.priority_rules = {
            "critical": ["崩溃", "crash", "无法使用", "数据丢失", "cannot", "失败"],
            "high": ["bug", "错误", "问题", "error", "不工作", "缓慢"],
            "medium": ["建议", "改进", "优化", "suggest", "improve"],
            "low": ["疑问", "咨询", "question", "询问"],
        }

        # 自动响应模板
        self.response_templates = {
            "bug_report": "感谢您的反馈！我们已经收到您关于{issue}的Bug报告。我们的技术团队正在调查此问题，预计将在{timeline}内给您答复。",
            "feature_request": "感谢您的建议！关于{feature}的功能需求我们已记录，我们会在产品规划中认真考虑您的建议。",
            "usability_issue": "感谢您的反馈！关于{issue}的使用问题，请尝试以下步骤：\n{steps}",
            "general": "感谢您的反馈！我们已收到您的消息并会尽快处理。如有紧急问题，请联系客服。",
        }

        # 知识库（常见问题解决方案）
        self.knowledge_base: dict[str, dict[str, Any]] = {}
        self.load_knowledge_base()

        # 处理统计
        self.processing_stats = {
            "total": 0,
            "auto_resolved": 0,
            "escalated": 0,
            "pending": 0,
        }

        # 批处理定时器
        self.batch_timer = QTimer(self)
        self.batch_timer.timeout.connect(self.process_batch)
        self.batch_queue: list[dict[str, Any]] = []

        # 数据路径
        self.data_dir = Path("data/feedback_processing")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("反馈处理器初始化完成")

    def load_patterns(self) -> None:
        """加载反馈模式"""
        # 预定义模式
        default_patterns = [
            FeedbackPattern(
                pattern_id="bug_crash",
                name="崩溃Bug",
                keywords=["崩溃", "crash", "闪退", "无响应"],
                regex_patterns=[r"崩溃", r"crash", r"闪退"],
                category="bug_report",
                priority="critical",
                auto_response=None,
            ),
            FeedbackPattern(
                pattern_id="bug_performance",
                name="性能问题",
                keywords=["卡顿", "慢", "slow", "lag", "延迟"],
                regex_patterns=[r"卡[顿|住]", r"slow", r"lag"],
                category="performance_issue",
                priority="high",
                auto_response="我们注意到您反馈的性能问题。请尝试：1. 清除缓存 2. 关闭其他应用 3. 重启软件",
            ),
            FeedbackPattern(
                pattern_id="feature_request",
                name="功能需求",
                keywords=["希望", "建议", "能否", "添加", "增加"],
                regex_patterns=[r"希望.*能", r"建议.*增加", r"能否.*添加"],
                category="feature_request",
                priority="medium",
                auto_response="感谢您的宝贵建议！我们会认真考虑您提出的功能需求。",
            ),
            FeedbackPattern(
                pattern_id="usability_confusion",
                name="使用困惑",
                keywords=["不知道", "如何", "怎么", "找不到", "不会"],
                regex_patterns=[r"不知道.*如何", r"怎么.*操作", r"找不到"],
                category="usability_issue",
                priority="medium",
                auto_response=None,
            ),
            FeedbackPattern(
                pattern_id="data_loss",
                name="数据丢失",
                keywords=["丢失", "消失", "不见", "删除", "loss"],
                regex_patterns=[r"数据.*丢失", r"文件.*消失", r"data.*loss"],
                category="bug_report",
                priority="critical",
                auto_response=None,
            ),
        ]

        for pattern in default_patterns:
            self.patterns[pattern.pattern_id] = pattern

        logger.info(f"已加载 {len(self.patterns)} 个反馈模式")

    def load_knowledge_base(self) -> None:
        """加载知识库"""
        # 预定义解决方案
        self.knowledge_base = {
            "performance_slow": {
                "problem": "软件运行缓慢",
                "solutions": [
                    "清除应用缓存：设置 -> 性能 -> 清除缓存",
                    "关闭后台应用以释放内存",
                    "检查是否有可用更新",
                    "降低图形质量设置",
                ],
                "related_docs": ["性能优化指南", "系统要求说明"],
            },
            "experiment_not_loading": {
                "problem": "实验无法加载",
                "solutions": [
                    "检查网络连接",
                    "清除浏览器缓存",
                    "尝试刷新页面",
                    "检查实验文件是否完整",
                ],
                "related_docs": ["实验加载问题排查", "网络连接指南"],
            },
            "data_export_failed": {
                "problem": "数据导出失败",
                "solutions": [
                    "检查磁盘空间是否充足",
                    "确认导出路径权限",
                    "尝试导出为不同格式",
                    "减小导出数据量",
                ],
                "related_docs": ["数据导出指南"],
            },
        }

    def process_feedback(self, feedback: dict[str, Any]) -> ProcessedFeedback:
        """处理单个反馈"""
        try:
            feedback_id = feedback.get("feedback_id", "")
            content = feedback.get("content", "")
            title = feedback.get("title", "")

            # 检测模式
            detected_patterns = self.detect_patterns(content + " " + title)

            # 自动分类
            auto_category = self.categorize_feedback(content, detected_patterns)

            # 自动优先级
            auto_priority = self.determine_priority(
                content, feedback.get("rating", 3), detected_patterns
            )

            # 提取实体
            entities = self.extract_entities(content)

            # 情感分析
            sentiment_score = self.analyze_sentiment(content)

            # 紧急度评分
            urgency_score = self.calculate_urgency(
                content, feedback.get("rating", 3), detected_patterns
            )

            # 生成建议响应
            suggested_response = self.generate_response(
                auto_category, detected_patterns, entities, feedback.get("rating", 3)
            )

            # 是否需要人工审核
            requires_review = self.needs_human_review(
                auto_priority, sentiment_score, urgency_score, detected_patterns
            )

            # 创建处理结果
            processed = ProcessedFeedback(
                feedback_id=feedback_id,
                original_feedback=feedback,
                detected_patterns=detected_patterns,
                auto_category=auto_category,
                auto_priority=auto_priority,
                extracted_entities=entities,
                sentiment_score=sentiment_score,
                urgency_score=urgency_score,
                suggested_response=suggested_response,
                requires_human_review=requires_review,
                processing_timestamp=datetime.now(),
            )

            # 发送信号
            self.feedback_processed.emit(
                feedback_id, self._processed_to_dict(processed)
            )

            # 发送检测到的模式
            for pattern_id in detected_patterns:
                pattern = self.patterns.get(pattern_id)
                if pattern:
                    self.pattern_detected.emit(feedback_id, pattern.name)

            # 自动响应
            if suggested_response and not requires_review:
                self.auto_response_generated.emit(feedback_id, suggested_response)

            # 升级处理
            if requires_review or auto_priority == "critical":
                self.escalation_required.emit(
                    feedback_id,
                    {
                        "priority": auto_priority,
                        "urgency": urgency_score,
                        "patterns": detected_patterns,
                        "reason": "需要人工审核" if requires_review else "高优先级问题",
                    },
                )

            # 更新统计
            self.processing_stats["total"] += 1
            if not requires_review and suggested_response:
                self.processing_stats["auto_resolved"] += 1
            elif requires_review:
                self.processing_stats["escalated"] += 1
            else:
                self.processing_stats["pending"] += 1

            return processed

        except Exception as e:
            logger.error(f"处理反馈失败: {e}")
            # 返回一个空的ProcessedFeedback对象
            return ProcessedFeedback(
                feedback_id="",
                original_feedback={},
                detected_patterns=[],
                auto_category="general_feedback",
                auto_priority="low",
                extracted_entities={},
                sentiment_score=0.0,
                urgency_score=0.0,
                suggested_response=None,
                requires_human_review=True,
                processing_timestamp=datetime.now(),
            )

    def detect_patterns(self, text: str) -> list[str]:
        """检测反馈模式"""
        detected = []

        text_lower = text.lower()

        for pattern_id, pattern in self.patterns.items():
            # 关键词匹配
            if any(keyword in text_lower for keyword in pattern.keywords):
                detected.append(pattern_id)
                continue

            # 正则匹配
            for regex in pattern.regex_patterns:
                if re.search(regex, text, re.IGNORECASE):
                    detected.append(pattern_id)
                    break

        return detected

    def categorize_feedback(self, content: str, detected_patterns: list[str]) -> str:
        """自动分类反馈"""
        # 基于检测到的模式分类
        if detected_patterns:
            # 使用最高优先级模式的分类
            categories = []
            for pattern_id in detected_patterns:
                pattern = self.patterns.get(pattern_id)
                if pattern:
                    categories.append(pattern.category)

            # 返回最常见的分类
            if categories:
                return Counter(categories).most_common(1)[0][0]

        # 基于关键词分类
        content_lower = content.lower()

        if any(
            word in content_lower for word in ["bug", "错误", "崩溃", "问题", "故障"]
        ):
            return "bug_report"
        elif any(
            word in content_lower for word in ["建议", "希望", "功能", "添加", "增加"]
        ):
            return "feature_request"
        elif any(word in content_lower for word in ["慢", "卡", "延迟", "slow", "lag"]):
            return "performance_issue"
        elif any(word in content_lower for word in ["如何", "怎么", "不会", "不懂"]):
            return "usability_issue"
        else:
            return "general_feedback"

    def determine_priority(
        self, content: str, rating: int, detected_patterns: list[str]
    ) -> str:
        """确定优先级"""
        content_lower = content.lower()

        # 模式优先级
        if detected_patterns:
            priorities = []
            for pattern_id in detected_patterns:
                pattern = self.patterns.get(pattern_id)
                if pattern:
                    priorities.append(pattern.priority)

            # 使用最高优先级
            priority_order = ["critical", "high", "medium", "low"]
            for priority in priority_order:
                if priority in priorities:
                    return priority

        # 关键词优先级
        for priority, keywords in self.priority_rules.items():
            if any(keyword in content_lower for keyword in keywords):
                return priority

        # 评分优先级
        if rating <= 2:
            return "high"
        elif rating == 3:
            return "medium"
        else:
            return "low"

    def extract_entities(self, text: str) -> dict[str, Any]:
        """提取实体信息"""
        entities = {}

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches[0] if len(matches) == 1 else matches

        return entities

    def analyze_sentiment(self, text: str) -> float:
        """情感分析（简化版）"""
        # 积极词
        positive_words = [
            "好",
            "棒",
            "优秀",
            "满意",
            "喜欢",
            "推荐",
            "完美",
            "excellent",
            "great",
            "love",
        ]

        # 消极词
        negative_words = [
            "差",
            "烂",
            "糟糕",
            "失望",
            "讨厌",
            "垃圾",
            "bug",
            "错误",
            "崩溃",
            "bad",
            "terrible",
            "hate",
        ]

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0  # 中性

        # 返回-1到1之间的分数
        return (positive_count - negative_count) / total

    def calculate_urgency(
        self, content: str, rating: int, detected_patterns: list[str]
    ) -> float:
        """计算紧急度（0-100）"""
        urgency = 50.0  # 基础值

        # 评分影响
        urgency += (3 - rating) * 10  # 低评分增加紧急度

        # 关键词影响
        urgent_keywords = [
            "紧急",
            "急",
            "立即",
            "马上",
            "urgent",
            "asap",
            "immediately",
        ]
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in urgent_keywords):
            urgency += 20

        # 模式影响
        for pattern_id in detected_patterns:
            pattern = self.patterns.get(pattern_id)
            if pattern and pattern.priority == "critical":
                urgency += 30
            elif pattern and pattern.priority == "high":
                urgency += 15

        return min(100, max(0, urgency))

    def generate_response(
        self,
        category: str,
        detected_patterns: list[str],
        entities: dict[str, Any],
        rating: int,
    ) -> str | None:
        """生成建议响应"""
        # 检查是否有预定义响应
        for pattern_id in detected_patterns:
            pattern = self.patterns.get(pattern_id)
            if pattern and pattern.auto_response:
                return pattern.auto_response

        # 使用模板生成响应
        template = self.response_templates.get(
            category, self.response_templates["general"]
        )

        # 填充模板变量
        response = template

        # 替换实体
        if "experiment_name" in entities:
            response = response.replace(
                "{issue}", f"实验'{entities['experiment_name']}'"
            )
        elif "feature_name" in entities:
            response = response.replace("{feature}", entities["feature_name"])
        else:
            response = response.replace("{issue}", "您反馈的问题")
            response = response.replace("{feature}", "您建议的功能")

        # 时间线
        if rating <= 2:
            response = response.replace("{timeline}", "24小时")
        else:
            response = response.replace("{timeline}", "3个工作日")

        # 添加解决步骤
        if "{steps}" in response:
            steps = self._find_solution_steps(category, entities)
            response = response.replace(
                "{steps}", "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
            )

        return response

    def _find_solution_steps(
        self, category: str, entities: dict[str, Any]
    ) -> list[str]:
        """查找解决步骤"""
        # 从知识库匹配解决方案
        for kb_key, kb_item in self.knowledge_base.items():
            if category in kb_key or any(str(v) in kb_key for v in entities.values()):
                solutions = kb_item.get("solutions")
                if isinstance(solutions, list):
                    return solutions

        # 默认通用步骤
        return [
            "检查是否有可用的软件更新",
            "查看帮助文档相关章节",
            "如问题持续，请联系技术支持",
        ]

    def needs_human_review(
        self,
        priority: str,
        sentiment_score: float,
        urgency_score: float,
        detected_patterns: list[str],
    ) -> bool:
        """判断是否需要人工审核"""
        # 关键问题需要人工审核
        if priority == "critical":
            return True

        # 极度负面情感
        if sentiment_score < -0.7:
            return True

        # 高紧急度
        if urgency_score > 80:
            return True

        # 复杂问题（多个模式）
        if len(detected_patterns) >= 3:
            return True

        return False

    def add_to_batch(self, feedback: dict[str, Any]) -> None:
        """添加到批处理队列"""
        self.batch_queue.append(feedback)

        # 启动批处理定时器
        if not self.batch_timer.isActive():
            self.batch_timer.start(5000)  # 5秒后处理

    def process_batch(self) -> None:
        """批量处理反馈"""
        if not self.batch_queue:
            self.batch_timer.stop()
            return

        logger.info(f"开始批量处理 {len(self.batch_queue)} 条反馈")

        processed_count = 0
        for feedback in self.batch_queue:
            result = self.process_feedback(feedback)
            if result:
                processed_count += 1

        self.batch_queue.clear()
        self.batch_timer.stop()

        logger.info(f"批量处理完成，成功处理 {processed_count} 条反馈")

    def get_processing_stats(self) -> dict[str, Any]:
        """获取处理统计"""
        return {
            "total_processed": self.processing_stats["total"],
            "auto_resolved": self.processing_stats["auto_resolved"],
            "escalated": self.processing_stats["escalated"],
            "pending": self.processing_stats["pending"],
            "auto_resolution_rate": (
                self.processing_stats["auto_resolved"]
                / self.processing_stats["total"]
                * 100
                if self.processing_stats["total"] > 0
                else 0
            ),
        }

    def _processed_to_dict(self, processed: ProcessedFeedback) -> dict[str, Any]:
        """转换为字典"""
        return {
            "feedback_id": processed.feedback_id,
            "detected_patterns": processed.detected_patterns,
            "auto_category": processed.auto_category,
            "auto_priority": processed.auto_priority,
            "extracted_entities": processed.extracted_entities,
            "sentiment_score": processed.sentiment_score,
            "urgency_score": processed.urgency_score,
            "suggested_response": processed.suggested_response,
            "requires_human_review": processed.requires_human_review,
            "processing_timestamp": processed.processing_timestamp.isoformat(),
        }

    def export_processing_report(self) -> str:
        """导出处理报告"""
        try:
            output_path = (
                self.data_dir
                / f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            report = {
                "generated_at": datetime.now().isoformat(),
                "statistics": self.get_processing_stats(),
                "patterns": {
                    pattern_id: {
                        "name": p.name,
                        "category": p.category,
                        "priority": p.priority,
                    }
                    for pattern_id, p in self.patterns.items()
                },
                "knowledge_base_size": len(self.knowledge_base),
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"处理报告已导出: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"导出处理报告失败: {e}")
            return ""
