"""
化学反应模拟器
实现试剂混合、颜色变化、反应过程等交互功能
"""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QColor

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChemicalReagent:
    """化学试剂类"""

    def __init__(
        self,
        reagent_id: str,
        name: str,
        concentration: float = 0.1,
        volume: float = 0.0,
        color: str = "#ffffff",
        ph: float = 7.0,
        density: float = 1.0,
        properties: dict[str, Any] | None = None,
    ):
        self.reagent_id = reagent_id
        self.name = name
        self.concentration = concentration  # mol/L
        self.volume = volume  # mL
        self.color = QColor(color)
        self.ph = ph
        self.density = density
        self.properties = properties or {}

    def get_moles(self) -> float:
        """获取摩尔数"""
        return self.concentration * self.volume / 1000.0

    def add_volume(self, volume: float) -> None:
        """添加体积"""
        self.volume += volume

    def mix_with(self, other: ChemicalReagent) -> ChemicalReagent:
        """与另一种试剂混合"""
        # 计算混合后的浓度
        total_volume = self.volume + other.volume
        if total_volume == 0:
            return ChemicalReagent("mixed", "混合溶液")

        # 加权平均浓度
        mixed_concentration = (
            (self.get_moles() + other.get_moles()) * 1000.0 / total_volume
        )

        # 混合颜色（简单平均）
        mixed_color = self._blend_colors(self.color, other.color)

        # 混合pH（简化计算）
        mixed_ph = self._calculate_mixed_ph(self, other)

        return ChemicalReagent(
            reagent_id="mixed",
            name="混合溶液",
            concentration=mixed_concentration,
            volume=total_volume,
            color=mixed_color.name(),
            ph=mixed_ph,
        )

    def _blend_colors(self, color1: QColor, color2: QColor) -> QColor:
        """混合两种颜色"""
        # 简单的颜色混合算法
        r = (color1.red() + color2.red()) // 2
        g = (color1.green() + color2.green()) // 2
        b = (color1.blue() + color2.blue()) // 2
        return QColor(r, g, b)

    def _calculate_mixed_ph(
        self, reagent1: ChemicalReagent, reagent2: ChemicalReagent
    ) -> float:
        """计算混合溶液的pH（简化）"""
        # 对于强酸强碱的简单计算
        if reagent1.ph < 7 and reagent2.ph > 7:
            # 酸碱中和
            moles_h = reagent1.get_moles() * (7 - reagent1.ph)
            moles_oh = reagent2.get_moles() * (reagent2.ph - 7)

            if abs(moles_h - moles_oh) < 0.001:
                return 7.0  # 完全中和
            elif moles_h > moles_oh:
                # 酸性
                excess_h = moles_h - moles_oh
                return 7.0 - math.log10(
                    excess_h / (reagent1.volume + reagent2.volume) * 1000
                )
            else:
                # 碱性
                excess_oh = moles_oh - moles_h
                return 7.0 + math.log10(
                    excess_oh / (reagent1.volume + reagent2.volume) * 1000
                )

        # 其他情况简单平均
        return (reagent1.ph + reagent2.ph) / 2.0


class Indicator:
    """指示剂类"""

    def __init__(
        self,
        indicator_id: str,
        name: str,
        color_range: tuple[str, str],
        ph_range: tuple[float, float],
    ):
        self.indicator_id = indicator_id
        self.name = name
        self.color_range = color_range
        self.ph_range = ph_range

    def get_color_at_ph(self, ph: float) -> QColor:
        """根据pH值获取指示剂颜色"""
        if ph <= self.ph_range[0]:
            return QColor(self.color_range[0])
        elif ph >= self.ph_range[1]:
            return QColor(self.color_range[1])
        else:
            # 在变色范围内，计算中间颜色
            ratio = (ph - self.ph_range[0]) / (self.ph_range[1] - self.ph_range[0])
            color1 = QColor(self.color_range[0])
            color2 = QColor(self.color_range[1])

            r = int(color1.red() + (color2.red() - color1.red()) * ratio)
            g = int(color1.green() + (color2.green() - color1.green()) * ratio)
            b = int(color1.blue() + (color2.blue() - color1.blue()) * ratio)

            return QColor(r, g, b)


