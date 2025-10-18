"""
热力学与动力学计算 - Cantera 适配层
用于高精度化学反应计算（可选，默认禁用）
"""

import logging
from typing import Any

import numpy as np

from . import registry, require_plugin

logger = logging.getLogger(__name__)


class ThermoKineticsCalculator:
    """热力学与动力学计算器"""

    def __init__(self):
        self.cantera = registry.get_module("cantera")
        self._gas = None

    @require_plugin("cantera")
    def initialize_gas(self, mechanism: str = "gri30.yaml", species: list[str] | None = None) -> bool:
        """初始化气体对象

        Args:
            mechanism: 反应机理文件
            species: 包含的物种列表（None表示全部）

        Returns:
            是否成功
        """
        import cantera as ct

        try:
            if species:
                self._gas = ct.Solution(mechanism, species=species)
            else:
                self._gas = ct.Solution(mechanism)

            logger.info(f"Cantera气体对象初始化成功: {mechanism}")
            return True

        except Exception as e:
            logger.error(f"Cantera初始化失败: {e}")
            return False

    @require_plugin("cantera")
    def calculate_equilibrium(
        self, temperature: float, pressure: float, composition: dict[str, float]
    ) -> dict[str, Any] | None:
        """计算化学平衡

        Args:
            temperature: 温度 (K)
            pressure: 压力 (Pa)
            composition: 组分摩尔分数 {'H2': 0.5, 'O2': 0.25, ...}

        Returns:
            平衡状态数据
        """
        if not self._gas:
            logger.error("未初始化气体对象")
            return None

        try:
            self._gas.TPX = temperature, pressure, composition
            self._gas.equilibrate("TP")

            return {
                "temperature": self._gas.T,
                "pressure": self._gas.P,
                "density": self._gas.density,
                "enthalpy": self._gas.enthalpy_mass,
                "entropy": self._gas.entropy_mass,
                "composition": dict(zip(self._gas.species_names, self._gas.X, strict=False)),
            }

        except Exception as e:
            logger.error(f"平衡计算失败: {e}")
            return None

    @require_plugin("cantera")
    def calculate_reaction_rate(
        self, temperature: float, pressure: float, composition: dict[str, float]
    ) -> np.ndarray | None:
        """计算反应速率

        Args:
            temperature: 温度 (K)
            pressure: 压力 (Pa)
            composition: 组分摩尔分数

        Returns:
            各反应的净反应速率数组
        """
        if not self._gas:
            return None

        try:
            self._gas.TPX = temperature, pressure, composition
            return self._gas.net_rates_of_progress

        except Exception as e:
            logger.error(f"反应速率计算失败: {e}")
            return None

    @require_plugin("cantera")
    def simulate_ignition(
        self,
        temperature: float,
        pressure: float,
        composition: dict[str, float],
        time_span: tuple[float, float] = (0, 0.1),
    ) -> dict[str, np.ndarray] | None:
        """模拟自燃过程

        Args:
            temperature: 初始温度 (K)
            pressure: 压力 (Pa)
            composition: 初始组分
            time_span: 时间范围 (s)

        Returns:
            时间序列数据
        """
        import cantera as ct

        if not self._gas:
            return None

        try:
            self._gas.TPX = temperature, pressure, composition

            # 创建反应器
            reactor = ct.IdealGasReactor(self._gas)
            network = ct.ReactorNet([reactor])

            # 时间序列
            times = []
            temps = []
            pressures = []

            t = time_span[0]
            while t < time_span[1]:
                network.advance(t)
                times.append(t)
                temps.append(reactor.T)
                pressures.append(reactor.thermo.P)
                t += (time_span[1] - time_span[0]) / 100

            return {
                "time": np.array(times),
                "temperature": np.array(temps),
                "pressure": np.array(pressures),
            }

        except Exception as e:
            logger.error(f"自燃模拟失败: {e}")
            return None


# 回退实现：简化计算
def _fallback_calculate_equilibrium(
    _self, temperature: float, pressure: float, composition: dict[str, float]
) -> dict[str, Any]:
    """回退：返回简化的平衡数据"""
    logger.warning("Cantera未安装，使用简化计算")

    # 返回输入状态（不进行平衡计算）
    return {
        "temperature": temperature,
        "pressure": pressure,
        "composition": composition,
        "note": "简化计算（未安装Cantera）",
    }


# 注册插件
registry.register(
    name="cantera",
    description="高精度热力学与动力学计算",
    module_name="cantera",
    license="BSD-3-Clause",
    fallback=_fallback_calculate_equilibrium,
)


def get_calculator() -> ThermoKineticsCalculator:
    """获取计算器实例"""
    return ThermoKineticsCalculator()


def is_available() -> bool:
    """检查Cantera是否可用"""
    return registry.is_available("cantera")
