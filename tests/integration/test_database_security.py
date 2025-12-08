"""
数据库操作防注入集成测试
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.models.user_record import ExperimentScore, UserRecord  # noqa: E402
from src.storage.database_manager import DatabaseManager  # noqa: E402


@pytest.mark.integration
def test_sql_injection_payload_does_not_corrupt_tables(tmp_path):
    """恶意payload不会破坏表结构或读取其他用户数据"""
    db_path = tmp_path / "integration_security.db"
    manager = DatabaseManager(str(db_path))

    try:
        manager.create_user("legit_user", "合法用户", "legit@example.com")
        record = UserRecord(
            record_id="legit_record",
            user_id="legit_user",
            experiment_id="chem101",
            experiment_title="安全实验",
            status="completed",
            completed_at=datetime.now(),
            score=ExperimentScore(total=88, scientific=0, procedural=0, safety=0),
        )
        manager.save_experiment_record(record)

        payload = "1'; DROP TABLE experiment_records; --"
        injected_result = manager.list_user_experiments(payload)
        assert injected_result == []

        # 数据仍然可读
        assert manager.get_user("legit_user") is not None
        fetched_record = manager.get_experiment_record("legit_record")
        assert fetched_record is not None
        assert fetched_record["user_id"] == "legit_user"

        # 带payload的模板/配置依然以普通数据存储
        malicious_template_id = "template'); DROP TABLE templates; --"
        manager.save_template(malicious_template_id, "注入探针", "safety", "{}")
        template = manager.get_template(malicious_template_id)
        assert template is not None
        assert template["template_id"] == malicious_template_id

        config_key = "timeout'); DROP TABLE configurations; --"
        manager.set_config(config_key, "15")
        assert manager.get_config(config_key) == "15"

        stats = manager.get_experiment_statistics()
        assert stats["total_records"] == 1
    finally:
        manager.close()
