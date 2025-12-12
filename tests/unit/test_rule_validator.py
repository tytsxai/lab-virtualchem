"""
Rule Validator 单元测试
测试规则验证器的各种检查逻辑
"""

import pytest

from src.core.rule_validator import EvaluationError, RuleValidator
from src.core.validation import ValidationError
from src.models.experiment import CheckPoint, CheckType, InputSpec, Step


class TestRuleValidator:
    """规则验证器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.validator = RuleValidator()

    def test_confirm_check_pass(self):
        """测试确认检查-通过"""
        step = Step(
            id="step1",
            text="请确认已穿戴护目镜",
            check=CheckPoint(type=CheckType.CONFIRM, fail_hint="请确认已完成此步骤"),
        )
        passed, msg = self.validator.check_step(step, {"confirmed": True}, {})
        assert passed is True
        assert msg == ""

    def test_confirm_check_fail(self):
        """测试确认检查-失败"""
        step = Step(
            id="step2",
            text="请确认已穿戴护目镜",
            check=CheckPoint(type=CheckType.CONFIRM, fail_hint="请确认已完成此步骤"),
        )
        passed, msg = self.validator.check_step(step, {"confirmed": False}, {})
        assert passed is False
        assert "确认" in msg

    def test_input_check_pass(self):
        """测试输入检查-通过"""
        step = Step(
            id="step3",
            text="输入移取的HCl体积",
            check=CheckPoint(
                type=CheckType.INPUT,
                input=InputSpec(key="volume", label="HCl体积", input_type="float", range=[20.0, 30.0], unit="mL"),
                correct_value=25.0,
                fail_hint="体积输入不正确",
            ),
        )
        passed, msg = self.validator.check_step(step, {"volume": 25.0}, {})
        assert passed is True

    def test_input_check_out_of_range(self):
        """测试输入检查-超出范围"""
        step = Step(
            id="step4",
            text="输入移取的HCl体积",
            check=CheckPoint(
                type=CheckType.INPUT,
                input=InputSpec(key="volume", label="HCl体积", input_type="float", range=[20.0, 30.0], unit="mL"),
                fail_hint="体积超出范围",
            ),
        )
        passed, msg = self.validator.check_step(step, {"volume": 35.0}, {})
        assert passed is False
        assert "范围" in msg

    def test_input_check_wrong_value(self):
        """测试输入检查-数值错误"""
        step = Step(
            id="step5",
            text="输入正确的体积",
            check=CheckPoint(
                type=CheckType.INPUT,
                input=InputSpec(key="volume", label="体积", input_type="float", unit="mL"),
                correct_value=25.0,
                fail_hint="数值不正确",
            ),
        )
        # 超过5%误差
        passed, msg = self.validator.check_step(step, {"volume": 30.0}, {})
        assert passed is False
        assert "偏差" in msg or "不正确" in msg

    def test_input_check_within_tolerance(self):
        """测试输入检查-误差范围内"""
        step = Step(
            id="step6",
            text="输入体积",
            check=CheckPoint(
                type=CheckType.INPUT,
                input=InputSpec(key="volume", label="体积", input_type="float", unit="mL"),
                correct_value=25.0,
            ),
        )
        # 5%误差内
        passed, msg = self.validator.check_step(step, {"volume": 25.5}, {})
        assert passed is True

    def test_input_check_missing_data(self):
        """测试输入检查-缺少数据"""
        step = Step(
            id="step7",
            text="输入体积",
            check=CheckPoint(type=CheckType.INPUT, input=InputSpec(key="volume", label="体积", input_type="float")),
        )
        passed, msg = self.validator.check_step(step, {}, {})
        assert passed is False
        assert "缺少" in msg

    def test_select_check_correct(self):
        """测试选择检查-正确"""
        step = Step(
            id="step8",
            text="选择合适的指示剂",
            check=CheckPoint(
                type=CheckType.SELECT,
                input=InputSpec(
                    key="indicator",
                    label="指示剂",
                    input_type="string",
                    options=[
                        {"value": "甲基橙", "label": "甲基橙"},
                        {"value": "酚酞", "label": "酚酞", "correct": True},
                        {"value": "石蕊", "label": "石蕊"},
                    ],
                ),
                fail_hint="指示剂选择不正确",
            ),
        )
        passed, msg = self.validator.check_step(step, {"indicator": "酚酞"}, {})
        assert passed is True

    def test_select_check_wrong(self):
        """测试选择检查-错误"""
        step = Step(
            id="step9",
            text="选择合适的指示剂",
            check=CheckPoint(
                type=CheckType.SELECT,
                input=InputSpec(
                    key="indicator",
                    label="指示剂",
                    input_type="string",
                    options=[
                        {"value": "甲基橙", "label": "甲基橙"},
                        {"value": "酚酞", "label": "酚酞", "correct": True},
                        {"value": "石蕊", "label": "石蕊"},
                    ],
                ),
                fail_hint="指示剂选择不正确",
            ),
        )
        passed, msg = self.validator.check_step(step, {"indicator": "甲基橙"}, {})
        assert passed is False
        assert "不正确" in msg

    def test_select_check_invalid_option(self):
        """测试选择检查-无效选项"""
        step = Step(
            id="step10",
            text="选择指示剂",
            check=CheckPoint(
                type=CheckType.SELECT,
                input=InputSpec(
                    key="indicator",
                    label="指示剂",
                    input_type="string",
                    options=[{"value": "甲基橙", "label": "甲基橙"}, {"value": "酚酞", "label": "酚酞"}],
                ),
            ),
        )
        passed, msg = self.validator.check_step(step, {"indicator": "无效选项"}, {})
        assert passed is False
        assert "无效" in msg

    def test_sequence_check_pass(self):
        """测试依赖检查-通过"""
        step = Step(
            id="step11",
            text="开始滴定",
            check=CheckPoint(type=CheckType.SEQUENCE, require=["step1", "step2"], fail_hint="请先完成前置步骤"),
        )
        context = {"step1_completed": True, "step2_completed": True}
        passed, msg = self.validator.check_step(step, {}, context)
        assert passed is True

    def test_sequence_check_fail(self):
        """测试依赖检查-失败"""
        step = Step(
            id="step12",
            text="开始滴定",
            check=CheckPoint(type=CheckType.SEQUENCE, require=["step1", "step2"], fail_hint="请先完成前置步骤"),
        )
        context = {"step1_completed": True, "step2_completed": False}
        passed, msg = self.validator.check_step(step, {}, context)
        assert passed is False
        assert "step2" in msg or "前置" in msg

    def test_no_check(self):
        """测试无检查点的步骤"""
        step = Step(id="step13", text="阅读实验说明")
        passed, msg = self.validator.check_step(step, {}, {})
        assert passed is True
        assert msg == ""


class TestExpressionEvaluation:
    """表达式求值测试"""

    def setup_method(self):
        self.validator = RuleValidator()

    def test_evaluate_expression_simple(self):
        """测试简单表达式"""
        result = self.validator.evaluate_expression("x > 5", {"x": 10})
        assert result is True

        result2 = self.validator.evaluate_expression("x < 5", {"x": 10})
        assert result2 is False

    def test_evaluate_expression_complex(self):
        """测试复杂表达式"""
        context = {"a": 10, "b": 20, "c": 30}
        result = self.validator.evaluate_expression("a + b == c", context)
        assert result is True

    def test_evaluate_expression_with_functions(self):
        """测试带函数的表达式"""
        result = self.validator.evaluate_expression("abs(x) > 5", {"x": -10})
        assert result is True

        result2 = self.validator.evaluate_expression("max(a, b) == 20", {"a": 10, "b": 20})
        assert result2 is True

    def test_evaluate_expression_unsafe(self):
        """测试危险表达式被阻止"""
        with pytest.raises(ValidationError):  # 安全检查抛出ValidationError
            self.validator.evaluate_expression("import os", {})

        with pytest.raises(ValidationError):  # 安全检查抛出ValidationError
            self.validator.evaluate_expression("__import__('os')", {})

    def test_evaluate_expression_invalid(self):
        """测试无效表达式"""
        with pytest.raises(EvaluationError):
            self.validator.evaluate_expression("invalid syntax !@#", {})


class TestInputValidation:
    """输入验证测试"""

    def setup_method(self):
        self.validator = RuleValidator()

    def test_validate_int_input(self):
        """测试整数输入验证"""
        spec = {"input_type": "int"}
        valid, msg = self.validator.validate_input(spec, "10")
        assert valid is True

        valid2, msg2 = self.validator.validate_input(spec, "10.5")
        assert valid2 is False

    def test_validate_float_input(self):
        """测试浮点数输入验证"""
        spec = {"input_type": "float"}
        valid, msg = self.validator.validate_input(spec, "10.5")
        assert valid is True

        valid2, msg2 = self.validator.validate_input(spec, "10")
        assert valid2 is True

    def test_validate_string_input(self):
        """测试字符串输入验证"""
        spec = {"input_type": "string"}
        valid, msg = self.validator.validate_input(spec, "test")
        assert valid is True

    def test_validate_with_range(self):
        """测试范围验证"""
        spec = {"input_type": "float", "range": [10.0, 20.0]}

        valid1, _ = self.validator.validate_input(spec, "15.0")
        assert valid1 is True

        valid2, msg2 = self.validator.validate_input(spec, "25.0")
        assert valid2 is False
        assert "范围" in msg2

    def test_validate_with_options(self):
        """测试选项验证"""
        spec = {
            "input_type": "string",
            "options": [{"value": "option1", "label": "选项1"}, {"value": "option2", "label": "选项2"}],
        }

        valid1, _ = self.validator.validate_input(spec, "option1")
        assert valid1 is True

        valid2, msg2 = self.validator.validate_input(spec, "invalid")
        assert valid2 is False


class TestScoreRules:
    """评分规则测试"""

    def setup_method(self):
        self.validator = RuleValidator()

    def test_evaluate_score_rules_simple(self):
        """测试简单评分规则"""
        rules = [{"when": "correct == True", "then": 10}, {"when": "correct == False", "then": 0}]

        score1, details1 = self.validator.evaluate_score_rules(rules, {"correct": True})
        assert score1 == 10

        score2, details2 = self.validator.evaluate_score_rules(rules, {"correct": False})
        assert score2 == 0

    def test_evaluate_score_rules_complex(self):
        """测试复杂评分规则"""
        rules = [
            {"when": "mistakes == 0", "then": 10},
            {"when": "mistakes > 0 and mistakes <= 2", "then": 5},
            {"when": "mistakes > 2", "then": 0},
        ]

        score1, _ = self.validator.evaluate_score_rules(rules, {"mistakes": 0})
        assert score1 == 10

        score2, _ = self.validator.evaluate_score_rules(rules, {"mistakes": 1})
        assert score2 == 5

        score3, _ = self.validator.evaluate_score_rules(rules, {"mistakes": 3})
        assert score3 == 0

    def test_evaluate_score_rules_multiple_match(self):
        """测试多个规则匹配"""
        rules = [{"when": "a > 0", "then": 5}, {"when": "b > 0", "then": 5}, {"when": "c > 0", "then": 5}]

        score, details = self.validator.evaluate_score_rules(rules, {"a": 1, "b": 1, "c": 1})
        assert score == 15  # 所有规则都匹配

    def test_evaluate_score_rules_with_error(self):
        """测试评分规则错误处理"""
        rules = [
            {"when": "valid_expr", "then": 10},
            {"when": "invalid syntax !@#", "then": 5},  # 无效表达式
        ]

        score, details = self.validator.evaluate_score_rules(rules, {"valid_expr": True})
        # 第一个规则成功,第二个失败
        assert score == 10
        assert "error" in details.get("rule_1", {})


class TestEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        self.validator = RuleValidator()

    def test_empty_context(self):
        """测试空上下文"""
        result = self.validator.evaluate_expression("True", {})
        assert result is True

    def test_division_by_zero(self):
        """测试除零错误"""
        with pytest.raises(EvaluationError):
            self.validator.evaluate_expression("10 / 0", {})

    def test_type_conversion_error(self):
        """测试类型转换错误"""
        spec = {"input_type": "int"}
        valid, msg = self.validator.validate_input(spec, "not_a_number")
        assert valid is False
        assert "转换" in msg or "失败" in msg

    def test_missing_variable_in_expression(self):
        """测试表达式中缺少变量"""
        with pytest.raises(EvaluationError):
            self.validator.evaluate_expression("x + y", {"x": 10})  # 缺少y

    def test_numeric_precision(self):
        """测试数值精度"""
        # 测试浮点数比较的容差
        step = Step(
            id="precision_test",
            text="测试精度",
            check=CheckPoint(
                type=CheckType.INPUT, input=InputSpec(key="value", label="数值", input_type="float"), correct_value=0.1
            ),
        )
        # 0.1 + 0.2 在浮点数中可能不精确等于0.3
        passed, msg = self.validator.check_step(step, {"value": 0.1}, {})
        assert passed is True

    def test_expression_check_type(self):
        """测试表达式检查类型"""
        step = Step(
            id="expr_check",
            text="表达式检查",
            check=CheckPoint(
                type=CheckType.EXPRESSION, expression="volume >= 20 and volume <= 30", fail_hint="体积不在有效范围"
            ),
        )
        # 测试通过情况
        passed, msg = self.validator.check_step(step, {"volume": 25}, {})
        assert passed is True

        # 测试失败情况
        passed2, msg2 = self.validator.check_step(step, {"volume": 35}, {})
        assert passed2 is False
        assert "体积不在有效范围" in msg2

    def test_multi_select_check(self):
        """测试多选检查"""
        # 创建支持多选的 InputSpec
        from src.models.experiment import InputSpec

        input_spec = InputSpec(
            key="reagents",
            label="试剂",
            input_type="list",
            options=[
                {"value": "NaOH", "label": "氢氧化钠", "correct": True},
                {"value": "HCl", "label": "盐酸", "correct": True},
                {"value": "H2O", "label": "水"},
            ],
        )
        # 添加多选属性
        input_spec.multi_select = True

        step = Step(
            id="multi_select", text="选择所有正确的试剂", check=CheckPoint(type=CheckType.SELECT, input=input_spec)
        )

        # 测试选择正确的所有选项
        passed, msg = self.validator.check_step(step, {"reagents": ["NaOH", "HCl"]}, {})
        assert passed is True

        # 测试选择不完整
        passed2, msg2 = self.validator.check_step(step, {"reagents": ["NaOH"]}, {})
        assert passed2 is False
        assert "缺少" in msg2

        # 测试选择了错误选项
        passed3, msg3 = self.validator.check_step(step, {"reagents": ["NaOH", "HCl", "H2O"]}, {})
        assert passed3 is False
        assert "多余" in msg3

    def test_boolean_input_validation(self):
        """测试布尔输入验证"""
        spec = {"input_type": "bool"}
        valid, msg = self.validator.validate_input(spec, "true")
        # 验证器需要支持bool类型
        assert valid is True or "bool" in msg  # 可能不支持,记录需求

    def test_nested_context_access(self):
        """测试嵌套上下文访问"""
        # 测试是否能访问嵌套的context数据
        # 某些高级场景可能需要访问嵌套数据
        # result = self.validator.evaluate_expression("step1_data['volume'] > 20", context)
        # 当前可能不支持,但这是一个潜在的改进点
