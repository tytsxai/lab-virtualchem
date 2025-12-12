from __future__ import annotations

import json
from datetime import timedelta

import pytest

from src.utils.recovery import AutoSave, RecoveryManager


@pytest.fixture
def manager(tmp_path):
    backup_dir = tmp_path / "backups"
    mgr = RecoveryManager(backup_dir=str(backup_dir))
    mgr.max_backups_per_name = 2
    mgr.backup_retention_days = 1
    return mgr


def test_create_backup_persists_metadata_and_restores(manager):
    data = {"experiment": "A1", "temperature": 25}
    assert manager.create_backup(data, "experimentA")
    assert manager._metadata["backups"]  # metadata recorded

    entry = manager._metadata["backups"][0]
    assert entry["name"] == "experimentA"
    assert entry["checksum"]

    restored = manager.restore_latest("experimentA")
    assert restored == data

    listed = manager.list_backups("experimentA")
    assert listed and listed[0]["file"] == entry["filename"]


def test_create_backup_invalid_input_returns_false(manager):
    before = len(manager._metadata["backups"])
    assert manager.create_backup({"ok": True}, "") is False
    assert manager.create_backup([], "bad_data") is False
    assert len(manager._metadata["backups"]) == before


def test_cleanup_limits_backups_per_name(manager):
    for i in range(3):
        assert manager.create_backup({"run": i}, "limited")

    files = list(manager.backup_dir.glob("limited_*.json"))
    assert len(files) == manager.max_backups_per_name

    entries = [b for b in manager._metadata["backups"] if b["name"] == "limited"]
    assert len(entries) == manager.max_backups_per_name


def test_delete_old_backups_updates_metadata(manager):
    manager.max_backups_per_name = 10
    for i in range(3):
        assert manager.create_backup({"archive": i}, "archive")

    deleted = manager.delete_old_backups("archive", keep_count=1)
    assert deleted == 2

    files = list(manager.backup_dir.glob("archive_*.json"))
    assert len(files) == 1
    entries = [b for b in manager._metadata["backups"] if b["name"] == "archive"]
    assert len(entries) == 1


def test_export_backup_creates_copy(manager, tmp_path):
    assert manager.create_backup({"value": 42}, "exportable")
    destination = tmp_path / "exported.json"

    assert manager.export_backup("exportable", destination)
    assert destination.exists()

    original = manager.restore_latest("exportable")
    exported = json.loads(destination.read_text(encoding="utf-8"))
    assert exported == original


def test_auto_save_flow():
    auto = AutoSave(save_interval=5)
    assert auto.has_unsaved_changes() is False
    assert auto.should_save() is False

    auto.mark_changed()
    assert auto.has_unsaved_changes() is True
    assert auto.should_save() is False

    auto.last_save_time -= timedelta(seconds=10)
    assert auto.should_save() is True

    auto.mark_saved()
    assert auto.has_unsaved_changes() is False
