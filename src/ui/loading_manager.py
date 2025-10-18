"""
加载管理器
提供统一的加载状态管理和用户体验优化
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .themes import ThemeManager

logger = get_logger(__name__)


class LoadingType(Enum):
    """加载类型"""

    SPINNER = "spinner"
    PROGRESS = "progress"
    PULSE = "pulse"
    WAVE = "wave"
    DOTS = "dots"
    CUSTOM = "custom"


class LoadingSize(Enum):
    """加载尺寸"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class LoadingTask:
    """加载任务"""

    id: str
    title: str
    description: str
    progress: float = 0.0
    total_steps: int = 0
    current_step: int = 0
    estimated_duration: int = 0  # 预计时长（秒）
    start_time: float = 0.0
    end_time: float | None = None
    status: str = "running"  # running, completed, failed, cancelled
    error: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LoadingSpinner(QWidget):
    """加载旋转器"""

    def __init__(self, size: LoadingSize = LoadingSize.MEDIUM, parent: QWidget | None = None):
        super().__init__(parent)

        self.size = size
        self.rotation = 0
        self.animation: QPropertyAnimation | None = None

        # 设置尺寸
        size_map = {
            LoadingSize.SMALL: 20,
            LoadingSize.MEDIUM: 40,
            LoadingSize.LARGE: 60,
        }
        self.spinner_size = size_map[size]
        self.setFixedSize(self.spinner_size, self.spinner_size)

        self.start_animation()

        logger.debug(f"创建加载旋转器: {size.value}")

    def start_animation(self):
        """开始动画"""
        self.animation = QPropertyAnimation(self, b"rotation")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(360)
        self.animation.setLoopCount(-1)  # 无限循环
        self.animation.start()

    def stop_animation(self):
        """停止动画"""
        if self.animation:
            self.animation.stop()

    def paintEvent(self, _event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算中心点
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 2

        # 绘制旋转的圆环
        pen = QPen(QColor(74, 144, 226), 3)
        painter.setPen(pen)

        # 绘制8个点
        for i in range(8):
            angle = (self.rotation + i * 45) % 360
            x = center_x + radius * 0.7 * painter.cos(angle * 3.14159 / 180)
            y = center_y + radius * 0.7 * painter.sin(angle * 3.14159 / 180)

            # 透明度渐变
            alpha = int(255 * (1 - i / 8))
            color = QColor(74, 144, 226, alpha)
            pen.setColor(color)
            painter.setPen(pen)

            painter.drawEllipse(int(x - 2), int(y - 2), 4, 4)


class LoadingDots(QWidget):
    """加载点动画"""

    def __init__(self, size: LoadingSize = LoadingSize.MEDIUM, parent: QWidget | None = None):
        super().__init__(parent)

        self.size = size
        self.animation: QPropertyAnimation | None = None

        # 设置尺寸
        size_map = {
            LoadingSize.SMALL: 60,
            LoadingSize.MEDIUM: 80,
            LoadingSize.LARGE: 100,
        }
        self.setFixedSize(size_map[size], 20)

        self.start_animation()

        logger.debug(f"创建加载点动画: {size.value}")

    def start_animation(self):
        """开始动画"""
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(1500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)
        self.animation.start()

    def stop_animation(self):
        """停止动画"""
        if self.animation:
            self.animation.stop()

    def paintEvent(self, _event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制3个点
        dot_size = 8
        spacing = 20
        start_x = (self.width() - 2 * spacing) // 2

        for i in range(3):
            x = start_x + i * spacing
            y = self.height() // 2

            # 计算透明度
            time_offset = i * 0.2
            alpha = int(255 * (0.3 + 0.7 * abs(painter.sin(time_offset * 3.14159))))

            color = QColor(74, 144, 226, alpha)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            painter.drawEllipse(x - dot_size // 2, y - dot_size // 2, dot_size, dot_size)


class LoadingWave(QWidget):
    """加载波浪动画"""

    def __init__(self, size: LoadingSize = LoadingSize.MEDIUM, parent: QWidget | None = None):
        super().__init__(parent)

        self.size = size
        self.animation: QPropertyAnimation | None = None

        # 设置尺寸
        size_map = {
            LoadingSize.SMALL: 60,
            LoadingSize.MEDIUM: 80,
            LoadingSize.LARGE: 100,
        }
        self.setFixedSize(size_map[size], 40)

        self.start_animation()

        logger.debug(f"创建加载波浪动画: {size.value}")

    def start_animation(self):
        """开始动画"""
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(2000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)
        self.animation.start()

    def stop_animation(self):
        """停止动画"""
        if self.animation:
            self.animation.stop()

    def paintEvent(self, _event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制波浪
        pen = QPen(QColor(74, 144, 226), 3)
        painter.setPen(pen)

        center_y = self.height() // 2
        amplitude = 15

        # 绘制波浪线
        points = []
        for x in range(0, self.width(), 2):
            y = center_y + amplitude * painter.sin(x * 0.1)
            points.append((x, y))

        if points:
            painter.drawPolyline(points)


class LoadingDialog(QWidget):
    """加载对话框"""

    task_completed = Signal(str)  # 任务ID
    task_failed = Signal(str, str)  # 任务ID, 错误信息
    task_cancelled = Signal(str)  # 任务ID

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.theme_manager = ThemeManager()
        self.current_task: LoadingTask | None = None

        # 窗口设置
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 150)

        # 动画
        self.fade_animation: QPropertyAnimation | None = None

        self.init_ui()
        self.apply_theme()

        logger.info("加载对话框初始化完成")

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 加载动画
        self.loading_widget = LoadingSpinner(LoadingSize.MEDIUM)
        layout.addWidget(self.loading_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel("加载中...")
        self.title_label.setObjectName("loadingTitle")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 描述
        self.description_label = QLabel("请稍候...")
        self.description_label.setObjectName("loadingDescription")
        self.description_label.setFont(QFont("Arial", 10))
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("loadingProgress")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("loadingStatus")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def apply_theme(self):
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: rgba(26, 26, 46, 0.95);
                    border: 2px solid #4a90e2;
                    border-radius: 10px;
                    color: #ffffff;
                }
                QLabel#loadingTitle {
                    color: #4a90e2;
                    font-weight: bold;
                }
                QLabel#loadingDescription {
                    color: #ffffff;
                    line-height: 1.3;
                }
                QLabel#loadingStatus {
                    color: #cccccc;
                    font-size: 9px;
                }
                QProgressBar#loadingProgress {
                    border: 1px solid #4a90e2;
                    border-radius: 5px;
                    background-color: rgba(255, 255, 255, 0.1);
                    text-align: center;
                }
                QProgressBar#loadingProgress::chunk {
                    background-color: #4a90e2;
                    border-radius: 4px;
                }
            """
            )

            logger.debug("加载对话框主题应用成功")

        except Exception as e:
            logger.warning(f"应用加载对话框主题失败: {e}")

    def show_task(self, task: LoadingTask):
        """显示任务"""
        self.current_task = task

        # 更新内容
        self.title_label.setText(task.title)
        self.description_label.setText(task.description)

        # 显示进度条
        if task.total_steps > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(task.total_steps)
            self.progress_bar.setValue(task.current_step)

            # 显示状态
            self.status_label.setVisible(True)
            self.status_label.setText(f"步骤 {task.current_step}/{task.total_steps}")
        else:
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)

        # 显示对话框
        self.show()
        self.center_on_parent()
        self.fade_in()

        logger.info(f"显示加载任务: {task.title}")

    def update_progress(self, current_step: int, total_steps: int | None = None):
        """更新进度"""
        if not self.current_task:
            return

        self.current_task.current_step = current_step
        if total_steps is not None:
            self.current_task.total_steps = total_steps

        # 更新进度条
        if self.current_task.total_steps > 0:
            self.progress_bar.setMaximum(self.current_task.total_steps)
            self.progress_bar.setValue(current_step)

            # 更新状态
            self.status_label.setText(f"步骤 {current_step}/{self.current_task.total_steps}")

            # 计算进度百分比
            progress = current_step / self.current_task.total_steps
            self.current_task.progress = progress

            # 更新描述
            if progress > 0:
                self.description_label.setText(f"进度: {progress:.1%}")

    def complete_task(self, success: bool = True, error: str | None = None):
        """完成任务"""
        if not self.current_task:
            return

        if success:
            self.current_task.status = "completed"
            self.current_task.end_time = 0.0  # 使用当前时间
            self.task_completed.emit(self.current_task.id)
            logger.info(f"加载任务完成: {self.current_task.title}")
        else:
            self.current_task.status = "failed"
            self.current_task.error = error
            self.current_task.end_time = 0.0
            self.task_failed.emit(self.current_task.id, error or "未知错误")
            logger.error(f"加载任务失败: {self.current_task.title} - {error}")

        # 延迟关闭
        QTimer.singleShot(1000, self.close_dialog)

    def cancel_task(self):
        """取消任务"""
        if not self.current_task:
            return

        self.current_task.status = "cancelled"
        self.current_task.end_time = 0.0
        self.task_cancelled.emit(self.current_task.id)

        logger.info(f"加载任务取消: {self.current_task.title}")
        self.close_dialog()

    def center_on_parent(self):
        """在父控件中居中"""
        if not self.parent():
            return

        parent_rect = self.parent().geometry()
        self.move(
            parent_rect.x() + (parent_rect.width() - self.width()) // 2,
            parent_rect.y() + (parent_rect.height() - self.height()) // 2,
        )

    def fade_in(self):
        """淡入动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def fade_out(self):
        """淡出动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()

    def close_dialog(self):
        """关闭对话框"""
        self.fade_out()


class LoadingManager:
    """加载管理器"""

    def __init__(self):
        self.active_tasks: dict[str, LoadingTask] = {}
        self.loading_dialog: LoadingDialog | None = None
        self.task_counter = 0

        logger.info("加载管理器初始化完成")

    def create_task(
        self,
        title: str,
        description: str,
        total_steps: int = 0,
        estimated_duration: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """创建加载任务"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        task = LoadingTask(
            id=task_id,
            title=title,
            description=description,
            total_steps=total_steps,
            estimated_duration=estimated_duration,
            start_time=0.0,  # 使用当前时间
            metadata=metadata or {},
        )

        self.active_tasks[task_id] = task

        logger.info(f"创建加载任务: {title}")
        return task_id

    def start_task(self, task_id: str, parent: QWidget | None = None) -> bool:
        """开始任务"""
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]
        task.start_time = 0.0  # 使用当前时间

        # 创建加载对话框
        if not self.loading_dialog:
            self.loading_dialog = LoadingDialog(parent)

        # 显示任务
        self.loading_dialog.show_task(task)

        logger.info(f"开始加载任务: {task.title}")
        return True

    def update_task_progress(self, task_id: str, current_step: int, total_steps: int | None = None) -> bool:
        """更新任务进度"""
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]

        # 更新进度
        if self.loading_dialog and self.loading_dialog.current_task and self.loading_dialog.current_task.id == task_id:
            self.loading_dialog.update_progress(current_step, total_steps)

        logger.debug(f"更新任务进度: {task.title} - {current_step}/{total_steps or task.total_steps}")
        return True

    def complete_task(self, task_id: str, success: bool = True, error: str | None = None) -> bool:
        """完成任务"""
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]

        # 完成任务
        if self.loading_dialog and self.loading_dialog.current_task and self.loading_dialog.current_task.id == task_id:
            self.loading_dialog.complete_task(success, error)

        # 从活跃任务中移除
        del self.active_tasks[task_id]

        logger.info(f"完成加载任务: {task.title}")
        return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]

        # 取消任务
        if self.loading_dialog and self.loading_dialog.current_task and self.loading_dialog.current_task.id == task_id:
            self.loading_dialog.cancel_task()

        # 从活跃任务中移除
        del self.active_tasks[task_id]

        logger.info(f"取消加载任务: {task.title}")
        return True

    def get_task(self, task_id: str) -> LoadingTask | None:
        """获取任务"""
        return self.active_tasks.get(task_id)

    def get_active_tasks(self) -> list[LoadingTask]:
        """获取活跃任务"""
        return list(self.active_tasks.values())

    def has_active_tasks(self) -> bool:
        """是否有活跃任务"""
        return len(self.active_tasks) > 0


