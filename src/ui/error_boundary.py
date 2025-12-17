"""
错误边界组件
提供前端错误捕获和优雅降级
"""

import logging
import traceback
from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ErrorBoundary(QWidget):
    """错误边界组件 - 捕获子组件错误"""

    error_occurred = Signal(Exception, str)  # 错误对象, 堆栈信息

    def __init__(
        self,
        child_widget: QWidget | None = None,
        fallback_widget: QWidget | None = None,
        on_error: Callable | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.child_widget = child_widget
        self.fallback_widget = fallback_widget
        self.on_error_callback = on_error
        self.has_error = False
        self.error_info = ""

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if self.child_widget:
            self.layout.addWidget(self.child_widget)

    def set_child(self, widget: QWidget):
        """设置子组件"""
        # 清除旧组件
        if self.child_widget:
            self.layout.removeWidget(self.child_widget)
            self.child_widget.deleteLater()

        self.child_widget = widget
        self.has_error = False

        if widget:
            self.layout.addWidget(widget)

    def catch_error(self, error: Exception, context: str = ""):
        """捕获错误"""
        self.has_error = True
        error_msg = str(error)
        stack_trace = traceback.format_exc()

        self.error_info = (
            f"错误: {error_msg}\n\n上下文: {context}\n\n堆栈:\n{stack_trace}"
        )

        logger.error(f"错误边界捕获错误 [{context}]: {error_msg}\n{stack_trace}")

        # 触发回调
        if self.on_error_callback:
            try:
                self.on_error_callback(error, self.error_info)
            except Exception as e:
                logger.error(f"错误回调失败: {e}")

        # 发送信号
        self.error_occurred.emit(error, stack_trace)

        # 显示降级UI
        self._show_fallback()

    def _show_fallback(self):
        """显示降级UI"""
        # 移除子组件
        if self.child_widget:
            self.layout.removeWidget(self.child_widget)
            self.child_widget.hide()

        # 使用自定义降级组件或默认错误UI
        if self.fallback_widget:
            self.layout.addWidget(self.fallback_widget)
        else:
            self._show_error_ui()

    def _show_error_ui(self):
        """显示默认错误UI"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)

        # 错误图标
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(icon_label)

        # 错误消息
        error_label = QLabel("组件加载失败")
        error_label.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            color: #D83B01;
            margin: 10px;
        """
        )
        error_label.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(error_label)

        # 友好提示
        hint_label = QLabel("💡 您可以尝试重试或联系技术支持")
        hint_label.setStyleSheet("color: #605E5C; margin: 5px;")
        hint_label.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(hint_label)

        # 详细信息（可展开）
        details_text = QTextEdit()
        details_text.setPlainText(self.error_info)
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(200)
        details_text.setStyleSheet(
            """
            background-color: #FFF3E0;
            border: 1px solid #FFB900;
            border-radius: 4px;
            padding: 8px;
            font-family: 'Courier New', monospace;
            font-size: 10px;
        """
        )
        error_layout.addWidget(details_text)

        # 按钮组
        button_layout = QHBoxLayout()

        # 重试按钮
        retry_btn = QPushButton("🔄 重试")
        retry_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """
        )
        retry_btn.clicked.connect(self.retry)
        button_layout.addWidget(retry_btn)

        # 复制错误信息按钮
        copy_btn = QPushButton("📋 复制错误")
        copy_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4A4FB0;
            }
        """
        )
        copy_btn.clicked.connect(self._copy_error_info)
        button_layout.addWidget(copy_btn)

        error_layout.addLayout(button_layout)

        self.layout.addWidget(error_widget)

    def _copy_error_info(self):
        """复制错误信息到剪贴板"""
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_info)
        logger.info("错误信息已复制到剪贴板")

    def retry(self):
        """重试加载"""
        logger.info("用户请求重试加载组件")

        # 清除错误状态
        self.has_error = False
        self.error_info = ""

        # 清除当前UI
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新显示子组件
        if self.child_widget:
            self.child_widget.show()
            self.layout.addWidget(self.child_widget)

    def reset(self):
        """重置边界"""
        self.retry()


class SafeWidget(QWidget):
    """安全组件包装器 - 自动捕获异常"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._error_boundary = None

    def safe_call(self, func: Callable, *args, **kwargs):
        """安全调用方法"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"安全调用失败: {func.__name__}", exc_info=True)
            if self._error_boundary:
                self._error_boundary.catch_error(e, f"调用{func.__name__}")
            return None

    def set_error_boundary(self, boundary: ErrorBoundary):
        """设置错误边界"""
        self._error_boundary = boundary


def with_error_boundary(
    widget_class: type,
    fallback_widget: QWidget | None = None,
    on_error: Callable | None = None,
):
    """错误边界装饰器（类工厂）"""

    def wrapper(*args, **kwargs):
        try:
            widget = widget_class(*args, **kwargs)
            boundary = ErrorBoundary(
                child_widget=widget, fallback_widget=fallback_widget, on_error=on_error
            )
            return boundary
        except Exception as e:
            logger.error(f"创建组件失败: {widget_class.__name__}", exc_info=True)
            boundary = ErrorBoundary(
                child_widget=None, fallback_widget=fallback_widget, on_error=on_error
            )
            boundary.catch_error(e, f"创建{widget_class.__name__}")
            return boundary

    return wrapper


if __name__ == "__main__":
    """测试错误边界"""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建会抛出错误的组件
    def create_buggy_widget():
        widget = QWidget()
        raise ValueError("测试错误")
        return widget

    # 使用错误边界
    boundary = ErrorBoundary()

    try:
        buggy = create_buggy_widget()
        boundary.set_child(buggy)
    except Exception as e:
        boundary.catch_error(e, "创建buggy组件")

    boundary.show()
    boundary.resize(400, 300)

    sys.exit(app.exec())
