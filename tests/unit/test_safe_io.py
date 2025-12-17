from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.utils import enhanced_error_handler, safe_io
from src.utils.safe_io import SafeFileIO, safe_read_json, safe_read_text


@pytest.fixture(autouse=True)
def disable_error_dialogs():
    """Avoid GUI dialogs interfering with tests."""
    handler = enhanced_error_handler.EnhancedErrorHandler()
    previous = handler.show_dialogs
    handler.show_dialogs = False
    try:
        yield
    finally:
        handler.show_dialogs = previous


def test_read_file_returns_content(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("chemistry", encoding="utf-8")

    assert SafeFileIO.read_file(file_path) == "chemistry"


def test_read_file_missing_returns_default(tmp_path):
    missing = tmp_path / "missing.txt"
    assert SafeFileIO.read_file(missing, default="fallback") == "fallback"


def test_write_file_creates_dirs_and_backup(tmp_path):
    target = tmp_path / "nested" / "data.txt"
    SafeFileIO.write_file(target, "original", create_dirs=True)

    SafeFileIO.write_file(target, "updated", backup=True)
    backup = target.with_suffix(".txt.backup")

    assert target.read_text(encoding="utf-8") == "updated"
    assert backup.read_text(encoding="utf-8") == "original"


def test_json_read_and_write(tmp_path):
    data = {"volume": 250, "unit": "mL", "label": "缓冲液"}
    json_file = tmp_path / "config" / "settings.json"
    SafeFileIO.write_json(json_file, data, create_dirs=True)

    assert SafeFileIO.read_json(json_file) == data

    text = json_file.read_text(encoding="utf-8")
    assert "缓冲液" in text  # ensure ensure_ascii=False


def test_copy_file_and_overwrite_control(tmp_path):
    src = tmp_path / "source.txt"
    dst = tmp_path / "copies" / "copied.txt"
    src.write_text("sample", encoding="utf-8")

    assert SafeFileIO.copy_file(src, dst)
    assert dst.read_text(encoding="utf-8") == "sample"

    dst.write_text("keep-me", encoding="utf-8")
    assert SafeFileIO.copy_file(src, dst, overwrite=False) is False
    assert dst.read_text(encoding="utf-8") == "keep-me"


def test_delete_file_and_missing_behaviour(tmp_path):
    file_path = tmp_path / "to_delete.txt"
    file_path.write_text("temp", encoding="utf-8")

    assert SafeFileIO.delete_file(file_path)
    assert not file_path.exists()

    assert SafeFileIO.delete_file(tmp_path / "missing.txt", missing_ok=True)
    assert (
        SafeFileIO.delete_file(tmp_path / "missing_strict.txt", missing_ok=False)
        is False
    )


def test_create_directory_success(tmp_path):
    new_dir = tmp_path / "a" / "b"
    assert SafeFileIO.create_directory(new_dir)
    assert new_dir.exists()


def test_check_disk_space_threshold(monkeypatch, tmp_path):
    free_space = {"value": 50 * 1024 * 1024}

    def fake_disk_usage(_path):
        return SimpleNamespace(total=0, used=0, free=free_space["value"])

    monkeypatch.setattr(safe_io.shutil, "disk_usage", fake_disk_usage)

    assert SafeFileIO.check_disk_space(tmp_path, required_mb=100) is False

    free_space["value"] = 500 * 1024 * 1024
    assert SafeFileIO.check_disk_space(tmp_path, required_mb=100) is True


def test_read_with_retry_succeeds_after_transient_failures(monkeypatch):
    attempts = {"count": 0}

    def flaky_read(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("temporary issue")
        return "content"

    monkeypatch.setattr(SafeFileIO, "read_file", staticmethod(flaky_read))
    sleep_delays: list[float] = []
    monkeypatch.setattr(safe_io.time, "sleep", sleep_delays.append)

    result = SafeFileIO.read_with_retry("file.txt", max_retries=4, retry_delay=0.1)
    assert result == "content"
    assert attempts["count"] == 3
    assert sleep_delays == [0.1, 0.1]


def test_read_with_retry_raises_after_exhaustion(monkeypatch):
    attempts = {"count": 0}

    def always_fail(*_args, **_kwargs):
        attempts["count"] += 1
        raise OSError("fatal")

    monkeypatch.setattr(SafeFileIO, "read_file", staticmethod(always_fail))
    monkeypatch.setattr(safe_io.time, "sleep", lambda _delay: None)

    with pytest.raises(OSError):
        SafeFileIO.read_with_retry("file.txt", max_retries=2, retry_delay=0.1)

    assert attempts["count"] == 2


def test_safe_read_helpers_return_defaults(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("lab notes", encoding="utf-8")
    assert safe_read_text(text_file) == "lab notes"
    assert safe_read_text(tmp_path / "missing.txt", default="memo") == "memo"

    payload = {"ph": 7}
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")
    assert safe_read_json(json_file) == payload

    default = {"fallback": True}
    assert safe_read_json(tmp_path / "missing.json", default) is default
