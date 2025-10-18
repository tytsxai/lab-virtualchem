"""曲线生成器 - 基于参数生成实验曲线"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class CurveGenerationError(Exception):
    """曲线生成错误"""

    pass


class CurveGenerator:
    """曲线生成器"""

    # pKa值数据库(来源: CRC Handbook)
    PKA_VALUES = {
        "acetic_acid": 4.76,  # 醋酸
        "formic_acid": 3.75,  # 甲酸
        "carbonic_acid_1": 6.35,  # 碳酸第一电离
        "carbonic_acid_2": 10.33,  # 碳酸第二电离
        "phosphoric_acid_1": 2.15,  # 磷酸第一电离
        "phosphoric_acid_2": 7.20,  # 磷酸第二电离
        "phosphoric_acid_3": 12.35,  # 磷酸第三电离
    }

    def __init__(self) -> None:
        """初始化曲线生成器"""
        pass

    def generate(self, curve_type: str, params: dict[str, Any], num_points: int = 100) -> tuple[np.ndarray, np.ndarray]:
        """生成曲线数据

        Args:
            curve_type: 曲线类型("titration_ph" / "temp_time" / ...)
            params: 参数字典(浓度、体积、温度等)
            num_points: 采样点数

        Returns:
            (x_data, y_data) 元组

        Raises:
            CurveGenerationError: 曲线生成失败
        """
        try:
            if curve_type == "titration_ph":
                return self.generate_titration_curve(
                    acid_type=params.get("acid_type", "strong"),
                    acid_M=params["acid_M"],
                    acid_V_ml=params["acid_V_ml"],
                    base_M=params["base_M"],
                    num_points=num_points,
                )
            elif curve_type == "temp_time":
                return self.generate_temperature_curve(
                    mode=params.get("mode", "heating"),
                    initial_temp=params["initial_temp"],
                    params=params,
                    num_points=num_points,
                )
            else:
                raise CurveGenerationError(f"不支持的曲线类型: {curve_type}")

        except KeyError as e:
            raise CurveGenerationError(f"缺少必要参数: {e}") from e
        except Exception as e:
            logger.error(f"曲线生成失败: {e}")
            raise CurveGenerationError(f"曲线生成失败: {e}") from e

    def generate_titration_curve(
        self,
        acid_type: str,
        acid_M: float,
        acid_V_ml: float,
        base_M: float,
        num_points: int = 100,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成滴定曲线(pH-体积)

        Args:
            acid_type: 酸类型("strong" / "weak" / "acetic_acid" / ...)
            acid_M: 酸浓度(mol/L)
            acid_V_ml: 酸体积(mL)
            base_M: 碱浓度(mol/L)
            num_points: 采样点数

        Returns:
            (体积数组, pH数组)
        """
        # 计算等当点体积
        V_eq = acid_M * acid_V_ml / base_M

        # 生成体积点(等当点附近加密)
        V_before = np.linspace(0, V_eq * 0.9, num_points // 3)
        V_near = np.linspace(V_eq * 0.9, V_eq * 1.1, num_points // 3)
        V_after = np.linspace(V_eq * 1.1, V_eq * 2, num_points // 3)
        V = np.concatenate([V_before, V_near, V_after])

        pH = np.zeros_like(V)

        if acid_type == "strong":
            # 强酸-强碱滴定
            pH = self._strong_acid_strong_base_titration(V, acid_M, acid_V_ml, base_M, V_eq)
        else:
            # 弱酸-强碱滴定
            pKa = self.PKA_VALUES.get(acid_type, 4.76)  # 默认使用醋酸pKa
            pH = self._weak_acid_strong_base_titration(V, acid_M, acid_V_ml, base_M, V_eq, pKa)

        # 添加随机噪声(±0.05 pH)
        noise = np.random.normal(0, 0.05, size=pH.shape)
        pH = np.clip(pH + noise, 0, 14)

        return V, pH

    def _strong_acid_strong_base_titration(
        self,
        V: np.ndarray,
        acid_M: float,
        acid_V_ml: float,
        base_M: float,
        V_eq: float,
    ) -> np.ndarray:
        """强酸-强碱滴定pH计算"""
        pH = np.zeros_like(V)

        for i, v in enumerate(V):
            if v < V_eq * 0.001:
                # 滴定前
                pH[i] = -np.log10(acid_M)
            elif v < V_eq:
                # 等当点前:剩余酸
                n_acid_remain = acid_M * acid_V_ml - base_M * v
                V_total = acid_V_ml + v
                H_concentration = n_acid_remain / V_total
                pH[i] = -np.log10(max(H_concentration, 1e-14))
            elif abs(v - V_eq) < 0.01:
                # 等当点
                pH[i] = 7.0
            else:
                # 等当点后:过量碱
                n_base_excess = base_M * v - acid_M * acid_V_ml
                V_total = acid_V_ml + v
                OH_concentration = n_base_excess / V_total
                pOH = -np.log10(max(OH_concentration, 1e-14))
                pH[i] = 14 - pOH

        return pH

    def _weak_acid_strong_base_titration(
        self,
        V: np.ndarray,
        acid_M: float,
        acid_V_ml: float,
        base_M: float,
        V_eq: float,
        pKa: float,
    ) -> np.ndarray:
        """弱酸-强碱滴定pH计算(Henderson-Hasselbalch方程)"""
        pH = np.zeros_like(V)

        for i, v in enumerate(V):
            if v < V_eq * 0.001:
                # 滴定前:弱酸溶液
                # pH ≈ (pKa - log[HA])/2
                pH[i] = (pKa - np.log10(acid_M)) / 2
            elif v < V_eq * 0.5:
                # 缓冲区前段
                f = v / V_eq  # 滴定分数
                pH[i] = pKa + np.log10(f / (1 - f))
            elif v < V_eq:
                # 缓冲区后段(接近等当点)
                f = v / V_eq
                # Henderson-Hasselbalch方程
                pH[i] = pKa + np.log10(f / (1 - f))
            elif abs(v - V_eq) < 0.01:
                # 等当点:盐溶液(碱性)
                pH[i] = 7 + (pKa + np.log10(acid_M)) / 2
            else:
                # 等当点后:过量强碱主导
                n_base_excess = base_M * v - acid_M * acid_V_ml
                V_total = acid_V_ml + v
                OH_concentration = n_base_excess / V_total
                pOH = -np.log10(max(OH_concentration, 1e-14))
                pH[i] = 14 - pOH

        return pH

    def generate_temperature_curve(
        self,
        mode: str,
        initial_temp: float,
        params: dict[str, Any],
        num_points: int = 100,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成温度曲线(温度-时间)

        Args:
            mode: 模式("heating" / "cooling")
            initial_temp: 初始温度(°C)
            params: 参数字典
            num_points: 采样点数

        Returns:
            (时间数组, 温度数组)
        """
        total_time = params.get("total_time_s", 600)  # 默认10分钟
        t = np.linspace(0, total_time, num_points)

        if mode == "heating":
            # 加热曲线
            power_W = params.get("power_W", 100)  # 加热功率
            mass_g = params.get("mass_g", 100)  # 质量
            specific_heat = params.get("specific_heat", 4.18)  # 比热容 J/(g·K)
            boiling_point = params.get("boiling_point", 100)  # 沸点

            # 恒功率加热: T = T0 + (P*t)/(m*c)
            temp = initial_temp + (power_W * t) / (mass_g * specific_heat)

            # 到达沸点后恒定
            temp = np.minimum(temp, boiling_point)

        else:
            # 冷却曲线(牛顿冷却定律)
            ambient_temp = params.get("ambient_temp", 25)  # 环境温度
            k = params.get("cooling_constant", 0.01)  # 冷却常数

            # T(t) = T_amb + (T0 - T_amb) * exp(-kt)
            temp = ambient_temp + (initial_temp - ambient_temp) * np.exp(-k * t)

        # 添加随机噪声(±0.5°C)
        noise = np.random.normal(0, 0.5, size=temp.shape)
        temp = temp + noise

        return t, temp
