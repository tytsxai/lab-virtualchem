"""
Recovery Manager 单元测试
测试数据恢复和自动保存功能
"""

import json
import tempfile
from pathlib import Path

from src.utils.recovery import AutoSave, RecoveryManager


class TestRecoveryManager:
    """恢复管理器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.manager = RecoveryManager(backup_dir=self.temp_dir)

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_backup(self):
        """测试创建备份"""
        data = {"test": "data", "value": 123}
        result = self.manager.create_backup(data, "test_backup")
        assert result is True

        # 验证备份文件存在
        backup_files = list(Path(self.temp_dir).glob("test_backup_*.json"))
        assert len(backup_files) == 1

    def test_restore_latest(self):
        """测试恢复最新备份"""
        data = {"test": "data", "value": 123}
        self.manager.create_backup(data, "test_backup")

        restored = self.manager.restore_latest("test_backup")
        assert restored is not None
        assert restored["test"] == "data"
        assert restored["value"] == 123

    def test_restore_non_existent(self):
        """测试恢复不存在的备份"""
        restored = self.manager.restore_latest("non_existent")
        assert restored is None

    def test_list_backups(self):
        """测试列出备份"""
        import time

        # 创建多个备份(加延迟避免时间戳冲突)
        self.manager.create_backup({"data": 1}, "backup1")
        time.sleep(0.01)
        self.manager.create_backup({"data": 2}, "backup1")
        time.sleep(0.01)
        self.manager.create_backup({"data": 3}, "backup2")

        # 列出所有backup1
        backups = self.manager.list_backups("backup1")
        assert len(backups) == 2  # 应该恰好有2个backup1

        # 列出所有备份
        all_backups = self.manager.list_backups()
        assert len(all_backups) == 3  # 应该恰好有3个备份

    def test_delete_old_backups(self):
        """测试删除旧备份"""
        import time

        # 创建5个备份(加延迟避免时间戳冲突)
        for i in range(5):
            self.manager.create_backup({"data": i}, "test")
            time.sleep(0.01)

        # 保留3个,删除2个
        deleted = self.manager.delete_old_backups("test", keep_count=3)
        assert deleted == 2

        # 验证只剩3个
        backups = self.manager.list_backups("test")
        assert len(backups) == 3

    def test_export_backup(self):
        """测试导出备份"""
        import tempfile

        data = {"export": "test"}
        self.manager.create_backup(data, "export_test")

        # 导出到临时文件
        export_path = Path(tempfile.mktemp(suffix=".json"))
        result = self.manager.export_backup("export_test", str(export_path))

        assert result is True
        assert export_path.exists()

        # 验证导出的数据
        with open(export_path, encoding="utf-8") as f:
            exported_data = json.load(f)
        assert exported_data["export"] == "test"

        # 清理
        export_path.unlink(missing_ok=True)


class TestAutoSave:
    """自动保存测试"""

    def test_initialization(self):
        """测试初始化"""
        auto_save = AutoSave(save_interval=60)
        assert auto_save.save_interval == 60
        assert auto_save.unsaved_changes is False

    def test_mark_changed(self):
        """测试标记更改"""
        auto_save = AutoSave()
        assert auto_save.has_unsaved_changes() is False

        auto_save.mark_changed()
        assert auto_save.has_unsaved_changes() is True

    def test_should_save_no_changes(self):
        """测试无更改时不需要保存"""
        auto_save = AutoSave(save_interval=1)
        assert auto_save.should_save() is False

    def test_should_save_with_changes(self):
        """测试有更改且时间到达时需要保存"""
        import time

        auto_save = AutoSave(save_interval=1)
        auto_save.mark_changed()

        # 立即检查,时间未到
        assert auto_save.should_save() is False

        # 等待超过间隔时间
        time.sleep(1.1)
        assert auto_save.should_save() is True

    def test_mark_saved(self):
        """测试标记已保存"""
        auto_save = AutoSave()
        auto_save.mark_changed()
        assert auto_save.has_unsaved_changes() is True

        auto_save.mark_saved()
        assert auto_save.has_unsaved_changes() is False

    def test_save_cycle(self):
        """测试完整的保存周期"""
        import time

        auto_save = AutoSave(save_interval=1)

        # 1. 初始状态:无更改
        assert auto_save.should_save() is False

        # 2. 标记更改
        auto_save.mark_changed()
        assert auto_save.has_unsaved_changes() is True

        # 3. 时间未到,不保存
        assert auto_save.should_save() is False

        # 4. 时间到达,需要保存
        time.sleep(1.1)
        assert auto_save.should_save() is True

        # 5. 标记已保存
        auto_save.mark_saved()
        assert auto_save.has_unsaved_changes() is False
        assert auto_save.should_save() is False
