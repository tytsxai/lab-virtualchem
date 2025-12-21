"""
快速提示系统
在用户使用过程中显示有用的提示
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuickTip(QWidget):
    """快速提示控件"""

    closed = Signal()

    def __init__(
        self, tip_text: str, duration: int = 5000, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.tip_text = tip_text
        self.duration = duration if duration > 0 else 5000  # 确保至少有5秒

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # 计算大小
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(tip_text)
        width = min(400, max(200, text_width + 60))
        height = 50

        self.setFixedSize(width, height)

        # 自动关闭定时器
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close_with_animation)
        if self.duration > 0:
            self.close_timer.start(self.duration)

    def show_at_bottom(self, parent_widget: QWidget | None = None):
        """在屏幕底部显示"""
        if parent_widget:
            # 在父控件底部
            parent_geometry = parent_widget.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + parent_geometry.height() - self.height() - 20
            self.move(x, y)
        else:
            # 在屏幕底部
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = screen.height() - self.height() - 50
            self.move(x, y)

        self.show()
        self.raise_()

        # 定时器已在构造函数中启动

    def close_with_animation(self):
        """带动画地关闭"""
        self.close()
        self.closed.emit()

    def paintEvent(self, _event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制阴影
        shadow_rect = self.rect().adjusted(2, 2, 2, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawRoundedRect(shadow_rect, 8, 8)

        # 绘制背景
        painter.setBrush(QColor(33, 150, 243))
        painter.drawRoundedRect(self.rect(), 8, 8)

        # 绘制图标
        icon_font = QFont()
        icon_font.setPointSize(16)
        painter.setFont(icon_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 10, 30, 30, Qt.AlignmentFlag.AlignCenter, "💡")

        # 绘制文本
        text_font = QFont()
        text_font.setPointSize(10)
        painter.setFont(text_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            45,
            0,
            self.width() - 55,
            self.height(),
            Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self.tip_text,
        )


class QuickTipsManager:
    """快速提示管理器"""

    _instance = None

    def __init__(self):
        self.shown_tips: set[str] = set()
        self.current_tip: QuickTip | None = None
        self.enabled = True

        # 加载已显示的提示
        self.load_shown_tips()

        logger.info("快速提示管理器初始化完成")

    @classmethod
    def instance(cls) -> QuickTipsManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def show_tip(
        self,
        tip_id: str,
        tip_text: str,
        force: bool = False,
        duration: int | None = None,
        parent: QWidget | None = None,
    ):
        """显示提示

        Args:
            tip_id: 提示ID（用于跟踪是否已显示）
            tip_text: 提示文本
            force: 是否强制显示（即使已显示过）
            duration: 显示时长（毫秒）。None 表示使用默认值，0 表示永久显示。
            parent: 父控件
        """
        if not self.enabled:
            return

        # 检查是否已显示过
        if not force and tip_id in self.shown_tips:
            return

        # 关闭当前提示
        if self.current_tip:
            self.current_tip.close()

        # 获取持续时间
        if duration is None:
            tip_duration = get_settings().get("tips.duration", 5000)
        else:
            tip_duration = duration

        # 创建并显示新提示
        self.current_tip = QuickTip(tip_text, tip_duration, parent)
        self.current_tip.closed.connect(lambda: self.on_tip_closed(tip_id))

        if parent:
            self.current_tip.show_at_bottom(parent)
        else:
            main_window = QApplication.activeWindow()
            self.current_tip.show_at_bottom(main_window)

        logger.debug(f"显示快速提示: {tip_id} (时长: {tip_duration}ms)")

    def on_tip_closed(self, tip_id: str):
        """提示关闭时的处理"""
        self.shown_tips.add(tip_id)
        self.save_shown_tips()
        self.current_tip = None

    def load_shown_tips(self):
        """加载已显示的提示"""
        try:
            tips_file = Path("data/shown_tips.txt")
            if tips_file.exists():
                with open(tips_file, encoding="utf-8") as f:
                    self.shown_tips = set(line.strip() for line in f if line.strip())
                logger.debug(f"已加载 {len(self.shown_tips)} 个已显示的提示")
        except Exception as e:
            logger.warning(f"加载已显示提示失败: {e}")

    def save_shown_tips(self):
        """保存已显示的提示"""
        try:
            tips_file = Path("data/shown_tips.txt")
            tips_file.parent.mkdir(parents=True, exist_ok=True)

            with open(tips_file, "w", encoding="utf-8") as f:
                for tip_id in self.shown_tips:
                    f.write(f"{tip_id}\n")

        except Exception as e:
            logger.warning(f"保存已显示提示失败: {e}")

    def reset_tips(self):
        """重置所有提示（清除已显示记录）"""
        self.shown_tips.clear()
        self.save_shown_tips()
        logger.info("已重置所有提示")

    def set_enabled(self, enabled: bool):
        """启用/禁用提示系统"""
        self.enabled = enabled
        logger.info(f"快速提示系统已{'启用' if enabled else '禁用'}")


# 预定义的提示
PREDEFINED_TIPS = {
    "first_run": "欢迎使用 VirtualChemLab！按 F1 查看帮助文档",
    "first_experiment": '双击实验可快速开始，或选中后点击"开始实验"按钮',
    "drag_drop": "您可以拖拽实验器材到实验区域进行操作",
    "shortcuts": "按 Ctrl+Shift+K 查看所有快捷键列表",
    "save_progress": "实验进度会自动保存，您可以随时继续",
    "knowledge_base": "按 Ctrl+K 打开知识库，查看化学知识和公式",
    "game_mode": "按 Ctrl+G 切换到游戏模式，获得更有趣的体验",
    "settings": "按 Ctrl+, 打开设置，个性化您的体验",
    "undo": "按 Ctrl+Z 可以撤销上一步操作",
    "reports": "完成实验后可以生成详细的实验报告",
    "achievements": "完成实验可获得成就和经验值，提升等级",
    "safety": "注意查看实验的安全警告，安全第一",
    "templates": "您可以创建自己的实验模板",
    "collaboration": "支持多人协作实验（需要配置服务器）",
    "export": "可以导出实验数据和报告为多种格式",
}


def show_quick_tip(
    tip_id: str,
    tip_text: str | None = None,
    force: bool = False,
    duration: int | None = None,
    parent: QWidget | None = None,
):
    """显示快速提示

    Args:
        tip_id: 提示ID（如果在预定义提示中则自动获取文本）
        tip_text: 提示文本（如果为None则从预定义中获取）
        force: 是否强制显示
        duration: 显示时长（毫秒）。None 表示使用默认值，0 表示永久显示。
        parent: 父控件
    """
    if tip_text is None:
        tip_text = PREDEFINED_TIPS.get(tip_id, tip_id)

    QuickTipsManager.instance().show_tip(tip_id, tip_text, force, duration, parent)
