from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest


PySide6 = pytest.importorskip("PySide6")
from PySide6 import QtCore, QtWidgets  # noqa: E402
from PySide6.QtCore import QObject, Signal  # noqa: E402

from src.integration.feedback_integration import FeedbackIntegration  # noqa: E402


@dataclass
class _Processed:
    auto_category: str
    auto_priority: str = "low"
    urgency_score: int = 0


class _FakeFeedbackProcessor(QObject):
    feedback_processed = Signal(str, dict)
    escalation_required = Signal(str, dict)

    def __init__(self, processed: _Processed | None = None) -> None:
        super().__init__()
        self._processed = processed

    def process_feedback(self, feedback: dict) -> _Processed | None:  # noqa: ANN401
        return self._processed

    def get_processing_stats(self) -> dict:
        return {"total_processed": 1}


class _FakeAnalytics(QObject):
    insight_generated = Signal(dict)
    nps_updated = Signal(float)

    def __init__(self, *, feedbacks: list[dict] | None = None) -> None:
        super().__init__()
        self.feedbacks = feedbacks or []
        self.insights: list[dict] = []
        self.segments: list[dict] = []


class _FakeABTesting(QObject):
    experiment_completed = Signal(str, dict)

    def __init__(self) -> None:
        super().__init__()
        self.experiments: dict[str, object] = {}
        self.active_experiments: dict[str, object] = {}
        self._seq = 0

    def create_experiment(self, **kwargs) -> str:  # noqa: ANN003
        self._seq += 1
        experiment_id = f"exp_{self._seq}"
        self.experiments[experiment_id] = kwargs
        self.active_experiments[experiment_id] = kwargs
        return experiment_id


class _FakeIterationManager(QObject):
    feature_proposed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.feature_requests: dict = {}
        self.bug_fixes: dict = {}
        self.improvements: dict = {}
        self.iterations: dict = {}

    def propose_feature_from_feedback(self, feedbacks: list[dict]) -> str:  # noqa: ARG002
        return "feat_1"

    def report_bug_from_feedback(self, feedback: dict) -> str:  # noqa: ARG002
        return "bug_1"

    def create_improvement_from_insights(self, insights: list[dict]) -> list[str]:  # noqa: ARG002
        return ["imp_1"]

    def save_feature(self, feature) -> None:  # noqa: ANN001, ARG002
        return None


@pytest.fixture(autouse=True)
def _qt_app() -> None:
    app_cls = getattr(QtCore, "QCoreApplication", None) or getattr(QtWidgets, "QApplication", None)
    if app_cls is None:
        return None
    try:
        instance = app_cls.instance()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        instance = None
    if instance is None:
        try:
            app_cls([])  # type: ignore[call-arg]
        except TypeError:
            app_cls()  # type: ignore[call-arg]


