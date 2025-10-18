"""
用户反馈分析系统
提供深度的反馈数据分析、可视化和洞察生成
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TrendDirection(str, Enum):
    """趋势方向"""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


class InsightType(str, Enum):
    """洞察类型"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    TREND = "trend"


@dataclass
class FeedbackTrend:
    """反馈趋势"""

    metric_name: str
    current_value: float
    previous_value: float
    change_percentage: float
    direction: TrendDirection
    period: str  # "day", "week", "month"
    data_points: list[tuple[datetime, float]]


@dataclass
class UserSegment:
    """用户细分"""

    segment_id: str
    name: str
    description: str
    user_count: int
    avg_satisfaction: float
    common_feedback_types: list[str]
    key_issues: list[str]
    characteristics: dict[str, Any]


@dataclass
class Insight:
    """数据洞察"""

    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    impact_score: float  # 0-100
    confidence: float  # 0-1
    affected_users: int
    suggested_actions: list[str]
    evidence: list[str]
    created_at: datetime


@dataclass
class NPSAnalysis:
    """NPS（净推荐值）分析"""

    nps_score: float  # -100 到 100
    promoters_count: int  # 推荐者（9-10分）
    passives_count: int  # 中立者（7-8分）
    detractors_count: int  # 贬损者（0-6分）
    promoters_percentage: float
    passives_percentage: float
    detractors_percentage: float
    trend: TrendDirection
    benchmark_comparison: dict[str, float]


