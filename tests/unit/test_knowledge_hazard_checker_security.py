from unittest.mock import Mock

from src.knowledge.hazard_checker import HazardChecker
from src.models.knowledge import (
    Hazard,
    HazardLevel,
    KnowledgeCard,
    KnowledgeType,
    PhysicalProperties,
)


def test_check_temperature_boiling_point_exceeded():
    reagent = KnowledgeCard(
        id="ethanol",
        type=KnowledgeType.REAGENT,
        title="乙醇",
        content="x",
        properties=PhysicalProperties(boiling_point=78.0),
        hazards=[],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = reagent

    checker = HazardChecker(reagent_db)
    alert = checker.check_temperature(110.0, ["ethanol"])

    assert alert is not None
    assert alert.level == HazardLevel.SEVERE
    assert "沸点" in alert.message


def test_check_temperature_high_temperature_warning():
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = None
    checker = HazardChecker(reagent_db)

    alert = checker.check_temperature(250.0, [])
    assert alert is not None
    assert alert.level == HazardLevel.WARNING
    assert alert.action == "confirm"


def test_check_mixing_h2so4_water_is_critical():
    reagent_db = Mock()
    checker = HazardChecker(reagent_db)
    alert = checker.check_mixing("h2so4_conc", "h2o")

    assert alert is not None
    assert alert.level == HazardLevel.CRITICAL
    assert alert.action == "stop"


def test_check_mixing_acid_base_warning():
    acid = KnowledgeCard(
        id="hcl",
        type=KnowledgeType.REAGENT,
        title="盐酸",
        content="x",
        hazards=[Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")],
    )
    base = KnowledgeCard(
        id="naoh",
        type=KnowledgeType.REAGENT,
        title="氢氧化钠(强碱)",
        content="x",
        hazards=[Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.side_effect = lambda rid: {"hcl": acid, "naoh": base}.get(
        rid
    )

    checker = HazardChecker(reagent_db)
    alert = checker.check_mixing("hcl", "naoh")

    assert alert is not None
    assert alert.level == HazardLevel.WARNING
    assert "中和" in alert.title


def test_check_reagent_hazards_and_emergency_procedures():
    reagent = KnowledgeCard(
        id="x",
        type=KnowledgeType.REAGENT,
        title="X",
        content="x",
        hazards=[
            Hazard(
                type="toxic",
                level=HazardLevel.SEVERE,
                hint="有毒",
                emergency="立即就医",
            )
        ],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = reagent

    checker = HazardChecker(reagent_db)
    level, hints = checker.check_reagent_hazards("x")

    assert level == HazardLevel.SEVERE
    assert hints == ["有毒"]
    assert checker.get_emergency_procedures("x") == ["立即就医"]


def test_check_protection_equipment_detects_missing():
    reagent = KnowledgeCard(
        id="acid",
        type=KnowledgeType.REAGENT,
        title="酸",
        content="x",
        hazards=[
            Hazard(type="corrosive", level=HazardLevel.SEVERE, hint="腐蚀性"),
            Hazard(type="toxic", level=HazardLevel.WARNING, hint="有毒"),
        ],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = reagent

    checker = HazardChecker(reagent_db)
    alert = checker.check_protection_equipment(["acid"], equipment=["goggles"])

    assert alert is not None
    assert alert.level == HazardLevel.WARNING
    assert "建议佩戴" in alert.message


def test_protection_equipment_sufficient_returns_none():
    reagent = KnowledgeCard(
        id="acid",
        type=KnowledgeType.REAGENT,
        title="酸",
        content="x",
        hazards=[Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = reagent

    checker = HazardChecker(reagent_db)
    assert (
        checker.check_protection_equipment(["acid"], equipment=["gloves", "goggles"])
        is None
    )


def test_emergency_procedures_default_messages():
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = None
    checker = HazardChecker(reagent_db)
    assert checker.get_emergency_procedures("missing") == ["无特殊应急处理要求"]


def test_additional_hazard_checker_branches():
    reagent_no_emergency = KnowledgeCard(
        id="r",
        type=KnowledgeType.REAGENT,
        title="R",
        content="x",
        hazards=[Hazard(type="toxic", level=HazardLevel.WARNING, hint="h")],
    )
    reagent_db = Mock()
    reagent_db.get_reagent.return_value = reagent_no_emergency
    checker = HazardChecker(reagent_db)

    assert checker.get_emergency_procedures("r") == ["请参考试剂安全数据表(SDS)"]
    assert checker.check_reagent_hazards("r")[0] == HazardLevel.WARNING

    reagent_no_hazards = KnowledgeCard(
        id="safe",
        type=KnowledgeType.REAGENT,
        title="safe",
        content="x",
        hazards=[],
    )
    reagent_db.get_reagent.return_value = reagent_no_hazards
    assert checker.check_reagent_hazards("safe") == (HazardLevel.INFO, [])

    reagent_db.get_reagent.return_value = None
    assert checker.check_mixing("x", "y") is None
    assert checker.check_temperature(25.0, ["x"]) is None
