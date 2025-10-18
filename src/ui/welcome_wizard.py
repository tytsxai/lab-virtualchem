"""
首次使用引导向导
帮助新用户快速了解和上手 VirtualChemLab
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..utils.i18n import I18n
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WelcomeWizard(QDialog):
    """欢迎向导对话框"""

    finished = Signal(bool)  # 是否完成向导 (True) 或跳过 (False)

    def __init__(self, parent=None, i18n: I18n | None = None):
        super().__init__(parent)
        self.i18n = i18n or I18n()
        self.current_page = 0
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(self.i18n.t("wizard.welcome_title", default="欢迎使用 VirtualChemLab"))
        self.setModal(True)
        self.resize(750, 550)

        # 设置样式
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f8f9fa;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
            }
        """
        )

        # 主布局
        layout = QVBoxLayout(self)

        # 页面堆栈
        self.page_stack = QStackedWidget()
        layout.addWidget(self.page_stack)

        # 创建各个页面
        self.pages = [
            self.create_welcome_page(),
            self.create_features_page(),
            self.create_howto_page(),
            self.create_tips_page(),
            self.create_finish_page(),
        ]

        for page in self.pages:
            self.page_stack.addWidget(page)

        # 底部按钮
        button_layout = QHBoxLayout()

        self.skip_btn = QPushButton(self.i18n.t("wizard.skip", default="跳过"))
        self.skip_btn.clicked.connect(self.skip_wizard)
        self.skip_btn.setStyleSheet("color: #666;")

        self.prev_btn = QPushButton("← " + self.i18n.t("wizard.previous", default="上一步"))
        self.prev_btn.clicked.connect(self.previous_page)
        self.prev_btn.setEnabled(False)

        self.next_btn = QPushButton(self.i18n.t("wizard.next", default="下一步") + " →")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setDefault(True)
        self.next_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """
        )

        self.finish_btn = QPushButton(self.i18n.t("wizard.finish", default="完成"))
        self.finish_btn.clicked.connect(self.finish_wizard)
        self.finish_btn.hide()

        # "不再显示"复选框
        self.dont_show_again = QCheckBox(self.i18n.t("wizard.dont_show_again"))

        button_layout.addWidget(self.dont_show_again)
        button_layout.addStretch()
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.finish_btn)

        layout.addLayout(button_layout)

    def create_welcome_page(self) -> QWidget:
        """创建欢迎页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # 标题
        title = QLabel(self.i18n.t("wizard.welcome_title"))
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 版本
        version = QLabel(self.i18n.t("wizard.version"))
        version.setStyleSheet("color: #666; font-size: 14px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # 介绍文字
        intro = QLabel(self.i18n.t("wizard.intro"))
        intro.setAlignment(Qt.AlignCenter)
        intro.setStyleSheet("font-size: 13px; line-height: 1.6;")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # 图标或图片占位
        icon_label = QLabel("🔬")
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        return page

    def create_features_page(self) -> QWidget:
        """创建功能介绍页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # 标题
        title = QLabel("✨ 核心功能")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 功能列表
        features = [
            ("🧪", "丰富的实验模板", "涵盖酸碱滴定、缓冲溶液、结晶、蒸馏等多种实验类型"),
            ("📊", "实时数据分析", "自动生成实验曲线和数据图表，直观展示实验过程"),
            ("💯", "智能评分系统", "根据操作准确度和安全规范自动评分，即时反馈"),
            ("📝", "实验报告生成", "一键生成专业的实验报告，包含数据、图表和分析"),
            ("📚", "知识库支持", "内置化学知识库，随时查询相关知识点"),
            ("⚠️", "安全提示", "实时提供安全操作提示，培养良好的实验习惯"),
        ]

        for icon, feature_title, description in features:
            feature_widget = self.create_feature_item(icon, feature_title, description)
            layout.addWidget(feature_widget)

        layout.addStretch()

        return page

    def create_feature_item(self, icon: str, title: str, description: str) -> QWidget:
        """创建功能项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)

        # 文字
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)

        # 样式
        widget.setStyleSheet(
            """
            QWidget {
                background-color: #f8f9fa;
                border-radius: 5px;
            }
        """
        )

        return widget

    def create_howto_page(self) -> QWidget:
        """创建使用方法页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # 标题
        title = QLabel("📖 如何开始实验")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 步骤说明
        steps = [
            ("1️⃣", "选择实验", "从左侧实验列表中选择您想要进行的实验"),
            ("2️⃣", "阅读说明", "仔细阅读实验目标、试剂清单和安全提示"),
            ("3️⃣", "按步骤操作", "按照步骤指引完成实验，每步操作都会有提示"),
            ("4️⃣", "记录数据", "在提示处输入实验数据和观察结果"),
            ("5️⃣", "查看结果", "实验结束后查看评分、图表和详细分析"),
            ("6️⃣", "生成报告", "如需要，可以生成并导出实验报告"),
        ]

        for icon, step_title, description in steps:
            step_widget = self.create_step_item(icon, step_title, description)
            layout.addWidget(step_widget)

        layout.addStretch()

        return page

    def create_step_item(self, icon: str, title: str, description: str) -> QWidget:
        """创建步骤项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px;")
        icon_label.setFixedWidth(40)
        icon_label.setAlignment(Qt.AlignTop)
        layout.addWidget(icon_label)

        # 文字
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #555; font-size: 12px;")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)

        return widget

    def create_tips_page(self) -> QWidget:
        """创建使用技巧页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # 标题
        title = QLabel("💡 实用技巧")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 技巧内容
        tips_html = """
        <div style='font-size: 12px; line-height: 1.8;'>
            <h3 style='color: #0078d4;'>⌨️ 快捷键</h3>
            <ul>
                <li><b>Ctrl+N</b> - 新建实验</li>
                <li><b>Ctrl+O</b> - 打开记录</li>
                <li><b>Ctrl+S</b> - 保存进度(自动)</li>
                <li><b>F5</b> - 刷新实验列表</li>
                <li><b>F1</b> - 打开帮助</li>
            </ul>

            <h3 style='color: #0078d4;'>🎯 操作建议</h3>
            <ul>
                <li>首次使用建议从 <b>"基础"</b> 难度的实验开始</li>
                <li>注意查看每步的 <b>安全提示</b> 和 <b>操作提示</b></li>
                <li>输入数据时注意 <b>单位</b> 和 <b>有效数字</b></li>
                <li>实验会 <b>自动保存进度</b>，可随时继续</li>
                <li>遇到问题可以查看 <b>知识库</b> 或 <b>提示</b></li>
            </ul>

            <h3 style='color: #0078d4;'>🔧 常见问题</h3>
            <ul>
                <li><b>Q: 实验列表为空？</b><br>
                    A: 检查 assets/templates 目录是否有实验模板文件</li>
                <li><b>Q: 如何查看历史记录？</b><br>
                    A: 菜单 → 实验 → 查看记录</li>
                <li><b>Q: 如何重做实验？</b><br>
                    A: 在记录浏览器中选择记录，点击"重做"</li>
            </ul>
        </div>
        """

        tips_browser = QTextBrowser()
        tips_browser.setHtml(tips_html)
        tips_browser.setOpenExternalLinks(False)
        layout.addWidget(tips_browser)

        return page

    def create_finish_page(self) -> QWidget:
        """创建完成页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # 图标
        icon = QLabel("🎉")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # 标题
        title = QLabel("准备就绪!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 说明
        message = QLabel(
            "您已经了解了 VirtualChemLab 的基本使用方法。\n\n"
            "现在可以开始您的虚拟实验之旅了！\n\n"
            "从左侧列表选择一个实验开始吧~ 🚀"
        )
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("font-size: 14px; line-height: 1.8;")
        message.setWordWrap(True)
        layout.addWidget(message)

        # 帮助提示
        help_text = QLabel("💡 提示: 随时按 F1 可以打开帮助文档")
        help_text.setStyleSheet("color: #666; font-size: 12px; margin-top: 30px;")
        help_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(help_text)

        return page

    def next_page(self):
        """下一页"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.page_stack.setCurrentIndex(self.current_page)
            self.update_buttons()

    def previous_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_stack.setCurrentIndex(self.current_page)
            self.update_buttons()

    def update_buttons(self):
        """更新按钮状态"""
        # 上一步按钮
        self.prev_btn.setEnabled(self.current_page > 0)

        # 下一步/完成按钮
        if self.current_page == len(self.pages) - 1:
            self.next_btn.hide()
            self.finish_btn.show()
            self.skip_btn.hide()
        else:
            self.next_btn.show()
            self.finish_btn.hide()
            self.skip_btn.show()

    def skip_wizard(self):
        """跳过向导"""
        self.finished.emit(False)
        self.accept()
        logger.info("用户跳过了欢迎向导")

    def finish_wizard(self):
        """完成向导"""
        self.finished.emit(True)
        self.accept()
        logger.info("用户完成了欢迎向导")

    def should_show_again(self) -> bool:
        """是否下次还要显示"""
        return not self.dont_show_again.isChecked()


def show_welcome_wizard(parent=None, i18n: I18n | None = None) -> bool:
    """显示欢迎向导

    Args:
        parent: 父窗口
        i18n: 国际化管理器

    Returns:
        是否应该下次还显示
    """
    wizard = WelcomeWizard(parent, i18n)
    wizard.exec()
    return wizard.should_show_again()