class ChemicalReactionSimulator(QObject):
    """化学反应模拟器"""

    # 信号
    reagent_added = Signal(str, float)  # 试剂ID, 体积
    solution_mixed = Signal(str, str, dict[str, Any])  # 试剂1ID, 试剂2ID, 结果
    color_changed = Signal(str, str)  # 容器ID, 新颜色
    ph_changed = Signal(str, float)  # 容器ID, 新pH
    reaction_completed = Signal(str, dict[str, Any])  # 反应ID, 结果

    def __init__(self) -> None:
        super().__init__()

        # 试剂库
        self.reagents: dict[str, ChemicalReagent] = {}
        self.indicators: dict[str, Indicator] = {}

        # 容器状态
        self.containers: dict[str, dict[str, Any]] = {}

        # 反应计时器
        self.reaction_timer = QTimer(self)
        self.reaction_timer.timeout.connect(self._update_reactions)
        self.reaction_timer.setInterval(100)  # 100ms更新一次

        self._initialize_reagents()
        self._initialize_indicators()

        logger.info("化学反应模拟器初始化完成")

    def _initialize_reagents(self) -> None:
        """初始化试剂库"""
        self.reagents = {
            "hcl": ChemicalReagent(
                reagent_id="hcl",
                name="盐酸",
                concentration=0.1,
                color="#ffffff",
                ph=1.0,
                density=1.05,
            ),
            "naoh": ChemicalReagent(
                reagent_id="naoh",
                name="氢氧化钠",
                concentration=0.1,
                color="#ffffff",
                ph=13.0,
                density=1.0,
            ),
            "water": ChemicalReagent(
                reagent_id="water",
                name="蒸馏水",
                concentration=0.0,
                color="#ffffff",
                ph=7.0,
                density=1.0,
            ),
        }

    def _initialize_indicators(self) -> None:
        """初始化指示剂库"""
        self.indicators = {
            "phenolphthalein": Indicator(
                indicator_id="phenolphthalein",
                name="酚酞",
                color_range=("#ffffff", "#ff69b4"),  # 无色到粉红色
                ph_range=(8.2, 10.0),
            ),
            "methyl_orange": Indicator(
                indicator_id="methyl_orange",
                name="甲基橙",
                color_range=("#ff4500", "#ffff00"),  # 红色到黄色
                ph_range=(3.1, 4.4),
            ),
        }

    def add_reagent_to_container(
        self, container_id: str, reagent_id: str, volume: float
    ) -> bool:
        """向容器中添加试剂"""
        if reagent_id not in self.reagents:
            logger.error(f"未知试剂: {reagent_id}")
            return False

        if container_id not in self.containers:
            self.containers[container_id] = {
                "reagents": {},
                "total_volume": 0.0,
                "ph": 7.0,
                "color": "#ffffff",
            }

        container = self.containers[container_id]
        reagent = self.reagents[reagent_id]

        # 添加试剂
        if reagent_id in container["reagents"]:
            container["reagents"][reagent_id] += volume
        else:
            container["reagents"][reagent_id] = volume

        container["total_volume"] += volume

        # 计算新的pH和颜色
        self._update_container_properties(container_id)

        self.reagent_added.emit(reagent_id, volume)
        logger.info(f"向容器 {container_id} 添加 {volume}mL {reagent.name}")

        return True

    def add_indicator_to_container(self, container_id: str, indicator_id: str) -> bool:
        """向容器中添加指示剂"""
        if indicator_id not in self.indicators:
            logger.error(f"未知指示剂: {indicator_id}")
            return False

        if container_id not in self.containers:
            logger.error(f"容器不存在: {container_id}")
            return False

        container = self.containers[container_id]
        indicator = self.indicators[indicator_id]

        # 添加指示剂
        container["indicator"] = indicator_id

        # 更新颜色
        self._update_container_properties(container_id)

        logger.info(f"向容器 {container_id} 添加指示剂 {indicator.name}")
        return True

    def _update_container_properties(self, container_id: str) -> None:
        """更新容器属性（pH、颜色等）"""
        container = self.containers[container_id]

        if not container["reagents"]:
            container["ph"] = 7.0
            container["color"] = "#ffffff"
            return

        # 计算混合溶液的pH
        total_moles_h = 0.0
        total_moles_oh = 0.0
        total_volume = container["total_volume"]

        for reagent_id, _volume in container["reagents"].items():
            reagent = self.reagents[reagent_id]
            moles = reagent.get_moles()

            if reagent.ph < 7:
                total_moles_h += moles
            elif reagent.ph > 7:
                total_moles_oh += moles

        # 计算pH
        if total_moles_h > total_moles_oh:
            # 酸性
            excess_h = total_moles_h - total_moles_oh
            container["ph"] = max(0.0, 7.0 - math.log10(excess_h / total_volume * 1000))
        elif total_moles_oh > total_moles_h:
            # 碱性
            excess_oh = total_moles_oh - total_moles_h
            container["ph"] = min(
                14.0, 7.0 + math.log10(excess_oh / total_volume * 1000)
            )
        else:
            # 中性
            container["ph"] = 7.0

        # 计算颜色
        if "indicator" in container:
            indicator_id = container["indicator"]
            indicator = self.indicators[indicator_id]
            container["color"] = indicator.get_color_at_ph(container["ph"]).name()
        else:
            # 无指示剂时，根据pH显示颜色
            container["color"] = self._get_ph_color(container["ph"])

        # 发送信号
        self.ph_changed.emit(container_id, container["ph"])
        self.color_changed.emit(container_id, container["color"])

    def _get_ph_color(self, ph: float) -> str:
        """根据pH值获取颜色"""
        if ph < 3:
            return "#ff0000"  # 红色
        elif ph < 5:
            return "#ff6600"  # 橙红色
        elif ph < 6:
            return "#ffaa00"  # 橙色
        elif ph < 7:
            return "#ffff00"  # 黄色
        elif ph < 8:
            return "#aaff00"  # 黄绿色
        elif ph < 9:
            return "#00ff00"  # 绿色
        elif ph < 11:
            return "#00aaff"  # 蓝色
        else:
            return "#0000ff"  # 深蓝色

    def get_container_state(self, container_id: str) -> dict[str, Any] | None:
        """获取容器状态"""
        return self.containers.get(container_id)

    def clear_container(self, container_id: str) -> None:
        """清空容器"""
        if container_id in self.containers:
            self.containers[container_id] = {
                "reagents": {},
                "total_volume": 0.0,
                "ph": 7.0,
                "color": "#ffffff",
            }
            self.ph_changed.emit(container_id, 7.0)
            self.color_changed.emit(container_id, "#ffffff")
            logger.info(f"清空容器 {container_id}")

    def start_reaction_simulation(self) -> None:
        """开始反应模拟"""
        self.reaction_timer.start()
        logger.info("开始反应模拟")

    def stop_reaction_simulation(self) -> None:
        """停止反应模拟"""
        self.reaction_timer.stop()
        logger.info("停止反应模拟")

    def _update_reactions(self) -> None:
        """更新反应状态"""
        try:
            # 遍历所有容器，检查是否有反应进行
            for container_id, container_data in self.containers.items():
                reagents = container_data.get("reagents", {})

                # 如果容器中有多种试剂，检查可能的反应
                if len(reagents) >= 2:
                    # 检查酸碱中和反应
                    if "hcl" in reagents and "naoh" in reagents:
                        # 计算反应量（简化模型：假设反应速率与浓度乘积成正比）
                        hcl_amount = reagents["hcl"]
                        naoh_amount = reagents["naoh"]

                        # 计算最小反应量（限制试剂）
                        reaction_amount = (
                            min(hcl_amount, naoh_amount) * 0.01
                        )  # 每次消耗1%

                        if reaction_amount > 0.001:  # 最小反应阈值
                            # 更新试剂量
                            reagents["hcl"] -= reaction_amount
                            reagents["naoh"] -= reaction_amount

                            # 生成产物（NaCl + H2O）
                            if "nacl" not in reagents:
                                reagents["nacl"] = 0.0
                            reagents["nacl"] += reaction_amount

                            # 更新pH值（简化：基于酸碱剩余量）
                            if reagents["hcl"] > reagents["naoh"]:
                                new_ph = (
                                    3.0 + (reagents["naoh"] / reagents["hcl"]) * 4.0
                                )
                            elif reagents["naoh"] > reagents["hcl"]:
                                new_ph = (
                                    11.0 - (reagents["hcl"] / reagents["naoh"]) * 4.0
                                )
                            else:
                                new_ph = 7.0

                            container_data["ph"] = new_ph
                            self.ph_changed.emit(container_id, new_ph)

                            # 发送反应完成信号（如果反应基本完成）
                            if min(hcl_amount, naoh_amount) < 0.01:
                                self.reaction_completed.emit(
                                    "neutralization",
                                    {
                                        "container_id": container_id,
                                        "product": "nacl",
                                        "amount": reagents["nacl"],
                                        "final_ph": new_ph,
                                    },
                                )
                                logger.info(
                                    f"容器 {container_id} 中和反应完成，pH={new_ph:.2f}"
                                )

        except Exception as e:
            logger.error(f"更新反应状态失败: {e}", exc_info=True)

    def get_reagent_info(self, reagent_id: str) -> ChemicalReagent | None:
        """获取试剂信息"""
        return self.reagents.get(reagent_id)

    def get_indicator_info(self, indicator_id: str) -> Indicator | None:
        """获取指示剂信息"""
        return self.indicators.get(indicator_id)
