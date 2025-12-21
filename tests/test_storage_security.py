import os
import tempfile
from pathlib import Path

import pytest

from src.models.user_record import UserRecord
from src.storage.database_manager import DatabaseManager
from src.storage.json_store import JSONStore
from src.storage.tinydb_store import TINYDB_AVAILABLE, TinyDBStore


def _posix_only():
    return os.name == "posix"


@pytest.mark.unit
def test_storage_symlink_attack_rejected_kv_save():
    if not _posix_only():
        pytest.skip("symlink 权限/语义依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir, enable_cache=False)
        outside = Path(tmpdir) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        target = store._resolve_key_path("evil_key")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        os.symlink(str(outside), str(target))

        assert store.save("evil_key", {"x": 1}) is False


@pytest.mark.unit
def test_storage_symlink_attack_rejected_kv_load():
    if not _posix_only():
        pytest.skip("symlink 权限/语义依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir, enable_cache=False)
        outside = Path(tmpdir) / "outside.json"
        outside.write_text('{"data": "pwned"}', encoding="utf-8")

        target = store._resolve_key_path("evil_load", ensure_parent=True)
        if target.exists():
            target.unlink()
        os.symlink(str(outside), str(target))

        assert store.load("evil_load") is None


@pytest.mark.unit
def test_storage_backup_does_not_follow_symlinks():
    if not _posix_only():
        pytest.skip("symlink 权限/语义依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir, enable_cache=False)
        user_dir = store.base_dir / "user1"
        user_dir.mkdir(parents=True, exist_ok=True)

        (user_dir / "real.json").write_text("{}", encoding="utf-8")

        outside = Path(tmpdir) / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        os.symlink(str(outside), str(user_dir / "link.txt"))

        assert store.backup_data("b1") is True
        backed_up_link = store.backup_dir / "b1" / "user1" / "link.txt"
        assert backed_up_link.exists()
        assert backed_up_link.is_symlink()


@pytest.mark.unit
def test_storage_save_record_refuses_symlink_backup():
    if not _posix_only():
        pytest.skip("symlink 权限/语义依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir, enable_cache=False)
        record = UserRecord(user_id="test_user", experiment_id="e1", record_id="r1")
        assert store.save_record(record) is True

        user_dir = store._get_user_dir("test_user")
        record_files = list(user_dir.glob("*.json"))
        assert record_files
        record_file = record_files[0]

        outside = Path(tmpdir) / "outside_record.json"
        outside.write_text("{}", encoding="utf-8")
        record_file.unlink()
        os.symlink(str(outside), str(record_file))

        assert store.save_record(record) is False


@pytest.mark.unit
def test_storage_file_permissions_json_store():
    if not _posix_only():
        pytest.skip("权限位检查依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir, enable_cache=False)
        record = UserRecord(user_id="test_user", experiment_id="e1", record_id="r1")
        assert store.save_record(record) is True
        store.set("a", 1)

        assert (store.base_dir.stat().st_mode & 0o777) == 0o700
        assert (store._kv_dir.stat().st_mode & 0o777) == 0o700

        index_file = store._get_index_file("test_user")
        assert (index_file.stat().st_mode & 0o777) == 0o600
        config_file = store.base_dir / "config.json"
        assert (config_file.stat().st_mode & 0o777) == 0o600


@pytest.mark.unit
def test_storage_file_permissions_database_manager():
    if not _posix_only():
        pytest.skip("权限位检查依赖 POSIX")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "db" / "test.db"
        db = DatabaseManager(str(db_path))
        try:
            assert db_path.exists()
            assert (db_path.parent.stat().st_mode & 0o777) == 0o700
            assert (db_path.stat().st_mode & 0o777) == 0o600
        finally:
            db.close()


@pytest.mark.unit
def test_storage_tinydb_path_validation_rejects_symlink():
    if not _posix_only():
        pytest.skip("symlink 权限/语义依赖 POSIX")
    if not TINYDB_AVAILABLE:
        pytest.skip("TinyDB 未安装，跳过路径校验测试")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        real_db = tmpdir_path / "real.json"
        real_db.write_text("{}", encoding="utf-8")
        link_db = tmpdir_path / "link.json"
        os.symlink(str(real_db), str(link_db))

        with pytest.raises(ValueError):
            TinyDBStore(link_db)

