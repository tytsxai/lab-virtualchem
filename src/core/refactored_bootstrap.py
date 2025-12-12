"""
重构后的启动引导器
整合所有重构后的组件，提供统一的启动流程
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .. import __version__ as APP_VERSION
from .common_exceptions import SystemError
from .error_handler import get_error_handler, initialize_default_handlers
from .import_manager import get_import_manager, register_lazy_module
from .unified_config_manager import get_config_manager
from .unified_performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)


class RefactoredBootstrap:
    """重构后的启动引导器"""

    def __init__(self):
        self._app: QApplication | None = None
        self._main_window = None
        self._initialized = False
        self._error_handler = get_error_handler()

    def initialize(self) -> bool:
        """初始化应用程序"""
        if self._initialized:
            return True

        try:
            logger.info("Starting VirtualChemLab bootstrap...")

            # 1. 初始化错误处理
            self._initialize_error_handling()

            # 2. 初始化导入管理
            self._initialize_import_management()

            # 3. 初始化配置管理
            self._initialize_config_management()

            # 4. 初始化性能监控
            self._initialize_performance_monitoring()

            # 5. 初始化Qt应用
            self._initialize_qt_application()

            # 6. 创建主窗口
            self._create_main_window()

            self._initialized = True
            logger.info("VirtualChemLab bootstrap completed successfully")
            return True

        except Exception as e:
            self._handle_bootstrap_error(e)
            return False

    def _initialize_error_handling(self) -> None:
        """初始化错误处理"""
        try:
            initialize_default_handlers()
            logger.info("Error handling initialized")
        except Exception as e:
            logger.error(f"Failed to initialize error handling: {e}")
            raise

    def _initialize_import_management(self) -> None:
        """初始化导入管理"""
        try:
            import_manager = get_import_manager()

            # 注册核心模块
            import_manager.register_module("core.common_exceptions", sys.modules[__name__])
            import_manager.register_module("core.error_handler", sys.modules[__name__])
            import_manager.register_module("core.unified_config_manager", sys.modules[__name__])
            import_manager.register_module("core.unified_performance_monitor", sys.modules[__name__])

            # 注册懒加载模块
            register_lazy_module("ui.refactored_main_window", "src.ui.refactored_main_window")
            register_lazy_module("ui.components", "src.ui.components")

            logger.info("Import management initialized")
        except Exception as e:
            logger.error(f"Failed to initialize import management: {e}")
            raise

    def _initialize_config_management(self) -> None:
        """初始化配置管理"""
        try:
            config_manager = get_config_manager()
            config_manager.initialize()

            # 验证配置
            if not config_manager.validate_all():
                logger.warning("Some configuration sections failed validation")

            logger.info("Configuration management initialized")
        except Exception as e:
            logger.error(f"Failed to initialize configuration management: {e}")
            raise

    def _initialize_performance_monitoring(self) -> None:
        """初始化性能监控"""
        try:
            performance_monitor = get_performance_monitor()

            # 启动性能监控
            performance_monitor.start_monitoring(interval=1.0)

            logger.info("Performance monitoring initialized")
        except Exception as e:
            logger.error(f"Failed to initialize performance monitoring: {e}")
            raise

    def _initialize_qt_application(self) -> None:
        """初始化Qt应用"""
        try:
            # 创建Qt应用
            self._app = QApplication(sys.argv)
            self._app.setApplicationName("VirtualChemLab")
            self._app.setApplicationDisplayName("虚拟化学实验室")
            self._app.setApplicationVersion(APP_VERSION)
            self._app.setOrganizationName("VirtualChemLab")

            # 启用高DPI支持
            self._app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            self._app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

            logger.info("Qt application initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Qt application: {e}")
            raise

    def _create_main_window(self) -> None:
        """创建主窗口"""
        try:
            # 使用导入管理器获取主窗口类
            main_window_class = get_import_manager().import_class(
                "ui.refactored_main_window",
                "RefactoredMainWindow"
            )

            if main_window_class is None:
                raise SystemError("Failed to import RefactoredMainWindow")

            # 创建主窗口实例
            self._main_window = main_window_class()
            self._main_window.show()

            logger.info("Main window created and shown")
        except Exception as e:
            logger.error(f"Failed to create main window: {e}")
            raise

    def _handle_bootstrap_error(self, error: Exception) -> None:
        """处理启动错误"""
        system_error = SystemError(
            message=f"Bootstrap failed: {str(error)}",
            component="RefactoredBootstrap",
            cause=error
        )
        self._error_handler.handle_error(system_error)

    def run(self) -> int:
        """运行应用程序"""
        if not self._initialized:
            if not self.initialize():
                return 1

        try:
            if self._app is None:
                raise SystemError("Qt application not initialized")

            return self._app.exec()
        except Exception as e:
            self._handle_bootstrap_error(e)
            return 1

    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止性能监控
            performance_monitor = get_performance_monitor()
            performance_monitor.stop_monitoring()

            # 清理主窗口
            if self._main_window:
                self._main_window.close()

            # 清理Qt应用
            if self._app:
                self._app.quit()

            logger.info("Bootstrap cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def create_bootstrap() -> RefactoredBootstrap:
    """创建启动引导器"""
    return RefactoredBootstrap()


def main() -> int:
    """主函数"""
    bootstrap = create_bootstrap()
    try:
        return bootstrap.run()
    finally:
        bootstrap.cleanup()


if __name__ == "__main__":
    sys.exit(main())
