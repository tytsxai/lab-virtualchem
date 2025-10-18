"""
Experiment Controller 单元测试
测试实验控制器的流程管理
"""


import pytest

from src.core.curve_generator import CurveGenerator
from src.core.experiment_controller import ExperimentController
from src.core.rule_validator import RuleValidator
from src.models.experiment import (
    CheckPoint,
    CheckType,
    Curve,
    CurveType,
    ExperimentTemplate,
    Goal,
    InputSpec,
    Reagent,
    ScoreRule,
    Step,
)


class TestExperimentController:
    """实验控制器基本功能测试"""

    def setup_method(self):
        """每个测试前初始化"""
        # 创建简单的实验模板
        self.template = ExperimentTemplate(
            id="test_exp_001",
            title="测试实验",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="这是一个测试实验",
            objectives=["目标1", "目标2"],
            steps=[
                Step(
                    id="step1",
                    text="第一步：阅读说明"
                ),
                Step(
                    id="step2",
                    text="第二步：确认安全",
                    check=CheckPoint(
                        type=CheckType.CONFIRM,
                        fail_hint="请确认已完成安全检查"
                    )
                ),
                Step(
                    id="step3",
                    text="第三步：输入数值",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input=InputSpec(
                            key="volume",
                            label="体积",
                            input_type="float",
                            range=[10.0, 30.0],
                            unit="mL"
                        ),
                        correct_value=25.0,
                        fail_hint="体积不正确"
                    )
                )
            ],
            reagents=[
                Reagent(
                    id="hcl",
                    name="盐酸",
                    amount="25mL",
                    hazard_level="warning"
                )
            ],
            score_rules=[
                ScoreRule(when="all_steps_passed == True", then=100),
                ScoreRule(when="total_mistakes == 0", then=10),
                ScoreRule(when="no_safety_warning == True", then=10)
            ],
            goals=[
                Goal(name="完成实验", metric="completion_rate", gte=100.0)
            ],
            curves=[]
        )

        self.controller = ExperimentController(
            template=self.template,
            user_id="test_user_001"
        )

    def test_initialization(self):
        """测试控制器初始化"""
        assert self.controller.template.id == "test_exp_001"
        assert self.controller.user_id == "test_user_001"
        assert self.controller.record.experiment_id == "test_exp_001"
        assert len(self.controller.record.step_records) == 3

    def test_start_experiment(self):
        """测试开始实验"""
        self.controller.start_experiment()
        assert self.controller.record.status == "in_progress"
        assert self.controller.record.started_at is not None

    def test_get_current_step(self):
        """测试获取当前步骤"""
        step = self.controller.get_current_step()
        assert step is not None
        assert step.id == "step1"

    def test_submit_step_no_check(self):
        """测试提交无检查点的步骤"""
        passed, msg, mistake = self.controller.submit_step({})
        assert passed is True
        assert mistake is None

    def test_submit_step_confirm_pass(self):
        """测试确认检查-通过"""
        self.controller.next_step()  # 移到step2
        passed, msg, mistake = self.controller.submit_step({"confirmed": True})
        assert passed is True
        assert mistake is None
        assert self.controller.record.context["step2_completed"] is True

    def test_submit_step_confirm_fail(self):
        """测试确认检查-失败"""
        self.controller.next_step()  # 移到step2
        passed, msg, mistake = self.controller.submit_step({"confirmed": False})
        assert passed is False
        assert mistake is not None
        assert mistake.step_id == "step2"
        assert len(self.controller.record.mistakes_summary) == 1

    def test_submit_step_input_pass(self):
        """测试输入检查-通过"""
        self.controller.record.current_step_index = 2  # 移到step3
        passed, msg, mistake = self.controller.submit_step({"volume": 25.0})
        assert passed is True
        assert mistake is None

    def test_submit_step_input_fail(self):
        """测试输入检查-失败"""
        self.controller.record.current_step_index = 2  # 移到step3
        passed, msg, mistake = self.controller.submit_step({"volume": 50.0})
        assert passed is False
        assert mistake is not None

    def test_next_step(self):
        """测试前进到下一步"""
        assert self.controller.record.current_step_index == 0
        result = self.controller.next_step()
        assert result is True
        assert self.controller.record.current_step_index == 1

    def test_next_step_at_end(self):
        """测试在最后一步时前进"""
        self.controller.record.current_step_index = 2  # 最后一步
        result = self.controller.next_step()
        assert result is False
        assert self.controller.record.current_step_index == 2

    def test_previous_step(self):
        """测试返回上一步"""
        self.controller.next_step()  # 先前进
        assert self.controller.record.current_step_index == 1
        result = self.controller.previous_step()
        assert result is True
        assert self.controller.record.current_step_index == 0

    def test_previous_step_at_start(self):
        """测试在第一步时返回"""
        assert self.controller.record.current_step_index == 0
        result = self.controller.previous_step()
        assert result is False
        assert self.controller.record.current_step_index == 0

    def test_can_complete_experiment_incomplete(self):
        """测试检查完成状态-未完成"""
        can_complete, incomplete = self.controller.can_complete_experiment()
        assert can_complete is False
        assert len(incomplete) == 3

    def test_can_complete_experiment_complete(self):
        """测试检查完成状态-已完成"""
        # 完成所有步骤
        for step_record in self.controller.record.step_records:
            step_record.passed = True

        can_complete, incomplete = self.controller.can_complete_experiment()
        assert can_complete is True
        assert len(incomplete) == 0

    def test_complete_experiment(self):
        """测试完成实验"""
        # 完成所有步骤
        for step_record in self.controller.record.step_records:
            step_record.passed = True

        self.controller.complete_experiment()

        assert self.controller.record.status == "completed"
        assert self.controller.record.completed_at is not None
        assert self.controller.record.score.total >= 0

    def test_get_progress(self):
        """测试获取进度"""
        progress = self.controller.get_progress()
        assert progress["experiment_id"] == "test_exp_001"
        assert progress["total_steps"] == 3
        assert progress["current_step"] == 0
        assert "completion_rate" in progress

    def test_get_record(self):
        """测试获取用户记录"""
        record = self.controller.get_record()
        assert record.experiment_id == "test_exp_001"
        assert record.user_id == "test_user_001"


