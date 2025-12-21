"""Unit tests for src.core.experiment_engine.

These tests focus on:
- 状态转换：start/pause/resume/cancel/complete
- 步骤执行：submit_step 自动推进与完成
- 错误处理：safe_execute 默认返回、验证异常分支
- 边界条件：无当前步骤、取消后提交
"""

from __future__ import annotations

from datetime import timedelta

import importlib

import pytest

from src.models.experiment import Curve, CurveType
from src.models.user_record import Mistake
from src.models.experiment import ExperimentTemplate, Step
from tests.fixtures.monitoring_stubs import build_monitoring_stubs


class StubValidator:
    def __init__(self, results: list[tuple[bool, str]]):
        self._results = list(results)

    def check_step(self, step, user_input, context):
        if self._results:
            return self._results.pop(0)
        return True, ""

    def evaluate_score_rules(self, rules, context):
        return 0, {}


@pytest.fixture
def two_step_template() -> ExperimentTemplate:
    return ExperimentTemplate(
        id="engine-flow",
        title="Engine Flow",
        steps=[Step(id="s1", text="Step 1"), Step(id="s2", text="Step 2")],
    )

@pytest.fixture
def engine_module():
    module = importlib.import_module("src.core.experiment_engine")
    return importlib.reload(module)


def test_experiment_engine_state_transitions(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )

    assert controller.state == engine_module.ExperimentState.NOT_STARTED
    controller.start_experiment()
    assert controller.state == engine_module.ExperimentState.IN_PROGRESS

    assert controller.pause_experiment() is True
    assert controller.state == engine_module.ExperimentState.PAUSED
    controller.pause_time = controller.pause_time - timedelta(seconds=1)  # type: ignore[operator]

    assert controller.resume_experiment() is True
    assert controller.state == engine_module.ExperimentState.IN_PROGRESS
    assert controller.total_pause_duration >= 1.0

    assert controller.cancel_experiment("stop") is True
    assert controller.state == engine_module.ExperimentState.CANCELLED
    assert controller.record.status == "cancelled"


