"""单位转换与管理模块

使用Pint库提供物理单位的定义、转换和验证功能。
避免单位错误,提升实验数据的准确性。
"""

import logging
from typing import Any

try:
    from pint import DimensionalityError, Quantity, UnitRegistry

    PINT_AVAILABLE = True
except ImportError:
    PINT_AVAILABLE = False
    UnitRegistry = None
    Quantity = None
    DimensionalityError = Exception

logger = logging.getLogger(__name__)


class UnitConverter:
    """单位转换器"""

    def __init__(self) -> None:
        """初始化单位转换器"""
        self.available = PINT_AVAILABLE

        if self.available:
            self.ureg = UnitRegistry()
            # 定义常用化学单位
            self._register_chemistry_units()
        else:
            self.ureg = None
            logger.warning("Pint未安装,单位转换功能不可用. 安装: pip install pint")

    def _register_chemistry_units(self) -> None:
        """注册化学常用单位"""
        if not self.available:
            return

        # 摩尔浓度单位
        self.ureg.define("M = mol / L = molar")
        self.ureg.define("mM = 0.001 * M = millimolar")
        self.ureg.define("uM = 0.000001 * M = micromolar")

        # pH单位(对数单位,特殊处理)
        # pH值本身无量纲,但可以定义方便计算
        self.ureg.define("pH = [] = pH_unit")

    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        """单位转换

        Args:
            value: 数值
            from_unit: 源单位
            to_unit: 目标单位

        Returns:
            转换后的数值

        Raises:
            ValueError: 单位不兼容时
        """
        if not self.available:
            logger.warning("Pint不可用,返回原值")
            return value

        try:
            quantity = value * self.ureg(from_unit)
            converted = quantity.to(to_unit)
            return float(converted.magnitude)
        except DimensionalityError as e:
            raise ValueError(f"单位不兼容: {from_unit} -> {to_unit}") from e

    def create_quantity(self, value: float, unit: str) -> Any | float:
        """创建带单位的量

        Args:
            value: 数值
            unit: 单位

        Returns:
            Pint Quantity对象,如果不可用返回原值
        """
        if not self.available:
            return value

        try:
            return value * self.ureg(unit)
        except Exception as e:
            logger.error(f"创建Quantity失败: {e}")
            return value

    def validate_unit(self, value: float, unit: str, expected_dimension: str) -> bool:
        """验证单位维度

        Args:
            value: 数值
            unit: 单位
            expected_dimension: 期望的维度 (如 '[length]', '[mass]', '[substance] / [volume]')

        Returns:
            是否符合期望维度
        """
        if not self.available:
            return True  # 无法验证,假设正确

        try:
            quantity = value * self.ureg(unit)
            expected = self.ureg(expected_dimension)
            return quantity.dimensionality == expected.dimensionality
        except Exception as e:
            logger.error(f"单位验证失败: {e}")
            return False

    def format_quantity(self, value: float, unit: str, precision: int = 2) -> str:
        """格式化带单位的量

        Args:
            value: 数值
            unit: 单位
            precision: 小数位数

        Returns:
            格式化字符串
        """
        if not self.available:
            return f"{value:.{precision}f} {unit}"

        try:
            quantity = value * self.ureg(unit)
            return f"{quantity:.{precision}f~P}"  # ~P 使用紧凑格式
        except Exception as e:
            logger.error(f"格式化失败: {e}")
            return f"{value:.{precision}f} {unit}"

    # 常用化学单位转换快捷方法

    def volume_to_liter(self, value: float, unit: str) -> float:
        """体积转换为升"""
        return self.convert(value, unit, "L")

    def volume_to_ml(self, value: float, unit: str) -> float:
        """体积转换为毫升"""
        return self.convert(value, unit, "mL")

    def mass_to_gram(self, value: float, unit: str) -> float:
        """质量转换为克"""
        return self.convert(value, unit, "g")

    def concentration_to_molar(self, value: float, unit: str) -> float:
        """浓度转换为摩尔/升"""
        return self.convert(value, unit, "M")

    def temperature_to_celsius(self, value: float, unit: str) -> float:
        """温度转换为摄氏度"""
        return self.convert(value, unit, "degC")

    def temperature_to_kelvin(self, value: float, unit: str) -> float:
        """温度转换为开尔文"""
        return self.convert(value, unit, "K")

    def pressure_to_atm(self, value: float, unit: str) -> float:
        """压强转换为大气压"""
        return self.convert(value, unit, "atm")

    def pressure_to_pascal(self, value: float, unit: str) -> float:
        """压强转换为帕斯卡"""
        return self.convert(value, unit, "Pa")

    # 化学计算辅助方法

    def calculate_molarity(self, moles: float, volume_ml: float) -> float:
        """计算摩尔浓度

        Args:
            moles: 物质的量(mol)
            volume_ml: 体积(mL)

        Returns:
            摩尔浓度(M)
        """
        if not self.available:
            return moles / (volume_ml / 1000.0)

        n = moles * self.ureg.mol
        V = volume_ml * self.ureg.mL
        M = (n / V).to("M")
        return float(M.magnitude)

    def calculate_mass(self, moles: float, molecular_weight: float) -> float:
        """计算质量

        Args:
            moles: 物质的量(mol)
            molecular_weight: 分子量(g/mol)

        Returns:
            质量(g)
        """
        if not self.available:
            return moles * molecular_weight

        n = moles * self.ureg.mol
        M = molecular_weight * self.ureg("g/mol")
        mass = (n * M).to("g")
        return float(mass.magnitude)

    def calculate_volume(self, moles: float, concentration_M: float) -> float:
        """计算体积

        Args:
            moles: 物质的量(mol)
            concentration_M: 浓度(M)

        Returns:
            体积(L)
        """
        if not self.available:
            return moles / concentration_M

        n = moles * self.ureg.mol
        C = concentration_M * self.ureg.M
        V = (n / C).to("L")
        return float(V.magnitude)

    def dilution_calculation(
        self,
        C1: float,
        V1: float,
        C2: float,
        V2: float | None = None,
        C1_unit: str = "M",
        V1_unit: str = "mL",
        C2_unit: str = "M",
        V2_unit: str = "mL",
    ) -> dict[str, float]:
        """稀释计算 C1V1 = C2V2

        Args:
            C1: 浓缩液浓度
            V1: 浓缩液体积
            C2: 稀释液浓度
            V2: 稀释液体积(可选)
            *_unit: 各参数单位

        Returns:
            计算结果字典
        """
        if not self.available:
            # 简化计算(假设单位一致)
            if V2 is None:
                V2 = (C1 * V1) / C2
            return {"C1": C1, "V1": V1, "C2": C2, "V2": V2}

        c1 = C1 * self.ureg(C1_unit)
        v1 = V1 * self.ureg(V1_unit)
        c2 = C2 * self.ureg(C2_unit)

        if V2 is None:
            # 计算V2
            v2 = (c1 * v1 / c2).to(V2_unit)
            V2 = float(v2.magnitude)
        else:
            v2 = V2 * self.ureg(V2_unit)

        return {
            "C1": float(c1.to(C1_unit).magnitude),
            "V1": float(v1.to(V1_unit).magnitude),
            "C2": float(c2.to(C2_unit).magnitude),
            "V2": float(v2.to(V2_unit).magnitude),
        }


# 全局实例
unit_converter = UnitConverter()


# 便捷函数
def convert(value: float, from_unit: str, to_unit: str) -> float:
    """便捷函数: 单位转换"""
    return unit_converter.convert(value, from_unit, to_unit)


def create_quantity(value: float, unit: str) -> Any | float:
    """便捷函数: 创建带单位的量"""
    return unit_converter.create_quantity(value, unit)


def format_value(value: float, unit: str, precision: int = 2) -> str:
    """便捷函数: 格式化数值"""
    return unit_converter.format_quantity(value, unit, precision)
