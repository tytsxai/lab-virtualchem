import json
import time


def test_disk_cache_backend_roundtrip_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.core.smart_cache_manager import DiskCacheBackend

    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(cache_dir)

    assert backend.set("key1", {"a": 1, "b": "x"}, ttl=10.0) is True
    assert backend.get("key1") == {"a": 1, "b": "x"}

    cache_files = list(cache_dir.glob("*.cache"))
    assert len(cache_files) == 1

    payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert payload["key"] == "key1"
    assert payload["value"] == {"a": 1, "b": "x"}


def test_disk_cache_backend_ttl_expiration_removes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.core.smart_cache_manager import DiskCacheBackend

    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(cache_dir)

    assert backend.set("expiring", {"ok": True}, ttl=0.01) is True
    cache_path = backend._get_cache_path("expiring")
    assert cache_path.exists()

    time.sleep(0.05)
    assert backend.get("expiring") is None
    assert cache_path.exists() is False


def test_disk_cache_backend_corrupt_file_is_cleaned_on_get(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.core.smart_cache_manager import DiskCacheBackend

    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(cache_dir)

    assert backend.set("key1", {"a": 1}, ttl=10.0) is True
    cache_path = backend._get_cache_path("key1")
    assert cache_path.exists()

    cache_path.write_text("not-json", encoding="utf-8")
    assert backend.get("key1") is None
    assert cache_path.exists() is False


def test_disk_cache_backend_non_json_serializable_value_is_skipped(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    from src.core.smart_cache_manager import DiskCacheBackend

    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(cache_dir)

    value = object()
    assert backend.set("key1", value, ttl=10.0) is False
    assert backend._get_cache_path("key1").exists() is False


def test_smart_cache_manager_set_succeeds_when_disk_cache_skips(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.core.smart_cache_manager import SmartCacheManager

    manager = SmartCacheManager({"cache_dir": tmp_path / "disk-cache"})

    value = object()
    assert manager.set("k", value, ttl=10.0) is True
    assert manager.get("k") is value
