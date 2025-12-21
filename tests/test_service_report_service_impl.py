from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.contracts.report_service import (
    ExportFormat,
    ReportRequest,
    ReportServiceConfig,
    ReportType,
)
from src.models.user_record import ExperimentScore, Mistake, UserRecord
from src.services.report_service_impl import ReportServiceImpl


class _FakeGenerator:
    def __init__(self) -> None:
        self._templates: dict[str, str] = {"experiment_builtin": "tpl"}
        self.generated: list[tuple[str, dict[str, Any] | None]] = []

    def generate(
        self,
        record: UserRecord,
        template: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        self.generated.append((record.record_id, options))
        name = template or "default"
        return f"<html><body>{name}:{record.record_id}</body></html>"

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def set_template(self, name: str, content: str) -> None:
        self._templates[name] = content


class _FakeExporter:
    def __init__(self) -> None:
        self.exports: list[Path] = []

    def export(
        self, content: str, output_path: Path, format: Any, metadata: dict[str, Any] | None = None
    ) -> bool:
        output_path.write_text(content, encoding="utf-8")
        self.exports.append(output_path)
        return True


class _Repo:
    def __init__(self, records: dict[str, UserRecord]) -> None:
        self.records = records

    def get(self, record_id: str) -> UserRecord | None:
        return self.records.get(record_id)

    def find(self, user_id: str) -> list[UserRecord]:
        return [r for r in self.records.values() if r.user_id == user_id]


def _record(record_id: str, *, user_id: str, score: int, exp_id: str = "exp") -> UserRecord:
    return UserRecord(
        record_id=record_id,
        user_id=user_id,
        experiment_id=exp_id,
        experiment_title="T",
        started_at=datetime.now() - timedelta(minutes=10),
        completed_at=datetime.now() - timedelta(minutes=1),
        status="completed",
        score=ExperimentScore(total=score, scientific=30, procedural=30, safety=20),
        mistakes_summary=[
            Mistake(step_id="s1", error_type="x", description="oops", severity="warning")
        ],
    )


def test_report_service_generate_report_experiment_and_export_report(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    repo = _Repo({"r1": _record("r1", user_id="u1", score=80)})
    config = ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path))
    service = ReportServiceImpl(generator=generator, exporter=exporter, record_repository=repo, config=config)

    resp = service.generate_report(
        ReportRequest(report_type=ReportType.EXPERIMENT, record_id="r1", format=ExportFormat.HTML)
    )
    assert resp.success is True
    assert resp.file_path is not None
    assert resp.file_path.exists()

    # export_report reads from cache first
    out2 = tmp_path / "exported.html"
    assert service.export_report("r1", out2, ExportFormat.HTML) is True
    assert out2.exists()
    assert "r1" in out2.read_text(encoding="utf-8")


def test_report_service_generate_report_handles_missing_record(tmp_path: Path):
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=_Repo({}),
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    resp = service.generate_report(
        ReportRequest(report_type=ReportType.EXPERIMENT, record_id="missing")
    )
    assert resp.success is False


def test_report_service_generate_comparison_and_summary(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    records = {
        "r1": _record("r1", user_id="u1", score=50, exp_id="exp_a"),
        "r2": _record("r2", user_id="u1", score=80, exp_id="exp_b"),
    }
    repo = _Repo(records)
    config = ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path))
    service = ReportServiceImpl(generator=generator, exporter=exporter, record_repository=repo, config=config)

    cmp = service.generate_report(
        ReportRequest(report_type=ReportType.COMPARISON, record_ids=["r1", "r2"], format=ExportFormat.MARKDOWN)
    )
    assert cmp.success is True
    assert cmp.file_path is not None
    assert cmp.file_path.exists()

    summary = service.generate_summary_report("u1", format=ExportFormat.MARKDOWN)
    assert summary.success is True


def test_report_service_get_available_templates_includes_fs_and_filters(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    (template_dir / "summary_custom.md").write_text(
        "report_type: summary\n# Summary", encoding="utf-8"
    )
    (template_dir / "analysis_custom.json").write_text(
        "{\"report_type\": \"analysis\"}", encoding="utf-8"
    )

    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(template_dir)),
    )

    all_templates = service.get_available_templates()
    assert "experiment_builtin" in all_templates
    assert "summary_custom" in all_templates
    assert "analysis_custom" in all_templates

    summaries = service.get_available_templates(ReportType.SUMMARY)
    assert "summary_custom" in summaries


