"""
反馈集成层
连接反馈系统、A/B测试、分析系统和产品迭代管理
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..analytics.feedback_analytics import FeedbackAnalytics
from ..analytics.feedback_processor import FeedbackProcessor
from ..product.iteration_manager import IterationManager
from ..testing.ab_testing_framework import ABTestingFramework
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackIntegration(QObject):
    """反馈集成系统"""

    # 信号
    workflow_triggered = Signal(str, dict)  # 工作流类型, 数据
    action_completed = Signal(str, str)  # 动作类型, 结果
    integration_error = Signal(str)  # 错误消息

    def __init__(
        self,
        feedback_processor: FeedbackProcessor | None = None,
        analytics: FeedbackAnalytics | None = None,
        ab_testing: ABTestingFramework | None = None,
        iteration_manager: IterationManager | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)

        # 初始化组件
        self.feedback_processor = feedback_processor or FeedbackProcessor()
        self.analytics = analytics or FeedbackAnalytics()
        self.ab_testing = ab_testing or ABTestingFramework()
        self.iteration_manager = iteration_manager or IterationManager()

        # 工作流配置
        self.workflows = {
            "feedback_to_feature": True,  # 反馈 -> 功能需求
            "feedback_to_bug": True,  # 反馈 -> Bug报告
            "insight_to_improvement": True,  # 洞察 -> 改进项
            "insight_to_ab_test": True,  # 洞察 -> A/B测试
            "ab_result_to_iteration": True,  # A/B测试结果 -> 迭代
        }

        # 自动化规则
        self.automation_rules = {
            "auto_create_feature": {
                "enabled": True,
                "min_feedback_count": 5,
                "min_user_votes": 10,
            },
            "auto_report_bug": {"enabled": True, "critical_priority_only": True},
            "auto_create_ab_test": {"enabled": True, "min_impact_score": 70},
            "auto_add_to_iteration": {"enabled": True, "auto_approve_threshold": 80},
        }

        # 数据同步
        self.sync_interval = 60000  # 60秒
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_data)
        self.sync_timer.start(self.sync_interval)

        # 连接信号
        self.connect_signals()

        # 数据路径
        self.data_dir = Path("data/integration")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("反馈集成系统初始化完成")

    def connect_signals(self) -> None:
        """连接组件信号"""
        # 反馈处理器信号
        self.feedback_processor.feedback_processed.connect(self.on_feedback_processed)
        self.feedback_processor.escalation_required.connect(self.on_escalation_required)

        # 分析系统信号
        self.analytics.insight_generated.connect(self.on_insight_generated)
        self.analytics.nps_updated.connect(self.on_nps_updated)

        # A/B测试信号
        self.ab_testing.experiment_completed.connect(self.on_experiment_completed)

        # 迭代管理器信号
        self.iteration_manager.feature_proposed.connect(self.on_feature_proposed)

    def process_feedback_workflow(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """处理反馈工作流"""
        try:
            workflow_results = {
                "feedback_id": feedback.get("feedback_id", ""),
                "actions": [],
            }

            # 1. 自动处理反馈
            processed = self.feedback_processor.process_feedback(feedback)

            if not processed:
                return workflow_results

            workflow_results["processed"] = True
            workflow_results["category"] = processed.auto_category
            workflow_results["priority"] = processed.auto_priority

            # 2. 根据类型触发不同工作流
            if processed.auto_category == "bug_report" and self.workflows.get(
                "feedback_to_bug"
            ):
                bug_id = self.create_bug_from_feedback(feedback, processed)
                if bug_id:
                    workflow_results["actions"].append(
                        {"type": "bug_created", "id": bug_id}
                    )

            elif processed.auto_category == "feature_request" and self.workflows.get(
                "feedback_to_feature"
            ):
                # 累积相似反馈后再创建功能需求
                similar_feedbacks = self.find_similar_feedbacks(feedback)
                min_feedback = self.automation_rules.get("auto_create_feature", {}).get(
                    "min_feedback_count", 5
                )
                if len(similar_feedbacks) >= min_feedback:
                    feature_id = self.iteration_manager.propose_feature_from_feedback(
                        similar_feedbacks
                    )
                    if feature_id:
                        workflow_results["actions"].append(
                            {"type": "feature_proposed", "id": feature_id}
                        )

            # 3. 检查是否需要A/B测试
            min_impact = self.automation_rules.get("auto_create_ab_test", {}).get(
                "min_impact_score", 70
            )
            if processed.urgency_score >= min_impact and self.workflows.get(
                "insight_to_ab_test"
            ):
                ab_experiment_id = self.create_ab_test_from_feedback(
                    feedback, processed
                )
                if ab_experiment_id:
                    workflow_results["actions"].append(
                        {"type": "ab_test_created", "id": ab_experiment_id}
                    )

            self.workflow_triggered.emit("feedback_processing", workflow_results)

            return workflow_results

        except Exception as e:
            logger.error(f"处理反馈工作流失败: {e}")
            self.integration_error.emit(str(e))
            return {}

    def create_bug_from_feedback(self, feedback: dict[str, Any], processed: Any) -> str:
        """从反馈创建Bug"""
        try:
            # 检查是否自动报告Bug
            auto_bug_config = self.automation_rules.get("auto_report_bug", {})
            if not auto_bug_config.get("enabled", False):
                return ""

            # 检查优先级
            if auto_bug_config.get("critical_priority_only", False):
                if getattr(processed, "auto_priority", "") != "critical":
                    return ""

            bug_id = self.iteration_manager.report_bug_from_feedback(feedback)

            if bug_id:
                logger.info(f"从反馈创建Bug: {bug_id}")
                self.action_completed.emit("bug_created", bug_id)

            return bug_id

        except Exception as e:
            logger.error(f"从反馈创建Bug失败: {e}")
            return ""

    def find_similar_feedbacks(self, feedback: dict[str, Any]) -> list[dict[str, Any]]:
        """查找相似反馈"""
        # 简化实现：基于关键词相似度
        similar = [feedback]  # 包含自己

        content = feedback.get("content", "").lower()
        keywords = set(content.split())

        for other_feedback in self.analytics.feedbacks:
            if other_feedback.get("feedback_id") == feedback.get("feedback_id"):
                continue

            other_content = other_feedback.get("content", "").lower()
            other_keywords = set(other_content.split())

            # 计算Jaccard相似度
            intersection = keywords & other_keywords
            union = keywords | other_keywords

            if union and len(intersection) / len(union) > 0.3:  # 30%相似度
                similar.append(other_feedback)

        return similar

    def create_ab_test_from_feedback(
        self, feedback: dict[str, Any], processed: Any
    ) -> str:
        """从反馈创建A/B测试"""
        try:
            ab_test_config = self.automation_rules.get("auto_create_ab_test", {})
            if not ab_test_config.get("enabled", False):
                return ""

            # 检查是否值得测试
            min_score = ab_test_config.get("min_impact_score", 70)
            if getattr(processed, "urgency_score", 0) < min_score:
                return ""

            # 创建测试假设
            hypothesis = f"优化{feedback.get('title', '')}可以提升用户满意度"

            # 定义变体
            variants = [
                {
                    "name": "对照组",
                    "type": "control",
                    "description": "当前版本",
                    "config": {},
                    "traffic_allocation": 0.5,
                },
                {
                    "name": "优化版",
                    "type": "treatment",
                    "description": "根据反馈优化的版本",
                    "config": {"feedback_id": feedback.get("feedback_id")},
                    "traffic_allocation": 0.5,
                },
            ]

            # 成功标准
            success_criteria = {"satisfaction_improvement": 0.1, "min_sample_size": 100}

            # 创建实验
            from ..testing.ab_testing_framework import ExperimentType

            experiment_id = self.ab_testing.create_experiment(
                name=f"反馈优化测试: {feedback.get('title', '')}",
                experiment_type=ExperimentType.FEATURE,
                description="基于用户反馈的优化测试",
                hypothesis=hypothesis,
                variants=variants,
                success_criteria=success_criteria,
                target_audience={"user_id_range": [0, 50]},  # 50%用户
                created_by="feedback_integration",
            )

            if experiment_id:
                logger.info(f"从反馈创建A/B测试: {experiment_id}")
                self.action_completed.emit("ab_test_created", experiment_id)

            return experiment_id

        except Exception as e:
            logger.error(f"从反馈创建A/B测试失败: {e}")
            return ""

    def on_feedback_processed(
        self, feedback_id: str, processed_data: dict[str, Any]
    ) -> None:
        """反馈处理完成"""
        logger.info(
            f"反馈已处理: {feedback_id}, 类别: {processed_data.get('auto_category')}"
        )

        # 触发工作流
        if processed_data.get("requires_human_review"):
            self.workflow_triggered.emit(
                "human_review_required",
                {"feedback_id": feedback_id, "reason": "需要人工审核"},
            )

    def on_escalation_required(self, feedback_id: str, details: dict[str, Any]) -> None:
        """需要升级处理"""
        logger.warning(
            f"反馈需要升级处理: {feedback_id}, 原因: {details.get('reason')}"
        )

        self.workflow_triggered.emit(
            "escalation",
            {
                "feedback_id": feedback_id,
                "priority": details.get("priority"),
                "urgency": details.get("urgency"),
            },
        )

    def on_insight_generated(self, insight: dict[str, Any]) -> None:
        """洞察生成"""
        logger.info(f"生成洞察: {insight.get('title')}")

        # 创建改进项
        if self.workflows.get("insight_to_improvement"):
            improvement_ids = self.iteration_manager.create_improvement_from_insights(
                [insight]
            )

            if improvement_ids:
                self.action_completed.emit(
                    "improvements_created", ",".join(improvement_ids)
                )

        # 创建A/B测试
        if (
            self.workflows.get("insight_to_ab_test")
            and insight.get("impact_score", 0) >= 70
        ):
            self.create_ab_test_from_insight(insight)

    def create_ab_test_from_insight(self, insight: dict[str, Any]) -> str:
        """从洞察创建A/B测试"""
        try:
            # 根据洞察类型确定测试类型
            from ..testing.ab_testing_framework import ExperimentType

            type_map = {
                "opportunity": ExperimentType.FEATURE,
                "negative": ExperimentType.UI_DESIGN,
                "trend": ExperimentType.WORKFLOW,
            }

            exp_type = type_map.get(insight.get("insight_type"), ExperimentType.FEATURE)

            # 创建变体
            suggested_action = insight.get("suggested_actions", ["优化实现"])
            action_text = (
                suggested_action[0]
                if isinstance(suggested_action, list) and suggested_action
                else "优化实现"
            )

            variants = [
                {
                    "name": "当前版本",
                    "type": "control",
                    "description": "现有实现",
                    "config": {},
                    "traffic_allocation": 0.5,
                },
                {
                    "name": "改进版本",
                    "type": "treatment",
                    "description": action_text,
                    "config": {"insight_id": str(insight.get("insight_id", ""))},
                    "traffic_allocation": 0.5,
                },
            ]

            experiment_id = self.ab_testing.create_experiment(
                name=f"洞察驱动测试: {insight.get('title', '未命名')}",
                experiment_type=exp_type,
                description=str(insight.get("description", "")),
                hypothesis="实施改进可以提升用户体验",
                variants=variants,
                success_criteria={
                    "impact_threshold": insight.get("impact_score", 0) * 0.5
                },
                created_by="insight_integration",
            )

            if experiment_id:
                logger.info(f"从洞察创建A/B测试: {experiment_id}")

            return experiment_id

        except Exception as e:
            logger.error(f"从洞察创建A/B测试失败: {e}")
            return ""

    def on_experiment_completed(self, experiment_id: str, results: dict[str, Any]):
        """A/B测试完成"""
        logger.info(
            f"A/B测试完成: {experiment_id}, 获胜变体: {results.get('winner_variant_id')}"
        )

        # 自动添加到迭代
        if self.workflows.get("ab_result_to_iteration"):
            self.add_ab_result_to_iteration(experiment_id, results)

    def add_ab_result_to_iteration(
        self, experiment_id: str, results: dict[str, Any]
    ) -> None:
        """将A/B测试结果添加到迭代"""
        try:
            winner_id = results.get("winner_variant_id")

            if not winner_id:
                logger.info(f"A/B测试 {experiment_id} 无明显获胜变体，不自动添加到迭代")
                return

            # 获取实验信息
            experiment = self.ab_testing.experiments.get(experiment_id)
            if not experiment:
                return

            # 创建功能需求
            feature_id = f"feat_ab_{int(datetime.now().timestamp() * 1000)}"

            from ..product.iteration_manager import (
                FeatureRequest,
                FeatureStatus,
                ImpactLevel,
            )

            # 确定影响等级
            total_participants = results.get("total_participants", 0)
            if total_participants >= 1000:
                impact = ImpactLevel.HIGH
            elif total_participants >= 500:
                impact = ImpactLevel.MEDIUM
            else:
                impact = ImpactLevel.LOW

            feature = FeatureRequest(
                request_id=feature_id,
                title=f"应用A/B测试结果: {experiment.name}",
                description=f"A/B测试 {experiment_id} 显示获胜变体效果更好，建议全面推广",
                source="ab_testing",
                priority=80,  # 高优先级
                impact_level=impact,
                effort_estimate=3,  # 假设3天
                status=FeatureStatus.APPROVED,  # 自动批准
                user_votes=total_participants,
            )

            self.iteration_manager.feature_requests[feature_id] = feature
            self.iteration_manager.save_feature(feature)

            logger.info(f"A/B测试结果已转换为功能需求: {feature_id}")

            self.action_completed.emit("ab_result_to_feature", feature_id)

        except Exception as e:
            logger.error(f"添加A/B测试结果到迭代失败: {e}")

    def on_nps_updated(self, score: float) -> None:
        """NPS更新"""
        logger.info(f"NPS更新: {score}")

        # 如果NPS过低，触发紧急改进
        if score < 0:
            self.workflow_triggered.emit(
                "nps_alert",
                {
                    "score": score,
                    "severity": "critical",
                    "action": "需要立即改进用户体验",
                },
            )

    def on_feature_proposed(self, feature_id: str) -> None:
        """功能提议"""
        logger.info(f"功能已提议: {feature_id}")

    def sync_data(self) -> None:
        """同步数据"""
        try:
            # 从反馈处理器获取统计
            processor_stats = self.feedback_processor.get_processing_stats()

            # 更新分析系统的反馈数据
            # 这里可以添加更多的数据同步逻辑

            logger.debug(
                f"数据同步完成，已处理 {processor_stats.get('total_processed', 0)} 条反馈"
            )

        except Exception as e:
            logger.error(f"数据同步失败: {e}")

    def generate_integration_report(self) -> dict[str, Any]:
        """生成集成报告"""
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "feedback_processing": self.feedback_processor.get_processing_stats(),
                "analytics": {
                    "total_feedbacks": len(self.analytics.feedbacks),
                    "insights_generated": len(self.analytics.insights),
                    "segments": len(self.analytics.segments),
                },
                "ab_testing": {
                    "total_experiments": len(self.ab_testing.experiments),
                    "active_experiments": len(self.ab_testing.active_experiments),
                },
                "product_iteration": {
                    "feature_requests": len(self.iteration_manager.feature_requests),
                    "bug_fixes": len(self.iteration_manager.bug_fixes),
                    "improvements": len(self.iteration_manager.improvements),
                    "iterations": len(self.iteration_manager.iterations),
                },
                "workflow_status": self.workflows,
                "automation_rules": self.automation_rules,
            }

            return report

        except Exception as e:
            logger.error(f"生成集成报告失败: {e}")
            return {}

    def export_integration_report(self, output_path: str | None = None) -> str:
        """导出集成报告"""
        try:
            if not output_path:
                output_file = (
                    self.data_dir
                    / f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
            else:
                output_file = Path(output_path)

            report = self.generate_integration_report()

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"集成报告已导出: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"导出集成报告失败: {e}")
            return ""
