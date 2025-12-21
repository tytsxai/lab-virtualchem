"""
UI 安全工具函数（XSS/注入防护）

说明：
- Qt 的 QLabel / toolTip 会在检测到 `<...>` 时按富文本渲染，容易产生 UI XSS。
- 本模块提供统一的转义与 PlainText 设置，避免各处重复实现。
"""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QTextEdit, QWidget


def escape_html(text: Any) -> str:
    """对可能来自用户/外部的数据做 HTML 转义。"""
    return html.escape("" if text is None else str(text), quote=True)


def set_plain_text(label: QLabel, text: Any) -> None:
    """以纯文本方式设置 QLabel 文本，避免富文本解释。"""
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setText("" if text is None else str(text))


def force_plain_text(label: QLabel) -> None:
    """将 QLabel 设为 PlainText（建议在控件初始化时调用）。"""
    label.setTextFormat(Qt.TextFormat.PlainText)


def set_safe_tooltip(widget: QWidget, text: Any) -> None:
    """设置安全 tooltip：对输入转义，避免富文本解释与事件属性注入。"""
    widget.setToolTip(escape_html(text))


def sanitize_user_text(text: Any, max_length: int, allow_newlines: bool) -> str:
    """对 UI 输入做长度限制与特殊字符过滤（防 UI XSS/注入）。"""
    raw = "" if text is None else str(text)
    if len(raw) > max_length:
        raw = raw[:max_length]

    # 过滤掉会触发 Qt 富文本解析的关键字符，以及控制字符
    disallowed = {"<", ">", "\x00"}
    if not allow_newlines:
        disallowed.update({"\r", "\n"})

    filtered = []
    for ch in raw:
        if ch in disallowed:
            continue
        # 过滤不可见控制字符（保留换行仅在 allow_newlines 时）
        code = ord(ch)
        if code < 32:
            if allow_newlines:
                if ch not in ("\t", "\n"):
                    continue
            else:
                if ch != "\t":
                    continue
        filtered.append(ch)

    return "".join(filtered)


def apply_text_constraints(widget: QWidget, max_length: int = 1000) -> None:
    """为 QLineEdit / QTextEdit 应用输入约束（长度 + 特殊字符过滤）。"""
    if isinstance(widget, QLineEdit):
        widget.setMaxLength(max_length)

        def _on_change() -> None:
            sanitized = sanitize_user_text(widget.text(), max_length, allow_newlines=False)
            if sanitized != widget.text():
                cursor = widget.cursorPosition()
                widget.blockSignals(True)
                widget.setText(sanitized)
                widget.setCursorPosition(min(cursor, len(sanitized)))
                widget.blockSignals(False)

        widget.textChanged.connect(_on_change)
        return

    if isinstance(widget, QTextEdit):
        allow_newlines = True

        def _on_change() -> None:
            text = widget.toPlainText()
            sanitized = sanitize_user_text(text, max_length, allow_newlines=allow_newlines)
            if sanitized != text:
                cursor = widget.textCursor()
                pos = cursor.position()
                widget.blockSignals(True)
                widget.setPlainText(sanitized)
                cursor = widget.textCursor()
                cursor.setPosition(min(pos, len(sanitized)))
                widget.setTextCursor(cursor)
                widget.blockSignals(False)

        widget.textChanged.connect(_on_change)
