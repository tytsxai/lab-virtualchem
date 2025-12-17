"""基础UI测试 - 简化版本，专注于数据模型验证"""

import pytest

from src.models.experiment import ExperimentTemplate, Step


@pytest.fixture
def sample_experiment():
    """创建示例实验"""
    # 添加步骤 - 使用完整的必需字段
    step1 = Step(id="step1", text="准备实验器材 - 检查并准备所需器材")
    step2 = Step(id="step2", text="进行实验 - 按照步骤进行实验")

    exp = ExperimentTemplate(
        id="test_exp",
        title="测试实验",
        description="这是一个测试实验",
        category="酸碱滴定",
        level="basic",
        steps=[step1, step2],
    )

    return exp


class TestExperimentTemplate:
    """实验模板数据模型测试"""

    def test_experiment_template_creation(self, sample_experiment):
        """测试实验模板创建"""
        assert sample_experiment is not None
        assert sample_experiment.id == "test_exp"
        assert sample_experiment.title == "测试实验"
        assert sample_experiment.description == "这是一个测试实验"
        assert sample_experiment.category == "酸碱滴定"
        assert sample_experiment.level == "basic"

    def test_experiment_has_steps(self, sample_experiment):
        """测试实验包含步骤"""
        assert len(sample_experiment.steps) == 2
        assert sample_experiment.steps[0].id == "step1"
        assert sample_experiment.steps[1].id == "step2"

    def test_step_has_required_fields(self, sample_experiment):
        """测试步骤包含必需字段"""
        step = sample_experiment.steps[0]
        assert step.id == "step1"
        assert step.text == "准备实验器材 - 检查并准备所需器材"
        assert step.hints == []  # 默认空列表
        assert step.safety_level == "info"  # 默认值

    def test_experiment_default_fields(self, sample_experiment):
        """测试实验模板默认字段"""
        assert sample_experiment.duration_min == 45  # 默认值
        assert sample_experiment.version == "1.0.0"  # 默认值
        assert sample_experiment.goals == []  # 默认空列表
        assert sample_experiment.curves == []  # 默认空列表
        assert sample_experiment.score_rules == []  # 默认空列表


class TestStepModel:
    """Step数据模型测试"""

    def test_step_creation(self):
        """测试步骤创建"""
        step = Step(id="test_step", text="这是测试步骤的说明")
        assert step.id == "test_step"
        assert step.text == "这是测试步骤的说明"

    def test_step_with_media(self):
        """测试带媒体的步骤"""
        step = Step(
            id="test_step",
            text="说明文本",
            media={"image": "test.png", "video": "test.mp4"},
        )
        assert step.media is not None
        assert step.media["image"] == "test.png"
        assert step.media["video"] == "test.mp4"

    def test_step_safety_level(self):
        """测试步骤安全等级"""
        step = Step(id="test_step", text="说明文本", safety_level="warning")
        assert step.safety_level == "warning"


class TestExperimentTemplateValidation:
    """实验模板验证测试"""

    def test_level_validation(self):
        """测试难度等级验证"""
        # 有效的等级
        for level in ["basic", "intermediate", "advanced"]:
            exp = ExperimentTemplate(
                id="test", title="测试", level=level, steps=[Step(id="s1", text="文本")]
            )
            assert exp.level == level

    def test_minimum_one_step_required(self):
        """测试至少需要一个步骤"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ExperimentTemplate(
                id="test",
                title="测试",
                steps=[],  # 空步骤列表应该失败
            )

        assert "steps" in str(exc_info.value)

    def test_step_id_uniqueness(self):
        """测试步骤ID唯一性"""
        from pydantic import ValidationError

        # 重复的步骤ID应该失败
        step1 = Step(id="same_id", text="文本1")
        step2 = Step(id="same_id", text="文本2")

        with pytest.raises(ValidationError) as exc_info:
            ExperimentTemplate(id="test", title="测试", steps=[step1, step2])

        assert "步骤ID必须唯一" in str(exc_info.value)

    def test_get_step_by_id(self, sample_experiment):
        """测试通过ID获取步骤"""
        step = sample_experiment.get_step_by_id("step1")
        assert step is not None
        assert step.id == "step1"
        assert step.text == "准备实验器材 - 检查并准备所需器材"

        # 不存在的ID应该返回None
        assert sample_experiment.get_step_by_id("non_existent") is None
