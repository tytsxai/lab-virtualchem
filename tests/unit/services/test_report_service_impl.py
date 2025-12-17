"""ReportServiceImpl 行为测试"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.contracts.report_service import (
    ExportFormat,
    ReportRequest,
    ReportServiceConfig,
    ReportType,
)
from src.interfaces.report import IReportExporter, IReportGenerator
from src.interfaces.report import ReportFormat as GeneratorReportFormat
from src.models.user_record import ExperimentScore, UserRecord
from src.services.report_service_impl import ReportServiceImpl


class DummyGenerator(IReportGenerator):
    """简单的模板记录器，便于断言"""

    def __init__(self, templates: dict[str, str] | None = None) -> None:
        self.templates = templates or {
            "experiment_basic": "{title}",
            "summary_overview": "{title}",
            "generic_template": "{title}",
        }
        self.generate_calls: list[dict[str, Any]] = []

    def generate(
        self,
        record: UserRecord,
        template: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        self.generate_calls.append(
            {"record": record, "template": template, "options": options}
        )
        resolved_template = template or next(iter(self.templates))
        return self.templates.get(resolved_template, "{title}")

    def set_template(self, template_name: str, template_content: str) -> None:
        self.templates[template_name] = template_content

    def list_templates(self) -> list[str]:
        return list(self.templates.keys())


class DummyExporter(IReportExporter):
    """无副作用导出器"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def export(
        self,
        content: str,
        output_path: Path,
        format: GeneratorReportFormat,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        self.calls.append(
            {
                "content": content,
                "output_path": output_path,
                "format": format,
                "metadata": metadata or {},
            }
        )
        return True

    def get_supported_formats(self) -> list[GeneratorReportFormat]:
        return [GeneratorReportFormat.HTML, GeneratorReportFormat.JSON]

    def validate_export(
        self, output_path: Path, format: GeneratorReportFormat
    ) -> tuple[bool, str]:
        return True, ""


class FakeRepository:
    """最小实现的仓储对象"""

    def __init__(self, record: UserRecord) -> None:
        self._record = record

    def get(self, record_id: str) -> UserRecord | None:
        if record_id == self._record.record_id:
            return self._record
        return None


def _build_service(
    tmp_path: Path, generator: DummyGenerator | None = None
) -> ReportServiceImpl:
    template_dir = tmp_path / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "outputs"
    config = ReportServiceConfig(
        template_dir=str(template_dir), output_dir=str(output_dir)
    )
    return ReportServiceImpl(
        generator or DummyGenerator(), DummyExporter(), None, config
    )


def test_get_available_templates_filters_by_report_type(tmp_path: Path) -> None:
    """确保 report_type 过滤生效，并将文件系统模板注册到生成器"""
    generator = DummyGenerator(
        {
            "experiment_basic": "{title}",
            "summary_overview": "{title}",
            "generic_template": "{title}",
        }
    )
    service = _build_service(tmp_path, generator)
    template_dir = Path(service.config.template_dir)
    summary_file = template_dir / "team_summary.json"
    summary_file.write_text(json.dumps({"report_type": "summary"}), encoding="utf-8")
    analysis_file = template_dir / "deep_analysis.md"
    analysis_file.write_text("report_type: analysis", encoding="utf-8")

    templates = service.get_available_templates(ReportType.SUMMARY)

    assert set(templates) == {"summary_overview", "team_summary"}
    assert "team_summary" in generator.templates  # 文件系统模板应被注册为可用模板


def test_get_available_templates_returns_all_when_no_match(tmp_path: Path) -> None:
    """没有匹配项时应回退到全部模板"""
    generator = DummyGenerator({"generic_one": "{title}", "generic_two": "{title}"})
    service = _build_service(tmp_path, generator)
    template_dir = Path(service.config.template_dir)
    (template_dir / "custom_template.md").write_text("plain content", encoding="utf-8")

    templates = service.get_available_templates(ReportType.PROGRESS)

    assert set(templates) == {"generic_one", "generic_two", "custom_template"}


def test_generate_report_uses_template_name(tmp_path: Path) -> None:
    """实验报告生成时应透传 template_name"""
    generator = DummyGenerator({"experiment_basic": "{title}"})
    record = UserRecord(
        record_id="rec-001",
        user_id="user-001",
        experiment_id="exp-1",
        experiment_title="Synthesis",
        score=ExperimentScore(total=90, scientific=30, procedural=30, safety=30),
    )
    repository = FakeRepository(record)
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    config = ReportServiceConfig(
        template_dir=str(template_dir), output_dir=str(tmp_path / "outputs")
    )
    service = ReportServiceImpl(generator, DummyExporter(), repository, config)
    request = ReportRequest(
        report_type=ReportType.EXPERIMENT,
        record_id=record.record_id,
        template_name="experiment_basic",
        format=ExportFormat.HTML,
    )

    response = service.generate_report(request)

    assert response.success
    assert generator.generate_calls, "应调用生成器"
    assert generator.generate_calls[-1]["template"] == "experiment_basic"
