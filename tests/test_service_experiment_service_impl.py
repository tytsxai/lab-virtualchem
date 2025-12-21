from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.contracts.experiment_service import (
    ExperimentRequest,
    ExperimentStatus,
    StepSubmissionRequest,
)
from src.models.experiment import ExperimentTemplate
from src.models.user_record import ExperimentScore, UserRecord
from src.services.experiment_service_impl import ExperimentServiceImpl


class _MemoryStorage:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.saved: list[tuple[str, Any]] = []

    def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:
        self.data[key] = value
        self.saved.append((key, value))
        return True

    def load(self, key: str) -> Any | None:
        return self.data.get(key)

    def delete(self, key: str) -> bool:  # pragma: no cover - not used
        return self.data.pop(key, None) is not None

    def exists(self, key: str) -> bool:  # pragma: no cover - not used
        return key in self.data

    def list_keys(self, prefix: str | None = None) -> list[str]:  # pragma: no cover
        if prefix is None:
            return list(self.data.keys())
        return [k for k in self.data if k.startswith(prefix)]

    def clear(self) -> bool:  # pragma: no cover - not used
        self.data.clear()
        return True


class _StepType(Enum):
    TEXT = "text"


@dataclass
class _Step:
    id: str
    content: str
    type: _StepType = _StepType.TEXT
    options: dict[str, Any] | None = None


class _FakeEngine:
    def __init__(self) -> None:
        self.initialized: tuple[ExperimentTemplate, str] | None = None
        self.started = False
        self._steps = [_Step(id="s1", content="c1"), _Step(id="s2", content="c2")]
        self._idx = 0
        self._record = UserRecord(
            record_id="r1",
            user_id="u1",
            experiment_id="t1",
            experiment_title="T",
            started_at=datetime.now() - timedelta(minutes=5),
            completed_at=datetime.now(),
            status="completed",
            score=ExperimentScore(total=80, scientific=30, procedural=30, safety=20),
        )
        self.closed = False

    def initialize(self, template: ExperimentTemplate, user_id: str) -> None:
        self.initialized = (template, user_id)

    def start(self) -> None:
        self.started = True

    def submit_step(self, user_input: dict[str, Any]) -> tuple[bool, str, Any | None]:
        if user_input.get("ok"):
            return True, "ok", None
        return False, "bad", None

    def next_step(self) -> bool:
        if self._idx < len(self._steps) - 1:
            self._idx += 1
            return True
        return False

    def get_current_step(self) -> _Step | None:
        return self._steps[self._idx]

    def get_progress(self) -> dict[str, Any]:
        return {
            "current_step_index": self._idx,
            "total_steps": len(self._steps),
            "completion_rate": self._idx / max(len(self._steps) - 1, 1),
            "total_mistakes": 0,
            "elapsed_time": 12,
        }

    def complete(self) -> UserRecord:
        return self._record

    def get_record(self) -> UserRecord:
        return self._record

    def close(self) -> None:
        self.closed = True


def test_experiment_service_create_start_submit_progress_complete_and_close():
    storage = _MemoryStorage()
    engine = _FakeEngine()

    template = ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}])
    storage.save("templates/t1", template)

    service = ExperimentServiceImpl(engine=engine, storage=storage)
    created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
    assert created.success is True
    assert created.status == ExperimentStatus.NOT_STARTED
    assert engine.initialized is not None

    started = service.start_experiment(created.experiment_id)
    assert started.success is True
    assert started.status == ExperimentStatus.IN_PROGRESS

    submit = service.submit_step(
        StepSubmissionRequest(
            experiment_id=created.experiment_id, step_id="s1", user_input={"ok": True}
        )
    )
    assert submit.success is True
    assert submit.passed is True
    assert submit.next_step_id == "s2"

    current = service.get_current_step(created.experiment_id)
    assert current is not None
    assert current["id"] == "s2"
    assert current["content"] == "c2"
    assert current["type"] == "text"

    progress = service.get_progress(created.experiment_id)
    assert progress is not None
    assert progress.total_steps == 2

    completed = service.complete_experiment(created.experiment_id)
    assert completed.success is True
    assert completed.status == ExperimentStatus.COMPLETED
    # default branch: persist to storage records/<user>/<exp_id>
    assert any(k.startswith("records/u1/") for k, _ in storage.saved)

    service.close()
    assert engine.closed is True


def test_experiment_service_create_fails_when_template_missing():
    service = ExperimentServiceImpl(engine=_FakeEngine(), storage=_MemoryStorage())
    resp = service.create_experiment(ExperimentRequest(user_id="u1", template_id="nope"))
    assert resp.success is False
    assert "模板不存在" in resp.message


def test_experiment_service_validate_experiment_collects_errors():
    service = ExperimentServiceImpl(engine=_FakeEngine(), storage=_MemoryStorage())
    template = ExperimentTemplate(id="", title="")
    ok, errors = service.validate_experiment(template)
    assert ok is False
    assert len(errors) >= 3


