from __future__ import annotations

from pathlib import Path

import pytest

from src.ai.experiment_compiler import ExperimentCompiler, compile_experiment


def _allowed_dir() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    allowed = project_root / "data" / "_pytest"
    allowed.mkdir(parents=True, exist_ok=True)
    return allowed


def test_compile_from_text_requires_ai_assistant():
    compiler = ExperimentCompiler(ai_assistant=None)
    result = compiler.compile_from_text("随便写点内容")
    assert result.success is False
    assert any("需要AI助手" in e for e in result.errors)
    assert any("启用AI助手" in s for s in result.suggestions)


def test_compile_from_yaml_empty_payload():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_yaml("")
    assert result.success is False
    assert any("YAML内容为空" in e for e in result.errors)


def test_compile_from_json_null_payload():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_json("null")
    assert result.success is False
    assert any("JSON内容为空" in e for e in result.errors)


def test_compile_from_json_decode_error():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_json("{")
    assert result.success is False
    assert any("JSON解析错误" in e for e in result.errors)


def test_compile_from_dict_missing_title():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_dict({"steps": [{"text": "步骤1", "check": {"type": "confirm"}}]})
    assert result.success is False
    assert any("缺少实验标题" in e for e in result.errors)


def test_compile_from_dict_step_normalize_failure_is_reported():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_dict(
        {
            "title": "t",
            "steps": [{"text": "步骤1", "check": {"type": "not-a-valid-type"}}],
        }
    )
    assert result.success is False
    assert any("标准化失败" in e for e in result.errors)


def test_compile_from_file_nonexistent_in_whitelist():
    compiler = ExperimentCompiler()
    result = compiler.compile_from_file("data/_pytest/does_not_exist.yaml")
    assert result.success is False
    assert any("文件不存在" in e for e in result.errors)


def test_compile_from_file_unsupported_suffix(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[2]
    allowed = _allowed_dir()
    file_path = allowed / f"sample_{tmp_path.name}.bin"
    file_path.write_text("hello", encoding="utf-8")
    try:
        compiler = ExperimentCompiler()
        result = compiler.compile_from_file(file_path.relative_to(project_root))
        assert result.success is False
        assert any("不支持的文件类型" in e for e in result.errors)
    finally:
        file_path.unlink(missing_ok=True)


def test_compile_experiment_auto_detects_yaml_string():
    result = compile_experiment(
        """
title: 自动探测
steps:
  - text: 步骤1
    check:
      type: confirm
""".strip(),
        format_type="auto",
    )
    assert result.success is True
    assert result.template is not None
    assert result.template.title == "自动探测"


def test_parse_with_ai_accepts_json_code_fence(monkeypatch):
    class DummyAssistant:
        def ask(self, _prompt: str) -> str:
            return (
                "```json\n"
                '{ "title": "t", "steps": [{"id":"s1","text":"步骤1","check":{"type":"confirm","fail_hint":"ok"},"hints":[]}], "reagents": [], "score_rules": [] }\n'
                "```"
            )

    compiler = ExperimentCompiler(ai_assistant=DummyAssistant())
    result = compiler.compile_from_text("whatever")
    assert result.success is True
