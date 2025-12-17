"""
等级提升对话框
显示等级提升的庆祝界面
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...utils.logger import get_logger

logger = get_logger(__name__)


class LevelUpDialog(QDialog):
    """等级提升对话框"""

    def __init__(
        self, new_level: int, rewards: dict[str, Any] | None = None, parent=None
    ):
        super().__init__(parent)
        self.new_level = new_level
        self.rewards = rewards or {}
        self._setup_ui()
        logger.info(f"显示等级提升对话框: 等级 {new_level}")

    def _setup_ui(self):
        """设置界面"""
        self.setWindowTitle("🎉 等级提升！")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 标题区域
        title_layout = QVBoxLayout()

        level_label = QLabel(f"恭喜升级到等级 {self.new_level}！")
        level_font = QFont()
        level_font.setBold(True)
        level_font.setPointSize(18)
        level_label.setFont(level_font)
        level_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("你获得了新的能力！")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-size: 12px;")

        title_layout.addWidget(level_label)
        title_layout.addWidget(subtitle_label)

        layout.addLayout(title_layout)

        # 奖励区域
        if self.rewards:
            rewards_label = QLabel("🎁 奖励物品:")
            rewards_label.setStyleSheet("font-weight: bold; margin-top: 10px;")

            rewards_text = ""
            for reward_type, reward_data in self.rewards.items():
                if reward_type == "exp_bonus":
                    rewards_text += f"经验加成: {reward_data}%\n"
                elif reward_type == "unlock_feature":
                    rewards_text += f"解锁功能: {reward_data}\n"
                elif reward_type == "cosmetic":
                    rewards_text += f"外观奖励: {reward_data}\n"

            rewards_value_label = QLabel(rewards_text.strip())
            rewards_value_label.setStyleSheet(
                "background-color: #f8f9fa; padding: 10px; border-radius: 5px;"
            )

            layout.addWidget(rewards_label)
            layout.addWidget(rewards_value_label)

        # 按钮
        button_layout = QHBoxLayout()

        # 稍后提醒按钮
        remind_button = QPushButton("稍后提醒")
        remind_button.clicked.connect(self._on_remind_later)

        # 立即使用按钮
        use_button = QPushButton("太棒了！")
        use_button.clicked.connect(self.accept)
        use_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        button_layout.addWidget(remind_button)
        button_layout.addStretch()
        button_layout.addWidget(use_button)

        layout.addLayout(button_layout)

        # 设置整体样式
        self.setStyleSheet("""
            LevelUpDialog {
                background-color: white;
                border-radius: 10px;
            }
        """)

    def _on_remind_later(self):
        """稍后提醒"""
        # 这里可以设置定时器稍后提醒
        self.accept()
        logger.info("用户选择稍后提醒等级提升")

    def showEvent(self, event):
        """显示事件 - 添加庆祝动画"""
        super().showEvent(event)

        # 这里可以添加庆祝动画效果
        # 比如闪烁、缩放等效果
        pass
