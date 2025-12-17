"""
产品迭代管理系统
基于用户反馈驱动产品快速迭代和优化
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class IterationStatus(str, Enum):
    """迭代状态"""

    PLANNING = "planning"  # 规划中
    IN_PROGRESS = "in_progress"  # 进行中
    TESTING = "testing"  # 测试中
    RELEASED = "released"  # 已发布
    CANCELLED = "cancelled"  # 已取消


class FeatureStatus(str, Enum):
    """功能状态"""

    PROPOSED = "proposed"  # 提议
    APPROVED = "approved"  # 已批准
    IN_DEVELOPMENT = "in_development"  # 开发中
    IN_TESTING = "in_testing"  # 测试中
    DEPLOYED = "deployed"  # 已部署
    REJECTED = "rejected"  # 已拒绝


class ImpactLevel(str, Enum):
    """影响等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FeatureRequest:
    """功能需求"""

    request_id: str
    title: str
    description: str
    source: str  # "user_feedback", "analytics", "team", "competitor"
    priority: int  # 1-100
    impact_level: ImpactLevel
    effort_estimate: int  # 工作日
    user_votes: int = 0
    feedback_count: int = 0
    status: FeatureStatus = FeatureStatus.PROPOSED
    assigned_to: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    target_iteration: str | None = None
    related_feedbacks: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class BugFix:
    """Bug修复"""

    bug_id: str
    title: str
    description: str
    severity: str  # "critical", "major", "minor", "trivial"
    affected_users: int
    reproduction_steps: list[str]
    fix_description: str = ""
    status: str = "open"  # "open", "in_progress", "fixed", "verified", "closed"
    assigned_to: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    fixed_at: datetime | None = None
    related_feedbacks: list[str] = field(default_factory=list)


@dataclass
class Improvement:
    """改进项"""

    improvement_id: str
    title: str
    description: str
    category: str  # "performance", "ux", "ui", "accessibility", "security"
    expected_impact: str
    implementation_notes: str = ""
    status: str = "proposed"
    priority: int = 50
    created_at: datetime = field(default_factory=datetime.now)
    related_feedbacks: list[str] = field(default_factory=list)


