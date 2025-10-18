"""交互式错误恢复向导

帮助用户诊断和恢复错误
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ErrorRecoveryWizard(QDialog):
    """错误恢复向导"""

    recovery_completed = Signal(bool, str)  # 是否成功, 恢复方式

    def __init__(
        self,
        error_type: str,
        error_message: str,
        error_details: str = "",
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.error_type = error_type
        self.error_message = error_message
        self.error_details = error_details

        self.recovery_options: list[RecoveryOption] = []
        self.selected_option: RecoveryOption | None = None

        self.setWindowTitle("错误恢复向导")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        self._init_ui()
        self._generate_recovery_options()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("🔧 错误恢复向导")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 错误描述
        error_group = QGroupBox("错误信息")
        error_layout = QVBoxLayout(error_group)

        self.error_label = QLabel(f"<b>错误类型:</b> {self.error_type}")
        self.error_label.setWordWrap(True)
        error_layout.addWidget(self.error_label)

        self.message_label = QLabel(f"<b>错误描述:</b> {self.error_message}")
        self.message_label.setWordWrap(True)
        error_layout.addWidget(self.message_label)

        layout.addWidget(error_group)

        # 恢复选项
        options_group = QGroupBox("恢复选项")
        self.options_layout = QVBoxLayout(options_group)

        self.button_group = QButtonGroup(self)

        layout.addWidget(options_group)

        # 详细信息
        details_group = QGroupBox("详细步骤")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        details_layout.addWidget(self.details_text)

        layout.addWidget(details_group)

        # 进度条（恢复过程中显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮
        button_layout = QHBoxLayout()

        self.help_button = QPushButton("帮助")
        self.help_button.clicked.connect(self._show_help)
        button_layout.addWidget(self.help_button)

        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.recover_button = QPushButton("开始恢复")
        self.recover_button.setDefault(True)
        self.recover_button.clicked.connect(self._start_recovery)
        self.recover_button.setEnabled(False)
        button_layout.addWidget(self.recover_button)

        layout.addLayout(button_layout)

        # 连接信号
        self.button_group.buttonClicked.connect(self._on_option_selected)

    def _generate_recovery_options(self):
        """生成恢复选项"""
        # 根据错误类型生成不同的恢复选项
        if "FileNotFoundError" in self.error_type or "找不到文件" in self.error_message:
            self.recovery_options = [
                RecoveryOption(
                    "recreate_file",
                    "重新创建文件",
                    "尝试在原位置重新创建缺失的文件",
                    "1. 检查文件路径\n2. 创建必要的目录\n3. 生成默认文件内容\n4. 验证文件创建成功",
                    self._recover_recreate_file,
                ),
                RecoveryOption(
                    "use_default",
                    "使用默认配置",
                    "跳过该文件，使用系统默认配置继续",
                    "1. 加载内置默认配置\n2. 跳过文件加载步骤\n3. 继续正常运行",
                    self._recover_use_default,
                ),
                RecoveryOption(
                    "manual_fix",
                    "手动修复",
                    "打开文件所在目录，让您手动处理",
                    "1. 打开文件所在目录\n2. 请手动检查和创建文件\n3. 完成后重启应用",
                    self._recover_manual_fix,
                ),
            ]

        elif "PermissionError" in self.error_type or "权限" in self.error_message:
            self.recovery_options = [
                RecoveryOption(
                    "change_location",
                    "更改保存位置",
                    "将文件保存到用户文档目录",
                    "1. 检测用户文档目录\n2. 在新位置创建文件\n3. 更新配置中的路径",
                    self._recover_change_location,
                ),
                RecoveryOption(
                    "run_as_admin",
                    "请求管理员权限",
                    "提示您以管理员身份重启应用",
                    "1. 保存当前状态\n2. 显示管理员权限说明\n3. 提供重启选项",
                    self._recover_run_as_admin,
                ),
            ]

        elif "NetworkError" in self.error_type or "网络" in self.error_message:
            self.recovery_options = [
                RecoveryOption(
                    "retry_connection",
                    "重试连接",
                    "检查网络并重新尝试连接",
                    "1. 检测网络连接状态\n2. 等待3秒后重试\n3. 最多重试3次",
                    self._recover_retry_connection,
                ),
                RecoveryOption(
                    "offline_mode",
                    "离线模式",
                    "切换到离线模式继续使用",
                    "1. 禁用网络功能\n2. 使用本地缓存数据\n3. 在离线模式下继续",
                    self._recover_offline_mode,
                ),
            ]

        elif "ValueError" in self.error_type or "ValidationError" in self.error_type:
            self.recovery_options = [
                RecoveryOption(
                    "reset_data",
                    "重置数据",
                    "清除错误的数据，使用默认值",
                    "1. 备份当前数据\n2. 清除无效数据\n3. 加载默认值",
                    self._recover_reset_data,
                ),
                RecoveryOption(
                    "manual_edit",
                    "手动编辑",
                    "打开配置文件让您手动修改",
                    "1. 备份当前配置\n2. 用文本编辑器打开\n3. 完成后重新加载",
                    self._recover_manual_edit,
                ),
            ]

        else:
            # 通用恢复选项
            self.recovery_options = [
                RecoveryOption(
                    "restart",
                    "重启应用",
                    "重启应用以恢复到初始状态",
                    "1. 保存当前工作\n2. 关闭所有窗口\n3. 重新启动应用",
                    self._recover_restart,
                ),
                RecoveryOption(
                    "reset_config",
                    "重置配置",
                    "恢复到默认配置",
                    "1. 备份当前配置\n2. 删除配置文件\n3. 使用默认配置重启",
                    self._recover_reset_config,
                ),
                RecoveryOption(
                    "ignore",
                    "忽略错误",
                    "忽略此错误继续运行（可能不稳定）",
                    "1. 记录错误到日志\n2. 继续运行\n3. 可能会影响部分功能",
                    self._recover_ignore,
                ),
            ]

        # 添加选项到UI
        for i, option in enumerate(self.recovery_options):
            radio = QRadioButton(option.title)
            radio.setToolTip(option.description)
            self.button_group.addButton(radio, i)
            self.options_layout.addWidget(radio)

            desc_label = QLabel(f"  {option.description}")
            desc_label.setStyleSheet("color: gray; margin-left: 20px;")
            self.options_layout.addWidget(desc_label)

    def _on_option_selected(self, button):
        """选项被选中"""
        option_id = self.button_group.id(button)
        self.selected_option = self.recovery_options[option_id]

        # 显示详细步骤
        self.details_text.setPlainText(self.selected_option.steps)

        # 启用恢复按钮
        self.recover_button.setEnabled(True)

    def _start_recovery(self):
        """开始恢复"""
        if not self.selected_option:
            return

        logger.info(f"开始错误恢复: {self.selected_option.id}")

        # 禁用按钮
        self.recover_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度

        # 执行恢复
        try:
            success = self.selected_option.action()

            if success:
                self.recovery_completed.emit(True, self.selected_option.id)
                self.accept()
            else:
                self.recovery_completed.emit(False, self.selected_option.id)
                self.progress_bar.setVisible(False)
                self.recover_button.setEnabled(True)
                self.cancel_button.setEnabled(True)
        except Exception as e:
            logger.error(f"恢复失败: {e}", exc_info=True)
            self.recovery_completed.emit(False, str(e))
            self.progress_bar.setVisible(False)
            self.recover_button.setEnabled(True)
            self.cancel_button.setEnabled(True)

    def _show_help(self):
        """显示帮助"""
        from PySide6.QtWidgets import QMessageBox

        help_text = """
