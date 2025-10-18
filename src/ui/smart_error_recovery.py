"""
智能错误恢复系统
提供友好的错误处理和自动恢复
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


class RecoveryStrategy(Enum):
    """恢复策略"""

    RETRY = "retry"  # 重试
    ROLLBACK = "rollback"  # 回滚
    RESET = "reset"  # 重置
    CONTINUE = "continue"  # 继续
    MANUAL = "manual"  # 手动处理


@dataclass
class ErrorContext:
    """错误上下文"""

    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    stack_trace: str
    user_action: str  # 用户正在进行的操作
    system_state: dict[str, Any]  # 系统状态快照


@dataclass
class RecoveryAction:
    """恢复动作"""

    strategy: RecoveryStrategy
    description: str
    action: Callable[[], bool]  # 返回是否成功
    auto_execute: bool = False  # 是否自动执行


class SmartErrorRecovery(QObject):
    """智能错误恢复系统"""

    # 信号
    error_occurred = Signal(ErrorContext)  # 错误发生
    recovery_attempted = Signal(RecoveryStrategy, bool)  # 恢复尝试，是否成功
    recovery_completed = Signal(bool)  # 恢复完成，是否成功

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 错误历史
        self.error_history: list[ErrorContext] = []

        # 恢复策略映射
        self.recovery_strategies: dict[str, list[RecoveryAction]] = {}

        # 自动恢复开关
        self.auto_recovery_enabled = True

        # 错误计数
        self.error_counts: dict[str, int] = {}

        logger.info("智能错误恢复系统初始化完成")

    def register_recovery_strategy(
        self,
        error_type: str,
        strategy: RecoveryStrategy,
        description: str,
        action: Callable[[], bool],
        auto: bool = False,
    ):
        """注册恢复策略

        Args:
            error_type: 错误类型
            strategy: 恢复策略
            description: 策略描述
            action: 恢复动作
            auto: 是否自动执行
        """
        if error_type not in self.recovery_strategies:
            self.recovery_strategies[error_type] = []

        recovery = RecoveryAction(strategy=strategy, description=description, action=action, auto_execute=auto)

        self.recovery_strategies[error_type].append(recovery)
        logger.info(f"注册恢复策略: {error_type} -> {strategy.value}")

    def handle_error(
        self,
        error: Exception,
        user_action: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        system_state: dict[str, Any] | None = None,
        parent_widget: QWidget | None = None,
    ) -> bool:
        """处理错误

        Args:
            error: 异常对象
            user_action: 用户操作描述
            severity: 严重程度
            system_state: 系统状态
            parent_widget: 父控件

        Returns:
            是否成功恢复
        """
        # 创建错误上下文
        context = ErrorContext(
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            user_action=user_action,
            system_state=system_state or {},
        )

        # 记录错误
        self.error_history.append(context)
        self.error_counts[context.error_type] = self.error_counts.get(context.error_type, 0) + 1

        # 发送信号
        self.error_occurred.emit(context)

        logger.error(
            f"错误发生: {context.error_type} - {context.error_message}\n"
            f"用户操作: {user_action}\n"
            f"严重程度: {severity.value}"
        )

        # 尝试恢复
        return self._attempt_recovery(context, parent_widget)

    def _attempt_recovery(self, context: ErrorContext, parent_widget: QWidget | None = None) -> bool:
        """尝试恢复

        Args:
            context: 错误上下文
            parent_widget: 父控件

        Returns:
            是否成功恢复
        """
        # 获取恢复策略
        strategies = self.recovery_strategies.get(context.error_type, [])

        if not strategies:
            logger.warning(f"没有可用的恢复策略: {context.error_type}")
            self._show_error_dialog(context, parent_widget)
            return False

        # 尝试自动恢复
        if self.auto_recovery_enabled:
            for recovery in strategies:
                if recovery.auto_execute:
                    logger.info(f"尝试自动恢复: {recovery.strategy.value}")

                    try:
                        success = recovery.action()
                        self.recovery_attempted.emit(recovery.strategy, success)

                        if success:
                            logger.info(f"自动恢复成功: {recovery.strategy.value}")
                            self.recovery_completed.emit(True)
                            return True

                    except Exception as e:
                        logger.error(f"自动恢复失败: {e}")

        # 显示恢复选项对话框
        return self._show_recovery_dialog(context, strategies, parent_widget)

    def _show_error_dialog(self, context: ErrorContext, parent: QWidget | None = None):
        """显示错误对话框"""
        icon_map = {
            ErrorSeverity.INFO: QMessageBox.Icon.Information,
            ErrorSeverity.WARNING: QMessageBox.Icon.Warning,
            ErrorSeverity.ERROR: QMessageBox.Icon.Critical,
            ErrorSeverity.CRITICAL: QMessageBox.Icon.Critical,
        }

        msg = QMessageBox(parent)
        msg.setIcon(icon_map.get(context.severity, QMessageBox.Icon.Critical))
        msg.setWindowTitle("错误")
        msg.setText(f"操作失败: {context.user_action}")
        msg.setInformativeText(context.error_message)
        msg.setDetailedText(context.stack_trace)

        # 添加建议
        suggestions = self._get_error_suggestions(context)
        if suggestions:
            msg.setText(msg.text() + "\n\n建议：\n" + "\n".join(f"• {s}" for s in suggestions))

        msg.exec()

    def _show_recovery_dialog(
        self, context: ErrorContext, strategies: list[RecoveryAction], parent: QWidget | None = None
    ) -> bool:
        """显示恢复选项对话框"""
        from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

        dialog = QDialog(parent)
        dialog.setWindowTitle("错误恢复")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # 错误信息
        error_label = QLabel(f"<b>错误：</b>{context.error_message}")
        error_label.setWordWrap(True)
        layout.addWidget(error_label)

        # 用户操作
        action_label = QLabel(f"<b>操作：</b>{context.user_action}")
        action_label.setWordWrap(True)
        layout.addWidget(action_label)

        # 恢复选项
        layout.addWidget(QLabel("\n<b>恢复选项：</b>"))

        for recovery in strategies:
            btn = QPushButton(f"{recovery.strategy.value}: {recovery.description}")
            btn.clicked.connect(lambda checked, r=recovery: self._execute_recovery(r, dialog))
            layout.addWidget(btn)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)

        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted

    def _execute_recovery(self, recovery: RecoveryAction, dialog: QDialog):
        """执行恢复动作"""
        try:
            success = recovery.action()
            self.recovery_attempted.emit(recovery.strategy, success)

            if success:
                logger.info(f"恢复成功: {recovery.strategy.value}")
                self.recovery_completed.emit(True)
                dialog.accept()
            else:
                logger.warning(f"恢复失败: {recovery.strategy.value}")
                QMessageBox.warning(dialog, "恢复失败", "恢复操作未成功，请尝试其他方式")

        except Exception as e:
            logger.error(f"执行恢复动作时出错: {e}")
            QMessageBox.critical(dialog, "恢复错误", f"执行恢复时发生错误：{e}")

    def _get_error_suggestions(self, context: ErrorContext) -> list[str]:
        """获取错误建议"""
        suggestions = []

        # 基于错误类型的建议
        if "FileNotFoundError" in context.error_type:
            suggestions.append("检查文件路径是否正确")
            suggestions.append("确认文件是否存在")

        elif "PermissionError" in context.error_type:
            suggestions.append("检查文件权限")
            suggestions.append("尝试以管理员身份运行")

        elif "ConnectionError" in context.error_type:
            suggestions.append("检查网络连接")
            suggestions.append("确认服务器地址正确")

        elif "ValueError" in context.error_type:
            suggestions.append("检查输入数据格式")
            suggestions.append("确认数值范围正确")

        elif "ImportError" in context.error_type:
            suggestions.append("检查依赖库是否安装")
            suggestions.append("运行 pip install -r requirements.txt")

        # 基于错误频率的建议
        if self.error_counts.get(context.error_type, 0) > 3:
            suggestions.append("此错误频繁发生，建议查看日志或联系技术支持")

        return suggestions

    def get_error_statistics(self) -> dict[str, Any]:
        """获取错误统计"""
        if not self.error_history:
            return {
                "total_errors": 0,
                "error_by_type": {},
                "error_by_severity": {},
                "recent_errors": [],
            }

        # 按类型统计
        by_type = {}
        for error in self.error_history:
            by_type[error.error_type] = by_type.get(error.error_type, 0) + 1

        # 按严重程度统计
        by_severity = {}
        for error in self.error_history:
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # 最近10个错误
        recent = [
            {
                "type": e.error_type,
                "message": e.error_message,
                "action": e.user_action,
                "time": e.timestamp.isoformat(),
            }
            for e in self.error_history[-10:]
        ]

        return {
            "total_errors": len(self.error_history),
            "error_by_type": by_type,
            "error_by_severity": by_severity,
            "recent_errors": recent,
        }


# 常用恢复策略工厂
class RecoveryStrategyFactory:
    """恢复策略工厂"""

    @staticmethod
    def create_retry_strategy(action: Callable[[], Any], max_retries: int = 3) -> Callable[[], bool]:
        """创建重试策略"""

        def retry():
            for i in range(max_retries):
                try:
                    action()
                    return True
                except Exception as e:
                    logger.warning(f"重试 {i + 1}/{max_retries} 失败: {e}")
                    if i == max_retries - 1:
                        return False
            return False

        return retry

    @staticmethod
    def create_rollback_strategy(backup_state: Any, restore_func: Callable[[Any], None]) -> Callable[[], bool]:
        """创建回滚策略"""

        def rollback():
            try:
                restore_func(backup_state)
                return True
            except Exception as e:
                logger.error(f"回滚失败: {e}")
                return False

        return rollback

    @staticmethod
    def create_reset_strategy(reset_func: Callable[[], None]) -> Callable[[], bool]:
        """创建重置策略"""

        def reset():
            try:
                reset_func()
                return True
            except Exception as e:
                logger.error(f"重置失败: {e}")
                return False

        return reset


# 全局单例
_error_recovery: SmartErrorRecovery | None = None


def get_error_recovery() -> SmartErrorRecovery:
    """获取错误恢复系统单例"""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = SmartErrorRecovery()
    return _error_recovery