def test_experiment_engine_submit_step_advances_and_completes(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok"), (True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    result1 = controller.submit_step({"confirmed": True})
    assert result1.is_valid is True
    assert controller.current_step_index == 1

    result2 = controller.submit_step({"confirmed": True})
    assert result2.is_valid is True
    assert controller.state == engine_module.ExperimentState.COMPLETED
    assert controller.record.status == "completed"


def test_experiment_engine_submit_step_records_mistake_on_failure(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(False, "bad input")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    step_record = controller.record.get_current_step_record()
    assert step_record is not None
    attempts_before = step_record.attempts

    result = controller.submit_step({"x": 1})
    assert result.is_valid is False
    assert result.mistake is not None
    assert controller.record.mistakes_summary
    assert controller.record.mistakes_summary[-1].description == "bad input"

    step_record_after = controller.record.get_current_step_record()
    assert step_record_after is not None
    assert step_record_after.attempts == attempts_before + 1


def test_experiment_engine_submit_step_rejects_when_cancelled(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.cancel_experiment("cancel")

    result = controller.submit_step({"confirmed": True})
    assert result.is_valid is False
    assert "不允许提交步骤" in result.message
    assert result.errors


def test_experiment_engine_submit_step_safe_execute_default_return(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    # 传入非 dict，触发 validate_type -> ValidationError，被 safe_execute 捕获并返回默认值
    result = controller.submit_step(["not-a-dict"])  # type: ignore[arg-type]
    assert result.is_valid is False
    assert "系统错误" in result.message
    assert result.errors


def test_experiment_engine_submit_step_no_current_step_boundary(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.record.current_step_index = 99

    result = controller.submit_step({"confirmed": True})
    assert result.is_valid is False
    assert result.message == "没有当前步骤"
    assert result.errors == ["没有当前步骤"]


def test_experiment_engine_auto_save_storage_failure_is_swallowed(
    engine_module, two_step_template: ExperimentTemplate
):
    class ExplodingStorage:
        def save_record(self, record) -> None:
            raise RuntimeError("boom")

    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        storage=ExplodingStorage(),
        enable_monitoring=False,
        enable_auto_save=True,
    )

    # start_experiment() 会触发 _auto_save_state，异常应被吞掉
    controller.start_experiment()
    assert controller.state == engine_module.ExperimentState.IN_PROGRESS


def test_experiment_engine_complete_experiment_generates_score_and_curves(
    engine_module, two_step_template: ExperimentTemplate
):
    class CurveGeneratorStub:
        class _Arr(list):
            def tolist(self):
                return list(self)

        def generate(self, curve_type, params):
            _ = (curve_type, params)
            return self._Arr([0.0, 1.0]), self._Arr([1.0, 2.0])

    template = two_step_template.model_copy(deep=True)
    template.curves = [
        Curve(id="c1", type=CurveType.TEMP_TIME, params={"x": "t", "y": "temp"})
    ]

    controller = engine_module.ExperimentController(
        template=template,
        user_id="student",
        validator=StubValidator([(True, "ok"), (True, "ok")]),
        curve_generator=CurveGeneratorStub(),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.submit_step({"confirmed": True})
    controller.submit_step({"confirmed": True})

    record = controller.complete_experiment()
    assert record.status == "completed"
    assert 0 <= record.score.total <= 100
    assert "c1" in record.curve_data


def test_experiment_engine_score_falls_back_when_rules_evaluation_raises(
    engine_module, two_step_template: ExperimentTemplate
):
    class ExplodingValidator(StubValidator):
        def evaluate_score_rules(self, rules, context):
            raise RuntimeError("nope")

    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=ExplodingValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.submit_step({"confirmed": True})

    # 只完成 1/2 步骤 => completion_rate=50
    record = controller.complete_experiment()
    assert record.score.total == 50


def test_experiment_engine_export_restore_and_duration_excludes_pause_time(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.pause_experiment()
    controller.pause_time = controller.pause_time - timedelta(seconds=1)  # type: ignore[operator]
    controller.resume_experiment()

    exported = controller.export_state()
    restored = engine_module.ExperimentController(
        template=two_step_template,
        user_id="clone",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    assert restored.restore_from_state(exported) is True
    assert restored.total_pause_duration >= 1.0
    assert restored.get_experiment_duration() >= 0.0


def test_experiment_engine_safety_and_learning_analysis(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.record.mistakes_summary.extend(
        [
            Mistake(
                step_id="s1",
                error_type="spill",
                description="danger",
                severity="critical",
            ),
            Mistake(
                step_id="s2",
                error_type="spill",
                description="careful",
                severity="severe",
            ),
        ]
    )

    assessment = controller.get_safety_assessment()
    assert assessment["overall_safety"] == "unsafe"
    assert assessment["critical_issues"]
    assert assessment["recommendations"]

    analysis = controller.get_learning_analysis()
    assert analysis["weaknesses"]
    assert analysis["progress_rate"] == 0.0


def test_experiment_engine_can_complete_reports_incomplete_steps(
    engine_module, two_step_template: ExperimentTemplate
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.record.step_records[0].passed = True
    controller.record.step_records[1].passed = False

    ok, missing = controller.can_complete_experiment()
    assert ok is False
    assert missing == ["s2"]


def test_experiment_engine_monitoring_hooks_are_exercised(
    engine_module, two_step_template: ExperimentTemplate
):
    monitor, trace_manager, metrics = build_monitoring_stubs()
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok"), (True, "ok")]),
        enable_monitoring=True,
        enable_auto_save=False,
        monitor_factory=lambda: monitor,
        trace_manager=trace_manager,
        metrics_collector=metrics,
    )
    controller.start_experiment()
    controller.submit_step({"confirmed": True})
    controller.submit_step({"confirmed": True})
    controller.complete_experiment()

    assert any(c["name"] == "experiment.initialized" for c in monitor.apm.counters)
    assert trace_manager.started and trace_manager.finished
    assert metrics.recorded


def test_experiment_engine_navigation_and_results(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    assert controller.go_to_step(-1) is False
    assert controller.go_to_step(99) is False
    assert controller.go_to_step(1) is True
    assert controller.previous_step() is True
    assert controller.previous_step() is False

    controller.submit_step({"confirmed": True})
    results = controller.get_results()
    assert isinstance(results, list)
    assert results[0]["step_id"] == "s1"
    assert results[0]["is_correct"] is True


def test_experiment_engine_restore_state_rejects_bad_state(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    bad_state = {"state": "definitely-not-a-real-state", "session_id": "x"}
    assert controller.restore_from_state(bad_state) is False


def test_experiment_engine_retry_current_step_clears_current_step_mistakes(
    engine_module, two_step_template
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(False, "bad")]),
        max_retries=2,
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.submit_step({"x": 1})
    assert controller.record.mistakes_summary

    assert controller.retry_current_step() is True
    assert controller.record.mistakes_summary == []


def test_experiment_engine_performance_metrics_contains_state(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    metrics = controller.get_performance_metrics()
    assert metrics["state"] == engine_module.ExperimentState.IN_PROGRESS.value
    assert metrics["total_steps"] == 2


def test_experiment_engine_submit_step_returns_error_when_validator_raises(
    engine_module, two_step_template
):
    class ExplodingCheckValidator(StubValidator):
        def check_step(self, step, user_input, context):
            raise RuntimeError("validator boom")

    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=ExplodingCheckValidator([]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    result = controller.submit_step({"x": 1})
    assert result.is_valid is False
    assert "验证过程出错" in result.message


def test_experiment_engine_submit_step_returns_error_when_step_record_update_fails(
    engine_module, two_step_template
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    # StepRecord.user_input 会校验 key，只允许字母数字/下划线/连字符
    result = controller.submit_step({"bad key": 1})
    assert result.is_valid is False
    assert result.message == "保存步骤结果失败"


def test_experiment_engine_submit_step_swallow_mistake_recording_failure(
    engine_module, two_step_template
):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(False, "bad")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    # 通过让 current_step.check 为“非空但缺少 fail_hint 属性”的对象，
    # 触发 Mistake 构造流程内的 AttributeError，覆盖错误吞掉分支。
    controller.template.steps[0].check = object()  # type: ignore[assignment]
    result = controller.submit_step({"x": 1})
    assert result.is_valid is False
    # 记录错误失败应被吞掉，不影响返回结构
    assert result.errors == ["bad"]


def test_experiment_engine_submit_step_swallow_context_update_failure(
    engine_module, two_step_template
):
    class BadDict(dict):
        def __setitem__(self, key, value):
            raise RuntimeError("context boom")

    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.record.context = BadDict()  # type: ignore[assignment]
    controller.start_experiment()
    result = controller.submit_step({"confirmed": True})
    assert result.is_valid is True


def test_experiment_engine_generate_curves_error_branch_is_handled(
    engine_module, two_step_template
):
    class ExplodingCurveGenerator:
        def generate(self, *_args, **_kwargs):
            raise RuntimeError("curve boom")

    template = two_step_template.model_copy(deep=True)
    template.curves = [
        Curve(id="c1", type=CurveType.TEMP_TIME, params={"x": "t", "y": "temp"})
    ]

    controller = engine_module.ExperimentController(
        template=template,
        user_id="student",
        curve_generator=ExplodingCurveGenerator(),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    for sr in controller.record.step_records:
        sr.passed = True
    controller.complete_experiment()
    assert controller.record.curve_data == {}


def test_experiment_engine_stepresult_supports_unpack_and_index(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(True, "ok")]),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    result = controller.submit_step({"confirmed": True})
    passed, message, mistake = tuple(result)
    assert passed is True
    assert message == "ok"
    assert mistake is None
    assert result[0] is True
    assert result[1] == "ok"


def test_experiment_engine_monitoring_init_failure_disables_monitoring(
    engine_module, two_step_template
):
    def exploding_monitor_factory():
        raise RuntimeError("monitor boom")

    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=True,
        enable_auto_save=False,
        monitor_factory=exploding_monitor_factory,
        trace_manager=object(),
        metrics_collector=object(),
    )
    assert controller._monitoring_enabled is False


def test_experiment_engine_userrecord_creation_failure_is_wrapped(engine_module, two_step_template):
    original = engine_module.UserRecord

    class ExplodingUserRecord:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("record boom")

    engine_module.UserRecord = ExplodingUserRecord  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match="无法创建用户记录"):
            engine_module.ExperimentController(
                template=two_step_template,
                user_id="student",
                enable_monitoring=False,
            )
    finally:
        engine_module.UserRecord = original  # type: ignore[assignment]


def test_experiment_engine_steprecord_init_failure_is_wrapped(engine_module, two_step_template):
    original = engine_module.StepRecord

    class ExplodingStepRecord:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("step record boom")

    engine_module.StepRecord = ExplodingStepRecord  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match="无法初始化步骤记录"):
            engine_module.ExperimentController(
                template=two_step_template,
                user_id="student",
                enable_monitoring=False,
            )
    finally:
        engine_module.StepRecord = original  # type: ignore[assignment]


def test_experiment_engine_monitoring_failure_metrics_on_failed_step(
    engine_module, two_step_template
):
    monitor, trace_manager, metrics = build_monitoring_stubs()
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        validator=StubValidator([(False, "bad")]),
        enable_monitoring=True,
        enable_auto_save=False,
        monitor_factory=lambda: monitor,
        trace_manager=trace_manager,
        metrics_collector=metrics,
    )
    controller.start_experiment()
    result = controller.submit_step({"x": 1})
    assert result.is_valid is False
    assert any(c["name"] == "experiment.step.failed" for c in monitor.apm.counters)


def test_experiment_engine_progress_record_and_state_export_fields(engine_module, two_step_template):
    controller = engine_module.ExperimentController(
        template=two_step_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    progress = controller.get_progress()
    assert progress["total_steps"] == 2
    assert progress["status"] == "in_progress"

    for sr in controller.record.step_records:
        sr.passed = True
    controller.complete_experiment()
    exported = controller.export_state()
    assert exported["end_time"] is not None
