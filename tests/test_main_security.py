from pathlib import Path
from types import SimpleNamespace

from src.main import _redact_startup_error, _resolve_log_file_path


def test_resolve_log_file_path_blocks_traversal(tmp_path: Path) -> None:
    config = SimpleNamespace(
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="../pwn.log"),
    )
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)

    resolved = _resolve_log_file_path(config, project_root=project_root)
    assert resolved.is_relative_to((project_root / "logs").resolve())
    assert resolved.name == "app.log"


def test_resolve_log_file_path_accepts_name_under_logs(tmp_path: Path) -> None:
    config = SimpleNamespace(
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app2.log"),
    )
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)

    resolved = _resolve_log_file_path(config, project_root=project_root)
    assert resolved.is_relative_to((project_root / "logs").resolve())
    assert resolved.name == "app2.log"


def test_resolve_log_file_path_strips_logs_prefix(tmp_path: Path) -> None:
    config = SimpleNamespace(
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="logs/nested/app.log"),
    )
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)

    resolved = _resolve_log_file_path(config, project_root=project_root)
    assert resolved.is_relative_to((project_root / "logs").resolve())
    assert resolved.as_posix().endswith("/logs/nested/app.log")


def test_redact_startup_error_does_not_leak_message() -> None:
    exc = OSError("secret: /private/path/config.json")
    redacted = _redact_startup_error(exc)
    assert "private" not in redacted
    assert "secret" not in redacted
    assert "OSError" in redacted

