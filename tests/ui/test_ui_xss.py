import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tooltip_enhancer_escapes_html_payload(qapp):
    from src.ui.tooltip_enhancer import TooltipEnhancer

    payload = '<img src=x onerror=alert(1)><script>alert("x")</script>'
    rendered = TooltipEnhancer._format_as_html(payload)
    assert "<img" not in rendered
    assert "<script" not in rendered
    assert "&lt;img" in rendered
    assert "&lt;script" in rendered


def test_feedback_widget_uses_plain_text(qapp):
    from PySide6.QtCore import Qt

    from src.ui.widgets.enhanced_feedback_widget import EnhancedFeedbackWidget

    widget = EnhancedFeedbackWidget()
    widget.show_feedback('<b onclick="alert(1)">X</b>', auto_hide=False)

    assert widget.message_label.textFormat() == Qt.TextFormat.PlainText
    assert "<b" in widget.message_label.text()


def test_validated_line_edit_tooltip_escaped(qapp):
    from src.ui.validated_input import ValidatedLineEdit

    def always_invalid(text: str):
        return False, f'bad: <img src=x onerror="{text}">'

    w = ValidatedLineEdit(validator=always_invalid, required=True)
    w.setText("x")
    w.validate()

    tooltip = w.toolTip()
    assert "<img" not in tooltip
    assert "&lt;img" in tooltip


def test_validate_dialog_path_rejects_outside_allowed(tmp_path: Path):
    from src.ui.path_security import validate_dialog_path

    outside = Path("/etc/passwd")
    with pytest.raises(ValueError):
        validate_dialog_path(str(outside))


def test_validate_dialog_path_accepts_temp(tmp_path: Path):
    from src.ui.path_security import default_allowed_dirs, validate_dialog_path

    # 使用 repo 的 temp 目录作为允许目录之一（测试环境下可写）
    # 注意：default_allowed_dirs() 依赖于项目结构，这里只验证逻辑分支。
    allowed = default_allowed_dirs()
    temp_dir = next((p for p in allowed if p.name == "temp"), None)
    if temp_dir is None:
        pytest.skip("project temp dir not configured")

    temp_dir.mkdir(parents=True, exist_ok=True)
    candidate = temp_dir / "xss_test_output.txt"
    assert validate_dialog_path(str(candidate), allowed_dirs=allowed) == candidate.resolve()

