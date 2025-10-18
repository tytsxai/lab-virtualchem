"""
带实时验证的输入控件
提供即时的视觉反馈和错误提示
"""

from __future__ import annotations

import re
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)


class ValidatedLineEdit(QLineEdit):
    """带实时验证的单行输入框"""

    validation_changed = Signal(bool)  # 验证状态改变

    def __init__(
        self,
        parent: QWidget | None = None,
        validator: Callable[[str], tuple[bool, str]] | None = None,
        placeholder: str = "",
        required: bool = False,
    ):
        super().__init__(parent)
        self.validator_func = validator
        self.required = required
        self._is_valid = False
        self._error_message = ""

        # 设置占位符
        if placeholder:
            self.setPlaceholderText(placeholder)

        # 样式
        self.update_style()

        # 连接信号 - 延迟验证以提高性能
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate)
        self.textChanged.connect(lambda: self.validation_timer.start(300))

    def validate(self) -> bool:
        """验证输入"""
        text = self.text().strip()

        # 检查必填
        if self.required and not text:
            self._is_valid = False
            self._error_message = "此字段为必填项"
            self.update_style()
            self.validation_changed.emit(False)
            return False

        # 如果为空且非必填，则有效
        if not text and not self.required:
            self._is_valid = True
            self._error_message = ""
            self.update_style()
            self.validation_changed.emit(True)
            return True

        # 自定义验证
        if self.validator_func:
            is_valid, error_msg = self.validator_func(text)
            self._is_valid = is_valid
            self._error_message = error_msg
        else:
            self._is_valid = True
            self._error_message = ""

        self.update_style()
        self.validation_changed.emit(self._is_valid)
        return self._is_valid

    def update_style(self):
        """更新样式以反映验证状态"""
        if not self.text() and not self.required:
            # 默认状态
            self.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #d1d8e0;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 11pt;
                    background-color: white;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                }
            """)
            self.setToolTip("")
        elif self._is_valid:
            # 有效状态
            self.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #2ecc71;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 11pt;
                    background-color: #e8f8f5;
                }
                QLineEdit:focus {
                    border-color: #27ae60;
                }
            """)
            self.setToolTip("✓ 输入有效")
        else:
            # 无效状态
            self.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #e74c3c;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 11pt;
                    background-color: #fadbd8;
                }
                QLineEdit:focus {
                    border-color: #c0392b;
                }
            """)
            self.setToolTip(f"✗ {self._error_message}")

    def is_valid(self) -> bool:
        """检查是否有效"""
        return self._is_valid

    def get_error_message(self) -> str:
        """获取错误消息"""
        return self._error_message


class ValidatedNumberInput(QDoubleSpinBox):
    """带验证的数字输入框"""

    validation_changed = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        decimals: int = 2,
        unit: str = "",
    ):
        super().__init__(parent)

        # 设置范围
        if min_value is not None:
            self.setMinimum(min_value)
        if max_value is not None:
            self.setMaximum(max_value)

        self.setDecimals(decimals)

        # 设置后缀（单位）
        if unit:
            self.setSuffix(f" {unit}")

        # 样式
        self.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #d1d8e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
                background-color: white;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 20px;
                border-radius: 3px;
            }
        """)

        # 连接信号
        self.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self, value: float):
        """值改变时"""
        is_valid = self.minimum() <= value <= self.maximum()
        self.validation_changed.emit(is_valid)


class ValidatedComboBox(QComboBox):
    """带验证的下拉框"""

    validation_changed = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        required: bool = True,
        placeholder: str = "请选择...",
    ):
        super().__init__(parent)
        self.required = required
        self._is_valid = not required

        # 添加占位符项
        if placeholder:
            self.addItem(placeholder)
            self.setCurrentIndex(0)

        # 样式
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #d1d8e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)

        # 连接信号
        self.currentIndexChanged.connect(self.validate)

    def validate(self):
        """验证选择"""
        # 如果选择了第一项（占位符），则无效
        if self.required:
            self._is_valid = self.currentIndex() > 0
        else:
            self._is_valid = True

        self.validation_changed.emit(self._is_valid)

        # 更新样式
        if self._is_valid or not self.required:
            self.setStyleSheet("""
                QComboBox {
                    border: 2px solid #2ecc71;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 11pt;
                    background-color: #e8f8f5;
                }
            """)
        else:
            self.setStyleSheet("""
                QComboBox {
                    border: 2px solid #e74c3c;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 11pt;
                    background-color: #fadbd8;
                }
            """)

    def is_valid(self) -> bool:
        """检查是否有效"""
        return self._is_valid


