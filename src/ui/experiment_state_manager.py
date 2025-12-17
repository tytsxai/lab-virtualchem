"""实验状态管理器 - 保存和恢复交互式实验状态"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentState:
    """实验状态快照"""

    def __init__(
        self,
        experiment_id: str,
        current_step_index: int = 0,
        item_positions: dict[str, tuple[float, float]] | None = None,
        item_states: dict[str, dict[str, Any]] | None = None,
        drop_actions: dict[str, str] | None = None,
        click_counts: dict[str, int] | None = None,
        action_sequence: list[str] | None = None,
        user_inputs: dict[str, Any] | None = None,
        context_data: dict[str, Any] | None = None,
    ):
        self.experiment_id = experiment_id
        self.current_step_index = current_step_index
        self.item_positions = item_positions or {}
        self.item_states = item_states or {}
        self.drop_actions = drop_actions or {}
        self.click_counts = click_counts or {}
        self.action_sequence = action_sequence or []
        self.user_inputs = user_inputs or {}
        self.context_data = context_data or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "experiment_id": self.experiment_id,
            "current_step_index": self.current_step_index,
            "item_positions": self.item_positions,
            "item_states": self.item_states,
            "drop_actions": self.drop_actions,
            "click_counts": self.click_counts,
            "action_sequence": self.action_sequence,
            "user_inputs": self.user_inputs,
            "context_data": self.context_data,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentState:
        """从字典创建"""
        state = cls(
            experiment_id=data["experiment_id"],
            current_step_index=data.get("current_step_index", 0),
            item_positions=data.get("item_positions", {}),
            item_states=data.get("item_states", {}),
            drop_actions=data.get("drop_actions", {}),
            click_counts=data.get("click_counts", {}),
            action_sequence=data.get("action_sequence", []),
            user_inputs=data.get("user_inputs", {}),
            context_data=data.get("context_data", {}),
        )

        if "timestamp" in data:
            state.timestamp = datetime.fromisoformat(data["timestamp"])

        return state


class ExperimentStateManager:
    """实验状态管理器"""

    def __init__(self, save_dir: Path | None = None):
        self.save_dir = save_dir or Path("data/experiment_states")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.current_state: ExperimentState | None = None
        self.state_history: list[ExperimentState] = []
        self.max_history = 10  # 最多保存10个历史状态

    def capture_state(
        self,
        experiment_id: str,
        scene: Any = None,
        controller: Any = None,
        **additional_data: Any,
    ) -> ExperimentState:
        """
        捕获当前实验状态

        Args:
            experiment_id: 实验ID
            scene: 交互式场景对象
            controller: 实验控制器
            **additional_data: 额外数据

        Returns:
            实验状态对象
        """
        # 从场景获取状态
        item_positions = {}
        item_states: dict[str, dict[str, Any]] = {}
        drop_actions = {}
        click_counts: dict[str, int] = {}

        if scene:
            scene_state = scene.get_state()
            item_positions = scene_state.get("item_positions", {})
            drop_actions = scene_state.get("drop_actions", {})

        # 从控制器获取状态
        current_step_index = 0
        user_inputs: dict[str, Any] = {}
        context_data: dict[str, Any] = {}

        if controller:
            current_step_index = controller.current_step_index
            user_inputs = getattr(controller, "user_inputs", {})
            context_data = getattr(controller.record, "context", {})

        # 创建状态快照
        state = ExperimentState(
            experiment_id=experiment_id,
            current_step_index=current_step_index,
            item_positions=item_positions,
            item_states=item_states,
            drop_actions=drop_actions,
            click_counts=click_counts,
            user_inputs=user_inputs,
            context_data=context_data,
            **additional_data,
        )

        self.current_state = state

        # 添加到历史
        self.state_history.append(state)
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)

        logger.info(f"已捕获实验状态: {experiment_id} (步骤 {current_step_index})")
        return state

    def restore_state(
        self,
        state: ExperimentState,
        scene: Any = None,
        controller: Any = None,
    ) -> bool:
        """
        恢复实验状态

        Args:
            state: 要恢复的状态
            scene: 交互式场景对象
            controller: 实验控制器

        Returns:
            是否恢复成功
        """
        try:
            # 恢复场景状态
            if scene:
                scene.load_state(
                    {
                        "item_positions": state.item_positions,
                        "drop_actions": state.drop_actions,
                    }
                )

            # 恢复控制器状态
            if controller:
                controller.current_step_index = state.current_step_index
                if hasattr(controller, "user_inputs"):
                    controller.user_inputs = state.user_inputs.copy()
                if hasattr(controller.record, "context"):
                    controller.record.context.update(state.context_data)

            self.current_state = state
            logger.info(f"已恢复实验状态: {state.experiment_id}")
            return True

        except Exception as e:
            logger.error(f"恢复状态失败: {e}", exc_info=True)
            return False

    def save_to_file(
        self, state: ExperimentState | None = None, filename: str | None = None
    ) -> Path:
        """
        保存状态到文件

        Args:
            state: 要保存的状态（默认为当前状态）
            filename: 文件名（默认自动生成）

        Returns:
            保存的文件路径
        """
        state = state or self.current_state

        if not state:
            raise ValueError("没有可保存的状态")

        if not filename:
            timestamp = state.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{state.experiment_id}_{timestamp}.json"

        file_path = self.save_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"状态已保存到: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"保存状态失败: {e}", exc_info=True)
            raise

    def load_from_file(self, file_path: Path | str) -> ExperimentState:
        """
        从文件加载状态

        Args:
            file_path: 文件路径

        Returns:
            实验状态对象
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"状态文件不存在: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            state = ExperimentState.from_dict(data)
            self.current_state = state

            logger.info(f"状态已加载: {file_path}")
            return state

        except Exception as e:
            logger.error(f"加载状态失败: {e}", exc_info=True)
            raise

    def list_saved_states(
        self, experiment_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        列出保存的状态文件

        Args:
            experiment_id: 实验ID（可选，用于筛选）

        Returns:
            状态文件信息列表
        """
        states = []

        for file_path in self.save_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                if experiment_id and data.get("experiment_id") != experiment_id:
                    continue

                states.append(
                    {
                        "file_path": str(file_path),
                        "experiment_id": data.get("experiment_id"),
                        "timestamp": data.get("timestamp"),
                        "step_index": data.get("current_step_index"),
                    }
                )

            except Exception as e:
                logger.warning(f"读取状态文件失败 {file_path}: {e}")

        # 按时间排序
        states.sort(key=lambda x: x["timestamp"], reverse=True)

        return states

    def get_undo_state(self) -> ExperimentState | None:
        """获取上一个状态（撤销用）"""
        if len(self.state_history) > 1:
            return self.state_history[-2]
        return None

    def clear_history(self) -> None:
        """清除历史记录"""
        self.state_history.clear()
        logger.info("历史记录已清除")

    def auto_save(
        self,
        experiment_id: str,
        scene: Any = None,
        controller: Any = None,
        interval_seconds: int = 60,
    ) -> None:
        """
        自动保存（需要在定时器中调用）

        Args:
            experiment_id: 实验ID
            scene: 交互式场景
            controller: 实验控制器
            interval_seconds: 保存间隔（秒）
        """
        state = self.capture_state(experiment_id, scene, controller)
        self.save_to_file(state, filename=f"{experiment_id}_autosave.json")
        logger.info(f"自动保存完成（间隔: {interval_seconds}秒）")
