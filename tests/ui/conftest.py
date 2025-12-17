"""
UI测试配置文件

提供pytest fixtures用于UI测试
"""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """创建QApplication实例

    整个测试会话只创建一次
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # 会话结束时清理
    # app.quit()
