"""
服务实现层单元测试
"""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from src.contracts.experiment_service import (
    ExperimentRequest,
    ExperimentServiceConfig,
    ExperimentStatus,
    StepSubmissionRequest,
)
from src.contracts.storage_service import (
    QueryFilter,
    QueryOperator,
    QueryRequest,
    SaveRequest,
    StorageServiceConfig,
)
from src.contracts.report_service import ReportType
from src.models.experiment import ExperimentTemplate, Step
from src.services import (
    ExperimentServiceImpl,
    PluginServiceImpl,
    ReportServiceImpl,
    StorageServiceImpl,
)


class TestExperimentServiceImpl(unittest.TestCase):
    """测试实验服务实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_engine = Mock()
        self.mock_storage = Mock()
        self.sample_template = ExperimentTemplate(
            id="template1",
            title="测试模板",
            description="示例模板",
            category="general",
            steps=[
                Step(id="step1", text="第一步"),
                Step(id="step2", text="第二步"),
            ],
        )
        self.service = ExperimentServiceImpl(
            engine_factory=lambda: self.mock_engine,
            storage=self.mock_storage,
            config=ExperimentServiceConfig(),
        )

    def test_create_experiment_success(self):
        """测试创建实验 - 成功"""
        # 准备
        self.mock_storage.load.side_effect = lambda key: self.sample_template if key.startswith("templates/") else None
        request = ExperimentRequest(user_id="user123", template_id="template1")

        # 执行
        response = self.service.create_experiment(request)

        # 断言
        self.assertTrue(response.success)
        self.assertEqual(response.status, ExperimentStatus.NOT_STARTED)
        self.assertIsNotNone(response.experiment_id)
        self.mock_engine.initialize.assert_called_once()

    def test_create_experiment_template_not_found(self):
        """测试创建实验 - 模板不存在"""
        # 准备
        self.mock_storage.load.return_value = None
        request = ExperimentRequest(user_id="user123", template_id="nonexistent")

        # 执行
        response = self.service.create_experiment(request)

        # 断言
        self.assertFalse(response.success)
        self.assertIn("模板不存在", response.message)

    def test_submit_step_success(self):
        """测试提交步骤 - 成功"""
        # 准备
        self.mock_storage.load.side_effect = lambda key: self.sample_template if key.startswith("templates/") else None
        self.mock_engine.submit_step.return_value = (True, "正确", None)
        self.mock_engine.next_step.return_value = True
        mock_step = Mock(id="step2")
        self.mock_engine.get_current_step.return_value = mock_step

        create_response = self.service.create_experiment(
            ExperimentRequest(user_id="user123", template_id="template1")
        )
        request = StepSubmissionRequest(
            experiment_id=create_response.experiment_id, step_id="step1", user_input={"answer": "42"}
        )

        # 执行
        response = self.service.submit_step(request)

        # 断言
        self.assertTrue(response.success)
        self.assertTrue(response.passed)
        self.assertEqual(response.next_step_id, "step2")


class TestStorageServiceImpl(unittest.TestCase):
    """测试存储服务实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_storage = Mock()
        self.service = StorageServiceImpl(self.mock_storage, StorageServiceConfig())

    def test_save_entity_success(self):
        """测试保存实体 - 成功"""
        # 准备
        self.mock_storage.save.return_value = True
        entity = Mock(id="entity123")
        request = SaveRequest(entity_type="test", entity=entity)

        # 执行
        response = self.service.save(request)

        # 断言
        self.assertTrue(response.success)
        self.assertIsNotNone(response.entity_id)
        self.mock_storage.save.assert_called_once()

    def test_query_with_filters(self):
        """测试查询 - 带过滤条件"""
        # 准备
        self.mock_storage.list_keys.return_value = ["test/1", "test/2", "test/3"]
        entities = [
            Mock(id="1", name="Alice", age=25),
            Mock(id="2", name="Bob", age=30),
            Mock(id="3", name="Charlie", age=35),
        ]
        self.mock_storage.load.side_effect = entities

        filters = [QueryFilter(field="age", operator=QueryOperator.GT, value=28)]
        request = QueryRequest(entity_type="test", filters=filters)

        # 执行
        response = self.service.query(request)

        # 断言
        self.assertTrue(response.success)
        self.assertEqual(len(response.data), 2)  # Bob and Charlie
        self.assertEqual(response.total_count, 2)

    def test_batch_operations(self):
        """测试批量操作"""
        # 准备
        self.mock_storage.save.return_value = True
        entities = [Mock(id=f"entity{i}") for i in range(3)]
        requests = [SaveRequest(entity_type="test", entity=e) for e in entities]

        # 执行
        responses = self.service.batch_save(requests)

        # 断言
        self.assertEqual(len(responses), 3)
        self.assertTrue(all(r.success for r in responses))
        self.assertEqual(self.mock_storage.save.call_count, 3)


