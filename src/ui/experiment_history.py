"""实验操作历史记录"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ActionType(str, Enum):
    """操作类型"""

    DRAG = "drag"  # 拖拽
    DROP = "drop"  # 放置
    CLICK = "click"  # 点击
    INPUT = "input"  # 输入
    SELECT = "select"  # 选择
    NAVIGATE = "navigate"  # 导航（切换步骤）
    SUBMIT = "submit"  # 提交


class ExperimentAction:
    """实验操作记录"""

    def __init__(
        self,
        action_type: ActionType,
        details: dict[str, Any],
        step_id: str | None = None,
        timestamp: datetime | None = None,
    ):
        self.action_type = action_type
        self.details = details
        self.step_id = step_id
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "action_type": self.action_type.value,
            "details": self.details,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """字符串表示"""
        time_str = self.timestamp.strftime("%H:%M:%S")
        step_str = f"[{self.step_id}]" if self.step_id else ""
        return f"[{time_str}]{step_str} {self.action_type.value}: {self.details}"


class ExperimentHistory:
    """实验操作历史管理器"""

    def __init__(self) -> None:
        self.actions: list[ExperimentAction] = []
        self.max_actions = 1000  # 最多保存1000条记录

    def record_drag(
        self, item_id: str, from_pos: tuple[float, float], to_pos: tuple[float, float], step_id: str | None = None
    ) -> None:
        """记录拖拽操作"""
        action = ExperimentAction(
            ActionType.DRAG,
            {"item_id": item_id, "from": from_pos, "to": to_pos},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录拖拽: {item_id} {from_pos} -> {to_pos}")

    def record_drop(
        self, item_id: str, zone_id: str, position: tuple[float, float], step_id: str | None = None
    ) -> None:
        """记录放置操作"""
        action = ExperimentAction(
            ActionType.DROP,
            {"item_id": item_id, "zone_id": zone_id, "position": position},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录放置: {item_id} -> {zone_id}")

    def record_click(
        self, item_id: str, position: tuple[float, float] | None = None, step_id: str | None = None
    ) -> None:
        """记录点击操作"""
        action = ExperimentAction(
            ActionType.CLICK,
            {"item_id": item_id, "position": position},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录点击: {item_id}")

    def record_input(self, field_name: str, value: Any, step_id: str | None = None) -> None:
        """记录输入操作"""
        action = ExperimentAction(
            ActionType.INPUT,
            {"field": field_name, "value": value},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录输入: {field_name} = {value}")

    def record_select(self, option_id: str, selected: bool, step_id: str | None = None) -> None:
        """记录选择操作"""
        action = ExperimentAction(
            ActionType.SELECT,
            {"option_id": option_id, "selected": selected},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录选择: {option_id} = {selected}")

    def record_navigate(self, from_step: int, to_step: int, direction: str) -> None:
        """记录导航操作"""
        action = ExperimentAction(
            ActionType.NAVIGATE,
            {"from_step": from_step, "to_step": to_step, "direction": direction},
        )
        self._add_action(action)
        logger.debug(f"记录导航: {from_step} -> {to_step} ({direction})")

    def record_submit(self, step_id: str, data: dict[str, Any], success: bool) -> None:
        """记录提交操作"""
        action = ExperimentAction(
            ActionType.SUBMIT,
            {"data": data, "success": success},
            step_id,
        )
        self._add_action(action)
        logger.debug(f"记录提交: {step_id} (成功: {success})")

    def _add_action(self, action: ExperimentAction) -> None:
        """添加操作记录"""
        self.actions.append(action)

        # 限制记录数量
        if len(self.actions) > self.max_actions:
            self.actions.pop(0)

    def get_actions_by_type(self, action_type: ActionType) -> list[ExperimentAction]:
        """获取指定类型的所有操作"""
        return [a for a in self.actions if a.action_type == action_type]

    def get_actions_by_step(self, step_id: str) -> list[ExperimentAction]:
        """获取指定步骤的所有操作"""
        return [a for a in self.actions if a.step_id == step_id]

    def get_recent_actions(self, count: int = 10) -> list[ExperimentAction]:
        """获取最近的N条操作"""
        return self.actions[-count:]

    def get_action_sequence(self) -> list[str]:
        """获取操作序列（用于序列验证）"""
        return [f"{a.action_type.value}:{a.details.get('item_id', '')}" for a in self.actions]

    def get_click_counts(self) -> dict[str, int]:
        """获取所有物品的点击次数"""
        click_counts: dict[str, int] = {}

        for action in self.actions:
            if action.action_type == ActionType.CLICK:
                item_id = action.details.get("item_id")
                if item_id:
                    click_counts[item_id] = click_counts.get(item_id, 0) + 1

        return click_counts

    def get_drop_actions(self) -> dict[str, str]:
        """获取所有放置操作（物品ID -> 区域ID）"""
        drop_actions: dict[str, str] = {}

        for action in self.actions:
            if action.action_type == ActionType.DROP:
                item_id = action.details.get("item_id")
                zone_id = action.details.get("zone_id")
                if item_id and zone_id:
                    drop_actions[item_id] = zone_id

        return drop_actions

    def get_statistics(self) -> dict[str, Any]:
        """获取操作统计信息"""
        if not self.actions:
            return {
                "total_actions": 0,
                "by_type": {},
                "duration": 0,
            }

        by_type: dict[str, int] = {}
        for action in self.actions:
            action_type = action.action_type.value
            by_type[action_type] = by_type.get(action_type, 0) + 1

        duration = 0
        if len(self.actions) >= 2:
            duration = int((self.actions[-1].timestamp - self.actions[0].timestamp).total_seconds())

        return {
            "total_actions": len(self.actions),
            "by_type": by_type,
            "duration": duration,
            "actions_per_minute": len(self.actions) / (duration / 60) if duration > 0 else 0,
        }

    def export_to_list(self) -> list[dict[str, Any]]:
        """导出为列表"""
        return [action.to_dict() for action in self.actions]

    def clear(self) -> None:
        """清空历史记录"""
        self.actions.clear()
        logger.info("操作历史已清空")

    def __len__(self) -> int:
        return len(self.actions)

    def __str__(self) -> str:
        stats = self.get_statistics()
        return f"ExperimentHistory({stats['total_actions']} actions, {stats['duration']:.1f}s)"
