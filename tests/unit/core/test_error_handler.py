"""ErrorHandler 单元测试"""

from __future__ import annotations

import pytest

from src.core import error_handler as error_handler_module
from src.core.common_exceptions import ErrorCategory as CoreCategory
from src.core.common_exceptions import ErrorSeverity as CoreSeverity
from src.core.common_exceptions import VirtualChemLabError
from src.core.error_handler import ErrorContext, ErrorHandler, safe_execute


def test_handle_virtual_error_updates_stats_and_triggers_callback() -> None:
    handler = ErrorHandler()
    triggered: list[str] = []

    def callback(error: VirtualChemLabError) -> None:
        triggered.append(error.message)

    handler.register_callback(CoreCategory.SYSTEM, callback)
    error = VirtualChemLabError(
        "boom", category=CoreCategory.SYSTEM, severity=CoreSeverity.LOW
    )

    result = handler.handle_error(error)

    assert result is None
    assert triggered == ["boom"]
    expected_key = f"{error.category.value}_{error.severity.value}"
    assert handler.get_error_stats()[expected_key] == 1


def test_handle_legacy_error_records_context() -> None:
    handler = ErrorHandler()
    context = ErrorContext(user_id="user-1", component="engine", operation="start")

    handler.handle_error(ValueError("bad input"), context)

    records = handler.get_error_records()
    assert len(records) == 1
    assert records[0].context.user_id == "user-1"
    stats = handler.get_error_statistics()
    assert stats["total_errors"] == 1
    assert stats["handled_errors"] == 1


def test_safe_execute_returns_fallback_and_tracks_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_handler = ErrorHandler()
    monkeypatch.setattr(error_handler_module, "_global_error_handler", local_handler)

    def boom() -> None:
        raise RuntimeError("unexpected")

    result = safe_execute(
        boom,
        fallback_value="ok",
        category=CoreCategory.SYSTEM,
        severity=CoreSeverity.HIGH,
    )

    assert result == "ok"
    key = "system_high"
    assert local_handler.get_error_stats()[key] == 1