def test_experiment_service_persist_record_uses_record_store_when_available():
    class _RecordStore:
        def __init__(self) -> None:
            self.saved: list[UserRecord] = []

        def save_record(self, record: UserRecord) -> None:
            self.saved.append(record)

    storage = _MemoryStorage()
    record_store = _RecordStore()
    engine = _FakeEngine()
    storage.save("templates/t1", ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}]))
    service = ExperimentServiceImpl(engine=engine, storage=storage, record_store=record_store)

    created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
    assert created.success is True
    completed = service.complete_experiment(created.experiment_id)
    assert completed.success is True
    assert record_store.saved


def test_experiment_service_init_requires_engine_and_storage():
    storage = _MemoryStorage()
    try:
        ExperimentServiceImpl(storage=storage, engine_factory=None, engine=None)  # type: ignore[arg-type]
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "engine_factory" in str(exc) or "engine" in str(exc)

    try:
        ExperimentServiceImpl(engine=_FakeEngine(), storage=None)  # type: ignore[arg-type]
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "storage" in str(exc)


def test_experiment_service_handles_missing_experiment_ids_and_errors():
    storage = _MemoryStorage()
    engine = _FakeEngine()
    storage.save("templates/t1", ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}]))
    service = ExperimentServiceImpl(engine=engine, storage=storage)

    started = service.start_experiment("missing")
    assert started.success is False

    paused = service.pause_experiment("missing")
    assert paused.success is False

    resumed = service.resume_experiment("missing")
    assert resumed.success is False

    submit_missing = service.submit_step(
        StepSubmissionRequest(experiment_id="missing", step_id="s1", user_input={})
    )
    assert submit_missing.success is False

    assert service.get_current_step("missing") is None
    assert service.get_progress("missing") is None
    assert service.get_record("missing") is None


def test_experiment_service_submit_step_failure_does_not_advance():
    storage = _MemoryStorage()
    engine = _FakeEngine()
    storage.save("templates/t1", ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}]))
    service = ExperimentServiceImpl(engine=engine, storage=storage)

    created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
    assert created.success is True

    failed = service.submit_step(
        StepSubmissionRequest(
            experiment_id=created.experiment_id, step_id="s1", user_input={"ok": False}
        )
    )
    assert failed.success is True
    assert failed.passed is False
    assert failed.next_step_id is None


def test_experiment_service_load_template_from_engine_fallback_and_invalid_dict():
    from pathlib import Path

    class _TemplateEngine:
        def __init__(self, templates_dir: Any) -> None:
            self.templates_dir = templates_dir

        def load_experiment(self, path: Any) -> Any:  # noqa: ANN401
            # return a dict that cannot be coerced into ExperimentTemplate
            return {"id": "t1", "title": "T", "steps": "bad"}

    storage = _MemoryStorage()
    engine = _FakeEngine()
    service = ExperimentServiceImpl(
        engine=engine,
        storage=storage,
        template_engine=_TemplateEngine(templates_dir=Path(".")),
    )
    assert service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1")).success is False


def test_experiment_service_persist_record_handles_storage_failures():
    class _BrokenStorage(_MemoryStorage):
        def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:
            raise RuntimeError("boom")

    storage = _BrokenStorage()
    engine = _FakeEngine()
    storage.data["templates/t1"] = ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}])
    service = ExperimentServiceImpl(engine=engine, storage=storage)

    created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
    assert created.success is True
    # should not raise even if persist fails
    completed = service.complete_experiment(created.experiment_id)
    assert completed.success is True


def test_experiment_service_close_is_idempotent_and_calls_stop_if_present():
    class _EngineWithStop(_FakeEngine):
        def __init__(self) -> None:
            super().__init__()
            self.stopped = 0

        def stop(self) -> None:
            self.stopped += 1

    storage = _MemoryStorage()
    engine = _EngineWithStop()
    storage.save("templates/t1", ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}]))
    service = ExperimentServiceImpl(engine=engine, storage=storage)

    created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
    assert created.success is True

    service.close()
    service.close()
    assert engine.stopped == 1


def test_experiment_service_context_manager_and_error_branches():
    class _BoomEngine(_FakeEngine):
        def start(self) -> None:
            raise RuntimeError("boom")

        def submit_step(self, user_input: dict[str, Any]) -> tuple[bool, str, Any | None]:  # noqa: ARG002
            raise RuntimeError("boom")

    storage = _MemoryStorage()
    engine = _BoomEngine()
    storage.save("templates/t1", ExperimentTemplate(id="t1", title="T", steps=[{"id": "st1", "text": "x"}]))
    with ExperimentServiceImpl(engine=engine, storage=storage) as service:
        created = service.create_experiment(ExperimentRequest(user_id="u1", template_id="t1"))
        assert created.success is True

        started = service.start_experiment(created.experiment_id)
        assert started.success is False
        assert "启动实验失败" in started.message

        failed = service.submit_step(
            StepSubmissionRequest(experiment_id=created.experiment_id, step_id="s1", user_input={})
        )
        assert failed.success is False
        assert "提交失败" in failed.message
