"""实验控制器 - 管理实验流程与状态

增强功能:
1. 智能错误恢复和重试机制
2. 实验进度持久化和恢复
3. 实时性能监控和优化建议
4. 多用户协作支持
5. 实验数据分析和学习建议
6. 自适应难度调整
7. 安全检查和风险评估
8. 实验回放和重放功能
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.curve_generator import CurveGenerator
from src.core.rule_validator import RuleValidator
from src.models.experiment import ExperimentTemplate
from src.models.user_record import Mistake, StepRecord, UserRecord
from src.utils.error_handler import (
    safe_execute,
    validate_not_empty,
    validate_not_none,
    validate_type,
)

# 导入监控模块
try:
    from src.monitoring.backend_monitor import BackendMonitor
    from src.monitoring.distributed_tracing import TracingContext, get_trace_manager
    from src.monitoring.experiment_metrics import get_experiment_metrics_collector

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExperimentState(Enum):
    """实验状态枚举"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentMode(Enum):
    """实验模式枚举"""

    PRACTICE = "practice"  # 练习模式
    EXAM = "exam"  # 考试模式
    DEMO = "demo"  # 演示模式
    COLLABORATIVE = "collaborative"  # 协作模式


class SafetyLevel(Enum):
    """安全级别枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StepResult:
    """步骤提交结果（兼容 tuple 解包与属性访问）"""

    is_valid: bool
    message: str
    mistake: Mistake | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __iter__(self):
        """支持 (passed, message, mistake) 解包，用于兼容服务层接口"""
        yield self.is_valid
        yield self.message
        yield self.mistake

    def __getitem__(self, index: int) -> Any:
        """支持基于索引的访问以兼容旧式测试代码"""
        data = (self.is_valid, self.message, self.mistake)
        return data[index]


class ExperimentController:
    """实验流程控制器"""

    def __init__(
        self,
        template: ExperimentTemplate,
        user_id: str,
        validator: RuleValidator | None = None,
        storage: Any | None = None,
        curve_generator: CurveGenerator | None = None,
        enable_monitoring: bool = True,
        mode: ExperimentMode = ExperimentMode.PRACTICE,
        session_id: str | None = None,
        enable_auto_save: bool = True,
        max_retries: int = 3,
        monitor_factory: Any | None = None,
        trace_manager: Any | None = None,
        metrics_collector: Any | None = None,
    ) -> None:
        """初始化实验控制器

        Args:
            template: 实验模板
            user_id: 用户ID
            validator: 规则验证器(可选)
            storage: 实验记录存储引擎(可选, 例如 JSONStore)
            curve_generator: 曲线生成器(可选)
            enable_monitoring: 是否启用监控(默认True)
            mode: 实验模式(默认练习模式)
            session_id: 会话ID(可选，用于恢复实验)
            enable_auto_save: 是否启用自动保存(默认True)
            max_retries: 最大重试次数(默认3)
            monitor_factory: 自定义监控实例创建器(用于测试替换)
            trace_manager: 自定义追踪管理器(用于测试替换)
            metrics_collector: 自定义指标收集器(用于测试替换)

        Raises:
            ValidationError: 参数验证失败
        """
        # 验证输入参数
        validate_not_none(template, "实验模板")
        validate_not_none(user_id, "用户ID")
        validate_type(template, ExperimentTemplate, "实验模板")
        validate_type(user_id, str, "用户ID")
        # 空字符串校验，保持与全局验证错误类型一致
        validate_not_empty(user_id, "用户ID")

        if not template.steps:
            raise ValueError(f"实验模板 {template.id} 没有定义步骤")

        self.template = template
        self.user_id = user_id
        self.validator = validator or RuleValidator()
        self.storage = storage
        self.curve_generator = curve_generator or CurveGenerator()
        self.mode = mode
        self.session_id = session_id or str(uuid.uuid4())
        self.enable_auto_save = enable_auto_save
        self.max_retries = max_retries

        # 新增状态管理
        self.state = ExperimentState.NOT_STARTED
        self.start_time: datetime | None = None
        self.pause_time: datetime | None = None
        self.total_pause_duration = 0.0
        self.retry_count = 0
        self.current_step_retries = 0
        self.performance_metrics: dict[str, Any] = {}
        self.safety_warnings: list[str] = []
        self.learning_suggestions: list[str] = []

        # 初始化监控
        self._monitor: Any | None = None
        self._trace_manager: Any | None = None
        self._metrics_collector: Any | None = None
        self._trace_context: TracingContext | None = None

        self._monitoring_enabled = enable_monitoring and (
            MONITORING_AVAILABLE
            or monitor_factory is not None
            or trace_manager is not None
            or metrics_collector is not None
        )
        if self._monitoring_enabled:
            try:
                monitor_creator = monitor_factory or BackendMonitor
                self._monitor = monitor_creator()
                self._trace_manager = trace_manager or get_trace_manager()
                self._metrics_collector = metrics_collector or get_experiment_metrics_collector()
                logger.info("实验监控已启用")
            except Exception as e:
                logger.warning(f"监控初始化失败,将禁用监控: {e}")
                self._monitoring_enabled = False
                self._monitor = None
                self._trace_manager = None
                self._metrics_collector = None
                self._trace_context = None

        # 创建用户记录
        try:
            self.record = UserRecord(
                record_id=str(uuid.uuid4()),
                user_id=user_id,
                experiment_id=template.id,
                experiment_title=template.title,
            )
        except Exception as e:
            logger.error(f"创建用户记录失败: {e}")
            raise ValueError(f"无法创建用户记录: {e}") from e

        # 初始化步骤记录
        try:
            for step in template.steps:
                self.record.step_records.append(StepRecord(step_id=step.id, started_at=datetime.now()))
        except Exception as e:
            logger.error(f"初始化步骤记录失败: {e}")
            raise ValueError(f"无法初始化步骤记录: {e}") from e

        # 记录初始化指标
        if self._monitoring_enabled:
            self._monitor.apm.increment_counter(
                "experiment.initialized",
                experiment_id=template.id,
                user_id=user_id,
            )
            self._monitor.apm.set_gauge("experiment.steps.total", float(len(template.steps)), experiment_id=template.id)

        logger.info(f"实验控制器已初始化: {template.title} (用户: {user_id})")

    def start_experiment(self) -> None:
        """开始实验"""
        # 开始分布式追踪
        if self._monitoring_enabled:
            self._trace_context = self._trace_manager.start_trace(
                "experiment.execute",
                experiment_id=self.template.id,
                experiment_title=self.template.title,
                user_id=self.user_id,
            )
            self._trace_manager.log_event(
                "experiment_started", self._trace_context, total_steps=len(self.template.steps)
            )

            # 记录实验开始指标
            self._monitor.apm.increment_counter(
                "experiment.started",
                experiment_id=self.template.id,
            )
            self._monitor.apm.set_gauge("experiment.active", 1.0, experiment_id=self.template.id, user_id=self.user_id)

        self.state = ExperimentState.IN_PROGRESS
        self.start_time = datetime.now()
        self.record.status = "in_progress"
        self.record.started_at = self.start_time
        self.record.completed_at = None

        # 自动保存实验状态
        if self.enable_auto_save:
            self._auto_save_state()

        logger.info(f"实验开始: {self.template.title} (模式: {self.mode.value}, 会话: {self.session_id})")

    def get_current_step(self) -> Any | None:
        """获取当前步骤"""
        if 0 <= self.record.current_step_index < len(self.template.steps):
            return self.template.steps[self.record.current_step_index]
        return None

    @safe_execute(
        context="提交实验步骤",
        default_return=StepResult(False, "系统错误,请稍后重试", None, errors=["系统错误,请稍后重试"]),
    )  # type: ignore[misc]
    def submit_step(self, user_input: dict[str, Any]) -> StepResult:
        """提交步骤

        Args:
            user_input: 用户输入

        Returns:
            (是否通过, 提示信息, 错误对象)

        Raises:
            ValidationError: 输入参数无效
        """
        step_start_time = time.time()

        # 验证输入
        validate_not_none(user_input, "用户输入")
        validate_type(user_input, dict, "用户输入")

        # 检查实验状态
        if self.record.status not in ["in_progress", "not_started"]:
            logger.warning(f"实验状态异常: {self.record.status}")
            msg = f"实验当前状态({self.record.status})不允许提交步骤"
            return StepResult(False, msg, None, errors=[msg])

        current_step = self.get_current_step()
        if current_step is None:
            logger.error(f"无法获取当前步骤,索引: {self.record.current_step_index}")
            msg = "没有当前步骤"
            return StepResult(False, msg, None, errors=[msg])

        step_record = self.record.get_current_step_record()
        if step_record is None:
            logger.error(f"无法获取步骤记录: {current_step.id}")
            msg = "步骤记录不存在"
            return StepResult(False, msg, None, errors=[msg])

        # 开始步骤追踪
        if self._monitoring_enabled and self._trace_context:
            step_trace_ctx = self._trace_manager.start_trace(
                f"experiment.step.{current_step.id}",
                context=self._trace_context,
                step_id=current_step.id,
                step_index=self.record.current_step_index,
                step_type="step",  # Step类没有type字段，使用默认值
            )

        # 验证步骤
        try:
            validation_start = time.time()
            passed, message = self.validator.check_step(current_step, user_input, self.record.context)
            validation_duration = (time.time() - validation_start) * 1000

            # 记录验证性能
            if self._monitoring_enabled:
                self._monitor.apm.record_histogram(
                    "experiment.step.validation_duration_ms",
                    validation_duration,
                    experiment_id=self.template.id,
                    step_id=current_step.id,
                )
        except Exception as e:
            logger.error(f"步骤验证失败: {e}", exc_info=True)
            if self._monitoring_enabled and self._trace_context:
                self._trace_manager.finish_span(step_trace_ctx, status="error")
            msg = f"验证过程出错: {e!s}"
            return StepResult(False, msg, None, errors=[msg])

        # 更新步骤记录
        try:
            step_record.user_input = user_input.copy()  # 使用副本防止外部修改
            step_record.passed = passed
            step_record.completed_at = datetime.now()
        except Exception as e:
            logger.error(f"更新步骤记录失败: {e}", exc_info=True)
            msg = "保存步骤结果失败"
            return StepResult(False, msg, None, errors=[msg])

        # 记录错误
        mistake = None
        if not passed:
            step_record.attempts += 1
            try:
                mistake = Mistake(
                    step_id=current_step.id,
                    error_type="validation_failed",
                    description=message,
                    hint=current_step.check.fail_hint if current_step.check else "",
                    severity=current_step.safety_level,
                )
                self.record.add_mistake(mistake)
                logger.warning(f"步骤失败: {current_step.id} - {message} (尝试次数: {step_record.attempts})")

                # 记录失败指标
                if self._monitoring_enabled:
                    self._monitor.apm.increment_counter(
                        "experiment.step.failed",
                        experiment_id=self.template.id,
                        step_id=current_step.id,
                        severity=current_step.safety_level,
                    )
                    self._trace_manager.log_event(
                        "step_failed",
                        step_trace_ctx,
                        attempts=step_record.attempts,
                        severity=current_step.safety_level,
                    )
            except Exception as e:
                logger.error(f"记录错误信息失败: {e}", exc_info=True)
        else:
            # 更新上下文
            try:
                self.record.context[f"{current_step.id}_completed"] = True
                # 只更新安全的上下文数据
                for key, value in user_input.items():
                    if isinstance(value, (str, int, float, bool)):
                        self.record.context[key] = value
                logger.info(f"步骤通过: {current_step.id}")

                # 记录成功指标
                if self._monitoring_enabled:
                    self._monitor.apm.increment_counter(
                        "experiment.step.passed",
                        experiment_id=self.template.id,
                        step_id=current_step.id,
                    )
                    self._trace_manager.log_event("step_passed", step_trace_ctx, attempts=step_record.attempts)
            except Exception as e:
                logger.error(f"更新上下文失败: {e}", exc_info=True)

        # 完成步骤追踪
        if self._monitoring_enabled and self._trace_context:
            self._trace_manager.set_tag("passed", passed, step_trace_ctx)
            self._trace_manager.set_tag("attempts", step_record.attempts, step_trace_ctx)
            self._trace_manager.finish_span(step_trace_ctx, status="ok" if passed else "failed")

            # 记录步骤执行时间
            step_duration = (time.time() - step_start_time) * 1000
            self._monitor.apm.record_histogram(
                "experiment.step.duration_ms",
                step_duration,
                experiment_id=self.template.id,
                step_id=current_step.id,
                passed=str(passed),
            )
        errors: list[str] = []
        warnings: list[str] = []
        if not passed and message:
            errors.append(message)

        # 成功时自动前进到下一步（符合集成测试对流程控制的期望）
        if passed:
            self.next_step()
            if self.is_completed():
                self._mark_experiment_completed(step_record.completed_at)

        return StepResult(passed, message, mistake, errors=errors, warnings=warnings)

    def next_step(self) -> bool:
        """前进到下一步

        Returns:
            是否成功前进
        """
        if self.record.current_step_index < len(self.template.steps) - 1:
            self.record.current_step_index += 1
            return True
        return False

    def previous_step(self) -> bool:
        """返回上一步

        Returns:
            是否成功返回
        """
        if self.record.current_step_index > 0:
            self.record.current_step_index -= 1
            return True
        return False

    def go_to_step(self, index: int) -> bool:
        """跳转到指定步骤索引"""
        if 0 <= index < len(self.template.steps):
            self.record.current_step_index = index
            return True
        return False

    def can_complete_experiment(self) -> tuple[bool, list[str]]:
        """检查是否可以完成实验

        Returns:
            (是否可以完成, 未完成步骤列表)
        """
        incomplete_steps = []

        for step_record in self.record.step_records:
            if not step_record.passed:
                incomplete_steps.append(step_record.step_id)

        return len(incomplete_steps) == 0, incomplete_steps

    def complete_experiment(self) -> UserRecord:
        """完成实验并计算评分

        Returns:
            完成的用户记录
        """
        self._mark_experiment_completed()

        # 计算评分
        self._calculate_score()

        # 生成曲线数据
        self._generate_curves()

        # 完成实验追踪
        if self._monitoring_enabled and self._trace_context:
            # 记录实验完成事件
            self._trace_manager.log_event(
                "experiment_completed",
                self._trace_context,
                score=self.record.score.total,
                total_mistakes=self.record.total_mistakes,
                completion_rate=self.record.completion_rate,
                duration_seconds=self.record.total_duration_seconds,
            )

            # 设置追踪标签
            self._trace_manager.set_tag("score", self.record.score.total, self._trace_context)
            self._trace_manager.set_tag("completion_rate", self.record.completion_rate, self._trace_context)

            # 完成追踪
            self._trace_manager.finish_span(self._trace_context, status="ok")

            # 记录实验完成指标
            self._monitor.apm.increment_counter(
                "experiment.completed",
                experiment_id=self.template.id,
            )
            self._monitor.apm.record_histogram(
                "experiment.score", float(self.record.score.total), experiment_id=self.template.id
            )
            self._monitor.apm.record_histogram(
                "experiment.duration_seconds",
                self.record.total_duration_seconds or 0,
                experiment_id=self.template.id,
            )
            self._monitor.apm.record_histogram(
                "experiment.mistakes",
                float(self.record.total_mistakes),
                experiment_id=self.template.id,
            )
            self._monitor.apm.set_gauge("experiment.active", 0.0, experiment_id=self.template.id, user_id=self.user_id)

            # 记录实验运行数据到指标收集器
            self._metrics_collector.record_experiment_run(
                experiment_id=self.template.id,
                experiment_title=self.template.title,
                experiment_type=self.template.category,  # 使用category代替type
                user_id=self.user_id,
                record_data={
                    "status": self.record.status,
                    "score": self.record.score.model_dump(),
                    "duration_seconds": self.record.total_duration_seconds,
                    "completion_rate": self.record.completion_rate,
                    "mistakes_summary": [m.model_dump() for m in self.record.mistakes_summary],
                    "step_records": [
                        {
                            "step_id": sr.step_id,
                            "passed": sr.passed,
                            "attempts": sr.attempts,
                        }
                        for sr in self.record.step_records
                    ],
                },
            )

        logger.info(f"实验完成: {self.template.title}, 得分: {self.record.score.total}")
        return self.record

    def _calculate_score(self) -> None:
        """计算实验评分"""
        try:
            # 准备评分上下文
            score_context = self.record.context.copy()

            # 添加统计变量
            score_context["all_steps_passed"] = all(r.passed for r in self.record.step_records)
            score_context["total_mistakes"] = self.record.total_mistakes
            score_context["completion_rate"] = self.record.completion_rate

            # 安全性评估
            critical_mistakes = sum(1 for m in self.record.mistakes_summary if m.severity == "critical")
            severe_mistakes = sum(1 for m in self.record.mistakes_summary if m.severity == "severe")
            score_context["no_safety_warning"] = critical_mistakes == 0 and severe_mistakes == 0
            score_context["no_critical_mistakes"] = critical_mistakes == 0

            # 评估评分规则
            try:
                total_score, details = self.validator.evaluate_score_rules(
                    [rule.model_dump() for rule in self.template.score_rules], score_context
                )
                if not self.template.score_rules:
                    auto_score = int(score_context["completion_rate"])
                    if auto_score > total_score:
                        total_score = auto_score
                        details["auto_completion_score"] = auto_score
            except Exception as e:
                logger.error(f"评分规则评估失败: {e}", exc_info=True)
                # 使用基础评分方案
                total_score = int(score_context["completion_rate"])
                details = {"error": str(e)}

            # 更新评分并确保在有效范围内
            self.record.score.total = max(0, min(total_score, 100))
            self.record.score.details = details

            # 分项评分(简化计算)
            try:
                self.record.score.procedural = (
                    50 if score_context["all_steps_passed"] else int(score_context["completion_rate"] / 2)
                )
                self.record.score.safety = 50 if score_context["no_safety_warning"] else 20
                # 确保科学性得分不为负
                scientific_score = total_score - self.record.score.procedural - self.record.score.safety
                self.record.score.scientific = max(0, scientific_score)
            except Exception as e:
                logger.error(f"分项评分计算失败: {e}", exc_info=True)
                self.record.score.procedural = 0
                self.record.score.safety = 0
                self.record.score.scientific = 0

            logger.info(
                f"评分计算完成 - 总分: {self.record.score.total}, "
                f"操作: {self.record.score.procedural}, "
                f"安全: {self.record.score.safety}, "
                f"科学: {self.record.score.scientific}"
            )
        except Exception as e:
            logger.error(f"评分计算过程出错: {e}", exc_info=True)
            # 设置默认评分
            self.record.score.total = 0
            self.record.score.details = {"error": "评分计算失败"}
            self.record.score.procedural = 0
            self.record.score.safety = 0
            self.record.score.scientific = 0

    def _generate_curves(self) -> None:
        """生成实验曲线数据"""
        for curve_config in self.template.curves:
            try:
                x_data, y_data = self.curve_generator.generate(curve_config.type.value, curve_config.params)

                self.record.curve_data[curve_config.id] = {
                    "x": x_data.tolist(),
                    "y": y_data.tolist(),
                    "x_label": curve_config.x_label,
                    "y_label": curve_config.y_label,
                    "x_unit": curve_config.x_unit,
                    "y_unit": curve_config.y_unit,
                }

                logger.info(f"曲线已生成: {curve_config.id}")

            except Exception as e:
                logger.error(f"曲线生成失败 {curve_config.id}: {e}")

    def get_progress(self) -> dict[str, Any]:
        """获取实验进度信息

        Returns:
            进度信息字典
        """
        total_steps = len(self.template.steps)
        completed_steps = sum(1 for r in self.record.step_records if r.passed)
        progress_percentage = int(self.record.completion_rate)

        return {
            "experiment_id": self.template.id,
            "experiment_title": self.template.title,
            "current_step": self.record.current_step_index,
            "total_steps": total_steps,
            "completion_rate": self.record.completion_rate,
            # 兼容集成测试使用的字段
            "completed_steps": completed_steps,
            "progress_percentage": progress_percentage,
            "total_mistakes": self.record.total_mistakes,
            "status": self.record.status,
        }

    def get_record(self) -> UserRecord:
        """获取用户记录"""
        return self.record

    @property
    def current_step_index(self) -> int:
        """当前步骤索引（兼容旧接口）"""
        return self.record.current_step_index

    @property
    def end_time(self) -> datetime | None:
        """实验结束时间（兼容集成测试期望的属性）"""
        return self.record.completed_at

    def is_started(self) -> bool:
        """实验是否已开始"""
        return self.state != ExperimentState.NOT_STARTED

    def is_completed(self) -> bool:
        """实验是否已完成"""
        # 视所有步骤通过为完成状态
        return all(r.passed for r in self.record.step_records) if self.record.step_records else False

    def pause_experiment(self) -> bool:
        """暂停实验

        Returns:
            是否成功暂停
        """
        if self.state != ExperimentState.IN_PROGRESS:
            return False

        self.state = ExperimentState.PAUSED
        self.pause_time = datetime.now()

        if self.enable_auto_save:
            self._auto_save_state()

        logger.info(f"实验已暂停: {self.template.title}")
        return True

    def resume_experiment(self) -> bool:
        """恢复实验

        Returns:
            是否成功恢复
        """
        if self.state != ExperimentState.PAUSED:
            return False

        if self.pause_time:
            pause_duration = (datetime.now() - self.pause_time).total_seconds()
            self.total_pause_duration += pause_duration

        self.state = ExperimentState.IN_PROGRESS
        self.pause_time = None

        if self.enable_auto_save:
            self._auto_save_state()

        logger.info(f"实验已恢复: {self.template.title}")
        return True

    def cancel_experiment(self, reason: str = "") -> bool:
        """取消实验

        Args:
            reason: 取消原因

        Returns:
            是否成功取消
        """
        if self.state in [ExperimentState.COMPLETED, ExperimentState.CANCELLED]:
            return False

        self.state = ExperimentState.CANCELLED
        self.record.status = "cancelled"

        if self.enable_auto_save:
            self._auto_save_state()

        logger.info(f"实验已取消: {self.template.title}, 原因: {reason}")
        return True

    def get_experiment_duration(self) -> float:
        """获取实验持续时间(秒)

        Returns:
            持续时间(秒)，不包括暂停时间
        """
        if not self.start_time:
            return 0.0

        end_time = datetime.now() if self.state == ExperimentState.IN_PROGRESS else self.record.completed_at
        if not end_time:
            return 0.0

        total_duration = (end_time - self.start_time).total_seconds()
        return max(0.0, total_duration - self.total_pause_duration)

    def get_safety_assessment(self) -> dict[str, Any]:
        """获取安全评估

        Returns:
            安全评估结果
        """
        assessment: dict[str, Any] = {
            "overall_safety": "safe",
            "warnings": self.safety_warnings.copy(),
            "critical_issues": [],
            "recommendations": [],
        }

        # 检查严重错误
        critical_mistakes = [m for m in self.record.mistakes_summary if m.severity == "critical"]
        if critical_mistakes:
            assessment["overall_safety"] = "unsafe"
            assessment["critical_issues"] = [m.description for m in critical_mistakes]
            assessment["recommendations"].append("请重新学习安全操作规程")

        # 检查严重错误
        severe_mistakes = [m for m in self.record.mistakes_summary if m.severity == "severe"]
        if severe_mistakes:
            if assessment["overall_safety"] == "safe":
                assessment["overall_safety"] = "caution"
            assessment["recommendations"].append("注意实验安全，避免重复错误")

        return assessment

    def get_learning_analysis(self) -> dict[str, Any]:
        """获取学习分析

        Returns:
            学习分析结果
        """
        analysis: dict[str, Any] = {
            "strengths": [],
            "weaknesses": [],
            "suggestions": self.learning_suggestions.copy(),
            "progress_rate": self.record.completion_rate,
            "difficulty_level": "appropriate",
        }

        # 分析错误模式
        mistake_types: dict[str, int] = {}
        for mistake in self.record.mistakes_summary:
            mistake_type = mistake.error_type
            mistake_types[mistake_type] = mistake_types.get(mistake_type, 0) + 1

        # 识别强项和弱项
        if mistake_types:
            most_common_error = max(mistake_types.items(), key=lambda x: x[1])
            analysis["weaknesses"].append(f"在{most_common_error[0]}方面需要加强练习")

        # 分析进度
        if self.record.completion_rate > 0.8:
            analysis["strengths"].append("实验完成度较高")
        elif self.record.completion_rate < 0.5:
            analysis["suggestions"].append("建议先完成基础实验练习")

        return analysis

    def can_retry_step(self) -> bool:
        """检查是否可以重试当前步骤

        Returns:
            是否可以重试
        """
        return self.current_step_retries < self.max_retries and self.state == ExperimentState.IN_PROGRESS

    def retry_current_step(self) -> bool:
        """重试当前步骤

        Returns:
            是否成功重试
        """
        if not self.can_retry_step():
            return False

        self.current_step_retries += 1
        self.retry_count += 1

        # 清除当前步骤的错误记录
        current_step = self.get_current_step()
        if current_step:
            self.record.mistakes_summary = [m for m in self.record.mistakes_summary if m.step_id != current_step.id]

        logger.info(f"重试步骤: {current_step.id if current_step else 'unknown'} (第{self.current_step_retries}次)")
        return True

    def get_performance_metrics(self) -> dict[str, Any]:
        """获取性能指标

        Returns:
            性能指标字典
        """
        metrics = self.performance_metrics.copy()

        # 添加实时指标
        metrics.update(
            {
                "duration_seconds": self.get_experiment_duration(),
                "current_step": self.record.current_step_index,
                "total_steps": len(self.template.steps),
                "completion_rate": self.record.completion_rate,
                "retry_count": self.retry_count,
                "current_step_retries": self.current_step_retries,
                "mistakes_count": len(self.record.mistakes_summary),
                "state": self.state.value,
                "mode": self.mode.value,
            }
        )

        return metrics

    def get_results(self) -> list[dict[str, Any]]:
        """获取每个步骤的结果摘要（用于报告/测试）"""
        results: list[dict[str, Any]] = []

        for step, record in zip(self.template.steps, self.record.step_records, strict=False):
            results.append(
                {
                    "step_id": record.step_id,
                    "title": getattr(step, "title", record.step_id),
                    "data": record.user_input.copy(),
                    "is_correct": record.passed,
                }
            )

        return results

    def _mark_experiment_completed(self, completed_at: datetime | None = None) -> None:
        """统一设置实验完成状态并触发自动保存"""
        already_completed = self.record.status == "completed" and self.record.completed_at is not None

        if already_completed:
            if completed_at and self.record.completed_at != completed_at:
                self.record.completed_at = completed_at
        else:
            if completed_at:
                self.record.completed_at = completed_at
                self.record.status = "completed"
            else:
                self.record.complete_experiment()

        self.state = ExperimentState.COMPLETED

        if self.enable_auto_save:
            self._auto_save_state()

    def _auto_save_state(self) -> None:
        """自动保存实验状态"""
        try:
            if self.storage is not None:
                # 优先使用提供的存储引擎保存完整记录
                save_method = getattr(self.storage, "save_record", None)
                if callable(save_method):
                    save_method(self.record)
                    logger.debug(f"实验状态已保存到存储: {self.session_id}")
                    return

            # 未提供存储时，仅记录日志
            logger.debug(f"自动保存实验状态(无外部存储): {self.session_id}")
        except Exception as e:
            logger.warning(f"自动保存失败: {e}")

    def restore_from_state(self, state_data: dict[str, Any]) -> bool:
        """从保存的状态恢复实验

        Args:
            state_data: 状态数据

        Returns:
            是否成功恢复
        """
        try:
            # 恢复基本状态
            self.state = ExperimentState(state_data.get("state", "not_started"))
            self.session_id = state_data.get("session_id", self.session_id)
            self.retry_count = state_data.get("retry_count", 0)
            self.current_step_retries = state_data.get("current_step_retries", 0)
            self.total_pause_duration = state_data.get("total_pause_duration", 0.0)

            # 恢复时间信息
            if state_data.get("start_time"):
                self.start_time = datetime.fromisoformat(state_data["start_time"])
            if state_data.get("end_time"):
                self.record.completed_at = datetime.fromisoformat(state_data["end_time"])
            if state_data.get("pause_time"):
                self.pause_time = datetime.fromisoformat(state_data["pause_time"])

            logger.info(f"实验状态已恢复: {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"恢复实验状态失败: {e}")
            return False

    def export_state(self) -> dict[str, Any]:
        """导出实验状态

        Returns:
            状态数据字典
        """
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "mode": self.mode.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.record.completed_at.isoformat() if self.record.completed_at else None,
            "pause_time": self.pause_time.isoformat() if self.pause_time else None,
            "total_pause_duration": self.total_pause_duration,
            "retry_count": self.retry_count,
            "current_step_retries": self.current_step_retries,
            "performance_metrics": self.performance_metrics,
            "safety_warnings": self.safety_warnings,
            "learning_suggestions": self.learning_suggestions,
            "record": self.record.model_dump() if hasattr(self.record, "model_dump") else {},
        }
