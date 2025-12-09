"""规则验证器 - 检查步骤、输入、表达式"""

import logging
import re
from typing import Any, Optional

from simpleeval import EvalWithCompoundTypes, simple_eval


class SecurityError(Exception):
    """安全错误"""
    pass

from src.core.validation import ValidationError
from src.models.experiment import CheckType, Step
from src.models.validation import validate_range

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """表达式求值错误"""

    pass


class RuleValidator:
    """规则验证器"""

    # 危险模式黑名单
    DANGEROUS_PATTERNS = [
        r"__\w+__",  # 双下划线方法
        r"import\s+",  # import语句
        r"eval\s*\(",  # eval调用
        r"exec\s*\(",  # exec调用
        r"compile\s*\(",  # compile调用
        r"open\s*\(",  # 文件操作
        r"os\.",  # os模块
        r"sys\.",  # sys模块
        r"subprocess",  # subprocess模块
    ]

    def __init__(self, hazard_checker: Optional[Any] = None) -> None:
        """初始化验证器

        Args:
            hazard_checker: 危险检查器(可选)，用于未来扩展安全规则
        """
        self.hazard_checker = hazard_checker
        # 白名单函数
        self.allowed_functions = {
            "abs": abs,
            "min": min,
            "max": max,
            "len": len,
            "range": range,
            "round": round,
            "int": int,
            "float": float,
            "str": str,
        }

        # 创建安全的求值器
        self.evaluator = EvalWithCompoundTypes(
            functions=self.allowed_functions,
            names={},  # 变量在运行时提供
        )

        # 编译危险模式
        self._dangerous_regex = [re.compile(pattern) for pattern in self.DANGEROUS_PATTERNS]

        # 表达式长度限制
        self.max_expression_length = 500

        # 上下文变量数量限制
        self.max_context_vars = 100

    def _validate_expression_security(self, expression: str) -> None:
        """验证表达式的安全性

        Args:
            expression: 要验证的表达式

        Raises:
            SecurityError: 如果表达式包含危险模式
        """
        # 检查表达式长度
        if len(expression) > self.max_expression_length:
            raise SecurityError(f"表达式过长: {len(expression)} > {self.max_expression_length}")

        # 检查危险模式
        for regex in self._dangerous_regex:
            if regex.search(expression):
                raise SecurityError(f"表达式包含危险模式: {expression}")

        # 检查括号匹配
        if expression.count('(') != expression.count(')'):
            raise SecurityError("表达式括号不匹配")

        # 检查方括号匹配
        if expression.count('[') != expression.count(']'):
            raise SecurityError("表达式方括号不匹配")

    def check_step(self, step: Step, user_input: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
        """检查步骤是否通过

        Args:
            step: 步骤定义
            user_input: 用户输入
            context: 上下文变量(之前步骤的状态)

        Returns:
            (是否通过, 提示信息)
        """
        # 兼容旧版模板: 当 step.check 为空但存在 validation_rules 字段时，
        # 使用简单规则进行验证（例如 range 范围检查）。
        if step.check is None:
            legacy_rules = getattr(step, "validation_rules", None)
            if legacy_rules:
                return self._validate_legacy_rules(legacy_rules, user_input)
            return True, ""

        check = step.check

        try:
            if check.type == CheckType.CONFIRM:
                # 确认类型:用户必须明确确认
                confirmed = user_input.get("confirmed", False)
                if not confirmed:
                    return False, check.fail_hint or "请确认已完成此步骤"
                return True, ""

            elif check.type == CheckType.INPUT:
                # 输入类型:验证输入值
                if check.input is None:
                    return False, "INPUT类型缺少输入规范"

                key = check.input.key
                if key not in user_input:
                    return False, f"缺少输入: {check.input.label}"

                value = user_input[key]

                # 验证范围
                if check.input.range:
                    valid, error_msg = validate_range(float(value), check.input.range)
                    if not valid:
                        return False, error_msg

                # 验证正确值(如果设置)
                if check.correct_value is not None:
                    if isinstance(check.correct_value, (int, float)):
                        # 数值比较(允许误差)
                        tolerance = abs(check.correct_value * 0.05)  # 5%误差
                        if abs(float(value) - check.correct_value) > tolerance:
                            return False, check.fail_hint or "数值与期望值偏差较大"
                    else:
                        # 精确比较
                        if str(value) != str(check.correct_value):
                            return False, check.fail_hint or "输入值不正确"

                return True, ""

            elif check.type == CheckType.SELECT:
                # 选择类型:验证选项(支持单选和多选)
                if check.input is None or check.input.options is None:
                    return False, "SELECT类型缺少选项规范"

                key = check.input.key
                if key not in user_input:
                    return False, f"缺少选择: {check.input.label}"

                selected_value = user_input[key]
                is_multi_select = check.input.multi_select if hasattr(check.input, "multi_select") else False

                # 处理多选
                if is_multi_select:
                    # 确保选中的是列表
                    if not isinstance(selected_value, list):
                        selected_value = [selected_value]

                    # 检查所有选项是否有效
                    valid_values = [opt.get("value") for opt in check.input.options]
                    for val in selected_value:
                        if val not in valid_values:
                            return False, f"选择的选项无效: {val}"

                    # 检查是否选择了所有正确选项
                    correct_options = [opt.get("value") for opt in check.input.options if opt.get("correct", False)]
                    if correct_options:
                        selected_set = set(selected_value)
                        correct_set = set(correct_options)
                        if selected_set != correct_set:
                            missing = correct_set - selected_set
                            extra = selected_set - correct_set
                            hint = check.fail_hint or "选择不完全正确"
                            if missing:
                                hint += f" (缺少: {', '.join(missing)})"
                            if extra:
                                hint += f" (多余: {', '.join(extra)})"
                            return False, hint

                    return True, ""
                else:
                    # 单选模式
                    # 检查是否为有效选项
                    valid_values = [opt.get("value") for opt in check.input.options]
                    if selected_value not in valid_values:
                        return False, "选择的选项无效"

                    # 检查是否为正确选项
                    correct_options = [opt.get("value") for opt in check.input.options if opt.get("correct", False)]
                    if correct_options and selected_value not in correct_options:
                        return False, check.fail_hint or "选择不正确"

                    return True, ""

            elif check.type == CheckType.SEQUENCE:
                # 依赖关系:检查前置步骤
                if check.require is None:
                    return False, "SEQUENCE类型缺少依赖列表"

                for required_step_id in check.require:
                    # 检查前置步骤是否已完成
                    step_completed = context.get(f"{required_step_id}_completed", False)
                    if not step_completed:
                        return (
                            False,
                            check.fail_hint or f"请先完成步骤: {required_step_id}",
                        )

                return True, ""

            elif check.type == CheckType.EXPRESSION:
                # 表达式检查:评估自定义表达式
                if check.expression is None or not check.expression.strip():
                    return False, "EXPRESSION类型缺少表达式"

                try:
                    # 合并用户输入和上下文
                    eval_context = {**context, **user_input}

                    # 安全验证表达式
                    self._validate_expression_security(check.expression)

                    # 评估表达式 - 使用 simple_eval 而不是 evaluator.eval
                    result = simple_eval(check.expression, functions=self.allowed_functions, names=eval_context)

                    # 检查结果是否为True
                    if not result:
                        return False, check.fail_hint or "表达式验证失败"

                    return True, ""

                except EvaluationError as e:
                    logger.error(f"表达式评估错误: {e}")
                    return False, f"表达式评估错误: {str(e)}"
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.error(f"表达式检查失败 - {type(e).__name__}: {e}")
                    return False, f"表达式检查失败: {str(e)}"
                except Exception as e:
                    # 捕获其他未预期的异常，但记录类型以便后续优化
                    logger.error(f"表达式检查出现未预期错误 ({type(e).__name__}): {e}", exc_info=True)
                    return False, f"表达式检查失败: {str(e)}"

            else:
                logger.warning(f"未知的检查点类型: {check.type}")
                return True, ""

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"步骤检查失败 - {type(e).__name__}: {e}")
            return False, f"检查过程出错: {e}"
        except Exception as e:
            # 捕获其他未预期的异常
            logger.error(f"步骤检查出现未预期错误 ({type(e).__name__}): {e}", exc_info=True)
            return False, f"检查过程出错: {e}"

    def evaluate_expression(self, expression: str, context: dict[str, Any]) -> bool:
        """安全求值表达式

        Args:
            expression: 表达式字符串
            context: 变量字典

        Returns:
            求值结果(布尔值)

        Raises:
            EvaluationError: 表达式错误或超时
        """
        # 验证表达式安全性
        try:
            self._validate_expression_security(expression)
        except SecurityError as exc:
            logger.error(f"表达式安全检查失败: {exc}")
            raise ValidationError(message=str(exc)) from exc

        # 验证上下文大小
        if len(context) > self.max_context_vars:
            logger.warning(f"上下文变量过多: {len(context)}")
            # 只保留最近的变量
            context = dict(list(context.items())[-self.max_context_vars :])

        try:
            # 创建安全的上下文副本(防止修改原始数据)
            safe_context = {}
            for key, value in context.items():
                # 只允许基本类型
                if isinstance(value, (int, float, str, bool, list, dict)):
                    safe_context[key] = value

            # 更新求值器的变量
            self.evaluator.names = safe_context

            # 求值(自动超时保护)
            result = simple_eval(expression, functions=self.allowed_functions, names=safe_context)

            # 转换为布尔值
            return bool(result)

        except (ValueError, TypeError, KeyError, AttributeError, NameError) as e:
            logger.error(f"表达式求值失败: {expression} - {type(e).__name__}: {e}")
            raise EvaluationError(f"表达式求值失败: {e}") from e
        except Exception as e:
            # 捕获其他未预期的异常
            logger.error(f"表达式求值出现未预期错误 ({type(e).__name__}): {expression} - {e}", exc_info=True)
            raise EvaluationError(f"表达式求值失败: {e}") from e

    def validate_input(self, input_spec: dict[str, Any], value: Any) -> tuple[bool, str]:
        """验证用户输入"""
        input_type = input_spec.get("input_type", "float")

        try:
            if input_type == "int":
                value = int(value)
            elif input_type == "float":
                value = float(value)
            elif input_type == "string":
                value = str(value)
            elif input_type == "bool":
                value = bool(value)

            range_spec = input_spec.get("range")
            if range_spec:
                valid, error_msg = validate_range(float(value), range_spec)
                if not valid:
                    return False, error_msg

            options = input_spec.get("options") or []
            if options:
                valid_values = [opt.get("value") for opt in options]
                if value not in valid_values:
                    return False, f"输入值必须是以下之一: {valid_values}"

            return True, ""

        except ValueError as exc:
            return False, f"类型转换失败: {exc}"
        except (TypeError, KeyError) as exc:
            logger.error(f"输入验证失败 - {type(exc).__name__}: {exc}")
            return False, f"验证失败: {exc}"
        except Exception as exc:  # noqa: BLE001 - 兜底记录日志
            logger.error(f"输入验证出现未预期错误 ({type(exc).__name__}): {exc}", exc_info=True)
            return False, f"验证失败: {exc}"

    def _validate_legacy_rules(self, rules: list[dict[str, Any]] | Any, user_input: dict[str, Any]) -> tuple[bool, str]:
        """兼容旧版 YAML 模板中的简单 validation_rules 定义。

        当前仅支持 tests 中使用的 range 规则:
        {
            "type": "range",
            "field": "volume_naoh",
            "min": 10,
            "max": 30,
            "error_message": "体积应在10-30mL之间",
        }
        """
        # 防御性处理: 非列表或空规则直接视为通过
        if not rules or not isinstance(rules, list):
            return True, ""

        for rule in rules:
            if not isinstance(rule, dict):
                continue

            rule_type = rule.get("type")
            if rule_type != "range":
                # 目前只实现 range，其他类型暂视为通过
                continue

            field = rule.get("field")
            if not field:
                continue

            if field not in user_input:
                msg = rule.get("error_message") or f"缺少输入字段: {field}"
                return False, msg

            try:
                value = float(user_input[field])
            except (TypeError, ValueError):
                msg = rule.get("error_message") or f"字段 {field} 的值无法转换为数值"
                return False, msg

            min_val = rule.get("min")
            max_val = rule.get("max")

            # 允许只设置一端
            if min_val is not None and value < float(min_val):
                msg = rule.get("error_message") or f"{field} 不能小于 {min_val}"
                return False, msg
            if max_val is not None and value > float(max_val):
                msg = rule.get("error_message") or f"{field} 不能大于 {max_val}"
                return False, msg

        # 所有规则都通过
        return True, ""

    def evaluate_score_rules(self, rules: list, context: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """计算评分

        Args:
            rules: 评分规则列表
            context: 上下文变量

        Returns:
            (总分, 评分详情)
        """
        total_score = 0
        details = {}

        for i, rule in enumerate(rules):
            rule_id = f"rule_{i}"
            try:
                condition = rule.get("when", "")
                score = rule.get("then", 0)

                if self.evaluate_expression(condition, context):
                    total_score += score
                    details[rule_id] = {
                        "condition": condition,
                        "score": score,
                        "passed": True,
                    }
                else:
                    details[rule_id] = {
                        "condition": condition,
                        "score": 0,
                        "passed": False,
                    }

            except (EvaluationError, ValueError, TypeError, KeyError) as e:
                logger.error(f"评分规则 {rule_id} 计算失败 - {type(e).__name__}: {e}")
                details[rule_id] = {"error": str(e), "score": 0}
            except Exception as e:
                # 捕获其他未预期的异常
                logger.error(f"评分规则 {rule_id} 出现未预期错误 ({type(e).__name__}): {e}", exc_info=True)
                details[rule_id] = {"error": str(e), "score": 0}

        return total_score, details
