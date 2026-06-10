from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_knowledge_parser_module():
    root = Path(__file__).resolve().parents[2]
    module_path = (
        root
        / "tools"
        / "chemlab_integration"
        / "src"
        / "parsers"
        / "knowledge_parser.py"
    )
    spec = importlib.util.spec_from_file_location(
        "chemlab_knowledge_parser", module_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


knowledge_parser = _load_knowledge_parser_module()


def test_parse_python_data_uses_static_literals_only(tmp_path):
    marker = tmp_path / "executed.txt"
    source = tmp_path / "molecules.py"
    source.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')",
                "WATER = {'name': 'Water', 'formula': 'H2O'}",
                "REAGENTS = [{'name': 'Ethanol', 'formula': 'C2H6O'}]",
                "DYNAMIC = {'value': Path('x')}",
            ]
        ),
        encoding="utf-8",
    )

    parser = knowledge_parser.KnowledgeParser()
    items = parser.parse_file(source)

    assert marker.exists() is False
    assert {"id": "WATER", "name": "Water", "formula": "H2O"} in items
    assert {"id": "REAGENTS_0", "name": "Ethanol", "formula": "C2H6O"} in items
    assert all(item["id"] != "DYNAMIC" for item in items)


def test_parse_python_data_accepts_annotated_literal_assignments(tmp_path):
    source = tmp_path / "apparatus.py"
    source.write_text(
        "APPARATUS: dict = {'name': 'Beaker', 'apparatus': True}\n",
        encoding="utf-8",
    )

    parser = knowledge_parser.KnowledgeParser()

    assert parser.parse_file(source) == [
        {"id": "APPARATUS", "name": "Beaker", "apparatus": True}
    ]
