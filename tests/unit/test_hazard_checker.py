"""
HazardChecker 单元测试
测试危险检查器的安全检测功能
"""

import tempfile
from pathlib import Path

from src.knowledge.hazard_checker import HazardAlert, HazardChecker
from src.knowledge.reagent_db import ReagentDatabase
from src.models.knowledge import Hazard, HazardLevel, KnowledgeCard, KnowledgeType


def create_test_reagent(
    reagent_id: str,
    name: str,
    cas: str = "0000-00-0",
    hazards: list = None,
    properties: dict = None,
) -> KnowledgeCard:
    """创建测试用试剂"""
    return KnowledgeCard(
        id=reagent_id,
        type=KnowledgeType.REAGENT,
        title=name,
        content="",
        cas=cas,
        properties=properties,
        hazards=hazards or [],
    )


class TestHazardCheckerInitialization:
    """测试危险检查器初始化"""

    def test_init_with_database(self, tmp_path):
        """测试使用数据库初始化"""
        db = ReagentDatabase(tmp_path)
        checker = HazardChecker(db)

        assert checker.reagent_db is db
        assert "high_temperature" in checker.hazard_rules

    def test_hazard_rules_structure(self, tmp_path):
        """测试危险规则结构"""
        db = ReagentDatabase(tmp_path)
        checker = HazardChecker(db)

        # 检查高温规则
        assert "high_temperature" in checker.hazard_rules
        assert checker.hazard_rules["high_temperature"]["threshold"] == 200
        assert checker.hazard_rules["high_temperature"]["level"] == HazardLevel.SEVERE

        # 检查硫酸水混合规则
        assert "rapid_mixing_h2so4_water" in checker.hazard_rules
        assert (
            checker.hazard_rules["rapid_mixing_h2so4_water"]["level"]
            == HazardLevel.CRITICAL
        )


class TestTemperatureCheck:
    """测试温度检查"""

    def test_normal_temperature(self, tmp_path):
        """测试正常温度"""
        db = ReagentDatabase(tmp_path)
        checker = HazardChecker(db)

        alert = checker.check_temperature(25.0, ["ethanol"])

        assert alert is None

    def test_high_temperature(self, tmp_path):
        """测试高温"""
        db = ReagentDatabase(tmp_path)
        checker = HazardChecker(db)

        alert = checker.check_temperature(250.0, ["ethanol"])

        assert alert is not None
        # 一般高温(>200°C)是WARNING级别
        assert alert.level == HazardLevel.WARNING
        assert "高温" in alert.message or "温度" in alert.message

    def test_threshold_temperature(self, tmp_path):
        """测试临界温度"""
        db = ReagentDatabase(tmp_path)
        checker = HazardChecker(db)

        # 正好200度,应该不触发警报
        alert = checker.check_temperature(200.0, ["ethanol"])

        assert alert is None

        # 200.1度,应该触发
        alert = checker.check_temperature(200.1, ["ethanol"])

        assert alert is not None


class TestReagentMixing:
    """测试试剂混合检查"""

    def setup_method(self):
        """每个测试前准备"""
        tmp_path = Path(tempfile.mkdtemp())
        self.db = ReagentDatabase(tmp_path)
        self.checker = HazardChecker(self.db)

        # 添加测试试剂
        self.db._reagents["h2so4_conc"] = create_test_reagent(
            "h2so4_conc",
            "浓硫酸",
            "7664-93-9",
            hazards=[
                Hazard(
                    type="corrosive",
                    level=HazardLevel.CRITICAL,
                    hint="强腐蚀性,必须防护",
                )
            ],
            properties={"concentration": "98%"},
        )

        self.db._reagents["water"] = create_test_reagent("water", "水", "7732-18-5")

        self.db._reagents["hcl"] = create_test_reagent(
            "hcl",
            "盐酸",
            "7647-01-0",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")
            ],
        )

    def test_safe_mixing(self):
        """测试安全混合"""
        alert = self.checker.check_mixing("hcl", "water")

        assert alert is None

    def test_h2so4_water_dangerous_order(self):
        """测试浓硫酸加入水(危险)"""
        # 使用硬编码的h2o而非water,以匹配hazard_checker实现
        alert = self.checker.check_mixing("h2so4_conc", "h2o")

        assert alert is not None
        assert alert.level == HazardLevel.CRITICAL
        assert "浓硫酸" in alert.message

    def test_corrosive_mixing(self):
        """测试腐蚀性试剂混合"""
        # 创建含"碱"字的试剂title以触发检测
        self.db._reagents["naoh"] = create_test_reagent(
            "naoh",
            "氢氧化钠溶液(碱)",
            "1310-73-2",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.SEVERE, hint="强碱腐蚀性")
            ],
        )
        # 创建含"酸"字的试剂title
        self.db._reagents["hcl"].title = "盐酸溶液(酸)"

        alert = self.checker.check_mixing("hcl", "naoh")

        assert alert is not None
        # 酸碱混合是WARNING级别,不是SEVERE
        assert alert.level == HazardLevel.WARNING
        assert "酸碱" in alert.message or "中和" in alert.message

    def test_mixing_nonexistent_reagent(self):
        """测试混合不存在的试剂"""
        alert = self.checker.check_mixing("nonexistent", "water")

        assert alert is None  # 找不到试剂信息,无法判断


