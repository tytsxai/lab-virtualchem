"""
布局比例分析器集成模块
提供与主窗口和其他UI组件的集成功能
"""

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from .layout_ratio_analyzer import (
    analyze_layout_ratios,
    batch_optimize_all_layouts,
    get_layout_analyzer,
    get_layout_optimizer,
    optimize_dialog_layout,
    optimize_main_window_layout,
)
from .layout_ratio_dialog import LayoutRatioDialog

logger = logging.getLogger(__name__)


class LayoutRatioManager(QObject):
    """布局比例管理器"""

    # 信号
    layout_analyzed = Signal(dict)  # 分析完成
    layout_optimized = Signal(str, dict)  # 优化完成
    preferences_changed = Signal(str, object)  # 偏好设置变化

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 获取分析器和优化器
        self.analyzer = get_layout_analyzer()
        self.optimizer = get_layout_optimizer()

        # 连接信号
        self.analyzer.analysis_completed.connect(self.layout_analyzed.emit)

        # 注册的组件
        self._registered_components: dict[str, QWidget] = {}

        # 自动优化设置
        self._auto_optimize_enabled = True
        self._optimization_threshold = 0.8  # 评分低于80%时自动优化

    def register_component(self, name: str, widget: QWidget) -> None:
        """注册组件"""
        try:
            self._registered_components[name] = widget
            logger.info(f"组件已注册: {name}")

            # 如果启用自动优化，立即分析
            if self._auto_optimize_enabled:
                self.analyze_and_optimize_component(name, widget)

        except Exception as e:
            logger.error(f"注册组件失败 {name}: {e}", exc_info=True)

    def unregister_component(self, name: str) -> None:
        """注销组件"""
        try:
            if name in self._registered_components:
                del self._registered_components[name]
                logger.info(f"组件已注销: {name}")
        except Exception as e:
            logger.error(f"注销组件失败 {name}: {e}", exc_info=True)

    def analyze_component(self, name: str) -> dict[str, Any]:
        """分析组件布局"""
        try:
            if name not in self._registered_components:
                logger.warning(f"组件未注册: {name}")
                return {}

            # 执行分析
            analysis_result = analyze_layout_ratios()

            # 提取组件相关的结果
            component_result = {
                "component_name": name,
                "timestamp": analysis_result.get("timestamp"),
                "screen_info": analysis_result.get("screen_info"),
                "accessibility_score": analysis_result.get("accessibility_score", 0),
                "golden_ratio_compliance": analysis_result.get("golden_ratio_compliance", 0),
                "responsive_score": analysis_result.get("responsive_score", 0),
            }

            logger.info(f"组件分析完成: {name}")
            return component_result

        except Exception as e:
            logger.error(f"分析组件失败 {name}: {e}", exc_info=True)
            return {}

    def optimize_component(self, name: str) -> bool:
        """优化组件布局"""
        try:
            if name not in self._registered_components:
                logger.warning(f"组件未注册: {name}")
                return False

            widget = self._registered_components[name]

            # 根据组件类型选择优化方法
            if name == "main_window":
                success = optimize_main_window_layout(widget)
            else:
                success = optimize_dialog_layout(widget, name)

            if success:
                logger.info(f"组件优化完成: {name}")
                self.layout_optimized.emit(name, {"status": "success"})
            else:
                logger.warning(f"组件优化失败: {name}")
                self.layout_optimized.emit(name, {"status": "failed"})

            return success

        except Exception as e:
            logger.error(f"优化组件失败 {name}: {e}", exc_info=True)
            self.layout_optimized.emit(name, {"status": "error", "error": str(e)})
            return False

    def analyze_and_optimize_component(self, name: str, _widget: QWidget) -> dict[str, Any]:
        """分析并优化组件"""
        try:
            # 先分析
            analysis_result = self.analyze_component(name)

            # 检查是否需要优化
            needs_optimization = False
            accessibility_score = analysis_result.get("accessibility_score", 0)
            responsive_score = analysis_result.get("responsive_score", 0)

            if (
                accessibility_score < self._optimization_threshold * 10
                or responsive_score < self._optimization_threshold * 100
            ):
                needs_optimization = True

            # 如果需要优化且启用自动优化
            if needs_optimization and self._auto_optimize_enabled:
                optimization_success = self.optimize_component(name)
                analysis_result["optimization_applied"] = optimization_success
            else:
                analysis_result["optimization_applied"] = False

            return analysis_result

        except Exception as e:
            logger.error(f"分析并优化组件失败 {name}: {e}", exc_info=True)
            return {}

    def analyze_all_components(self) -> dict[str, dict[str, Any]]:
        """分析所有注册的组件"""
        try:
            results = {}
            for name in self._registered_components:
                results[name] = self.analyze_component(name)

            logger.info(f"所有组件分析完成，共 {len(results)} 个组件")
            return results

        except Exception as e:
            logger.error(f"分析所有组件失败: {e}", exc_info=True)
            return {}

    def optimize_all_components(self) -> dict[str, bool]:
        """优化所有注册的组件"""
        try:
            # 准备批量优化数据
            widgets_to_optimize = []
            for name, widget in self._registered_components.items():
                widgets_to_optimize.append((widget, name))

            # 执行批量优化
            results = batch_optimize_all_layouts(widgets_to_optimize)

            # 发出优化完成信号
            for name, success in results.items():
                self.layout_optimized.emit(name, {"status": "success" if success else "failed"})

            logger.info(f"所有组件优化完成，成功: {sum(results.values())}/{len(results)}")
            return results

        except Exception as e:
            logger.error(f"优化所有组件失败: {e}", exc_info=True)
            return {}

    def show_analysis_dialog(self, parent: QWidget | None = None) -> None:
        """显示分析对话框"""
        try:
            dialog = LayoutRatioDialog(parent)
            dialog.layout_optimized.connect(self.layout_optimized.emit)
            dialog.show()
            logger.info("布局分析对话框已显示")
        except Exception as e:
            logger.error(f"显示分析对话框失败: {e}", exc_info=True)

    def set_auto_optimize(self, enabled: bool) -> None:
        """设置自动优化"""
        self._auto_optimize_enabled = enabled
        logger.info(f"自动优化已{'启用' if enabled else '禁用'}")

    def set_optimization_threshold(self, threshold: float) -> None:
        """设置优化阈值"""
        self._optimization_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"优化阈值已设置为: {self._optimization_threshold}")

    def get_registered_components(self) -> list[str]:
        """获取已注册的组件列表"""
        return list(self._registered_components.keys())

    def get_component_info(self, name: str) -> dict[str, Any] | None:
        """获取组件信息"""
        if name not in self._registered_components:
            return None

        widget = self._registered_components[name]
        return {
            "name": name,
            "type": type(widget).__name__,
            "visible": widget.isVisible(),
            "size": widget.size(),
            "position": widget.pos(),
        }

    def export_component_report(self, name: str, file_path: str) -> bool:
        """导出组件报告"""
        try:
            if name not in self._registered_components:
                logger.warning(f"组件未注册: {name}")
                return False

            # 获取分析结果
            self.analyze_component(name)

            # 导出报告
            from .layout_ratio_analyzer import export_layout_analysis_report

            return export_layout_analysis_report(file_path)

        except Exception as e:
            logger.error(f"导出组件报告失败 {name}: {e}", exc_info=True)
            return False


