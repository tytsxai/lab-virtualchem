from __future__ import annotations

from pathlib import Path

from src.ai.experiment_compiler import compile_experiment


def _basic_yaml() -> str:
    return """
title: 测试实验
steps:
  - text: 步骤1
    check:
      type: confirm
"""


def test_compile_experiment_with_yaml_string():
    """compile_experiment 应能直接处理 YAML 字符串内容。"""
    result = compile_experiment(_basic_yaml(), format_type="yaml")
    assert result.success
    assert result.template is not None
    assert result.template.title == "测试实验"
    assert len(result.template.steps) == 1


def test_compile_experiment_with_yaml_file(tmp_path: Path):
    """当传入文件路径且显式声明为 yaml 时，应读取文件内容。"""
    project_root = Path(__file__).resolve().parents[2]
    allowed_dir = project_root / "data" / "_pytest"
    allowed_dir.mkdir(parents=True, exist_ok=True)

    yaml_file = allowed_dir / f"sample_{tmp_path.name}.yaml"
    yaml_file.write_text(_basic_yaml(), encoding="utf-8")

    try:
        result = compile_experiment(yaml_file.relative_to(project_root), format_type="yaml")
        assert result.success
        assert result.template is not None
        assert result.template.steps[0].text == "步骤1"
    finally:
        yaml_file.unlink(missing_ok=True)
