"""Unit tests for /healthz and /readyz handlers."""

from __future__ import annotations

from pathlib import Path

from src import __version__ as APP_VERSION
from src.api.server import APIRequestHandler


def test_healthz_reports_build_and_checks(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "z" * 32)
    monkeypatch.setenv("VCL_HEALTH_DIR", str(tmp_path / "health"))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    captured: dict = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type(
        "S",
        (),
        {
            "template_engine": type("E", (), {"templates_dir": templates_dir})(),
            "storage": type("St", (), {"base_dir": data_dir})(),
        },
    )()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_healthz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 200
    assert captured["data"]["version"] == APP_VERSION
    assert captured["data"]["build"]["version"] == APP_VERSION
    assert captured["data"]["checks"]["disk_writable"]["ok"] is True


def test_readyz_defaults_to_ready_when_optional_deps_skipped(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VCL_READY_CHECK_DB", raising=False)
    monkeypatch.delenv("REDIS_ENABLED", raising=False)

    captured: dict = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type("S", (), {})()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_readyz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 200
    assert captured["data"]["status"] == "ready"
    assert captured["data"]["version"] == APP_VERSION


def test_healthz_does_not_require_admin_secret_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.delenv("VCL_ADMIN_SECRET_KEY", raising=False)
    monkeypatch.setenv("VCL_HEALTH_DIR", str(tmp_path / "health"))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    captured: dict = {}
    handler = object.__new__(APIRequestHandler)
    handler.headers = {}
    handler.server = type(
        "S",
        (),
        {
            "template_engine": type("E", (), {"templates_dir": templates_dir})(),
            "storage": type("St", (), {"base_dir": data_dir})(),
        },
    )()

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture  # type: ignore[attr-defined]
    APIRequestHandler._handle_healthz(handler, trace_id="t")  # type: ignore[arg-type]

    assert captured["status"] == 200
    assert captured["data"]["checks"]["secrets"]["admin"]["ok"] is True
    assert captured["data"]["checks"]["secrets"]["admin"]["detail"] == "skipped"