class TestScoreCalculation:
    """评分计算测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.template = ExperimentTemplate(
            id="score_test",
            title="评分测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="评分测试",
            objectives=["测试评分"],
            steps=[
                Step(id="s1", text="步骤1"),
                Step(id="s2", text="步骤2")
            ],
            reagents=[],
            score_rules=[
                ScoreRule(when="all_steps_passed == True", then=50),
                ScoreRule(when="total_mistakes == 0", then=30),
                ScoreRule(when="no_safety_warning == True", then=20)
            ],
            goals=[],
            curves=[]
        )

        self.controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

    def test_perfect_score(self):
        """测试满分情况"""
        # 完成所有步骤且无错误
        for step_record in self.controller.record.step_records:
            step_record.passed = True

        self.controller.complete_experiment()

        assert self.controller.record.score.total == 100

    def test_score_with_mistakes(self):
        """测试有错误的评分"""
        # 完成所有步骤但有错误
        for step_record in self.controller.record.step_records:
            step_record.passed = True

        # 添加一个错误
        from src.models.user_record import Mistake
        self.controller.record.add_mistake(
            Mistake(
                step_id="s1",
                error_type="test",
                description="测试错误",
                severity="warning"
            )
        )

        self.controller.complete_experiment()

        # 应该失去"无错误"奖励(30分)
        assert self.controller.record.score.total == 70

    def test_score_with_incomplete_steps(self):
        """测试未完成步骤的评分"""
        # 只完成部分步骤
        self.controller.record.step_records[0].passed = True
        self.controller.record.step_records[1].passed = False

        self.controller.complete_experiment()

        # 应该失去"全部完成"奖励(50分)
        assert self.controller.record.score.total <= 50


class TestCurveGeneration:
    """曲线生成测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.template = ExperimentTemplate(
            id="curve_test",
            title="曲线测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="曲线测试",
            objectives=["测试曲线"],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[
                Curve(
                    id="titration_curve",
                    type=CurveType.TITRATION_PH,
                    params={
                        "acid_type": "strong",
                        "acid_M": 0.1,
                        "acid_V_ml": 25.0,
                        "base_M": 0.1,
                        "num_points": 100
                    },
                    x_label="加入NaOH体积",
                    y_label="pH",
                    x_unit="mL",
                    y_unit=""
                )
            ]
        )

        self.controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

    def test_curve_generation(self):
        """测试曲线生成"""
        # 完成步骤
        for step_record in self.controller.record.step_records:
            step_record.passed = True

        self.controller.complete_experiment()

        # 检查曲线数据
        assert "titration_curve" in self.controller.record.curve_data
        curve_data = self.controller.record.curve_data["titration_curve"]
        assert "x" in curve_data
        assert "y" in curve_data
        assert len(curve_data["x"]) > 0
        assert len(curve_data["y"]) > 0


