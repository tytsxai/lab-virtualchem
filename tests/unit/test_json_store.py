"""
JSON存储系统单元测试
"""

import tempfile
from datetime import datetime

import pytest

from src.models.user_record import Mistake, StepRecord, UserRecord
from src.storage.json_store import JSONStore


@pytest.fixture
def temp_store():
    """创建临时存储系统"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JSONStore(base_dir=tmpdir)
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
        completed_at=now
    )
    record.score.total = 85
    record.status = "completed"

    # 添加步骤记录
    step = StepRecord(
        step_id="step1",
        passed=True,
        user_input={"value": 10}
    )
    step.completed_at = now
    record.step_records.append(step)

    # 添加错误
    mistake = Mistake(
        step_id="step2",
        error_type="input_error",
        description="测试错误",
        severity="warning"
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
        loaded = temp_store.load_record(
            sample_record.user_id,
            sample_record.record_id
        )

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
            completed_at=datetime.now()
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
            record_id="test_record_002"
        )
        temp_store.save_record(record2)

        # 筛选特定实验
        records = temp_store.list_records(
            user_id="test_user",
            experiment_id="test_exp"
        )
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
                completed_at=datetime.now()
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
            record_id="rec1"
        )
        temp_store.save_record(record1)

        record2 = UserRecord(
            user_id="test_user",
            experiment_id="recrystallization",
            experiment_title="重结晶",
            record_id="rec2"
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
                completed_at=now
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
                completed_at=datetime.now()
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
