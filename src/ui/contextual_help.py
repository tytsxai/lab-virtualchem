"""
上下文相关帮助系统
根据用户当前位置提供相关帮助
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HelpTopic:
    """帮助主题"""

    id: str
    title: str
    content: str
    keywords: list[str]
    related: list[str]  # 相关主题ID
    see_also: list[str] | None = None  # 参见


class ContextualHelpWidget(QWidget):
    """上下文帮助控件"""

    close_requested = Signal()

    def __init__(self, help_topic: HelpTopic, parent: QWidget | None = None):
        super().__init__(parent)
        self.help_topic = help_topic

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(350)
        self.setMaximumWidth(500)

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(f"📖 {self.help_topic.title}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(title_label)

        # 内容
        content_browser = QTextBrowser()
        content_browser.setHtml(self.help_topic.content)
        content_browser.setOpenExternalLinks(True)
        content_browser.setMaximumHeight(200)
        content_browser.setStyleSheet(
            """
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 10pt;
            }
        """
        )
        layout.addWidget(content_browser)

        # 相关主题
        if self.help_topic.related:
            related_label = QLabel("相关主题:")
            related_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(related_label)

            for related_id in self.help_topic.related[:3]:  # 最多显示3个
                btn = QPushButton(f"→ {related_id}")
                btn.setFlat(True)
                btn.setStyleSheet(
                    """
                    QPushButton {
                        text-align: left;
                        padding: 4px 8px;
                        color: #2196F3;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #e3f2fd;
                        border-radius: 4px;
                    }
                """
                )
                layout.addWidget(btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        )
        layout.addWidget(close_btn)

        # 设置整体样式
        self.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 8px;
            }
        """
        )

    def show_near_widget(self, target_widget: QWidget):
        """在目标控件附近显示

        Args:
            target_widget: 目标控件
        """
        # 计算位置（在控件右侧）
        target_pos = target_widget.mapToGlobal(QPoint(0, 0))
        x = target_pos.x() + target_widget.width() + 10
        y = target_pos.y()

        self.move(x, y)
        self.show()
        self.raise_()


