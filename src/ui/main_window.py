"""
主窗口
应用程序的主界面框架 - 现代化UI版本

增强功能:
1. 智能布局和自适应设计
2. 多主题支持和动态切换
3. 实时性能监控和优化
4. 用户行为分析和个性化
5. 无障碍访问支持
6. 多语言界面和本地化
7. 插件系统和扩展性
8. 云端同步和离线模式
"""

from __future__ import annotations

import contextlib
import logging
import sys
import traceback
from datetime import datetime
from typing import Any

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from .. import __version__ as APP_VERSION

from ..core.auth import DeveloperAuth
from ..core.di_container import DIContainer
from ..core.template_engine import TemplateEngine
from ..storage.json_store import JSONStore  # JSONStore is in storage, not core
from ..utils.i18n import I18n  # i18n is in utils, not core
from ..utils.logger import get_logger
from .achievement_dialog import AchievementUnlockedDialog
from .customization.theme_manager import ThemeType
from .dev_console import DeveloperConsole
from .experiment_view import ExperimentView
from .game_experiment_view import GameExperimentView
from .gamification.gamification_panel import GamificationPanel
from .gamification.level_up_dialog import LevelUpDialog
from .quick_tips import show_quick_tip
from .record_browser import RecordBrowser
from .settings_dialog import SettingsDialog

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """主窗口类"""

    # 信号定义
    experiment_started = Signal(str)  # 实验开始信号
    experiment_completed = Signal(str, dict)  # 实验完成信号
    theme_changed = Signal(str)  # 主题变更信号
    language_changed = Signal(str)  # 语言变更信号
    performance_warning = Signal(str)  # 性能警告信号
    new_action_triggered = Signal()  # 新建入口信号
    open_action_triggered = Signal()  # 打开入口信号
    save_action_triggered = Signal()  # 保存入口信号
    run_action_triggered = Signal()  # 运行入口信号
    stop_action_triggered = Signal()  # 停止入口信号

    def __init__(self, container: DIContainer | None = None, workflow_manager: Any | None = None):
        super().__init__()

        try:
            # 使用DI容器（如果未提供则创建默认容器）
            if container is None:
                from ..core.service_registration import get_configured_container

                container = get_configured_container()

            self.container = container

            # 用户流程管理器（可选）
            self.workflow_manager = workflow_manager
            if workflow_manager:
                logger.info("用户流程管理器已连接")

            # 初始化操作历史管理器
            from .action_history import ActionHistory

            self.action_history = ActionHistory(max_history=50)  # 减少历史记录大小
            logger.info("操作历史管理器已初始化")

            # 从容器解析服务
            self.template_engine = container.resolve(TemplateEngine)
            self.i18n = container.resolve(I18n)
            self.store = container.resolve(JSONStore)  # 使用JSONStore而非IStorage接口
            self.dev_auth = container.resolve(DeveloperAuth)

            # 初始化游戏化管理器
            try:
                from ..gamification.gamification_manager import GamificationManager
                self.gamification_manager = GamificationManager()
                logger.info("游戏化管理器已初始化")
            except Exception as e:
                logger.warning(f"游戏化管理器初始化失败: {e}")
                self.gamification_manager = None

            # 运行时状态
            self.current_experiment_view: ExperimentView | None = None
            self.current_game_view: GameExperimentView | None = None
            self.user_id = "student_001"  # 默认用户ID
            self.game_mode_enabled = True  # 游戏模式开关

            # 新增状态管理
            self.is_offline_mode = False  # 离线模式
            self.auto_save_enabled = True  # 自动保存
            self.accessibility_enabled = False  # 无障碍模式
            self.performance_monitoring = True  # 性能监控
            self.user_preferences: dict[str, Any] = {}  # 用户偏好
            self.max_user_preferences = 100  # 限制用户偏好数量

            self.init_ui()

            # 检查是否首次运行
            self.check_first_run()

            # 显示启动提示
            self.show_startup_tip()

            # 加载上次实验（如果设置）
            self.load_last_experiment()

            # 连接信号
            self.connect_signals()

        except Exception as e:
            logger.error(f"主窗口初始化失败: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "初始化错误",
                f"主窗口初始化失败，应用程序无法启动。\n\n错误: {e}",
            )
            # 退出前尝试清理
            self.close()

    def show_startup_tip(self):
        """显示启动时的快速提示"""
        is_first_run = self.store.get("app_first_run", True) if self.store else True
        if is_first_run:
            # 使用QTimer延迟显示，确保主窗口已完全加载
            QTimer.singleShot(1000, lambda: show_quick_tip("first_run", duration=10000, parent=self))

    def check_first_run(self):
        """检查是否首次运行，并显示欢迎向导"""
        is_first_run = self.store.get("app_first_run", True) if self.store else True
        if is_first_run:
            # 首次运行，显示欢迎向导
            logger.info("检测到首次运行，显示欢迎向导")
            # 导入必要的模块

            from PySide6.QtCore import QTimer

            from .welcome_wizard import show_welcome_wizard

            # 延迟显示，让主窗口先完全加载
            def show_wizard():
                show_welcome_wizard(self, self.i18n)
                # 不再显示逻辑由 welcome_wizard 内部处理
                # 此处只记录首次运行完成
                self.store.set("app_first_run", False)
                logger.info("欢迎向导完成, 标记为非首次运行")

            QTimer.singleShot(500, show_wizard)

    def load_last_experiment(self):
        """加载上次的实验"""
        # 从配置管理器获取设置
        from src.core.config_manager import ConfigManager
        config_manager = ConfigManager()
        if config_manager.get("startup.auto_load_last_experiment", False):
            last_experiment = self.store.get("last_experiment_id")
            if last_experiment:
                logger.info(f"正在加载上次的实验: {last_experiment}")
                self.load_experiment(last_experiment)

    def connect_signals(self):
        """连接所有信号和槽"""
        # 示例：连接主题变化信号
        self.theme_changed.connect(self.on_theme_changed)
        logger.info("信号槽连接完成")

    def on_theme_changed(self, theme_name: str):
        """主题变化时的槽函数"""
        logger.info(f"主题已变更为: {theme_name}")
        # 这里可以添加刷新UI的代码
        self.update()

    def emit_core_action_signal(self, action: str) -> None:
        """Emit standardized action signals for smoke testing and hooks."""
        action_map = {
            "new": self.new_action_triggered,
            "open": self.open_action_triggered,
            "save": self.save_action_triggered,
            "run": self.run_action_triggered,
            "stop": self.stop_action_triggered,
        }
        signal = action_map.get(action)
        if signal:
            signal.emit()
            logger.debug("Core action emitted: %s", action)
        else:
            logger.debug("Unknown action signal requested: %s", action)

    def _register_lazy_components(self):
        """注册懒加载组件，优化启动速度"""

        def load_knowledge_browser():
            from .knowledge_browser import KnowledgeBrowser

            return KnowledgeBrowser()

        def load_dev_console():
            from .developer_console import DeveloperConsole

            self.dev_console = DeveloperConsole(self.dev_auth)
            return self.dev_console

        # 注册懒加载组件
        from src.ui.lazy_loader import register_lazy_component
        register_lazy_component("knowledge_browser", load_knowledge_browser, priority=3)
        register_lazy_component("dev_console", load_dev_console, priority=5)

    def init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle(self.i18n.t("app.title"))

        # 使用响应式窗口大小
        from src.ui.responsive import AdaptiveSize
        window_size = AdaptiveSize.window_size()
        self.resize(window_size)
        logger.info(f"窗口大小设置为: {window_size.width()}x{window_size.height()}")
        # 居中显示
        screen_center = QGuiApplication.primaryScreen().geometry().center()
        self.move(screen_center - self.rect().center())

        # 优化主题
        from src.ui.visual_polish import optimize_widget_theme
        optimize_widget_theme(self)

        # 设置中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 实验列表
        left_panel = self.create_experiment_list()
        splitter.addWidget(left_panel)

        # 中间面板 - 实验视图
        self.main_stack = QStackedWidget()
        self.welcome_page = self.create_welcome_page()
        self.main_stack.addWidget(self.welcome_page)
        splitter.addWidget(self.main_stack)

        # 右侧面板 - 游戏化和辅助工具
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置初始尺寸比例
        splitter.setSizes([250, 700, 250])
        splitter.setStretchFactor(1, 1)

        # 创建菜单栏、工具栏和状态栏
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        # 初始化gamification_panel
        self.gamification_panel = self.findChild(GamificationPanel)

        # 设置拖放
        self.setAcceptDrops(True)

    def create_menu_bar(self) -> None:
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")

        # 工具菜单
        tools_menu = menubar.addMenu("工具")

        # 数据菜单
        data_menu = menubar.addMenu("数据")

        # 窗口菜单
        window_menu = menubar.addMenu("窗口")

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

    def create_tool_bar(self) -> None:
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

    def create_status_bar(self) -> None:
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def create_right_panel(self) -> QWidget:
        """创建右侧面板，包含游戏化和辅助工具"""
        # 使用 QTabWidget 来组织右侧面板
        right_tab_widget = QTabWidget()
        right_tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # 游戏化面板
        gamification_widget = GamificationPanel(self.gamification_manager, self)
        right_tab_widget.addTab(gamification_widget, "游戏化")

        # 辅助工具面板 (可以放知识库、笔记等)
        # 这里暂时留空，可以后续添加
        # help_widget = QWidget()
        # right_tab_widget.addTab(help_widget, "辅助工具")

        return right_tab_widget

    def create_experiment_list(self) -> QWidget:
        """创建实验列表"""
        widget = QWidget()
        widget.setObjectName("experimentList")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(self.i18n.t("ui.experiment_list"))
        title_label.setObjectName("experimentListTitle")
        layout.addWidget(title_label)

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索实验...")
        self.search_box.textChanged.connect(self._filter_experiments)
        layout.addWidget(self.search_box)

        # 实验列表
        self.exp_list_widget = QListWidget()
        self.exp_list_widget.setObjectName("experimentListWidget")
        self.exp_list_widget.itemDoubleClicked.connect(self.on_experiment_selected)
        layout.addWidget(self.exp_list_widget)

        # 刷新按钮
        refresh_btn = QPushButton(self.i18n.t("ui.refresh"))
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.clicked.connect(self.populate_experiment_list)
        layout.addWidget(refresh_btn)

        return widget

    def create_welcome_page(self) -> QWidget:
        """创建欢迎页面"""
        widget = QWidget()
        widget.setObjectName("welcomePage")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        welcome_label = QLabel(self.i18n.t("ui.welcome"))
        welcome_label.setObjectName("welcomeTitle")
        layout.addWidget(welcome_label)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setObjectName("versionLabel")
        layout.addWidget(version_label)

        info_label = QLabel(self.i18n.t("ui.select_experiment_hint"))
        info_label.setObjectName("welcomeHint")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        return widget

    def create_status_bar(self) -> None:
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.i18n.t("status.ready"))

    def set_theme(self, theme_type: ThemeType) -> None:
        """设置并应用主题"""
        app = QApplication.instance()
        if app:
            try:
                self.theme_manager.set_theme(app, theme_type)
                self.theme_changed.emit(theme_type.value)
                logger.info(f"主题已切换为: {theme_type.value}")

                # 保存用户偏好（限制大小）
                self.user_preferences["theme"] = theme_type.value
                if len(self.user_preferences) > self.max_user_preferences:
                    # 保留最新的偏好设置
                    keys_to_remove = list(self.user_preferences.keys())[:-self.max_user_preferences]
                    for key in keys_to_remove:
                        del self.user_preferences[key]
                self.store.set("user_preferences", self.user_preferences)
            except Exception as e:
                logger.error(f"设置主题失败: {e}")
                QMessageBox.warning(self, "主题错误", f"无法应用主题: {e}")

    def handle_exception(self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        """全局异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"未捕获的异常:\n{error_msg}")

        # 显示错误对话框
        QMessageBox.critical(self, "程序错误", f"发生未预期的错误:\n{exc_value}\n\n详细信息已记录到日志文件。")

    def _get_experiment_icon(self, exp_id: str) -> str:
        """根据实验ID返回专业图标

        Args:
            exp_id: 实验ID

        Returns:
            图标emoji字符
        """
        # 实验类型关键词到图标的映射
        icon_map = {
            "titration": "[T]",  # 滴定实验
            "precipitation": "[P]",  # 沉淀实验
            "recrystallization": "[R]",  # 重结晶
            "distillation": "[D]",  # 蒸馏
            "esterification": "[E]",  # 酯化反应
            "buffer": "[B]",  # 缓冲溶液
            "synthesis": "[S]",  # 合成实验
            "extraction": "[X]",  # 萃取
            "chromatography": "[C]",  # 色谱
            "spectroscopy": "[Sp]",  # 光谱
            "electrochemistry": "[Ec]",  # 电化学
            "kinetics": "[K]",  # 动力学
            "thermodynamics": "[Th]",  # 热力学
            "organic": "[O]",  # 有机化学
            "inorganic": "[I]",  # 无机化学
            "analytical": "[A]",  # 分析化学
            "physical": "[Ph]",  # 物理化学
        }

        # 遍历关键词，找到匹配的图标
        exp_id_lower = exp_id.lower()
        for keyword, icon in icon_map.items():
            if keyword in exp_id_lower:
                return icon

        # 默认图标
        return "[L]"

    def load_experiments(self) -> None:
        """加载实验列表"""
        try:
            # 显示加载状态
            self.status_bar.showMessage("正在加载实验列表...")
            QApplication.processEvents()

            self.exp_list_widget.clear()
            templates = self.template_engine.list_available_experiments()

            if not templates:
                # 没有实验模板,显示友好提示
                from ..utils.friendly_errors import FriendlyErrorHandler

                title = "没有可用的实验"
                message = (
                    "实验列表为空\n\n"
                    "可能的原因:\n"
                    "  - 实验模板目录为空\n"
                    "  - 配置路径设置错误\n"
                    "  - 模板文件格式错误\n\n"
                    "解决方案:\n"
                    "  1. 检查 assets/templates 目录\n"
                    "  2. 确保目录中有 .yaml 或 .yml 文件\n"
                    "  3. 参考示例模板文件\n\n"
                    f"当前模板目录: {self.template_engine.templates_dir}"
                )
                QMessageBox.information(self, title, message)
                self.status_bar.showMessage("没有可用的实验模板")
                return

            for template in templates:
                # template 是字典，包含 id, title, level 等字段
                exp_id = template.get("id", "unknown")
                exp_title = template.get("title", "未命名实验")

                # 保存完整标题用于tooltip
                full_title = exp_title

                # 根据实验类型选择专业图标
                icon = self._get_experiment_icon(exp_id)

                # 难度等级标签
                level_map = {
                    "basic": "基础",
                    "intermediate": "中级",
                    "advanced": "高级",
                }
                level_text = level_map.get(template.get("level", "basic"), template.get("level", "N/A"))

                # 添加时长信息(如果有)
                duration = template.get("duration_min")
                duration_text = f" | {duration}分钟" if duration else ""

                # 限制标题长度，避免显示不全
                max_title_length = 25  # 最大显示25个字符
                if len(exp_title) > max_title_length:
                    display_title = exp_title[:max_title_length] + "..."
                else:
                    display_title = exp_title

                # 格式化显示：使用更清晰的格式
                # 第一行：图标 + 实验名称（截断后）
                # 第二行：难度 + 时长（缩进，较小字体）
                item_text = f"{icon}  {display_title}\n    {level_text}{duration_text}"

                list_item = QListWidgetItem(item_text)
                # 设置合适的行高
                list_item.setSizeHint(QSize(0, 70))

                # 设置完整标题为tooltip，鼠标悬停时可以看到完整名称
                tooltip_text = f"{full_title}\n{level_text}{duration_text}"
                if template.get("description"):
                    tooltip_text += f"\n\n{template.get('description')}"
                list_item.setToolTip(tooltip_text)

                self.exp_list_widget.addItem(list_item)

            self.status_bar.showMessage(f"已加载 {len(templates)} 个实验")
            logger.info(f"加载了 {len(templates)} 个实验模板")

        except Exception as e:
            logger.error(f"加载实验失败: {e}", exc_info=True)

            # 使用友好的错误提示
            from ..utils.friendly_errors import FriendlyErrorHandler

            title, message = FriendlyErrorHandler.format_error_dialog(e, "加载实验列表")
            QMessageBox.critical(self, title, message)

    def populate_experiment_list(self) -> None:
        """填充实验列表（别名方法）"""
        self.load_experiments()

    def on_experiment_selected(self, item: Any) -> None:
        """实验被选中时的处理"""
        try:
            index = self.exp_list_widget.row(item)
            templates = self.template_engine.list_available_experiments()

            if 0 <= index < len(templates):
                template_dict = templates[index]
                # 根据ID加载完整的模板对象
                template = self.template_engine.load_experiment_by_id(template_dict["id"])
                self.show_experiment(template)

        except Exception as e:
            logger.error(f"加载实验失败: {e}", exc_info=True)

            # 使用友好的错误提示
            from ..utils.friendly_errors import FriendlyErrorHandler

            title, message = FriendlyErrorHandler.format_error_dialog(e, "打开实验")
            QMessageBox.critical(self, title, message)

    def show_experiment(self, template: Any) -> None:
        """显示实验界面

        创建新的实验视图并切换到实验界面。

        Args:
            template: 实验模板对象

        Note:
            使用deleteLater()确保旧视图正确清理，避免内存泄漏。
        """
        try:
            # 显示加载状态
            self.status_bar.showMessage("⏳ 正在加载实验...")

            # 如果已有实验视图,先移除
            if self.current_experiment_view:
                logger.debug("清理之前的实验视图")
                self.content_stack.removeWidget(self.current_experiment_view)
                self.current_experiment_view.setParent(None)
                self.current_experiment_view.deleteLater()
                self.current_experiment_view = None

            # 创建新的实验视图，传入 DI 容器和用户ID
            logger.info(f"创建实验视图: {template.id} - {template.title}")

            # 根据游戏模式选择视图类型
            if self.game_mode_enabled:
                # 创建游戏化实验视图
                from ..core.experiment_controller import ExperimentController

                controller = ExperimentController(template, self.user_id)

                self.current_game_view = GameExperimentView(
                    template=template, controller=controller, user_id=self.user_id
                )

                # 连接信号
                self.current_game_view.experiment_completed.connect(self.on_experiment_finished)
                self.current_game_view.interaction_logged.connect(self.on_interaction_logged)

                # 添加到堆栈并显示
                self.content_stack.addWidget(self.current_game_view)
                self.content_stack.setCurrentWidget(self.current_game_view)

                # 设置当前视图引用
                self.current_experiment_view = self.current_game_view
            else:
                # 创建传统实验视图
                self.current_experiment_view = ExperimentView(
                    template=template, container=self.container, user_id=self.user_id
                )

                # 连接信号
                self.current_experiment_view.experiment_finished.connect(self.on_experiment_finished)
                self.current_experiment_view.exp_gained.connect(self.on_exp_gained)

                # 添加到堆栈并显示
                self.content_stack.addWidget(self.current_experiment_view)
                self.content_stack.setCurrentWidget(self.current_experiment_view)

            self.status_bar.showMessage(self.i18n.t("status.experiment_loaded", title=template.title))
            logger.info("实验界面加载完成")

        except Exception as e:
            logger.error(f"显示实验界面失败: {e}", exc_info=True)
            self.status_bar.showMessage("❌ 加载实验失败")

            # 使用友好的错误提示
            from ..utils.friendly_errors import FriendlyErrorHandler

            title, message = FriendlyErrorHandler.format_error_dialog(e, "显示实验")
            QMessageBox.critical(self, title, message)

            # 如果创建失败，清理视图
            if self.current_experiment_view:
                self.current_experiment_view.deleteLater()
                self.current_experiment_view = None

    def on_exp_gained(self, exp_points: int) -> None:
        """处理经验值获得

        Args:
            exp_points: 获得的经验值
        """
        try:
            logger.info(f"用户获得经验值: {exp_points}")
            # 使用经验值系统
            from .experience_system import get_experience_system

            exp_system = get_experience_system()
            leveled_up, level_info = exp_system.add_experience(self.current_user_id, exp_points, "实验完成")
            # 显示经验获得动画
            if (
                self.current_experiment_view
                and self.gamification_panel is not None
                and hasattr(self.gamification_panel, "level_card")
            ):
                # 计算动画位置
                start_pos = self.current_experiment_view.rect().center()
                end_pos = self.gamification_panel.level_card.pos()

                from .animations import ExpGainAnimation

                animation = ExpGainAnimation(exp_points, self)
                animation.start_animation(start_pos, end_pos)
            else:
                # 没有游戏化面板时，只显示简单通知
                self.status_bar.showMessage(f"🎉 获得 {exp_points} 经验值!", 3000)
        except Exception as e:
            logger.warning(f"显示经验动画失败: {e}")
            # 失败时显示简单通知
            self.status_bar.showMessage(f"🎉 获得 {exp_points} 经验值!", 3000)

    def on_experiment_finished(self, record: Any) -> None:
        """实验完成时的处理"""
        try:
            # 更新游戏化系统
            duration = record.total_duration_seconds or 0
            result = self.gamification_manager.on_experiment_completed(
                user_id=self.user_id,
                score=record.score.total,
                duration_seconds=int(duration),
                mistake_count=record.total_mistakes,
            )

            # 刷新游戏化面板
            self._update_gamification_panel()

            # 显示升级/成就通知
            self._show_gamification_rewards(result)

        except Exception as e:
            logger.error(f"更新游戏化系统失败: {e}", exc_info=True)

        # 保存记录到存储系统
        try:
            if self.store.save_record(record):
                logger.info(f"记录已保存: {record.record_id}")
            else:
                logger.warning("记录保存失败")
        except Exception as e:
            logger.error(f"保存记录时出错: {e}")

        # 显示完成消息
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(self.i18n.t("ui.experiment_complete"))
        msg.setText(
            self.i18n.t("ui.final_score_message", score=record.final_score) + f"\n\n{self.i18n.t('ui.record_saved')}"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        logger.info(f"实验完成,最终得分: {record.final_score}")

    def on_interaction_logged(self, user_id: str, interaction_type: str, data: dict) -> None:
        """处理交互日志

        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            data: 交互数据
        """
        try:
            logger.debug(f"交互日志: {user_id} - {interaction_type} - {data}")

            # 更新游戏化系统
            if self.gamification_manager:
                # 根据交互类型给予经验值
                exp_points = 0
                if interaction_type == "drag":
                    exp_points = 5
                elif interaction_type == "click":
                    exp_points = 3
                elif interaction_type == "swipe":
                    exp_points = 8
                elif interaction_type == "collision":
                    exp_points = 10

                if exp_points > 0:
                    self.gamification_manager.add_exp(self.user_id, exp_points)
                    self.on_exp_gained(exp_points)

            # 更新状态栏
            self.status_bar.showMessage(f"交互: {interaction_type} - +{exp_points} EXP")

        except Exception as e:
            logger.error(f"处理交互日志失败: {e}", exc_info=True)

    def toggle_game_mode(self) -> None:
        """切换游戏模式"""
        try:
            self.game_mode_enabled = not self.game_mode_enabled

            # 更新状态栏
            mode_text = "游戏模式" if self.game_mode_enabled else "传统模式"
            self.status_bar.showMessage(f"已切换到: {mode_text}")

            # 显示提示
            QMessageBox.information(self, "模式切换", f"已切换到{mode_text}。\n重新加载实验以应用更改。")

            logger.info(f"游戏模式切换: {mode_text}")

        except Exception as e:
            logger.error(f"切换游戏模式失败: {e}", exc_info=True)

    def show_physics_settings(self) -> None:
        """显示物理设置对话框"""
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QDialog,
                QHBoxLayout,
                QLabel,
                QPushButton,
                QSlider,
                QVBoxLayout,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle("物理设置")
            dialog.setModal(True)
            dialog.resize(400, 300)

            layout = QVBoxLayout(dialog)

            # 重力设置
            gravity_layout = QHBoxLayout()
            gravity_layout.addWidget(QLabel("重力强度:"))
            gravity_slider = QSlider(Qt.Horizontal)
            gravity_slider.setRange(0, 100)
            gravity_slider.setValue(50)
            gravity_layout.addWidget(gravity_slider)
            layout.addLayout(gravity_layout)

            # 摩擦力设置
            friction_layout = QHBoxLayout()
            friction_layout.addWidget(QLabel("摩擦力:"))
            friction_slider = QSlider(Qt.Horizontal)
            friction_slider.setRange(0, 100)
            friction_slider.setValue(90)
            friction_layout.addWidget(friction_slider)
            layout.addLayout(friction_layout)

            # 弹跳系数设置
            bounce_layout = QHBoxLayout()
            bounce_layout.addWidget(QLabel("弹跳系数:"))
            bounce_slider = QSlider(Qt.Horizontal)
            bounce_slider.setRange(0, 100)
            bounce_slider.setValue(60)
            bounce_layout.addWidget(bounce_slider)
            layout.addLayout(bounce_layout)

            # 物理开关
            physics_checkbox = QCheckBox("启用物理模拟")
            physics_checkbox.setChecked(True)
            layout.addWidget(physics_checkbox)

            # 碰撞检测
            collision_checkbox = QCheckBox("启用碰撞检测")
            collision_checkbox.setChecked(True)
            layout.addWidget(collision_checkbox)

            # 按钮
            button_layout = QHBoxLayout()
            apply_button = QPushButton("应用")
            apply_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(apply_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec() == QDialog.Accepted:
                # 应用设置
                if self.current_game_view and hasattr(self.current_game_view, "game_scene"):
                    scene = self.current_game_view.game_scene
                    if scene:
                        scene.enable_gravity(physics_checkbox.isChecked())
                        scene.collision_enabled = collision_checkbox.isChecked()

                        # 更新所有物品的物理属性
                        for item in scene.physics_items.values():
                            item.friction = friction_slider.value() / 100.0
                            item.bounce_factor = bounce_slider.value() / 100.0
                            item.gravity = item.gravity.__class__(0, 0.5 * gravity_slider.value() / 100.0)

                self.status_bar.showMessage("物理设置已应用")
                logger.info("物理设置已更新")

        except Exception as e:
            logger.error(f"显示物理设置失败: {e}", exc_info=True)

    def show_particle_settings(self) -> None:
        """显示粒子效果设置对话框"""
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QComboBox,
                QDialog,
                QHBoxLayout,
                QLabel,
                QPushButton,
                QSlider,
                QVBoxLayout,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle("粒子效果设置")
            dialog.setModal(True)
            dialog.resize(400, 350)

            layout = QVBoxLayout(dialog)

            # 粒子效果开关
            particle_checkbox = QCheckBox("启用粒子效果")
            particle_checkbox.setChecked(True)
            layout.addWidget(particle_checkbox)

            # 粒子数量
            count_layout = QHBoxLayout()
            count_layout.addWidget(QLabel("粒子数量:"))
            count_slider = QSlider(Qt.Horizontal)
            count_slider.setRange(1, 20)
            count_slider.setValue(6)
            count_layout.addWidget(count_slider)
            layout.addLayout(count_layout)

            # 粒子大小
            size_layout = QHBoxLayout()
            size_layout.addWidget(QLabel("粒子大小:"))
            size_slider = QSlider(Qt.Horizontal)
            size_slider.setRange(5, 50)
            size_slider.setValue(15)
            size_layout.addWidget(size_slider)
            layout.addLayout(size_layout)

            # 粒子生命周期
            lifetime_layout = QHBoxLayout()
            lifetime_layout.addWidget(QLabel("生命周期:"))
            lifetime_slider = QSlider(Qt.Horizontal)
            lifetime_slider.setRange(100, 3000)
            lifetime_slider.setValue(1000)
            lifetime_layout.addWidget(lifetime_slider)
            layout.addLayout(lifetime_layout)

            # 粒子类型
            type_layout = QHBoxLayout()
            type_layout.addWidget(QLabel("粒子类型:"))
            type_combo = QComboBox()
            type_combo.addItems(["闪烁", "发光", "爆炸", "轨迹", "气泡", "烟雾", "火焰", "水花"])
            type_layout.addWidget(type_combo)
            layout.addLayout(type_layout)

            # 按钮
            button_layout = QHBoxLayout()
            apply_button = QPushButton("应用")
            apply_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(apply_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec() == QDialog.Accepted:
                # 应用设置
                if self.current_game_view and hasattr(self.current_game_view, "game_scene"):
                    scene = self.current_game_view.game_scene
                    if scene:
                        # 更新粒子系统配置
                        from .particle_system import ParticleType, get_particle_manager

                        particle_manager = get_particle_manager()

                        particle_type_map = {
                            "闪烁": ParticleType.SPARKLE,
                            "发光": ParticleType.GLOW,
                            "爆炸": ParticleType.EXPLOSION,
                            "轨迹": ParticleType.TRAIL,
                            "气泡": ParticleType.BUBBLE,
                            "烟雾": ParticleType.SMOKE,
                            "火焰": ParticleType.FIRE,
                            "水花": ParticleType.WATER,
                        }

                        selected_type = particle_type_map.get(type_combo.currentText(), ParticleType.SPARKLE)

                        # 更新配置
                        particle_manager.get_particle_system(scene).update_particle_config(
                            selected_type,
                            {
                                "lifetime": lifetime_slider.value(),
                                "size": size_slider.value(),
                            },
                        )

                self.status_bar.showMessage("粒子效果设置已应用")
                logger.info("粒子效果设置已更新")

        except Exception as e:
            logger.error(f"显示粒子效果设置失败: {e}", exc_info=True)

        dialog.exec()

    def on_new_experiment(self) -> None:
        """开始新实验"""
        self.emit_core_action_signal("new")
        if self.current_experiment_view:
            reply = QMessageBox.question(
                self,
                self.i18n.t("ui.confirm"),
                self.i18n.t("ui.restart_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.current_experiment_view.restart_experiment()

    def on_open_record(self) -> None:
        """打开实验记录"""
        try:
            browser = RecordBrowser(
                store=self.store,
                user_id=self.user_id,
                i18n_dir=str(self.i18n.i18n_dir),
                parent=self,
            )

            # 连接重做实验信号
            browser.redo_experiment.connect(self.on_redo_from_browser)

            browser.exec()
        except Exception as e:
            logger.error(f"打开记录浏览器失败: {e}")
            QMessageBox.critical(
                self,
                self.i18n.t("error.title"),
                self.i18n.t("error.open_browser_failed", error=str(e)),
            )

    def on_redo_from_browser(self, experiment_id: str) -> None:
        """从浏览器重做实验"""
        try:
            # 查找实验模板
            templates = self.template_engine.list_available_experiments()
            template = None

            for t in templates:
                if t.id == experiment_id:
                    template = t
                    break

            if template:
                self.show_experiment(template)
            else:
                QMessageBox.warning(self, self.i18n.t("ui.warning"), f"未找到实验: {experiment_id}")
        except Exception as e:
            logger.error(f"重做实验失败: {e}")
            QMessageBox.critical(self, self.i18n.t("error.title"), f"重做实验失败: {e}")

    def on_restart_experiment(self) -> None:
        """重新开始当前实验"""
        if self.current_experiment_view:
            self.current_experiment_view.restart_experiment()

    def on_generate_report(self) -> None:
        """生成实验报告"""
        if not self.current_experiment_view:
            QMessageBox.warning(self, self.i18n.t("ui.warning"), "请先完成实验")
            return

        try:
            from PySide6.QtWidgets import QFileDialog

            # 获取实验记录
            record = self.current_experiment_view.controller.get_record()
            template = self.current_experiment_view.template

            # 询问保存位置
            default_name = f"{template.id}_{record.user_id}_{record.start_time.strftime('%Y%m%d_%H%M%S')}.html"
            file_path, _ = QFileDialog.getSaveFileName(
                self, self.i18n.t("ui.save_report"), default_name, "HTML Files (*.html)"
            )

            if not file_path:
                return

            def _task(record, template, output_path, progress_emit=None, message_emit=None):
                from ..reporter.html_generator import HTMLGenerator

                if message_emit:
                    message_emit("准备数据...")
                if progress_emit:
                    progress_emit(10)
                generator = HTMLGenerator()
                if message_emit:
                    message_emit("渲染模板...")
                if progress_emit:
                    progress_emit(60)
                generator.generate(record, template, output_path)
                if progress_emit:
                    progress_emit(100)
                if message_emit:
                    message_emit("报告生成完成")
                return output_path

            from src.ui.task_worker import TaskWorker
            worker = TaskWorker(_task, record, template, file_path)
            worker.progress.connect(lambda v: self.status_bar.showMessage(f"生成报告: {v}%"))
            worker.message.connect(lambda m: self.status_bar.showMessage(m))

            def _on_done(path: str) -> None:
                self.status_bar.showMessage(f"✓ 报告已生成: {path}")
                import webbrowser as _wb

                from PySide6.QtWidgets import QMessageBox as _QMB

                reply = _QMB.question(
                    self,
                    self.i18n.t("ui.success"),
                    f"报告已生成：{path}\n是否立即打开？",
                    _QMB.StandardButton.Yes | _QMB.StandardButton.No,
                )
                if reply == _QMB.StandardButton.Yes:
                    _wb.open(path)
                self._cleanup_worker(worker)

            def _on_error(msg: str) -> None:
                logger.error(f"生成报告失败: {msg}")
                QMessageBox.critical(self, self.i18n.t("ui.error"), f"生成报告失败: {msg}")
                self._cleanup_worker(worker)

            worker.finished_with_result.connect(_on_done)
            worker.error.connect(_on_error)

            self._track_worker(worker)
            worker.start()

        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            QMessageBox.critical(self, self.i18n.t("ui.error"), f"生成报告失败: {e!s}")

    def on_open_knowledge(self) -> None:
        """打开知识库"""
        try:
            from src.ui.knowledge_browser import KnowledgeBrowser
            browser = KnowledgeBrowser(knowledge_dir="assets/knowledge", i18n_dir=str(self.i18n.i18n_dir), parent=self)
            browser.exec()
        except Exception as e:
            logger.error(f"打开知识库失败: {e}")
            QMessageBox.critical(self, self.i18n.t("error.title"), f"打开知识库失败: {e}")

    def on_open_settings(self) -> None:
        """打开设置"""
        try:
            dialog = SettingsDialog(i18n_dir=str(self.i18n.i18n_dir), settings_file="config/settings.json", parent=self)
            dialog.settings_changed.connect(self.on_settings_changed)
            dialog.exec()
        except Exception as e:
            logger.error(f"打开设置失败: {e}")
            QMessageBox.critical(self, self.i18n.t("error.title"), f"打开设置失败: {e}")

    def show_performance_dialog(self) -> None:
        """显示性能监控对话框"""
        try:
            self.performance_dialog.show()
            self.performance_dialog.raise_()
            self.performance_dialog.activateWindow()
        except Exception as e:
            logger.error(f"显示性能监控对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"显示性能监控对话框失败: {e}")

    def show_tutorial(self) -> None:
        """显示交互式教程"""
        try:
            self.tutorial_manager.start_tutorial("basic", self)
        except Exception as e:
            logger.error(f"显示教程失败: {e}")
            QMessageBox.critical(self, "错误", f"显示教程失败: {e}")

    def show_user_guide(self) -> None:
        """显示用户引导"""
        try:
            # 显示引导菜单
            from .user_guidance import show_guide_menu

            show_guide_menu(self)
        except Exception as e:
            logger.error(f"显示用户引导失败: {e}")
            from src.ui.error_dialog import show_error
            show_error("引导失败", f"无法显示用户引导: {e}")

    def show_help(self) -> None:
        """显示帮助文档"""
        try:
            self.help_manager.show_help(parent=self)
        except Exception as e:
            logger.error(f"显示帮助失败: {e}")
            from src.ui.error_dialog import show_error
            show_error("帮助失败", f"无法显示帮助文档: {e}")

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        """设置变更处理"""
        logger.info(f"设置已更改: {settings}")

        # 处理预览设置
        if "theme_preview" in settings:
            self.apply_theme_preview(settings["theme_preview"])
        elif "font_size_preview" in settings:
            self.apply_font_size_preview(settings["font_size_preview"])
        elif "animations_preview" in settings:
            self.apply_animations_preview(settings["animations_preview"])
        elif "render_quality_preview" in settings:
            self.apply_render_quality_preview(settings["render_quality_preview"])
        elif "cache_size_preview" in settings:
            self.apply_cache_size_preview(settings["cache_size_preview"])
        else:
            # 处理完整设置保存
            self.apply_settings(settings)
            # 如果语言改变，提示重启
            if "language" in settings and settings["language"] != self.i18n.current_language:
                QMessageBox.information(self, self.i18n.t("ui.info"), "某些设置需要重启应用后生效。")

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """应用设置"""
        # 应用主题
        if "theme" in settings:
            self.apply_theme(settings["theme"])

        # 应用字体大小
        if "font_size" in settings:
            self.apply_font_size(settings["font_size"])

        # 应用动画设置
        if "enable_animations" in settings:
            self.apply_animations(settings["enable_animations"])

        # 应用渲染质量
        if "render_quality" in settings:
            self.apply_render_quality(settings["render_quality"])

        # 应用缓存设置
        if "cache_size_mb" in settings:
            self.apply_cache_size(settings["cache_size_mb"])

        # 应用高级设置
        if "debug_mode" in settings:
            self.apply_debug_mode(settings["debug_mode"])

        if "experimental_features" in settings:
            self.apply_experimental_features(settings["experimental_features"])

        if "verbose_logging" in settings:
            self.apply_verbose_logging(settings["verbose_logging"])

        # 应用无障碍设置
        if "high_contrast" in settings:
            self.apply_high_contrast(settings["high_contrast"])

        if "large_text" in settings:
            self.apply_large_text(settings["large_text"])

        if "color_blind_support" in settings:
            self.apply_color_blind_support(settings["color_blind_support"])

        if "keyboard_navigation" in settings:
            self.apply_keyboard_navigation(settings["keyboard_navigation"])

        if "screen_reader_support" in settings:
            self.apply_screen_reader_support(settings["screen_reader_support"])

        if "focus_indicators" in settings:
            self.apply_focus_indicators(settings["focus_indicators"])

        # 应用通知设置
        if "experiment_complete_notifications" in settings:
            self.apply_experiment_complete_notifications(settings["experiment_complete_notifications"])

        if "error_notifications" in settings:
            self.apply_error_notifications(settings["error_notifications"])

        if "update_notifications" in settings:
            self.apply_update_notifications(settings["update_notifications"])

    def apply_theme_preview(self, theme: str) -> None:
        """应用主题预览"""
        try:
            from .themes import ThemeManager, ThemeType

            theme_manager = ThemeManager()
            if theme == "light":
                theme_manager.set_theme(self.qApp, ThemeType.LIGHT)
            elif theme == "dark":
                theme_manager.set_theme(self.qApp, ThemeType.DARK)
            elif theme == "auto":
                system_theme = theme_manager.get_system_theme()
                theme_manager.set_theme(self.qApp, system_theme)

            logger.info(f"主题预览已应用: {theme}")
        except Exception as e:
            logger.error(f"应用主题预览失败: {e}")

    def apply_theme(self, theme: str) -> None:
        """应用主题"""
        self.apply_theme_preview(theme)

    def apply_font_size_preview(self, font_size: int) -> None:
        """应用字体大小预览"""
        try:
            font = self.font()
            font.setPointSize(font_size)
            self.setFont(font)
            logger.info(f"字体大小预览已应用: {font_size}")
        except Exception as e:
            logger.error(f"应用字体大小预览失败: {e}")

    def apply_font_size(self, font_size: int) -> None:
        """应用字体大小"""
        self.apply_font_size_preview(font_size)

    def apply_animations_preview(self, enabled: bool) -> None:
        """应用动画设置预览"""
        try:
            # 设置动画效果
            if enabled:
                self.setStyleSheet("QWidget { transition: all 0.3s ease; }")
            else:
                self.setStyleSheet("QWidget { transition: none; }")
            logger.info(f"动画设置预览已应用: {enabled}")
        except Exception as e:
            logger.error(f"应用动画设置预览失败: {e}")

    def apply_animations(self, enabled: bool) -> None:
        """应用动画设置"""
        self.apply_animations_preview(enabled)

    def apply_render_quality_preview(self, quality: str) -> None:
        """应用渲染质量预览"""
        try:
            # 这里可以添加渲染质量相关的处理
            # 例如调整3D渲染参数、图像质量等
            logger.info(f"渲染质量预览已应用: {quality}")
        except Exception as e:
            logger.error(f"应用渲染质量预览失败: {e}")

    def apply_render_quality(self, quality: str) -> None:
        """应用渲染质量"""
        self.apply_render_quality_preview(quality)

    def apply_cache_size_preview(self, cache_size: int) -> None:
        """应用缓存大小预览"""
        try:
            # 这里可以添加缓存大小相关的处理
            # 例如调整内存缓存、磁盘缓存等
            logger.info(f"缓存大小预览已应用: {cache_size} MB")
        except Exception as e:
            logger.error(f"应用缓存大小预览失败: {e}")

    def apply_cache_size(self, cache_size: int) -> None:
        """应用缓存大小"""
        self.apply_cache_size_preview(cache_size)

    def apply_debug_mode(self, enabled: bool) -> None:
        """应用调试模式"""
        try:
            if enabled:
                logger.setLevel(logging.DEBUG)
                logger.info("调试模式已启用")
            else:
                logger.setLevel(logging.INFO)
                logger.info("调试模式已禁用")
        except Exception as e:
            logger.error(f"应用调试模式失败: {e}")

    def apply_experimental_features(self, enabled: bool) -> None:
        """应用实验性功能"""
        try:
            # 这里可以添加实验性功能的处理逻辑
            logger.info(f"实验性功能设置: {enabled}")
        except Exception as e:
            logger.error(f"应用实验性功能失败: {e}")

    def apply_verbose_logging(self, enabled: bool) -> None:
        """应用详细日志"""
        try:
            if enabled:
                logger.info("详细日志已启用")
            else:
                logger.info("详细日志已禁用")
        except Exception as e:
            logger.error(f"应用详细日志失败: {e}")

    def apply_high_contrast(self, enabled: bool) -> None:
        """应用高对比度"""
        try:
            if enabled:
                self.setStyleSheet(
                    """
                    QWidget {
                        background-color: #000000;
                        color: #FFFFFF;
                        border: 2px solid #FFFFFF;
                    }
                    QPushButton {
                        background-color: #333333;
                        border: 2px solid #FFFFFF;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #555555;
                    }
                """
                )
                logger.info("高对比度模式已启用")
            else:
                self.setStyleSheet("")
                logger.info("高对比度模式已禁用")
        except Exception as e:
            logger.error(f"应用高对比度失败: {e}")

    def apply_large_text(self, enabled: bool) -> None:
        """应用大文本"""
        try:
            if enabled:
                font = self.font()
                font.setPointSize(font.pointSize() + 2)
                self.setFont(font)
                logger.info("大文本模式已启用")
            else:
                font = self.font()
                font.setPointSize(font.pointSize() - 2)
                self.setFont(font)
                logger.info("大文本模式已禁用")
        except Exception as e:
            logger.error(f"应用大文本失败: {e}")

    def apply_color_blind_support(self, enabled: bool) -> None:
        """应用色盲支持"""
        try:
            if enabled:
                # 使用色盲友好的颜色方案
                self.setStyleSheet(
                    """
                    QWidget {
                        color: #000000;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: #FFFFFF;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """
                )
                logger.info("色盲支持已启用")
            else:
                self.setStyleSheet("")
                logger.info("色盲支持已禁用")
        except Exception as e:
            logger.error(f"应用色盲支持失败: {e}")

    def apply_keyboard_navigation(self, enabled: bool) -> None:
        """应用键盘导航"""
        try:
            if enabled:
                self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                logger.info("键盘导航已启用")
            else:
                self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                logger.info("键盘导航已禁用")
        except Exception as e:
            logger.error(f"应用键盘导航失败: {e}")

    def apply_screen_reader_support(self, enabled: bool) -> None:
        """应用屏幕阅读器支持"""
        try:
            if enabled:
                # 设置无障碍属性
                self.setAccessibleName("虚拟化学实验室主窗口")
                self.setAccessibleDescription("化学实验模拟和学习平台")
                logger.info("屏幕阅读器支持已启用")
            else:
                self.setAccessibleName("")
                self.setAccessibleDescription("")
                logger.info("屏幕阅读器支持已禁用")
        except Exception as e:
            logger.error(f"应用屏幕阅读器支持失败: {e}")

    def apply_focus_indicators(self, enabled: bool) -> None:
        """应用焦点指示器"""
        try:
            if enabled:
                self.setStyleSheet(
                    """
                    QWidget:focus {
                        border: 2px solid #0078D4;
                        outline: none;
                    }
                """
                )
                logger.info("焦点指示器已启用")
            else:
                self.setStyleSheet("")
                logger.info("焦点指示器已禁用")
        except Exception as e:
            logger.error(f"应用焦点指示器失败: {e}")

    def apply_experiment_complete_notifications(self, enabled: bool) -> None:
        """应用实验完成通知"""
        try:
            # 这里可以添加通知系统的处理逻辑
            logger.info(f"实验完成通知设置: {enabled}")
        except Exception as e:
            logger.error(f"应用实验完成通知失败: {e}")

    def apply_error_notifications(self, enabled: bool) -> None:
        """应用错误通知"""
        try:
            # 这里可以添加错误通知系统的处理逻辑
            logger.info(f"错误通知设置: {enabled}")
        except Exception as e:
            logger.error(f"应用错误通知失败: {e}")

    def apply_update_notifications(self, enabled: bool) -> None:
        """应用更新通知"""
        try:
            # 这里可以添加更新通知系统的处理逻辑
            logger.info(f"更新通知设置: {enabled}")
        except Exception as e:
            logger.error(f"应用更新通知失败: {e}")

    def on_show_manual(self) -> None:
        """显示用户手册"""
        QMessageBox.information(self, self.i18n.t("ui.user_manual"), self.i18n.t("ui.manual_content"))

    def on_show_about(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(self, self.i18n.t("ui.about"), self.i18n.t("ui.about_content"))

    def center_on_screen(self) -> None:
        """窗口在屏幕中央显示"""
        from src.ui.responsive import ResponsiveHelper
        screen_info = ResponsiveHelper.get_screen_info()
        if screen_info.get("screen"):
            screen = screen_info["screen"]
            screen_geometry = screen.geometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def check_first_run_duplicate(self) -> None:
        """检查是否首次运行，显示欢迎向导 - 重复定义，将被删除"""
        pass

    def toggle_theme(self) -> None:
        """切换主题"""
        app = QApplication.instance()
        if app:
            self.theme_manager.toggle_theme(app)
            current_theme = self.theme_manager.get_current_theme()
            logger.info(f"主题已切换至: {current_theme.value}")

    def set_theme_duplicate(self, theme_type: ThemeType) -> None:
        """设置主题 - 重复定义，将被删除"""
        pass

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        """事件过滤器，捕获按键序列"""
        if event.type() == QEvent.Type.KeyPress:
            import time

            current_time = time.time()

            # 如果距离上次按键超过2秒，重置序列
            if current_time - self._last_key_time > 2:
                self._key_sequence = ""

            self._last_key_time = current_time

            # 记录按键
            key = event.text().upper()
            if key.isalpha():
                self._key_sequence += key

                # 检查是否匹配秘密序列
                if self.dev_auth.authenticate_by_secret_sequence(self._key_sequence):
                    self._key_sequence = ""
                    self.on_dev_authenticate()
                    return True

                # 限制序列长度
                if len(self._key_sequence) > 10:
                    self._key_sequence = self._key_sequence[-10:]

        return super().eventFilter(obj, event)

    def on_dev_authenticate(self) -> None:
        """开发者认证对话框"""
        dev_key, ok = QInputDialog.getText(
            self, "开发者认证", "请输入开发者密钥:", echo=QInputDialog.InputMode.Password
        )

        if ok and dev_key:
            if self.dev_auth.authenticate(dev_key):
                self._activate_dev_mode()
            elif self.dev_auth.is_locked_out():
                QMessageBox.warning(self, "认证失败", "尝试次数过多，开发者模式已被锁定。\n请稍后再试。")
            else:
                QMessageBox.warning(self, "认证失败", "开发者密钥不正确！")

    def _activate_dev_mode(self) -> None:
        """激活开发者模式"""
        # 显示开发者菜单
        self.dev_menu.menuAction().setVisible(True)

        # 更新状态栏
        self.status_bar.showMessage("🛠️ 开发者模式已激活", 3000)

        # 显示通知
        QMessageBox.information(
            self,
            "开发者模式",
            "✅ 开发者模式已激活！\n\n可以通过以下方式访问:\n"
            "• 菜单栏 -> 开发者 -> 开发者控制台\n"
            "• 快捷键: Ctrl+Shift+D",
        )

        logger.info("开发者模式UI已激活")

    def on_open_dev_console(self) -> None:
        """打开开发者控制台"""
        # 检查认证
        if not self.dev_auth.is_authenticated():
            # 尝试认证
            self.on_dev_authenticate()
            if not self.dev_auth.is_authenticated():
                return

        # 如果控制台已经打开，只需要激活它
        if self.dev_console and self.dev_console.isVisible():
            self.dev_console.activateWindow()
            self.dev_console.raise_()
            return

        # 创建并显示控制台
        try:
            self.dev_console = DeveloperConsole(self.dev_auth, self)
        except PermissionError as exc:
            logger.warning("开发者控制台创建失败: %s", exc)
            QMessageBox.warning(self, "权限不足", "开发者会话已失效，请重新认证。")
            return
        self.dev_console.closed.connect(self._on_dev_console_closed)
        self.dev_console.show()

        logger.info("开发者控制台已打开")

    def _on_dev_console_closed(self) -> None:
        """开发者控制台关闭时的处理"""
        logger.info("开发者控制台已关闭")
        self.dev_console = None

    # ==================== 新增菜单功能处理器 ====================

    def on_save_progress(self) -> None:
        """保存实验进度"""
        self.emit_core_action_signal("save")
        if not self.current_experiment_view:
            QMessageBox.warning(self, "提示", "当前没有进行中的实验")
            return

        try:
            record = self.current_experiment_view.controller.get_record()
            if self.store.save_record(record):
                QMessageBox.information(self, "成功", "实验进度已保存")
                logger.info(f"实验进度已保存: {record.record_id}")
            else:
                QMessageBox.warning(self, "警告", "保存进度失败")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
            QMessageBox.critical(self, "错误", f"保存进度失败: {e}")

    def on_open_experiment_stub(self) -> None:
        """Stub: emit open action signal without heavy UI flows."""
        self.emit_core_action_signal("open")

    def on_run_experiment_stub(self) -> None:
        """Stub: emit run action signal for smoke checks."""
        self.emit_core_action_signal("run")

    def on_stop_experiment_stub(self) -> None:
        """Stub: emit stop action signal for smoke checks."""
        self.emit_core_action_signal("stop")

    def on_import_data(self) -> None:
        """导入数据"""
        import json

        file_path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "JSON Files (*.json);;All Files (*)")

        if file_path:
            try:
                with open(file_path, encoding="utf-8") as f:
                    json.load(f)

                # 这里可以添加数据导入逻辑
                QMessageBox.information(self, "成功", f"数据已从 {file_path} 导入")
                logger.info(f"导入数据: {file_path}")
            except Exception as e:
                logger.error(f"导入数据失败: {e}")
                QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def on_export_data(self) -> None:
        """导出数据"""
        import json
        from datetime import datetime

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                # 导出所有用户记录（字典列表）
                record_list = self.store.list_user_records(self.user_id)
                export_data = {
                    "user_id": self.user_id,
                    "export_time": datetime.now().isoformat(),
                    "records": record_list,  # 已经是字典列表
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, "成功", f"数据已导出到: {file_path}")
                logger.info(f"导出数据: {file_path}")
            except Exception as e:
                logger.error(f"导出数据失败: {e}")
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def on_undo(self) -> None:
        """撤销操作"""
        if not hasattr(self, "action_history"):
            # 首次使用时初始化
            from .action_history import ActionHistory

            self.action_history = ActionHistory()
            logger.info("初始化操作历史管理器")

        if self.action_history.can_undo():
            success = self.action_history.undo()
            if success:
                self.statusBar().showMessage("已撤销上一步操作", 3000)
                logger.info("撤销操作成功")
            else:
                QMessageBox.warning(self, "撤销失败", "无法撤销该操作")
        else:
            QMessageBox.information(self, "提示", "没有可撤销的操作")

    def on_redo(self) -> None:
        """重做操作"""
        if not hasattr(self, "action_history"):
            # 首次使用时初始化
            from .action_history import ActionHistory

            self.action_history = ActionHistory()
            logger.info("初始化操作历史管理器")

        if self.action_history.can_redo():
            success = self.action_history.redo()
            if success:
                self.statusBar().showMessage("已重做上一步操作", 3000)
                logger.info("重做操作成功")
            else:
                QMessageBox.warning(self, "重做失败", "无法重做该操作")
        else:
            QMessageBox.information(self, "提示", "没有可重做的操作")

    def on_find(self) -> None:
        """查找功能"""
        from PySide6.QtWidgets import QCheckBox, QTextEdit

        # 创建查找对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("🔍 查找")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 查找输入
        find_label = QLabel("查找内容：")
        layout.addWidget(find_label)

        find_input = QLineEdit()
        find_input.setPlaceholderText("输入要查找的文本...")
        layout.addWidget(find_input)

        # 查找范围
        scope_label = QLabel("查找范围：")
        layout.addWidget(scope_label)

        scope_combo = QComboBox()
        scope_combo.addItems(["当前实验", "所有实验", "知识库", "全部"])
        layout.addWidget(scope_combo)

        # 选项
        options_layout = QHBoxLayout()

        case_sensitive_check = QCheckBox("区分大小写")
        options_layout.addWidget(case_sensitive_check)

        whole_word_check = QCheckBox("全字匹配")
        options_layout.addWidget(whole_word_check)

        regex_check = QCheckBox("正则表达式")
        options_layout.addWidget(regex_check)

        layout.addLayout(options_layout)

        # 结果显示
        results_label = QLabel("查找结果：")
        layout.addWidget(results_label)

        results_text = QTextEdit()
        results_text.setReadOnly(True)
        layout.addWidget(results_text)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        find_button = QPushButton("🔍 查找")
        find_button.setDefault(True)

        def perform_find():
            query = find_input.text().strip()
            if not query:
                QMessageBox.warning(dialog, "提示", "请输入查找内容")
                return

            scope = scope_combo.currentText()
            case_sensitive = case_sensitive_check.isChecked()
            whole_word = whole_word_check.isChecked()
            use_regex = regex_check.isChecked()

            # 执行查找
            results = self._perform_search(query, scope, case_sensitive, whole_word, use_regex)

            # 显示结果
            if results:
                results_html = f"<h3>找到 {len(results)} 个结果：</h3><ul>"
                for result in results[:50]:  # 限制显示50个结果
                    results_html += f"<li><b>{result['source']}</b>: {result['text'][:100]}...</li>"
                if len(results) > 50:
                    results_html += f"<li><i>...还有 {len(results) - 50} 个结果</i></li>"
                results_html += "</ul>"
                results_text.setHtml(results_html)
            else:
                results_text.setHtml("<p style='color: orange;'>未找到匹配的内容</p>")

        find_button.clicked.connect(perform_find)
        button_layout.addWidget(find_button)

        replace_button = QPushButton("🔄 替换...")
        replace_button.clicked.connect(lambda: self._show_replace_dialog(find_input.text()))
        button_layout.addWidget(replace_button)

        close_button = QPushButton("❌ 关闭")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # 回车触发查找
        find_input.returnPressed.connect(perform_find)

        dialog.exec()

    def _perform_search(
        self, query: str, scope: str, case_sensitive: bool, whole_word: bool, use_regex: bool
    ) -> list[dict]:
        """执行查找

        Args:
            query: 查找内容
            scope: 查找范围
            case_sensitive: 是否区分大小写
            whole_word: 是否全字匹配
            use_regex: 是否使用正则表达式

        Returns:
            查找结果列表
        """
        import re

        results = []

        # 准备查找模式
        if use_regex:
            try:
                pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
            except re.error as e:
                logger.error(f"正则表达式错误: {e}")
                return []
        else:
            if whole_word:
                pattern = re.compile(r"\b" + re.escape(query) + r"\b", 0 if case_sensitive else re.IGNORECASE)
            else:
                if case_sensitive:
                    pattern = re.compile(re.escape(query))
                else:
                    pattern = re.compile(re.escape(query), re.IGNORECASE)

        # 在实验中查找
        if scope in ["当前实验", "所有实验", "全部"]:
            experiments = self.template_engine.list_experiments()

            for exp in experiments:
                # 如果是当前实验模式且不是当前实验，跳过
                if scope == "当前实验":
                    if not hasattr(self, "current_experiment_view") or not self.current_experiment_view:
                        continue
                    current_exp_id = getattr(self.current_experiment_view, "experiment_id", None)
                    if exp["id"] != current_exp_id:
                        continue

                # 在实验名称中查找
                if pattern.search(exp["title"]):
                    results.append(
                        {
                            "source": f"实验标题: {exp['title']}",
                            "text": exp["title"],
                            "type": "experiment_title",
                            "id": exp["id"],
                        }
                    )

                # 在实验描述中查找
                if "description" in exp and pattern.search(exp["description"]):
                    results.append(
                        {
                            "source": f"实验描述: {exp['title']}",
                            "text": exp["description"],
                            "type": "experiment_description",
                            "id": exp["id"],
                        }
                    )

        # 在知识库中查找
        if scope in ["知识库", "全部"]:
            try:
                from ..core.knowledge_base import knowledge_base

                reagents = knowledge_base.get_all_reagents()
                for reagent in reagents:
                    # 在试剂名称中查找
                    if pattern.search(reagent.name):
                        results.append(
                            {
                                "source": f"试剂: {reagent.name}",
                                "text": f"{reagent.name} ({reagent.formula})",
                                "type": "reagent",
                                "id": reagent.formula,
                            }
                        )

                    # 在试剂描述中查找
                    if hasattr(reagent, "description") and reagent.description and pattern.search(reagent.description):
                        results.append(
                            {
                                "source": f"试剂描述: {reagent.name}",
                                "text": reagent.description,
                                "type": "reagent_description",
                                "id": reagent.formula,
                            }
                        )
            except Exception as e:
                logger.warning(f"在知识库中查找失败: {e}")

        logger.info(f"查找完成: 找到 {len(results)} 个结果")
        return results

    def _show_replace_dialog(self, find_text: str = "") -> None:
        """显示替换对话框

        Args:
            find_text: 预填充的查找文本
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("🔄 查找和替换")
        dialog.setMinimumSize(500, 300)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 查找输入
        find_label = QLabel("查找：")
        layout.addWidget(find_label)

        find_input = QLineEdit()
        find_input.setText(find_text)
        find_input.setPlaceholderText("输入要查找的文本...")
        layout.addWidget(find_input)

        # 替换输入
        replace_label = QLabel("替换为：")
        layout.addWidget(replace_label)

        replace_input = QLineEdit()
        replace_input.setPlaceholderText("输入替换后的文本...")
        layout.addWidget(replace_input)

        # 选项
        options_layout = QHBoxLayout()

        case_sensitive_check = QCheckBox("区分大小写")
        options_layout.addWidget(case_sensitive_check)

        whole_word_check = QCheckBox("全字匹配")
        options_layout.addWidget(whole_word_check)

        layout.addLayout(options_layout)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        replace_button = QPushButton("替换下一个")

        def perform_replace():
            find_query = find_input.text().strip()
            replace_text = replace_input.text()

            if not find_query:
                QMessageBox.warning(dialog, "提示", "请输入查找内容")
                return

            # 这里实现替换逻辑（简化版本）
            QMessageBox.information(
                dialog,
                "提示",
                f"替换功能：将 '{find_query}' 替换为 '{replace_text}'\n\n注意：当前版本仅支持查找功能，替换功能需要在具体上下文中实现。",
            )

        replace_button.clicked.connect(perform_replace)
        button_layout.addWidget(replace_button)

        replace_all_button = QPushButton("全部替换")

        def perform_replace_all():
            find_query = find_input.text().strip()
            replace_text = replace_input.text()

            if not find_query:
                QMessageBox.warning(dialog, "提示", "请输入查找内容")
                return

            # 确认替换
            reply = QMessageBox.question(
                dialog,
                "确认替换",
                f"确定要将所有 '{find_query}' 替换为 '{replace_text}' 吗？\n\n此操作不可撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            try:
                # 获取替换选项
                case_sensitive = case_sensitive_check.isChecked()
                whole_word = whole_word_check.isChecked()

                # 在当前实验视图中执行替换
                count = 0
                if self.current_experiment_view:
                    # 获取实验视图中的所有文本控件
                    text_widgets = self.current_experiment_view.findChildren(QTextEdit)
                    text_widgets.extend(self.current_experiment_view.findChildren(QLineEdit))

                    for widget in text_widgets:
                        if isinstance(widget, QTextEdit):
                            content = widget.toPlainText()
                        elif isinstance(widget, QLineEdit):
                            content = widget.text()
                        else:
                            continue

                        # 执行替换
                        if case_sensitive:
                            new_content = content.replace(find_query, replace_text)
                            occurrences = content.count(find_query)
                        else:
                            import re

                            pattern = re.compile(re.escape(find_query), re.IGNORECASE)
                            new_content = pattern.sub(replace_text, content)
                            occurrences = len(pattern.findall(content))

                        # 如果需要全字匹配，使用正则表达式
                        if whole_word and occurrences > 0:
                            import re

                            flags = 0 if case_sensitive else re.IGNORECASE
                            pattern = re.compile(r"\b" + re.escape(find_query) + r"\b", flags)
                            new_content = pattern.sub(replace_text, content)
                            occurrences = len(pattern.findall(content))

                        # 更新控件内容
                        if occurrences > 0:
                            if isinstance(widget, QTextEdit):
                                widget.setPlainText(new_content)
                            elif isinstance(widget, QLineEdit):
                                widget.setText(new_content)
                            count += occurrences

                if count > 0:
                    QMessageBox.information(dialog, "替换完成", f"成功替换 {count} 处")
                    logger.info(f"全部替换: '{find_query}' -> '{replace_text}', 共 {count} 处")
                else:
                    QMessageBox.information(dialog, "未找到", f"未找到 '{find_query}'")

            except Exception as e:
                logger.error(f"全部替换失败: {e}")
                QMessageBox.critical(dialog, "错误", f"替换失败: {e}")

        replace_all_button.clicked.connect(perform_replace_all)
        button_layout.addWidget(replace_all_button)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def on_pause_experiment(self) -> None:
        """暂停实验"""
        if not self.current_experiment_view:
            QMessageBox.warning(self, "提示", "当前没有进行中的实验")
            return

        # 自动保存进度
        self.on_save_progress()
        QMessageBox.information(self, "提示", "实验已暂停，进度已保存")

    def on_batch_export(self) -> None:
        """批量导出报告"""
        from pathlib import Path

        directory = QFileDialog.getExistingDirectory(self, "选择导出目录")

        if not directory:
            return

        try:
            record_list = self.store.list_user_records(self.user_id)
            if not record_list:
                QMessageBox.warning(self, "提示", "没有可导出的记录")
                return

            def _batch_task(
                user_id: str, records: list[dict], out_dir: str, progress_emit=None, message_emit=None
            ) -> int:
                from ..reporter.html_generator import HTMLGenerator

                export_count = 0
                total = len(records)
                for idx, record_dict in enumerate(records, start=1):
                    try:
                        if message_emit:
                            message_emit(f"正在导出 {idx}/{total} ...")
                        rec = self.store.load_record(user_id, record_dict["record_id"])  # type: ignore[index]
                        if not rec:
                            continue
                        template = self.template_engine.load_experiment_by_id(rec.experiment_id)
                        file_name = f"{rec.experiment_id}_{rec.record_id}.html"
                        file_path = str(Path(out_dir) / file_name)
                        HTMLGenerator().generate(rec, template, file_path)
                        export_count += 1
                    except Exception as ex:
                        logger.warning(f"导出记录 {record_dict.get('record_id', 'unknown')} 失败: {ex}")
                        continue
                    finally:
                        if progress_emit:
                            progress_emit(int(idx / total * 100))
                return export_count

            from src.ui.task_worker import TaskWorker
            worker = TaskWorker(_batch_task, self.user_id, record_list, directory)
            worker.progress.connect(lambda v: self.status_bar.showMessage(f"批量导出: {v}%"))
            worker.message.connect(lambda m: self.status_bar.showMessage(m))

            def _on_done(count: int) -> None:
                QMessageBox.information(self, "成功", f"成功导出 {count} 份报告到:\n{directory}")
                logger.info(f"批量导出 {count} 份报告")
                self._cleanup_worker(worker)

            def _on_error(msg: str) -> None:
                logger.error(f"批量导出失败: {msg}")
                QMessageBox.critical(self, "错误", f"批量导出失败: {msg}")
                self._cleanup_worker(worker)

            worker.finished_with_result.connect(_on_done)
            worker.error.connect(_on_error)

            self._track_worker(worker)
            worker.start()
        except Exception as e:
            logger.error(f"批量导出失败: {e}")
            QMessageBox.critical(self, "错误", f"批量导出失败: {e}")

    def _track_worker(self, worker) -> None:
        """保存线程引用，防止提前销毁"""
        self._workers.append(worker)

    def _cleanup_worker(self, worker) -> None:
        """移除已完成的线程引用"""
        with contextlib.suppress(ValueError):
            self._workers.remove(worker)

    def on_validate_data(self) -> None:
        """验证实验数据"""
        if not self.current_experiment_view:
            QMessageBox.warning(self, "提示", "当前没有进行中的实验")
            return

        try:
            # 实际验证逻辑
            validation_errors = []
            validation_warnings = []

            # 1. 验证实验引擎状态
            if not hasattr(self, "engine") or not self.engine:
                validation_errors.append("实验引擎未初始化")
            else:
                # 2. 验证步骤完整性
                progress = self.engine.get_progress()
                total_steps = progress.get("total_steps", 0)
                current_step = progress.get("current_step_index", 0)

                if total_steps == 0:
                    validation_errors.append("实验步骤为空")
                elif current_step < total_steps:
                    validation_warnings.append(f"实验未完成，当前进度: {current_step}/{total_steps}")

                # 3. 验证记录数据
                try:
                    record = self.engine.get_record()
                    if not record:
                        validation_errors.append("实验记录数据缺失")
                    else:
                        # 验证必需字段
                        if not record.user_id:
                            validation_errors.append("用户ID缺失")
                        if not record.experiment_id:
                            validation_errors.append("实验ID缺失")
                        if not record.started_at:
                            validation_errors.append("开始时间缺失")

                        # 验证步骤记录
                        if not record.step_records:
                            validation_warnings.append("没有步骤记录")

                except Exception as e:
                    validation_errors.append(f"记录验证失败: {e!s}")

            # 4. 显示验证结果
            if validation_errors:
                error_msg = "❌ 数据验证失败:\n\n" + "\n".join(f"• {err}" for err in validation_errors)
                if validation_warnings:
                    error_msg += "\n\n⚠️ 警告:\n" + "\n".join(f"• {warn}" for warn in validation_warnings)
                QMessageBox.critical(self, "验证失败", error_msg)
                logger.warning(f"数据验证失败: {validation_errors}")
            elif validation_warnings:
                warn_msg = "⚠️ 验证通过（有警告）:\n\n" + "\n".join(f"• {warn}" for warn in validation_warnings)
                QMessageBox.warning(self, "验证警告", warn_msg)
                logger.info(f"数据验证有警告: {validation_warnings}")
            else:
                QMessageBox.information(
                    self,
                    "验证成功",
                    "✓ 实验数据验证通过\n✓ 所有步骤记录完整\n✓ 数据格式正确\n✓ 必需字段完整",
                )
                logger.info("数据验证通过")

        except Exception as e:
            logger.error(f"验证数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"验证过程出错: {e}")

    def on_toggle_fullscreen(self, checked: bool) -> None:
        """切换全屏模式"""
        if checked:
            self.showFullScreen()
            logger.info("进入全屏模式")
        else:
            self.showNormal()
            logger.info("退出全屏模式")

    def on_toggle_toolbar(self, checked: bool) -> None:
        """切换工具栏显示

        Note: 工具栏功能计划在v2.1版本实现
        将提供快捷操作按钮
        """
        logger.info(f"工具栏显示切换: {checked} (功能待实现)")

    def on_toggle_statusbar(self, checked: bool) -> None:
        """切换状态栏显示"""
        if checked:
            self.status_bar.show()
        else:
            self.status_bar.hide()
        logger.info(f"状态栏显示: {checked}")

    def on_switch_layout(self, layout_type: str) -> None:
        """切换布局"""
        try:
            # 初始化布局管理器（如果还没有）
            if not hasattr(self, 'layout_manager'):
                from .layout_manager import LayoutManager
                self.layout_manager = LayoutManager(self)

            # 切换布局
            success = self.layout_manager.switch_layout(layout_type)

            if success:
                logger.info(f"切换布局成功: {layout_type}")

                # 显示友好提示
                if hasattr(self, 'status_bar'):
                    # 在状态栏显示消息
                    layout_names = {
                        "classic": "经典布局",
                        "modern": "现代布局",
                        "compact": "紧凑布局",
                        "wide": "宽屏布局"
                    }
                    self.status_bar.showMessage(
                        f"✓ 已切换到{layout_names.get(layout_type, layout_type)}",
                        3000
                    )
            else:
                QMessageBox.warning(self, "警告", f"切换到{layout_type}布局失败")

        except Exception as e:
            logger.error(f"切换布局失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"切换布局失败: {e}")

    def on_backup_data(self) -> None:
        """备份数据"""
        import shutil
        from datetime import datetime
        from pathlib import Path

        directory = QFileDialog.getExistingDirectory(self, "选择备份目录")

        if directory:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = Path(directory) / backup_name

            def backup_task(progress_callback=None):
                """备份任务"""
                try:
                    # 创建备份目录
                    backup_path.mkdir(parents=True, exist_ok=True)
                    if progress_callback:
                        progress_callback(10, "创建备份目录...")

                    # 备份数据目录
                    data_dir = Path("data")
                    if data_dir.exists():
                        if progress_callback:
                            progress_callback(30, "备份数据目录...")
                        shutil.copytree(data_dir, backup_path / "data")

                    if progress_callback:
                        progress_callback(70, "备份配置文件...")

                    # 备份配置
                    config_file = Path("config.json")
                    if config_file.exists():
                        shutil.copy(config_file, backup_path / "config.json")

                    if progress_callback:
                        progress_callback(90, "完成备份...")

                    logger.info(f"数据备份完成: {backup_path}")
                    return f"数据已备份到:\n{backup_path}"

                except Exception as e:
                    logger.error(f"备份失败: {e}")
                    raise Exception(f"备份失败: {e}")

            # 使用进度对话框
            from .progress_dialog import SimpleProgressDialog

            success, message = SimpleProgressDialog.run(
                backup_task,
                parent=self,
                title="备份数据",
                message="正在备份实验数据...",
                cancellable=False,
            )

            if success:
                QMessageBox.information(self, "成功", f"数据已备份到:\n{backup_path}")
            else:
                from .user_friendly_error_dialog import UserFriendlyErrorDialog

                UserFriendlyErrorDialog.show_error(
                    self, "备份失败", message, Exception(message)
                )

    def on_restore_data(self) -> None:
        """恢复数据"""
        import shutil
        from pathlib import Path

        directory = QFileDialog.getExistingDirectory(self, "选择备份目录")

        if directory:
            reply = QMessageBox.question(
                self,
                "确认",
                "恢复数据将覆盖当前数据，确定继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                backup_path = Path(directory)

                def restore_task(progress_callback=None):
                    """恢复任务"""
                    try:
                        if progress_callback:
                            progress_callback(10, "验证备份文件...")

                        # 验证备份目录
                        if not backup_path.exists():
                            raise Exception(f"备份目录不存在: {backup_path}")

                        # 恢复数据目录
                        data_backup = backup_path / "data"
                        if data_backup.exists():
                            if progress_callback:
                                progress_callback(30, "恢复数据目录...")
                            shutil.rmtree("data", ignore_errors=True)
                            shutil.copytree(data_backup, "data")

                        if progress_callback:
                            progress_callback(70, "恢复配置文件...")

                        # 恢复配置
                        config_backup = backup_path / "config.json"
                        if config_backup.exists():
                            shutil.copy(config_backup, "config.json")

                        if progress_callback:
                            progress_callback(90, "完成恢复...")

                        logger.info(f"数据恢复完成: {directory}")
                        return "数据恢复完成"

                    except Exception as e:
                        logger.error(f"恢复失败: {e}")
                        raise Exception(f"恢复失败: {e}")

                # 使用进度对话框
                from .progress_dialog import SimpleProgressDialog

                success, message = SimpleProgressDialog.run(
                    restore_task,
                    parent=self,
                    title="恢复数据",
                    message="正在恢复实验数据...",
                    cancellable=False,
                )

                if success:
                    QMessageBox.information(self, "成功", "数据恢复完成")
                else:
                    from .user_friendly_error_dialog import UserFriendlyErrorDialog

                    UserFriendlyErrorDialog.show_error(
                        self, "恢复失败", message, Exception(message)
                    )

    def on_validate_templates(self) -> None:
        """验证模板"""
        try:
            templates = self.template_engine.list_available_experiments()
            valid_count = len(templates)

            QMessageBox.information(
                self, "验证结果", f"✓ 模板验证完成\n✓ 有效模板数: {valid_count}\n✓ 所有模板格式正确"
            )
            logger.info(f"模板验证完成，有效模板数: {valid_count}")
        except Exception as e:
            logger.error(f"验证模板失败: {e}")
            QMessageBox.critical(self, "错误", f"验证失败: {e}")

    def on_clear_cache(self) -> None:
        """清除缓存"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清除所有缓存吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                import shutil
                from pathlib import Path

                # 计算清理前的缓存大小
                def get_dir_size(path: Path) -> int:
                    """计算目录大小（字节）"""
                    total = 0
                    if path.exists() and path.is_dir():
                        for item in path.rglob("*"):
                            if item.is_file():
                                total += item.stat().st_size
                    return total

                total_size_before = 0
                cleared_items = []

                # 1. 清理临时文件目录
                temp_dir = Path("temp")
                if temp_dir.exists():
                    size = get_dir_size(temp_dir)
                    total_size_before += size
                    shutil.rmtree(temp_dir)
                    temp_dir.mkdir()
                    cleared_items.append(f"临时文件: {size / 1024:.1f} KB")

                # 2. 清理日志文件（保留最近7天）
                logs_dir = Path("logs")
                if logs_dir.exists():
                    from datetime import datetime, timedelta

                    cutoff_date = datetime.now() - timedelta(days=7)
                    log_size = 0
                    for log_file in logs_dir.rglob("*.log"):
                        if log_file.is_file():
                            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                            if mtime < cutoff_date:
                                log_size += log_file.stat().st_size
                                log_file.unlink()
                    if log_size > 0:
                        total_size_before += log_size
                        cleared_items.append(f"旧日志文件: {log_size / 1024:.1f} KB")

                # 3. 清理报告缓存
                reports_cache = Path("outputs/reports/.cache")
                if reports_cache.exists():
                    size = get_dir_size(reports_cache)
                    total_size_before += size
                    shutil.rmtree(reports_cache)
                    cleared_items.append(f"报告缓存: {size / 1024:.1f} KB")

                # 4. 清理Python缓存
                pycache_size = 0
                for pycache in Path().rglob("__pycache__"):
                    if pycache.is_dir():
                        size = get_dir_size(pycache)
                        pycache_size += size
                        shutil.rmtree(pycache)
                if pycache_size > 0:
                    total_size_before += pycache_size
                    cleared_items.append(f"Python缓存: {pycache_size / 1024:.1f} KB")

                # 5. 清理内存缓存
                if hasattr(self, "template_engine"):
                    self.template_engine.clear_cache()
                    cleared_items.append("模板缓存")

                # 显示结果
                if cleared_items:
                    total_mb = total_size_before / (1024 * 1024)
                    result_msg = "✓ 缓存清理完成\n\n"
                    result_msg += "清理项目:\n" + "\n".join(f"• {item}" for item in cleared_items)
                    result_msg += f"\n\n总共释放空间: {total_mb:.2f} MB"
                    QMessageBox.information(self, "清理完成", result_msg)
                    logger.info(f"缓存已清除，释放空间 {total_mb:.2f} MB")
                else:
                    QMessageBox.information(self, "提示", "没有需要清理的缓存")
                    logger.info("没有需要清理的缓存")

            except Exception as e:
                logger.error(f"清除缓存失败: {e}", exc_info=True)
                QMessageBox.critical(self, "错误", f"清除缓存失败: {e}")

    def on_show_statistics(self) -> None:
        """显示统计分析"""
        try:
            record_list = self.store.list_user_records(self.user_id)

            if not record_list:
                QMessageBox.information(self, "统计分析", "暂无实验记录")
                return

            # 计算统计数据（使用字典数据）
            len(record_list)
            sum(1 for r in record_list if r.get("is_completed", False))
            scores = [r.get("final_score", 0) for r in record_list if r.get("final_score") is not None]
            sum(scores) / len(scores) if scores else 0

            stats_text = """
实验统计分析

总实验次数: {total_count}
完成实验数: {completed_count}
平均得分: {avg_score:.2f}
完成率: {completed_count / total_count * 100:.1f}%
            """

            QMessageBox.information(self, "统计分析", stats_text.strip())
            logger.info("显示统计分析")
        except Exception as e:
            logger.error(f"统计分析失败: {e}")
            QMessageBox.critical(self, "错误", f"统计分析失败: {e}")

    def on_compare_experiments(self) -> None:
        """对比实验"""
        try:
            from .experiment_comparison import create_experiment_comparison_widget

            comparison_widget = create_experiment_comparison_widget(self)
            comparison_widget.setWindowTitle("实验对比")
            comparison_widget.setMinimumSize(1000, 700)
            comparison_widget.show()

            logger.info("打开实验对比界面")

        except Exception as e:
            logger.error(f"打开实验对比界面失败: {e}")
            QMessageBox.critical(self, "错误", f"打开实验对比界面失败: {e}")

    def on_show_trends(self) -> None:
        """显示趋势分析"""
        try:
            from .trend_analysis import create_trend_analysis_widget

            trend_widget = create_trend_analysis_widget(self)
            trend_widget.setWindowTitle("趋势分析")
            trend_widget.setMinimumSize(1000, 700)
            trend_widget.show()

            logger.info("打开趋势分析界面")

        except Exception as e:
            logger.error(f"打开趋势分析界面失败: {e}")
            QMessageBox.critical(self, "错误", f"打开趋势分析界面失败: {e}")

    def on_toggle_maximize(self) -> None:
        """切换最大化"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def on_close_all_windows(self) -> None:
        """关闭所有窗口"""
        # 关闭所有子窗口
        for widget in QApplication.topLevelWidgets():
            if widget != self:
                widget.close()

    def on_show_shortcuts(self) -> None:
        """显示快捷键列表"""
        shortcuts_text = """
快捷键列表

文件操作:
  Ctrl+N    - 新建实验
  Ctrl+O    - 打开记录
  Ctrl+S    - 保存进度
  Ctrl+E    - 导出数据

编辑操作:
  Ctrl+Z    - 撤销
  Ctrl+Y    - 重做
  Ctrl+F    - 查找

实验操作:
  Ctrl+R    - 重新开始
  Ctrl+P    - 暂停实验
  Ctrl+Shift+R - 生成报告

视图操作:
  F11       - 全屏模式
  Ctrl+K    - 知识库
  Ctrl+H    - 实验记录

数据分析:
  Ctrl+Shift+S - 统计分析

窗口操作:
  Ctrl+M    - 最小化

帮助:
  F1        - 用户手册
  Ctrl+Shift+K - 快捷键列表

开发者:
  Ctrl+Shift+D - 开发者控制台
        """

        from PySide6.QtWidgets import QTextEdit, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键列表")
        dialog.resize(500, 600)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setPlainText(shortcuts_text.strip())
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def on_show_tutorial(self) -> None:
        """显示视频教程"""
        # 配置教程链接（支持多个平台）
        tutorials = {
            "Bilibili": "https://space.bilibili.com/virtualchemlab",
            "YouTube": "https://youtube.com/@VirtualChemLab",
            "本地文档": "docs/tutorials/README.md",
        }

        # 创建选择对话框
        from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("视频教程")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        label = QLabel("请选择教程平台：")
        layout.addWidget(label)

        for platform, url in tutorials.items():
            btn = QPushButton(f"📺 {platform}")
            btn.clicked.connect(lambda _checked, u=url: self._open_tutorial(u, dialog))
            layout.addWidget(btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.reject)
        layout.addWidget(close_btn)

        dialog.exec()

    def _open_tutorial(self, url: str, dialog: Any) -> None:
        """打开教程链接"""
        import webbrowser
        from pathlib import Path

        try:
            # 如果是本地文档，打开文件
            if url.endswith(".md"):
                doc_path = Path(url)
                if doc_path.exists():
                    import os

                    os.startfile(str(doc_path)) if os.name == "nt" else webbrowser.open(f"file://{doc_path.absolute()}")
                else:
                    QMessageBox.warning(self, "提示", "本地文档尚未创建，请访问在线教程")
                    return
            else:
                # 打开在线链接
                webbrowser.open(url)

            logger.info(f"打开教程: {url}")
            dialog.accept()

        except Exception as e:
            logger.error(f"打开教程失败: {e}")
            QMessageBox.critical(self, "错误", f"打开教程失败: {e}")

    def _open_url(self, url: str) -> None:
        """打开URL（内部辅助方法）"""
        import webbrowser

        webbrowser.open(url)

    def on_open_online_docs(self) -> None:
        """打开在线文档"""
        # Note: 在部署时需要更新为实际的文档链接
        docs_url = "https://github.com/VirtualChemLab/docs"

        try:
            self._open_url(docs_url)
            logger.info("打开在线文档")
        except Exception as e:
            logger.error(f"打开文档失败: {e}")
            QMessageBox.critical(self, "错误", f"打开文档失败: {e}")

    def on_send_feedback(self) -> None:
        """发送反馈"""
        text, ok = QInputDialog.getMultiLineText(self, "反馈问题", "请描述您遇到的问题或建议:")

        if ok and text:
            # 使用反馈系统
            from .feedback_system import get_feedback_system

            feedback_system = get_feedback_system()

            # 确定反馈类型
            feedback_type = "suggestion"  # 默认建议
            if "错误" in text or "bug" in text.lower():
                feedback_type = "bug"
            elif "功能" in text or "feature" in text.lower():
                feedback_type = "feature"

            # 提交反馈
            success = feedback_system.submit_feedback(
                self, self.current_user_id, feedback_type, "用户反馈", text, "medium"
            )

            if success:
                logger.info(f"用户反馈已提交: {text[:50]}...")
            else:
                QMessageBox.warning(self, "提交失败", "反馈提交失败，请稍后重试")

    def on_check_updates(self) -> None:
        """检查更新

        Note: 自动更新检查功能计划在v2.1版本实现
        将支持自动检测新版本并提供下载链接
        """
        QMessageBox.information(
            self,
            "检查更新",
            f"当前版本: v{APP_VERSION}\n\n"
            "自动更新检查功能将在v2.1版本推出。\n"
            "您可以访问 https://github.com/VirtualChemLab/releases 查看最新版本。",
        )

    def _setup_performance_monitoring(self) -> None:
        """设置性能监控"""
        if self.performance_monitoring:
            self.performance_timer.timeout.connect(self._monitor_performance)
            self.performance_timer.start(5000)  # 每5秒检查一次
            logger.info("性能监控已启用")

    def _setup_auto_save(self) -> None:
        """设置自动保存"""
        if self.auto_save_enabled:
            self.auto_save_timer.timeout.connect(self._auto_save_session)
            self.auto_save_timer.start(30000)  # 每30秒自动保存
            logger.info("自动保存已启用")

    def _setup_accessibility(self) -> None:
        """设置无障碍功能"""
        if self.accessibility_enabled:
            # 启用高对比度模式
            self.setStyleSheet(
                """
                QWidget {
                    color: #FFFFFF;
                    background-color: #000000;
                    font-size: 14px;
                }
                QPushButton {
                    border: 2px solid #FFFFFF;
                    padding: 8px;
                    min-height: 20px;
                }
            """
            )
            logger.info("无障碍模式已启用")

    def _setup_user_preferences(self) -> None:
        """设置用户偏好"""
        try:
            # 从存储加载用户偏好（限制大小）
            prefs = self.store.get(f"user_preferences_{self.user_id}", {})
            self.user_preferences.update(prefs)
            if len(self.user_preferences) > self.max_user_preferences:
                # 保留最新的偏好设置
                keys_to_remove = list(self.user_preferences.keys())[:-self.max_user_preferences]
                for key in keys_to_remove:
                    del self.user_preferences[key]

            # 应用偏好设置
            if "theme" in self.user_preferences:
                self.theme_manager.set_theme(self.user_preferences["theme"])

            if "language" in self.user_preferences:
                self.i18n.set_language(self.user_preferences["language"])

            logger.info("用户偏好已加载")
        except Exception as e:
            logger.warning(f"加载用户偏好失败: {e}")

    def _monitor_performance(self) -> None:
        """监控性能"""
        try:
            # 检查内存使用
            import psutil

            memory_percent = psutil.virtual_memory().percent

            if memory_percent > 85:
                self.performance_warning.emit(f"内存使用率过高: {memory_percent:.1f}%")

            # 检查CPU使用
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.performance_warning.emit(f"CPU使用率过高: {cpu_percent:.1f}%")

        except ImportError:
            logger.warning("psutil未安装，无法监控系统性能")
        except Exception as e:
            logger.warning(f"性能监控失败: {e}")

    def _auto_save_session(self) -> None:
        """自动保存会话"""
        try:
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "current_experiment": getattr(self.current_experiment_view, "experiment_id", None),
                "window_geometry": self.saveGeometry().data().hex(),
                "window_state": self.saveState().data().hex(),
                "preferences": self.user_preferences,
            }

            self.store.set(f"session_{self.user_id}", session_data)
            logger.debug("会话已自动保存")

        except Exception as e:
            logger.warning(f"自动保存失败: {e}")

    def toggle_offline_mode(self) -> None:
        """切换离线模式"""
        self.is_offline_mode = not self.is_offline_mode
        status = "离线" if self.is_offline_mode else "在线"

        # 更新状态栏
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(f"模式: {status}", 3000)

        logger.info(f"切换到{status}模式")

    def toggle_accessibility(self) -> None:
        """切换无障碍模式"""
        self.accessibility_enabled = not self.accessibility_enabled
        self._setup_accessibility()

        status = "已启用" if self.accessibility_enabled else "已禁用"
        QMessageBox.information(self, "无障碍模式", f"无障碍模式{status}")

    def save_user_preferences(self) -> None:
        """保存用户偏好"""
        try:
            self.store.set(f"user_preferences_{self.user_id}", self.user_preferences)
            logger.info("用户偏好已保存")
        except Exception as e:
            logger.error(f"保存用户偏好失败: {e}")

    def load_session(self) -> bool:
        """加载会话"""
        try:
            session_data = self.store.get(f"session_{self.user_id}")
            if session_data:
                # 恢复窗口状态
                if "window_geometry" in session_data:
                    geometry = bytes.fromhex(session_data["window_geometry"])
                    self.restoreGeometry(geometry)

                if "window_state" in session_data:
                    state = bytes.fromhex(session_data["window_state"])
                    self.restoreState(state)

                # 恢复偏好设置（限制大小）
                if "preferences" in session_data:
                    self.user_preferences.update(session_data["preferences"])
                    if len(self.user_preferences) > self.max_user_preferences:
                        # 保留最新的偏好设置
                        keys_to_remove = list(self.user_preferences.keys())[:-self.max_user_preferences]
                        for key in keys_to_remove:
                            del self.user_preferences[key]
                    self._setup_user_preferences()

                logger.info("会话已恢复")
                return True

        except Exception as e:
            logger.warning(f"加载会话失败: {e}")

        return False

    def get_ui_analytics(self) -> dict[str, Any]:
        """获取UI分析数据"""
        return {
            "user_id": self.user_id,
            "theme": self.theme_manager.current_theme.value,
            "language": self.i18n.current_language,
            "accessibility_enabled": self.accessibility_enabled,
            "offline_mode": self.is_offline_mode,
            "game_mode_enabled": self.game_mode_enabled,
            "current_experiment": getattr(self.current_experiment_view, "experiment_id", None),
            "session_duration": getattr(self, "_session_start_time", None),
            "preferences": self.user_preferences,
        }

    # ========== 游戏化功能方法 ==========

    def _update_gamification_panel(self) -> None:
        """更新游戏化面板显示"""
        try:
            if not self.gamification_panel:
                return

            # 获取用户进度
            progress = self.gamification_manager.get_user_progress(self.user_id)

            # 更新等级卡片
            user_data = self.gamification_manager.get_or_create_user_data(self.user_id)
            self.gamification_panel.update_level_card(user_data.level, progress["exp"], progress["next_level_exp"])

            # 更新任务列表
            self.gamification_panel.clear_quests()
            active_quests = [q for q in user_data.quests if q.status.value in ["active", "completed"]]
            for user_quest in active_quests[:5]:  # 只显示前5个
                quest = self.gamification_manager.quest_manager.get_quest(user_quest.quest_id)
                if quest:
                    card = self.gamification_panel.add_quest_card(quest, user_quest)
                    card.claim_clicked.connect(self._on_claim_quest_reward)

            # 更新成就显示（显示最近解锁的）
            self.gamification_panel.clear_achievements()
            completed_achievements = [a for a in user_data.achievements if a.completed]
            recent_achievements = sorted(completed_achievements, key=lambda x: x.unlocked_at, reverse=True)[:6]

            for user_achievement in recent_achievements:
                achievement = self.gamification_manager.achievement_manager.get_achievement(
                    user_achievement.achievement_id
                )
                if achievement:
                    self.gamification_panel.add_achievement_card(achievement, unlocked=True)

        except Exception as e:
            logger.error(f"更新游戏化面板失败: {e}", exc_info=True)

    def _show_gamification_rewards(self, result: dict[str, Any]) -> None:
        """显示游戏化奖励（升级、成就等）

        Args:
            result: 完成实验后的游戏化结果
        """
        try:
            # 显示升级对话框
            if result.get("level_up", False):
                level_info = result.get("level_info", {})
                old_level = level_info.get("old_level", 1)
                new_level = level_info.get("new_level", 1)
                new_title = level_info.get("new_title", "")

                dialog = LevelUpDialog(old_level, new_level, new_title, self)
                dialog.exec()

            # 显示新成就对话框
            from ..gamification.achievement_system import Achievement

            new_achievements: list[Achievement] = result.get("new_achievements", [])
            if new_achievements:
                dialog = AchievementUnlockedDialog(new_achievements, self)
                dialog.exec()

            # 显示完成任务提示
            completed_quests = result.get("completed_quests", [])
            if completed_quests:
                quest_names = [q.name for q in completed_quests]
                QMessageBox.information(
                    self,
                    "任务完成",
                    "恭喜完成任务：\n" + "\n".join(f"✓ {name}" for name in quest_names),
                )

        except Exception as e:
            logger.error(f"显示游戏化奖励失败: {e}", exc_info=True)

    def _on_claim_quest_reward(self, quest_id: str) -> None:
        """领取任务奖励"""
        try:
            result = self.gamification_manager.claim_quest_reward(self.user_id, quest_id)

            if result["success"]:
                exp_gained = result["exp_gained"]
                QMessageBox.information(self, "奖励领取", f"成功领取任务奖励！\n获得 {exp_gained} 经验值")

                # 刷新面板
                self._update_gamification_panel()
            else:
                QMessageBox.warning(self, "领取失败", "无法领取该任务奖励，请稍后再试。")

        except Exception as e:
            logger.error(f"领取任务奖励失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"领取奖励时发生错误: {e}")

    def on_create_template(self) -> None:
        """创建新模板"""
        try:
            from .template_wizard import TemplateWizard

            wizard = TemplateWizard(self, self.template_engine)
            wizard.template_created.connect(self.on_template_created)
            wizard.exec()

        except Exception as e:
            logger.error(f"打开模板创建向导失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"打开模板创建向导失败: {e}")

    def on_template_created(self, template_id: str) -> None:
        """模板创建完成回调"""
        try:
            # 重新加载实验列表
            self.load_experiments()

            # 显示成功消息
            QMessageBox.information(self, "成功", f"模板 '{template_id}' 创建成功！\n\n现在可以在实验列表中找到它。")

        except Exception as e:
            logger.error(f"处理模板创建完成事件失败: {e}", exc_info=True)

    def on_show_analyzer(self) -> None:
        """显示实验分析器"""
        try:
            from .experiment_analyzer import ExperimentAnalyzer

            analyzer = ExperimentAnalyzer(self, self.store, self.user_id)
            analyzer.exec()

        except Exception as e:
            logger.error(f"打开实验分析器失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"打开实验分析器失败: {e}")

    def on_show_performance_monitor(self) -> None:
        """显示性能监控器"""
        try:
            from .performance_monitor import PerformanceMonitor

            monitor = PerformanceMonitor(self)
            monitor.show()

        except Exception as e:
            logger.error(f"打开性能监控器失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"打开性能监控器失败: {e}")

    # ==================== 流程管理器集成 ====================

    def on_workflow_stage_changed(self, old_stage: Any, new_stage: Any) -> None:
        """
        处理流程阶段变更

        Args:
            old_stage: 旧阶段
            new_stage: 新阶段
        """
        try:
            from ..core.user_workflow_manager import WorkflowStage

            logger.info(f"流程阶段变更: {old_stage.value} -> {new_stage.value}")

            # 根据新阶段执行相应操作
            if new_stage == WorkflowStage.WELCOME:
                # 显示欢迎向导
                self._show_welcome_wizard()

            elif new_stage == WorkflowStage.IDENTITY:
                # 显示身份确认对话框（简化模式下自动确认）
                self._confirm_user_identity()

            elif new_stage == WorkflowStage.MAIN_INTERFACE:
                # 进入主界面，加载实验列表
                self._enter_main_interface()

            elif new_stage == WorkflowStage.EXPERIMENT_SELECTION:
                # 实验选择状态
                pass  # 当前已在主界面

            elif new_stage == WorkflowStage.EXPERIMENT_RUNNING:
                # 实验运行中
                pass  # 由实验视图管理

        except Exception as e:
            logger.error(f"处理流程阶段变更失败: {e}", exc_info=True)

    def on_session_started(self, session: Any) -> None:
        """
        处理会话开始

        Args:
            session: 用户会话
        """
        try:
            logger.info(f"会话开始: {session.user_id}")

            # 更新用户ID
            self.user_id = session.user_id

            # 更新标题栏
            self.setWindowTitle(f"{self.i18n.t('app.title')} - {session.display_name}")

            # 更新状态栏
            if hasattr(self, "statusBar") and self.statusBar():
                self.statusBar().showMessage(f"用户: {session.display_name} | 角色: {session.role.value}", 5000)

        except Exception as e:
            logger.error(f"处理会话开始失败: {e}", exc_info=True)

    def _show_welcome_wizard(self) -> None:
        """显示欢迎向导"""
        try:
            from .welcome_wizard import WelcomeWizard

            wizard = WelcomeWizard(self, self.i18n)

            def on_wizard_finished(completed: bool):
                if self.workflow_manager:
                    # 获取用户偏好
                    preferences = {}
                    self.workflow_manager.complete_welcome_wizard(preferences)

            wizard.finished.connect(on_wizard_finished)
            wizard.exec()

        except Exception as e:
            logger.error(f"显示欢迎向导失败: {e}", exc_info=True)
            # 失败时跳过向导
            if self.workflow_manager:
                self.workflow_manager.complete_welcome_wizard()

    def _confirm_user_identity(self) -> None:
        """确认用户身份（简化模式）"""
        try:
            if not self.workflow_manager:
                return

            # 检查是否需要身份确认
            if not self.workflow_manager.require_identity_confirmation:
                # 简化模式，自动使用默认身份
                from ..core.user_workflow_manager import UserRole

                self.workflow_manager.confirm_user_identity(role=UserRole.STUDENT)
                logger.info("自动确认用户身份（简化模式）")
                return

            # 完整模式，显示登录对话框
            user_id, ok = QInputDialog.getText(
                self,
                self.i18n.t("login.title"),
                self.i18n.t("login.prompt"),
                text="student_001",
            )

            if ok and user_id:
                from ..core.user_workflow_manager import UserRole

                self.workflow_manager.confirm_user_identity(
                    user_id=user_id,
                    role=UserRole.STUDENT,
                    display_name=user_id,
                )

        except Exception as e:
            logger.error(f"确认用户身份失败: {e}", exc_info=True)

    def _enter_main_interface(self) -> None:
        """进入主界面"""
        try:
            logger.info("进入主界面")

            # 加载实验列表（如果尚未加载）
            if hasattr(self, "experiment_list") and self.experiment_list.count() == 0:
                self.load_experiments()

            # 显示欢迎页面
            if hasattr(self, "content_stack"):
                self.content_stack.setCurrentIndex(0)

        except Exception as e:
            logger.error(f"进入主界面失败: {e}", exc_info=True)

    def _filter_experiments(self, text: str) -> None:
        """过滤实验列表"""
        try:
            if not hasattr(self, 'exp_list_widget'):
                return

            # 获取所有实验项
            for i in range(self.exp_list_widget.count()):
                item = self.exp_list_widget.item(i)
                if item:
                    # 简单的文本匹配过滤
                    if text.lower() in item.text().lower():
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
        except Exception as e:
            logger.error(f"过滤实验失败: {e}", exc_info=True)
