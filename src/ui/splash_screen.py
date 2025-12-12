"""
启动画面
提供美观的启动加载界面，显示加载进度和提示信息
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QLinearGradient,
    QPainter,
    QPaintEvent,
)
from PySide6.QtWidgets import QApplication, QWidget

from .. import __version__ as APP_VERSION
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModernSplashScreen(QWidget):
    """现代化启动画面"""

    finished = Signal()
    progress_updated = Signal(int, str)

    def __init__(self, width: int = 600, height: int = 400):
        super().__init__()
        self.progress = 0
        self.status_message = "正在初始化..."
        self.loading_angle = 0
        self._is_finishing = False  # 防止重复调用finish
        self._fade_animation: QPropertyAnimation | None = None  # 保存动画引用，防止被垃圾回收
        self.tips = [
            "💡 提示：使用快捷键 F1 随时查看帮助",
            "💡 提示：Ctrl+G 可以切换游戏模式，体验更有趣的实验",
            "💡 提示：拖拽实验器材可以进行操作，就像真实实验室一样",
            "💡 提示：实验进度会自动保存，随时可以继续",
            "💡 提示：查看知识库了解化学知识，Ctrl+K 快速打开",
            "💡 提示：注意查看实验的安全提示，安全第一",
            "💡 提示：使用 Ctrl+Z 可以撤销操作，不用担心出错",
            "💡 提示：按 F5 刷新实验列表，获取最新模板",
            "💡 提示：双击实验可快速开始，开启您的化学之旅",
            "💡 提示：右键菜单有更多选项，探索更多功能",
            "💡 提示：按 Ctrl+, 打开设置，个性化您的体验",
            "💡 提示：完成实验可获得成就和经验值",
            "💡 提示：遇到问题？按 Ctrl+Shift+D 打开开发者控制台",
        ]
        self.current_tip = random.choice(self.tips)

        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(width, height)

        # 居中显示
        self.center_on_screen()

        # 启动定时器用于动画
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(30)  # 约33 FPS

        logger.info("启动画面已创建")

    def center_on_screen(self) -> None:
        """窗口居中"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def set_progress(self, value: int, message: str = "") -> None:
        """设置进度

        Args:
            value: 进度值 (0-100)
            message: 状态消息
        """
        self.progress = max(0, min(100, value))
        if message:
            self.status_message = message
            logger.debug(f"启动进度: {value}% - {message}")
        self.progress_updated.emit(self.progress, self.status_message)
        self.update()
        QApplication.processEvents()  # 强制更新界面

        # 在某些关键点更换提示
        if self.progress in [25, 50, 75]:
            self.change_tip()

        # 达到 100% 时，延迟一会儿再关闭，让用户看到完成消息
        if self.progress >= 100 and not self._is_finishing:
            QTimer.singleShot(800, self.finish)  # 800ms 后开始关闭动画

    def update_animation(self) -> None:
        """更新动画"""
        self.loading_angle = (self.loading_angle + 6) % 360
        self.update()

    def finish(self) -> None:
        """完成启动"""
        # 防止重复调用
        if self._is_finishing:
            logger.debug("启动画面已在关闭中，忽略重复调用")
            return

        self._is_finishing = True
        self.animation_timer.stop()

        # 淡出动画 - 保存为实例变量防止被垃圾回收
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(500)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self._on_fade_finished)
        self._fade_animation.start()

        logger.info("启动画面开始关闭")

    def _on_fade_finished(self) -> None:
        """淡出动画完成"""
        logger.info("启动画面淡出完成")
        self.close()
        self.finished.emit()
        # 清理动画对象
        if self._fade_animation:
            self._fade_animation.deleteLater()
            self._fade_animation = None

    def closeEvent(self, event: Any) -> None:
        """关闭事件 - 确保清理资源"""
        try:
            # 停止动画定时器
            if self.animation_timer.isActive():
                self.animation_timer.stop()

            # 断开所有信号连接
            try:
                self.animation_timer.timeout.disconnect()
            except RuntimeError:
                # 信号已断开，忽略错误
                pass

            # 清理淡出动画
            if self._fade_animation:
                self._fade_animation.stop()
                self._fade_animation.deleteLater()
                self._fade_animation = None

            logger.info("启动画面资源已清理")
        except Exception as e:
            logger.error(f"清理启动画面资源失败: {e}", exc_info=True)
        finally:
            # 调用父类的关闭事件
            super().closeEvent(event)

    def paintEvent(self, _event: QPaintEvent) -> None:
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        self.draw_background(painter)

        # 绘制标题
        self.draw_title(painter)

        # 绘制加载动画
        self.draw_loading_animation(painter)

        # 绘制进度条
        self.draw_progress_bar(painter)

        # 绘制状态消息
        self.draw_status_message(painter)

        # 绘制提示
        self.draw_tip(painter)

        # 绘制版本信息
        self.draw_version(painter)

    def draw_background(self, painter: QPainter) -> None:
        """绘制背景"""
        # 绘制圆角矩形背景
        rect = self.rect()

        # 阴影效果
        shadow_rect = rect.adjusted(5, 5, 5, 5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawRoundedRect(shadow_rect, 20, 20)

        # 主背景 - 渐变色
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(45, 52, 68))
        gradient.setColorAt(1, QColor(30, 36, 48))

        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 20, 20)

        # 顶部装饰条
        header_gradient = QLinearGradient(0, 0, self.width(), 0)
        header_gradient.setColorAt(0, QColor(74, 144, 226, 200))
        header_gradient.setColorAt(0.5, QColor(80, 227, 194, 200))
        header_gradient.setColorAt(1, QColor(74, 144, 226, 200))

        painter.setBrush(header_gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), 5, 5, 5)

    def draw_title(self, painter: QPainter) -> None:
        """绘制标题"""
        # 标题文字
        title_font = QFont()
        title_font.setFamily("Microsoft YaHei UI" if hasattr(QFontDatabase, "addApplicationFont") else "Arial")
        title_font.setPointSize(28)
        title_font.setBold(True)
        painter.setFont(title_font)

        # 标题阴影
        painter.setPen(QColor(0, 0, 0, 60))
        painter.drawText(QRect(2, 52, self.width(), 60), Qt.AlignmentFlag.AlignCenter, "🧪 VirtualChemLab")

        # 标题文字
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRect(0, 50, self.width(), 60), Qt.AlignmentFlag.AlignCenter, "🧪 VirtualChemLab")

        # 副标题
        subtitle_font = QFont()
        subtitle_font.setFamily("Microsoft YaHei UI" if hasattr(QFontDatabase, "addApplicationFont") else "Arial")
        subtitle_font.setPointSize(12)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(QRect(0, 100, self.width(), 30), Qt.AlignmentFlag.AlignCenter, "虚拟化学实验室")

    def draw_loading_animation(self, painter: QPainter) -> None:
        """绘制加载动画"""
        center_x = self.width() // 2
        center_y = self.height() // 2 - 20
        radius = 40

        # 绘制旋转圆环
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(8):
            angle = (self.loading_angle + i * 45) % 360
            alpha = int(255 * (i + 1) / 8)

            # 计算点位置
            import math

            rad = math.radians(angle)
            x = center_x + radius * math.cos(rad)
            y = center_y + radius * math.sin(rad)

            # 绘制点
            painter.setBrush(QColor(74, 144, 226, alpha))
            painter.drawEllipse(int(x - 6), int(y - 6), 12, 12)

    def draw_progress_bar(self, painter: QPainter) -> None:
        """绘制进度条"""
        bar_height = 8
        bar_y = self.height() - 100
        margin = 60
        bar_width = self.width() - 2 * margin

        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(60, 70, 90))
        painter.drawRoundedRect(margin, bar_y, bar_width, bar_height, bar_height // 2, bar_height // 2)

        # 进度条
        if self.progress > 0:
            progress_width = int(bar_width * self.progress / 100)

            # 渐变进度条
            gradient = QLinearGradient(margin, bar_y, margin + progress_width, bar_y)
            gradient.setColorAt(0, QColor(74, 144, 226))
            gradient.setColorAt(1, QColor(80, 227, 194))

            painter.setBrush(gradient)
            painter.drawRoundedRect(margin, bar_y, progress_width, bar_height, bar_height // 2, bar_height // 2)

        # 进度百分比
        progress_font = QFont()
        progress_font.setPointSize(10)
        progress_font.setBold(True)
        painter.setFont(progress_font)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(QRect(0, bar_y + 15, self.width(), 20), Qt.AlignmentFlag.AlignCenter, f"{self.progress}%")

    def draw_status_message(self, painter: QPainter) -> None:
        """绘制状态消息"""
        status_font = QFont()
        status_font.setPointSize(10)
        painter.setFont(status_font)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(
            QRect(0, self.height() - 75, self.width(), 25), Qt.AlignmentFlag.AlignCenter, self.status_message
        )

    def draw_tip(self, painter: QPainter) -> None:
        """绘制提示"""
        tip_font = QFont()
        tip_font.setPointSize(9)
        painter.setFont(tip_font)
        painter.setPen(QColor(160, 160, 160))

        # 提示文字
        painter.drawText(
            QRect(20, self.height() - 50, self.width() - 40, 25),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.current_tip,
        )

    def draw_version(self, painter: QPainter) -> None:
        """绘制版本信息"""
        version_font = QFont()
        version_font.setPointSize(8)
        painter.setFont(version_font)
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(
            QRect(10, self.height() - 25, self.width() - 20, 20),
            Qt.AlignmentFlag.AlignRight,
            f"v{APP_VERSION}",
        )

    def change_tip(self) -> None:
        """更换提示"""
        old_tip = self.current_tip
        while self.current_tip == old_tip and len(self.tips) > 1:
            self.current_tip = random.choice(self.tips)
        self.update()


def create_splash_screen(width: int = 600, height: int = 400) -> ModernSplashScreen:
    """创建启动画面

    Args:
        width: 宽度
        height: 高度

    Returns:
        启动画面实例
    """
    splash = ModernSplashScreen(width, height)
    splash.show()
    return splash


def run_with_splash(main_func: Callable[..., int], *args: Any, **kwargs: Any) -> int:
    """在启动画面中运行主函数

    Args:
        main_func: 主函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        退出代码
    """
    splash = create_splash_screen()

    # 模拟加载过程
    stages = [
        (10, "正在加载配置..."),
        (20, "正在检查依赖..."),
        (30, "正在初始化服务..."),
        (50, "正在加载资源..."),
        (70, "正在准备界面..."),
        (90, "正在完成初始化..."),
        (100, "启动完成!"),
    ]

    for progress, message in stages:
        splash.set_progress(progress, message)
        QTimer.singleShot(100, lambda: None)  # 短暂延迟以显示进度

    # 运行主函数
    try:
        result = main_func(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"启动失败: {e}")
        return 1
    finally:
        if splash.isVisible():
            splash.finish()
