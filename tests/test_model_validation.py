import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError


def test_user_role_enum_constraint():
    from src.storage.database_manager import DatabaseManager

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(str(db_path))
        try:
            db.create_user(
                user_id="ok_user",
                username="OK",
                email="ok@example.com",
                role="student",
            )
            with pytest.raises(Exception):
                db.create_user(
                    user_id="bad_user",
                    username="BAD",
                    email="bad@example.com",
                    role="hacker",
                )
        finally:
            db.close()


def test_license_repr_does_not_leak_secret():
    from src.models.database import License

    license_key = "SECRET_LICENSE_KEY_1234567890"
    lic = License(
        license_key=license_key,
        user_id="u1",
        device_id="dev1",
    )
    rendered = repr(lic)
    assert "SECRET" not in rendered
    assert "LICENSE_KEY" not in rendered
    assert license_key not in rendered


def test_configuration_get_value_catches_json_decode_error():
    from src.models.database import Configuration

    cfg = Configuration(key="k1", value="{not-json", value_type="json", category="c1")
    assert cfg.get_value() == "{not-json"


def test_user_record_schema_validation_rejects_bad_keys_and_values():
    from src.models.user_record import ExperimentScore, UserRecord

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            experiment_title="t",
            started_at=datetime.now(),
            score=ExperimentScore(),
            context={"bad key": 1},
            curve_data={},
        )

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            experiment_title="t",
            started_at=datetime.now(),
            score=ExperimentScore(),
            context={"ok_key": {"nested": set([1])}},
            curve_data={},
        )


def test_user_record_curve_data_schema_validation():
    from src.models.user_record import ExperimentScore, UserRecord

    record = UserRecord(
        record_id="r1",
        user_id="u1",
        experiment_id="e1",
        experiment_title="t",
        started_at=datetime.now(),
        score=ExperimentScore(),
        context={},
        curve_data={
            "curve_1": {
                "x": [0, 1, 2],
                "y": [7.0, 7.1, 7.2],
                "x_label": "V",
                "y_label": "pH",
            }
        },
    )
    assert record.curve_data["curve_1"]["x"] == [0, 1, 2]

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

    with pytest.raises(ValidationError):
        UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="e1",
            experiment_title="t",
            started_at=datetime.now(),
            score=ExperimentScore(),
            context={},
            curve_data={"curve_1": {"x": [0], "y": [1, 2]}},
        )


def test_knowledge_content_length_limit():
    from src.models.knowledge import KnowledgeCard, KnowledgeType

    KnowledgeCard(
        id="k1",
        type=KnowledgeType.FAQ,
        title="t",
        content="ok",
    )
    with pytest.raises(ValidationError):
        KnowledgeCard(
            id="k2",
            type=KnowledgeType.FAQ,
            title="t",
            content="a" * 10001,
        )


def test_experiment_template_forbids_extra_fields():
    from src.models.experiment import ExperimentTemplate, Step

    with pytest.raises(ValidationError):
        ExperimentTemplate(
            id="e1",
            title="t",
            steps=[Step(id="s1", text="do")],
            unknown_field=123,
        )
