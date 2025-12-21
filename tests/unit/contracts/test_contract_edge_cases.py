from __future__ import annotations

import json

import pytest

from src.contracts.maintenance_service import MaintenanceReportFormat
from src.contracts.plugin_service import PluginExecuteRequest, PluginStatus
from src.contracts.report_service import ExportFormat
from src.contracts.experiment_service import ExperimentStatus, StepSubmissionRequest
from src.contracts.storage_service import (
    InMemoryStorageService,
    QueryFilter,
    QueryOperator,
    QueryRequest,
    SaveRequest,
)
from src.core.maintenance.maintenance_service import MaintenanceServiceImpl


def test_export_format_pdf_value_is_pdf() -> None:
    assert ExportFormat.PDF.value == "pdf"


def test_experiment_and_plugin_contracts_are_importable() -> None:
    assert ExperimentStatus.NOT_STARTED.value == "not_started"
    assert StepSubmissionRequest(experiment_id="e1", step_id="s1", user_input={})

    assert PluginStatus.ACTIVE.value == "active"
    assert PluginExecuteRequest(plugin_name="p", action="run")


def test_inmemory_storage_save_requires_entity_type_and_entity() -> None:
    service = InMemoryStorageService()

    response = service.save(SaveRequest(entity_type="", entity={"id": "1"}))
    assert not response.success
    assert response.errors

    response = service.save(SaveRequest(entity_type="x", entity=None))
    assert not response.success
    assert response.errors


def test_inmemory_storage_query_sort_empty_is_safe() -> None:
    service = InMemoryStorageService()
    response = service.query(QueryRequest(entity_type="missing", sort_by="age"))
    assert response.success
    assert response.data == []
    assert response.total_count == 0
    assert response.has_more is False


def test_inmemory_storage_query_comparison_typeerror_is_caught() -> None:
    service = InMemoryStorageService()
    service.save(SaveRequest(entity_type="t", entity={"id": "1", "age": "not-a-number"}))

    response = service.query(
        QueryRequest(
            entity_type="t",
            filters=[QueryFilter(field="age", operator=QueryOperator.GT, value=1)],
        )
    )
    assert response.success
    assert response.data == []


def test_inmemory_storage_query_limit_zero_returns_empty_and_has_more() -> None:
    service = InMemoryStorageService()
    for idx in range(3):
        service.save(SaveRequest(entity_type="t", entity={"id": str(idx), "age": idx}))

    response = service.query(QueryRequest(entity_type="t", limit=0))
    assert response.success
    assert response.total_count == 3
    assert response.data == []
    assert response.has_more is True


def test_inmemory_storage_query_has_more_uses_offset_and_limit() -> None:
    service = InMemoryStorageService()
    for idx in range(3):
        service.save(SaveRequest(entity_type="t", entity={"id": str(idx), "age": idx}))

    first = service.query(QueryRequest(entity_type="t", sort_by="age", limit=2, offset=0))
    assert [item["id"] for item in first.data] == ["0", "1"]
    assert first.total_count == 3
    assert first.has_more is True

    second = service.query(QueryRequest(entity_type="t", sort_by="age", limit=2, offset=2))
    assert [item["id"] for item in second.data] == ["2"]
    assert second.total_count == 3
    assert second.has_more is False


def test_maintenance_export_report_accepts_enum(tmp_path) -> None:
    service = MaintenanceServiceImpl(base_path=str(tmp_path))
    service.history.append({"event": "ok"})

    output_path = tmp_path / "maintenance.json"
    assert service.export_report(str(output_path), format=MaintenanceReportFormat.JSON)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["history"][-1]["event"] == "ok"


def test_maintenance_export_report_rejects_unknown_format(tmp_path) -> None:
    service = MaintenanceServiceImpl(base_path=str(tmp_path))
    assert service.export_report(str(tmp_path / "out.txt"), format="txt") is False
