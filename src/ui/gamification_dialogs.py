"""
游戏化对话框
用于显示升级、成就解锁等通知
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..gamification.achievement_system import Achievement
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LevelUpDialog(QDialog):
    """升级对话框"""

    def __init__(self, old_level: int, new_level: int, new_title: str, parent=None):
        super().__init__(parent)
        self.old_level = old_level
        self.new_level = new_level
        self.new_title = new_title
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("恭喜升级！")
        self.setFixedSize(400, 300)
        self.setModal(True)

        # 移除标题栏装饰
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # 样式
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFD700, stop:1 #FFA500
                );
                border: 3px solid #FF8C00;
                border-radius: 15px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: white;
                color: #FF8C00;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("🎉 恭喜升级！")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # 等级变化
        level_label = QLabel(f"等级 {self.old_level} → {self.new_level}")
        level_label.setAlignment(Qt.AlignCenter)
        level_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        layout.addWidget(level_label)

        # 新称号
        title_text = QLabel(f"获得称号：{self.new_title}")
        title_text.setAlignment(Qt.AlignCenter)
        title_text.setStyleSheet("font-size: 18px;")
        layout.addWidget(title_text)

        layout.addStretch()

        # 确定按钮
        ok_btn = QPushButton("太棒了！")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        # 自动关闭定时器（5秒后）
        QTimer.singleShot(5000, self.accept)


class AchievementUnlockedDialog(QDialog):
    """成就解锁对话框"""

    def __init__(self, achievements: list[Achievement], parent=None):
        super().__init__(parent)
        self.achievements = achievements
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("成就解锁！")
        self.setFixedSize(450, 400)
        self.setModal(True)

        # 移除标题栏装饰
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # 样式
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9C27B0, stop:1 #673AB7
                );
                border: 3px solid #7B1FA2;
                border-radius: 15px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: white;
                color: #9C27B0;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("🏆 成就解锁！")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # 成就列表（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
        """
        )

        achievements_widget = QWidget()
        achievements_layout = QVBoxLayout(achievements_widget)
        achievements_layout.setSpacing(10)

        for achievement in self.achievements:
            # 成就卡片
            card = QWidget()
            card.setStyleSheet(
                """
                QWidget {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                }
            """
            )
            card_layout = QHBoxLayout(card)

            # 图标
            icon_label = QLabel(achievement.icon)
            icon_label.setStyleSheet("font-size: 36px;")
            card_layout.addWidget(icon_label)

            # 信息
            info_layout = QVBoxLayout()
            name_label = QLabel(achievement.name)
            name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            info_layout.addWidget(name_label)

            desc_label = QLabel(achievement.description)
            desc_label.setStyleSheet("font-size: 12px;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

            reward_label = QLabel(f"🎁 +{achievement.exp_reward} EXP")
            reward_label.setStyleSheet("font-size: 12px; font-weight: bold;")
            info_layout.addWidget(reward_label)

            card_layout.addLayout(info_layout, 1)

            achievements_layout.addWidget(card)

        scroll.setWidget(achievements_widget)
        layout.addWidget(scroll)

        # 确定按钮
        ok_btn = QPushButton("太好了！")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        # 自动关闭定时器（8秒后）
        QTimer.singleShot(8000, self.accept)
