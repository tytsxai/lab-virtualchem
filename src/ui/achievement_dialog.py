"""
成就对话框
显示成就解锁界面
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Achievement:
    """成就数据类"""

    def __init__(self, id: str, name: str, description: str, icon_path: str = "", rarity: str = "common"):
        self.id = id
        self.name = name
        self.description = description
        self.icon_path = icon_path
        self.rarity = rarity


class AchievementItem(QWidget):
    """成就项组件"""

    def __init__(self, achievement: Achievement):
        super().__init__()
        self.achievement = achievement
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)

        # 图标
        icon_label = QLabel()
        if self.achievement.icon_path:
            pixmap = QPixmap(self.achievement.icon_path)
            if not pixmap.isNull():
                # 缩放图标
                scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)
                icon_label.setPixmap(scaled_pixmap)
        else:
            # 默认图标
            icon_label.setText("🏆")
            icon_label.setStyleSheet("font-size: 32px;")

        # 成就信息
        info_layout = QVBoxLayout()

        name_label = QLabel(self.achievement.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(14)
        name_label.setFont(name_font)

        desc_label = QLabel(self.achievement.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")

        rarity_label = QLabel(f"稀有度: {self.achievement.rarity}")
        rarity_label.setStyleSheet("font-size: 10px; color: #888;")

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        info_layout.addWidget(rarity_label)

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)

        # 样式
        self.setStyleSheet("""
            AchievementItem {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 10px;
                margin: 2px;
            }
        """)


class AchievementUnlockedDialog(QDialog):
    """成就解锁对话框"""

    def __init__(self, achievements: list[Achievement], parent=None):
        super().__init__(parent)
        self.achievements = achievements
        self._setup_ui()
        logger.info(f"显示成就解锁对话框: {len(achievements)} 个成就")

    def _setup_ui(self):
        """设置界面"""
        self.setWindowTitle("🎉 成就解锁！")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("恭喜你解锁了新成就！")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 添加成就项
        for achievement in self.achievements:
            item = AchievementItem(achievement)
            scroll_layout.addWidget(item)

        # 添加弹性空间
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 分享按钮（可选）
        share_button = QPushButton("分享成就")
        share_button.clicked.connect(self._on_share)

        # 确定按钮
        ok_button = QPushButton("太棒了！")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        button_layout.addWidget(share_button)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        # 设置样式
        self.setStyleSheet("""
            AchievementUnlockedDialog {
                background-color: white;
            }
        """)

    def _on_share(self):
        """分享成就"""
        # 这里可以实现分享功能
        logger.info("用户选择分享成就")

    def _on_close(self):
        """关闭对话框"""
        self.accept()