# 全局布局比例管理器实例
_global_layout_manager: LayoutRatioManager | None = None


def get_layout_manager() -> LayoutRatioManager:
    """获取全局布局比例管理器实例"""
    global _global_layout_manager
    if _global_layout_manager is None:
        _global_layout_manager = LayoutRatioManager()
    return _global_layout_manager


def register_layout_component(name: str, widget: QWidget) -> None:
    """注册布局组件"""
    manager = get_layout_manager()
    manager.register_component(name, widget)


def unregister_layout_component(name: str) -> None:
    """注销布局组件"""
    manager = get_layout_manager()
    manager.unregister_component(name)


def analyze_layout_component(name: str) -> dict[str, Any]:
    """分析布局组件"""
    manager = get_layout_manager()
    return manager.analyze_component(name)


def optimize_layout_component(name: str) -> bool:
    """优化布局组件"""
    manager = get_layout_manager()
    return manager.optimize_component(name)


def show_layout_analysis_dialog(parent: QWidget | None = None) -> None:
    """显示布局分析对话框"""
    manager = get_layout_manager()
    manager.show_analysis_dialog(parent)


def set_auto_layout_optimize(enabled: bool) -> None:
    """设置自动布局优化"""
    manager = get_layout_manager()
    manager.set_auto_optimize(enabled)


def get_registered_layout_components() -> list[str]:
    """获取已注册的布局组件列表"""
    manager = get_layout_manager()
    return manager.get_registered_components()
