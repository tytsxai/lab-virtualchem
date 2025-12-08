"""
数据库管理器防注入单元测试
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.models.user_record import ExperimentScore, UserRecord  # noqa: E402
from src.storage.database_manager import DatabaseManager  # noqa: E402


@pytest.fixture
def db_manager(tmp_path):
    """创建隔离的数据库管理器实例"""
    db_path = tmp_path / "security.db"
    manager = DatabaseManager(str(db_path))
    yield manager
    manager.close()


def test_malicious_identifiers_are_escaped(db_manager):
    """恶意ID应被当作普通数据存储，不影响表结构"""
    db_manager.create_user("safe_user", "安全用户", "safe@example.com")

    payload = "attacker'; DROP TABLE users; --"
    db_manager.create_user(payload, "恶意用户", "attacker@example.com")

    stored_payload = db_manager.get_user(payload)
    assert stored_payload is not None
    assert stored_payload["user_id"] == payload

    # 原有用户不受影响
    safe_user = db_manager.get_user("safe_user")
    assert safe_user is not None
    assert safe_user["user_id"] == "safe_user"


def test_injection_like_filters_do_not_leak_rows(db_manager):
    """查询条件中的注入片段不会绕过过滤"""
    db_manager.create_user("victim", "受害者", "victim@example.com")
    victim_record = UserRecord(
        record_id="victim_record",
        user_id="victim",
        experiment_id="exp1",
        experiment_title="安全实验",
        status="completed",
        completed_at=datetime.now(),
        score=ExperimentScore(total=90, scientific=0, procedural=0, safety=0),
    )
    db_manager.save_experiment_record(victim_record)

    db_manager.create_user("other_user", "其他用户", "other@example.com")
    other_record = UserRecord(
        record_id="other_record",
        user_id="other_user",
        experiment_id="exp2",
        experiment_title="其他实验",
        status="completed",
        completed_at=datetime.now(),
        score=ExperimentScore(total=80, scientific=0, procedural=0, safety=0),
    )
    db_manager.save_experiment_record(other_record)

    malicious_filter = "victim' OR '1'='1"
    malicious_records = db_manager.list_user_experiments(malicious_filter)
    assert malicious_records == []

    safe_records = db_manager.list_user_experiments("victim")
    assert len(safe_records) == 1
    assert safe_records[0]["record_id"] == "victim_record"


def test_pagination_strings_are_normalized(db_manager):
    """LIMIT/OFFSET 参数会被规范化，拒绝注入片段"""
    for i in range(3):
        db_manager.create_user(f"user_{i}", f"用户{i}", f"user{i}@example.com")

    # 带有SQL片段的limit/offset应被安全转换
    users = db_manager.list_users(limit="2; DROP TABLE users; --", offset="0")
    assert len(users) >= 3
    assert all("user_id" in user for user in users)
