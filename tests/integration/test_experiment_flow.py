"""
实验流程集成测试

测试完整的实验流程：
- 模板加载
- 实验控制
- 数据验证
- 记录保存
"""

from datetime import datetime

import pytest
import yaml

from src.core.experiment_controller import ExperimentController
from src.core.rule_validator import RuleValidator
from src.core.template_engine import TemplateEngine
from src.knowledge.hazard_checker import HazardChecker
from src.knowledge.reagent_db import ReagentDatabase
from src.storage.json_store import JSONStore


class TestExperimentFlow:
    """实验流程测试"""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """创建临时存储"""
        store = JSONStore(base_dir=str(tmp_path / "data"))
        yield store

    @pytest.fixture
    def template_engine(self, tmp_path):
        """创建模板引擎"""
        # 创建临时模板目录
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # 创建测试模板
        template_data = {
            "experiment": {  # 必需的根节点
                "id": "test_exp_001",
                "title": "测试滴定实验",
                "level": "basic",
                "category": "酸碱滴定",
                "description": "用于集成测试的滴定实验",
                "steps": [
                    {
                        "id": "step1",
                        "title": "准备溶液",
                        "text": "准备标准溶液和待测溶液",
                        "inputs": [
                            {
                                "id": "volume_naoh",
                                "label": "NaOH体积",
                                "type": "number",
                                "unit": "mL",
                                "min_value": 0,
                                "max_value": 50,
                            }
                        ],
                        "validation_rules": [
                            {
                                "type": "range",
                                "field": "volume_naoh",
                                "min": 10,
                                "max": 30,
                                "error_message": "体积应在10-30mL之间",
                            }
                        ],
                        "correct_value": 25.0,
                    },
                    {
                        "id": "step2",
                        "title": "进行滴定",
                        "text": "使用标准溶液滴定待测溶液",
                        "inputs": [
                            {
                                "id": "volume_used",
                                "label": "消耗体积",
                                "type": "number",
                                "unit": "mL",
                                "min_value": 0,
                                "max_value": 50,
                            }
                        ],
                        "validation_rules": [
                            {
                                "type": "range",
                                "field": "volume_used",
                                "min": 20,
                                "max": 30,
                                "error_message": "消耗体积异常",
                            }
                        ],
                        "correct_value": 24.5,
                    },
                ],
            }
        }

        template_file = templates_dir / "test_exp_001.yaml"
        with open(template_file, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        engine = TemplateEngine(templates_dir=str(templates_dir))
        return engine

    @pytest.fixture
    def experiment_controller(self, template_engine, temp_storage):
        """创建实验控制器"""
        template = template_engine.load_experiment_by_id("test_exp_001")

        reagent_db = ReagentDatabase()
        hazard_checker = HazardChecker(reagent_db=reagent_db)
        validator = RuleValidator(hazard_checker=hazard_checker)

        controller = ExperimentController(
            template=template, validator=validator, storage=temp_storage, user_id="test_user"
        )
        return controller

    def test_complete_successful_experiment(self, experiment_controller):
        """测试完整的成功实验流程"""
        controller = experiment_controller

        # 1. 开始实验
        controller.start_experiment()
        assert controller.current_step_index == 0
        assert controller.is_started()

        # 2. 完成第一步 - 输入正确值
        result = controller.submit_step({"volume_naoh": 25.0})
        assert result.is_valid
        assert controller.current_step_index == 1

        # 3. 完成第二步
        result = controller.submit_step({"volume_used": 24.5})
        assert result.is_valid

        # 4. 实验完成
        assert controller.is_completed()

        # 5. 获取结果
        results = controller.get_results()
        assert len(results) == 2
        assert results[0]["step_id"] == "step1"
        assert results[0]["data"]["volume_naoh"] == 25.0

    def test_experiment_with_mistakes(self, experiment_controller):
        """测试有错误的实验流程"""
        controller = experiment_controller

        # 开始实验
        controller.start_experiment()

        # 提交错误值（超出范围）
        result = controller.submit_step({"volume_naoh": 50.0})  # 超过最大值30
        assert not result.is_valid
        assert len(result.errors) > 0

        # 应该还在第一步
        assert controller.current_step_index == 0

        # 提交正确值
        result = controller.submit_step({"volume_naoh": 25.0})
        assert result.is_valid
        assert controller.current_step_index == 1

    def test_experiment_navigation(self, experiment_controller):
        """测试实验导航"""
        controller = experiment_controller

        controller.start_experiment()

        # 完成第一步
        result = controller.submit_step({"volume_naoh": 25.0})
        assert result.is_valid
        assert controller.current_step_index == 1

        # 可以返回上一步
        controller.go_to_step(0)
        assert controller.current_step_index == 0

        # 可以前进到下一步
        controller.go_to_step(1)
        assert controller.current_step_index == 1

    def test_experiment_progress_tracking(self, experiment_controller):
        """测试实验进度追踪"""
        controller = experiment_controller

        controller.start_experiment()

        # 初始进度
        progress = controller.get_progress()
        assert progress["total_steps"] == 2
        assert progress["completed_steps"] == 0
        assert progress["progress_percentage"] == 0

        # 完成第一步
        controller.submit_step({"volume_naoh": 25.0})
        progress = controller.get_progress()
        assert progress["completed_steps"] == 1
        assert progress["progress_percentage"] == 50

        # 完成第二步
        controller.submit_step({"volume_used": 24.5})
        progress = controller.get_progress()
        assert progress["completed_steps"] == 2
        assert progress["progress_percentage"] == 100

    def test_multiple_users_same_experiment(self, template_engine, temp_storage):
        """测试多个用户同时进行相同实验"""
        template = template_engine.load_experiment_by_id("test_exp_001")

        reagent_db = ReagentDatabase()
        hazard_checker = HazardChecker(reagent_db=reagent_db)
        validator = RuleValidator(hazard_checker=hazard_checker)

        # 创建两个控制器
        controller1 = ExperimentController(
            template=template, validator=validator, storage=temp_storage, user_id="user1"
        )
        controller2 = ExperimentController(
            template=template, validator=validator, storage=temp_storage, user_id="user2"
        )

        # 两个用户独立进行实验
        controller1.start_experiment()
        controller2.start_experiment()

        controller1.submit_step({"volume_naoh": 25.0})
        controller2.submit_step({"volume_naoh": 26.0})

        # 验证独立性
        results1 = controller1.get_results()
        results2 = controller2.get_results()

        assert results1[0]["data"]["volume_naoh"] == 25.0
        assert results2[0]["data"]["volume_naoh"] == 26.0

    def test_experiment_time_tracking(self, experiment_controller):
        """测试实验时间追踪"""
        import time

        controller = experiment_controller
        controller.start_experiment()

        # 记录开始时间
        start_time = controller.start_time
        assert start_time is not None

        # 等待一小段时间
        time.sleep(0.1)

        # 完成实验
        controller.submit_step({"volume_naoh": 25.0})
        controller.submit_step({"volume_used": 24.5})

        # 验证时间记录
        end_time = controller.end_time
        assert end_time is not None
        assert end_time > start_time

        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.1


class TestSafetyChecks:
    """安全检查测试"""

    @pytest.fixture
    def dangerous_template(self, tmp_path):
        """创建包含危险操作的模板"""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        template_data = {
            "experiment": {  # 必需的根节点
                "id": "dangerous_exp",
                "title": "高温实验",
                "level": "advanced",
                "category": "加热反应",
                "description": "包含高温操作的实验",
                "steps": [
                    {
                        "id": "step1",
                        "title": "加热",
                        "text": "将溶液加热",
                        "inputs": [
                            {
                                "id": "temperature",
                                "label": "温度",
                                "type": "number",
                                "unit": "°C",
                                "min_value": 0,
                                "max_value": 200,
                            }
                        ],
                        "validation_rules": [
                            {
                                "type": "range",
                                "field": "temperature",
                                "min": 50,
                                "max": 150,
                                "warning": "温度过高可能有危险",
                            }
                        ],
                        "correct_value": 100,
                    }
                ],
            }
        }

        template_file = templates_dir / "dangerous_exp.yaml"
        with open(template_file, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        engine = TemplateEngine(templates_dir=str(templates_dir))
        return engine

    def test_dangerous_temperature_warning(self, dangerous_template, tmp_path):
        """测试危险温度警告"""
        template = dangerous_template.load_experiment_by_id("dangerous_exp")

        store = JSONStore(base_dir=str(tmp_path / "data"))
        reagent_db = ReagentDatabase()
        hazard_checker = HazardChecker(reagent_db=reagent_db)
        validator = RuleValidator(hazard_checker=hazard_checker)

        controller = ExperimentController(
            template=template, validator=validator, storage=store, user_id="test_user"
        )

        controller.start_experiment()

        # 测试高温输入
        result = controller.submit_step({"temperature": 180})
        # 应该有警告（可能允许，但有警告）
        assert len(result.warnings) > 0 or not result.is_valid


class TestReportGeneration:
    """报告生成测试"""

    def test_complete_report_pipeline(self, tmp_path):
        """测试完整的报告生成流程"""
        from src.models.experiment import Step
        from src.reporter.html_generator import HTMLReportGenerator

        # 创建测试步骤
        Step(id="step1", text="测试步骤: 这是测试步骤的说明")

        # 创建测试数据
        experiment_data = {
            "experiment_id": "test_001",
            "experiment_name": "测试实验",
            "user_id": "test_user",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "steps": [
                {
                    "step_id": "step1",
                    "title": "测试步骤",
                    "data": {"input1": 25.0},
                    "is_correct": True,
                    "score": 100,
                }
            ],
            "total_score": 100,
        }

        # 生成报告
        generator = HTMLReportGenerator()
        html_content = generator.generate(experiment_data)

        # 验证报告内容
        assert html_content is not None
        assert "test_001" in html_content
        assert "测试实验" in html_content

        # 保存报告
        report_file = tmp_path / "report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        assert report_file.exists()
        assert report_file.stat().st_size > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
