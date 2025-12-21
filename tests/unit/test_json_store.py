"""
JSON存储系统单元测试
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from unittest import mock
import threading
import importlib
from typing import Any

import pytest

from src.core.validation import ValidationError
from src.models.user_record import Mistake, StepRecord, UserRecord


@pytest.fixture(scope="session")
def json_store_module():
    # 延迟 import：确保 pytest-cov 已启动 coverage 采样。
    return importlib.import_module("src.storage.json_store")


@pytest.fixture(scope="session")
def JSONStoreCls(json_store_module):
    return json_store_module.JSONStore


@pytest.fixture(scope="session")
def DataIntegrityLevelEnum(json_store_module):
    return json_store_module.DataIntegrityLevel


@pytest.fixture
def temp_store(JSONStoreCls):
    """创建临时存储系统"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStoreCls(base_dir=tmpdir)
        yield store


@pytest.fixture
def sample_record():
    """创建示例记录"""
    now = datetime.now()
    record = UserRecord(
        user_id="test_user",
        experiment_id="test_exp",
        experiment_title="测试实验",
        record_id="test_record_001",
        started_at=now,
        completed_at=now,
    )
    record.score.total = 85
    record.status = "completed"

    # 添加步骤记录
    step = StepRecord(step_id="step1", passed=True, user_input={"value": 10})
    step.completed_at = now
    record.step_records.append(step)

    # 添加错误
    mistake = Mistake(
        step_id="step2",
        error_type="input_error",
        description="测试错误",
        severity="warning",
    )
    record.mistakes_summary.append(mistake)

    return record