class InputWithLabel(QWidget):
    """带标签的输入控件组合"""

    def __init__(
        self,
        label: str,
        input_widget: QWidget,
        required: bool = False,
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.input_widget = input_widget

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 标签
        label_widget = QLabel(label + ("*" if required else ""))
        label_widget.setStyleSheet("""
            QLabel {
                font-size: 11pt;
                font-weight: 500;
                color: #2c3e50;
            }
        """)
        label_widget.setMinimumWidth(120)
        layout.addWidget(label_widget)

        # 输入控件
        layout.addWidget(input_widget, 1)

        # 帮助图标（如果有帮助文本）
        if help_text:
            help_label = QLabel("ⓘ")
            help_label.setStyleSheet("""
                QLabel {
                    color: #3498db;
                    font-size: 14pt;
                    font-weight: bold;
                }
            """)
            help_label.setToolTip(help_text)
            help_label.setCursor(Qt.CursorShape.WhatsThisCursor)
            layout.addWidget(help_label)

    def get_value(self):
        """获取输入值"""
        if isinstance(self.input_widget, (QLineEdit, ValidatedLineEdit)):
            return self.input_widget.text()
        elif isinstance(self.input_widget, (QSpinBox, QDoubleSpinBox, ValidatedNumberInput)):
            return self.input_widget.value()
        elif isinstance(self.input_widget, (QComboBox, ValidatedComboBox)):
            return self.input_widget.currentText()
        return None

    def is_valid(self) -> bool:
        """检查是否有效"""
        if hasattr(self.input_widget, 'is_valid'):
            return self.input_widget.is_valid()
        elif hasattr(self.input_widget, 'validate'):
            return self.input_widget.validate()
        return True


# 常用验证器
class Validators:
    """预定义的验证器"""

    @staticmethod
    def email(text: str) -> tuple[bool, str]:
        """邮箱验证"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, text):
            return True, ""
        return False, "请输入有效的邮箱地址"

    @staticmethod
    def phone(text: str) -> tuple[bool, str]:
        """手机号验证"""
        pattern = r'^1[3-9]\d{9}$'
        if re.match(pattern, text):
            return True, ""
        return False, "请输入有效的手机号码"

    @staticmethod
    def number(min_val: float | None = None, max_val: float | None = None):
        """数字范围验证"""
        def validator(text: str) -> tuple[bool, str]:
            try:
                value = float(text)
                if min_val is not None and value < min_val:
                    return False, f"数值不能小于 {min_val}"
                if max_val is not None and value > max_val:
                    return False, f"数值不能大于 {max_val}"
                return True, ""
            except ValueError:
                return False, "请输入有效的数字"
        return validator

    @staticmethod
    def min_length(length: int):
        """最小长度验证"""
        def validator(text: str) -> tuple[bool, str]:
            if len(text) >= length:
                return True, ""
            return False, f"长度不能少于 {length} 个字符"
        return validator

    @staticmethod
    def max_length(length: int):
        """最大长度验证"""
        def validator(text: str) -> tuple[bool, str]:
            if len(text) <= length:
                return True, ""
            return False, f"长度不能超过 {length} 个字符"
        return validator

    @staticmethod
    def pattern(regex: str, error_msg: str = "格式不正确"):
        """正则表达式验证"""
        def validator(text: str) -> tuple[bool, str]:
            if re.match(regex, text):
                return True, ""
            return False, error_msg
        return validator