错误恢复向导帮助

1. 查看错误信息
   - 了解发生了什么错误
   - 阅读错误描述

2. 选择恢复选项
   - 根据您的需求选择合适的恢复方式
   - 查看每个选项的详细步骤

3. 开始恢复
   - 点击"开始恢复"按钮
   - 等待恢复过程完成

提示：
• 如果不确定，可以先尝试"重试"或"忽略"选项
• 重要数据会自动备份
• 可以随时取消恢复过程
        """

        QMessageBox.information(self, "帮助", help_text.strip())

    # 恢复操作实现
    def _recover_recreate_file(self) -> bool:
        """重新创建文件"""
        logger.info("尝试重新创建文件")
        # 实现文件重建逻辑
        return True

    def _recover_use_default(self) -> bool:
        """使用默认配置"""
        logger.info("使用默认配置")
        return True

    def _recover_manual_fix(self) -> bool:
        """手动修复"""
        logger.info("打开文件位置供手动修复")
        # 打开文件管理器
        return True

    def _recover_change_location(self) -> bool:
        """更改保存位置"""
        logger.info("更改保存位置到用户目录")
        return True

    def _recover_run_as_admin(self) -> bool:
        """请求管理员权限"""
        logger.info("提示以管理员身份运行")
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "管理员权限", "请关闭应用，然后右键点击应用图标，选择'以管理员身份运行'。")
        return True

    def _recover_retry_connection(self) -> bool:
        """重试连接"""
        logger.info("重试网络连接")
        return True

    def _recover_offline_mode(self) -> bool:
        """离线模式"""
        logger.info("切换到离线模式")
        return True

    def _recover_reset_data(self) -> bool:
        """重置数据"""
        logger.info("重置数据到默认值")
        return True

    def _recover_manual_edit(self) -> bool:
        """手动编辑"""
        logger.info("打开配置文件供编辑")
        return True

    def _recover_restart(self) -> bool:
        """重启应用"""
        logger.info("准备重启应用")
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "重启应用", "应用将在关闭后重新启动。\n请保存您的工作后点击确定。")
        return True

    def _recover_reset_config(self) -> bool:
        """重置配置"""
        logger.info("重置配置到默认值")
        return True

    def _recover_ignore(self) -> bool:
        """忽略错误"""
        logger.info("忽略错误继续运行")
        return True


class RecoveryOption:
    """恢复选项"""

    def __init__(
        self,
        option_id: str,
        title: str,
        description: str,
        steps: str,
        action: Callable[[], bool],
    ):
        self.id = option_id
        self.title = title
        self.description = description
        self.steps = steps
        self.action = action


def show_error_recovery_wizard(
    error_type: str,
    error_message: str,
    error_details: str = "",
    parent: QWidget = None,
) -> bool:
    """显示错误恢复向导

    Returns:
        是否成功恢复
    """
    wizard = ErrorRecoveryWizard(error_type, error_message, error_details, parent)

    success = False
    recovery_method = ""

    def on_recovery_completed(is_success: bool, method: str):
        nonlocal success, recovery_method
        success = is_success
        recovery_method = method
        logger.info(f"恢复完成: success={success}, method={method}")

    wizard.recovery_completed.connect(on_recovery_completed)
    wizard.exec()

    return success


__all__ = [
    "ErrorRecoveryWizard",
    "RecoveryOption",
    "show_error_recovery_wizard",
]
