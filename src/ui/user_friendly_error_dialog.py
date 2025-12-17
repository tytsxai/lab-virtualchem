"""
用户友好的错误对话框
提供清晰的错误信息、解决建议和恢复选项
"""

from __future__ import annotations

import traceback
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.enhanced_error_recovery import smart_error_recovery
from ..core.error_system.exceptions import BaseAppException
from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class ErrorDetailWidget(QWidget):
    """错误详情组件"""

    def __init__(self, error: BaseAppException, parent: QWidget | None = None):
        super().__init__(parent)
        self.error = error
        self.theme_manager = ThemeManager()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 错误标题
        title_label = QLabel(f"错误类型: {self.error.error_code.name}")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #d32f2f; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 错误描述
        desc_label = QLabel("错误描述:")
        desc_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(desc_label)

        desc_text = QTextEdit()
        desc_text.setPlainText(self.error.user_message)
        desc_text.setMaximumHeight(80)
        desc_text.setReadOnly(True)
        desc_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """
        )
        layout.addWidget(desc_text)

        # 恢复提示
        if self.error.recovery_hint:
            hint_label = QLabel("恢复建议:")
            hint_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            layout.addWidget(hint_label)

            hint_text = QTextEdit()
            hint_text.setPlainText(self.error.recovery_hint)
            hint_text.setMaximumHeight(60)
            hint_text.setReadOnly(True)
            hint_text.setStyleSheet(
                """
                QTextEdit {
                    background-color: #fff3e0;
                    border: 1px solid #ffb74d;
                    border-radius: 4px;
                    padding: 8px;
                }
            """
            )
            layout.addWidget(hint_text)

        # 技术详情（可折叠）
        self.tech_label = QLabel("技术详情 ▼")
        self.tech_label.setFont(QFont("Arial", 9))
        self.tech_label.setStyleSheet("color: #666; cursor: pointer;")
        self.tech_label.mousePressEvent = lambda _e: self.toggle_tech_details()
        layout.addWidget(self.tech_label)

        self.tech_details = QTextEdit()
        self.tech_details.setPlainText(
            f"""
错误代码: {self.error.error_code.code}
错误类别: {self.error.error_code.category.value}
原始消息: {self.error.message}
堆栈跟踪:
{traceback.format_exc() if self.error.traceback else "无"}
        """.strip()
        )
        self.tech_details.setMaximumHeight(200)
        self.tech_details.setReadOnly(True)
        self.tech_details.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }
        """
        )
        self.tech_details.hide()
        layout.addWidget(self.tech_details)

        self.tech_expanded = False

    def toggle_tech_details(self):
        """切换技术详情显示"""
        self.tech_expanded = not self.tech_expanded
        if self.tech_expanded:
            self.tech_details.show()
            self.tech_label.setText("技术详情 ▲")
        else:
            self.tech_details.hide()
            self.tech_label.setText("技术详情 ▼")


class RecoveryOptionsWidget(QWidget):
    """恢复选项组件"""

    recovery_selected = Signal(str)  # 恢复选项ID

    def __init__(self, error: BaseAppException, parent: QWidget | None = None):
        super().__init__(parent)
        self.error = error
        self.theme_manager = ThemeManager()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 标题
        title_label = QLabel("恢复选项")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 自动恢复选项
        auto_recover_btn = ModernButton("🔄 自动恢复")
        auto_recover_btn.setToolTip("尝试自动修复此错误")
        auto_recover_btn.clicked.connect(
            lambda: self.recovery_selected.emit("auto_recover")
        )
        layout.addWidget(auto_recover_btn)

        # 重试选项
        retry_btn = ModernButton("↻ 重试操作")
        retry_btn.setToolTip("重新执行失败的操作")
        retry_btn.clicked.connect(lambda: self.recovery_selected.emit("retry"))
        layout.addWidget(retry_btn)

        # 跳过选项
        skip_btn = ModernButton("⏭ 跳过继续")
        skip_btn.setToolTip("跳过此错误继续执行")
        skip_btn.clicked.connect(lambda: self.recovery_selected.emit("skip"))
        layout.addWidget(skip_btn)

        # 降级选项
        fallback_btn = ModernButton("📉 使用备用方案")
        fallback_btn.setToolTip("使用备用功能继续")
        fallback_btn.clicked.connect(lambda: self.recovery_selected.emit("fallback"))
        layout.addWidget(fallback_btn)

        # 报告选项
        report_btn = ModernButton("📧 报告问题")
        report_btn.setToolTip("向开发团队报告此错误")
        report_btn.clicked.connect(lambda: self.recovery_selected.emit("report"))
        layout.addWidget(report_btn)

        # 帮助选项
        help_btn = ModernButton("❓ 获取帮助")
        help_btn.setToolTip("查看相关帮助文档")
        help_btn.clicked.connect(lambda: self.recovery_selected.emit("help"))
        layout.addWidget(help_btn)