class ContextualHelpManager:
    """上下文帮助管理器"""

    _instance = None

    def __init__(self):
        self.help_topics: dict[str, HelpTopic] = {}
        self.current_help_widget: ContextualHelpWidget | None = None

        # 加载默认帮助主题
        self.load_default_topics()

        logger.info("上下文帮助管理器初始化完成")

    @classmethod
    def instance(cls) -> ContextualHelpManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_default_topics(self):
        """加载默认帮助主题"""
        default_topics = [
            HelpTopic(
                id="start_experiment",
                title="开始实验",
                content="""
                <p>要开始一个实验，请按照以下步骤操作：</p>
                <ol>
                    <li>从左侧列表中选择一个实验模板</li>
                    <li>查看实验简介和所需器材</li>
                    <li>点击"开始实验"按钮</li>
                    <li>按照步骤提示完成实验</li>
                </ol>
                <p><b>提示：</b>双击实验模板可快速开始</p>
                """,
                keywords=["开始", "实验", "模板"],
                related=["experiment_steps", "save_progress"],
            ),
            HelpTopic(
                id="experiment_steps",
                title="实验步骤",
                content="""
                <p>实验步骤会显示在界面右侧：</p>
                <ul>
                    <li>✅ 已完成的步骤显示为绿色</li>
                    <li>🔵 当前步骤高亮显示</li>
                    <li>⚪ 未完成的步骤为灰色</li>
                </ul>
                <p><b>操作提示：</b>将鼠标悬停在步骤上可查看详细说明</p>
                """,
                keywords=["步骤", "进度", "完成"],
                related=["start_experiment", "undo_operation"],
            ),
            HelpTopic(
                id="save_progress",
                title="保存进度",
                content="""
                <p>您的实验进度会自动保存：</p>
                <ul>
                    <li>每隔5分钟自动保存一次</li>
                    <li>暂停实验时自动保存</li>
                    <li>您也可以按 <b>Ctrl+S</b> 手动保存</li>
                </ul>
                <p><b>注意：</b>保存的进度可以在"历史记录"中找到</p>
                """,
                keywords=["保存", "进度", "自动"],
                related=["view_history", "continue_experiment"],
            ),
            HelpTopic(
                id="undo_operation",
                title="撤销操作",
                content="""
                <p>如果操作失误，可以撤销：</p>
                <ul>
                    <li>按 <b>Ctrl+Z</b> 撤销上一步操作</li>
                    <li>按 <b>Ctrl+Y</b> 重做已撤销的操作</li>
                    <li>最多可以撤销50步操作</li>
                </ul>
                <p><b>提示：</b>某些关键步骤可能无法撤销</p>
                """,
                keywords=["撤销", "重做", "恢复"],
                related=["experiment_steps", "reset_experiment"],
            ),
            HelpTopic(
                id="knowledge_base",
                title="知识库",
                content="""
                <p>知识库包含丰富的化学知识：</p>
                <ul>
                    <li>化学元素和周期表</li>
                    <li>常用化学反应</li>
                    <li>实验技巧和注意事项</li>
                    <li>安全操作规程</li>
                </ul>
                <p><b>快捷键：</b>按 <b>Ctrl+K</b> 快速打开知识库</p>
                """,
                keywords=["知识库", "学习", "化学"],
                related=["search_knowledge", "periodic_table"],
            ),
            HelpTopic(
                id="shortcuts",
                title="快捷键",
                content="""
                <p>常用快捷键列表：</p>
                <ul>
                    <li><b>F1</b> - 打开帮助</li>
                    <li><b>Ctrl+N</b> - 新建实验</li>
                    <li><b>Ctrl+S</b> - 保存进度</li>
                    <li><b>Ctrl+Z</b> - 撤销</li>
                    <li><b>Ctrl+K</b> - 知识库</li>
                    <li><b>Ctrl+G</b> - 游戏模式</li>
                    <li><b>Ctrl+,</b> - 设置</li>
                </ul>
                <p><b>完整列表：</b>按 <b>Ctrl+Shift+K</b> 查看所有快捷键</p>
                """,
                keywords=["快捷键", "键盘", "操作"],
                related=["settings", "customize"],
            ),
        ]

        for topic in default_topics:
            self.help_topics[topic.id] = topic

        logger.debug(f"已加载 {len(default_topics)} 个帮助主题")

    def show_help(self, topic_id: str, target_widget: QWidget | None = None):
        """显示帮助

        Args:
            topic_id: 帮助主题ID
            target_widget: 目标控件（帮助将显示在其附近）
        """
        if topic_id not in self.help_topics:
            logger.warning(f"未找到帮助主题: {topic_id}")
            return

        # 关闭当前帮助
        if self.current_help_widget:
            self.current_help_widget.close()

        # 创建并显示新帮助
        topic = self.help_topics[topic_id]
        self.current_help_widget = ContextualHelpWidget(topic)

        if target_widget:
            self.current_help_widget.show_near_widget(target_widget)
        else:
            self.current_help_widget.show()

        logger.debug(f"显示帮助主题: {topic_id}")

    def hide_help(self):
        """隐藏当前帮助"""
        if self.current_help_widget:
            self.current_help_widget.close()
            self.current_help_widget = None

    def add_topic(self, topic: HelpTopic):
        """添加帮助主题

        Args:
            topic: 帮助主题
        """
        self.help_topics[topic.id] = topic
        logger.debug(f"添加帮助主题: {topic.id}")

    def search_topics(self, keyword: str) -> list[HelpTopic]:
        """搜索帮助主题

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的帮助主题列表
        """
        keyword = keyword.lower()
        results = []

        for topic in self.help_topics.values():
            # 在标题、内容和关键词中搜索
            if (
                keyword in topic.title.lower()
                or keyword in topic.content.lower()
                or any(keyword in kw.lower() for kw in topic.keywords)
            ):
                results.append(topic)

        return results


def show_contextual_help(topic_id: str, target_widget: QWidget | None = None):
    """显示上下文帮助

    Args:
        topic_id: 帮助主题ID
        target_widget: 目标控件
    """
    ContextualHelpManager.instance().show_help(topic_id, target_widget)
