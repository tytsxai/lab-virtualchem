"""危险检查器"""

import logging

from src.knowledge.reagent_db import ReagentDatabase
from src.models.knowledge import HazardLevel

logger = logging.getLogger(__name__)


class HazardAlert:
    """危险警报"""

    def __init__(
        self,
        level: HazardLevel,
        title: str,
        message: str,
        action: str = "pause",
    ) -> None:
        """初始化警报

        Args:
            level: 危害等级
            title: 标题
            message: 详细信息
            action: 建议操作(pause/stop/confirm)
        """
        self.level = level
        self.title = title
        self.message = message
        self.action = action


class HazardChecker:
    """危险检查器"""

    def __init__(self, reagent_db: ReagentDatabase) -> None:
        """初始化检查器

        Args:
            reagent_db: 试剂数据库
        """
        self.reagent_db = reagent_db

        # 危险操作规则
        self.hazard_rules = {
            "high_temperature": {
                "threshold": 200,  # °C
                "level": HazardLevel.SEVERE,
                "message": "温度过高,可能导致试剂分解或容器损坏",
            },
            "rapid_mixing_h2so4_water": {
                "level": HazardLevel.CRITICAL,
                "message": "禁止将水快速加入浓硫酸!应将浓硫酸缓慢加入水中",
            },
            "unprotected_corrosive": {
                "level": HazardLevel.SEVERE,
                "message": "操作腐蚀性试剂必须佩戴防护用具",
            },
        }

    def check_temperature(self, temperature: float, reagent_ids: list[str]) -> HazardAlert | None:
        """检查温度是否安全

        Args:
            temperature: 温度(°C)
            reagent_ids: 涉及的试剂ID列表

        Returns:
            危险警报或None
        """
        for reagent_id in reagent_ids:
            reagent = self.reagent_db.get_reagent(reagent_id)
            if not reagent or not reagent.properties:
                continue

            # 检查是否超过沸点
            if reagent.properties.boiling_point and temperature > reagent.properties.boiling_point + 20:
                return HazardAlert(
                    level=HazardLevel.SEVERE,
                    title="温度过高",
                    message=f"{reagent.title} 的沸点为 {reagent.properties.boiling_point}°C, "
                    f"当前温度 {temperature}°C 过高",
                    action="pause",
                )

        # 一般高温警告
        if temperature > 200:
            return HazardAlert(
                level=HazardLevel.WARNING,
                title="高温警告",
                message=f"当前温度 {temperature}°C 较高,请注意安全",
                action="confirm",
            )

        return None

    def check_mixing(self, reagent1_id: str, reagent2_id: str) -> HazardAlert | None:
        """检查两种试剂混合是否安全

        Args:
            reagent1_id: 试剂1的ID
            reagent2_id: 试剂2的ID

        Returns:
            危险警报或None
        """
        # 浓硫酸与水
        if reagent1_id == "h2so4_conc" and reagent2_id == "h2o" or reagent1_id == "h2o" and reagent2_id == "h2so4_conc":
            return HazardAlert(
                level=HazardLevel.CRITICAL,
                title="严重警告:浓硫酸与水混合",
                message="必须将浓硫酸缓慢加入水中,禁止将水加入浓硫酸!",
                action="stop",
            )

        # 获取试剂信息
        reagent1 = self.reagent_db.get_reagent(reagent1_id)
        reagent2 = self.reagent_db.get_reagent(reagent2_id)

        if not reagent1 or not reagent2:
            return None

        # 检查酸碱混合
        is_acid1 = reagent1.has_hazard_type("corrosive") and "酸" in reagent1.title
        is_acid2 = reagent2.has_hazard_type("corrosive") and "酸" in reagent2.title
        is_base1 = reagent1.has_hazard_type("corrosive") and "碱" in reagent1.title
        is_base2 = reagent2.has_hazard_type("corrosive") and "碱" in reagent2.title

        if (is_acid1 and is_base2) or (is_base1 and is_acid2):
            return HazardAlert(
                level=HazardLevel.WARNING,
                title="酸碱中和反应",
                message="酸碱混合会发生中和反应并放热,请缓慢混合",
                action="confirm",
            )

        return None

    def check_reagent_hazards(self, reagent_id: str) -> tuple[HazardLevel, list[str]]:
        """检查试剂的危险性

        Args:
            reagent_id: 试剂ID

        Returns:
            (最高危害等级, 危害提示列表)
        """
        reagent = self.reagent_db.get_reagent(reagent_id)

        if not reagent or not reagent.hazards:
            return HazardLevel.INFO, []

        highest_level = reagent.get_highest_hazard_level() or HazardLevel.INFO
        hints = [h.hint for h in reagent.hazards]

        return highest_level, hints

    def check_protection_equipment(self, reagent_ids: list[str], equipment: list[str]) -> HazardAlert | None:
        """检查防护装备是否充分

        Args:
            reagent_ids: 试剂ID列表
            equipment: 已佩戴的防护装备列表

        Returns:
            危险警报或None
        """
        required_equipment = set()

        for reagent_id in reagent_ids:
            reagent = self.reagent_db.get_reagent(reagent_id)
            if not reagent or not reagent.hazards:
                continue

            # 根据危害类型确定所需防护装备
            for hazard in reagent.hazards:
                if hazard.type == "corrosive":
                    required_equipment.add("gloves")
                    required_equipment.add("goggles")
                    if hazard.level in [HazardLevel.SEVERE, HazardLevel.CRITICAL]:
                        required_equipment.add("lab_coat")
                elif hazard.type == "toxic":
                    required_equipment.add("mask")
                    required_equipment.add("gloves")
                elif hazard.type == "flammable":
                    required_equipment.add("goggles")

        missing = required_equipment - set(equipment)

        if missing:
            equipment_names = {
                "gloves": "防护手套",
                "goggles": "护目镜",
                "mask": "口罩/面罩",
                "lab_coat": "实验服",
            }

            missing_names = [equipment_names.get(e, e) for e in missing]

            return HazardAlert(
                level=HazardLevel.WARNING,
                title="防护装备不足",
                message=f"建议佩戴: {', '.join(missing_names)}",
                action="confirm",
            )

        return None

    def get_emergency_procedures(self, reagent_id: str) -> list[str]:
        """获取应急处理程序

        Args:
            reagent_id: 试剂ID

        Returns:
            应急处理步骤列表
        """
        reagent = self.reagent_db.get_reagent(reagent_id)

        if not reagent or not reagent.hazards:
            return ["无特殊应急处理要求"]

        procedures = []
        for hazard in reagent.hazards:
            if hazard.emergency:
                procedures.append(hazard.emergency)

        return procedures if procedures else ["请参考试剂安全数据表(SDS)"]
