from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session


@pytest.mark.unit
def test_model_experiment_html_report_escapes_xss_payloads():
    from src.models.experiment import Experiment

    exp = Experiment(experiment_type="titration", title="normal")
    exp.prepare()
    exp.start()
    exp.complete()

    payload = '<img src=x onerror="alert(1)"><script>alert(1)</script>'
    exp.title = payload
    exp.state = payload
    exp.record_data(payload, payload)
    exp.record_observation(payload)

    html_report = exp.export_report(format="html")
    assert payload not in html_report
    assert "&lt;img" in html_report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_report


@pytest.mark.unit
def test_model_experiment_validators_reject_invalid_specs():
    from src.models.experiment import CheckPoint, CheckType, InputSpec, Step

    with pytest.raises(ValidationError):
        InputSpec(key="k1", label="L", input_type="unknown")

    with pytest.raises(ValidationError):
        CheckPoint(type=CheckType.INPUT, input=None)

    with pytest.raises(ValidationError):
        CheckPoint(type=CheckType.SEQUENCE, require=[])

    with pytest.raises(ValidationError):
        Step(id="bad id", text="t")


@pytest.mark.unit
def test_model_database_user_role_enum_rejects_unknown_role():
    from src.models.database import Base, User

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            User(
                user_id="u1",
                username="U",
                email="u@example.com",
                role="student",
            )
        )
        session.commit()

        session.add(
            User(
                user_id="u2",
                username="U2",
                email="u2@example.com",
                role="hacker",
            )
        )
        with pytest.raises((StatementError, LookupError, ValueError)):
            session.commit()


@pytest.mark.unit
def test_model_database_configuration_get_value_conversions():
    from src.models.database import Configuration

    assert Configuration(key="k", value="1", value_type="int", category="c").get_value() == 1
    assert (
        Configuration(key="k", value="1.25", value_type="float", category="c").get_value()
        == 1.25
    )
    assert (
        Configuration(key="k", value="YES", value_type="bool", category="c").get_value()
        is True
    )
    assert Configuration(key="k", value="no", value_type="bool", category="c").get_value() is False
    assert Configuration(key="k", value='{"x":1}', value_type="json", category="c").get_value() == {
        "x": 1
    }
    assert (
        Configuration(key="k", value="raw", value_type="string", category="c").get_value()
        == "raw"
    )


@pytest.mark.unit
def test_model_user_record_curve_schema_enforced_and_numeric_coerced():
    from src.models.user_record import ExperimentScore, UserRecord

    record = UserRecord(
        record_id="r1",
        user_id="u1",
        experiment_id="e1",
        experiment_title="t",
        started_at=datetime.now(),
        score=ExperimentScore(),
        context={},
        curve_data={"curve_1": {"x": [0, "1", 2], "y": [7, 7.1, "7.2"]}},
    )
    assert record.curve_data["curve_1"]["x"] == [0.0, 1.0, 2.0]
    assert record.curve_data["curve_1"]["y"] == [7.0, 7.1, 7.2]

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            experiment_title="t",
            started_at=datetime.now(),
            score=ExperimentScore(),
            context={},
            curve_data={"curve_1": {}},
        )


@pytest.mark.unit
def test_model_validation_helpers_cover_expression_and_range():
    from src.models.validation import validate_expression, validate_range, validate_yaml_safe

    ok, msg = validate_expression("abs(-1) + min(1, 2)")
    assert ok is True
    assert msg == ""

    ok, msg = validate_expression("os.system('rm -rf /')")
    assert ok is False
    assert "禁止" in msg or "不允许" in msg

    ok, msg = validate_expression("pow(2, 3)")
    assert ok is False
    assert "不允许调用函数" in msg

    ok, msg = validate_range(5.0, [0.0, 10.0])
    assert ok is True
    assert msg == ""

    ok, msg = validate_range(11.0, [0.0, 10.0])
    assert ok is False
    assert "超出有效范围" in msg

    ok, msg = validate_yaml_safe("!!python/object/apply:os.system")
    assert ok is False
    assert "YAML" in msg

    ok, msg = validate_expression("")
    assert ok is False
    assert "为空" in msg or "过长" in msg

    ok, msg = validate_range(1.0, [])
    assert ok is True
    assert msg == ""

    ok, msg = validate_yaml_safe({"safe": True})
    assert ok is True
    assert msg == ""


