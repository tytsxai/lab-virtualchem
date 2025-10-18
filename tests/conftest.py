"""
测试配置文件
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """Qt应用程序fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # 测试结束后不关闭应用程序，避免影响其他测试


@pytest.fixture
def temp_dir(tmp_path):
    """临时目录fixture"""
    return tmp_path


@pytest.fixture
def sample_config():
    """示例配置fixture"""
    return {
        "app": {"name": "TestApp", "version": "1.0.0", "language": "zh_CN", "theme": "dark"},
        "ui": {"font_size": 12, "font_family": "Arial", "animation_enabled": True},
        "game": {"physics_enabled": True, "gravity_strength": 0.5, "friction": 0.9},
    }


@pytest.fixture
def sample_experiment_template():
    """示例实验模板fixture"""
    return {
        "id": "test_experiment",
        "title": "测试实验",
        "description": "这是一个测试实验",
        "category": "general",
        "steps": [
            {"id": "step1", "text": "第一步：准备器材", "type": "preparation"},
            {"id": "step2", "text": "第二步：进行实验", "type": "experiment"},
        ],
    }