def test_report_service_preview_report(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    repo = _Repo({"r1": _record("r1", user_id="u1", score=80)})
    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )

    html = service.preview_report(ReportRequest(report_type=ReportType.EXPERIMENT, record_id="r1"))
    assert "<html" in html
    assert "r1" in html


def test_report_service_export_report_can_load_from_filesystem(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    outdir = tmp_path / "out"
    outdir.mkdir()

    # simulate persisted report content
    (outdir / "r2.html").write_text("persisted", encoding="utf-8")

    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(outdir), template_dir=str(tmp_path)),
    )
    exported = tmp_path / "exported.html"
    assert service.export_report("r2", exported, ExportFormat.HTML) is True
    assert exported.read_text(encoding="utf-8") == "persisted"


def test_report_service_export_report_returns_false_when_missing(tmp_path: Path):
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    assert service.export_report("missing", tmp_path / "x.html", ExportFormat.HTML) is False


def test_report_service_preview_report_fallback_and_error(tmp_path: Path):
    class _BoomGenerator(_FakeGenerator):
        def generate(self, record: UserRecord, template: str | None = None, options: dict[str, Any] | None = None) -> str:  # noqa: ARG002
            raise RuntimeError("boom")

    repo = _Repo({"r1": _record("r1", user_id="u1", score=80)})
    service = ReportServiceImpl(
        generator=_BoomGenerator(),
        exporter=_FakeExporter(),
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    html = service.preview_report(ReportRequest(report_type=ReportType.EXPERIMENT, record_id="r1"))
    assert "预览失败" in html

    # missing record -> fallback template
    html2 = service.preview_report(ReportRequest(report_type=ReportType.EXPERIMENT, record_id="missing"))
    assert "无法预览报告" in html2


def test_report_service_template_type_inference_helpers(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # json with nested metadata.report_types
    (template_dir / "nested.json").write_text(
        "{\"metadata\": {\"report_types\": [\"summary\", \"analysis\"]}}", encoding="utf-8"
    )
    # yaml absent dependency -> should fallback to inline parsing for yaml if yaml is missing; here use md instead
    (template_dir / "inline.md").write_text("report_types: experiment, progress", encoding="utf-8")
    # invalid json -> fallback to inline extraction and name inference
    (template_dir / "bad.json").write_text("{not json", encoding="utf-8")

    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(template_dir)),
    )
    templates = service.get_available_templates()
    assert "nested" in templates
    assert "inline" in templates
    assert "bad" in templates

    summaries = service.get_available_templates(ReportType.SUMMARY)
    assert "nested" in summaries


def test_report_service_generate_report_catches_specific_exceptions(tmp_path: Path):
    class _FailingReportService(ReportServiceImpl):
        def generate_experiment_report(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise ValueError("bad args")

    service = _FailingReportService(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=_Repo({"r1": _record("r1", user_id="u1", score=80)}),
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    resp = service.generate_report(ReportRequest(report_type=ReportType.EXPERIMENT, record_id="r1"))
    assert resp.success is False
    assert "参数错误" in resp.message

    class _FailingReportService2(ReportServiceImpl):
        def generate_experiment_report(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise OSError("disk")

    service2 = _FailingReportService2(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=_Repo({"r1": _record("r1", user_id="u1", score=80)}),
        config=ReportServiceConfig(output_dir=str(tmp_path / "out2"), template_dir=str(tmp_path)),
    )
    resp2 = service2.generate_report(ReportRequest(report_type=ReportType.EXPERIMENT, record_id="r1"))
    assert resp2.success is False
    assert "文件操作失败" in resp2.message


def test_report_service_private_helpers_direct(tmp_path: Path):
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    assert service._convert_format(ExportFormat.JSON).value == "json"
    assert service._coerce_report_type("SUMMARY") == ReportType.SUMMARY
    assert service._name_matches_report_type("my_实验_report", ReportType.EXPERIMENT) is True
    assert service._name_matches_report_type("cmp_report", ReportType.COMPARISON) is True

    types = service._convert_to_report_types({"metadata": {"report_type": "analysis"}})
    assert ReportType.ANALYSIS in types


def test_report_service_load_templates_skips_bad_encoding(tmp_path: Path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "ok.md").write_text("report_type: summary", encoding="utf-8")
    # invalid utf-8 to force UnicodeDecodeError
    (template_dir / "bad.md").write_bytes(b"\xff\xfe\xff\xfe")

    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(template_dir)),
    )
    templates = service.get_available_templates()
    assert "ok" in templates
    assert "bad" not in templates


def test_report_service_generate_recommendations_and_differences(tmp_path: Path):
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )

    low = _record("r1", user_id="u1", score=10)
    low.score.safety = 0
    low.mistakes_summary = [Mistake(step_id="s1", error_type="x", description=str(i)) for i in range(10)]
    high = _record("r2", user_id="u1", score=90)
    high.score.safety = 50
    recs = service._generate_recommendations([low, high])
    assert any("整体分数偏低" in r for r in recs)
    assert any("错误较多" in r for r in recs)
    assert any("安全意识不足" in r for r in recs)

    diffs = service._calculate_differences([low, high])
    assert diffs["score_range"] == 80
    assert service._calculate_differences([low]) == {}