@dataclass
class ProductIteration:
    """产品迭代"""

    iteration_id: str
    version: str
    name: str
    description: str
    status: IterationStatus
    start_date: datetime
    end_date: datetime
    feature_requests: list[str] = field(default_factory=list)
    bug_fixes: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    success_metrics: dict[str, Any] = field(default_factory=dict)
    actual_metrics: dict[str, Any] = field(default_factory=dict)
    feedback_driven_changes: int = 0
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class IterationManager(QObject):
    """迭代管理器"""

    # 信号
    feature_proposed = Signal(str)  # 功能ID
    feature_approved = Signal(str)  # 功能ID
    bug_reported = Signal(str)  # Bug ID
    iteration_planned = Signal(str)  # 迭代ID
    iteration_completed = Signal(str, dict)  # 迭代ID, 结果
    priority_changed = Signal(str, int, int)  # 项ID, 旧优先级, 新优先级

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 数据存储
        self.feature_requests: dict[str, FeatureRequest] = {}
        self.bug_fixes: dict[str, BugFix] = {}
        self.improvements: dict[str, Improvement] = {}
        self.iterations: dict[str, ProductIteration] = {}

        # 反馈映射（反馈ID -> 功能/Bug ID）
        self.feedback_to_items: dict[str, list[str]] = defaultdict(list)

        # 优先级权重配置
        self.priority_weights = {
            "user_votes": 0.3,
            "feedback_count": 0.25,
            "impact_level": 0.25,
            "urgency": 0.2,
        }

        # 数据路径
        self.data_dir = Path("data/product_iteration")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.load_data()

        logger.info("产品迭代管理器初始化完成")

    def propose_feature_from_feedback(self, feedbacks: list[dict[str, Any]]) -> str:
        """从反馈中提议功能"""
        try:
            # 分析反馈，提取共同需求
            common_requests = self._analyze_common_requests(feedbacks)

            if not common_requests:
                logger.warning("未发现共同的功能需求")
                return ""

            # 创建功能需求
            feature_id = f"feat_{int(datetime.now().timestamp() * 1000)}"

            # 获取最常见的需求
            top_request = common_requests[0]

            feature = FeatureRequest(
                request_id=feature_id,
                title=top_request["title"],
                description=top_request["description"],
                source="user_feedback",
                priority=self._calculate_priority(
                    len(feedbacks), top_request.get("urgency", 50)
                ),
                impact_level=self._determine_impact_level(len(feedbacks)),
                effort_estimate=self._estimate_effort(
                    top_request["title"], top_request["description"]
                ),
                user_votes=len(feedbacks),
                feedback_count=len(feedbacks),
                related_feedbacks=[f.get("feedback_id", "") for f in feedbacks],
            )

            self.feature_requests[feature_id] = feature

            # 建立反馈映射
            for feedback in feedbacks:
                feedback_id = feedback.get("feedback_id", "")
                if feedback_id:
                    self.feedback_to_items[feedback_id].append(feature_id)

            self.save_feature(feature)
            self.feature_proposed.emit(feature_id)

            logger.info(
                f"从 {len(feedbacks)} 条反馈中提议功能: {feature_id} - {feature.title}"
            )

            return feature_id

        except Exception as e:
            logger.error(f"从反馈提议功能失败: {e}")
            return ""

    def _analyze_common_requests(
        self, feedbacks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """分析共同需求"""
        # 简化实现：基于关键词聚类
        keyword_clusters = defaultdict(list)

        for feedback in feedbacks:
            content = feedback.get("content", "").lower()
            title = feedback.get("title", "").lower()

            # 提取关键词
            keywords = self._extract_keywords(content + " " + title)

            for keyword in keywords:
                keyword_clusters[keyword].append(feedback)

        # 找到最大的集群
        if not keyword_clusters:
            return []

        largest_cluster = max(keyword_clusters.items(), key=lambda x: len(x[1]))
        keyword, cluster_feedbacks = largest_cluster

        # 生成需求描述
        request = {
            "title": f"增强{keyword}功能",
            "description": self._generate_description(cluster_feedbacks),
            "urgency": (
                sum(f.get("urgency_score", 50) for f in cluster_feedbacks)
                / len(cluster_feedbacks)
                if cluster_feedbacks
                else 50
            ),
        }

        return [request]

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词"""
        # 功能相关关键词
        feature_keywords = [
            "导出",
            "导入",
            "分享",
            "协作",
            "实验",
            "报告",
            "图表",
            "数据",
            "分析",
            "搜索",
            "过滤",
            "排序",
            "自定义",
            "模板",
            "快捷键",
            "批量",
            "自动",
        ]

        found_keywords = []
        for keyword in feature_keywords:
            if keyword in text:
                found_keywords.append(keyword)

        return found_keywords

    def _generate_description(self, feedbacks: list[dict[str, Any]]) -> str:
        """生成需求描述"""
        # 汇总用户诉求
        descriptions = [f.get("content", "") for f in feedbacks[:5]]  # 取前5条
        combined = " ".join(descriptions)

        # 简化版：返回摘要
        return f"基于用户反馈，用户希望: {combined[:200]}..."

    def _calculate_priority(self, user_count: int, urgency: float) -> int:
        """计算优先级"""
        # 综合用户数和紧急度
        user_score = min(user_count * 5, 50)  # 最多50分
        urgency_score = urgency / 2  # 最多50分

        return int(user_score + urgency_score)

    def _determine_impact_level(self, user_count: int) -> ImpactLevel:
        """确定影响等级"""
        if user_count >= 100:
            return ImpactLevel.CRITICAL
        elif user_count >= 50:
            return ImpactLevel.HIGH
        elif user_count >= 20:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW

    def _estimate_effort(self, title: str, description: str) -> int:
        """估算工作量（工作日）"""
        # 简化实现：基于复杂度关键词
        complex_keywords = ["集成", "重构", "架构", "算法", "优化", "迁移"]
        medium_keywords = ["增强", "改进", "扩展", "支持"]

        text = (title + " " + description).lower()

        if any(keyword in text for keyword in complex_keywords):
            return 10  # 复杂任务
        elif any(keyword in text for keyword in medium_keywords):
            return 5  # 中等任务
        else:
            return 2  # 简单任务

    def report_bug_from_feedback(self, feedback: dict[str, Any]) -> str:
        """从反馈报告Bug"""
        try:
            bug_id = f"bug_{int(datetime.now().timestamp() * 1000)}"

            bug = BugFix(
                bug_id=bug_id,
                title=feedback.get("title", ""),
                description=feedback.get("content", ""),
                severity=self._determine_severity(feedback),
                affected_users=1,  # 初始值
                reproduction_steps=self._extract_reproduction_steps(
                    feedback.get("content", "")
                ),
                related_feedbacks=[feedback.get("feedback_id", "")],
            )

            self.bug_fixes[bug_id] = bug

            # 建立反馈映射
            feedback_id = feedback.get("feedback_id", "")
            if feedback_id:
                self.feedback_to_items[feedback_id].append(bug_id)

            self.save_bug(bug)
            self.bug_reported.emit(bug_id)

            logger.info(f"报告Bug: {bug_id} - {bug.title}")

            return bug_id

        except Exception as e:
            logger.error(f"报告Bug失败: {e}")
            return ""

    def _determine_severity(self, feedback: dict[str, Any]) -> str:
        """确定Bug严重程度"""
        priority = feedback.get("priority", "medium")
        rating = feedback.get("rating", 3)

        if priority == "critical" or rating <= 1:
            return "critical"
        elif priority == "high" or rating == 2:
            return "major"
        elif priority == "medium":
            return "minor"
        else:
            return "trivial"

    def _extract_reproduction_steps(self, content: str) -> list[str]:
        """提取复现步骤"""
        # 简化实现：查找步骤相关的描述
        steps = []

        # 查找编号列表
        import re

        numbered_steps = re.findall(
            r"(?:第?\s*\d+\s*[、.)]|步骤\s*\d+[:：])\s*([^。\n]+)", content
        )
        if numbered_steps:
            steps = numbered_steps

        if not steps:
            # 没有明确步骤，使用整体描述
            steps = [content[:100]]

        return steps[:5]  # 最多5步

    def create_improvement_from_insights(
        self, insights: list[dict[str, Any]]
    ) -> list[str]:
        """从洞察创建改进项"""
        improvement_ids = []

        try:
            for insight in insights:
                if insight.get("insight_type") in ["opportunity", "negative"]:
                    improvement_id = f"imp_{int(datetime.now().timestamp() * 1000)}"

                    # 确定类别
                    category = self._categorize_improvement(insight)

                    improvement = Improvement(
                        improvement_id=improvement_id,
                        title=insight.get("title", ""),
                        description=insight.get("description", ""),
                        category=category,
                        expected_impact=insight.get("impact_score", 0),
                        priority=int(insight.get("impact_score", 50)),
                        related_feedbacks=insight.get("evidence", []),
                    )

                    self.improvements[improvement_id] = improvement
                    improvement_ids.append(improvement_id)

                    self.save_improvement(improvement)

                    logger.info(f"创建改进项: {improvement_id} - {improvement.title}")

            return improvement_ids

        except Exception as e:
            logger.error(f"创建改进项失败: {e}")
            return []

    def _categorize_improvement(self, insight: dict[str, Any]) -> str:
        """分类改进项"""
        title = insight.get("title", "").lower()
        description = insight.get("description", "").lower()

        text = title + " " + description

        if any(word in text for word in ["性能", "速度", "慢", "卡", "performance"]):
            return "performance"
        elif any(word in text for word in ["界面", "ui", "布局", "设计"]):
            return "ui"
        elif any(word in text for word in ["体验", "交互", "操作", "流程", "ux"]):
            return "ux"
        elif any(word in text for word in ["无障碍", "accessibility", "可访问"]):
            return "accessibility"
        elif any(word in text for word in ["安全", "security", "隐私"]):
            return "security"
        else:
            return "general"

    def plan_iteration(
        self,
        version: str,
        name: str,
        duration_weeks: int = 2,
        goals: list[str] | None = None,
    ) -> str:
        """规划迭代"""
        try:
            iteration_id = f"iter_{int(datetime.now().timestamp() * 1000)}"

            iteration = ProductIteration(
                iteration_id=iteration_id,
                version=version,
                name=name,
                description=f"{name} - 版本 {version}",
                status=IterationStatus.PLANNING,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(weeks=duration_weeks),
                goals=goals or [],
            )

            # 自动选择高优先级项目
            self._auto_select_items(iteration)

            self.iterations[iteration_id] = iteration
            self.save_iteration(iteration)

            self.iteration_planned.emit(iteration_id)

            logger.info(f"规划迭代: {iteration_id} - {name}")

            return iteration_id

        except Exception as e:
            logger.error(f"规划迭代失败: {e}")
            return ""

    def _auto_select_items(self, iteration: ProductIteration) -> None:
        """自动选择迭代项目"""
        # 选择高优先级功能
        sorted_features = sorted(
            self.feature_requests.values(), key=lambda f: f.priority, reverse=True
        )

        total_effort = 0
        capacity = 40  # 假设2周40个工作日

        for feature in sorted_features:
            if (
                feature.status == FeatureStatus.APPROVED
                and total_effort + feature.effort_estimate <= capacity
            ):
                iteration.feature_requests.append(feature.request_id)
                total_effort += feature.effort_estimate

                if feature.related_feedbacks:
                    iteration.feedback_driven_changes += 1

        # 选择关键Bug
        critical_bugs = [
            b
            for b in self.bug_fixes.values()
            if b.severity == "critical" and b.status == "open"
        ]
        for bug in critical_bugs[:5]:  # 最多5个关键Bug
            iteration.bug_fixes.append(bug.bug_id)

            if bug.related_feedbacks:
                iteration.feedback_driven_changes += 1

        # 选择高优先级改进
        sorted_improvements = sorted(
            self.improvements.values(), key=lambda i: i.priority, reverse=True
        )
        for improvement in sorted_improvements[:10]:  # 最多10个改进
            if improvement.status == "proposed":
                iteration.improvements.append(improvement.improvement_id)

                if improvement.related_feedbacks:
                    iteration.feedback_driven_changes += 1

        logger.info(
            f"迭代自动选择: {len(iteration.feature_requests)} 功能, "
            f"{len(iteration.bug_fixes)} Bug, {len(iteration.improvements)} 改进"
        )

    def update_priority_from_feedback(
        self, item_id: str, new_feedback_count: int, new_votes: int
    ) -> bool:
        """根据反馈更新优先级"""
        try:
            if item_id in self.feature_requests:
                feature = self.feature_requests[item_id]
                old_priority = feature.priority

                feature.feedback_count = new_feedback_count
                feature.user_votes = new_votes

                # 重新计算优先级
                feature.priority = self._recalculate_feature_priority(feature)

                self.save_feature(feature)
                self.priority_changed.emit(item_id, old_priority, feature.priority)

                logger.info(
                    f"功能 {item_id} 优先级从 {old_priority} 更新为 {feature.priority}"
                )

                return True

            return False

        except Exception as e:
            logger.error(f"更新优先级失败: {e}")
            return False

    def _recalculate_feature_priority(self, feature: FeatureRequest) -> int:
        """重新计算功能优先级"""
        # 用户投票得分
        vote_score = min(feature.user_votes * 2, 30)

        # 反馈数量得分
        feedback_score = min(feature.feedback_count * 1.5, 25)

        # 影响等级得分
        impact_scores = {"low": 10, "medium": 20, "high": 30, "critical": 40}
        impact_score = impact_scores.get(feature.impact_level.value, 10)

        # 时间因素（新功能优先级略高）
        age_days = (datetime.now() - feature.created_at).days
        urgency_score = max(5, 15 - age_days * 0.5)  # 随时间降低

        total = int(vote_score + feedback_score + impact_score + urgency_score)

        return min(100, max(1, total))

    def complete_iteration(
        self, iteration_id: str, actual_metrics: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """完成迭代"""
        try:
            if iteration_id not in self.iterations:
                return {}

            iteration = self.iterations[iteration_id]
            iteration.status = IterationStatus.RELEASED
            iteration.actual_metrics = actual_metrics or {}

            # 计算迭代成果
            results = {
                "iteration_id": iteration_id,
                "version": iteration.version,
                "name": iteration.name,
                "features_delivered": len(iteration.feature_requests),
                "bugs_fixed": len(iteration.bug_fixes),
                "improvements_made": len(iteration.improvements),
                "feedback_driven_changes": iteration.feedback_driven_changes,
                "duration_days": (iteration.end_date - iteration.start_date).days,
                "success_metrics": iteration.success_metrics,
                "actual_metrics": iteration.actual_metrics,
            }

            self.save_iteration(iteration)
            self.iteration_completed.emit(iteration_id, results)

            logger.info(f"迭代完成: {iteration_id} - {iteration.name}")

            return results

        except Exception as e:
            logger.error(f"完成迭代失败: {e}")
            return {}

    def get_roadmap(self, months: int = 6) -> dict[str, Any]:
        """获取产品路线图"""
        try:
            roadmap = {
                "timeframe": f"{months}个月",
                "planned_iterations": [],
                "top_features": [],
                "key_improvements": [],
            }

            # 获取已规划的迭代
            planned_iters = [
                i
                for i in self.iterations.values()
                if i.status in [IterationStatus.PLANNING, IterationStatus.IN_PROGRESS]
            ]

            planned_iterations_list: list[dict[str, Any]] = [
                {
                    "version": i.version,
                    "name": i.name,
                    "start_date": i.start_date.isoformat(),
                    "end_date": i.end_date.isoformat(),
                    "feature_count": len(i.feature_requests),
                }
                for i in sorted(planned_iters, key=lambda x: x.start_date)
            ]
            roadmap["planned_iterations"] = planned_iterations_list

            # 获取高优先级功能
            top_features = sorted(
                [
                    f
                    for f in self.feature_requests.values()
                    if f.status in [FeatureStatus.PROPOSED, FeatureStatus.APPROVED]
                ],
                key=lambda f: f.priority,
                reverse=True,
            )[:10]

            top_features_list: list[dict[str, Any]] = [
                {
                    "title": f.title,
                    "priority": f.priority,
                    "user_votes": f.user_votes,
                    "impact": f.impact_level.value,
                    "status": f.status.value,
                }
                for f in top_features
            ]
            roadmap["top_features"] = top_features_list

            # 关键改进
            key_improvements = sorted(
                self.improvements.values(), key=lambda i: i.priority, reverse=True
            )[:10]

            key_improvements_list: list[dict[str, Any]] = [
                {
                    "title": i.title,
                    "category": i.category,
                    "priority": i.priority,
                    "status": i.status,
                }
                for i in key_improvements
            ]
            roadmap["key_improvements"] = key_improvements_list

            return roadmap

        except Exception as e:
            logger.error(f"获取路线图失败: {e}")
            return {}

    def save_feature(self, feature: FeatureRequest) -> None:
        """保存功能需求"""
        try:
            file_path = self.data_dir / "features" / f"{feature.request_id}.json"
            file_path.parent.mkdir(exist_ok=True)

            data = {
                "request_id": feature.request_id,
                "title": feature.title,
                "description": feature.description,
                "source": feature.source,
                "priority": feature.priority,
                "impact_level": feature.impact_level.value,
                "effort_estimate": feature.effort_estimate,
                "user_votes": feature.user_votes,
                "feedback_count": feature.feedback_count,
                "status": feature.status.value,
                "assigned_to": feature.assigned_to,
                "created_at": feature.created_at.isoformat(),
                "updated_at": feature.updated_at.isoformat(),
                "target_iteration": feature.target_iteration,
                "related_feedbacks": feature.related_feedbacks,
                "metrics": feature.metrics,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"保存功能需求失败: {e}")

    def save_bug(self, bug: BugFix) -> None:
        """保存Bug"""
        try:
            file_path = self.data_dir / "bugs" / f"{bug.bug_id}.json"
            file_path.parent.mkdir(exist_ok=True)

            data = {
                "bug_id": bug.bug_id,
                "title": bug.title,
                "description": bug.description,
                "severity": bug.severity,
                "affected_users": bug.affected_users,
                "reproduction_steps": bug.reproduction_steps,
                "fix_description": bug.fix_description,
                "status": bug.status,
                "assigned_to": bug.assigned_to,
                "created_at": bug.created_at.isoformat(),
                "fixed_at": bug.fixed_at.isoformat() if bug.fixed_at else None,
                "related_feedbacks": bug.related_feedbacks,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"保存Bug失败: {e}")

    def save_improvement(self, improvement: Improvement) -> None:
        """保存改进项"""
        try:
            file_path = (
                self.data_dir / "improvements" / f"{improvement.improvement_id}.json"
            )
            file_path.parent.mkdir(exist_ok=True)

            data = {
                "improvement_id": improvement.improvement_id,
                "title": improvement.title,
                "description": improvement.description,
                "category": improvement.category,
                "expected_impact": improvement.expected_impact,
                "implementation_notes": improvement.implementation_notes,
                "status": improvement.status,
                "priority": improvement.priority,
                "created_at": improvement.created_at.isoformat(),
                "related_feedbacks": improvement.related_feedbacks,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"保存改进项失败: {e}")

    def save_iteration(self, iteration: ProductIteration) -> None:
        """保存迭代"""
        try:
            file_path = self.data_dir / "iterations" / f"{iteration.iteration_id}.json"
            file_path.parent.mkdir(exist_ok=True)

            data = {
                "iteration_id": iteration.iteration_id,
                "version": iteration.version,
                "name": iteration.name,
                "description": iteration.description,
                "status": iteration.status.value,
                "start_date": iteration.start_date.isoformat(),
                "end_date": iteration.end_date.isoformat(),
                "feature_requests": iteration.feature_requests,
                "bug_fixes": iteration.bug_fixes,
                "improvements": iteration.improvements,
                "goals": iteration.goals,
                "success_metrics": iteration.success_metrics,
                "actual_metrics": iteration.actual_metrics,
                "feedback_driven_changes": iteration.feedback_driven_changes,
                "created_by": iteration.created_by,
                "created_at": iteration.created_at.isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"保存迭代失败: {e}")

    def load_data(self) -> None:
        """加载数据"""
        try:
            # 加载功能需求
            features_dir = self.data_dir / "features"
            if features_dir.exists():
                for file_path in features_dir.glob("*.json"):
                    with open(file_path, encoding="utf-8") as f:
                        _ = json.load(f)
                        # 重建对象...
                        # 简化实现，仅记录日志
                        pass

            logger.info("数据加载完成")

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
