"""
游戏化UI组件
提供平面化设计的游戏化界面元素
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..gamification.achievement_system import Achievement
from ..gamification.level_system import UserLevel
from ..gamification.quest_system import Quest, UserQuest
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FlatProgressBar(QProgressBar):
    """平面化进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        self.setFixedHeight(24)
        self._setup_style()

    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                background-color: #f5f5f5;
                text-align: center;
                font-weight: bold;
                color: #333;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #8BC34A
                );
                border-radius: 10px;
            }
        """
        )


class LevelBadge(QWidget):
    """等级徽章"""

    def __init__(self, level: int = 1, parent=None):
        super().__init__(parent)
        self.level = level
        self.setFixedSize(80, 80)

    def set_level(self, level: int):
        """设置等级"""
        self.level = level
        self.update()

    def paintEvent(self, event):  # noqa: ARG002
        """绘制徽章"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 外圈
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        if self.level < 10:
            gradient.setColorAt(0, QColor("#8BC34A"))
            gradient.setColorAt(1, QColor("#4CAF50"))
        elif self.level < 30:
            gradient.setColorAt(0, QColor("#42A5F5"))
            gradient.setColorAt(1, QColor("#1E88E5"))
        elif self.level < 50:
            gradient.setColorAt(0, QColor("#AB47BC"))
            gradient.setColorAt(1, QColor("#8E24AA"))
        else:
            gradient.setColorAt(0, QColor("#FFA726"))
            gradient.setColorAt(1, QColor("#FB8C00"))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#ff"), 3))
        painter.drawEllipse(5, 5, 70, 70)

        # 内圈
        painter.setBrush(QColor("#ff"))
        painter.drawEllipse(12, 12, 56, 56)

        # 等级文字
        painter.setPen(QColor("#333"))
        font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, str(self.level))


class UserLevelCard(QWidget):
    """用户等级卡片"""

    def __init__(self, user_level: UserLevel | None = None, parent=None):
        super().__init__(parent)
        self.user_level = user_level
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFixedHeight(120)
        self.setStyleSheet(
            """
            UserLevelCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
            }
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 等级徽章
        self.level_badge = LevelBadge()
        layout.addWidget(self.level_badge)

        # 信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 用户名和称号
        self.title_label = QLabel("化学新手")
        self.title_label.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            color: #333;
        """
        )
        info_layout.addWidget(self.title_label)

        # 等级信息
        self.level_label = QLabel("等级 1")
        self.level_label.setStyleSheet("font-size: 13px; color: #666;")
        info_layout.addWidget(self.level_label)

        # 经验进度条
        self.exp_bar = FlatProgressBar()
        self.exp_bar.setFormat("%v / %m EXP")
        info_layout.addWidget(self.exp_bar)

        layout.addLayout(info_layout, 1)

        # 更新显示
        if self.user_level:
            self.update_display()

    def update_display(self):
        """更新显示"""
        if not self.user_level:
            return

        self.level_badge.set_level(self.user_level.level)
        self.title_label.setText(self.user_level.title)
        self.level_label.setText(f"等级 {self.user_level.level}")

    def set_exp_progress(self, current: int, required: int):
        """设置经验进度

        Args:
            current: 当前经验
            required: 所需经验
        """
        self.exp_bar.setMaximum(required if required > 0 else 100)
        self.exp_bar.setValue(current)

    def set_user_level(self, user_level: UserLevel):
        """设置用户等级"""
        self.user_level = user_level
        self.update_display()


class AchievementCard(QWidget):
    """成就卡片"""

    clicked = Signal(str)  # 点击信号，传递成就ID

    def __init__(self, achievement: Achievement, unlocked: bool = False, parent=None):
        super().__init__(parent)
        self.achievement = achievement
        self.unlocked = unlocked
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFixedSize(180, 200)
        self.setCursor(Qt.PointingHandCursor)

        # 根据稀有度设置边框颜色
        rarity_colors = {
            "common": "#9E9E9E",
            "rare": "#2196F3",
            "epic": "#9C27B0",
            "legendary": "#FF9800",
        }
        rarity_colors.get(self.achievement.rarity, "#9E9E9E")

        # 样式
        self.setStyleSheet(
            """
            AchievementCard {{
                background-color: white;
                border: 3px solid {border_color};
                border-radius: 10px;
                opacity: {opacity};
            }}
            AchievementCard:hover {{
                border-width: 4px;
            }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 图标
        icon_label = QLabel(self.achievement.icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)

        # 名称
        name_label = QLabel(self.achievement.name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #333;
        """
        )
        layout.addWidget(name_label)

        # 描述
        desc_label = QLabel(self.achievement.description)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            """
            font-size: 11px;
            color: #666;
        """
        )
        layout.addWidget(desc_label)

        # 奖励
        reward_label = QLabel(f"🎁 {self.achievement.exp_reward} EXP")
        reward_label.setAlignment(Qt.AlignCenter)
        reward_label.setStyleSheet(
            """
            font-size: 12px;
            color: #4CAF50;
            font-weight: bold;
        """
        )
        layout.addWidget(reward_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.achievement.id)


