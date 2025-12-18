"""
增强的启动画面
提供更详细的加载进度和预估时间
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QLabel, QProgressBar, QSplashScreen, QVBoxLayout, QWidget

from .. import __version__ as APP_VERSION
from ..utils.logger import get_logger
from ..utils.startup_optimizer import ProgressEstimator

logger = get_logger(__name__)


class EnhancedSplashScreen(QSplashScreen):
    """增强的启动画面"""

    finished = Signal()

    def __init__(self):
        super().__init__()

        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 进度估算器
        self.progress_estimator = ProgressEstimator()

        # 初始化步骤（带预估时间）
        self.progress_estimator.add_step("init_logging", 0.3)
        self.progress_estimator.add_step("check_dependencies", 1.0)
        self.progress_estimator.add_step("load_config", 0.5)
        self.progress_estimator.add_step("setup_container", 0.8)
        self.progress_estimator.add_step("load_preferences", 0.4)
        self.progress_estimator.add_step("init_feedback", 0.3)
        self.progress_estimator.add_step("init_help", 0.3)
        self.progress_estimator.add_step("create_window", 1.0)

        # UI 组件
        self.title_label: QLabel | None = None
        self.status_label: QLabel | None = None
        self.progress_bar: QProgressBar | None = None
        self.tip_label: QLabel | None = None
        self.time_label: QLabel | None = None

        # 提示信息
        self.tips = [
            "💡 按 F1 可以随时查看帮助文档",
            "💡 按 Ctrl+G 切换游戏模式，体验更有趣的实验",
            "💡 按 Ctrl+P 打开命令面板，快速访问功能",
            "💡 支持拖拽实验器材进行操作",
            "💡 实验数据会自动保存，无需担心丢失",
            "💡 按 Ctrl+Z 可以撤销上一步操作",
            "💡 在设置中可以调整界面语言和主题",
            "💡 首次使用？查看欢迎向导了解核心功能",
            "💡 支持触摸操作：单击、拖拽、双击、长按",
            "💡 按 Space 键可以震动实验器材",
            "💡 按 G 键可以切换重力效果",
            "💡 按 R 键可以重置所有器材位置",
            "💡 完成实验可以获得成就和经验值",
            "💡 支持导出实验报告为 PDF 格式",
            "💡 可以创建自己的实验模板",
        ]

        self.current_tip_index = 0

        # 初始化UI
        self.init_ui()

        # 定时更新提示
        self.tip_timer = QTimer(self)
        self.tip_timer.timeout.connect(self.rotate_tip)
        self.tip_timer.start(3000)  # 每3秒更换提示

        # 定时更新预估时间
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_remaining_time)

        logger.info("增强启动画面初始化完成")

    def init_ui(self):
        """初始化UI"""
        # 设置大小
        self.setFixedSize(600, 400)

        # 创建中心控件
        central = QWidget(self)
        central.setGeometry(0, 0, 600, 400)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel("🧪 VirtualChemLab")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #0066CC;")
        layout.addWidget(self.title_label)

        # 版本
        version_label = QLabel(f"v{APP_VERSION} - 虚拟化学实验室")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setFont(QFont("Arial", 10))
        version_label.setStyleSheet("color: #666;")
        layout.addWidget(version_label)

        # 间距
        layout.addSpacing(20)

        # 状态标签
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 11))
        self.status_label.setStyleSheet("color: #333;")
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #f0f0f0;
                height: 28px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066CC,
                    stop:1 #00C853
                );
                border-radius: 6px;
            }
        """
        )
        layout.addWidget(self.progress_bar)

        # 预估时间
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("Arial", 9))
        self.time_label.setStyleSheet("color: #999;")
        layout.addWidget(self.time_label)

        # 间距
        layout.addSpacing(20)

        # 提示标签
        self.tip_label = QLabel(self.tips[0])
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setWordWrap(True)
        self.tip_label.setFont(QFont("Arial", 10))
        self.tip_label.setStyleSheet(
            """
            background-color: #E3F2FD;
            color: #1976D2;
            padding: 15px;
            border-radius: 8px;
        """
        )
        layout.addWidget(self.tip_label)

        # 底部版权
        copyright_label = QLabel("© 2025 VirtualChemLab Team")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setFont(QFont("Arial", 8))
        copyright_label.setStyleSheet("color: #999;")
        layout.addWidget(copyright_label)

        # 设置样式
        central.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border-radius: 16px;
            }
        """
        )

    def paintEvent(self, _event):
        """绘制背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制阴影
        shadow_rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawRoundedRect(shadow_rect, 16, 16)

        # 绘制主背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(255, 255, 255))
        gradient.setColorAt(1, QColor(240, 245, 250))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 16, 16)

    def rotate_tip(self):
        """轮换提示"""
        self.current_tip_index = (self.current_tip_index + 1) % len(self.tips)
        self.tip_label.setText(self.tips[self.current_tip_index])

        # 淡入淡出动画
        self.animate_fade_in(self.tip_label)

    def animate_fade_in(self, widget: QWidget):
        """淡入动画"""
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(300)
        animation.setStartValue(0.3)
        animation.setEndValue(1.0)
        animation.start()

        # 保持引用避免被垃圾回收
        widget.setProperty("_fade_animation", animation)

    def start_progress(self):
        """开始进度追踪"""
        self.progress_estimator.start()
        self.time_timer.start(500)  # 每0.5秒更新一次时间

    def set_progress(self, value: int, message: str, step_name: str | None = None):
        """设置进度

        Args:
            value: 进度值 (0-100)
            message: 状态消息
            step_name: 步骤名称（用于自动计算进度）
        """
        if step_name:
            # 使用估算器自动计算进度
            auto_value = self.progress_estimator.complete_step(step_name)
            self.progress_bar.setValue(int(auto_value))
        else:
            self.progress_bar.setValue(value)

        self.status_label.setText(message)
        logger.debug(f"启动进度: {value}% - {message}")

        # 100% 时自动关闭
        if value >= 100:
            QTimer.singleShot(800, self.close_splash)

    def update_remaining_time(self):
        """更新预估剩余时间"""
        remaining = self.progress_estimator.get_estimated_remaining_time()

        if remaining > 0:
            self.time_label.setText(f"预计剩余时间: {remaining:.1f} 秒")
        else:
            self.time_label.setText("")

    def close_splash(self):
        """关闭启动画面"""
        self.tip_timer.stop()
        self.time_timer.stop()

        # 淡出动画
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(400)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.finished.connect(self.finish_close)
        animation.start()

        # 保持引用
        self.setProperty("_close_animation", animation)

    def finish_close(self):
        """完成关闭"""
        self.finished.emit()
        self.close()
        logger.info("启动画面已关闭")


def create_enhanced_splash_screen() -> EnhancedSplashScreen:
    """创建增强的启动画面"""
    splash = EnhancedSplashScreen()

    # 居中显示
    from PySide6.QtWidgets import QApplication

    screen = QApplication.primaryScreen().geometry()
    splash.move(
        (screen.width() - splash.width()) // 2, (screen.height() - splash.height()) // 2
    )

    return splash
