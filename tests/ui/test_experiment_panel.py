"""
实验面板UI测试
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

try:
    from src.ui.experiment_panel import ExperimentPanel

    HAS_EXPERIMENT_PANEL = True
except ImportError:
    HAS_EXPERIMENT_PANEL = False


@pytest.mark.skipif(not HAS_EXPERIMENT_PANEL, reason="ExperimentPanel not implemented")
class TestExperimentPanel:
    """实验面板测试类"""

    @pytest.fixture
    def panel(self, qtbot):
        """创建实验面板fixture"""
        panel = ExperimentPanel()
        qtbot.addWidget(panel)
        return panel

    def test_panel_creation(self, panel):
        """测试面板创建"""
        assert panel is not None

    def test_panel_has_start_button(self, panel):
        """测试是否有开始按钮"""
        # 查找开始按钮
        start_btn = panel.findChild(QPushButton, "startButton")
        assert start_btn is not None

    def test_start_experiment(self, panel, qtbot):
        """测试开始实验"""
        # 点击开始按钮
        start_btn = panel.findChild(QPushButton, "startButton")
        qtbot.mouseClick(start_btn, Qt.LeftButton)

        # 等待状态变化
        qtbot.wait(100)

        # 验证实验是否开始
        assert panel.is_running()