def test_report_service_generate_summary_empty_and_date_filtering(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()

    class _RepoFindAll:
        def __init__(self, records: list[UserRecord]) -> None:
            self._records = records

        def find_all(self) -> list[UserRecord]:
            return list(self._records)

    r_old = _record("old", user_id="u1", score=70)
    r_old.started_at = datetime(2000, 1, 1)
    r_new = _record("new", user_id="u1", score=80)
    r_new.started_at = datetime(2099, 1, 1)

    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=_RepoFindAll([r_old, r_new]),
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )

    empty = service.generate_summary_report("missing")
    assert empty.success is False

    filtered = service.generate_summary_report("u1", start_date="2099-01-01", end_date="2099-12-31", format=ExportFormat.MARKDOWN)
    assert filtered.success is True


def test_report_service_generate_comparison_requires_two_records(tmp_path: Path):
    generator = _FakeGenerator()
    exporter = _FakeExporter()
    repo = _Repo({"r1": _record("r1", user_id="u1", score=80)})
    service = ReportServiceImpl(
        generator=generator,
        exporter=exporter,
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    resp = service.generate_comparison_report(["r1"], format=ExportFormat.MARKDOWN)
    assert resp.success is False


def test_report_service_summary_content_and_mistake_analysis(tmp_path: Path):
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    records = [
        _record("r1", user_id="u1", score=10, exp_id="e1"),
        _record("r2", user_id="u1", score=20, exp_id="e1"),
        _record("r3", user_id="u1", score=30, exp_id="e2"),
    ]
    summary_data = {
        "user_id": "u1",
        "start_date": None,
        "end_date": None,
        "total_experiments": len(records),
        "completed_experiments": len(records),
        "average_score": 20.0,
        "total_time": 0.0,
        "experiments_by_type": service._count_by_type(records),
        "score_trend": service._calculate_score_trend(records),
        "common_mistakes": service._analyze_common_mistakes(records),
    }
    content = service._generate_summary_content(summary_data)
    assert "学习汇总报告" in content
    assert "- e1:" in content


def test_report_service_export_report_handles_exporter_failure(tmp_path: Path):
    class _FailExporter(_FakeExporter):
        def export(self, content: str, output_path: Path, format: Any, metadata: dict[str, Any] | None = None) -> bool:  # noqa: ARG002
            raise RuntimeError("boom")

    outdir = tmp_path / "out"
    outdir.mkdir()
    (outdir / "r1.html").write_text("persisted", encoding="utf-8")
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FailExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(outdir), template_dir=str(tmp_path)),
    )
    assert service.export_report("r1", tmp_path / "x.html", ExportFormat.HTML) is False