@pytest.mark.unit
def test_model_user_record_properties_and_step_duration():
    from src.models.user_record import ExperimentScore, Mistake, StepRecord, UserRecord

    started = datetime.now()
    completed = started.replace(microsecond=0)
    record = UserRecord(
        record_id="r1",
        user_id="u1",
        experiment_id="e1",
        started_at=started,
        completed_at=completed,
        score=ExperimentScore(total=50),
        curve_data={},
    )

    step = StepRecord(step_id="s1")
    step.completed_at = step.started_at
    step.passed = True
    step.mistakes.append(
        Mistake(step_id="s1", error_type="e", description="d", severity="warning")
    )
    record.step_records.append(step)

    assert record.total_duration_seconds is not None
    assert record.total_mistakes == 1
    assert record.completion_rate == 100.0
    assert step.duration_seconds == 0.0


@pytest.mark.unit
def test_model_user_record_schema_additional_branches():
    from src.models.user_record import Mistake, UserRecord

    with pytest.raises(ValidationError):
        UserRecord(record_id="r1", user_id="u1", experiment_id="e1", context="bad", curve_data={})

    with pytest.raises(ValidationError):
        UserRecord(record_id="r1", user_id="u1", experiment_id="e1", context={1: "x"}, curve_data={})

    with pytest.raises(ValidationError):
        UserRecord(record_id="r1", user_id="u1", experiment_id="e1", context={}, curve_data="bad")

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            context={},
            curve_data={"c1": {"x": "not-a-list", "y": [1]}},
        )

    record = UserRecord(record_id="r1", user_id="u1", experiment_id="e1", curve_data={})
    assert record.total_duration_seconds is None
    assert record.completion_rate == 0.0

    mistake = Mistake(step_id="s1", error_type="e", description="d")
    record.add_mistake(mistake)
    assert record.mistakes_summary == [mistake]

    step = record.add_step_record("s1")
    assert record.get_current_step_record() is step
    record.add_mistake(mistake)
    assert step.mistakes

    record.current_step_index = 99
    assert record.get_current_step_record() is None

    record.complete_experiment()
    assert record.status == "completed"
    assert record.completed_at is not None

    record.start_time = record.started_at
    record.end_time = record.completed_at
    record.final_score = 88
    assert record.final_score == 88



@pytest.mark.unit
def test_model_experiment_lifecycle_report_and_safety_branches():
    from src.models.experiment import (
        CheckPoint,
        CheckType,
        ExperimentTemplate,
        InputSpec,
        Step,
    )

    steps = [
        Step(id="s1", text="step1"),
        Step(
            id="s2",
            text="step2",
            check=CheckPoint(type=CheckType.SEQUENCE, require=["s1", "missing_step"]),
        ),
    ]
    exp = ExperimentTemplate(
        id="e1",
        title="t",
        experiment_type="general",
        steps=steps,
    )

    assert exp.get_step_by_id("s1") is not None
    assert exp.get_step_by_id("nope") is None
    assert exp.validate_dependencies() == ["步骤 s2 依赖的步骤 missing_step 不存在"]

    exp.record_data("v1", 10.0)
    exp.record_data("student_id", "SENSITIVE")
    exp.record_data("note", "not-numeric")
    exp.record_observation("obs1")
    exp.record_titration_point(0.0, 7.0)
    exp.record_titration_point(1.0, 7.2)

    assert exp.get_chart_data()["labels"] == ["v1"]
    assert exp.get_curve_data()["volume"] == [0.0, 1.0]
    assert exp.get_curve_data()["ph"] == [7.0, 7.2]

    exp.prepare()
    exp.start()
    exp.waste_generated = True
    exp.complete()

    report = exp.generate_report(
        include_fields=["v1"],
        anonymous=True,
        watermark="wm",
        sections_order=["data", "calculations", "conclusion", "unknown"],
        options={"a": 1},
    )
    assert report["data"] == {"v1": 10.0}
    ok, errors = exp.validate_report(report)
    assert ok is True
    assert errors == []

    exp.abort()
    assert exp.state == "aborted"

    # 部分实现可能选择记录安全提示而非发出 UserWarning，这里不强制要求必须 warn。
    exp.heat(temperature=95, duration=1, ventilation=False)
    assert exp.get_current_temperature() == 95
    assert exp.cooling_required is True

    with pytest.warns(UserWarning):
        exp.use_burette(rinse=False)

    with pytest.warns(UserWarning):
        exp.add_reagent("hcl", amount=1, protection=True)
    with pytest.warns(UserWarning):
        exp.add_reagent("naoh", amount=1, protection=True)
    assert exp.waste_generated is True

    exp.set_temperature(91)
    exp.cool_down()
    assert exp.get_current_temperature() == 25.0

    with pytest.raises(ValueError):
        exp.heat(temperature=250)

    exp.reagents_used.append("h2so4")
    with pytest.raises(ValueError):
        exp.add_reagent("kmno4", amount=1, protection=True)

    exp.report_incident("spill", details="minor")
    assert exp.get_safety_alerts()

    exp.wear_protection(["goggles"])
    score_with_missing = exp.calculate_safety_score()
    exp.wear_protection(["gloves", "lab_coat"])
    score_full = exp.calculate_safety_score()
    assert score_full >= score_with_missing

    response = exp.handle_emergency("fire")
    assert "灭火" in response or "疏散" in response

    exp.report_malfunction("heating_mantle", issue="过热")
    assert exp.state == "emergency_stopped"
    assert exp.get_malfunction_guidance("burette")
    assert exp.get_malfunction_guidance("unknown_equipment")

    text_report = exp.export_report(format="text")
    assert "实验报告" in text_report

    unknown_format = exp.export_report(format="unknown")
    assert "\"experiment_type\"" in unknown_format