class LoadingOverlay(QWidget):
    """加载覆盖层"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 加载组件
        self.loading_widget: QWidget | None = None
        self.message_label: QLabel | None = None

        self.init_ui()
        self.apply_theme()

        logger.info("加载覆盖层初始化完成")

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 加载动画
        self.loading_widget = LoadingSpinner(LoadingSize.LARGE)
        layout.addWidget(self.loading_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 消息标签
        self.message_label = QLabel("加载中...")
        self.message_label.setObjectName("loadingMessage")
        self.message_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def apply_theme(self):
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: rgba(0, 0, 0, 150);
                }
                QLabel#loadingMessage {
                    color: #ffffff;
                    font-weight: bold;
                }
            """
            )

            logger.debug("加载覆盖层主题应用成功")

        except Exception as e:
            logger.warning(f"应用加载覆盖层主题失败: {e}")

    def show_loading(self, message: str = "加载中..."):
        """显示加载"""
        self.message_label.setText(message)
        self.show()

        # 设置覆盖层大小
        if self.parent():
            self.setGeometry(self.parent().geometry())

    def hide_loading(self):
        """隐藏加载"""
        self.hide()


# 全局加载管理器实例
_loading_manager: LoadingManager | None = None


def get_loading_manager() -> LoadingManager:
    """获取全局加载管理器"""
    global _loading_manager
    if _loading_manager is None:
        _loading_manager = LoadingManager()
    return _loading_manager


# 便捷函数
def show_loading(title: str, description: str, parent: QWidget | None = None, total_steps: int = 0) -> str:
    """显示加载对话框"""
    manager = get_loading_manager()
    task_id = manager.create_task(title, description, total_steps)
    manager.start_task(task_id, parent)
    return task_id


def update_loading_progress(task_id: str, current_step: int, total_steps: int | None = None) -> bool:
    """更新加载进度"""
    return get_loading_manager().update_task_progress(task_id, current_step, total_steps)


def hide_loading(task_id: str, success: bool = True, error: str | None = None) -> bool:
    """隐藏加载对话框"""
    return get_loading_manager().complete_task(task_id, success, error)


def cancel_loading(task_id: str) -> bool:
    """取消加载"""
    return get_loading_manager().cancel_task(task_id)
