import json
from pathlib import Path
from types import MethodType

import pytest


PySide6 = pytest.importorskip("PySide6")
from PySide6 import QtCore, QtWidgets  # noqa: E402


from src.integration.feedback_integration import FeedbackIntegration  # noqa: E402


@pytest.mark.integration
def test_export_integration_report_blocks_path_traversal(tmp_path: Path) -> None:
    app_cls = getattr(QtCore, "QCoreApplication", None) or getattr(QtWidgets, "QApplication", None)
    if app_cls is not None:
        try:
            instance = app_cls.instance()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            instance = None
        if instance is None:
            try:
                _ = app_cls([])  # type: ignore[call-arg]
            except TypeError:
                _ = app_cls()  # type: ignore[call-arg]

    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    try:
        integration.generate_integration_report = MethodType(  # type: ignore[assignment]
            lambda self: {"ok": True}, integration
        )
        out = integration.export_integration_report(output_path="../../evil.json")
        assert out == ""
        assert not (tmp_path / "evil.json").exists()
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_export_integration_report_default_no_overwrite(tmp_path: Path) -> None:
    app_cls = getattr(QtCore, "QCoreApplication", None) or getattr(QtWidgets, "QApplication", None)
    if app_cls is not None:
        try:
            instance = app_cls.instance()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            instance = None
        if instance is None:
            try:
                _ = app_cls([])  # type: ignore[call-arg]
            except TypeError:
                _ = app_cls()  # type: ignore[call-arg]

    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    try:
        integration.generate_integration_report = MethodType(  # type: ignore[assignment]
            lambda self: {"value": 1}, integration
        )

        output_file = (tmp_path / "integration" / "report.json").resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps({"value": 0}), encoding="utf-8")

        out = integration.export_integration_report(output_path="report.json")
        assert out == ""
        assert json.loads(output_file.read_text(encoding="utf-8"))["value"] == 0
    finally:
        integration.shutdown()


@pytest.mark.integration
def test_export_integration_report_allows_relative_within_data_dir(tmp_path: Path) -> None:
    app_cls = getattr(QtCore, "QCoreApplication", None) or getattr(QtWidgets, "QApplication", None)
    if app_cls is not None:
        try:
            instance = app_cls.instance()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            instance = None
        if instance is None:
            try:
                _ = app_cls([])  # type: ignore[call-arg]
            except TypeError:
                _ = app_cls()  # type: ignore[call-arg]

    integration = FeedbackIntegration(data_dir=tmp_path / "integration")
    try:
        integration.generate_integration_report = MethodType(  # type: ignore[assignment]
            lambda self: {"ok": True}, integration
        )

        out = integration.export_integration_report(output_path="safe/report.json")
        assert out
        output_path = Path(out)
        assert output_path.is_file()
        assert output_path.resolve().is_relative_to((tmp_path / "integration").resolve())
    finally:
        integration.shutdown()