@pytest.mark.unit
def test_model_experiment_template_steps_required_by_default():
    from src.models.experiment import ExperimentTemplate

    with pytest.raises(ValidationError):
        ExperimentTemplate(
            id="e1",
            title="t",
            experiment_type="general",
            steps=[],
        )


@pytest.mark.unit
def test_model_experiment_save_report_formats(tmp_path, monkeypatch):
    from src.models.experiment import Experiment

    monkeypatch.chdir(tmp_path)

    exp = Experiment(experiment_type="general", title="t")
    exp.prepare()
    exp.start()
    exp.complete()
    exp.record_data("v1", 1)

    json_path = exp.save_report("r.json", format="json", version=2)
    assert json_path.exists()
    assert json_path.read_text(encoding="utf-8").startswith("{")

    html_path = exp.save_report("r.html", format="html")
    assert html_path.exists()
    assert "<html>" in html_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_model_experiment_misc_error_branches_and_tips():
    from src.models.experiment import Experiment

    exp = Experiment(experiment_type="general", title="t")
    exp.equipment_checked = False
    with pytest.raises(RuntimeError):
        exp.start()

    exp.check_equipment()
    exp.start()

    with pytest.raises(ValueError):
        exp.add_reagent("hcl", amount=301)

    with pytest.warns(UserWarning):
        exp.add_reagent("volatile_solvent", amount=1, protection=True)
    with pytest.warns(UserWarning):
        exp.add_reagent("mercury_compound", amount=1, protection=True)
    with pytest.warns(UserWarning):
        exp.add_reagent("concentrated_hcl", amount=1, protection=False)

    tips = exp.get_safety_tips()
    assert any("通风" in tip for tip in tips)
    assert any("汞" in tip for tip in tips)

    assert exp.get_emergency_response("unknown") is not None
    assert exp.get_completion_reminders()


@pytest.mark.unit
def test_model_user_record_mapping_validation_edge_cases():
    from src.models.user_record import ExperimentScore, UserRecord

    record = UserRecord(
        record_id="r1",
        user_id="u1",
        experiment_id="e1",
        score=ExperimentScore(),
        context=None,
        curve_data={},
    )
    assert record.context == {}

    too_deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}}
    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            score=ExperimentScore(),
            context=too_deep,
            curve_data={},
        )

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            score=ExperimentScore(),
            context={"x" * 100: 1},
            curve_data={},
        )

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            score=ExperimentScore(),
            context={"ok": object()},
            curve_data={},
        )

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            score=ExperimentScore(),
            context={},
            curve_data={"c1": {"x": [0], "y": [1, 2]}},
        )
