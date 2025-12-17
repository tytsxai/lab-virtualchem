"""
布局比例分析器使用示例
演示如何在主窗口和其他组件中使用布局比例分析功能
"""

import logging
from typing import Any

from PySide6.QtWidgets import QApplication, QMainWindow

from .layout_ratio_integration import (
    get_layout_manager,
    register_layout_component,
    show_layout_analysis_dialog,
    unregister_layout_component,
)

logger = logging.getLogger(__name__)


class ExampleMainWindow(QMainWindow):
    """示例主窗口"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("布局比例分析器示例")
        self.setMinimumSize(1200, 800)

        # 获取布局管理器
        self.layout_manager = get_layout_manager()

        # 连接信号
        self.layout_manager.layout_analyzed.connect(self.on_layout_analyzed)
        self.layout_manager.layout_optimized.connect(self.on_layout_optimized)

        # 初始化UI
        self.init_ui()

        # 注册组件
        self.register_components()

    def init_ui(self) -> None:
        """初始化UI"""
        # 这里可以添加实际的UI初始化代码
        pass

    def register_components(self) -> None:
        """注册组件"""
        try:
            # 注册主窗口
            register_layout_component("main_window", self)

            # 注册其他组件
            # register_layout_component("experiment_list", self.experiment_list)
            # register_layout_component("content_area", self.content_area)

            logger.info("组件注册完成")

        except Exception as e:
            logger.error(f"组件注册失败: {e}", exc_info=True)

    def on_layout_analyzed(self, result: dict[str, Any]) -> None:
        """布局分析完成回调"""
        try:
            logger.info(f"布局分析完成: {result}")

            # 可以在这里处理分析结果
            accessibility_score = result.get("accessibility_score", 0)
            responsive_score = result.get("responsive_score", 0)

            # 更新状态栏或显示通知
            self.statusBar().showMessage(
                f"布局分析完成 - 无障碍评分: {accessibility_score:.1f}, 响应式评分: {responsive_score:.1f}"
            )

        except Exception as e:
            logger.error(f"处理布局分析结果失败: {e}", exc_info=True)

    def on_layout_optimized(self, component_name: str, result: dict[str, Any]) -> None:
        """布局优化完成回调"""
        try:
            status = result.get("status", "unknown")
            logger.info(f"布局优化完成: {component_name} - {status}")

            # 更新状态栏
            self.statusBar().showMessage(f"布局优化完成: {component_name} - {status}")

        except Exception as e:
            logger.error(f"处理布局优化结果失败: {e}", exc_info=True)

    def show_layout_analysis(self) -> None:
        """显示布局分析对话框"""
        try:
            show_layout_analysis_dialog(self)
        except Exception as e:
            logger.error(f"显示布局分析对话框失败: {e}", exc_info=True)

    def analyze_current_layout(self) -> None:
        """分析当前布局"""
        try:
            # 分析所有组件
            results = self.layout_manager.analyze_all_components()

            # 输出分析结果
            for name, result in results.items():
                logger.info(f"组件 {name} 分析结果: {result}")

        except Exception as e:
            logger.error(f"分析当前布局失败: {e}", exc_info=True)

    def optimize_current_layout(self) -> None:
        """优化当前布局"""
        try:
            # 优化所有组件
            results = self.layout_manager.optimize_all_components()

            # 输出优化结果
            for name, success in results.items():
                logger.info(f"组件 {name} 优化结果: {'成功' if success else '失败'}")

        except Exception as e:
            logger.error(f"优化当前布局失败: {e}", exc_info=True)

    def closeEvent(self, event: Any) -> None:
        """窗口关闭事件"""
        try:
            # 注销组件
            unregister_layout_component("main_window")

            # 调用父类方法
            super().closeEvent(event)

        except Exception as e:
            logger.error(f"窗口关闭处理失败: {e}", exc_info=True)


def create_example_application() -> QApplication:
    """创建示例应用程序"""
    app = QApplication([])

    # 创建主窗口
    main_window = ExampleMainWindow()
    main_window.show()

    return app


def run_layout_analysis_example() -> None:
    """运行布局分析示例"""
    try:
        # 创建应用程序
        app = create_example_application()

        # 获取布局管理器
        layout_manager = get_layout_manager()

        # 设置自动优化
        layout_manager.set_auto_optimize(True)
        layout_manager.set_optimization_threshold(0.8)

        # 分析当前布局
        main_window = app.activeWindow()
        if main_window and isinstance(main_window, ExampleMainWindow):
            main_window.analyze_current_layout()

        # 运行应用程序
        app.exec()

    except Exception as e:
        logger.error(f"运行布局分析示例失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 运行示例
    run_layout_analysis_example()
