"""
交互式实验控制器
整合所有交互式实验功能，提供统一的控制接口
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QGraphicsScene

from ..utils.logger import get_logger
from .chemical_reaction_simulator import ChemicalReactionSimulator
from .experiment_data_recorder import ExperimentDataRecorder
from .interactive_validator import InteractiveValidator
from .reaction_animation import ReactionAnimation

logger = get_logger(__name__)


class InteractiveExperimentController(QObject):
    """交互式实验控制器"""

    # 信号
    experiment_started = Signal(str)  # 实验ID
    experiment_completed = Signal(str, dict[str, Any])  # 实验ID, 结果
    step_changed = Signal(str, str)  # 实验ID, 步骤ID
    validation_result = Signal(str, bool, str)  # 步骤ID, 是否通过, 消息
    data_recorded = Signal(str, str, object)  # 步骤ID, 数据类型, 值

    def __init__(self, experiment_id: str):
        super().__init__()

        self.experiment_id = experiment_id

        # 初始化各个组件
        self.reaction_simulator = ChemicalReactionSimulator()
        self.data_recorder = ExperimentDataRecorder(experiment_id)
        self.validator = InteractiveValidator()
        self.animation = ReactionAnimation()

        # 实验状态
        self.current_step = ""
        self.experiment_active = False
        self.step_history: list[str] = []

        # 连接信号
        self._connect_signals()

        logger.info(f"交互式实验控制器初始化完成: {experiment_id}")

    def _connect_signals(self) -> None:
        """连接内部信号"""
        # 数据记录器信号
        self.data_recorder.data_recorded.connect(self._on_data_recorded)
        self.data_recorder.calculation_completed.connect(self._on_calculation_completed)
        self.data_recorder.experiment_completed.connect(self._on_experiment_completed)

        # 验证器信号
        self.validator.validation_completed.connect(self._on_validation_completed)
        self.validator.step_passed.connect(self._on_step_passed)
        self.validator.step_failed.connect(self._on_step_failed)

        # 反应模拟器信号
        self.reaction_simulator.reagent_added.connect(self._on_reagent_added)
        self.reaction_simulator.ph_changed.connect(self._on_ph_changed)
        self.reaction_simulator.color_changed.connect(self._on_color_changed)

    def set_scene(self, scene: QGraphicsScene) -> None:
        """设置场景"""
        self.animation.set_scene(scene)
        scene.reaction_animation = self.animation
        logger.info("场景设置完成")

    def start_experiment(self, _experiment_config: dict[str, Any]) -> bool:
        """开始实验"""
        if self.experiment_active:
            logger.warning("实验已在进行中")
            return False

        self.experiment_active = True
        self.step_history.clear()

        # 清空之前的数据
        self.data_recorder.clear_data()
        self.validator.clear_operation_history()

        # 开始动画
        self.animation.start_animation()

        self.experiment_started.emit(self.experiment_id)
        logger.info(f"开始实验: {self.experiment_id}")

        return True

    def start_step(self, step_id: str, step_config: dict[str, Any]) -> bool:
        """开始步骤"""
        if not self.experiment_active:
            logger.warning("实验未开始")
            return False

        self.current_step = step_id
        self.step_history.append(step_id)

        # 开始数据记录
        self.data_recorder.start_step(step_id)

        # 开始验证
        validation_config = step_config.get("validation", {})
        self.validator.start_step_validation(step_id, validation_config)

        self.step_changed.emit(self.experiment_id, step_id)
        logger.info(f"开始步骤: {step_id}")

        return True

    def add_reagent(self, container_id: str, reagent_id: str, volume: float) -> bool:
        """添加试剂"""
        if not self.experiment_active:
            return False

        # 添加到反应模拟器
        success = self.reaction_simulator.add_reagent_to_container(
            container_id, reagent_id, volume
        )

        if success:
            # 记录数据
            self.data_recorder.record_reagent_addition(reagent_id, volume)

            # 创建动画效果
            self.animation.create_bubble_effect(100, 100, 5)

            logger.info(f"添加试剂: {reagent_id} {volume}mL 到 {container_id}")

        return success

    def add_indicator(self, container_id: str, indicator_id: str) -> bool:
        """添加指示剂"""
        if not self.experiment_active:
            return False

        success = self.reaction_simulator.add_indicator_to_container(
            container_id, indicator_id
        )

        if success:
            logger.info(f"添加指示剂: {indicator_id} 到 {container_id}")

        return success

    def record_volume_reading(self, volume: float, unit: str = "mL") -> None:
        """记录体积读数"""
        if self.experiment_active:
            self.data_recorder.record_volume_reading(volume, unit)

    def record_ph_reading(self, ph: float) -> None:
        """记录pH读数"""
        if self.experiment_active:
            self.data_recorder.record_ph_reading(ph)

    def record_temperature(self, temperature: float, unit: str = "°C") -> None:
        """记录温度"""
        if self.experiment_active:
            self.data_recorder.record_temperature(temperature, unit)

    def record_observation(self, observation: str) -> None:
        """记录观察结果"""
        if self.experiment_active:
            self.data_recorder.record_observation(observation)

    def validate_drop_action(
        self,
        item_id: str,
        zone_id: str,
        expected_item_id: str | None = None,
        expected_zone_id: str | None = None,
    ) -> bool:
        """验证拖放动作"""
        if not self.experiment_active:
            return False

        result = self.validator.validate_drop_action(
            item_id, zone_id, expected_item_id, expected_zone_id
        )

        return result.passed

    def validate_click_action(
        self, item_id: str, expected_item_id: str | None = None, required_times: int = 1
    ) -> bool:
        """验证点击动作"""
        if not self.experiment_active:
            return False

        result = self.validator.validate_click_action(
            item_id, expected_item_id, required_times
        )

        return result.passed

    def validate_input_value(
        self, value: float, expected_value: float | None = None, tolerance: float = 0.1
    ) -> bool:
        """验证输入值"""
        if not self.experiment_active:
            return False

        result = self.validator.validate_input_value(value, expected_value, tolerance)

        return result.passed

    def complete_step(self) -> dict[str, Any]:
        """完成当前步骤"""
        if not self.experiment_active or not self.current_step:
            return {}

        # 计算步骤得分
        step_score = self.validator.calculate_step_score(self.current_step)

        # 获取步骤数据
        step_data = self.data_recorder.get_step_data(self.current_step)

        result = {
            "step_id": self.current_step,
            "score": step_score,
            "data_points": len(step_data),
            "completed_time": time.time(),
        }

        logger.info(f"完成步骤: {self.current_step}, 得分: {step_score}")

        return result

    def complete_experiment(self) -> dict[str, Any]:
        """完成实验"""
        if not self.experiment_active:
            return {}

        self.experiment_active = False

        # 停止动画
        self.animation.stop_animation()

        # 生成最终报告
        final_report = self.data_recorder.complete_experiment()

        # 添加验证结果
        final_report["validation_summary"] = {
            "total_steps": len(self.step_history),
            "step_history": self.step_history,
        }

        self.experiment_completed.emit(self.experiment_id, final_report)
        logger.info(f"实验完成: {self.experiment_id}")

        return final_report

    def get_experiment_status(self) -> dict[str, Any]:
        """获取实验状态"""
        return {
            "experiment_id": self.experiment_id,
            "active": self.experiment_active,
            "current_step": self.current_step,
            "step_history": self.step_history,
            "total_steps": len(self.step_history),
        }

    def get_container_state(self, container_id: str) -> dict[str, Any] | None:
        """获取容器状态"""
        return self.reaction_simulator.get_container_state(container_id)

    def clear_container(self, container_id: str) -> None:
        """清空容器"""
        self.reaction_simulator.clear_container(container_id)
        logger.info(f"清空容器: {container_id}")

    def export_experiment_data(self, file_path: str) -> bool:
        """导出实验数据"""
        return self.data_recorder.export_data(file_path)

    def import_experiment_data(self, file_path: str) -> bool:
        """导入实验数据"""
        return self.data_recorder.import_data(file_path)

    def get_reagent_info(self, reagent_id: str) -> Any | None:
        """获取试剂信息"""
        return self.reaction_simulator.get_reagent_info(reagent_id)

    def get_indicator_info(self, indicator_id: str) -> Any | None:
        """获取指示剂信息"""
        return self.reaction_simulator.get_indicator_info(indicator_id)

    def create_visual_effect(
        self, effect_type: str, x: float, y: float, **kwargs: Any
    ) -> None:
        """创建视觉效果"""
        if effect_type == "bubble":
            count = kwargs.get("count", 10)
            self.animation.create_bubble_effect(x, y, count)
        elif effect_type == "smoke":
            count = kwargs.get("count", 15)
            self.animation.create_smoke_effect(x, y, count)
        elif effect_type == "explosion":
            count = kwargs.get("count", 20)
            self.animation.create_explosion_effect(x, y, count)
        elif effect_type == "color_transition":
            animation_id = kwargs.get("animation_id", "default")
            start_color = kwargs.get("start_color")
            end_color = kwargs.get("end_color")
            duration = kwargs.get("duration", 1.0)

            if start_color and end_color:
                self.animation.start_color_transition(
                    animation_id, start_color, end_color, duration
                )

    def _on_data_recorded(self, step_id: str, data_type: str, value: Any) -> None:
        """处理数据记录信号"""
        self.data_recorded.emit(step_id, data_type, value)

    def _on_calculation_completed(
        self, calculation_type: str, _result: dict[str, Any]
    ) -> None:
        """处理计算完成信号"""
        logger.info(f"计算完成: {calculation_type}")

    def _on_experiment_completed(self, _final_report: dict[str, Any]) -> None:
        """处理实验完成信号"""
        logger.info("实验数据记录完成")

    def _on_validation_completed(self, step_id: str, result: Any) -> None:
        """处理验证完成信号"""
        self.validation_result.emit(step_id, result.passed, result.message)

    def _on_step_passed(self, step_id: str, score: float) -> None:
        """处理步骤通过信号"""
        logger.info(f"步骤通过: {step_id}, 得分: {score}")

    def _on_step_failed(self, step_id: str, message: str) -> None:
        """处理步骤失败信号"""
        logger.warning(f"步骤失败: {step_id}, 原因: {message}")

    def _on_reagent_added(self, reagent_id: str, volume: float) -> None:
        """处理试剂添加信号"""
        logger.info(f"试剂添加: {reagent_id} {volume}mL")

    def _on_ph_changed(self, container_id: str, ph: float) -> None:
        """处理pH变化信号"""
        logger.info(f"pH变化: {container_id} -> {ph}")

    def _on_color_changed(self, container_id: str, color: str) -> None:
        """处理颜色变化信号"""
        logger.info(f"颜色变化: {container_id} -> {color}")


class InteractiveExperimentManager(QObject):
    """交互式实验管理器"""

    # 信号
    experiment_created = Signal(str)  # 实验ID
    experiment_destroyed = Signal(str)  # 实验ID

    def __init__(self):
        super().__init__()

        # 实验实例
        self.experiments: dict[str, InteractiveExperimentController] = {}

        logger.info("交互式实验管理器初始化完成")

    def create_experiment(self, experiment_id: str) -> InteractiveExperimentController:
        """创建实验实例"""
        if experiment_id in self.experiments:
            logger.warning(f"实验已存在: {experiment_id}")
            return self.experiments[experiment_id]

        controller = InteractiveExperimentController(experiment_id)
        self.experiments[experiment_id] = controller

        self.experiment_created.emit(experiment_id)
        logger.info(f"创建实验: {experiment_id}")

        return controller

    def get_experiment(
        self, experiment_id: str
    ) -> InteractiveExperimentController | None:
        """获取实验实例"""
        return self.experiments.get(experiment_id)

    def destroy_experiment(self, experiment_id: str) -> bool:
        """销毁实验实例"""
        if experiment_id not in self.experiments:
            return False

        del self.experiments[experiment_id]
        self.experiment_destroyed.emit(experiment_id)
        logger.info(f"销毁实验: {experiment_id}")

        return True

    def list_experiments(self) -> list[str]:
        """列出所有实验"""
        return list(self.experiments.keys())

    def get_experiment_count(self) -> int:
        """获取实验数量"""
        return len(self.experiments)
