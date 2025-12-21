from __future__ import annotations

import time

from src.contracts.maintenance_service import (
    CacheType,
    CleanupRequest,
    DiagnosisRequest,
    HealthCheckResponse,
    MaintenanceReportFormat,
    MaintenanceTaskResponse,
)
from src.interfaces.maintenance import IssueSeverity


def test_cache_type_and_report_format_enums_can_be_constructed_from_values() -> None:
    assert CacheType("disk") == CacheType.DISK
    assert MaintenanceReportFormat("csv") == MaintenanceReportFormat.CSV


def test_cleanup_request_default_cache_types_is_new_list_each_time() -> None:
    r1 = CleanupRequest()
    r2 = CleanupRequest()
    assert r1.cache_types == [CacheType.ALL]
    r1.cache_types.append(CacheType.DISK)
    assert r2.cache_types == [CacheType.ALL]


def test_diagnosis_request_default_severity_threshold_is_low() -> None:
    req = DiagnosisRequest()
    assert req.severity_threshold == IssueSeverity.LOW


def test_healthcheck_and_task_response_timestamps_are_not_shared() -> None:
    h1 = HealthCheckResponse(healthy=True, health_score=99.0)
    time.sleep(0.001)
    h2 = HealthCheckResponse(healthy=True, health_score=99.0)
    assert h1.timestamp != h2.timestamp

    t1 = MaintenanceTaskResponse(success=True)
    time.sleep(0.001)
    t2 = MaintenanceTaskResponse(success=True)
    assert t1.timestamp != t2.timestamp