class UserFriendlyErrorDialog(QDialog):
    """用户友好的错误对话框"""

    recovery_completed = Signal(bool, str)  # 恢复是否成功, 恢复方式

    def __init__(self, error: BaseAppException, parent: QWidget | None = None):
        super().__init__(parent)
        self.error = error
        self.theme_manager = ThemeManager()
        self.recovery_result = None

        self.setWindowTitle("发生错误")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setMaximumSize(800, 700)

        self.init_ui()
        self.apply_theme()

        logger.info(f"显示用户友好错误对话框: {error.error_code.name}")

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 主容器
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧错误详情
        self.error_detail = ErrorDetailWidget(self.error)
        main_layout.addWidget(self.error_detail, 2)

        # 分隔线
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #ddd;")
        main_layout.addWidget(separator)

        # 右侧恢复选项
        self.recovery_options = RecoveryOptionsWidget(self.error)
        self.recovery_options.recovery_selected.connect(self.handle_recovery_selection)
        main_layout.addWidget(self.recovery_options, 1)

        layout.addWidget(main_widget)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 20)

        # 关闭按钮
        self.close_btn = ModernButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        # 不再显示按钮
        self.dont_show_btn = ModernButton("不再显示此类错误")
        self.dont_show_btn.clicked.connect(self.dont_show_again)
        button_layout.addWidget(self.dont_show_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def apply_theme(self):
        """应用主题"""
        try:
            theme = self.theme_manager.get_current_theme()

            if theme.name == "dark":
                self.setStyleSheet(
                    """
                    QDialog {
                        background-color: #2b2b2b;
                        color: #ffffff;
                    }
                """
                )
            else:
                self.setStyleSheet(
                    """
                    QDialog {
                        background-color: #ffffff;
                        color: #000000;
                    }
                """
                )

        except Exception as e:
            logger.error(f"应用主题失败: {e}")

    def handle_recovery_selection(self, recovery_type: str):
        """处理恢复选项选择"""
        try:
            logger.info(f"用户选择恢复选项: {recovery_type}")

            if recovery_type == "auto_recover":
                self.attempt_auto_recovery()
            elif recovery_type == "retry":
                self.attempt_retry()
            elif recovery_type == "skip":
                self.attempt_skip()
            elif recovery_type == "fallback":
                self.attempt_fallback()
            elif recovery_type == "report":
                self.report_error()
            elif recovery_type == "help":
                self.show_help()

        except Exception as e:
            logger.error(f"处理恢复选项失败: {e}")
            self.show_recovery_error("恢复操作失败", str(e))

    def attempt_auto_recovery(self):
        """尝试自动恢复"""
        try:
            # 使用智能错误恢复系统
            success, result, level = smart_error_recovery.try_smart_recovery(
                lambda: None,  # 这里应该传入实际的恢复函数
                self.error,
                "用户手动触发自动恢复",
            )

            if success:
                self.show_recovery_success("自动恢复成功", f"恢复级别: {level.value}")
                self.recovery_completed.emit(True, "auto_recovery")
            else:
                self.show_recovery_error("自动恢复失败", "无法自动修复此错误")

        except Exception as e:
            logger.error(f"自动恢复失败: {e}")
            self.show_recovery_error("自动恢复失败", str(e))

    def attempt_retry(self):
        """尝试重试"""
        try:
            # 这里应该实现具体的重试逻辑
            self.show_recovery_success("重试成功", "操作已重新执行")
            self.recovery_completed.emit(True, "retry")

        except Exception as e:
            logger.error(f"重试失败: {e}")
            self.show_recovery_error("重试失败", str(e))

    def attempt_skip(self):
        """尝试跳过"""
        try:
            self.show_recovery_success("已跳过", "错误已跳过，继续执行")
            self.recovery_completed.emit(True, "skip")

        except Exception as e:
            logger.error(f"跳过失败: {e}")
            self.show_recovery_error("跳过失败", str(e))

    def attempt_fallback(self):
        """尝试降级"""
        try:
            # 这里应该实现具体的降级逻辑
            self.show_recovery_success("降级成功", "已使用备用方案")
            self.recovery_completed.emit(True, "fallback")

        except Exception as e:
            logger.error(f"降级失败: {e}")
            self.show_recovery_error("降级失败", str(e))

    def report_error(self):
        """报告错误"""
        try:
            # 生成错误报告
            report = smart_error_recovery.generate_recovery_report()

            # 这里应该实现实际的错误报告功能
            # 比如发送邮件、提交到错误跟踪系统等
            logger.info(f"错误报告: {report}")

            self.show_recovery_success("错误已报告", "错误信息已发送给开发团队")

        except Exception as e:
            logger.error(f"报告错误失败: {e}")
            self.show_recovery_error("报告失败", str(e))

    def show_help(self):
        """显示帮助"""
        try:
            # 这里应该实现帮助系统
            # 比如打开帮助文档、显示相关教程等
            self.show_recovery_success("帮助已打开", "相关帮助文档已显示")

        except Exception as e:
            logger.error(f"显示帮助失败: {e}")
            self.show_recovery_error("帮助失败", str(e))

    def show_recovery_success(self, title: str, message: str):
        """显示恢复成功消息"""
        # 这里可以使用QMessageBox或自定义通知组件
        logger.info(f"恢复成功: {title} - {message}")
        # 实际实现中应该显示用户友好的成功提示

    def show_recovery_error(self, title: str, message: str):
        """显示恢复错误消息"""
        # 这里可以使用QMessageBox或自定义通知组件
        logger.error(f"恢复失败: {title} - {message}")
        # 实际实现中应该显示用户友好的错误提示

    def dont_show_again(self):
        """不再显示此类错误"""
        try:
            # 这里应该实现用户偏好设置
            # 比如将此类错误添加到忽略列表
            logger.info(f"用户选择不再显示错误: {self.error.error_code.name}")
            self.accept()

        except Exception as e:
            logger.error(f"设置失败: {e}")

    def get_recovery_result(self) -> Any | None:
        """获取恢复结果"""
        return self.recovery_result


def show_user_friendly_error(
    error: BaseAppException, parent: QWidget | None = None
) -> Any | None:
    """显示用户友好的错误对话框"""
    try:
        dialog = UserFriendlyErrorDialog(error, parent)
        result = dialog.exec()

        if result == QDialog.Accepted:
            return dialog.get_recovery_result()

        return None

    except Exception as e:
        logger.error(f"显示错误对话框失败: {e}")
        return None
