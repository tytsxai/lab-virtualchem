"""
Minimal ExperimentController tests to ensure core flows work.
"""

from __future__ import annotations

import pytest

from src.core.experiment_controller import (
    ExperimentController,
    ExperimentMode,
    ExperimentState,
)
from src.models.experiment import CheckPoint, CheckType, ExperimentTemplate, Step


class DummyValidator:
    def __init__(self, should_pass: bool = True):
        self.should_pass = should_pass

    def check_step(self, step, user_input, context):
        return (self.should_pass, "OK" if self.should_pass else "输入不正确")

    def evaluate_score_rules(self, rules, context):
        return 100, {"auto": "basic"}


@pytest.fixture
def simple_template():
    step = Step(id="step-1", text="Add reagent", check=CheckPoint(type=CheckType.CONFIRM))
    return ExperimentTemplate(id="exp-1", title="Demo Experiment", steps=[step])


def test_start_experiment_updates_state(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        validator=DummyValidator(),
        enable_monitoring=False,
        enable_auto_save=False,
        mode=ExperimentMode.PRACTICE,
    )

    controller.start_experiment()

    assert controller.state == ExperimentState.IN_PROGRESS
    assert controller.record.status == "in_progress"
    assert controller.record.started_at is not None


def test_submit_step_success_completes_experiment(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        validator=DummyValidator(should_pass=True),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    result = controller.submit_step({"temperature": 20})

    assert result.is_valid is True
    assert controller.record.step_records[0].passed is True
    assert controller.record.status == "completed"
    assert controller.record.current_step_index == 0  # single step


def test_submit_step_failure_records_mistake(simple_template):
    controller = ExperimentController(
        template=simple_template,
        user_id="student",
        validator=DummyValidator(should_pass=False),
        enable_monitoring=False,
        enable_auto_save=False,
    )
    controller.start_experiment()

    result = controller.submit_step({"temperature": 20})

    assert result.is_valid is False
    assert controller.record.step_records[0].passed is False
    assert controller.record.mistakes_summary
    assert controller.state == ExperimentState.IN_PROGRESS
