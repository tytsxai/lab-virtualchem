"""
重构后的主窗口
使用组件化架构，提高代码的可维护性和可扩展性
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.common_exceptions import UIError
from ..core.di_container import DIContainer
from ..core.error_handler import get_error_handler
from ..core.service_registration import get_configured_container
from ..core.template_engine import TemplateEngine
from .components import (
    MenuComponent,
    StatusBarComponent,
    ToolbarComponent,
    WindowManager,
    create_component,
    register_component,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from .experiment_state_manager import ExperimentStateManager


class RefactoredMainWindow(QMainWindow):
    """重构后的主窗口"""

    # 信号定义
    window_ready = Signal()
    experiment_started = Signal(str)
    experiment_stopped = Signal(str)
    settings_changed = Signal(dict)

    def __init__(
        self, container: DIContainer | None = None, workflow_manager=None, parent=None
    ):
        super().__init__(parent)

        # 如果未显式传入容器，则使用全局配置好的容器
        if container is None:
            try:
                container = get_configured_container()
            except Exception as exc:
                logger.error(f"初始化DI容器失败: {exc}")
                container = None

        self._container: DIContainer | None = container
        self._workflow_manager = workflow_manager
        self._error_handler = get_error_handler()

        # 组件管理
        self._window_manager = WindowManager(self)
        self._components: dict[str, Any] = {}

        # UI组件
        self._menu_component: MenuComponent | None = None
        self._toolbar_component: ToolbarComponent | None = None
        self._statusbar_component: StatusBarComponent | None = None

        # 主内容区域和状态
        self._central_widget: QWidget | None = None
        self._splitter: QSplitter | None = None
        self._stacked_widget: QStackedWidget | None = None
        self._template_engine: TemplateEngine | None = None
        self._current_experiment_id: str | None = None
        self._state_manager: ExperimentStateManager | None = None  # 引号避免循环导入
        self._current_view: QWidget | None = None

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

        # 初始化实验状态管理器（按需导入，避免UI启动失败）
        try:
            from .experiment_state_manager import ExperimentStateManager

            self._state_manager = ExperimentStateManager()
        except Exception as exc:  # pragma: no cover - 启动容错
            logger.warning(f"实验状态管理器初始化失败: {exc}")
            self._state_manager = None

        # 初始化模板引擎
        if self._container is not None:
            try:
                self._template_engine = self._container.resolve(TemplateEngine)
            except Exception as exc:
                logger.warning(f"解析 TemplateEngine 失败: {exc}")

    def _load_experiment_view(self, template: Any) -> None:
        """在堆叠窗口中加载实验视图"""
        if self._stacked_widget is None:
            return

        # 清理现有视图
        if self._current_view is not None:
            try:
                self._stacked_widget.removeWidget(self._current_view)
                self._current_view.setParent(None)
                self._current_view.deleteLater()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"清理旧实验视图失败: {exc}")
            finally:
                self._current_view = None

        try:
            from .experiment_view import ExperimentView

            view = ExperimentView(
                template=template, container=self._container, user_id="student_001"
            )
            self._stacked_widget.addWidget(view)
            self._stacked_widget.setCurrentWidget(view)
            self._current_view = view
            logger.info("实验视图已加载到重构主窗口")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"创建实验视图失败: {exc}", exc_info=True)
            self._current_view = None

    def _get_current_scene_and_controller(self) -> tuple[Any | None, Any | None]:
        """返回当前视图的场景和控制器（如果可用）"""
        view = self._current_view
        if view is None:
            return None, None

        controller = getattr(view, "controller", None)
        scene = None

        # 优先尝试交互式实验视图
        interactive_view = getattr(view, "interactive_view", None)
        if interactive_view is not None:
            try:
                if hasattr(interactive_view, "get_scene"):
                    scene = interactive_view.get_scene()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"获取交互式场景失败: {exc}")

        # 游戏化视图
        if scene is None:
            scene = getattr(view, "game_scene", None)

        return scene, controller

    def _capture_current_state(self) -> Any | None:
        """捕获当前实验状态"""
        if not self._state_manager or not self._current_experiment_id:
            return None

        scene, controller = self._get_current_scene_and_controller()
        try:
            return self._state_manager.capture_state(
                self._current_experiment_id,
                scene=scene,
                controller=controller,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"捕获实验状态失败: {exc}", exc_info=True)
            return None

    def _restore_loaded_state(self, state: Any) -> bool:
        """恢复已加载的实验状态"""
        if not self._state_manager:
            return False

        scene, controller = self._get_current_scene_and_controller()
        try:
            return self._state_manager.restore_state(
                state, scene=scene, controller=controller
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"恢复实验状态失败: {exc}", exc_info=True)
            return False

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
            self._toolbar_component.action_triggered.connect(
                self._handle_toolbar_action
            )

        # 连接状态栏信号
        if self._statusbar_component:
            self._statusbar_component.status_changed.connect(self._on_status_changed)
            self._statusbar_component.progress_changed.connect(
                self._on_progress_changed
            )

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
            cause=error,
        )
        self._error_handler.handle_error(ui_error)

    def _new_experiment(self) -> None:
        """新建实验"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在创建新实验...")

        # 需要模板引擎
        if not self._template_engine:
            self._statusbar_component.set_status("模板引擎未初始化，无法创建实验", 3000)
            return

        try:
            templates = self._template_engine.list_available_experiments()
            if not templates:
                self._statusbar_component.set_status("未找到可用实验模板", 3000)
                return

            # 弹出简单对话框让用户选择模板ID
            from PySide6.QtWidgets import QInputDialog

            items = [
                t["id"] if isinstance(t, dict) else getattr(t, "id", "")
                for t in templates
            ]
            items = [i for i in items if i]
            if not items:
                self._statusbar_component.set_status("模板列表为空", 3000)
                return

            selected_id, ok = QInputDialog.getItem(
                self,
                "选择实验模板",
                "请选择要创建的实验：",
                items,
                0,
                False,
            )
            if not ok or not selected_id:
                self._statusbar_component.set_status("已取消新建实验", 3000)
                return

            # 加载模板并记录当前实验ID
            template = self._template_engine.load_experiment_by_id(selected_id)
            self._current_experiment_id = selected_id

            # 在主界面中加载实验视图
            self._load_experiment_view(template)

            # 这里预留后续将 ExperimentView/GameExperimentView 挂到 _stacked_widget 的接口
            logger.info(
                f"新实验已选择: {selected_id} - {getattr(template, 'title', '')}"
            )
            self._statusbar_component.set_status(f"已创建实验: {selected_id}", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"创建新实验失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"创建失败: {e}", 3000)

    def _open_experiment(self) -> None:
        """打开实验"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在打开实验...")

        if not self._state_manager:
            self._statusbar_component.set_status(
                "状态管理器未初始化，无法打开实验", 3000
            )
            return

        try:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "打开实验",
                "data/experiment_states",
                "实验文件 (*.json);;所有文件 (*)",
            )
            if file_path:
                # 加载实验状态
                state = self._state_manager.load_from_file(file_path)
                self._current_experiment_id = state.experiment_id

                if not self._template_engine:
                    self._statusbar_component.set_status(
                        "模板引擎未初始化，无法加载实验视图", 3000
                    )
                    return

                # 加载模板和视图
                template = self._template_engine.load_experiment_by_id(
                    state.experiment_id
                )
                self._load_experiment_view(template)

                restored = self._restore_loaded_state(state)
                if restored:
                    self._statusbar_component.set_status(
                        f"已加载实验状态: {file_path}", 3000
                    )
                else:
                    self._statusbar_component.set_status(
                        f"已加载: {file_path}（部分状态未恢复）", 3000
                    )
                logger.info(f"打开实验状态文件: {file_path}")
            else:
                self._statusbar_component.set_status("未选择文件", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"打开实验失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"打开失败: {e}", 3000)

    def _save_experiment(self) -> None:
        """保存实验"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在保存实验...")

        try:
            # 打开保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存实验",
                "data/experiment_states",
                "实验文件 (*.json);;所有文件 (*)",
            )
            if file_path:
                state = self._capture_current_state()
                if state is None:
                    self._statusbar_component.set_status(
                        "当前没有可保存的实验状态", 3000
                    )
                    return

                saved_path = self._state_manager.save_to_file(state)
                dest_path = Path(file_path)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(saved_path, dest_path)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"复制实验状态文件失败: {exc}")
                    # 回退到直接写入目标文件
                    dest_path.write_text(
                        saved_path.read_text(encoding="utf-8"), encoding="utf-8"
                    )

                logger.info(f"保存实验到: {file_path}")
                self._statusbar_component.set_status(f"已保存: {file_path}", 3000)
            else:
                self._statusbar_component.set_status("未选择保存位置", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"保存实验失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"保存失败: {e}", 3000)

    def _run_experiment(self) -> None:
        """运行实验"""
        if not self._statusbar_component:
            return

        if not self._current_experiment_id:
            self._statusbar_component.set_status("请先通过“新建实验”选择模板", 3000)
            return

        self._statusbar_component.set_status("正在运行实验...")
        self._statusbar_component.show_progress(0, 100)

        # 暂时只更新状态栏和信号，核心实验执行仍由具体视图负责
        try:
            self.experiment_started.emit(self._current_experiment_id)
            logger.info(f"实验已启动: {self._current_experiment_id}")
            self._statusbar_component.set_progress(100)
            self._statusbar_component.set_status("实验运行中...", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"运行实验失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"运行失败: {e}", 3000)

    def _stop_experiment(self) -> None:
        """停止实验"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在停止实验...")
        try:
            if self._current_experiment_id:
                self.experiment_stopped.emit(self._current_experiment_id)
                logger.info(f"实验已停止: {self._current_experiment_id}")

            self._statusbar_component.hide_progress()
            self._statusbar_component.set_status("实验已停止", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"停止实验失败: {e}", exc_info=True)
            self._statusbar_component.hide_progress()
            self._statusbar_component.set_status(f"停止失败: {e}", 3000)

    def _show_settings(self) -> None:
        """显示设置"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在打开设置...")
        try:
            from .settings_dialog import SettingsDialog

            dialog = SettingsDialog(
                i18n_dir="assets/i18n",
                settings_file="config/settings.json",
                parent=self,
            )
            # 透传设置变更事件给外部监听者
            dialog.settings_changed.connect(self.settings_changed)
            if dialog.exec():
                self._statusbar_component.set_status("设置已保存", 3000)
            else:
                self._statusbar_component.set_status("设置已取消", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"打开设置对话框失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"打开设置失败: {e}", 3000)

    def _show_help(self) -> None:
        """显示帮助"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在打开帮助...")
        try:
            from .help_system import HelpManager

            help_manager = HelpManager()
            help_manager.show_help(context="main_window", parent=self)
            self._statusbar_component.set_status("帮助已打开", 3000)
        except Exception as e:  # noqa: BLE001
            logger.error(f"打开帮助系统失败: {e}", exc_info=True)
            self._statusbar_component.set_status(f"打开帮助失败: {e}", 3000)

    def _show_about(self) -> None:
        """显示关于"""
        if not self._statusbar_component:
            return

        self._statusbar_component.set_status("正在打开关于...")
        try:
            from .. import __version__ as APP_VERSION

            about_text = f"""
            <h2>VirtualChemLab - 虚拟化学实验室</h2>
            <p><b>版本:</b> v{APP_VERSION}</p>
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
        except Exception as e:  # noqa: BLE001
            logger.error(f"打开关于对话框失败: {e}", exc_info=True)
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
            window_config = config_manager.get_app_config().get("window", {})
            if window_config:
                width = window_config.get("width", 1200)
                height = window_config.get("height", 800)
                self.resize(width, height)

                if window_config.get("maximized", False):
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
                "width": self.width(),
                "height": self.height(),
                "maximized": self.isMaximized(),
            }
            config_manager.update_app_config({"window": window_config})

            logger.info("设置保存成功")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _handle_initialization_error(self, error: Exception) -> None:
        """处理初始化错误"""
        ui_error = UIError(
            message=f"Failed to initialize RefactoredMainWindow: {str(error)}",
            widget="RefactoredMainWindow",
            action="initialize",
            cause=error,
        )
        self._error_handler.handle_error(ui_error)

    def get_component(self, name: str) -> Any | None:
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
