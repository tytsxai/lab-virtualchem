"""
主窗口UI测试
"""

import pytest

from src.ui.main_window import MainWindow


class TestMainWindow:
    """主窗口测试类"""

    @pytest.fixture
    def main_window(self, qtbot):
        """创建主窗口fixture"""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_window_creation(self, main_window):
        """测试窗口创建"""
        assert main_window is not None
        assert main_window.windowTitle() != ""

    def test_window_shows(self, main_window, qtbot):
        """测试窗口显示"""
        main_window.show()
        assert main_window.isVisible()

    def test_window_has_menu_bar(self, main_window):
        """测试菜单栏存在"""
        menu_bar = main_window.menuBar()
        assert menu_bar is not None

    def test_window_has_status_bar(self, main_window):
        """测试状态栏存在"""
        status_bar = main_window.statusBar()
        assert status_bar is not None

    def test_window_default_size(self, main_window):
        """测试默认窗口大小"""
        size = main_window.size()
        # 窗口应该有合理的初始大小
        assert size.width() >= 800
        assert size.height() >= 600

    def test_window_close(self, main_window, qtbot):
        """测试窗口关闭"""
        main_window.show()
        qtbot.waitExposed(main_window)

        # 模拟关闭事件
        main_window.close()
        assert not main_window.isVisible()
