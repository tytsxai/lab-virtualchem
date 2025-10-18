"""
实验数据记录器
记录实验过程中的数据，进行计算和分析
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentDataPoint:
    """实验数据点"""

    def __init__(
        self,
        timestamp: float,
        step_id: str,
        data_type: str,
        value: Any,
        unit: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        self.timestamp = timestamp
        self.step_id = step_id
        self.data_type = data_type
        self.value = value
        self.unit = unit
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "step_id": self.step_id,
            "data_type": self.data_type,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentDataPoint:
        """从字典创建"""
        return cls(
            timestamp=data["timestamp"],
            step_id=data["step_id"],
            data_type=data["data_type"],
            value=data["value"],
            unit=data.get("unit", ""),
            metadata=data.get("metadata", {}),
        )


class ExperimentCalculation:
    """实验计算器"""

    @staticmethod
    def calculate_titration_volume(initial_volume: float, final_volume: float) -> float:
        """计算滴定消耗体积"""
        return final_volume - initial_volume

    @staticmethod
    def calculate_concentration(titrant_concentration: float, titrant_volume: float, analyte_volume: float) -> float:
        """计算待测物浓度"""
        if analyte_volume == 0:
            return 0.0
        return (titrant_concentration * titrant_volume) / analyte_volume

    @staticmethod
    def calculate_percentage_error(experimental: float, theoretical: float) -> float:
        """计算百分比误差"""
        if theoretical == 0:
            return 0.0
        return abs((experimental - theoretical) / theoretical) * 100

    @staticmethod
    def calculate_ph_from_concentration(concentration: float, is_acid: bool = True) -> float:
        """从浓度计算pH"""
        if concentration <= 0:
            return 7.0

        if is_acid:
            return -math.log10(concentration)
        else:
            return 14.0 + math.log10(concentration)

    @staticmethod
    def calculate_molarity(moles: float, volume_liters: float) -> float:
        """计算摩尔浓度"""
        if volume_liters == 0:
            return 0.0
        return moles / volume_liters

    @staticmethod
    def calculate_moles_from_volume_and_concentration(volume_ml: float, concentration_mol_l: float) -> float:
        """从体积和浓度计算摩尔数"""
        return (volume_ml / 1000.0) * concentration_mol_l


class ExperimentDataRecorder(QObject):
    """实验数据记录器"""

    # 信号
    data_recorded = Signal(str, str, object)  # 步骤ID, 数据类型, 值
    calculation_completed = Signal(str, dict[str, Any])  # 计算类型, 结果
    experiment_completed = Signal(dict[str, Any])  # 实验结果

    def __init__(self, experiment_id: str):
        super().__init__()

        self.experiment_id = experiment_id
        self.start_time = time.time()
        self.data_points: list[ExperimentDataPoint] = []
        self.calculations: dict[str, Any] = {}
        self.current_step = ""

        logger.info(f"实验数据记录器初始化: {experiment_id}")

    def start_step(self, step_id: str) -> None:
        """开始步骤"""
        self.current_step = step_id
        logger.info(f"开始步骤: {step_id}")

    def record_volume_reading(self, volume: float, unit: str = "mL") -> None:
        """记录体积读数"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(), step_id=self.current_step, data_type="volume_reading", value=volume, unit=unit
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "volume_reading", volume)
        logger.info(f"记录体积读数: {volume} {unit}")

    def record_mass_reading(self, mass: float, unit: str = "g") -> None:
        """记录质量读数"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(), step_id=self.current_step, data_type="mass_reading", value=mass, unit=unit
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "mass_reading", mass)
        logger.info(f"记录质量读数: {mass} {unit}")

    def record_temperature(self, temperature: float, unit: str = "°C") -> None:
        """记录温度"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(), step_id=self.current_step, data_type="temperature", value=temperature, unit=unit
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "temperature", temperature)
        logger.info(f"记录温度: {temperature} {unit}")

    def record_ph_reading(self, ph: float) -> None:
        """记录pH读数"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(), step_id=self.current_step, data_type="ph_reading", value=ph, unit=""
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "ph_reading", ph)
        logger.info(f"记录pH读数: {ph}")

    def record_reagent_addition(self, reagent_id: str, volume: float, unit: str = "mL") -> None:
        """记录试剂添加"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(),
            step_id=self.current_step,
            data_type="reagent_addition",
            value={"reagent_id": reagent_id, "volume": volume},
            unit=unit,
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "reagent_addition", {"reagent_id": reagent_id, "volume": volume})
        logger.info(f"记录试剂添加: {reagent_id} {volume} {unit}")

    def record_observation(self, observation: str) -> None:
        """记录观察结果"""
        data_point = ExperimentDataPoint(
            timestamp=time.time(), step_id=self.current_step, data_type="observation", value=observation, unit=""
        )
        self.data_points.append(data_point)
        self.data_recorded.emit(self.current_step, "observation", observation)
        logger.info(f"记录观察结果: {observation}")

    def calculate_titration_results(self) -> dict[str, Any]:
        """计算滴定结果"""
        # 获取体积读数
        volume_readings = [dp for dp in self.data_points if dp.data_type == "volume_reading"]

        if len(volume_readings) < 2:
            return {"error": "体积读数不足"}

        # 计算消耗体积
        initial_volume = volume_readings[0].value
        final_volume = volume_readings[-1].value
        consumed_volume = ExperimentCalculation.calculate_titration_volume(initial_volume, final_volume)

        # 计算浓度（假设已知条件）
        titrant_concentration = 0.1  # mol/L
        analyte_volume = 25.0  # mL

        calculated_concentration = ExperimentCalculation.calculate_concentration(
            titrant_concentration, consumed_volume, analyte_volume
        )

        # 计算误差
        theoretical_concentration = 0.1  # mol/L
        percentage_error = ExperimentCalculation.calculate_percentage_error(
            calculated_concentration, theoretical_concentration
        )

        results = {
            "initial_volume": initial_volume,
            "final_volume": final_volume,
            "consumed_volume": consumed_volume,
            "calculated_concentration": calculated_concentration,
            "percentage_error": percentage_error,
            "titrant_concentration": titrant_concentration,
            "analyte_volume": analyte_volume,
        }

        self.calculations["titration_results"] = results
        self.calculation_completed.emit("titration_results", results)

        logger.info(f"滴定结果计算完成: {results}")
        return results

    def calculate_ph_curve(self) -> dict[str, Any]:
        """计算pH曲线"""
        ph_readings = [dp for dp in self.data_points if dp.data_type == "ph_reading"]

        volume_readings = [dp for dp in self.data_points if dp.data_type == "volume_reading"]

        if not ph_readings or not volume_readings:
            return {"error": "pH或体积读数不足"}

        # 创建pH-体积曲线数据
        curve_data = []
        for i, ph_point in enumerate(ph_readings):
            if i < len(volume_readings):
                curve_data.append({"volume": volume_readings[i].value, "ph": ph_point.value})

        results = {
            "curve_data": curve_data,
            "endpoint_volume": curve_data[-1]["volume"] if curve_data else 0,
            "endpoint_ph": curve_data[-1]["ph"] if curve_data else 7.0,
        }

        self.calculations["ph_curve"] = results
        self.calculation_completed.emit("ph_curve", results)

        logger.info(f"pH曲线计算完成: {len(curve_data)} 个数据点")
        return results

    def get_step_data(self, step_id: str) -> list[ExperimentDataPoint]:
        """获取步骤数据"""
        return [dp for dp in self.data_points if dp.step_id == step_id]

    def get_data_by_type(self, data_type: str) -> list[ExperimentDataPoint]:
        """按类型获取数据"""
        return [dp for dp in self.data_points if dp.data_type == data_type]

    def get_experiment_summary(self) -> dict[str, Any]:
        """获取实验摘要"""
        end_time = time.time()
        duration = end_time - self.start_time

        # 统计各类数据
        data_types = {}
        for dp in self.data_points:
            if dp.data_type not in data_types:
                data_types[dp.data_type] = 0
            data_types[dp.data_type] += 1

        # 获取步骤列表
        steps = list({dp.step_id for dp in self.data_points})

        summary = {
            "experiment_id": self.experiment_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "duration_seconds": duration,
            "total_data_points": len(self.data_points),
            "data_types": data_types,
            "steps": steps,
            "calculations": self.calculations,
        }

        return summary

    def export_data(self, file_path: str) -> bool:
        """导出数据到文件"""
        try:
            export_data = {
                "experiment_summary": self.get_experiment_summary(),
                "data_points": [dp.to_dict() for dp in self.data_points],
                "calculations": self.calculations,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"实验数据导出成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return False

    def import_data(self, file_path: str) -> bool:
        """从文件导入数据"""
        try:
            with open(file_path, encoding="utf-8") as f:
                import_data = json.load(f)

            # 导入数据点
            self.data_points = [ExperimentDataPoint.from_dict(dp) for dp in import_data.get("data_points", [])]

            # 导入计算结果
            self.calculations = import_data.get("calculations", {})

            logger.info(f"实验数据导入成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            return False

    def clear_data(self) -> None:
        """清空数据"""
        self.data_points.clear()
        self.calculations.clear()
        self.start_time = time.time()
        logger.info("实验数据已清空")

    def complete_experiment(self) -> dict[str, Any]:
        """完成实验"""
        # 执行最终计算
        titration_results = self.calculate_titration_results()
        ph_curve = self.calculate_ph_curve()

        # 生成最终报告
        final_report = {
            "experiment_summary": self.get_experiment_summary(),
            "titration_results": titration_results,
            "ph_curve": ph_curve,
            "completion_time": datetime.now().isoformat(),
        }

        self.experiment_completed.emit(final_report)
        logger.info("实验完成，生成最终报告")

        return final_report
