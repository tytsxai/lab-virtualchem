"""集成管理器 - 统一管理所有增强功能"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget

from ..utils.interactive_validator import InteractiveValidator
from ..utils.logger import get_logger
from .cache_manager import cache_manager, scene_cache_manager
from .error_handler import ErrorContext, error_handler
from .experiment_history import ExperimentHistory
from .experiment_state_manager import ExperimentStateManager
from .interactive_scene import InteractiveExperimentScene
from .keyboard_shortcuts import KeyboardShortcutManager
from .performance_optimizer import get_performance_optimizer

logger = get_logger(__name__)


class IntegrationManager(QObject):
    """集成管理器"""

    # 信号
    system_ready = Signal()
    optimization_completed = Signal(dict)
    error_occurred = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 核心组件
        self.history: ExperimentHistory | None = None
        self.state_manager: ExperimentStateManager | None = None
        self.validator: InteractiveValidator | None = None
        self.shortcuts: KeyboardShortcutManager | None = None
        self.scene: InteractiveExperimentScene | None = None
        self._timers_started = False

        # 优化定时器
        self.optimization_timer = QTimer(self)
        self.optimization_timer.timeout.connect(self._perform_optimization)

        # 缓存清理定时器
        self.cache_cleanup_timer = QTimer(self)
        self.cache_cleanup_timer.timeout.connect(self._cleanup_cache)

        # 连接错误处理器信号
        error_handler.error_occurred.connect(self.error_occurred)

        logger.info("集成管理器已初始化")

    def initialize_components(
        self,
        scene: InteractiveExperimentScene | None = None,
        history: ExperimentHistory | None = None,
        state_manager: ExperimentStateManager | None = None,
        validator: InteractiveValidator | None = None,
        shortcuts: KeyboardShortcutManager | None = None,
    ) -> None:
        """初始化所有组件"""
        with ErrorContext(error_handler, "初始化组件"):
            self.scene = scene
            self.history = history
            self.state_manager = state_manager
            self.validator = validator
            self.shortcuts = shortcuts

            # 注册快捷键
            if self.shortcuts and isinstance(self.parent(), QWidget):
                parent_widget = self.parent()
                assert isinstance(parent_widget, QWidget)
                self.shortcuts.register_shortcuts(parent_widget)

            self._ensure_timers_started()
            logger.info("所有组件已初始化")
            self.system_ready.emit()

    def _ensure_timers_started(self) -> None:
        """在组件完成初始化后再启动后台定时器，避免模块导入副作用。"""
        if self._timers_started:
            return
        self.optimization_timer.start(300000)  # 5分钟
        self.cache_cleanup_timer.start(600000)  # 10分钟
        self._timers_started = True

    def save_experiment_state(self, experiment_id: str) -> str | None:
        """保存实验状态"""
        with ErrorContext(error_handler, "保存实验状态"):
            if not self.state_manager or not self.scene:
                error_handler.handle_warning("状态管理器或场景未初始化")
                return None

            try:
                state = self.state_manager.capture_state(experiment_id, self.scene)
                file_path = self.state_manager.save_to_file(state)

                # 缓存场景状态
                if self.scene:
                    scene_state = self.scene.get_state()
                    scene_cache_manager.cache_scene_state(experiment_id, scene_state)

                logger.info(f"实验状态已保存: {file_path}")
                return str(file_path)
            except Exception as e:
                error_handler.handle_error(e, "保存实验状态")
                return None

    def load_experiment_state(
        self, experiment_id: str, file_path: str | None = None
    ) -> bool:
        """加载实验状态"""
        with ErrorContext(error_handler, "加载实验状态"):
            if not self.state_manager or not self.scene:
                error_handler.handle_warning("状态管理器或场景未初始化")
                return False

            # 如果没有指定文件路径，尝试从缓存加载
            if not file_path:
                cached_state = scene_cache_manager.get_scene_state(experiment_id)
                if cached_state:
                    self.scene.load_state(cached_state)
                    logger.info(f"从缓存加载场景状态: {experiment_id}")
                    return True
                else:
                    error_handler.handle_warning("没有可用的保存状态")
                    return False

            # 从文件加载
            try:
                state = self.state_manager.load_from_file(file_path)
                self.state_manager.restore_state(state, self.scene)
                logger.info(f"实验状态已加载: {file_path}")
                return True
            except Exception as e:
                error_handler.handle_error(e, "加载实验状态")
                return False

    def validate_current_step(self, step_config: dict[str, Any]) -> tuple[bool, str]:
        """验证当前步骤"""
        with ErrorContext(error_handler, "验证当前步骤"):
            if not self.validator or not self.history:
                return False, "验证器或历史记录未初始化"

            try:
                # 获取当前操作状态
                drop_actions = self.history.get_drop_actions()
                click_counts = self.history.get_click_counts()

                # 执行验证
                check_config = step_config.get("interactive_check", {})
                check_type = check_config.get("type")

                if check_type == "drop":
                    return self.validator.validate_drop_action(
                        check_config, drop_actions
                    )
                elif check_type == "click":
                    return self.validator.validate_click_action(
                        check_config, click_counts
                    )
                elif check_type == "sequence":
                    # 获取最近的操作序列
                    recent_actions = self.history.get_recent_actions(
                        50
                    )  # 获取最近50个操作
                    # 转换为字符串序列
                    sequence_strings = [
                        f"{action.action_type.value}:{action.details.get('item_id', '')}"
                        for action in recent_actions
                    ]
                    return self.validator.validate_sequence_action(
                        check_config, sequence_strings
                    )
                elif check_type == "combined":
                    return self.validator.validate_combined_actions(
                        check_config, drop_actions, click_counts
                    )
                else:
                    return True, "无验证要求"
            except Exception as e:
                error_handler.handle_error(e, "验证当前步骤")
                return False, f"验证失败: {str(e)}"

    def record_action(self, action_type: str, **kwargs: Any) -> None:
        """记录操作"""
        with ErrorContext(error_handler, "记录操作"):
            if not self.history:
                return

            if action_type == "drag":
                self.history.record_drag(
                    kwargs["item_id"],
                    kwargs["from_pos"],
                    kwargs["to_pos"],
                    kwargs.get("step_id"),
                )
            elif action_type == "drop":
                self.history.record_drop(
                    kwargs["item_id"],
                    kwargs["zone_id"],
                    kwargs["position"],
                    kwargs.get("step_id"),
                )
            elif action_type == "click":
                self.history.record_click(
                    kwargs["item_id"], kwargs.get("position"), kwargs.get("step_id")
                )

    def get_system_statistics(self) -> dict[str, Any]:
        """获取系统统计"""
        optimizer = get_performance_optimizer()
        stats = {
            "performance": optimizer.check_performance(),
            "cache": cache_manager.get_statistics(),
            "scene_cache": scene_cache_manager.get_statistics(),
            "errors": error_handler.get_statistics(),
        }

        if self.history:
            stats["history"] = self.history.get_statistics()

        if self.validator:
            stats["validation"] = self.validator.get_validation_statistics()

        return stats

    def _perform_optimization(self) -> None:
        """执行性能优化"""
        with ErrorContext(error_handler, "性能优化"):
            optimizer = get_performance_optimizer()
            optimizer.full_optimization(
                scene=self.scene, history=self.history, state_manager=self.state_manager
            )

            # 发送优化完成信号
            stats = self.get_system_statistics()
            self.optimization_completed.emit(stats)

    def _cleanup_cache(self) -> None:
        """清理缓存"""
        with ErrorContext(error_handler, "缓存清理"):
            expired_count = cache_manager.cleanup_expired()
            scene_expired_count = scene_cache_manager.cleanup_expired()

            if expired_count > 0 or scene_expired_count > 0:
                logger.info(
                    f"缓存清理完成: 通用缓存 {expired_count} 项, 场景缓存 {scene_expired_count} 项"
                )

    def cleanup(self) -> None:
        """清理资源"""
        with ErrorContext(error_handler, "清理资源"):
            # 停止定时器
            self.optimization_timer.stop()
            self.cache_cleanup_timer.stop()

            # 保存缓存
            cache_manager.save_to_file("cache.json")
            scene_cache_manager.save_to_file("scene_cache.json")

            # 清理内存
            optimizer = get_performance_optimizer()
            optimizer.cleanup_memory()

            logger.info("集成管理器清理完成")

    def enable_debug_mode(self, enabled: bool = True) -> None:
        """启用调试模式"""
        if enabled:
            # 启用详细日志
            error_handler.set_logging_enabled(True)
            error_handler.set_dialog_enabled(False)  # 调试时不显示对话框

            # 减少优化间隔
            self._ensure_timers_started()
            self.optimization_timer.setInterval(60000)  # 1分钟

            logger.info("调试模式已启用")
        else:
            # 恢复正常设置
            error_handler.set_dialog_enabled(True)
            self.optimization_timer.setInterval(300000)  # 5分钟

            logger.info("调试模式已禁用")


# 全局集成管理器实例
integration_manager = IntegrationManager()
