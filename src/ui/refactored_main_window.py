"""
重构后的主窗口
使用组件化架构，提高代码的可维护性和可扩展性
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.common_exceptions import UIError
from ..core.error_handler import get_error_handler, safe_execute
from .components import (
    MenuComponent,
    StatusBarComponent,
    ToolbarComponent,
    WindowManager,
    create_component,
    register_component,
)

logger = logging.getLogger(__name__)


class RefactoredMainWindow(QMainWindow):
    """重构后的主窗口"""

    # 信号定义
    window_ready = Signal()
    experiment_started = Signal(str)
    experiment_stopped = Signal(str)
    settings_changed = Signal(dict)

    def __init__(self, container=None, workflow_manager=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._workflow_manager = workflow_manager
        self._error_handler = get_error_handler()

        # 组件管理
        self._window_manager = WindowManager(self)
        self._components: Dict[str, Any] = {}

        # UI组件
        self._menu_component: Optional[MenuComponent] = None
        self._toolbar_component: Optional[ToolbarComponent] = None
        self._statusbar_component: Optional[StatusBarComponent] = None

        # 主内容区域
        self._central_widget: Optional[QWidget] = None
        self._splitter: Optional[QSplitter] = None
        self._stacked_widget: Optional[QStackedWidget] = None

        # 初始化定时器
        self._init_timer = QTimer()
        self._init_timer.timeout.connect(self._delayed_initialize)
        self._init_timer.setSingleShot(True)

        # 注册组件
        self._register_components()

        # 延迟初始化
        self._init_timer.start(100)

    def _register_components(self) -> None:
        """注册组件"""
        register_component("menu", MenuComponent)
        register_component("toolbar", ToolbarComponent)
        register_component("statusbar", StatusBarComponent)

    def _delayed_initialize(self) -> None:
        """延迟初始化"""
        try:
            self._setup_ui()
            self._create_components()
            self._connect_signals()
            self._load_settings()
            self.window_ready.emit()
            logger.info("RefactoredMainWindow initialized successfully")
        except Exception as e:
            self._handle_initialization_error(e)

    def _setup_ui(self) -> None:
        """设置UI"""
        self.setWindowTitle("VirtualChemLab - 虚拟化学实验室")
        self.setMinimumSize(1200, 800)

        # 创建中央部件
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        # 创建主布局
        layout = QVBoxLayout(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建分割器
        self._splitter = QSplitter()
        layout.addWidget(self._splitter)

        # 创建堆叠部件
        self._stacked_widget = QStackedWidget()
        self._splitter.addWidget(self._stacked_widget)

    def _create_components(self) -> None:
        """创建组件"""
        # 创建菜单组件
        self._menu_component = create_component("menu", self)
        if self._menu_component:
            self.setMenuBar(self._menu_component.get_menubar())
            self._components["menu"] = self._menu_component

        # 创建工具栏组件
        self._toolbar_component = create_component("toolbar", self)
        if self._toolbar_component:
            self.addToolBar(self._toolbar_component.get_toolbar())
            self._components["toolbar"] = self._toolbar_component

        # 创建状态栏组件
        self._statusbar_component = create_component("statusbar", self)
        if self._statusbar_component:
            self.setStatusBar(self._statusbar_component.get_statusbar())
            self._components["statusbar"] = self._statusbar_component

        # 初始化所有组件
        self._window_manager.initialize_all_windows()

    def _connect_signals(self) -> None:
        """连接信号"""
        # 连接菜单信号
        if self._menu_component:
            self._menu_component.action_triggered.connect(self._handle_menu_action)

        # 连接工具栏信号
        if self._toolbar_component:
            self._toolbar_component.action_triggered.connect(self._handle_toolbar_action)

        # 连接状态栏信号
        if self._statusbar_component:
            self._statusbar_component.status_changed.connect(self._on_status_changed)
            self._statusbar_component.progress_changed.connect(self._on_progress_changed)

        # 连接窗口管理器信号
        self._window_manager.window_created.connect(self._on_window_created)
        self._window_manager.window_destroyed.connect(self._on_window_destroyed)
        self._window_manager.window_error.connect(self._on_window_error)

    def _handle_menu_action(self, action: str) -> None:
        """处理菜单动作"""
        try:
            if action == "new_experiment":
                self._new_experiment()
            elif action == "open_experiment":
                self._open_experiment()
            elif action == "save_experiment":
                self._save_experiment()
            elif action == "exit":
                self.close()
            elif action == "run_experiment":
                self._run_experiment()
            elif action == "stop_experiment":
                self._stop_experiment()
            elif action == "settings":
                self._show_settings()
            elif action == "help":
                self._show_help()
            elif action == "about":
                self._show_about()
            else:
                logger.warning(f"Unknown menu action: {action}")
        except Exception as e:
            self._handle_action_error(action, e)

    def _handle_toolbar_action(self, action: str) -> None:
        """处理工具栏动作"""
        try:
            if action == "new_experiment":
                self._new_experiment()
            elif action == "open_experiment":
                self._open_experiment()
            elif action == "save_experiment":
                self._save_experiment()
            elif action == "run_experiment":
                self._run_experiment()
            elif action == "stop_experiment":
                self._stop_experiment()
            elif action == "settings":
                self._show_settings()
            elif action == "help":
                self._show_help()
            else:
                logger.warning(f"Unknown toolbar action: {action}")
        except Exception as e:
            self._handle_action_error(action, e)

    def _handle_action_error(self, action: str, error: Exception) -> None:
        """处理动作错误"""
        ui_error = UIError(
            message=f"Error handling action {action}: {str(error)}",
            widget="RefactoredMainWindow",
            action=action,
            cause=error
        )
        self._error_handler.handle_error(ui_error)

    def _new_experiment(self) -> None:
        """新建实验"""
        self._statusbar_component.set_status("正在创建新实验...")
        try:
            # 获取实验管理器
            if self._container and hasattr(self._container, 'get'):
                experiment_manager = self._container.get('experiment_manager')
                if experiment_manager:
                    # 创建新实验会话
                    from ..core.enhanced_experiment_manager import (
                        EnhancedExperimentManager,
                    )

                    # 这里可以弹出对话框让用户选择实验模板
                    self._statusbar_component.set_status("请选择实验模板", 3000)
                else:
                    self._statusbar_component.set_status("实验管理器未初始化", 3000)
            else:
                self._statusbar_component.set_status("容器未初始化", 3000)
        except Exception as e:
            logger.error(f"创建新实验失败: {e}")
            self._statusbar_component.set_status(f"创建失败: {e}", 3000)

    def _open_experiment(self) -> None:
        """打开实验"""
        self._statusbar_component.set_status("正在打开实验...")
        try:
            from PySide6.QtWidgets import QFileDialog

            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "打开实验",
                "data/experiment_states",
                "实验文件 (*.json);;所有文件 (*)"
            )
            if file_path:
                # 加载实验状态
                logger.info(f"打开实验文件: {file_path}")
                self._statusbar_component.set_status(f"已打开: {file_path}", 3000)
            else:
                self._statusbar_component.set_status("未选择文件", 3000)
        except Exception as e:
            logger.error(f"打开实验失败: {e}")
            self._statusbar_component.set_status(f"打开失败: {e}", 3000)

    def _save_experiment(self) -> None:
        """保存实验"""
        self._statusbar_component.set_status("正在保存实验...")
        try:
            from PySide6.QtWidgets import QFileDialog

            # 打开保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存实验",
                "data/experiment_states",
                "实验文件 (*.json);;所有文件 (*)"
            )
            if file_path:
                # 保存实验状态
                logger.info(f"保存实验到: {file_path}")
                self._statusbar_component.set_status(f"已保存: {file_path}", 3000)
            else:
                self._statusbar_component.set_status("未选择保存位置", 3000)
        except Exception as e:
            logger.error(f"保存实验失败: {e}")
            self._statusbar_component.set_status(f"保存失败: {e}", 3000)

    def _run_experiment(self) -> None:
        """运行实验"""
        self._statusbar_component.set_status("正在运行实验...")
        self._statusbar_component.show_progress(0, 100)
        try:
            # 获取当前实验控制器
            if self._container and hasattr(self._container, 'get'):
                controller = self._container.get('experiment_controller')
                if controller:
                    # 启动实验
                    controller.start_experiment()
                    self.experiment_started.emit(controller.template.id)
                    logger.info("实验已启动")
                else:
                    self._statusbar_component.set_status("请先选择实验", 3000)
            else:
                self._statusbar_component.set_status("容器未初始化", 3000)
        except Exception as e:
            logger.error(f"运行实验失败: {e}")
            self._statusbar_component.set_status(f"运行失败: {e}", 3000)

    def _stop_experiment(self) -> None:
        """停止实验"""
        self._statusbar_component.set_status("正在停止实验...")
        try:
            # 获取当前实验控制器
            if self._container and hasattr(self._container, 'get'):
                controller = self._container.get('experiment_controller')
                if controller:
                    # 取消实验
                    controller.cancel_experiment("用户手动停止")
                    self.experiment_stopped.emit(controller.template.id)
                    logger.info("实验已停止")
            self._statusbar_component.hide_progress()
            self._statusbar_component.set_status("实验已停止", 3000)
        except Exception as e:
            logger.error(f"停止实验失败: {e}")
            self._statusbar_component.hide_progress()
            self._statusbar_component.set_status(f"停止失败: {e}", 3000)

    def _show_settings(self) -> None:
        """显示设置"""
        self._statusbar_component.set_status("正在打开设置...")
        try:
            from .config_dialog import ConfigDialog

            # 创建并显示配置对话框
            dialog = ConfigDialog(self)
            if dialog.exec():
                # 用户点击了确定，配置已保存
                self._statusbar_component.set_status("设置已保存", 3000)
                # 发出配置改变信号
                self.settings_changed.emit(dialog.get_config_summary())
            else:
                self._statusbar_component.set_status("设置已取消", 3000)
        except Exception as e:
            logger.error(f"打开设置对话框失败: {e}")
            self._statusbar_component.set_status(f"打开设置失败: {e}", 3000)

    def _show_help(self) -> None:
        """显示帮助"""
        self._statusbar_component.set_status("正在打开帮助...")
        try:
            from .help_system import HelpManager

            # 创建并显示帮助系统
            help_manager = HelpManager()
            help_manager.show_help(context="main_window", parent=self)
            self._statusbar_component.set_status("帮助已打开", 3000)
        except Exception as e:
            logger.error(f"打开帮助系统失败: {e}")
            self._statusbar_component.set_status(f"打开帮助失败: {e}", 3000)

    def _show_about(self) -> None:
        """显示关于"""
        self._statusbar_component.set_status("正在打开关于...")
        try:
            from PySide6.QtWidgets import QMessageBox

            # 创建关于对话框
            about_text = """
            <h2>VirtualChemLab - 虚拟化学实验室</h2>
            <p><b>版本:</b> v2.0.0 (Beta)</p>
            <p><b>描述:</b> 虚拟化学实验室是一个交互式的化学实验模拟平台，
            提供安全、有趣的实验环境。</p>
            <p><b>特性:</b></p>
            <ul>
                <li>实时物理模拟</li>
                <li>游戏化体验</li>
                <li>粒子效果系统</li>
                <li>智能AI助手</li>
            </ul>
            <p><b>许可证:</b> MIT License</p>
            <p><b>作者:</b> VirtualChemLab Team</p>
            """
            QMessageBox.about(self, "关于 VirtualChemLab", about_text)
            self._statusbar_component.set_status("关于已打开", 3000)
        except Exception as e:
            logger.error(f"打开关于对话框失败: {e}")
            self._statusbar_component.set_status(f"打开关于失败: {e}", 3000)

    def _on_status_changed(self, status: str) -> None:
        """状态改变处理"""
        logger.debug(f"Status changed: {status}")

    def _on_progress_changed(self, progress: int) -> None:
        """进度改变处理"""
        logger.debug(f"Progress changed: {progress}")

    def _on_window_created(self, name: str) -> None:
        """窗口创建处理"""
        logger.debug(f"Window created: {name}")

    def _on_window_destroyed(self, name: str) -> None:
        """窗口销毁处理"""
        logger.debug(f"Window destroyed: {name}")

    def _on_window_error(self, name: str, error: str) -> None:
        """窗口错误处理"""
        logger.error(f"Window error in {name}: {error}")

    def _load_settings(self) -> None:
        """加载设置"""
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            # 加载窗口设置
            window_config = config_manager.get_app_config().get('window', {})
            if window_config:
                width = window_config.get('width', 1200)
                height = window_config.get('height', 800)
                self.resize(width, height)

                if window_config.get('maximized', False):
                    self.showMaximized()

            logger.info("设置加载成功")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def _save_settings(self) -> None:
        """保存设置"""
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            # 保存窗口设置
            window_config = {
                'width': self.width(),
                'height': self.height(),
                'maximized': self.isMaximized()
            }
            config_manager.update_app_config({'window': window_config})

            logger.info("设置保存成功")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _handle_initialization_error(self, error: Exception) -> None:
        """处理初始化错误"""
        ui_error = UIError(
            message=f"Failed to initialize RefactoredMainWindow: {str(error)}",
            widget="RefactoredMainWindow",
            action="initialize",
            cause=error
        )
        self._error_handler.handle_error(ui_error)

    def get_component(self, name: str) -> Optional[Any]:
        """获取组件"""
        return self._components.get(name)

    def add_component(self, name: str, component: Any) -> None:
        """添加组件"""
        self._components[name] = component
        self._window_manager.register_window(name, component)

    def remove_component(self, name: str) -> None:
        """移除组件"""
        if name in self._components:
            component = self._components.pop(name)
            self._window_manager.unregister_window(name)
            component.cleanup()

    def closeEvent(self, event) -> None:
        """关闭事件处理"""
        try:
            # 保存设置
            self._save_settings()

            # 清理组件
            self._window_manager.cleanup_all_windows()

            # 接受关闭事件
            event.accept()
            logger.info("RefactoredMainWindow closed successfully")
        except Exception as e:
            logger.error(f"Error during close: {e}")
            event.accept()  # 仍然关闭窗口