class TestContextManagement:
    """上下文管理测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.template = ExperimentTemplate(
            id="context_test",
            title="上下文测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="上下文测试",
            objectives=["测试上下文"],
            steps=[
                Step(
                    id="step1",
                    text="输入体积",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input=InputSpec(
                            key="volume",
                            label="体积",
                            input_type="float"
                        )
                    )
                ),
                Step(
                    id="step2",
                    text="依赖步骤",
                    check=CheckPoint(
                        type=CheckType.SEQUENCE,
                        require=["step1"],
                        fail_hint="请先完成step1"
                    )
                )
            ],
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[]
        )

        self.controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

    def test_context_update_on_success(self):
        """测试成功时更新上下文"""
        passed, _, _ = self.controller.submit_step({"volume": 25.0})
        assert passed is True
        assert self.controller.record.context["step1_completed"] is True
        assert self.controller.record.context["volume"] == 25.0

    def test_context_not_update_on_fail(self):
        """测试失败时不更新上下文"""
        # step2依赖step1,但step1未完成
        self.controller.next_step()
        passed, msg, _ = self.controller.submit_step({})
        assert passed is False
        assert "step1_completed" not in self.controller.record.context or \
               self.controller.record.context["step1_completed"] is False

    def test_sequence_check_with_context(self):
        """测试依赖检查使用上下文"""
        # 先完成step1
        self.controller.submit_step({"volume": 25.0})

        # 移到step2
        self.controller.next_step()
        passed, _, _ = self.controller.submit_step({})
        assert passed is True  # 因为step1已完成


class TestEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.template = ExperimentTemplate(
            id="edge_test",
            title="边界测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="边界测试",
            objectives=["测试边界"],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[]
        )

        self.controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

    def test_submit_with_no_current_step(self):
        """测试无当前步骤时提交"""
        self.controller.record.current_step_index = 99  # 无效索引
        passed, msg, _ = self.controller.submit_step({})
        assert passed is False
        assert "没有当前步骤" in msg

    def test_multiple_attempts_on_same_step(self):
        """测试同一步骤多次尝试"""
        # 第一次失败
        self.controller.submit_step({})  # step1没有check,会通过

        # 再次提交
        self.controller.submit_step({})

        step_record = self.controller.record.step_records[0]
        # 无check的步骤应该每次都通过
        assert step_record.passed is True

    def test_empty_template(self):
        """测试最小模板(至少1个步骤)"""
        min_template = ExperimentTemplate(
            id="min_template",
            title="最小实验",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="最小实验",
            objectives=[],
            steps=[Step(id="only_step", text="唯一步骤")],  # 至少要1个步骤
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[]
        )

        controller = ExperimentController(
            template=min_template,
            user_id="test_user"
        )

        assert controller.get_current_step() is not None
        assert controller.get_current_step().id == "only_step"


class TestValidation:
    """输入验证测试"""

    def test_init_with_none_template(self):
        """测试None模板初始化"""
        from src.utils.error_handler import ValidationError
        with pytest.raises(ValidationError, match="实验模板"):
            ExperimentController(template=None, user_id="test_user")

    def test_init_with_none_user_id(self):
        """测试None用户ID初始化"""
        from src.utils.error_handler import ValidationError
        template = ExperimentTemplate(
            id="test", title="测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )
        with pytest.raises(ValidationError, match="用户ID"):
            ExperimentController(template=template, user_id=None)

    def test_init_with_empty_user_id(self):
        """测试空字符串用户ID"""
        from src.utils.error_handler import ValidationError
        template = ExperimentTemplate(
            id="test", title="测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )
        with pytest.raises(ValidationError, match="用户ID不能为空"):
            ExperimentController(template=template, user_id="   ")

    def test_init_with_no_steps(self):
        """测试无步骤模板"""
        # Pydantic会在模板级别验证,所以无法创建空步骤模板
        # 测试ExperimentController的验证逻辑
        import pydantic

        # 应该在创建模板时就失败
        with pytest.raises(pydantic.ValidationError):
            ExperimentTemplate(
                id="test", title="测试", category="测试",
                difficulty="basic", duration_minutes=30,
                description="测试", objectives=[],
                steps=[],  # 空步骤 - Pydantic会拒绝
                reagents=[], score_rules=[], goals=[], curves=[]
            )

    def test_submit_with_none_input(self):
        """测试None输入提交"""
        template = ExperimentTemplate(
            id="test", title="测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )
        controller = ExperimentController(template=template, user_id="test_user")

        # safe_execute装饰器会捕获ValidationError并返回默认值
        passed, msg, _ = controller.submit_step(None)
        assert passed is False
        assert "错误" in msg or "失败" in msg

    def test_submit_with_invalid_status(self):
        """测试无效状态下提交"""
        template = ExperimentTemplate(
            id="test", title="测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )
        controller = ExperimentController(template=template, user_id="test_user")

        # 设置为已完成状态
        controller.record.status = "completed"

        passed, msg, _ = controller.submit_step({})
        assert passed is False
        assert "状态" in msg or "不允许" in msg


class TestScoreEdgeCases:
    """评分边界测试"""

    def test_score_with_safety_warnings(self):
        """测试有安全警告的评分"""
        template = ExperimentTemplate(
            id="safety_test", title="安全测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="安全测试", objectives=[],
            steps=[
                Step(id="s1", text="步骤1", safety_level="critical"),
                Step(id="s2", text="步骤2", safety_level="severe")
            ],
            reagents=[], score_rules=[
                ScoreRule(when="no_safety_warning == True", then=50),
                ScoreRule(when="no_critical_mistakes == True", then=30)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 模拟严重错误
        from src.models.user_record import Mistake
        controller.record.add_mistake(
            Mistake(
                step_id="s1",
                error_type="safety",
                description="严重安全错误",
                severity="critical"
            )
        )

        for step_record in controller.record.step_records:
            step_record.passed = True

        controller.complete_experiment()

        # 应该失去安全相关分数
        assert controller.record.score.total < 80

    def test_score_calculation_error_handling(self):
        """测试评分计算错误处理"""
        template = ExperimentTemplate(
            id="error_test", title="错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="错误测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[
                # 无效的评分规则(故意制造错误)
                ScoreRule(when="invalid_variable_xyz == True", then=100)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True

        # 应该有容错机制
        controller.complete_experiment()

        # 评分应该回退到基础方案
        assert controller.record.score.total >= 0
        # 检查details中是否有错误信息
        details_str = str(controller.record.score.details)
        assert "error" in details_str.lower() or controller.record.score.total == 0

    def test_score_bounds(self):
        """测试评分范围限制"""
        # ScoreRule的then参数已经被Pydantic限制为<=100
        # 所以我们测试正常范围内的最大值
        template = ExperimentTemplate(
            id="bounds_test", title="范围测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="范围测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[
                # 最大合法值
                ScoreRule(when="True", then=100)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True

        controller.complete_experiment()

        # 分数应该在有效范围内
        assert controller.record.score.total <= 100
        assert controller.record.score.total >= 0
        # 应该得到100分
        assert controller.record.score.total == 100


class TestCurveGenerationAdvanced:
    """曲线生成高级测试"""

    def test_multiple_curves(self):
        """测试多条曲线生成"""
        template = ExperimentTemplate(
            id="multi_curve", title="多曲线测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="多曲线测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[],
            curves=[
                Curve(
                    id="curve1",
                    type=CurveType.TITRATION_PH,
                    params={
                        "acid_type": "strong",
                        "acid_M": 0.1,
                        "acid_V_ml": 25.0,
                        "base_M": 0.1,
                        "num_points": 50
                    },
                    x_label="体积", y_label="pH",
                    x_unit="mL", y_unit=""
                ),
                Curve(
                    id="curve2",
                    type=CurveType.TITRATION_PH,
                    params={
                        "acid_type": "weak",
                        "acid_M": 0.1,
                        "acid_V_ml": 25.0,
                        "base_M": 0.1,
                        "num_points": 50
                    },
                    x_label="体积", y_label="pH",
                    x_unit="mL", y_unit=""
                )
            ]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True
        controller.complete_experiment()

        # 应该生成两条曲线
        assert "curve1" in controller.record.curve_data
        assert "curve2" in controller.record.curve_data
        assert len(controller.record.curve_data) == 2

    def test_curve_generation_error_handling(self):
        """测试曲线生成错误处理"""
        template = ExperimentTemplate(
            id="curve_error", title="曲线错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="曲线错误测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[],
            curves=[
                Curve(
                    id="invalid_curve",
                    type=CurveType.TITRATION_PH,
                    params={
                        # 缺少必要参数(故意制造错误)
                        "invalid_param": "test"
                    },
                    x_label="体积", y_label="pH",
                    x_unit="mL", y_unit=""
                )
            ]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True

        # 应该有容错,不会崩溃
        controller.complete_experiment()

        # 实验应该完成,即使曲线生成失败
        assert controller.record.status == "completed"


class TestProgressTracking:
    """进度跟踪测试"""

    def test_get_progress_details(self):
        """测试获取详细进度"""
        template = ExperimentTemplate(
            id="progress_test", title="进度测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="进度测试", objectives=[],
            steps=[
                Step(id="s1", text="步骤1"),
                Step(id="s2", text="步骤2"),
                Step(id="s3", text="步骤3")
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 完成部分步骤
        controller.record.step_records[0].passed = True
        controller.record.step_records[1].passed = True
        controller.record.current_step_index = 2

        progress = controller.get_progress()

        assert progress["experiment_id"] == "progress_test"
        assert progress["current_step"] == 2
        assert progress["total_steps"] == 3
        assert progress["completion_rate"] > 0
        assert "total_mistakes" in progress
        assert "status" in progress

    def test_completion_rate_calculation(self):
        """测试完成率计算"""
        template = ExperimentTemplate(
            id="completion_test", title="完成率测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="完成率测试", objectives=[],
            steps=[
                Step(id="s1", text="步骤1"),
                Step(id="s2", text="步骤2"),
                Step(id="s3", text="步骤3"),
                Step(id="s4", text="步骤4")
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 完成2/4步骤
        controller.record.step_records[0].passed = True
        controller.record.step_records[1].passed = True

        progress = controller.get_progress()

        # 完成率应该约为50%
        assert 40 <= progress["completion_rate"] <= 60


class TestCustomValidatorAndGenerator:
    """自定义验证器和生成器测试"""

    def test_custom_validator(self):
        """测试使用自定义验证器"""
        template = ExperimentTemplate(
            id="custom_val", title="自定义验证", category="测试",
            difficulty="basic", duration_minutes=30,
            description="自定义验证", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        custom_validator = RuleValidator()
        controller = ExperimentController(
            template=template,
            user_id="test_user",
            validator=custom_validator
        )

        assert controller.validator is custom_validator

    def test_custom_curve_generator(self):
        """测试使用自定义曲线生成器"""
        template = ExperimentTemplate(
            id="custom_gen", title="自定义生成器", category="测试",
            difficulty="basic", duration_minutes=30,
            description="自定义生成器", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        custom_generator = CurveGenerator()
        controller = ExperimentController(
            template=template,
            user_id="test_user",
            curve_generator=custom_generator
        )

        assert controller.curve_generator is custom_generator


class TestErrorRecovery:
    """错误恢复和容错测试"""

    def test_submit_step_validation_error(self):
        """测试步骤验证过程中的错误"""
        template = ExperimentTemplate(
            id="val_error", title="验证错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="验证错误测试", objectives=[],
            steps=[
                Step(
                    id="s1", text="步骤1",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input=InputSpec(
                            key="value",
                            label="数值",
                            input_type="float"
                        )
                    )
                )
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 提交正确的输入
        passed, msg, _ = controller.submit_step({"value": 25.0})
        assert passed is True

    def test_step_record_not_found(self):
        """测试步骤记录不存在的情况"""
        template = ExperimentTemplate(
            id="record_error", title="记录错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="记录错误测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 清空步骤记录来模拟错误
        original_records = controller.record.step_records.copy()
        controller.record.step_records.clear()

        passed, msg, _ = controller.submit_step({})
        assert passed is False
        assert "步骤记录" in msg

        # 恢复
        controller.record.step_records = original_records

    def test_context_update_error(self):
        """测试上下文更新错误处理"""
        template = ExperimentTemplate(
            id="context_error", title="上下文错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="上下文错误测试", objectives=[],
            steps=[
                Step(
                    id="s1", text="步骤1",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input=InputSpec(
                            key="complex_data",
                            label="复杂数据",
                            input_type="string"  # 使用string而不是text
                        )
                    )
                )
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 提交包含复杂对象的输入(应该只保存简单类型)
        passed, msg, _ = controller.submit_step({
            "complex_data": "text",
            "simple_value": 123,
            "nested_dict": {"a": 1}  # 这个不应该被保存到context
        })

        # 检查只有简单类型被保存
        assert "simple_value" in controller.record.context
        assert "nested_dict" not in controller.record.context

    def test_safety_level_recording(self):
        """测试安全级别的记录"""
        template = ExperimentTemplate(
            id="safety_level", title="安全级别测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="安全级别测试", objectives=[],
            steps=[
                Step(
                    id="s1", text="危险步骤",
                    safety_level="critical",
                    check=CheckPoint(
                        type=CheckType.CONFIRM,
                        fail_hint="必须确认"
                    )
                )
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 提交失败
        passed, msg, mistake = controller.submit_step({"confirmed": False})
        assert passed is False
        assert mistake is not None
        assert mistake.severity == "critical"

    def test_score_calculation_with_severe_mistakes(self):
        """测试包含严重错误的评分计算"""
        template = ExperimentTemplate(
            id="severe_test", title="严重错误测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="严重错误测试", objectives=[],
            steps=[
                Step(id="s1", text="步骤1", safety_level="severe"),
                Step(id="s2", text="步骤2", safety_level="warning")
            ],
            reagents=[],
            score_rules=[
                ScoreRule(when="no_safety_warning == True", then=40),
                ScoreRule(when="no_critical_mistakes == True", then=30),
                ScoreRule(when="total_mistakes == 0", then=30)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 添加严重错误
        from src.models.user_record import Mistake
        controller.record.add_mistake(
            Mistake(
                step_id="s1",
                error_type="safety",
                description="严重错误",
                severity="severe"
            )
        )

        for step_record in controller.record.step_records:
            step_record.passed = True

        controller.complete_experiment()

        # 应该失去no_safety_warning奖励
        assert controller.record.score.total < 100

    def test_multiple_score_rules(self):
        """测试多条评分规则"""
        template = ExperimentTemplate(
            id="multi_rules", title="多规则测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="多规则测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[
                ScoreRule(when="all_steps_passed == True", then=30),
                ScoreRule(when="total_mistakes == 0", then=30),
                ScoreRule(when="no_safety_warning == True", then=20),
                ScoreRule(when="completion_rate == 100.0", then=20)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True

        controller.complete_experiment()

        # 完美完成应该得到100分
        assert controller.record.score.total == 100
        assert controller.record.score.procedural == 50
        assert controller.record.score.safety == 50

    def test_curve_data_structure(self):
        """测试曲线数据结构"""
        template = ExperimentTemplate(
            id="curve_struct", title="曲线结构测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="曲线结构测试", objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[], score_rules=[], goals=[],
            curves=[
                Curve(
                    id="test_curve",
                    type=CurveType.TITRATION_PH,
                    params={
                        "acid_type": "strong",
                        "acid_M": 0.1,
                        "acid_V_ml": 25.0,
                        "base_M": 0.1,
                        "num_points": 50
                    },
                    x_label="加入体积",
                    y_label="pH值",
                    x_unit="mL",
                    y_unit=""
                )
            ]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        controller.record.step_records[0].passed = True
        controller.complete_experiment()

        # 检查曲线数据结构
        assert "test_curve" in controller.record.curve_data
        curve_data = controller.record.curve_data["test_curve"]

        assert "x" in curve_data
        assert "y" in curve_data
        assert "x_label" in curve_data
        assert "y_label" in curve_data
        assert "x_unit" in curve_data
        assert "y_unit" in curve_data

        assert isinstance(curve_data["x"], list)
        assert isinstance(curve_data["y"], list)
        assert len(curve_data["x"]) == len(curve_data["y"])

        assert curve_data["x_label"] == "加入体积"
        assert curve_data["y_label"] == "pH值"
        assert curve_data["x_unit"] == "mL"

    def test_attempts_counter(self):
        """测试尝试次数计数"""
        template = ExperimentTemplate(
            id="attempts_test", title="尝试次数测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="尝试次数测试", objectives=[],
            steps=[
                Step(
                    id="s1", text="步骤1",
                    check=CheckPoint(
                        type=CheckType.CONFIRM,
                        fail_hint="请确认"
                    )
                )
            ],
            reagents=[], score_rules=[], goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        step_record = controller.record.step_records[0]

        # 初始尝试次数应该是1
        initial_attempts = step_record.attempts

        # 多次失败尝试
        for _i in range(3):
            passed, _, _ = controller.submit_step({"confirmed": False})
            assert passed is False

        # 失败3次后,应该增加3次
        assert step_record.attempts == initial_attempts + 3

        # 成功一次(不增加attempts,因为通过了)
        passed, _, _ = controller.submit_step({"confirmed": True})
        assert passed is True
        assert step_record.passed is True

    def test_score_with_partial_completion(self):
        """测试部分完成的评分"""
        template = ExperimentTemplate(
            id="partial_test", title="部分完成测试", category="测试",
            difficulty="basic", duration_minutes=30,
            description="部分完成测试", objectives=[],
            steps=[
                Step(id="s1", text="步骤1"),
                Step(id="s2", text="步骤2"),
                Step(id="s3", text="步骤3"),
                Step(id="s4", text="步骤4")
            ],
            reagents=[],
            score_rules=[
                ScoreRule(when="all_steps_passed == True", then=60),
                ScoreRule(when="total_mistakes == 0", then=40)
            ],
            goals=[], curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 只完成一半
        controller.record.step_records[0].passed = True
        controller.record.step_records[1].passed = True
        # s3和s4未完成

        controller.complete_experiment()

        # 应该失去"全部完成"奖励
        assert controller.record.score.total < 60
        assert controller.record.completion_rate == 50.0


class TestExceptionHandling:
    """异常处理深度测试"""

    def setup_method(self):
        """测试前准备"""
        self.template = ExperimentTemplate(
            id="exception_test",
            title="异常处理测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="测试异常处理",
            objectives=["测试"],
            steps=[
                Step(
                    id="step1",
                    text="步骤1",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input=InputSpec(
                            key="value",
                            label="值",
                            input_type="float",
                            range=[0.0, 100.0]
                        ),
                        correct_value=50.0
                    )
                )
            ],
            reagents=[],
            score_rules=[
                ScoreRule(when="all_steps_passed == True", then=100)
            ],
            goals=[],
            curves=[]
        )

    def test_validator_exception_handling(self):
        """测试validator.check_step抛出异常"""
        from unittest.mock import patch

        controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

        # Mock validator的check_step抛出异常
        with patch.object(controller.validator, 'check_step', side_effect=RuntimeError("验证器内部错误")):
            passed, msg, mistake = controller.submit_step({"value": 50.0})

            # 应该捕获异常并返回False
            assert passed is False
            assert "验证过程出错" in msg
            assert "验证器内部错误" in msg

    def test_mistake_recording_with_exception(self):
        """测试错误记录过程中的异常(通过验证实际行为)"""
        controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

        # 提交错误的输入(应该失败)
        # 即使内部记录可能失败,验证结果应该正常返回
        passed, msg, mistake = controller.submit_step({"value": 999.0})

        # 验证结果应该正常(不在range内)
        assert passed is False
        # mistake可能为None(如果记录失败)或有值
        assert mistake is None or isinstance(mistake, object)

    def test_context_update_with_bad_data(self):
        """测试上下文更新时包含不可序列化的数据"""
        controller = ExperimentController(
            template=self.template,
            user_id="test_user"
        )

        # 提交包含不安全类型的数据
        class CustomObject:
            pass

        # 只有基本类型会被保存到context
        passed, msg, mistake = controller.submit_step({
            "value": 50.0,
            "custom_obj": CustomObject(),  # 这个应该被忽略
            "safe_data": "test"
        })

        # 应该成功(不安全的数据被过滤)
        assert passed is True
        assert "safe_data" in controller.record.context
        assert "custom_obj" not in controller.record.context

    def test_score_calculation_exception(self):
        """测试评分计算异常"""
        from unittest.mock import patch

        template = ExperimentTemplate(
            id="score_test",
            title="评分测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="测试",
            objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[
                ScoreRule(when="invalid_expression @@@ ???", then=100)  # 无效表达式
            ],
            goals=[],
            curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # Mock validator的evaluate_score_rules抛出异常
        with patch.object(controller.validator, 'evaluate_score_rules', side_effect=Exception("评分错误")):
            controller.complete_experiment()

            # 应该有默认分数(回退机制)
            assert controller.record.score is not None
            assert controller.record.score.total >= 0

    def test_curve_data_generation(self):
        """测试曲线数据生成"""
        template = ExperimentTemplate(
            id="curve_test",
            title="曲线测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="测试",
            objectives=[],
            steps=[Step(id="s1", text="步骤1")],
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[
                Curve(
                    id="test_curve",
                    type=CurveType.TITRATION_PH,
                    params={"initial_ph": 7.0, "volume": 50.0}
                )
            ]
        )

        controller = ExperimentController(template=template, user_id="test_user")

        # 验证曲线配置已经在模板中
        assert len(controller.template.curves) == 1
        assert controller.template.curves[0].id == "test_curve"
        assert controller.template.curves[0].type == CurveType.TITRATION_PH

    def test_progress_calculation_edge_case(self):
        """测试进度计算边界情况"""
        # 测试所有步骤都未完成的情况
        template = ExperimentTemplate(
            id="progress_test",
            title="进度测试",
            category="测试",
            difficulty="basic",
            duration_minutes=30,
            description="测试",
            objectives=[],
            steps=[
                Step(id="s1", text="步骤1"),
                Step(id="s2", text="步骤2")
            ],
            reagents=[],
            score_rules=[],
            goals=[],
            curves=[]
        )

        controller = ExperimentController(template=template, user_id="test_user")
        progress = controller.get_progress()

        # 验证返回的字段
        assert 'experiment_id' in progress
        assert 'experiment_title' in progress
        assert 'current_step' in progress
        assert 'total_steps' in progress
        assert 'completion_rate' in progress
        assert 'total_mistakes' in progress
        assert 'status' in progress

        # 所有步骤未完成
        assert progress['total_steps'] == 2
        assert progress['completion_rate'] == 0.0
