"""
开发者控制台
提供调试、监控和开发工具的界面
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConsoleOutputWidget(QTextEdit):
    """控制台输出组件"""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)  # 限制行数

        # 设置字体
        font = self.font()
        font.setFamily("Consolas")
        font.setPointSize(10)
        self.setFont(font)

    def append_message(self, message: str, level: str = "info") -> None:
        """添加消息"""
        if level == "error":
            color = "red"
        elif level == "warning":
            color = "orange"
        elif level == "debug":
            color = "gray"
        else:
            color = "black"

        formatted_message = f'<span style="color: {color};">{message}</span><br>'
        self.append(formatted_message)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class SystemInfoWidget(QWidget):
    """系统信息组件"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 这里可以添加系统信息显示
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("系统信息面板\n(待实现)")

        layout.addWidget(info_text)


class PerformanceMonitorWidget(QWidget):
    """性能监控组件"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 这里可以添加性能监控显示
        monitor_text = QTextEdit()
        monitor_text.setReadOnly(True)
        monitor_text.setPlainText("性能监控面板\n(待实现)")

        layout.addWidget(monitor_text)


class DeveloperConsole(QDialog):
    """开发者控制台"""

    closed = Signal()

    def __init__(self, dev_auth=None, parent=None):
        super().__init__(parent)
        self.dev_auth = dev_auth
        self._setup_ui()
        logger.info("开发者控制台已打开")

    def _setup_ui(self):
        """设置界面"""
        self.setWindowTitle("开发者控制台")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowFlags(Qt.WindowType.Window)

        layout = QVBoxLayout(self)

        # 标签页
        tab_widget = QTabWidget()

        # 控制台输出
        console_tab = QWidget()
        console_layout = QVBoxLayout(console_tab)
        self.console_output = ConsoleOutputWidget()
        console_layout.addWidget(self.console_output)

        tab_widget.addTab(console_tab, "控制台")

        # 系统信息
        system_tab = SystemInfoWidget()
        tab_widget.addTab(system_tab, "系统信息")

        # 性能监控
        performance_tab = PerformanceMonitorWidget()
        tab_widget.addTab(performance_tab, "性能监控")

        layout.addWidget(tab_widget)

        self.setLayout(layout)

    def append_console_message(self, message: str, level: str = "info") -> None:
        """添加控制台消息"""
        self.console_output.append_message(message, level)

    def closeEvent(self, event):
        """关闭事件"""
        self.closed.emit()
        super().closeEvent(event)
        logger.info("开发者控制台已关闭")