class QuestCard(QWidget):
    """任务卡片"""

    claim_clicked = Signal(str)  # 领取奖励信号，传递任务ID

    def __init__(self, quest: Quest, user_quest: UserQuest, parent=None):
        super().__init__(parent)
        self.quest = quest
        self.user_quest = user_quest
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFixedHeight(120)
        self.setStyleSheet(
            """
            QuestCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
            }
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 图标
        icon_label = QLabel(self.quest.icon)
        icon_label.setFixedSize(60, 60)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            """
            font-size: 36px;
            background-color: #f5f5f5;
            border-radius: 30px;
        """
        )
        layout.addWidget(icon_label)

        # 信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 任务名称
        name_label = QLabel(self.quest.name)
        name_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #333;
        """
        )
        info_layout.addWidget(name_label)

        # 任务描述
        desc_label = QLabel(self.quest.description)
        desc_label.setStyleSheet("font-size: 12px; color: #666;")
        info_layout.addWidget(desc_label)

        # 进度条
        progress_bar = FlatProgressBar()
        progress_bar.setMaximum(self.user_quest.target)
        progress_bar.setValue(self.user_quest.progress)
        progress_bar.setFormat("%v / %m")
        info_layout.addWidget(progress_bar)

        layout.addLayout(info_layout, 1)

        # 领取按钮
        self.claim_btn = QPushButton("领取奖励")
        self.claim_btn.setFixedSize(80, 35)
        self.claim_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """
        )
        self.claim_btn.clicked.connect(lambda: self.claim_clicked.emit(self.quest.id))

        # 根据状态设置按钮
        if self.user_quest.is_completed and self.user_quest.status.value == "completed":
            self.claim_btn.setEnabled(True)
        else:
            self.claim_btn.setEnabled(False)
            self.claim_btn.setText("未完成")

        layout.addWidget(self.claim_btn, alignment=Qt.AlignCenter)


class ExpGainAnimation(QLabel):
    """经验获得动画"""

    def __init__(self, exp: int, parent=None):
        super().__init__(parent)
        self.setText(f"+{exp} EXP")
        self.setStyleSheet(
            """
            font-size: 20px;
            font-weight: bold;
            color: #4CAF50;
            background-color: rgba(255, 255, 255, 200);
            border: 2px solid #4CAF50;
            border-radius: 5px;
            padding: 5px 10px;
        """
        )
        self.adjustSize()

        # 设置动画
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(1500)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(self.deleteLater)

    def start_animation(self, start_pos, end_pos):
        """开始动画

        Args:
            start_pos: 起始位置
            end_pos: 结束位置
        """
        self.move(start_pos)
        self.show()
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()


class GamificationPanel(QWidget):
    """游戏化面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 用户等级卡片
        self.level_card = UserLevelCard()
        layout.addWidget(self.level_card)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)

        # 标签：任务
        quests_label = QLabel("📋 每日任务")
        quests_label.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 5px;
        """
        )
        layout.addWidget(quests_label)

        # 任务列表区域
        self.quests_scroll = QScrollArea()
        self.quests_scroll.setWidgetResizable(True)
        self.quests_scroll.setFixedHeight(250)
        self.quests_scroll.setStyleSheet("border: none;")

        self.quests_container = QWidget()
        self.quests_layout = QVBoxLayout(self.quests_container)
        self.quests_layout.setSpacing(10)
        self.quests_layout.addStretch()

        self.quests_scroll.setWidget(self.quests_container)
        layout.addWidget(self.quests_scroll)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line2)

        # 标签：最近成就
        achievements_label = QLabel("🏆 最近成就")
        achievements_label.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 5px;
        """
        )
        layout.addWidget(achievements_label)

        # 成就网格
        self.achievements_grid = QGridLayout()
        self.achievements_grid.setSpacing(10)
        layout.addLayout(self.achievements_grid)

        layout.addStretch()

    def update_level_card(self, user_level, current_exp: int, required_exp: int):
        """更新等级卡片"""
        self.level_card.set_user_level(user_level)
        self.level_card.set_exp_progress(current_exp, required_exp)

    def add_quest_card(self, quest: Quest, user_quest: UserQuest):
        """添加任务卡片"""
        card = QuestCard(quest, user_quest)
        # 在addStretch之前插入
        self.quests_layout.insertWidget(self.quests_layout.count() - 1, card)
        return card

    def add_achievement_card(self, achievement: Achievement, unlocked: bool = False):
        """添加成就卡片"""
        card = AchievementCard(achievement, unlocked)

        # 计算网格位置
        count = self.achievements_grid.count()
        row = count // 3
        col = count % 3

        self.achievements_grid.addWidget(card, row, col)
        return card

    def clear_quests(self):
        """清空任务列表"""
        while self.quests_layout.count() > 1:  # 保留stretch
            item = self.quests_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear_achievements(self):
        """清空成就网格"""
        while self.achievements_grid.count():
            item = self.achievements_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
