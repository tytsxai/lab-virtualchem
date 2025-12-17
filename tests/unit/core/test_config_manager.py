"""ConfigManager 单元测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core import config_manager as cm


@pytest.fixture()
def isolated_config_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> cm.ConfigManager:
    """使用临时 home 目录创建独立的 ConfigManager 实例"""
    monkeypatch.setattr(cm.Path, "home", classmethod(lambda cls: tmp_path))
    cm.ConfigManager._instance = None
    manager = cm.ConfigManager()
    yield manager
    cm.ConfigManager._instance = None


def test_set_and_get_nested_value(isolated_config_manager: cm.ConfigManager) -> None:
    """应支持点路径设置/读取配置"""
    manager = isolated_config_manager
    manager.set("ui.font_size", 18)
    manager.set("app.language", "en_US")

    assert manager.get("ui.font_size") == 18
    assert manager.get("app.language") == "en_US"


def test_reset_to_default_restores_sections(
    isolated_config_manager: cm.ConfigManager,
) -> None:
    """reset_to_default 应恢复默认配置"""
    manager = isolated_config_manager
    manager.set("app.name", "CustomApp")
    manager.set("logging.level", "DEBUG")

    manager.reset_to_default()

    assert manager.get_app_config()["name"] == "VirtualChemLab"
    assert manager.get_logging_config()["level"] == "INFO"
