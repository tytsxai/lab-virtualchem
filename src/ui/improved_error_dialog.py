"""
改进的错误对话框
提供更友好的错误提示和解决方案
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImprovedErrorDialog(QDialog):
    """改进的错误对话框"""

    copy_details_clicked = Signal()
    report_clicked = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        suggestions: list[str] | None = None,
        error_type: str = "error",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.error_details = details
        self.suggestions = suggestions or []
        self.error_type = error_type

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)

        self.init_ui(message)

    def init_ui(self, message: str):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 顶部图标和消息区域
        header_layout = QHBoxLayout()

        # 错误图标
        icon_label = QLabel()
        icon_map = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        icon_label.setText(icon_map.get(self.error_type, "❌"))
        icon_label.setStyleSheet("font-size: 36px;")
        header_layout.addWidget(icon_label)

        # 主要消息
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_font = QFont()
        message_font.setPointSize(11)
        message_label.setFont(message_font)
        header_layout.addWidget(message_label, 1)

        layout.addLayout(header_layout)

        # 建议区域
        if self.suggestions:
            layout.addSpacing(10)

            suggestions_label = QLabel("💡 建议的解决方案:")
            suggestions_label.setStyleSheet("font-weight: bold; color: #2196F3;")
            layout.addWidget(suggestions_label)

            for i, suggestion in enumerate(self.suggestions, 1):
                suggestion_label = QLabel(f"{i}. {suggestion}")
                suggestion_label.setWordWrap(True)
                suggestion_label.setStyleSheet("margin-left: 20px; color: #555;")
                layout.addWidget(suggestion_label)

        # 详细信息区域（可折叠）
        if self.error_details:
            layout.addSpacing(10)

            self.details_button = QPushButton("显示详细信息 ▼")
            self.details_button.setFlat(True)
            self.details_button.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    border: none;
                    background: transparent;
                    color: #2196F3;
                }
                QPushButton:hover {
                    background: #f0f0f0;
                }
            """
            )
            self.details_button.clicked.connect(self.toggle_details)
            layout.addWidget(self.details_button)

            self.details_text = QTextEdit()
            self.details_text.setPlainText(self.error_details)
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(150)
            self.details_text.setVisible(False)
            self.details_text.setStyleSheet(
                """
                QTextEdit {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 9pt;
                }
            """
            )
            layout.addWidget(self.details_text)

        # 底部按钮
        button_layout = QHBoxLayout()

        # 复制详情按钮
        if self.error_details:
            self.copy_btn = QPushButton("📋 复制详情")
            self.copy_btn.clicked.connect(self.copy_details)
            button_layout.addWidget(self.copy_btn)

        # 报告问题按钮
        self.report_btn = QPushButton("🐛 报告问题")
        self.report_btn.clicked.connect(self.report_error)
        button_layout.addWidget(self.report_btn)

        button_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("确定")
        self.close_btn.setDefault(True)
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """
        )
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 设置对话框样式
        self.setStyleSheet(
            """
            QDialog {
                background-color: white;
            }
        """
        )

    def toggle_details(self):
        """切换详细信息显示"""
        is_visible = self.details_text.isVisible()
        self.details_text.setVisible(not is_visible)

        if is_visible:
            self.details_button.setText("显示详细信息 ▼")
            self.adjustSize()
        else:
            self.details_button.setText("隐藏详细信息 ▲")
            self.setMinimumHeight(self.sizeHint().height() + 150)

    def copy_details(self):
        """复制详情到剪贴板"""
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_details)

        # 临时更改按钮文本
        original_text = self.copy_btn.text()
        self.copy_btn.setText("✅ 已复制")
        self.copy_btn.setEnabled(False)

        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            2000,
            lambda: (
                self.copy_btn.setText(original_text),
                self.copy_btn.setEnabled(True),
            ),
        )

        self.copy_details_clicked.emit()

    def report_error(self):
        """报告错误"""
        self.report_clicked.emit()


def show_error(
    title: str = "错误",
    message: str = "发生了一个错误",
    details: str = "",
    suggestions: list[str] | None = None,
    parent: QWidget | None = None,
) -> int:
    """显示错误对话框

    Args:
        title: 标题
        message: 主要消息
        details: 详细信息
        suggestions: 建议列表
        parent: 父控件

    Returns:
        对话框结果
    """
    dialog = ImprovedErrorDialog(title, message, details, suggestions, "error", parent)
    return dialog.exec()


def show_warning(
    title: str = "警告",
    message: str = "请注意",
    details: str = "",
    suggestions: list[str] | None = None,
    parent: QWidget | None = None,
) -> int:
    """显示警告对话框

    Args:
        title: 标题
        message: 主要消息
        details: 详细信息
        suggestions: 建议列表
        parent: 父控件

    Returns:
        对话框结果
    """
    dialog = ImprovedErrorDialog(
        title, message, details, suggestions, "warning", parent
    )
    return dialog.exec()


def show_info(
    title: str = "提示",
    message: str = "信息",
    details: str = "",
    suggestions: list[str] | None = None,
    parent: QWidget | None = None,
) -> int:
    """显示信息对话框

    Args:
        title: 标题
        message: 主要消息
        details: 详细信息
        suggestions: 建议列表
        parent: 父控件

    Returns:
        对话框结果
    """
    dialog = ImprovedErrorDialog(title, message, details, suggestions, "info", parent)
    return dialog.exec()
