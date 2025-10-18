"""
错误对话框
提供错误显示功能
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from ..utils.logger import get_logger

logger = get_logger(__name__)


def show_error(title: str, message: str, parent=None) -> None:
    """显示错误对话框

    Args:
        title: 错误标题
        message: 错误消息
        parent: 父控件
    """
    try:
        QMessageBox.critical(parent, title, message)
        logger.info(f"显示错误对话框: {title}")
    except Exception as e:
        logger.error(f"显示错误对话框失败: {e}")


def show_warning(title: str, message: str, parent=None) -> None:
    """显示警告对话框

    Args:
        title: 警告标题
        message: 警告消息
        parent: 父控件
    """
    try:
        QMessageBox.warning(parent, title, message)
        logger.info(f"显示警告对话框: {title}")
    except Exception as e:
        logger.error(f"显示警告对话框失败: {e}")


def show_info(title: str, message: str, parent=None) -> None:
    """显示信息对话框

    Args:
        title: 信息标题
        message: 信息消息
        parent: 父控件
    """
    try:
        QMessageBox.information(parent, title, message)
        logger.info(f"显示信息对话框: {title}")
    except Exception as e:
        logger.error(f"显示信息对话框失败: {e}")


def show_question(title: str, message: str, parent=None) -> bool:
    """显示问题对话框

    Args:
        title: 问题标题
        message: 问题消息
        parent: 父控件

    Returns:
        用户选择结果
    """
    try:
        result = QMessageBox.question(parent, title, message)
        logger.info(f"显示问题对话框: {title}")
        return result == QMessageBox.StandardButton.Yes
    except Exception as e:
        logger.error(f"显示问题对话框失败: {e}")
        return False