class TestJSONStore:
    """JSON存储系统测试"""

    def test_initialization(self, temp_store):
        """测试初始化"""
        assert temp_store.base_dir.exists()
        assert temp_store.base_dir.is_dir()

    def test_save_record(self, temp_store, sample_record):
        """测试保存记录"""
        result = temp_store.save_record(sample_record)
        assert result is True

        # 验证文件存在
        user_dir = temp_store._get_user_dir(sample_record.user_id)
        assert user_dir.exists()

        # 验证索引文件存在
        index_file = temp_store._get_index_file(sample_record.user_id)
        assert index_file.exists()

    def test_load_record(self, temp_store, sample_record):
        """测试加载记录"""
        # 先保存
        temp_store.save_record(sample_record)

        # 再加载
        loaded = temp_store.load_record(sample_record.user_id, sample_record.record_id)

        assert loaded is not None
        assert loaded.user_id == sample_record.user_id
        assert loaded.experiment_id == sample_record.experiment_id
        assert loaded.score.total == sample_record.score.total
        assert len(loaded.step_records) == 1
        assert len(loaded.mistakes_summary) == 1

    def test_load_nonexistent_record(self, temp_store):
        """测试加载不存在的记录"""
        loaded = temp_store.load_record("test_user", "nonexistent")
        assert loaded is None

    def test_list_records_empty(self, temp_store):
        """测试列出空记录"""
        records = temp_store.list_records(user_id="test_user")
        assert len(records) == 0

    def test_list_records_single_user(self, temp_store, sample_record):
        """测试列出单个用户的记录"""
        temp_store.save_record(sample_record)

        records = temp_store.list_records(user_id="test_user")
        assert len(records) == 1
        assert records[0]["record_id"] == "test_record_001"

    def test_list_records_multiple(self, temp_store, sample_record):
        """测试列出多个记录"""
        # 保存第一个记录
        temp_store.save_record(sample_record)

        # 创建第二个记录
        record2 = UserRecord(
            user_id="test_user",
            experiment_id="test_exp2",
            experiment_title="测试实验2",
            record_id="test_record_002",
            completed_at=datetime.now(),
        )
        record2.score.total = 90
        temp_store.save_record(record2)

        records = temp_store.list_records(user_id="test_user")
        assert len(records) == 2

    def test_list_records_filter_by_experiment(self, temp_store, sample_record):
        """测试按实验筛选"""
        temp_store.save_record(sample_record)

        record2 = UserRecord(
            user_id="test_user",
            experiment_id="other_exp",
            experiment_title="其他实验",
            record_id="test_record_002",
        )
        temp_store.save_record(record2)

        # 筛选特定实验
        records = temp_store.list_records(user_id="test_user", experiment_id="test_exp")
        assert len(records) == 1
        assert records[0]["experiment_id"] == "test_exp"

    def test_list_records_limit(self, temp_store):
        """测试限制返回数量"""
        # 创建多个记录
        for i in range(5):
            record = UserRecord(
                user_id="test_user",
                experiment_id="test_exp",
                experiment_title=f"测试实验{i}",
                record_id=f"record_{i}",
                completed_at=datetime.now(),
            )
            temp_store.save_record(record)

        # 限制返回3条
        records = temp_store.list_records(user_id="test_user", limit=3)
        assert len(records) == 3

    def test_delete_record(self, temp_store, sample_record):
        """测试删除记录"""
        # 先保存
        temp_store.save_record(sample_record)

        # 验证存在
        assert temp_store.load_record("test_user", "test_record_001") is not None

        # 删除
        result = temp_store.delete_record("test_user", "test_record_001")
        assert result is True

        # 验证已删除
        assert temp_store.load_record("test_user", "test_record_001") is None

    def test_delete_nonexistent_record(self, temp_store):
        """测试删除不存在的记录"""
        result = temp_store.delete_record("test_user", "nonexistent")
        assert result is False

    def test_search_records(self, temp_store):
        """测试搜索记录"""
        # 创建多个记录
        record1 = UserRecord(
            user_id="test_user",
            experiment_id="titration",
            experiment_title="酸碱滴定",
            record_id="rec1",
        )
        temp_store.save_record(record1)

        record2 = UserRecord(
            user_id="test_user",
            experiment_id="recrystallization",
            experiment_title="重结晶",
            record_id="rec2",
        )
        temp_store.save_record(record2)

        # 搜索"滴定"
        results = temp_store.search_records("滴定", user_id="test_user")
        assert len(results) == 1
        assert results[0]["experiment_title"] == "酸碱滴定"

    def test_get_stats(self, temp_store):
        """测试统计信息"""
        # 创建多个记录
        for i in range(3):
            now = datetime.now()
            record = UserRecord(
                user_id="test_user",
                experiment_id="test_exp",
                experiment_title=f"测试实验{i}",
                record_id=f"rec{i}",
                started_at=now,
                completed_at=now,
            )
            record.score.total = 80 + i * 5  # 80, 85, 90
            temp_store.save_record(record)

        # 获取统计
        stats = temp_store.get_stats("test_user")

        assert stats["total_experiments"] == 3
        assert stats["average_score"] == 85.0  # (80 + 85 + 90) / 3
        assert stats["best_score"] == 90

    def test_update_record(self, temp_store, sample_record):
        """测试更新记录"""
        # 保存初始记录
        temp_store.save_record(sample_record)

        # 修改并保存
        sample_record.score.total = 95
        temp_store.save_record(sample_record)

        # 加载验证
        loaded = temp_store.load_record("test_user", "test_record_001")
        assert loaded.score.total == 95

        # 验证只有一条记录
        records = temp_store.list_records(user_id="test_user")
        assert len(records) == 1

    def test_index_ordering(self, temp_store):
        """测试索引按时间倒序"""
        import time

        # 创建多个记录，间隔保存
        for i in range(3):
            record = UserRecord(
                user_id="test_user",
                experiment_id="test_exp",
                experiment_title=f"测试实验{i}",
                record_id=f"rec{i}",
                completed_at=datetime.now(),
            )
            record.score.total = i * 10
            temp_store.save_record(record)
            time.sleep(0.1)  # 确保时间不同

        # 获取记录列表
        records = temp_store.list_records(user_id="test_user")

        # 验证倒序（最新的在前）
        assert records[0]["record_id"] == "rec2"
        assert records[1]["record_id"] == "rec1"
        assert records[2]["record_id"] == "rec0"

    def test_get_user_dir_rejects_path_traversal_user_id(self, temp_store):
        """user_id 应严格白名单校验，禁止路径遍历"""
        with pytest.raises(ValidationError):
            temp_store._get_user_dir("../evil")

    def _write_index(
        self, store: Any, user_id: str, record_id: str, filename: str
    ) -> Path:
        index_path = store._get_index_file(user_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_data = {
            "records": [
                {
                    "record_id": record_id,
                    "filename": filename,
                    "experiment_id": "exp",
                    "experiment_title": "t",
                    "started_at": datetime.now().isoformat(),
                    "finished_at": None,
                    "final_score": 0,
                    "status": "completed",
                }
            ]
        }
        index_path.write_text(json.dumps(index_data, ensure_ascii=False), encoding="utf-8")
        return index_path

    def test_load_record_rejects_traversal_filename(self, temp_store):
        """load_record 应拒绝索引中包含路径分隔符的 filename"""
        user_id = "test_user"
        record_id = "rec_traversal"

        outside_file = temp_store.base_dir / "outside.json"
        outside_record = UserRecord(
            user_id=user_id,
            experiment_id="exp",
            experiment_title="t",
            record_id=record_id,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        outside_file.write_text(
            json.dumps(outside_record.model_dump(mode="json"), ensure_ascii=False),
            encoding="utf-8",
        )

        self._write_index(temp_store, user_id, record_id, "../outside.json")

        loaded = temp_store.load_record(user_id, record_id)
        assert loaded is None

    def test_delete_record_rejects_traversal_filename(self, temp_store):
        """delete_record 应拒绝索引中包含路径分隔符的 filename"""
        user_id = "test_user"
        record_id = "rec_delete_traversal"

        outside_file = temp_store.base_dir / "outside_delete.json"
        outside_record = UserRecord(
            user_id=user_id,
            experiment_id="exp",
            experiment_title="t",
            record_id=record_id,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        outside_file.write_text(
            json.dumps(outside_record.model_dump(mode="json"), ensure_ascii=False),
            encoding="utf-8",
        )

        self._write_index(temp_store, user_id, record_id, "../outside_delete.json")

        result = temp_store.delete_record(user_id, record_id)
        assert result is False
        assert outside_file.exists()

    def test_delete_record_refuses_symlink(self, temp_store):
        """delete_record 删除前应检查不是符号链接"""
        user_id = "test_user"
        record_id = "rec_symlink"

        outside_file = temp_store.base_dir / "outside_symlink_target.json"
        outside_record = UserRecord(
            user_id=user_id,
            experiment_id="exp",
            experiment_title="t",
            record_id=record_id,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        outside_file.write_text(
            json.dumps(outside_record.model_dump(mode="json"), ensure_ascii=False),
            encoding="utf-8",
        )

        user_dir = temp_store._get_user_dir(user_id)
        link_path = user_dir / "link.json"
        link_path.symlink_to(outside_file)

        self._write_index(temp_store, user_id, record_id, "link.json")

        result = temp_store.delete_record(user_id, record_id)
        assert result is False
        assert outside_file.exists()
        assert link_path.exists()
        assert link_path.is_symlink()

    def test_kv_save_load_delete_and_cache(self, temp_store):
        """覆盖 IStorage 键值接口的读写/缓存路径"""
        assert temp_store.save("prefs/theme", {"mode": "dark"}) is True
        assert temp_store.exists("prefs/theme") is True

        first = temp_store.load("prefs/theme")
        assert first == {"mode": "dark"}

        # 第二次应走缓存命中路径
        second = temp_store.load("prefs/theme")
        assert second == {"mode": "dark"}

        assert temp_store.delete("prefs/theme") is True
        assert temp_store.load("prefs/theme") is None

    def test_kv_list_keys_prefix_records_and_clear(self, temp_store):
        """覆盖 list_keys(records/) 与 clear 分支"""
        assert temp_store.save("a/b", 1) is True
        assert temp_store.save("a/c", 2) is True

        assert temp_store.list_keys(prefix="a") == ["a/b", "a/c"]

        # records/ 前缀应映射到 base_dir
        assert temp_store.save("records/demo_user/demo_key", 123) is True
        keys = temp_store.list_keys(prefix="records/demo_user")
        assert "records/demo_user/demo_key" in keys

        assert temp_store.clear() is True
        assert temp_store.list_keys(prefix="a") == []

    def test_normalize_key_rejects_invalid(self, temp_store):
        with pytest.raises(ValueError):
            temp_store._normalize_key("")
        with pytest.raises(ValueError):
            temp_store._normalize_key("..")
        with pytest.raises(ValueError):
            temp_store._normalize_key("../evil")

    def test_cache_evict_oldest_entry(self, tmp_path, JSONStoreCls):
        """覆盖缓存淘汰逻辑"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), enable_cache=True, cache_size=1)
        assert store.save("k1", 1) is True
        assert store.save("k2", 2) is True  # 触发淘汰

        # load 只验证不崩溃且能返回最新数据
        assert store.load("k2") == 2

    def test_reject_symlink_escape_on_save(self, tmp_path, JSONStoreCls):
        """覆盖 _reject_symlink_path 的符号链接逃逸拒绝"""
        base_dir = tmp_path / "data"
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir(parents=True, exist_ok=True)
        store = JSONStoreCls(base_dir=str(base_dir))

        escape = base_dir / ".kv_store" / "escape"
        escape.parent.mkdir(parents=True, exist_ok=True)
        escape.symlink_to(outside_dir, target_is_directory=True)

        # 通过 symlink 指向 base_dir 外部，应被拒绝
        assert store.save("escape/evil", {"x": 1}) is False

    def test_load_record_file_with_compression(self, tmp_path, JSONStoreCls):
        """覆盖 _load_record_file 解压缩分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), enable_compression=True)
        payload = {"record_id": "r1", "user_id": "u", "experiment_id": "e", "started_at": datetime.now().isoformat()}
        compressed = store._compress_data(payload)
        path = tmp_path / "data" / "compressed.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(compressed, ensure_ascii=False), encoding="utf-8")

        loaded = store._load_record_file(path)
        assert loaded is not None
        assert loaded["record_id"] == "r1"

    def test_verify_data_integrity_modes(self, tmp_path, JSONStoreCls, DataIntegrityLevelEnum):
        """覆盖完整性校验 BASIC/STRONG/CRYPTOGRAPHIC 分支"""
        now_iso = datetime.now().isoformat()
        minimal = {"record_id": "r", "user_id": "u", "experiment_id": "e", "started_at": now_iso}

        store_basic = JSONStoreCls(base_dir=str(tmp_path / "basic"), integrity_level=DataIntegrityLevelEnum.BASIC)
        assert store_basic._verify_data_integrity(minimal, {}) is True
        assert store_basic._verify_data_integrity({"record_id": "r"}, {}) is False

        store_strong = JSONStoreCls(base_dir=str(tmp_path / "strong"), integrity_level=DataIntegrityLevelEnum.STRONG)
        assert store_strong._verify_data_integrity(minimal, {}) is True
        assert store_strong._verify_data_integrity({**minimal, "started_at": "not-a-date"}, {}) is False

        store_crypto = JSONStoreCls(base_dir=str(tmp_path / "crypto"), integrity_level=DataIntegrityLevelEnum.CRYPTOGRAPHIC)
        data_str = json.dumps(minimal, sort_keys=True, ensure_ascii=False)
        import hashlib

        good_hash = hashlib.sha256(data_str.encode()).hexdigest()
        assert store_crypto._verify_data_integrity(minimal, {"hash": good_hash}) is True
        assert store_crypto._verify_data_integrity(minimal, {"hash": "bad"}) is False
        assert store_crypto._verify_data_integrity(minimal, {}) is False

    def test_backup_and_cleanup_old_data(self, tmp_path, JSONStoreCls):
        """覆盖 backup_data 与 cleanup_old_data 的主要路径"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))

        user_id = "user1"
        user_dir = store._get_user_dir(user_id)
        record_path = user_dir / "old.json"
        record_path.write_text("{}", encoding="utf-8")

        index_path = store._get_index_file(user_id)
        index_data = {
            "records": [
                {
                    "record_id": "r_old",
                    "filename": "old.json",
                    "started_at": (datetime.now() - timedelta(days=365)).isoformat(),
                },
                {
                    "record_id": "r_bad_time",
                    "filename": "keep.json",
                    "started_at": "bad",
                },
            ]
        }
        (user_dir / "keep.json").write_text("{}", encoding="utf-8")
        index_path.write_text(json.dumps(index_data, ensure_ascii=False), encoding="utf-8")

        assert store.backup_data("b1") is True
        assert (store.backup_dir / "b1" / user_id / "old.json").exists()

        cleaned = store.cleanup_old_data(days=90)
        assert cleaned == 1
        assert not record_path.exists()
        assert (store.archive_dir / f"{user_id}_old.json").exists()

    def test_get_set_wrappers(self, temp_store):
        temp_store.set("k", "v")
        assert temp_store.get("k") == "v"
        assert temp_store.get("missing", default=123) == 123

    def test_safe_path_join_rejects_invalid_parts(self, tmp_path, JSONStoreCls):
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        base = store.base_dir

        with pytest.raises(ValidationError):
            store._safe_path_join(base)
        with pytest.raises(ValidationError):
            store._safe_path_join(base, None)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            store._safe_path_join(base, 123)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            store._safe_path_join(base, "   ")
        with pytest.raises(ValidationError):
            store._safe_path_join(base, "a/b", require_basename=True)
        with pytest.raises(ValidationError):
            store._safe_path_join(base, "../evil")

        # 正常拼接应返回 base_dir 下路径
        p = store._safe_path_join(base, "ok", require_basename=True)
        assert p.is_relative_to(base.resolve())

    def test_kv_load_payload_without_data_wrapper(self, temp_store):
        """load() 兼容历史格式（payload 不是 {data: ...}）"""
        path = temp_store._resolve_key_path("raw/value")
        path.write_text(json.dumps([1, 2, 3], ensure_ascii=False), encoding="utf-8")

        loaded = temp_store.load("raw/value")
        assert loaded == [1, 2, 3]

    def test_kv_delete_returns_false_on_unlink_error(self, temp_store):
        """delete() 遇到不可 unlink 的路径应返回 False"""
        path = temp_store._resolve_key_path("dir/entry")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()  # 目录而非文件，unlink 会抛异常
        assert temp_store.delete("dir/entry") is False

    def test_storage_statistics_and_serialize_variants(self, tmp_path, JSONStoreCls):
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), enable_cache=True, cache_size=10)

        store.load("missing")  # cache miss
        store.save("x", 1)
        store.load("x")  # cache hit
        stats = store.get_storage_statistics()
        assert "cache_hit_rate" in stats
        assert stats["storage_mode"] == "standard"

        @dataclass
        class DC:
            a: int

        assert store.save("dataclass", DC(a=1)) is True
        assert store.load("dataclass") == {"a": 1}

        assert store.save("list", [DC(a=2), {"b": 3}]) is True
        assert store.load("list") == [{"a": 2}, {"b": 3}]

        # pydantic model_dump 分支
        model = UserRecord(
            user_id="u",
            experiment_id="e",
            experiment_title="t",
            record_id="rid",
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        assert store.save("model", model) is True
        loaded_model = store.load("model")
        assert isinstance(loaded_model, dict)
        assert loaded_model["record_id"] == "rid"

        class Obj:
            def __init__(self):
                self.x = 1

        assert store.save("obj", Obj()) is True
        assert store.load("obj") == {"x": 1}

        # 不可序列化类型应触发异常分支，save 返回 False
        assert store.save("bad", {1, 2, 3}) is False

    def test_cache_helpers_and_record_file_error_branches(self, tmp_path, JSONStoreCls):
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), enable_cache=False)
        store._cache_data("k", 1)  # enable_cache=False 直接返回

        store.enable_cache = True
        store._evict_oldest_cache_entry()  # 空缓存直接返回

        # _load_record_file 解压失败分支
        store.enable_compression = True
        bad_compressed = tmp_path / "data" / "bad_compressed.json"
        bad_compressed.parent.mkdir(parents=True, exist_ok=True)
        bad_compressed.write_text(json.dumps("not-hex", ensure_ascii=False), encoding="utf-8")
        assert store._load_record_file(bad_compressed) is None

        # _load_record_file 读取异常分支（非法 JSON）
        bad_json = tmp_path / "data" / "bad_json.json"
        bad_json.write_text("{not json", encoding="utf-8")
        assert store._load_record_file(bad_json) is None

    def test_reject_symlink_path_breaks_on_missing_parts(self, tmp_path, JSONStoreCls):
        """覆盖 _reject_symlink_path 的 FileNotFoundError break 分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        target = store.base_dir / ".kv_store" / "missing" / "file.json"
        # 中间目录不存在，应触发 FileNotFoundError 并正常 break（不抛异常）
        store._reject_symlink_path(target)

    def test_collect_keys_returns_empty_when_base_missing(self, tmp_path, JSONStoreCls):
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        missing_dir = tmp_path / "no_such_dir"
        assert store._collect_keys(missing_dir, prefix=None) == []

    def test_load_returns_none_on_invalid_json(self, temp_store):
        """覆盖 load() 的异常分支"""
        path = temp_store._resolve_key_path("invalid/json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        assert temp_store.load("invalid/json") is None

    def test_atomic_write_json_cleans_temp_on_failure(self, tmp_path, JSONStoreCls):
        """覆盖 _atomic_write_json 的临时文件清理分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        target = store.base_dir / ".kv_store" / "x.json"

        with mock.patch("os.replace", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                store._atomic_write_json(target, {"a": 1})

        # 临时文件应被清理
        tmp_files = list(target.parent.glob("*.tmp"))
        assert tmp_files == []

    def test_atomic_write_json_ignores_temp_cleanup_errors(self, tmp_path, JSONStoreCls):
        """覆盖 _atomic_write_json 清理异常吞掉分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        target = store.base_dir / ".kv_store" / "y.json"

        original_unlink = Path.unlink

        def _unlink_raises(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self.suffix == ".tmp":
                raise PermissionError("deny")
            return original_unlink(self, *args, **kwargs)

        with mock.patch("os.replace", side_effect=RuntimeError("boom")), mock.patch.object(Path, "unlink", _unlink_raises):
            with pytest.raises(RuntimeError):
                store._atomic_write_json(target, {"a": 1})

    def test_clear_returns_false_on_unlink_error(self, tmp_path, JSONStoreCls):
        """覆盖 clear() 的异常分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        assert store.save("will_fail", 1) is True

        with mock.patch.object(Path, "unlink", side_effect=PermissionError("deny")):
            assert store.clear() is False

    def test_clear_unlinks_files_and_directories(self, tmp_path, JSONStoreCls):
        """覆盖 clear() 的正常 unlink/rmtree 分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        # 文件（触发 unlink）
        assert store.save("root_file", 1) is True
        # 子目录（触发 rmtree）
        assert store.save("sub/dir_file", 2) is True
        assert store.clear() is True
        assert store.list_keys() == []

    def test_reject_symlink_path_rejects_internal_symlink(self, tmp_path, JSONStoreCls):
        """覆盖 _reject_symlink_path 的 is_symlink() 拒绝分支（不依赖越界）"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        real_dir = store.base_dir / ".kv_store" / "real"
        real_dir.mkdir(parents=True, exist_ok=True)
        link_dir = store.base_dir / ".kv_store" / "link"
        link_dir.symlink_to(real_dir, target_is_directory=True)

        assert store.save("link/x", 1) is False

    def test_reject_symlink_path_rejects_symlink_file(self, tmp_path, JSONStoreCls):
        """覆盖 _reject_symlink_path 对“目标文件自身是 symlink”的拒绝分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        store._kv_dir.mkdir(parents=True, exist_ok=True)
        real = store._kv_dir / "real.json"
        real.write_text("{}", encoding="utf-8")
        link = store._kv_dir / "symlink.json"
        link.symlink_to(real)

        assert store.save("symlink", {"x": 1}) is False

    def test_verify_data_integrity_handles_exception(self, tmp_path, JSONStoreCls, DataIntegrityLevelEnum):
        """覆盖 _verify_data_integrity 的异常兜底分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), integrity_level=DataIntegrityLevelEnum.STRONG)
        data = {"record_id": "r", "user_id": "u", "experiment_id": "e", "started_at": None}
        assert store._verify_data_integrity(data, {}) is False

    def test_hash_and_compress_helpers(self, tmp_path, JSONStoreCls):
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), enable_compression=False)
        payload = {"a": 1}
        compressed = store._compress_data(payload)
        assert isinstance(compressed, str)
        assert json.loads(compressed) == payload

        digest = store._calculate_data_hash(payload)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_list_records_all_users(self, tmp_path, JSONStoreCls):
        """覆盖 list_records() 的“所有用户”分支"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))

        now = datetime.now()
        r1 = UserRecord(
            user_id="u1",
            experiment_id="e1",
            experiment_title="t1",
            record_id="r1",
            started_at=now,
            completed_at=now,
        )
        r2 = UserRecord(
            user_id="u2",
            experiment_id="e2",
            experiment_title="t2",
            record_id="r2",
            started_at=now,
            completed_at=now,
        )
        assert store.save_record(r1) is True
        assert store.save_record(r2) is True

        records = store.list_records()
        user_ids = {item.get("user_id") for item in records}
        assert {"u1", "u2"}.issubset(user_ids)

    def test_reject_symlink_path_rejects_broken_symlink(self, tmp_path, JSONStoreCls):
        """覆盖 _reject_symlink_path 的 FileNotFoundError 分支（破损 symlink）"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        store._kv_dir.mkdir(parents=True, exist_ok=True)
        link = store._kv_dir / "broken.json"
        link.symlink_to(store._kv_dir / "no_such_target.json")

        assert store.save("broken", {"x": 1}) is False

    def test_safe_path_join_require_basename_rejects_non_basename(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _safe_path_join 的 Path(...).name != stripped 分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        base = store.base_dir

        # 通过修改 os.sep/os.altsep，使第一个“包含分隔符”检查失效，
        # 触发后续 Path(stripped).name != stripped 的分支。
        import src.storage.json_store as json_store_mod

        monkeypatch.setattr(json_store_mod.os, "sep", "|", raising=False)
        monkeypatch.setattr(json_store_mod.os, "altsep", None, raising=False)
        with pytest.raises(ValidationError):
            store._safe_path_join(base, "a/b", require_basename=True)

    def test_fsync_dir_non_posix_and_exception_paths(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _fsync_dir 的非 posix 直返与异常吞掉分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))

        import src.storage.json_store as json_store_mod

        monkeypatch.setattr(json_store_mod.os, "name", "nt", raising=False)
        store._fsync_dir(store.base_dir)  # 非 posix：直接返回

        monkeypatch.setattr(json_store_mod.os, "name", "posix", raising=False)
        monkeypatch.setattr(json_store_mod.os, "open", mock.Mock(side_effect=OSError("deny")))
        store._fsync_dir(store.base_dir)  # 异常：吞掉

    def test_chmod_best_effort_non_posix_and_exception(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _chmod_best_effort 的 os.name!=posix 与 chmod 异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        p = store.base_dir / "x.json"
        p.write_text("{}", encoding="utf-8")

        import src.storage.json_store as json_store_mod

        monkeypatch.setattr(json_store_mod.os, "name", "nt", raising=False)
        store._chmod_best_effort(p, 0o600)

        monkeypatch.setattr(json_store_mod.os, "name", "posix", raising=False)
        monkeypatch.setattr(json_store_mod.os, "chmod", mock.Mock(side_effect=OSError("deny")))
        store._chmod_best_effort(p, 0o600)

    def test_reject_symlink_path_non_posix_returns(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _reject_symlink_path 的 os.name!=posix 直返分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        import src.storage.json_store as json_store_mod

        monkeypatch.setattr(json_store_mod.os, "name", "nt", raising=False)
        store._reject_symlink_path(store.base_dir / "any.json")

    def test_serialize_value_uses_dict_method(self, tmp_path, JSONStoreCls):
        """覆盖 _serialize_value 的 hasattr(value, 'dict') 分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))

        class HasDict:
            def dict(self):
                return {"ok": True}

        assert store.save("has_dict", HasDict()) is True
        assert store.load("has_dict") == {"ok": True}

    def test_verify_data_integrity_none_level(self, tmp_path, JSONStoreCls, DataIntegrityLevelEnum):
        """覆盖 _verify_data_integrity 的 NONE 直返分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"), integrity_level=DataIntegrityLevelEnum.NONE)
        assert store._verify_data_integrity({}, {}) is True

    def test_cleanup_old_data_warning_and_outer_exception(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 cleanup_old_data 的内层 warning 与外层异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        user_id = "u1"
        user_dir = store._get_user_dir(user_id)
        old_file = user_dir / "old.json"
        old_file.write_text("{}", encoding="utf-8")
        idx = {
            "records": [
                {
                    "record_id": "r1",
                    "filename": "old.json",
                    "started_at": (datetime.now() - timedelta(days=365)).isoformat(),
                }
            ]
        }
        store._get_index_file(user_id).write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

        monkeypatch.setattr("src.storage.json_store.shutil.move", mock.Mock(side_effect=RuntimeError("boom")))
        assert store.cleanup_old_data(days=90) == 0

        original_iterdir = Path.iterdir

        def _iterdir_raises(self: Path):  # type: ignore[no-untyped-def]
            if self == store.base_dir:
                raise RuntimeError("boom")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", _iterdir_raises)
        assert store.cleanup_old_data(days=90) == 0

    def test_backup_data_default_name_and_failure(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 backup_data 的默认名称与异常返回 False 分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        user_dir = store._get_user_dir("u1")
        (user_dir / "a.json").write_text("{}", encoding="utf-8")

        assert store.backup_data() is True  # backup_name=None 分支

        monkeypatch.setattr("src.storage.json_store.shutil.copytree", mock.Mock(side_effect=RuntimeError("boom")))
        assert store.backup_data("b_fail") is False

    def test_get_user_dir_empty_and_ensure_dir_error(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _get_user_dir 的空 user_id 与 mkdir 异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        with pytest.raises(ValidationError):
            store._get_user_dir("   ")

        monkeypatch.setattr(store, "_ensure_dir", mock.Mock(side_effect=OSError("deny")))
        with pytest.raises(OSError):
            store._get_user_dir("user_ok")

    def test_load_index_returns_empty_on_invalid_json(self, tmp_path, JSONStoreCls):
        """覆盖 _load_index 解析异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        index_file = store._get_index_file("u1")
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("{not json", encoding="utf-8")
        assert store._load_index("u1") == {"records": []}

    def test_save_index_raises_on_write_error(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 _save_index 的异常 re-raise 分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        monkeypatch.setattr(store, "_atomic_write_json", mock.Mock(side_effect=RuntimeError("boom")))
        with pytest.raises(RuntimeError):
            store._save_index("u1", {"records": []})

    def test_save_record_validation_and_write_failures(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 save_record 的多种异常/错误处理路径。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        assert store.save_record(None) is False  # 记录为空
        assert store.save_record("bad") is False  # type: ignore[arg-type]

        now = datetime.now()
        record = UserRecord(
            user_id="u1",
            experiment_id="e",
            experiment_title="t",
            record_id="r1",
            started_at=now,
            completed_at=now,
        )
        record.score.total = 1

        # 让备份分支触发：先写入一个“旧文件”，并让 copy2 失败（走 warning）
        user_dir = store._get_user_dir(record.user_id)
        filename = store._generate_filename(record)
        (user_dir / filename).write_text("{}", encoding="utf-8")
        monkeypatch.setattr("src.storage.json_store.shutil.copy2", mock.Mock(side_effect=RuntimeError("boom")))
        assert store.save_record(record) is True

        # 旧文件是 symlink：应拒绝备份（被 safe_execute 捕获并返回 False）
        target = user_dir / "real_target.json"
        target.write_text("{}", encoding="utf-8")
        (user_dir / filename).unlink()
        (user_dir / filename).symlink_to(target)
        assert store.save_record(record) is False

        # 写入失败：_atomic_write_json 抛异常 -> 返回 False
        (user_dir / filename).unlink(missing_ok=True)
        monkeypatch.setattr(store, "_atomic_write_json", mock.Mock(side_effect=RuntimeError("boom")))
        assert store.save_record(record) is False

    def test_load_record_missing_file_from_index(self, tmp_path, JSONStoreCls):
        """覆盖 load_record 的“索引有条目但文件不存在”分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        user_id = "u1"
        store._get_user_dir(user_id)
        store._get_index_file(user_id).write_text(
            json.dumps(
                {"records": [{"record_id": "r1", "filename": "missing.json"}]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        assert store.load_record(user_id, "r1") is None

    def test_list_records_exception_path(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 list_records 的异常兜底分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        original_iterdir = Path.iterdir

        def _iterdir_raises(self: Path):  # type: ignore[no-untyped-def]
            if self == store.base_dir:
                raise RuntimeError("boom")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", _iterdir_raises)
        assert store.list_records() == []

    def test_list_user_records_wrapper(self, temp_store, sample_record):
        """覆盖 list_user_records 的便捷包装分支。"""
        assert temp_store.save_record(sample_record) is True
        assert len(temp_store.list_user_records(sample_record.user_id)) == 1

    def test_get_stats_empty_and_time_parse_error(self, tmp_path, JSONStoreCls):
        """覆盖 get_stats 的空记录与时间解析异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        assert store.get_stats("missing")["total_experiments"] == 0

        # 构造一条“坏时间”记录，触发 except 分支（pass）
        user_id = "u1"
        store._get_user_dir(user_id)
        store._get_index_file(user_id).write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "record_id": "r1",
                            "filename": "x.json",
                            "final_score": 1,
                            "started_at": "bad",
                            "finished_at": "also-bad",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        stats = store.get_stats(user_id)
        assert stats["total_experiments"] == 1
        assert stats["total_time_minutes"] == 0

    def test_get_and_set_config_error_paths(self, tmp_path, monkeypatch, JSONStoreCls):
        """覆盖 get()/set() 的读取异常与 set() 写入异常分支。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))
        config_file = store.base_dir / "config.json"
        config_file.write_text("{not json", encoding="utf-8")
        assert store.get("k", default=123) == 123

        # set() 读取已有配置分支
        config_file.write_text(json.dumps({"a": 1}, ensure_ascii=False), encoding="utf-8")
        store.set("b", 2)
        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert loaded["a"] == 1
        assert loaded["b"] == 2

        # set() 写入失败：吞掉异常
        monkeypatch.setattr(store, "_atomic_write_json", mock.Mock(side_effect=RuntimeError("boom")))
        store.set("c", 3)

    def test_save_record_concurrent_same_user_is_serialized(self, tmp_path, monkeypatch, JSONStoreCls):
        """并发场景：同一 user_id 的 save_record 应被用户锁串行化。"""
        store = JSONStoreCls(base_dir=str(tmp_path / "data"))

        now = datetime.now()
        r1 = UserRecord(
            user_id="u1",
            experiment_id="e",
            experiment_title="t",
            record_id="r1",
            started_at=now,
            completed_at=now,
        )
        r2 = UserRecord(
            user_id="u1",
            experiment_id="e",
            experiment_title="t",
            record_id="r2",
            started_at=now,
            completed_at=now,
        )

        active = 0
        active_lock = threading.Lock()
        overlap_detected = False
        entered = threading.Event()
        release = threading.Event()

        def atomic_write_side_effect(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal active, overlap_detected
            with active_lock:
                active += 1
                if active > 1:
                    overlap_detected = True
            entered.set()
            release.wait(timeout=2)
            with active_lock:
                active -= 1

        monkeypatch.setattr(store, "_atomic_write_json", mock.Mock(side_effect=atomic_write_side_effect))

        results: list[bool] = []

        def _run(rec: UserRecord) -> None:
            results.append(store.save_record(rec))

        t1 = threading.Thread(target=_run, args=(r1,))
        t2 = threading.Thread(target=_run, args=(r2,))
        t1.start()
        assert entered.wait(timeout=2) is True
        t2.start()
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)

        assert results == [True, True] or results == [True] * len(results)
        assert overlap_detected is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