class TestReportServiceImpl(unittest.TestCase):
    """测试报告服务实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_generator = Mock()
        self.mock_exporter = Mock()
        self.mock_repository = Mock()
        self.service = ReportServiceImpl(
            self.mock_generator, self.mock_exporter, self.mock_repository
        )

    def test_generate_experiment_report_success(self):
        """测试生成实验报告 - 成功"""
        # 准备
        mock_record = Mock(
            record_id="rec123",
            user_id="user123",
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        self.mock_generator.generate.return_value = "<html>Report</html>"
        self.mock_exporter.export.return_value = True

        # 执行
        from src.contracts.report_service import ExportFormat

        response = self.service.generate_experiment_report(mock_record, format=ExportFormat.HTML)

        # 断言
        self.assertTrue(response.success)
        self.assertIsNotNone(response.file_path)
        self.mock_generator.generate.assert_called_once()
        self.mock_exporter.export.assert_called_once()

    def test_load_user_records(self):
        """测试加载用户记录"""
        # 准备
        mock_records = [
            Mock(
                user_id="user123",
                started_at=datetime(2025, 1, i),
                experiment_id=f"exp{i}",
            )
            for i in range(1, 6)
        ]
        self.mock_repository.find.return_value = mock_records

        # 执行
        records = self.service._load_user_records("user123")

        # 断言
        self.assertEqual(len(records), 5)
        self.mock_repository.find.assert_called_once()

    def test_report_caching(self):
        """测试报告缓存"""
        # 缓存报告
        self.service._cache_report("report123", "<html>Cached</html>")

        # 从缓存加载
        content = self.service._load_report_from_storage("report123")

        # 断言
        self.assertEqual(content, "<html>Cached</html>")

    def test_get_available_templates_filters_by_type(self):
        """模板过滤应根据类型关键字工作"""
        self.mock_generator.list_templates.return_value = [
            "experiment_default",
            "summary_overview",
            "analysis_detail",
        ]

        templates = self.service.get_available_templates(ReportType.SUMMARY)

        self.assertIn("summary_overview", templates)
        self.assertNotIn("experiment_default", templates)

    def test_load_report_from_storage_reads_file(self):
        """当缓存未命中时应从磁盘加载"""
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            report_path = tmp_dir / "report_test.html"
            report_path.write_text("<html>Disk</html>", encoding="utf-8")

            self.service.config.output_dir = str(tmp_dir)

            content = self.service._load_report_from_storage("report_test")

            self.assertEqual(content, "<html>Disk</html>")


class TestPluginServiceImpl(unittest.TestCase):
    """测试插件服务实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_loader = Mock()
        self.mock_registry = Mock()
        self.service = PluginServiceImpl(self.mock_loader, self.mock_registry)

    def test_execute_plugin_success(self):
        """测试执行插件 - 成功"""
        # 准备
        mock_plugin = Mock()
        mock_plugin.is_available.return_value = True
        mock_plugin.execute.return_value = {"result": "success"}
        self.mock_registry.get.return_value = mock_plugin

        from src.contracts.plugin_service import PluginExecuteRequest

        request = PluginExecuteRequest(
            plugin_name="test_plugin", action="run", params={"key": "value"}
        )

        # 执行
        response = self.service.execute_plugin(request)

        # 断言
        self.assertTrue(response.success)
        self.assertEqual(response.result, {"result": "success"})
        mock_plugin.execute.assert_called_once_with("run", {"key": "value"})

    def test_execute_plugin_not_found(self):
        """测试执行插件 - 插件不存在"""
        # 准备
        self.mock_registry.get.return_value = None

        from src.contracts.plugin_service import PluginExecuteRequest

        request = PluginExecuteRequest(plugin_name="nonexistent", action="run")

        # 执行
        response = self.service.execute_plugin(request)

        # 断言
        self.assertFalse(response.success)
        self.assertIn("插件不存在", response.error)


def run_tests():
    """运行所有测试"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
