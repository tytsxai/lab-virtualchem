"""
游戏化面板
显示用户等级、经验、任务和成就
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...utils.logger import get_logger

logger = get_logger(__name__)


class LevelCard(QWidget):
    """等级卡片"""

    def __init__(self):
        super().__init__()
        self.level = 1
        self.exp = 0
        self.next_level_exp = 100
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 等级标题
        self.level_label = QLabel("等级 1")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        # 经验进度条
        self.exp_bar = QProgressBar()
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setValue(0)
        self.exp_bar.setTextVisible(True)
        self.exp_bar.setFormat("经验: %v/%m")

        # 经验文本
        self.exp_label = QLabel("0 / 100 XP")
        self.exp_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.level_label)
        layout.addWidget(self.exp_bar)
        layout.addWidget(self.exp_label)

        # 样式
        self.setStyleSheet("""
            LevelCard {
                background-color: #f8f9fa;
                border: 2px solid #007bff;
                border-radius: 10px;
                padding: 15px;
            }
        """)

    def update_level(self, level: int, exp: int, next_level_exp: int):
        """更新等级信息"""
        self.level = level
        self.exp = exp
        self.next_level_exp = next_level_exp

        self.level_label.setText(f"等级 {level}")
        self.exp_bar.setRange(0, next_level_exp)
        self.exp_bar.setValue(exp)
        self.exp_label.setText(f"{exp} / {next_level_exp} XP")


class QuestCard(QWidget):
    """任务卡片"""

    def __init__(self, quest_data: dict[str, Any]):
        super().__init__()
        self.quest_data = quest_data
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 任务标题
        title = QLabel(self.quest_data.get("title", "未知任务"))
        title.setStyleSheet("font-weight: bold;")

        # 任务描述
        description = QLabel(self.quest_data.get("description", ""))
        description.setWordWrap(True)

        # 任务进度
        progress = self.quest_data.get("progress", 0)
        total = self.quest_data.get("total", 1)

        progress_label = QLabel(f"进度: {progress}/{total}")
        progress_label.setStyleSheet("color: #666; font-size: 12px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(progress_label)

        # 样式
        self.setStyleSheet("""
            QuestCard {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 10px;
                margin: 2px;
            }
        """)


class AchievementCard(QWidget):
    """成就卡片"""

    def __init__(self, achievement_data: dict[str, Any]):
        super().__init__()
        self.achievement_data = achievement_data
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)

        # 成就图标
        icon_label = QLabel("🏆")
        icon_label.setStyleSheet("font-size: 24px;")

        # 成就信息
        info_layout = QVBoxLayout()

        title = QLabel(self.achievement_data.get("title", "未知成就"))
        title.setStyleSheet("font-weight: bold;")

        description = QLabel(self.achievement_data.get("description", ""))
        description.setWordWrap(True)

        info_layout.addWidget(title)
        info_layout.addWidget(description)

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)

        # 样式
        unlocked = self.achievement_data.get("unlocked", False)
        if unlocked:
            self.setStyleSheet("""
                AchievementCard {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                AchievementCard {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 2px;
                }
            """)


class GamificationPanel(QWidget):
    """游戏化面板"""

    def __init__(self, gamification_manager=None, parent=None):
        super().__init__(parent)
        self.gamification_manager = gamification_manager
        self.level_card = None
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 等级卡片
        self.level_card = LevelCard()
        layout.addWidget(self.level_card)

        # 任务区域
        quests_label = QLabel("📋 活跃任务")
        quests_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(quests_label)

        self.quests_scroll = QScrollArea()
        self.quests_widget = QWidget()
        self.quests_layout = QVBoxLayout(self.quests_widget)
        self.quests_scroll.setWidget(self.quests_widget)
        self.quests_scroll.setWidgetResizable(True)
        layout.addWidget(self.quests_scroll)

        # 成就区域
        achievements_label = QLabel("🏆 成就")
        achievements_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(achievements_label)

        self.achievements_scroll = QScrollArea()
        self.achievements_widget = QWidget()
        self.achievements_layout = QVBoxLayout(self.achievements_widget)
        self.achievements_scroll.setWidget(self.achievements_widget)
        self.achievements_scroll.setWidgetResizable(True)
        layout.addWidget(self.achievements_scroll)

        # 添加弹性空间
        layout.addStretch()

    def update_level_card(self, level: int, exp: int, next_level_exp: int):
        """更新等级卡片"""
        if self.level_card:
            self.level_card.update_level(level, exp, next_level_exp)

    def clear_quests(self):
        """清空任务"""
        # 清空布局
        while self.quests_layout.count():
            child = self.quests_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def add_quest_card(self, quest_data: dict[str, Any]) -> QuestCard:
        """添加任务卡片"""
        card = QuestCard(quest_data)
        self.quests_layout.addWidget(card)
        return card

    def clear_achievements(self):
        """清空成就"""
        # 清空布局
        while self.achievements_layout.count():
            child = self.achievements_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def add_achievement_card(self, achievement_data: dict[str, Any], unlocked: bool = False) -> AchievementCard:  # noqa: ARG002
        """添加成就卡片"""
        card = AchievementCard(achievement_data)
        self.achievements_layout.addWidget(card)
        return card
