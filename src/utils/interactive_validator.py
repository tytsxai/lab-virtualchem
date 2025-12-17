"""交互式实验验证器"""

from __future__ import annotations

from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class InteractiveValidator:
    """交互式检查点验证器"""

    def __init__(self) -> None:
        self.validation_history: list[dict[str, Any]] = []

    def validate_drop_action(
        self,
        check_config: dict[str, Any],
        actual_drops: dict[str, str],
    ) -> tuple[bool, str]:
        """
        验证拖拽动作

        Args:
            check_config: 检查配置 {"type": "drop", "item_id": "beaker", "zone_id": "work_area"}
            actual_drops: 实际放置情况 {"beaker": "work_area", ...}

        Returns:
            (是否通过, 提示信息)
        """
        required_item = check_config.get("item_id")
        required_zone = check_config.get("zone_id")

        if not required_item or not required_zone:
            logger.warning("拖拽检查配置不完整")
            return False, "检查配置错误"

        actual_zone = actual_drops.get(required_item)

        if actual_zone == required_zone:
            msg = f"✓ 正确！已将 {required_item} 放置到 {required_zone}"
            logger.info(f"拖拽验证通过: {required_item} -> {required_zone}")
            self._record_validation("drop", True, check_config)
            return True, msg
        elif actual_zone:
            msg = f"✗ 错误！{required_item} 应该放到 {required_zone}，而不是 {actual_zone}"
            logger.info(
                f"拖拽验证失败: {required_item} -> {actual_zone} (期望: {required_zone})"
            )
            self._record_validation("drop", False, check_config)
            return False, msg
        else:
            msg = f"✗ 请将 {required_item} 拖拽到 {required_zone}"
            logger.info(f"拖拽验证失败: {required_item} 未放置")
            self._record_validation("drop", False, check_config)
            return False, msg

    def validate_click_action(
        self,
        check_config: dict[str, Any],
        actual_clicks: dict[str, int],
    ) -> tuple[bool, str]:
        """
        验证点击动作

        Args:
            check_config: 检查配置 {"type": "click", "item_id": "reagent_hcl", "required_times": 1}
            actual_clicks: 实际点击次数 {"reagent_hcl": 3, ...}

        Returns:
            (是否通过, 提示信息)
        """
        required_item = check_config.get("item_id")
        required_times = check_config.get("required_times", 1)

        if not required_item:
            logger.warning("点击检查配置不完整")
            return False, "检查配置错误"

        actual_times = actual_clicks.get(required_item, 0)

        if actual_times >= required_times:
            msg = f"✓ 正确！已点击 {required_item} {actual_times} 次"
            logger.info(f"点击验证通过: {required_item} 点击 {actual_times} 次")
            self._record_validation("click", True, check_config)
            return True, msg
        else:
            msg = f"✗ 请点击 {required_item}（还需点击 {required_times - actual_times} 次）"
            logger.info(
                f"点击验证失败: {required_item} 点击 {actual_times}/{required_times} 次"
            )
            self._record_validation("click", False, check_config)
            return False, msg

    def validate_sequence_action(
        self,
        check_config: dict[str, Any],
        action_sequence: list[str],
    ) -> tuple[bool, str]:
        """
        验证操作序列

        Args:
            check_config: 检查配置 {"type": "sequence", "required_sequence": ["step1", "step2", "step3"]}
            action_sequence: 实际操作序列

        Returns:
            (是否通过, 提示信息)
        """
        required_sequence = check_config.get("required_sequence", [])

        if not required_sequence:
            logger.warning("序列检查配置不完整")
            return False, "检查配置错误"

        # 检查序列是否匹配
        if len(action_sequence) < len(required_sequence):
            msg = f"✗ 操作步骤不完整（已完成 {len(action_sequence)}/{len(required_sequence)}）"
            logger.info("序列验证失败: 步骤不完整")
            self._record_validation("sequence", False, check_config)
            return False, msg

        # 检查顺序是否正确
        for i, required_action in enumerate(required_sequence):
            if i >= len(action_sequence) or action_sequence[i] != required_action:
                msg = f"✗ 操作顺序错误！第 {i + 1} 步应该是 {required_action}"
                logger.info(f"序列验证失败: 第 {i + 1} 步错误")
                self._record_validation("sequence", False, check_config)
                return False, msg

        msg = f"✓ 正确！完成了所有 {len(required_sequence)} 个步骤"
        logger.info("序列验证通过")
        self._record_validation("sequence", True, check_config)
        return True, msg

    def validate_combined_actions(
        self,
        check_config: dict[str, Any],
        actual_drops: dict[str, str],
        actual_clicks: dict[str, int],
    ) -> tuple[bool, str]:
        """
        验证组合动作（拖拽 + 点击）

        Args:
            check_config: 检查配置 {"type": "combined", "actions": [...]}
            actual_drops: 实际放置情况
            actual_clicks: 实际点击次数

        Returns:
            (是否通过, 提示信息)
        """
        required_actions = check_config.get("actions", [])

        if not required_actions:
            logger.warning("组合检查配置不完整")
            return False, "检查配置错误"

        results = []
        for action in required_actions:
            action_type = action.get("type")

            if action_type == "drop":
                passed, msg = self.validate_drop_action(action, actual_drops)
                results.append((passed, msg))
            elif action_type == "click":
                passed, msg = self.validate_click_action(action, actual_clicks)
                results.append((passed, msg))

        all_passed = all(r[0] for r in results)

        if all_passed:
            msg = "✓ 所有操作都正确完成！"
            logger.info("组合验证通过")
            self._record_validation("combined", True, check_config)
            return True, msg
        else:
            failed_msgs = [r[1] for r in results if not r[0]]
            msg = "\n".join(failed_msgs)
            logger.info("组合验证失败")
            self._record_validation("combined", False, check_config)
            return False, msg

    def _record_validation(
        self, check_type: str, passed: bool, config: dict[str, Any]
    ) -> None:
        """记录验证结果"""
        self.validation_history.append(
            {
                "check_type": check_type,
                "passed": passed,
                "config": config,
                "timestamp": None,  # 可以添加时间戳
            }
        )

    def get_validation_statistics(self) -> dict[str, Any]:
        """获取验证统计信息"""
        if not self.validation_history:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "by_type": {},
            }

        total = len(self.validation_history)
        passed = sum(1 for v in self.validation_history if v["passed"])
        failed = total - passed

        by_type: dict[str, dict[str, int]] = {}
        for validation in self.validation_history:
            check_type = validation["check_type"]
            if check_type not in by_type:
                by_type[check_type] = {"total": 0, "passed": 0, "failed": 0}

            by_type[check_type]["total"] += 1
            if validation["passed"]:
                by_type[check_type]["passed"] += 1
            else:
                by_type[check_type]["failed"] += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "by_type": by_type,
        }

    def reset(self) -> None:
        """重置验证历史"""
        self.validation_history.clear()
        logger.info("验证器已重置")
