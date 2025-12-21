from pathlib import Path

import pytest


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_card_rejects_path_traversal(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    loader = KnowledgeLoader()

    outside = tmp_path / "outside.yaml"
    _write_yaml(
        outside,
        """
id: outside
type: reagent
title: outside
content: hi
""".lstrip(),
    )

    assert loader.load_card(outside) is None


@pytest.mark.skipif(
    not hasattr(Path, "symlink_to"), reason="platform does not support symlinks"
)
def test_load_card_rejects_symlink(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    type_dir = trusted_dir / KnowledgeType.REAGENT.value
    outside = tmp_path / "outside.yaml"
    _write_yaml(
        outside,
        """
id: outside
type: reagent
title: outside
content: hi
""".lstrip(),
    )

    symlink_path = type_dir / "link.yaml"
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(outside)

    loader = KnowledgeLoader()
    assert loader.load_card(symlink_path) is None


def test_load_card_rejects_oversized_file(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)
    monkeypatch.setattr(loader_module, "MAX_KNOWLEDGE_FILE_BYTES", 64)

    type_dir = trusted_dir / KnowledgeType.REAGENT.value
    big_file = type_dir / "big.yaml"
    big_payload = (
        "id: big\n"
        "type: reagent\n"
        "title: big\n"
        "content: |\n"
        "  " + ("x" * 200) + "\n"
    )
    _write_yaml(big_file, big_payload)

    loader = KnowledgeLoader()
    assert loader.load_card(big_file) is None


def test_load_cards_by_type_works_for_valid_file(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    type_dir = trusted_dir / KnowledgeType.REAGENT.value
    card_file = type_dir / "water.yaml"
    _write_yaml(
        card_file,
        """
id: water
type: reagent
title: 水
content: 纯水
tags: [safe]
""".lstrip(),
    )

    loader = KnowledgeLoader()
    cards = loader.load_cards_by_type(KnowledgeType.REAGENT)

    assert len(cards) == 1
    assert cards[0].id == "water"


def test_get_card_by_id_and_search_cards(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    reagent_dir = trusted_dir / KnowledgeType.REAGENT.value
    _write_yaml(
        reagent_dir / "hcl.yaml",
        """
id: hcl
type: reagent
title: 盐酸
content: 强酸
tags: [acid]
""".lstrip(),
    )
    _write_yaml(
        reagent_dir / "naoh.yaml",
        """
id: naoh
type: reagent
title: 氢氧化钠
content: 强碱
tags: [base]
""".lstrip(),
    )

    loader = KnowledgeLoader()
    assert loader.get_card_by_id("hcl") is not None
    assert loader.get_card_by_id("missing") is None

    results = loader.search_cards("强", KnowledgeType.REAGENT)
    assert {c.id for c in results} == {"hcl", "naoh"}

    loader.clear_cache()
    assert loader.get_card_by_id("hcl") is not None


def test_loader_ignores_external_knowledge_dir_and_handles_missing_type_dir(
    tmp_path, monkeypatch
):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    loader = KnowledgeLoader(Path("/untrusted/path"))
    cards = loader.load_cards_by_type(KnowledgeType.PROCEDURE)
    assert cards == []


def test_loader_handles_empty_and_invalid_yaml(tmp_path, monkeypatch):
    from src.knowledge import loader as loader_module
    from src.knowledge.loader import KnowledgeLoader
    from src.models.knowledge import KnowledgeType

    trusted_dir = tmp_path / "trusted_knowledge"
    monkeypatch.setattr(loader_module, "TRUSTED_KNOWLEDGE_DIR", trusted_dir)

    type_dir = trusted_dir / KnowledgeType.REAGENT.value
    empty_file = type_dir / "empty.yaml"
    _write_yaml(empty_file, "")

    invalid_file = type_dir / "bad.yaml"
    _write_yaml(invalid_file, "id: x\n: bad\n")

    loader = KnowledgeLoader()
    assert loader.load_card(empty_file) is None
    assert loader.load_card(invalid_file) is None
