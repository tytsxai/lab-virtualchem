"""Focused tests for ExperimentController state, retries, and monitoring hooks."""

import sys
import types
from datetime import timedelta
from pathlib import Path

import pytest

# 提前注入轻量级依赖桩，避免外部GUI/日志依赖影响单测
stub_root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "pyside6_stub"
if str(stub_root) not in sys.path:
    sys.path.insert(0, str(stub_root))

if "src.utils.logger" not in sys.modules:
    logger_stub = types.ModuleType("src.utils.logger")
    logger_stub.setup_logger = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    sys.modules["src.utils.logger"] = logger_stub

from src.core.experiment_controller import ExperimentController, ExperimentState
from src.models.experiment import ExperimentTemplate, Step
from tests.fixtures.monitoring_stubs import build_monitoring_stubs


class AlwaysPassValidator:
    """简单校验器，始终返回通过，用于隔离核心流程。"""

    def check_step(self, step, user_input, context):
        return True, ""

    def evaluate_score_rules(self, rules, context):
        return 0, {}


class EmptyAllowedTemplate(ExperimentTemplate):
    """允许空步骤以便验证控制器自身的校验逻辑。"""

    allow_empty_steps = True


@pytest.fixture
def simple_template():
    return ExperimentTemplate(
        id="state-flow",
        title="State Flow",
        steps=[Step(id="s1", text="Step 1"), Step(id="s2", text="Step 2")],
    )


def test_init_rejects_template_without_steps():
    empty_template = EmptyAllowedTemplate(id="empty-exp", title="Empty", steps=[])

    with pytest.raises(ValueError):
        ExperimentController(template=empty_template, user_id="student", enable_monitoring=False)


def test_pause_and_resume_state_flow(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )

    controller.start_experiment()
    assert controller.pause_experiment() is True
    assert controller.state == ExperimentState.PAUSED
    # 人为回溯暂停时间，确保恢复后累计暂停时长大于0
    controller.pause_time = controller.pause_time - timedelta(seconds=1)  # type: ignore[operator]

    assert controller.resume_experiment() is True
    assert controller.state == ExperimentState.IN_PROGRESS
    assert controller.total_pause_duration >= 1.0


def test_cancel_after_completion_refuses(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )

    controller.start_experiment()
    for step_record in controller.record.step_records:
        step_record.passed = True
    controller.complete_experiment()

    assert controller.state == ExperimentState.COMPLETED
    assert controller.cancel_experiment("already done") is False
    assert controller.state == ExperimentState.COMPLETED
    assert controller.record.status == "completed"


def test_retry_current_step_respects_limits(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        max_retries=2,
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    first = controller.retry_current_step()
    second = controller.retry_current_step()
    third = controller.retry_current_step()

    assert (first, second, third) == (True, True, False)
    assert controller.current_step_retries == 2
    assert controller.retry_count == 2

    controller.state = ExperimentState.PAUSED
    assert controller.can_retry_step() is False


def test_auto_save_disabled_skips_storage(simple_template):
    class DummyStorage:
        def __init__(self) -> None:
            self.saved = 0

        def save_record(self, record) -> None:
            self.saved += 1

    storage = DummyStorage()
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        storage=storage,
        enable_auto_save=False,
        enable_monitoring=False,
    )

    controller.start_experiment()
    for step_record in controller.record.step_records:
        step_record.passed = True
    controller.complete_experiment()

    assert storage.saved == 0


def test_monitoring_stubs_capture_signals(simple_template):
    monitor, trace_manager, metrics = build_monitoring_stubs()
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        validator=AlwaysPassValidator(),
        enable_monitoring=True,
        enable_auto_save=False,
        monitor_factory=lambda: monitor,
        trace_manager=trace_manager,
        metrics_collector=metrics,
    )

    controller.start_experiment()
    for step_record in controller.record.step_records:
        step_record.passed = True
    controller.complete_experiment()

    assert any(item["name"] == "experiment.initialized" for item in monitor.apm.counters)
    assert any(gauge["name"] == "experiment.active" for gauge in monitor.apm.gauges)
    assert trace_manager.started
    assert trace_manager.finished
    assert metrics.recorded


def test_export_and_restore_state_round_trip(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    controller.pause_experiment()
    exported = controller.export_state()

    restored = ExperimentController(
        template=simple_template,
        user_id="clone",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    assert restored.restore_from_state(exported) is True
    assert restored.state == ExperimentState.PAUSED
    assert restored.session_id == exported["session_id"]
    assert restored.pause_time is not None
    assert restored.start_time is not None


def test_performance_metrics_reflect_retries(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()
    assert controller.retry_current_step() is True

    metrics = controller.get_performance_metrics()

    assert metrics["retry_count"] == 1
    assert metrics["current_step_retries"] == 1
    assert metrics["state"] == ExperimentState.IN_PROGRESS.value
    assert metrics["total_steps"] == len(simple_template.steps)
