from __future__ import annotations

import json

from src.ai import experiment_compiler as ec
from src.ai.experiment_compiler import ExperimentCompiler, save_compiled_template


class DummyAssistant:
    def __init__(self, response: str):
        self._response = response

    def ask(self, _prompt: str) -> str:
        return self._response


def test_compile_from_json_rejects_oversized_payload():
    oversized = json.dumps({"a": "x" * (ec.MAX_INPUT_JSON_CHARS + 1)}, ensure_ascii=False)
    compiler = ExperimentCompiler()
    result = compiler.compile_from_json(oversized)
    assert not result.success
    assert any("JSON内容过大" in e for e in result.errors)


def test_parse_with_ai_validates_schema_and_fails_cleanly():
    assistant = DummyAssistant('{"title":"t"}')
    compiler = ExperimentCompiler(ai_assistant=assistant)
    result = compiler.compile_from_text("whatever")
    assert not result.success
    assert any("AI无法解析实验内容" in e for e in result.errors)


def test_parse_with_ai_rejects_oversized_ai_json():
    huge_json = "{" + '"title":"' + ("x" * (ec.MAX_AI_JSON_CHARS + 1)) + '"}'
    assistant = DummyAssistant(huge_json)
    compiler = ExperimentCompiler(ai_assistant=assistant)
    result = compiler.compile_from_text("whatever")
    assert not result.success
    assert any("AI无法解析实验内容" in e for e in result.errors)


def test_save_compiled_template_uses_safe_dump(tmp_path):
    compiler = ExperimentCompiler()
    result = compiler.compile_from_dict(
        {
            "title": "测试实验",
            "steps": [{"text": "步骤1", "check": {"type": "confirm"}}],
        }
    )
    assert result.success
    out = tmp_path / "out.yaml"
    assert save_compiled_template(result, out, format_type="yaml")
    text = out.read_text(encoding="utf-8")
    assert "!!python" not in text
    assert "experiment:" in text