def test_report_service_close_is_idempotent(tmp_path: Path):
    class _Closable(_FakeGenerator):
        def __init__(self) -> None:
            super().__init__()
            self.closed = 0

        def close(self) -> None:
            self.closed += 1

    gen = _Closable()
    exp = _FakeExporter()
    service = ReportServiceImpl(
        generator=gen,
        exporter=exp,
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    service.close()
    service.close()
    assert gen.closed == 1


def test_report_service_context_manager_and_close_swallow_exceptions(tmp_path: Path):
    class _BadCloseExporter(_FakeExporter):
        def close(self) -> None:
            raise RuntimeError("boom")

    class _BadCloseGenerator(_FakeGenerator):
        def close(self) -> None:
            raise RuntimeError("boom")

    with ReportServiceImpl(
        generator=_BadCloseGenerator(),
        exporter=_BadCloseExporter(),
        record_repository=None,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    ) as service:
        assert service.get_available_templates()  # exercise normal path too


def test_report_service_generate_experiment_report_export_failure_and_exception(tmp_path: Path):
    class _FalseExporter(_FakeExporter):
        def export(self, content: str, output_path: Path, format: Any, metadata: dict[str, Any] | None = None) -> bool:  # noqa: ARG002
            return False

    generator = _FakeGenerator()
    repo = _Repo({"r1": _record("r1", user_id="u1", score=80)})
    service = ReportServiceImpl(
        generator=generator,
        exporter=_FalseExporter(),
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    resp = service.generate_experiment_report(repo.get("r1"))  # type: ignore[arg-type]
    assert resp.success is False
    assert "报告导出失败" in resp.message

    class _BoomGenerator(_FakeGenerator):
        def generate(self, record: UserRecord, template: str | None = None, options: dict[str, Any] | None = None) -> str:  # noqa: ARG002
            raise RuntimeError("boom")

    service2 = ReportServiceImpl(
        generator=_BoomGenerator(),
        exporter=_FakeExporter(),
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out2"), template_dir=str(tmp_path)),
    )
    resp2 = service2.generate_experiment_report(repo.get("r1"))  # type: ignore[arg-type]
    assert resp2.success is False
    assert "生成实验报告失败" in resp2.message


def test_report_service_comparison_export_failure_and_exception(tmp_path: Path):
    class _FalseExporter(_FakeExporter):
        def export(self, content: str, output_path: Path, format: Any, metadata: dict[str, Any] | None = None) -> bool:  # noqa: ARG002
            return False

    repo = _Repo(
        {
            "r1": _record("r1", user_id="u1", score=10),
            "r2": _record("r2", user_id="u1", score=20),
        }
    )
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FalseExporter(),
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    resp = service.generate_comparison_report(["r1", "r2"], format=ExportFormat.MARKDOWN)
    assert resp.success is False
    assert "报告导出失败" in resp.message

    class _BoomComparison(ReportServiceImpl):
        def _generate_comparison_content(self, comparison_data: dict[str, Any]) -> str:  # noqa: ARG002
            raise RuntimeError("boom")

    service2 = _BoomComparison(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=repo,
        config=ReportServiceConfig(output_dir=str(tmp_path / "out2"), template_dir=str(tmp_path)),
    )
    resp2 = service2.generate_comparison_report(["r1", "r2"], format=ExportFormat.MARKDOWN)
    assert resp2.success is False
    assert "生成对比报告失败" in resp2.message


def test_report_service_load_user_records_find_by_and_exception(tmp_path: Path):
    class _RepoFindBy:
        def __init__(self, records: list[UserRecord], boom: bool = False) -> None:
            self._records = records
            self._boom = boom

        def find_by(self, predicate):  # noqa: ANN001
            if self._boom:
                raise RuntimeError("boom")
            return [r for r in self._records if predicate(r)]

    repo = _RepoFindBy([_record("r1", user_id="u1", score=1), _record("r2", user_id="u2", score=2)])
    service = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=repo,  # type: ignore[arg-type]
        config=ReportServiceConfig(output_dir=str(tmp_path / "out"), template_dir=str(tmp_path)),
    )
    records = service._load_user_records("u1")
    assert [r.record_id for r in records] == ["r1"]

    service2 = ReportServiceImpl(
        generator=_FakeGenerator(),
        exporter=_FakeExporter(),
        record_repository=_RepoFindBy([], boom=True),  # type: ignore[arg-type]
        config=ReportServiceConfig(output_dir=str(tmp_path / "out2"), template_dir=str(tmp_path)),
    )
    assert service2._load_user_records("u1") == []
