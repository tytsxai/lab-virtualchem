"""
帮助系统
提供上下文相关的帮助和文档功能
"""

import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class HelpTopic:
    """帮助主题"""

    def __init__(
        self,
        topic_id: str,
        title: str,
        content: str,
        category: str = "general",
        keywords: list[str] | None = None,
        related_topics: list[str] | None = None,
    ):
        self.topic_id = topic_id
        self.title = title
        self.content = content
        self.category = category
        self.keywords = keywords or []
        self.related_topics = related_topics or []


class HelpDialog(QDialog):
    """帮助对话框"""

    # 信号
    topic_selected = Signal(str)  # topic_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.theme_manager = ThemeManager()

        self.setWindowTitle("📚 帮助文档")
        self.setMinimumSize(800, 600)
        self.setModal(False)

        # 帮助数据
        self.help_topics: dict[str, HelpTopic] = {}
        self.current_topic: HelpTopic | None = None

        self.init_ui()
        self.load_help_topics()
        self.apply_theme()

        logger.info("帮助对话框初始化完成")

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 标题
        title_label = QLabel("📚 VirtualChemLab 帮助文档")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)

        # 左侧：主题列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 搜索框
        search_label = QLabel("搜索帮助主题:")
        left_layout.addWidget(search_label)

        self.search_edit = QTextEdit()
        self.search_edit.setMaximumHeight(30)
        self.search_edit.setPlaceholderText("输入关键词搜索...")
        self.search_edit.textChanged.connect(self.filter_topics)
        left_layout.addWidget(self.search_edit)

        # 搜索选项
        search_options_layout = QHBoxLayout()

        self.search_title_checkbox = QCheckBox("标题")
        self.search_title_checkbox.setChecked(True)
        search_options_layout.addWidget(self.search_title_checkbox)

        self.search_content_checkbox = QCheckBox("内容")
        self.search_content_checkbox.setChecked(True)
        search_options_layout.addWidget(self.search_content_checkbox)

        self.search_keywords_checkbox = QCheckBox("关键词")
        self.search_keywords_checkbox.setChecked(True)
        search_options_layout.addWidget(self.search_keywords_checkbox)

        left_layout.addLayout(search_options_layout)

        # 主题列表
        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self.on_topic_selected)
        left_layout.addWidget(self.topic_list)

        main_splitter.addWidget(left_widget)

        # 右侧：内容显示
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 内容标题
        self.content_title = QLabel("")
        self.content_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_layout.addWidget(self.content_title)

        # 内容文本
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        right_layout.addWidget(self.content_text)

        # 相关主题
        related_label = QLabel("相关主题:")
        right_layout.addWidget(related_label)

        self.related_list = QListWidget()
        self.related_list.itemClicked.connect(self.on_related_topic_selected)
        self.related_list.setMaximumHeight(100)
        right_layout.addWidget(self.related_list)

        main_splitter.addWidget(right_widget)

        # 设置分割器比例
        main_splitter.setSizes([300, 500])

        # 按钮
        button_layout = QHBoxLayout()

        self.home_button = ModernButton("🏠 首页")
        self.home_button.clicked.connect(self.show_home)
        button_layout.addWidget(self.home_button)

        self.back_button = ModernButton("⬅️ 返回")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        self.forward_button = ModernButton("➡️ 前进")
        self.forward_button.clicked.connect(self.go_forward)
        button_layout.addWidget(self.forward_button)

        button_layout.addStretch()

        self.print_button = ModernButton("🖨️ 打印")
        self.print_button.clicked.connect(self.print_content)
        button_layout.addWidget(self.print_button)

        self.close_button = ModernButton("❌ 关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def load_help_topics(self) -> None:
        """加载帮助主题"""
        # 基础操作
        self.add_topic(
            HelpTopic(
                "getting_started",
                "快速开始",
                "欢迎使用 VirtualChemLab！\n\n"
                "快速开始步骤：\n"
                "1. 选择实验模板\n"
                "2. 点击开始实验\n"
                "3. 按照步骤进行操作\n"
                "4. 观察实验结果\n\n"
                "💡 提示：首次使用建议运行教程模式。",
                category="basic",
                keywords=["开始", "新手", "入门", "教程"],
                related_topics=["tutorial", "experiment_selection"],
            )
        )

        self.add_topic(
            HelpTopic(
                "tutorial",
                "交互式教程",
                "VirtualChemLab 提供交互式教程，帮助您快速上手。\n\n"
                "教程内容包括：\n"
                "• 基础操作指南\n"
                "• 游戏模式介绍\n"
                "• 物理模拟功能\n"
                "• 粒子效果系统\n\n"
                "如何启动教程：\n"
                "1. 点击菜单栏的'帮助'\n"
                "2. 选择'交互式教程'\n"
                "3. 按照提示完成教程\n\n"
                "💡 提示：教程可以随时跳过或重新开始。",
                category="basic",
                keywords=["教程", "学习", "指导", "新手"],
                related_topics=["getting_started", "game_mode"],
            )
        )

        self.add_topic(
            HelpTopic(
                "experiment_selection",
                "选择实验",
                "VirtualChemLab 提供多种类型的化学实验：\n\n"
                "实验类型：\n"
                "• 滴定实验：学习酸碱滴定技术\n"
                "• 合成实验：进行有机合成反应\n"
                "• 晶体生长：观察晶体形成过程\n"
                "• 电化学：研究电化学反应\n\n"
                "选择实验：\n"
                "1. 在左侧列表中选择实验\n"
                "2. 查看实验详情和难度\n"
                "3. 点击'开始实验'按钮\n\n"
                "💡 提示：建议从简单实验开始。",
                category="basic",
                keywords=["实验", "选择", "类型", "难度"],
                related_topics=["getting_started", "experiment_types"],
            )
        )

        # 游戏模式
        self.add_topic(
            HelpTopic(
                "game_mode",
                "游戏模式",
                "VirtualChemLab 的游戏模式提供独特的交互体验。\n\n"
                "游戏特性：\n"
                "• 物理模拟引擎\n"
                "• 粒子效果系统\n"
                "• 分数和连击系统\n"
                "• 稀有度物品系统\n\n"
                "切换游戏模式：\n"
                "• 快捷键：Ctrl+G\n"
                "• 菜单：游戏模式 → 切换游戏模式\n\n"
                "游戏控制：\n"
                "• 拖拽：移动实验器材\n"
                "• 点击：与物品交互\n"
                "• 空格键：震动所有物品\n"
                "• G键：切换重力\n"
                "• R键：重置所有物品\n\n"
                "💡 提示：游戏模式让学习更有趣！",
                category="game",
                keywords=["游戏", "模式", "交互", "物理"],
                related_topics=["physics_simulation", "particle_effects"],
            )
        )

        self.add_topic(
            HelpTopic(
                "physics_simulation",
                "物理模拟",
                "VirtualChemLab 内置了强大的物理模拟引擎。\n\n"
                "物理特性：\n"
                "• 重力模拟\n"
                "• 碰撞检测\n"
                "• 摩擦力和弹跳\n"
                "• 实时物理更新\n\n"
                "物理参数：\n"
                "• 重力强度：控制物品下落速度\n"
                "• 摩擦力：影响物品滑动阻力\n"
                "• 弹跳系数：决定碰撞反弹程度\n"
                "• 碰撞检测：启用/禁用碰撞检测\n\n"
                "调整物理设置：\n"
                "1. 菜单 → 游戏模式 → 物理设置\n"
                "2. 调整各项参数\n"
                "3. 点击应用保存设置\n\n"
                "💡 提示：物理模拟让实验更真实。",
                category="game",
                keywords=["物理", "模拟", "重力", "碰撞"],
                related_topics=["game_mode", "physics_settings"],
            )
        )

        self.add_topic(
            HelpTopic(
                "particle_effects",
                "粒子效果",
                "粒子效果系统为实验增添了视觉魅力。\n\n"
                "效果类型：\n"
                "• 闪烁：物品交互时的光效\n"
                "• 发光：物品激活时的光环\n"
                "• 爆炸：碰撞时的爆发效果\n"
                "• 轨迹：移动时的拖尾效果\n"
                "• 气泡：液体中的气泡效果\n"
                "• 烟雾：加热时的烟雾效果\n"
                "• 火焰：燃烧时的火焰效果\n"
                "• 水花：液体溅射效果\n\n"
                "调整粒子效果：\n"
                "1. 菜单 → 游戏模式 → 粒子效果设置\n"
                "2. 调整效果类型和强度\n"
                "3. 点击应用保存设置\n\n"
                "💡 提示：粒子效果可以提升视觉体验。",
                category="game",
                keywords=["粒子", "效果", "视觉", "动画"],
                related_topics=["game_mode", "visual_effects"],
            )
        )

        # 高级功能
        self.add_topic(
            HelpTopic(
                "performance_monitoring",
                "性能监控",
                "VirtualChemLab 内置了性能监控系统。\n\n"
                "监控指标：\n"
                "• CPU 使用率\n"
                "• 内存使用量\n"
                "• 帧率 (FPS)\n"
                "• 物理更新时间\n"
                "• 粒子数量\n"
                "• 活跃物品数量\n\n"
                "打开性能监控：\n"
                "• 快捷键：Ctrl+Shift+P\n"
                "• 菜单：性能监控\n\n"
                "优化建议：\n"
                "• 降低粒子效果数量\n"
                "• 减少物理计算复杂度\n"
                "• 清理内存缓存\n"
                "• 执行垃圾回收\n\n"
                "💡 提示：定期检查性能有助于流畅体验。",
                category="advanced",
                keywords=["性能", "监控", "优化", "FPS"],
                related_topics=["optimization", "system_requirements"],
            )
        )

        self.add_topic(
            HelpTopic(
                "configuration",
                "配置管理",
                "VirtualChemLab 提供灵活的配置管理系统。\n\n"
                "配置类型：\n"
                "• 应用设置：语言、主题、窗口大小\n"
                "• UI设置：字体、动画、效果\n"
                "• 游戏设置：物理参数、粒子效果\n"
                "• 实验设置：自动进行、数据记录\n"
                "• 路径设置：实验、模板、备份路径\n"
                "• 日志设置：日志级别、文件大小\n\n"
                "打开配置：\n"
                "• 快捷键：Ctrl+Shift+,\n"
                "• 菜单：设置\n\n"
                "配置功能：\n"
                "• 导入/导出配置\n"
                "• 重置为默认设置\n"
                "• 实时配置更新\n\n"
                "💡 提示：备份重要配置设置。",
                category="advanced",
                keywords=["配置", "设置", "管理", "导入导出"],
                related_topics=["settings", "backup"],
            )
        )

        # 故障排除
        self.add_topic(
            HelpTopic(
                "troubleshooting",
                "故障排除",
                "常见问题及解决方案：\n\n"
                "问题1：应用启动缓慢\n"
                "解决方案：\n"
                "• 检查系统资源使用情况\n"
                "• 关闭不必要的后台程序\n"
                "• 清理临时文件\n"
                "• 重启应用程序\n\n"
                "问题2：游戏模式卡顿\n"
                "解决方案：\n"
                "• 降低粒子效果数量\n"
                "• 减少物理计算复杂度\n"
                "• 检查性能监控面板\n"
                "• 更新显卡驱动程序\n\n"
                "问题3：实验数据丢失\n"
                "解决方案：\n"
                "• 检查自动保存设置\n"
                "• 查看备份文件\n"
                "• 恢复最近保存的数据\n"
                "• 联系技术支持\n\n"
                "💡 提示：遇到问题请查看日志文件。",
                category="troubleshooting",
                keywords=["问题", "故障", "解决", "错误"],
                related_topics=["performance_monitoring", "backup"],
            )
        )

        # 显示首页
        self.show_home()

    def add_topic(self, topic: HelpTopic) -> None:
        """添加帮助主题"""
        self.help_topics[topic.topic_id] = topic

    def filter_topics(self) -> None:
        """过滤主题"""
        search_text = self.search_edit.toPlainText().lower()

        self.topic_list.clear()

        for topic_id, topic in self.help_topics.items():
            match = False

            # 根据搜索选项进行匹配
            if (
                self.search_title_checkbox.isChecked()
                and search_text in topic.title.lower()
                or self.search_content_checkbox.isChecked()
                and search_text in topic.content.lower()
                or self.search_keywords_checkbox.isChecked()
                and any(search_text in keyword.lower() for keyword in topic.keywords)
            ):
                match = True

            if match or not search_text:  # 没有搜索文本时显示所有主题
                item = QListWidgetItem(topic.title)
                item.setData(Qt.ItemDataRole.UserRole, topic_id)

                # 添加匹配度指示
                if search_text:
                    score = self._calculate_match_score(topic, search_text)
                    if score > 0.8:
                        item.setText(f"⭐ {topic.title}")
                    elif score > 0.6:
                        item.setText(f"🔍 {topic.title}")

                self.topic_list.addItem(item)

    def _calculate_match_score(self, topic: HelpTopic, search_text: str) -> float:
        """计算匹配度"""
        score = 0.0

        # 标题完全匹配
        if search_text == topic.title.lower():
            score += 1.0
        # 标题包含
        elif search_text in topic.title.lower():
            score += 0.8

        # 内容匹配
        if search_text in topic.content.lower():
            score += 0.6

        # 关键词匹配
        keyword_matches = sum(
            1 for keyword in topic.keywords if search_text in keyword.lower()
        )
        if keyword_matches > 0:
            score += 0.4 * keyword_matches / len(topic.keywords)

        return min(score, 1.0)

    def on_topic_selected(self, item: QListWidgetItem) -> None:
        """处理主题选择"""
        topic_id = item.data(Qt.ItemDataRole.UserRole)
        self.show_topic(topic_id)

    def show_topic(self, topic_id: str) -> None:
        """显示主题"""
        if topic_id not in self.help_topics:
            return

        topic = self.help_topics[topic_id]
        self.current_topic = topic

        # 添加到历史记录
        if not hasattr(self, "_history"):
            self._history: list[str] = []
            self._history_index = -1

        # 如果当前主题不在历史记录中，添加到历史记录
        if not self._history or self._history[self._history_index] != topic_id:
            # 删除当前位置之后的历史记录
            if self._history_index < len(self._history) - 1:
                self._history = self._history[: self._history_index + 1]

            # 添加新主题
            self._history.append(topic_id)
            self._history_index = len(self._history) - 1

        # 更新内容
        self.content_title.setText(topic.title)
        self.content_text.setText(topic.content)

        # 更新相关主题
        self.related_list.clear()
        for related_id in topic.related_topics:
            if related_id in self.help_topics:
                related_topic = self.help_topics[related_id]
                item = QListWidgetItem(related_topic.title)
                item.setData(Qt.ItemDataRole.UserRole, related_id)
                self.related_list.addItem(item)

        # 发送信号
        self.topic_selected.emit(topic_id)

    def on_related_topic_selected(self, item: QListWidgetItem) -> None:
        """处理相关主题选择"""
        topic_id = item.data(Qt.ItemDataRole.UserRole)
        self.show_topic(topic_id)

    def show_home(self) -> None:
        """显示首页"""
        self.content_title.setText("📚 VirtualChemLab 帮助文档")
        self.content_text.setText(
            "欢迎使用 VirtualChemLab 帮助系统！\n\n"
            "在这里您可以找到：\n"
            "• 快速开始指南\n"
            "• 详细功能说明\n"
            "• 故障排除方法\n"
            "• 高级功能使用\n\n"
            "使用左侧列表浏览主题，或使用搜索框查找特定内容。\n\n"
            "💡 提示：首次使用建议查看'快速开始'和'交互式教程'。"
        )
        self.related_list.clear()

    def go_back(self) -> None:
        """返回"""
        if hasattr(self, "_history") and hasattr(self, "_history_index"):
            if self._history_index > 0:
                self._history_index -= 1
                topic_id = self._history[self._history_index]
                self.show_topic(topic_id)
                logger.info(f"返回到主题: {topic_id}")
            else:
                logger.info("已经是历史记录的第一页")
        else:
            # 初始化历史记录
            self._history = []
            self._history_index = -1
            logger.info("历史记录功能已初始化")

    def go_forward(self) -> None:
        """前进"""
        if hasattr(self, "_history") and hasattr(self, "_history_index"):
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                topic_id = self._history[self._history_index]
                self.show_topic(topic_id)
                logger.info(f"前进到主题: {topic_id}")
            else:
                logger.info("已经是历史记录的最后一页")
        else:
            # 初始化历史记录
            self._history = []
            self._history_index = -1
            logger.info("历史记录功能已初始化")

    def print_content(self) -> None:
        """打印内容"""
        if self.current_topic:
            try:
                from PySide6.QtPrintSupport import QPrintDialog, QPrinter
                from PySide6.QtWidgets import QMessageBox

                # 创建打印机
                printer = QPrinter()

                # 显示打印对话框
                print_dialog = QPrintDialog(printer, self)
                print_dialog.setWindowTitle("打印帮助内容")

                if print_dialog.exec():
                    # 创建打印内容
                    from PySide6.QtGui import QTextDocument

                    document = QTextDocument()
                    html_content = f"""
                    <html>
                    <head>
                        <title>{self.current_topic.title}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 20px; }}
                            h1 {{ color: #333; border-bottom: 2px solid #4a90e2; }}
                            p {{ line-height: 1.6; }}
                        </style>
                    </head>
                    <body>
                        <h1>{self.current_topic.title}</h1>
                        <div>{self.current_topic.content.replace(chr(10), "<br>")}</div>
                    </body>
                    </html>
                    """

                    document.setHtml(html_content)
                    document.print_(printer)

                    logger.info(f"成功打印主题: {self.current_topic.title}")
                    QMessageBox.information(self, "打印完成", "内容已发送到打印机")
                else:
                    logger.info("用户取消了打印操作")

            except ImportError:
                # 如果没有打印支持，导出为文本文件
                from PySide6.QtWidgets import QFileDialog, QMessageBox

                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    "保存帮助内容",
                    f"{self.current_topic.title}.txt",
                    "文本文件 (*.txt)",
                )

                if filename:
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(f"{self.current_topic.title}\n")
                            f.write("=" * len(self.current_topic.title) + "\n\n")
                            f.write(self.current_topic.content)

                        logger.info(f"帮助内容已保存到: {filename}")
                        QMessageBox.information(
                            self, "保存完成", f"内容已保存到:\n{filename}"
                        )
                    except Exception as e:
                        logger.error(f"保存文件失败: {e}")
                        QMessageBox.warning(
                            self, "保存失败", f"保存文件时发生错误:\n{e}"
                        )

            except Exception as e:
                logger.error(f"打印功能失败: {e}")
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "打印失败", f"打印过程中发生错误:\n{e}")
        else:
            logger.warning("没有可打印的内容")

    def apply_theme(self) -> None:
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #16213e;
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    selection-background-color: #4a90e2;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #2d1b69;
                }
                QListWidget::item:selected {
                    background-color: #4a90e2;
                }
                QTextEdit {
                    background-color: #16213e;
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12px;
                }
                QLabel {
                    color: #ffffff;
                }
            """
            )

            logger.info("帮助主题应用成功")

        except Exception as e:
            logger.warning(f"应用帮助主题失败: {e}")


class HelpManager:
    """帮助管理器"""

    def __init__(self) -> None:
        self.help_dialog: HelpDialog | None = None
        self.context_help: dict[str, str] = {}

        # 初始化上下文帮助
        self._init_context_help()

        logger.info("帮助管理器初始化完成")

    def _init_context_help(self) -> None:
        """初始化上下文帮助"""
        self.context_help = {
            "main_window": "getting_started",
            "experiment_list": "experiment_selection",
            "game_mode": "game_mode",
            "physics_settings": "physics_simulation",
            "particle_settings": "particle_effects",
            "performance_dialog": "performance_monitoring",
            "settings_dialog": "configuration",
            "tutorial_dialog": "tutorial",
        }

    def show_help(
        self, context: str | None = None, parent: QWidget | None = None
    ) -> None:
        """显示帮助"""
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(parent)

        if context and context in self.context_help:
            topic_id = self.context_help[context]
            self.help_dialog.show_topic(topic_id)

        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def show_topic(self, topic_id: str, parent: QWidget | None = None) -> None:
        """显示特定主题"""
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(parent)

        self.help_dialog.show_topic(topic_id)
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def open_online_docs(self) -> None:
        """打开在线文档"""
        try:
            webbrowser.open("https://virtualchemlab.readthedocs.io")
        except Exception as e:
            logger.error(f"打开在线文档失败: {e}")


# 全局帮助管理器实例
_help_manager: HelpManager | None = None


def get_help_manager() -> HelpManager:
    """获取全局帮助管理器"""
    global _help_manager
    if _help_manager is None:
        _help_manager = HelpManager()
    return _help_manager