class FeedbackAnalytics(QObject):
    """反馈分析系统"""

    # 信号
    insight_generated = Signal(dict)  # 洞察数据
    trend_detected = Signal(str, dict)  # 趋势名称, 趋势数据
    segment_analyzed = Signal(str, dict)  # 细分ID, 细分数据
    nps_updated = Signal(float)  # NPS分数

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 数据存储
        self.feedbacks: list[dict[str, Any]] = []
        self.insights: list[Insight] = []
        self.segments: dict[str, UserSegment] = {}
        self.trends: dict[str, FeedbackTrend] = {}

        # 分析配置
        self.min_sample_size = 30
        self.trend_threshold = 0.15  # 15%变化才认为是趋势
        self.high_impact_threshold = 70

        # 数据路径
        self.data_dir = Path("data/feedback_analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("反馈分析系统初始化完成")

    def load_feedbacks(self, feedbacks: list[dict[str, Any]]) -> None:
        """加载反馈数据"""
        self.feedbacks = feedbacks
        logger.info(f"已加载 {len(feedbacks)} 条反馈")

    def analyze_satisfaction_trends(self, period: str = "week") -> list[FeedbackTrend]:
        """分析满意度趋势"""
        try:
            trends = []

            # 按时间段分组
            periods = self._group_by_period(self.feedbacks, period)

            if len(periods) < 2:
                logger.warning("数据不足，无法分析趋势")
                return []

            # 计算各时间段的平均满意度
            period_scores = []
            for period_start, period_feedbacks in sorted(periods.items()):
                if period_feedbacks:
                    avg_score = sum(f.get("rating", 0) for f in period_feedbacks) / len(period_feedbacks)
                    period_scores.append((period_start, avg_score))

            # 分析趋势
            if len(period_scores) >= 2:
                current_value = period_scores[-1][1]
                previous_value = period_scores[-2][1]
                change = ((current_value - previous_value) / previous_value * 100) if previous_value > 0 else 0

                # 确定趋势方向
                if abs(change) < 5:
                    direction = TrendDirection.STABLE
                elif change > 15:
                    direction = TrendDirection.IMPROVING
                elif change < -15:
                    direction = TrendDirection.DECLINING
                else:
                    # 检查波动性
                    variance = self._calculate_variance([score for _, score in period_scores])
                    direction = TrendDirection.VOLATILE if variance > 1.0 else TrendDirection.STABLE

                trend = FeedbackTrend(
                    metric_name="user_satisfaction",
                    current_value=current_value,
                    previous_value=previous_value,
                    change_percentage=change,
                    direction=direction,
                    period=period,
                    data_points=period_scores,
                )

                trends.append(trend)
                self.trends["user_satisfaction"] = trend

                self.trend_detected.emit("user_satisfaction", {"change": change, "direction": direction.value})

            return trends

        except Exception as e:
            logger.error(f"分析满意度趋势失败: {e}")
            return []

    def _group_by_period(self, feedbacks: list[dict[str, Any]], period: str) -> dict[datetime, list[dict[str, Any]]]:
        """按时间段分组"""
        groups: dict[datetime, list[dict[str, Any]]] = defaultdict(list)

        for feedback in feedbacks:
            timestamp_raw = feedback.get("timestamp")
            if isinstance(timestamp_raw, str):
                timestamp = datetime.fromisoformat(timestamp_raw)
            elif isinstance(timestamp_raw, datetime):
                timestamp = timestamp_raw
            else:
                continue

            if period == "day":
                period_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                period_key = timestamp - timedelta(days=timestamp.weekday())
                period_key = period_key.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "month":
                period_key = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                period_key = timestamp

            groups[period_key].append(feedback)

        return groups

    def _calculate_variance(self, values: list[float]) -> float:
        """计算方差"""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

    def calculate_nps(self, time_range: timedelta | None = None) -> NPSAnalysis:
        """计算NPS分数"""
        try:
            # 筛选时间范围内的反馈
            filtered_feedbacks = self.feedbacks
            if time_range:
                cutoff = datetime.now() - time_range
                filtered_feedbacks = [
                    f
                    for f in self.feedbacks
                    if datetime.fromisoformat(f.get("timestamp", "")) >= cutoff
                    if isinstance(f.get("timestamp"), str)
                ]

            if not filtered_feedbacks:
                logger.warning("没有可用的反馈数据来计算NPS")
                return NPSAnalysis(
                    nps_score=0,
                    promoters_count=0,
                    passives_count=0,
                    detractors_count=0,
                    promoters_percentage=0,
                    passives_percentage=0,
                    detractors_percentage=0,
                    trend=TrendDirection.STABLE,
                    benchmark_comparison={},
                )

            # 分类用户
            promoters = [f for f in filtered_feedbacks if f.get("rating", 0) >= 9]
            passives = [f for f in filtered_feedbacks if 7 <= f.get("rating", 0) <= 8]
            detractors = [f for f in filtered_feedbacks if f.get("rating", 0) <= 6]

            total = len(filtered_feedbacks)
            promoters_pct = len(promoters) / total * 100
            passives_pct = len(passives) / total * 100
            detractors_pct = len(detractors) / total * 100

            # 计算NPS
            nps_score = promoters_pct - detractors_pct

            # 分析趋势
            trend = self._analyze_nps_trend(nps_score)

            # 行业基准对比
            benchmark: dict[str, float] = {
                "industry_average": 30.0,  # 教育行业平均NPS
                "good_score": 50.0,
                "excellent_score": 70.0,
            }

            nps_analysis = NPSAnalysis(
                nps_score=nps_score,
                promoters_count=len(promoters),
                passives_count=len(passives),
                detractors_count=len(detractors),
                promoters_percentage=promoters_pct,
                passives_percentage=passives_pct,
                detractors_percentage=detractors_pct,
                trend=trend,
                benchmark_comparison=benchmark,
            )

            self.nps_updated.emit(nps_score)

            return nps_analysis

        except Exception as e:
            logger.error(f"计算NPS失败: {e}")
            return NPSAnalysis(
                nps_score=0,
                promoters_count=0,
                passives_count=0,
                detractors_count=0,
                promoters_percentage=0,
                passives_percentage=0,
                detractors_percentage=0,
                trend=TrendDirection.STABLE,
                benchmark_comparison={},
            )

    def _analyze_nps_trend(self, current_nps: float) -> TrendDirection:
        """分析NPS趋势"""
        # 这里可以基于历史数据分析趋势
        # 简化实现：基于当前值判断
        if current_nps >= 50:
            return TrendDirection.IMPROVING
        elif current_nps <= 0:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE

    def segment_users(self) -> list[UserSegment]:
        """用户细分分析"""
        try:
            segments = []

            # 按满意度细分
            satisfaction_segments = self._segment_by_satisfaction()
            segments.extend(satisfaction_segments)

            # 按反馈类型细分
            feedback_type_segments = self._segment_by_feedback_type()
            segments.extend(feedback_type_segments)

            # 保存细分结果
            for segment in segments:
                self.segments[segment.segment_id] = segment
                self.segment_analyzed.emit(segment.segment_id, self._segment_to_dict(segment))

            return segments

        except Exception as e:
            logger.error(f"用户细分失败: {e}")
            return []

    def _segment_by_satisfaction(self) -> list[UserSegment]:
        """按满意度细分"""
        segments = []

        # 高满意度用户
        high_satisfaction = [f for f in self.feedbacks if f.get("rating", 0) >= 4]
        if high_satisfaction:
            common_types = self._get_common_feedback_types(high_satisfaction)
            segments.append(
                UserSegment(
                    segment_id="high_satisfaction",
                    name="高满意度用户",
                    description="评分4-5星的用户",
                    user_count=len(high_satisfaction),
                    avg_satisfaction=sum(f.get("rating", 0) for f in high_satisfaction) / len(high_satisfaction),
                    common_feedback_types=common_types,
                    key_issues=[],
                    characteristics={"satisfaction_level": "high"},
                )
            )

        # 低满意度用户
        low_satisfaction = [f for f in self.feedbacks if f.get("rating", 0) <= 2]
        if low_satisfaction:
            common_types = self._get_common_feedback_types(low_satisfaction)
            key_issues = self._extract_key_issues(low_satisfaction)
            segments.append(
                UserSegment(
                    segment_id="low_satisfaction",
                    name="低满意度用户",
                    description="评分1-2星的用户",
                    user_count=len(low_satisfaction),
                    avg_satisfaction=sum(f.get("rating", 0) for f in low_satisfaction) / len(low_satisfaction),
                    common_feedback_types=common_types,
                    key_issues=key_issues,
                    characteristics={"satisfaction_level": "low"},
                )
            )

        return segments

    def _segment_by_feedback_type(self) -> list[UserSegment]:
        """按反馈类型细分"""
        segments = []

        # 按类型分组
        type_groups = defaultdict(list)
        for feedback in self.feedbacks:
            fb_type = feedback.get("feedback_type", "general")
            type_groups[fb_type].append(feedback)

        # 创建细分
        for fb_type, feedbacks in type_groups.items():
            if len(feedbacks) >= self.min_sample_size:
                avg_rating = sum(f.get("rating", 0) for f in feedbacks) / len(feedbacks)
                segments.append(
                    UserSegment(
                        segment_id=f"type_{fb_type}",
                        name=f"{fb_type}反馈用户",
                        description=f"主要提供{fb_type}类型反馈的用户",
                        user_count=len(feedbacks),
                        avg_satisfaction=avg_rating,
                        common_feedback_types=[fb_type],
                        key_issues=self._extract_key_issues(feedbacks),
                        characteristics={"primary_feedback_type": fb_type},
                    )
                )

        return segments

    def _get_common_feedback_types(self, feedbacks: list[dict[str, Any]]) -> list[str]:
        """获取常见反馈类型"""
        types = [f.get("feedback_type", "general") for f in feedbacks]
        counter = Counter(types)
        return [t for t, _ in counter.most_common(3)]

    def _extract_key_issues(self, feedbacks: list[dict[str, Any]]) -> list[str]:
        """提取关键问题"""
        # 分析反馈内容，提取关键词
        issues = []

        # 负面关键词
        negative_keywords = {
            "bug": "系统错误",
            "slow": "性能问题",
            "crash": "崩溃问题",
            "difficult": "使用困难",
            "confusing": "界面混乱",
            "error": "功能错误",
        }

        issue_counts: Counter[str] = Counter()

        for feedback in feedbacks:
            content = feedback.get("content", "").lower()
            for keyword, issue in negative_keywords.items():
                if keyword in content:
                    issue_counts[issue] += 1

        # 返回最常见的问题
        issues = [issue for issue, _ in issue_counts.most_common(5)]

        return issues

    def generate_insights(self) -> list[Insight]:
        """生成数据洞察"""
        try:
            insights: list[Insight] = []
            timestamp = datetime.now()

            # 满意度洞察
            satisfaction_insights = self._generate_satisfaction_insights(timestamp)
            insights.extend(satisfaction_insights)

            # 趋势洞察
            trend_insights = self._generate_trend_insights(timestamp)
            insights.extend(trend_insights)

            # 细分洞察
            segment_insights = self._generate_segment_insights(timestamp)
            insights.extend(segment_insights)

            # 优先级排序
            insights.sort(key=lambda x: x.impact_score, reverse=True)

            # 保存洞察
            self.insights = insights

            # 发送高影响洞察
            for insight in insights:
                if insight.impact_score >= self.high_impact_threshold:
                    self.insight_generated.emit(self._insight_to_dict(insight))

            return insights

        except Exception as e:
            logger.error(f"生成洞察失败: {e}")
            return []

    def _generate_satisfaction_insights(self, timestamp: datetime) -> list[Insight]:
        """生成满意度相关洞察"""
        insights = []

        if len(self.feedbacks) < self.min_sample_size:
            return insights

        # 计算总体满意度
        avg_rating = sum(f.get("rating", 0) for f in self.feedbacks) / len(self.feedbacks)

        # 低满意度警告
        if avg_rating < 3.0:
            low_rating_users = [f for f in self.feedbacks if f.get("rating", 0) <= 2]
            insights.append(
                Insight(
                    insight_id=f"insight_{int(timestamp.timestamp())}",
                    insight_type=InsightType.RISK,
                    title="用户满意度偏低",
                    description=f"平均满意度仅为 {avg_rating:.1f}/5.0，有 {len(low_rating_users)} 位用户给出低分评价",
                    impact_score=85,
                    confidence=0.9,
                    affected_users=len(low_rating_users),
                    suggested_actions=[
                        "立即审查低分用户的具体反馈",
                        "识别并修复最常见的问题",
                        "主动联系不满意用户了解详情",
                        "考虑推出改进计划并告知用户",
                    ],
                    evidence=[f"低分评价数量: {len(low_rating_users)}", f"平均分: {avg_rating:.2f}"],
                    created_at=timestamp,
                )
            )

        # 高满意度机会
        elif avg_rating >= 4.5:
            high_rating_users = [f for f in self.feedbacks if f.get("rating", 0) >= 4]
            insights.append(
                Insight(
                    insight_id=f"insight_{int(timestamp.timestamp())}_pos",
                    insight_type=InsightType.POSITIVE,
                    title="用户满意度优秀",
                    description=f"平均满意度达到 {avg_rating:.1f}/5.0，用户反馈非常积极",
                    impact_score=75,
                    confidence=0.95,
                    affected_users=len(high_rating_users),
                    suggested_actions=[
                        "收集用户成功案例和推荐语",
                        "鼓励满意用户推荐给其他人",
                        "分析高满意度的关键因素并强化",
                        "考虑推出用户推荐奖励计划",
                    ],
                    evidence=[f"高分评价数量: {len(high_rating_users)}", f"平均分: {avg_rating:.2f}"],
                    created_at=timestamp,
                )
            )

        return insights

    def _generate_trend_insights(self, timestamp: datetime) -> list[Insight]:
        """生成趋势相关洞察"""
        insights = []

        for metric_name, trend in self.trends.items():
            if trend.direction == TrendDirection.DECLINING and abs(trend.change_percentage) > 10:
                insights.append(
                    Insight(
                        insight_id=f"insight_trend_{metric_name}",
                        insight_type=InsightType.RISK,
                        title=f"{metric_name}呈下降趋势",
                        description=f"{metric_name}在过去{trend.period}下降了{abs(trend.change_percentage):.1f}%",
                        impact_score=80,
                        confidence=0.85,
                        affected_users=len(self.feedbacks),
                        suggested_actions=[
                            f"分析{metric_name}下降的根本原因",
                            "检查最近的产品变更是否导致问题",
                            "与用户沟通了解具体不满",
                        ],
                        evidence=[f"变化: {trend.change_percentage:.1f}%", f"期间: {trend.period}"],
                        created_at=timestamp,
                    )
                )

        return insights

    def _generate_segment_insights(self, timestamp: datetime) -> list[Insight]:
        """生成细分相关洞察"""
        insights = []

        # 分析低满意度细分
        if "low_satisfaction" in self.segments:
            segment = self.segments["low_satisfaction"]
            if segment.user_count >= self.min_sample_size:
                insights.append(
                    Insight(
                        insight_id="insight_segment_low_sat",
                        insight_type=InsightType.OPPORTUNITY,
                        title="低满意度用户群体需要关注",
                        description=f"有{segment.user_count}位低满意度用户，平均分仅{segment.avg_satisfaction:.1f}",
                        impact_score=75,
                        confidence=0.9,
                        affected_users=segment.user_count,
                        suggested_actions=[
                            f"优先解决: {', '.join(segment.key_issues[:3]) if segment.key_issues else '用户核心痛点'}",
                            "为这部分用户提供专门的支持",
                            "考虑针对性的产品改进",
                        ],
                        evidence=[f"用户数: {segment.user_count}", f"关键问题: {', '.join(segment.key_issues[:2])}"],
                        created_at=timestamp,
                    )
                )

        return insights

    def _insight_to_dict(self, insight: Insight) -> dict[str, Any]:
        """转换洞察为字典"""
        return {
            "insight_id": insight.insight_id,
            "insight_type": insight.insight_type.value,
            "title": insight.title,
            "description": insight.description,
            "impact_score": insight.impact_score,
            "confidence": insight.confidence,
            "affected_users": insight.affected_users,
            "suggested_actions": insight.suggested_actions,
            "evidence": insight.evidence,
            "created_at": insight.created_at.isoformat(),
        }

    def _segment_to_dict(self, segment: UserSegment) -> dict[str, Any]:
        """转换细分为字典"""
        return {
            "segment_id": segment.segment_id,
            "name": segment.name,
            "description": segment.description,
            "user_count": segment.user_count,
            "avg_satisfaction": segment.avg_satisfaction,
            "common_feedback_types": segment.common_feedback_types,
            "key_issues": segment.key_issues,
            "characteristics": segment.characteristics,
        }

    def export_analytics_report(self, output_path: str | None = None) -> str:
        """导出分析报告"""
        try:
            if not output_path:
                output_file = self.data_dir / f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                output_file = Path(output_path)

            # NPS分析
            nps = self.calculate_nps()

            # 趋势分析
            trends = self.analyze_satisfaction_trends()

            # 细分分析
            segments = self.segment_users()

            # 洞察生成
            insights = self.generate_insights()

            report = {
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_feedbacks": len(self.feedbacks),
                    "nps_score": nps.nps_score,
                    "avg_satisfaction": (
                        sum(f.get("rating", 0) for f in self.feedbacks) / len(self.feedbacks) if self.feedbacks else 0
                    ),
                },
                "nps_analysis": {
                    "score": nps.nps_score,
                    "promoters": nps.promoters_count,
                    "passives": nps.passives_count,
                    "detractors": nps.detractors_count,
                    "benchmark_comparison": nps.benchmark_comparison,
                },
                "trends": [
                    {
                        "metric": t.metric_name,
                        "change": t.change_percentage,
                        "direction": t.direction.value,
                        "current_value": t.current_value,
                    }
                    for t in trends
                ],
                "segments": [self._segment_to_dict(s) for s in segments],
                "insights": [self._insight_to_dict(i) for i in insights],
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"分析报告已导出到: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"导出分析报告失败: {e}")
            return ""
