import json


def test_get_incompatible_pairs_falls_back_on_invalid_schema(tmp_path, monkeypatch):
    from src.knowledge.reagent_db import ReagentDatabase

    safety_file = tmp_path / "safety.json"
    safety_file.write_text(
        json.dumps(
            [
                {
                    "name": "试剂配伍禁忌",
                    "incompatible_pairs": "not-a-list",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = ReagentDatabase.__new__(ReagentDatabase)
    monkeypatch.setattr(db, "_get_safety_file_path", lambda: safety_file)

    pairs = db.get_incompatible_pairs()
    assert any(p[0] == "h2so4_conc" and p[1] == "h2o" for p in pairs)


def test_get_incompatible_pairs_parses_valid_schema(tmp_path, monkeypatch):
    from src.knowledge.reagent_db import ReagentDatabase

    safety_file = tmp_path / "safety.json"
    safety_file.write_text(
        json.dumps(
            [
                {
                    "name": "试剂配伍禁忌",
                    "incompatible_pairs": [
                        {
                            "reagent1": "a",
                            "reagent2": "b",
                            "risk": "高",
                            "description": "desc",
                        }
                    ],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = ReagentDatabase.__new__(ReagentDatabase)
    monkeypatch.setattr(db, "_get_safety_file_path", lambda: safety_file)

    pairs = db.get_incompatible_pairs()
    assert pairs == [("a", "b", "高", "desc")]


def test_check_compatibility_matches_bidirectional(monkeypatch):
    from src.knowledge.reagent_db import ReagentDatabase

    db = ReagentDatabase.__new__(ReagentDatabase)
    monkeypatch.setattr(
        db,
        "get_incompatible_pairs",
        lambda: [("a", "b", "高", "desc")],
    )

    ok, msg = db.check_compatibility("a", "c")
    assert ok is True

    ok, msg = db.check_compatibility("a", "b")
    assert ok is False
    assert "风险等级" in msg

    ok, msg = db.check_compatibility("b", "a")
    assert ok is False


def test_reagent_db_load_and_search_paths(monkeypatch):
    from unittest.mock import Mock

    from src.knowledge.reagent_db import ReagentDatabase
    from src.models.knowledge import KnowledgeCard, KnowledgeType

    loader = Mock()
    loader.search_cards.return_value = []
    loader.load_cards_by_type.return_value = [
        KnowledgeCard(
            id="hcl",
            type=KnowledgeType.REAGENT,
            title="盐酸",
            content="x",
            cas="7647-01-0",
        )
    ]

    db = ReagentDatabase.__new__(ReagentDatabase)
    db.loader = loader
    db._reagents = {}
    db._load_reagents()

    assert db.get_reagent("hcl") is not None
    assert db.get_reagent_by_cas("7647-01-0") is not None
    assert db.get_reagent_by_cas("0000-00-0") is None

    _ = db.search_reagents("anything")
    loader.search_cards.assert_called_once()


def test_get_hazardous_reagents_sorting_and_reload(monkeypatch):
    from unittest.mock import Mock

    from src.knowledge.reagent_db import ReagentDatabase
    from src.models.knowledge import Hazard, HazardLevel, KnowledgeCard, KnowledgeType

    reagent_low = KnowledgeCard(
        id="low",
        type=KnowledgeType.REAGENT,
        title="low",
        content="x",
        hazards=[Hazard(type="t", level=HazardLevel.WARNING, hint="w")],
    )
    reagent_high = KnowledgeCard(
        id="high",
        type=KnowledgeType.REAGENT,
        title="high",
        content="x",
        hazards=[Hazard(type="t", level=HazardLevel.CRITICAL, hint="c")],
    )

    loader = Mock()
    loader.load_cards_by_type.return_value = [reagent_low, reagent_high]

    db = ReagentDatabase.__new__(ReagentDatabase)
    db.loader = loader
    db._reagents = {"old": reagent_low}

    db.reload()
    hazardous = db.get_hazardous_reagents(HazardLevel.WARNING)
    assert [r.id for r in hazardous] == ["high", "low"]


def test_reagent_db_schema_models_covered_via_reload():
    import importlib

    import src.knowledge.reagent_db as mod

    importlib.reload(mod)


def test_reagent_db_init_uses_default_trusted_dir(monkeypatch):
    from src.knowledge import reagent_db as mod
    from src.models.knowledge import KnowledgeType

    class DummyLoader:
        def __init__(self, knowledge_dir):
            self.knowledge_dir = knowledge_dir

        def load_cards_by_type(self, card_type):
            assert card_type == KnowledgeType.REAGENT
            return []

        def search_cards(self, query, card_type):
            return []

        def clear_cache(self):
            return None

    monkeypatch.setattr(mod, "KnowledgeLoader", DummyLoader)
    db = mod.ReagentDatabase(knowledge_dir=None)
    assert hasattr(db.loader, "knowledge_dir")