@pytest.mark.integration
def test_export_integration_report_sanitizes_absolute_output_path(tmp_path: Path) -> None:
    data_dir = tmp_path / "integration"
    outside = tmp_path / "outside.json"

    integration = FeedbackIntegration(data_dir=data_dir)
    try:
        integration.generate_integration_report = lambda: {"ok": True}  # type: ignore[method-assign]
        out = integration.export_integration_report(output_path=str(outside))
        assert out
        assert not outside.exists()
        out_path = Path(out)
        assert out_path.is_file()
        assert out_path.resolve().is_relative_to(data_dir.resolve())
        assert out_path.name == "outside.json"
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_export_integration_report_overwrite_true(tmp_path: Path) -> None:
    data_dir = tmp_path / "integration"
    integration = FeedbackIntegration(data_dir=data_dir)
    try:
        target = data_dir / "report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"value": 0}), encoding="utf-8")

        integration.generate_integration_report = lambda: {"value": 1}  # type: ignore[method-assign]
        out = integration.export_integration_report(output_path="report.json", overwrite=True)
        assert Path(out).resolve() == target.resolve()
        assert json.loads(target.read_text(encoding="utf-8"))["value"] == 1
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_export_integration_report_default_creates_file(tmp_path: Path) -> None:
    data_dir = tmp_path / "integration"
    integration = FeedbackIntegration(data_dir=data_dir)
    try:
        integration.generate_integration_report = lambda: {"hello": "world"}  # type: ignore[method-assign]
        out = integration.export_integration_report()
        assert out
        out_path = Path(out)
        assert out_path.is_file()
        assert out_path.suffix == ".json"
        assert out_path.resolve().is_relative_to(data_dir.resolve())
        assert json.loads(out_path.read_text(encoding="utf-8"))["hello"] == "world"
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_shutdown_stops_timer_and_is_idempotent(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    timer = integration.sync_timer
    try:
        assert timer.isActive()
        integration.shutdown()
        assert not timer.isActive()
        integration.shutdown()
        assert not timer.isActive()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_process_feedback_workflow_creates_bug_and_ab_test(tmp_path: Path) -> None:
    processed = _Processed(auto_category="bug_report", auto_priority="critical", urgency_score=99)
    processor = _FakeFeedbackProcessor(processed)
    analytics = _FakeAnalytics()
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()

    integration = FeedbackIntegration(
        feedback_processor=processor,
        analytics=analytics,
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    triggered: list[tuple[str, dict]] = []
    integration.workflow_triggered.connect(lambda name, data: triggered.append((name, data)))
    try:
        feedback = {"feedback_id": "f1", "title": "Crash", "content": "app crash"}
        result = integration.process_feedback_workflow(feedback)
        types = {a["type"] for a in result["actions"]}
        assert "bug_created" in types
        assert "ab_test_created" in types
        assert triggered and triggered[0][0] == "feedback_processing"
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_process_feedback_workflow_proposes_feature_when_similar_enough(tmp_path: Path) -> None:
    processed = _Processed(auto_category="feature_request", auto_priority="medium", urgency_score=0)
    processor = _FakeFeedbackProcessor(processed)
    analytics = _FakeAnalytics(
        feedbacks=[
            {"feedback_id": "f2", "content": "please add export report button"},
            {"feedback_id": "f3", "content": "add export report feature"},
        ]
    )
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()

    integration = FeedbackIntegration(
        feedback_processor=processor,
        analytics=analytics,
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    try:
        integration.automation_rules["auto_create_feature"]["min_feedback_count"] = 2
        feedback = {"feedback_id": "f1", "content": "add export report option"}
        result = integration.process_feedback_workflow(feedback)
        assert {"type": "feature_proposed", "id": "feat_1"} in result["actions"]
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_init_without_data_dir_falls_back_when_get_config_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.integration.feedback_integration.get_config",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    integration = FeedbackIntegration()
    try:
        assert integration.data_dir.resolve().is_relative_to(tmp_path.resolve())
        assert integration.data_dir.is_dir()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_process_feedback_workflow_emits_error_on_exception(tmp_path: Path) -> None:
    class _BoomProcessor(_FakeFeedbackProcessor):
        def process_feedback(self, feedback: dict) -> _Processed | None:  # noqa: ARG002
            raise RuntimeError("explode")

    integration = FeedbackIntegration(
        feedback_processor=_BoomProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=_FakeABTesting(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    errors: list[str] = []
    integration.integration_error.connect(errors.append)
    try:
        assert integration.process_feedback_workflow({"feedback_id": "f1"}) == {}
        assert errors and "explode" in errors[0]
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_create_bug_from_feedback_respects_flags_and_handles_errors(tmp_path: Path) -> None:
    class _IterationBoom(_FakeIterationManager):
        def report_bug_from_feedback(self, feedback: dict) -> str:  # noqa: ARG002
            raise RuntimeError("db down")

    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=_FakeABTesting(),
        iteration_manager=_IterationBoom(),
        data_dir=tmp_path / "integration",
    )
    try:
        processed = _Processed(auto_category="bug_report", auto_priority="low", urgency_score=0)
        integration.automation_rules["auto_report_bug"]["critical_priority_only"] = True
        assert integration.create_bug_from_feedback({"feedback_id": "f1"}, processed) == ""

        integration.automation_rules["auto_report_bug"]["enabled"] = False
        processed.auto_priority = "critical"
        assert integration.create_bug_from_feedback({"feedback_id": "f1"}, processed) == ""

        integration.automation_rules["auto_report_bug"]["enabled"] = True
        assert integration.create_bug_from_feedback({"feedback_id": "f1"}, processed) == ""
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_find_similar_feedbacks_includes_self_and_filters_by_similarity(tmp_path: Path) -> None:
    analytics = _FakeAnalytics(
        feedbacks=[
            {"feedback_id": "other", "content": "alpha beta gamma"},
            {"feedback_id": "same", "content": "should be skipped"},
        ]
    )
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("feature_request")),
        analytics=analytics,
        ab_testing=_FakeABTesting(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        feedback = {"feedback_id": "same", "content": "alpha beta"}
        similar = integration.find_similar_feedbacks(feedback)
        assert similar[0]["feedback_id"] == "same"
        assert any(item.get("feedback_id") == "other" for item in similar)
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_feedback_processed_triggers_human_review(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    triggered: list[tuple[str, dict]] = []
    integration.workflow_triggered.connect(lambda name, data: triggered.append((name, data)))
    try:
        integration.on_feedback_processed(
            "f1", {"auto_category": "x", "requires_human_review": True}
        )
        assert triggered and triggered[0][0] == "human_review_required"
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_nps_updated_negative_emits_alert(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    triggered: list[tuple[str, dict]] = []
    integration.workflow_triggered.connect(lambda name, data: triggered.append((name, data)))
    try:
        integration.on_nps_updated(-1.0)
        assert any(name == "nps_alert" for name, _ in triggered)
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_generate_report_and_sync_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _FakeFeedbackProcessor(_Processed("bug_report"))
    analytics = _FakeAnalytics()
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()
    integration = FeedbackIntegration(
        feedback_processor=processor,
        analytics=analytics,
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    try:
        report = integration.generate_integration_report()
        assert report["feedback_processing"]["total_processed"] == 1
        assert report["analytics"]["total_feedbacks"] == 0

        monkeypatch.setattr(processor, "get_processing_stats", lambda: (_ for _ in ()).throw(RuntimeError("nope")))
        integration.sync_data()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_create_ab_test_from_feedback_disabled_and_min_score(tmp_path: Path) -> None:
    processed = _Processed(auto_category="bug_report", auto_priority="critical", urgency_score=10)
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(processed),
        analytics=_FakeAnalytics(),
        ab_testing=_FakeABTesting(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        integration.automation_rules["auto_create_ab_test"]["enabled"] = False
        assert integration.create_ab_test_from_feedback({"feedback_id": "f1"}, processed) == ""

        integration.automation_rules["auto_create_ab_test"]["enabled"] = True
        integration.automation_rules["auto_create_ab_test"]["min_impact_score"] = 50
        processed.urgency_score = 49
        assert integration.create_ab_test_from_feedback({"feedback_id": "f1"}, processed) == ""
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_create_ab_test_from_insight_happy_path(tmp_path: Path) -> None:
    ab_testing = _FakeABTesting()
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=ab_testing,
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        insight = {
            "insight_id": 1,
            "title": "Improve UI",
            "description": "users struggle",
            "insight_type": "negative",
            "impact_score": 80,
            "suggested_actions": ["tweak button"],
        }
        exp_id = integration.create_ab_test_from_insight(insight)
        assert exp_id
        assert exp_id in ab_testing.experiments
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_add_ab_result_to_iteration_handles_missing_winner_and_missing_experiment(
    tmp_path: Path,
) -> None:
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    try:
        integration.add_ab_result_to_iteration("exp_x", {"winner_variant_id": None})
        integration.add_ab_result_to_iteration("exp_x", {"winner_variant_id": "v1"})
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_add_ab_result_to_iteration_creates_feature_request(tmp_path: Path) -> None:
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    try:
        ab_testing.experiments["exp_1"] = SimpleNamespace(name="Test Exp")
        integration.add_ab_result_to_iteration(
            "exp_1", {"winner_variant_id": "v1", "total_participants": 1000}
        )
        assert any(str(k).startswith("feat_ab_") for k in iteration_manager.feature_requests)
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_init_without_data_dir_uses_config_user_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Paths:
        user_data = str(tmp_path / "ud")

    class _Cfg:
        paths = _Paths()

    monkeypatch.setattr("src.integration.feedback_integration.get_config", lambda: _Cfg())
    integration = FeedbackIntegration()
    try:
        assert integration.data_dir.resolve() == (tmp_path / "ud" / "integration").resolve()
        assert integration.data_dir.is_dir()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_shutdown_swallow_timer_errors(tmp_path: Path) -> None:
    class _Timeout:
        def disconnect(self, _fn) -> None:  # noqa: ANN001, ARG002
            raise RuntimeError("disconnect failed")

    class _BadTimer:
        timeout = _Timeout()

        def stop(self) -> None:
            raise RuntimeError("stop failed")

    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    try:
        integration.sync_timer = _BadTimer()  # type: ignore[assignment]
        integration.shutdown()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_process_feedback_workflow_returns_empty_when_not_processed(tmp_path: Path) -> None:
    processor = _FakeFeedbackProcessor(processed=None)
    integration = FeedbackIntegration(
        feedback_processor=processor,
        analytics=_FakeAnalytics(),
        ab_testing=_FakeABTesting(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        result = integration.process_feedback_workflow({"feedback_id": "f1"})
        assert result["feedback_id"] == "f1"
        assert result["actions"] == []
        assert "processed" not in result
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_create_ab_test_from_feedback_handles_exception(tmp_path: Path) -> None:
    class _BoomAB(_FakeABTesting):
        def create_experiment(self, **kwargs) -> str:  # noqa: ANN003, ARG002
            raise RuntimeError("ab broke")

    processed = _Processed(auto_category="bug_report", auto_priority="critical", urgency_score=99)
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(processed),
        analytics=_FakeAnalytics(),
        ab_testing=_BoomAB(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        assert integration.create_ab_test_from_feedback({"feedback_id": "f1"}, processed) == ""
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_escalation_required_emits_workflow(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    triggered: list[tuple[str, dict]] = []
    integration.workflow_triggered.connect(lambda name, data: triggered.append((name, data)))
    try:
        integration.on_escalation_required("f1", {"reason": "urgent", "priority": "p1", "urgency": 99})
        assert triggered and triggered[0][0] == "escalation"
        assert triggered[0][1]["urgency"] == 99
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_insight_generated_creates_improvement_and_ab_test(tmp_path: Path) -> None:
    ab_testing = _FakeABTesting()
    iteration_manager = _FakeIterationManager()
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    completed: list[tuple[str, str]] = []
    integration.action_completed.connect(lambda name, value: completed.append((name, value)))
    called: list[dict] = []
    integration.create_ab_test_from_insight = lambda insight: (called.append(insight) or "exp_1")  # type: ignore[method-assign]
    try:
        integration.on_insight_generated({"title": "t", "impact_score": 70})
        assert ("improvements_created", "imp_1") in completed
        assert called
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_create_ab_test_from_insight_handles_exception(tmp_path: Path) -> None:
    class _BoomAB(_FakeABTesting):
        def create_experiment(self, **kwargs) -> str:  # noqa: ANN003, ARG002
            raise RuntimeError("ab broke")

    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=_BoomAB(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        assert integration.create_ab_test_from_insight({"title": "x", "impact_score": 80}) == ""
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_experiment_completed_respects_workflow_flag(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    called: list[tuple[str, dict]] = []
    integration.add_ab_result_to_iteration = lambda exp_id, results: called.append((exp_id, results))  # type: ignore[method-assign]
    try:
        integration.workflows["ab_result_to_iteration"] = True
        integration.on_experiment_completed("exp_1", {"winner_variant_id": "v1"})
        assert called

        called.clear()
        integration.workflows["ab_result_to_iteration"] = False
        integration.on_experiment_completed("exp_1", {"winner_variant_id": "v1"})
        assert not called
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_add_ab_result_to_iteration_medium_and_error(tmp_path: Path) -> None:
    class _BoomIteration(_FakeIterationManager):
        def save_feature(self, feature) -> None:  # noqa: ANN001, ARG002
            raise RuntimeError("disk full")

    ab_testing = _FakeABTesting()
    iteration_manager = _BoomIteration()
    integration = FeedbackIntegration(
        feedback_processor=_FakeFeedbackProcessor(_Processed("bug_report")),
        analytics=_FakeAnalytics(),
        ab_testing=ab_testing,
        iteration_manager=iteration_manager,
        data_dir=tmp_path / "integration",
    )
    try:
        ab_testing.experiments["exp_1"] = SimpleNamespace(name="Test Exp")
        integration.add_ab_result_to_iteration(
            "exp_1", {"winner_variant_id": "v1", "total_participants": 500}
        )
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_generate_report_handles_exception_and_sync_debug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _FakeFeedbackProcessor(_Processed("bug_report"))
    integration = FeedbackIntegration(
        feedback_processor=processor,
        analytics=_FakeAnalytics(),
        ab_testing=_FakeABTesting(),
        iteration_manager=_FakeIterationManager(),
        data_dir=tmp_path / "integration",
    )
    try:
        integration.sync_data()
        monkeypatch.setattr(processor, "get_processing_stats", lambda: (_ for _ in ()).throw(RuntimeError("nope")))
        assert integration.generate_integration_report() == {}
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_on_feature_proposed_smoke(tmp_path: Path) -> None:
    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    try:
        integration.on_feature_proposed("feat_1")
    finally:
        integration.shutdown()
