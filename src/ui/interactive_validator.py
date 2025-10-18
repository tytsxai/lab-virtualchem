"""
交互式实验验证器
验证用户操作，提供实时反馈和评分
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """验证结果"""

    def __init__(
        self,
        passed: bool,
        score: float = 0.0,
        message: str = "",
        hints: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ):
        self.passed = passed
        self.score = score
        self.message = message
        self.hints = hints or []
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "score": self.score,
            "message": self.message,
            "hints": self.hints,
            "data": self.data,
        }


class InteractiveValidator(QObject):
    """交互式实验验证器"""

    # 信号
    validation_completed = Signal(str, ValidationResult)  # 步骤ID, 验证结果
    step_passed = Signal(str, float)  # 步骤ID, 得分
    step_failed = Signal(str, str)  # 步骤ID, 错误信息

    def __init__(self):
        super().__init__()

        # 验证规则
        self.validation_rules: dict[str, dict[str, Any]] = {}

        # 用户操作历史
        self.operation_history: list[dict[str, Any]] = []

        # 当前步骤状态
        self.current_step = ""
        self.step_start_time = 0.0

        logger.info("交互式实验验证器初始化完成")

    def start_step_validation(self, step_id: str, validation_config: dict[str, Any]) -> None:
        """开始步骤验证"""
        self.current_step = step_id
        self.validation_rules[step_id] = validation_config
        self.step_start_time = time.time()

        logger.info(f"开始步骤验证: {step_id}")

    def validate_drop_action(
        self, item_id: str, zone_id: str, expected_item_id: str | None = None, expected_zone_id: str | None = None
    ) -> ValidationResult:
        """验证拖放动作"""
        # 记录操作
        operation = {"type": "drop", "item_id": item_id, "zone_id": zone_id, "timestamp": time.time()}
        self.operation_history.append(operation)

        # 验证规则
        passed = True
        score = 0.0
        message = ""
        hints = []

        if expected_item_id and item_id != expected_item_id:
            passed = False
            message = f"物品错误: 期望 {expected_item_id}, 实际 {item_id}"
            hints.append("请选择正确的实验器材")
        else:
            score += 50.0

        if expected_zone_id and zone_id != expected_zone_id:
            passed = False
            message = f"放置区域错误: 期望 {expected_zone_id}, 实际 {zone_id}"
            hints.append("请将物品放置在正确的区域")
        else:
            score += 50.0

        if passed:
            message = "✓ 放置正确"

        result = ValidationResult(passed, score, message, hints)
        self._emit_validation_result(result)

        return result

    def validate_click_action(
        self, item_id: str, expected_item_id: str | None = None, required_times: int = 1
    ) -> ValidationResult:
        """验证点击动作"""
        # 记录操作
        operation = {"type": "click", "item_id": item_id, "timestamp": time.time()}
        self.operation_history.append(operation)

        # 统计点击次数
        click_count = sum(1 for op in self.operation_history if op["type"] == "click" and op["item_id"] == item_id)

        # 验证规则
        passed = True
        score = 0.0
        message = ""
        hints = []

        if expected_item_id and item_id != expected_item_id:
            passed = False
            message = f"点击物品错误: 期望 {expected_item_id}, 实际 {item_id}"
            hints.append("请点击正确的试剂瓶")
        else:
            score += 50.0

        if click_count < required_times:
            passed = False
            message = f"点击次数不足: 需要 {required_times} 次, 实际 {click_count} 次"
            hints.append(f"请继续点击 {required_times - click_count} 次")
        else:
            score += 50.0

        if passed:
            message = f"✓ 点击正确 ({click_count}/{required_times})"

        result = ValidationResult(passed, score, message, hints)
        self._emit_validation_result(result)

        return result

    def validate_sequence_action(self, required_sequence: list[str], _tolerance: float = 5.0) -> ValidationResult:
        """验证操作序列"""
        # 获取最近的操作序列
        recent_operations = self.operation_history[-len(required_sequence) :]

        if len(recent_operations) < len(required_sequence):
            return ValidationResult(
                False, 0.0, "操作序列不完整", [f"还需要 {len(required_sequence) - len(recent_operations)} 个操作"]
            )

        # 验证序列
        passed = True
        score = 0.0
        message = ""
        hints = []

        for i, expected_op in enumerate(required_sequence):
            if i >= len(recent_operations):
                passed = False
                break

            actual_op = recent_operations[i]
            if not self._matches_operation(expected_op, actual_op):
                passed = False
                break

        if passed:
            score = 100.0
            message = "✓ 操作序列正确"
        else:
            message = "操作序列错误"
            hints.append("请按照正确的顺序进行操作")

        result = ValidationResult(passed, score, message, hints)
        self._emit_validation_result(result)

        return result

    def validate_input_value(
        self,
        value: float,
        expected_value: float | None = None,
        tolerance: float = 0.1,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> ValidationResult:
        """验证输入值"""
        passed = True
        score = 0.0
        message = ""
        hints = []

        # 检查范围
        if min_value is not None and value < min_value:
            passed = False
            message = f"数值过小: 最小值为 {min_value}"
            hints.append("请检查读数是否正确")
        elif max_value is not None and value > max_value:
            passed = False
            message = f"数值过大: 最大值为 {max_value}"
            hints.append("请检查读数是否正确")
        else:
            score += 50.0

        # 检查期望值
        if expected_value is not None:
            if abs(value - expected_value) <= tolerance:
                score += 50.0
                message = "✓ 数值正确"
            else:
                passed = False
                message = f"数值误差过大: 期望 {expected_value}±{tolerance}, 实际 {value}"
                hints.append("请仔细读取数值")
        else:
            if passed:
                message = "✓ 数值在合理范围内"

        result = ValidationResult(passed, score, message, hints)
        self._emit_validation_result(result)

        return result

    def validate_combined_action(self, actions: list[dict[str, Any]]) -> ValidationResult:
        """验证组合动作"""
        total_score = 0.0
        all_passed = True
        messages = []
        hints = []

        for action in actions:
            action_type = action.get("type")

            if action_type == "drop":
                result = self.validate_drop_action(
                    action.get("item_id", ""),
                    action.get("zone_id", ""),
                    action.get("expected_item_id"),
                    action.get("expected_zone_id"),
                )
            elif action_type == "click":
                result = self.validate_click_action(
                    action.get("item_id", ""), action.get("expected_item_id"), action.get("required_times", 1)
                )
            else:
                result = ValidationResult(False, 0.0, f"未知动作类型: {action_type}")

            total_score += result.score
            if not result.passed:
                all_passed = False

            messages.append(result.message)
            hints.extend(result.hints)

        # 计算平均得分
        avg_score = total_score / len(actions) if actions else 0.0

        message = "✓ 所有动作正确" if all_passed else "部分动作需要修正"

        result = ValidationResult(all_passed, avg_score, message, hints)
        self._emit_validation_result(result)

        return result

    def calculate_step_score(self, step_id: str) -> float:
        """计算步骤得分"""
        if step_id not in self.validation_rules:
            return 0.0

        # 获取该步骤的所有验证结果
        step_operations = [op for op in self.operation_history if op.get("step_id") == step_id]

        if not step_operations:
            return 0.0

        # 根据操作类型计算得分
        total_score = 0.0
        operation_count = 0

        for op in step_operations:
            if op["type"] == "drop":
                total_score += 50.0
            elif op["type"] == "click":
                total_score += 30.0
            elif op["type"] == "input":
                total_score += 40.0

            operation_count += 1

        return total_score / operation_count if operation_count > 0 else 0.0

    def get_operation_history(self, step_id: str | None = None) -> list[dict[str, Any]]:
        """获取操作历史"""
        if step_id:
            return [op for op in self.operation_history if op.get("step_id") == step_id]
        return self.operation_history.copy()

    def clear_operation_history(self) -> None:
        """清空操作历史"""
        self.operation_history.clear()
        logger.info("操作历史已清空")

    def _matches_operation(self, expected: str, actual: dict[str, Any]) -> bool:
        """检查操作是否匹配"""
        if ":" not in expected:
            return False

        op_type, op_id = expected.split(":", 1)

        if op_type != actual.get("type"):
            return False

        if op_type == "drop":
            return op_id == actual.get("zone_id")
        elif op_type == "click":
            return op_id == actual.get("item_id")

        return False

    def _emit_validation_result(self, result: ValidationResult) -> None:
        """发送验证结果信号"""
        self.validation_completed.emit(self.current_step, result)

        if result.passed:
            self.step_passed.emit(self.current_step, result.score)
        else:
            self.step_failed.emit(self.current_step, result.message)


# 导入time模块
import time  # noqa: E402