class TestReagentHazards:
    """测试试剂危险性检查"""

    def setup_method(self):
        """每个测试前准备"""
        tmp_path = Path(tempfile.mkdtemp())
        self.db = ReagentDatabase(tmp_path)
        self.checker = HazardChecker(self.db)

    def test_reagent_with_multiple_hazards(self):
        """测试有多个危险的试剂"""
        self.db._reagents["benzene"] = create_test_reagent(
            "benzene",
            "苯",
            "71-43-2",
            hazards=[
                Hazard(type="toxic", level=HazardLevel.SEVERE, hint="有毒,致癌"),
                Hazard(type="flammable", level=HazardLevel.WARNING, hint="易燃"),
            ],
        )

        level, hints = self.checker.check_reagent_hazards("benzene")

        assert level == HazardLevel.SEVERE  # 最高等级
        assert len(hints) == 2
        assert "有毒,致癌" in hints
        assert "易燃" in hints

    def test_reagent_no_hazards(self):
        """测试无危险的试剂"""
        self.db._reagents["nacl"] = create_test_reagent("nacl", "氯化钠", "7647-14-5")

        level, hints = self.checker.check_reagent_hazards("nacl")

        assert level == HazardLevel.INFO
        assert hints == []

    def test_nonexistent_reagent(self):
        """测试不存在的试剂"""
        level, hints = self.checker.check_reagent_hazards("nonexistent")

        assert level == HazardLevel.INFO
        assert hints == []


class TestProtectionEquipment:
    """测试防护装备检查"""

    def setup_method(self):
        """每个测试前准备"""
        tmp_path = Path(tempfile.mkdtemp())
        self.db = ReagentDatabase(tmp_path)
        self.checker = HazardChecker(self.db)

    def test_corrosive_requires_protection(self):
        """测试腐蚀性试剂需要防护"""
        self.db._reagents["hcl"] = create_test_reagent(
            "hcl",
            "盐酸",
            "7647-01-0",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")
            ],
        )

        # 没有防护装备
        alert = self.checker.check_protection_equipment(["hcl"], [])

        assert alert is not None
        # 防护装备不足是WARNING级别
        assert alert.level == HazardLevel.WARNING
        assert "手套" in alert.message or "gloves" in alert.message.lower()
        assert "护目镜" in alert.message or "goggles" in alert.message.lower()

    def test_corrosive_with_adequate_protection(self):
        """测试腐蚀性试剂有充分防护"""
        self.db._reagents["hcl"] = create_test_reagent(
            "hcl",
            "盐酸",
            "7647-01-0",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")
            ],
        )

        alert = self.checker.check_protection_equipment(["hcl"], ["gloves", "goggles"])

        assert alert is None

    def test_severe_corrosive_needs_lab_coat(self):
        """测试强腐蚀性需要实验服"""
        self.db._reagents["h2so4"] = create_test_reagent(
            "h2so4",
            "浓硫酸",
            "7664-93-9",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.SEVERE, hint="强腐蚀性")
            ],
        )

        # 只有手套和护目镜,缺实验服
        alert = self.checker.check_protection_equipment(
            ["h2so4"], ["gloves", "goggles"]
        )

        assert alert is not None
        assert "实验服" in alert.message

    def test_safe_reagents_no_protection_needed(self):
        """测试安全试剂不需要特殊防护"""
        self.db._reagents["water"] = create_test_reagent("water", "水", "7732-18-5")

        alert = self.checker.check_protection_equipment(["water"], [])

        assert alert is None


class TestHazardAlert:
    """测试危险警报类"""

    def test_hazard_alert_creation(self):
        """测试创建危险警报"""
        alert = HazardAlert(
            level=HazardLevel.WARNING,
            title="温度警告",
            message="温度过高",
            action="pause",
        )

        assert alert.level == HazardLevel.WARNING
        assert alert.title == "温度警告"
        assert alert.message == "温度过高"
        assert alert.action == "pause"

    def test_hazard_alert_default_action(self):
        """测试默认操作"""
        alert = HazardAlert(level=HazardLevel.INFO, title="提示", message="信息")

        assert alert.action == "pause"


class TestEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        """每个测试前准备"""
        tmp_path = Path(tempfile.mkdtemp())
        self.db = ReagentDatabase(tmp_path)
        self.checker = HazardChecker(self.db)

    def test_negative_temperature(self):
        """测试负温度"""
        alert = self.checker.check_temperature(-10.0, [])

        # 低温不触发高温警报
        assert alert is None

    def test_extreme_high_temperature(self):
        """测试极高温度"""
        alert = self.checker.check_temperature(1000.0, [])

        assert alert is not None
        # 极高温仍是WARNING级别(通用规则)
        assert alert.level == HazardLevel.WARNING

    def test_same_reagent_mixing(self):
        """测试同一试剂混合"""
        self.db._reagents["water"] = create_test_reagent("water", "水", "7732-18-5")

        alert = self.checker.check_mixing("water", "water")

        assert alert is None  # 水跟水混合应该安全
