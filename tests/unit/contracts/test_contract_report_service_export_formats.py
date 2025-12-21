from __future__ import annotations

from pathlib import Path

from src.contracts.report_service import (
    ExportFormat,
    ReportRequest,
    ReportResponse,
    ReportServiceConfig,
    ReportType,
)


def test_report_export_formats_have_expected_values() -> None:
    assert ExportFormat.PDF.value == "pdf"
    assert ExportFormat.HTML.value == "html"
    assert ExportFormat.DOCX.value == "docx"
    assert ExportFormat.MARKDOWN.value == "markdown"
    assert ExportFormat.JSON.value == "json"
    assert ExportFormat.CSV.value == "csv"


def test_report_service_config_defaults_are_stable() -> None:
    config = ReportServiceConfig()
    assert config.default_format == ExportFormat.PDF
    assert config.template_dir
    assert config.output_dir


def test_report_request_and_response_default_factories_are_isolated() -> None:
    req1 = ReportRequest(report_type=ReportType.SUMMARY)
    req2 = ReportRequest(report_type=ReportType.SUMMARY)
    req1.record_ids.append("r1")
    req1.options["k"] = "v"
    assert req2.record_ids == []
    assert req2.options == {}

    resp1 = ReportResponse(success=True)
    resp2 = ReportResponse(success=True)
    resp1.warnings.append("w1")
    assert resp2.warnings == []


def test_report_response_accepts_path_and_inline_content() -> None:
    response = ReportResponse(
        success=True,
        report_id="rep-1",
        file_path=Path("outputs/reports/rep-1.html"),
        content="<html/>",
    )
    assert response.file_path is not None
    assert response.content == "<html/>"

