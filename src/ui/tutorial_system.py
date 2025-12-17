"""
教程系统
提供交互式教程和用户引导功能
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class TutorialStep:
    """教程步骤"""

    def __init__(
        self,
        step_id: str,
        title: str,
        content: str,
        target_widget: QWidget | None = None,
        highlight_area: tuple | None = None,
        action_hint: str | None = None,
        difficulty: str = "easy",
        estimated_time: int = 30,
        prerequisites: list[str] | None = None,
        completion_criteria: dict[str, Any] | None = None,
    ):
        self.step_id = step_id
        self.title = title
        self.content = content
        self.target_widget = target_widget
        self.highlight_area = highlight_area  # (x, y, width, height)
        self.action_hint = action_hint
        self.difficulty = difficulty
        self.estimated_time = estimated_time
        self.prerequisites = prerequisites or []
        self.completion_criteria = completion_criteria or {}
        self.completed = False
        self.completion_time: datetime | None = None
        self.attempts = 0
        self.user_feedback: str | None = None


class TutorialDialog(QDialog):
    """教程对话框"""

    # 信号
    step_completed = Signal(str)  # step_id
    tutorial_completed = Signal()
    tutorial_skipped = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.theme_manager = ThemeManager()

        self.setWindowTitle("🎓 交互式教程")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        # 教程数据
        self.tutorial_steps: list[TutorialStep] = []
        self.current_step_index = 0

        self.init_ui()
        self.apply_theme()

        logger.info("教程对话框初始化完成")

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        self.title_label = QLabel("🎓 欢迎使用 VirtualChemLab")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 进度指示器
        self.progress_label = QLabel("步骤 1 / 5")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

        # 内容区域
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setMaximumHeight(200)
        layout.addWidget(self.content_text)

        # 操作提示
        self.hint_label = QLabel("")
        self.hint_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.hint_label.setStyleSheet("color: #4a90e2;")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        # 按钮
        button_layout = QHBoxLayout()

        self.previous_button = ModernButton("⬅️ 上一步")
        self.previous_button.clicked.connect(self.previous_step)
        self.previous_button.setEnabled(False)
        button_layout.addWidget(self.previous_button)

        self.next_button = ModernButton("下一步 ➡️")
        self.next_button.clicked.connect(self.next_step)
        button_layout.addWidget(self.next_button)

        self.skip_button = ModernButton("跳过教程")
        self.skip_button.clicked.connect(self.skip_tutorial)
        button_layout.addWidget(self.skip_button)

        self.finish_button = ModernButton("完成")
        self.finish_button.clicked.connect(self.finish_tutorial)
        self.finish_button.hide()
        button_layout.addWidget(self.finish_button)

        layout.addLayout(button_layout)

    def set_tutorial_steps(self, steps: list[TutorialStep]):
        """设置教程步骤"""
        self.tutorial_steps = steps
        self.current_step_index = 0
        self.update_display()

    def update_display(self):
        """更新显示"""
        if not self.tutorial_steps or self.current_step_index >= len(
            self.tutorial_steps
        ):
            return

        current_step = self.tutorial_steps[self.current_step_index]

        # 更新标题
        self.title_label.setText(f"🎓 {current_step.title}")

        # 更新进度
        self.progress_label.setText(
            f"步骤 {self.current_step_index + 1} / {len(self.tutorial_steps)}"
        )

        # 更新内容
        self.content_text.setText(current_step.content)

        # 更新提示
        if current_step.action_hint:
            self.hint_label.setText(f"💡 {current_step.action_hint}")
            self.hint_label.show()
        else:
            self.hint_label.hide()

        # 更新按钮状态
        self.previous_button.setEnabled(self.current_step_index > 0)

        if self.current_step_index == len(self.tutorial_steps) - 1:
            self.next_button.hide()
            self.finish_button.show()
        else:
            self.next_button.show()
            self.finish_button.hide()

    def next_step(self):
        """下一步"""
        if self.current_step_index < len(self.tutorial_steps):
            current_step = self.tutorial_steps[self.current_step_index]
            current_step.completed = True
            self.step_completed.emit(current_step.step_id)

            self.current_step_index += 1
            self.update_display()

    def previous_step(self):
        """上一步"""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.update_display()

    def skip_tutorial(self):
        """跳过教程"""
        self.tutorial_skipped.emit()
        self.accept()

    def finish_tutorial(self):
        """完成教程"""
        if self.current_step_index < len(self.tutorial_steps):
            current_step = self.tutorial_steps[self.current_step_index]
            current_step.completed = True
            self.step_completed.emit(current_step.step_id)

        self.tutorial_completed.emit()
        self.accept()

    def apply_theme(self):
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #16213e;
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12px;
                }
                QLabel {
                    color: #ffffff;
                }
            """
            )

            logger.info("教程主题应用成功")

        except Exception as e:
            logger.warning(f"应用教程主题失败: {e}")


class TutorialProgress:
    """教程进度"""

    def __init__(self):
        self.completed_steps: dict[str, list[str]] = {}  # tutorial_id -> step_ids
        self.step_times: dict[
            str, dict[str, float]
        ] = {}  # tutorial_id -> {step_id: time_taken}
        self.user_preferences: dict[str, Any] = {}
        self.difficulty_level: str = "medium"
        self.learning_style: str = "visual"
        self.last_accessed: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "completed_steps": self.completed_steps,
            "step_times": self.step_times,
            "user_preferences": self.user_preferences,
            "difficulty_level": self.difficulty_level,
            "learning_style": self.learning_style,
            "last_accessed": self.last_accessed.isoformat()
            if self.last_accessed
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TutorialProgress":
        """从字典创建"""
        progress = cls()
        progress.completed_steps = data.get("completed_steps", {})
        progress.step_times = data.get("step_times", {})
        progress.user_preferences = data.get("user_preferences", {})
        progress.difficulty_level = data.get("difficulty_level", "medium")
        progress.learning_style = data.get("learning_style", "visual")
        last_accessed = data.get("last_accessed")
        progress.last_accessed = (
            datetime.fromisoformat(last_accessed) if last_accessed else None
        )
        return progress


class TutorialManager:
    """教程管理器"""

    def __init__(self):
        self.tutorials: dict[str, list[TutorialStep]] = {}
        self.completed_tutorials: set[str] = set()
        self.current_tutorial: str | None = None
        self.progress = TutorialProgress()
        self.progress_file = Path("data/tutorial_progress.json")

        # 初始化默认教程
        self._init_default_tutorials()

        # 加载进度
        self._load_progress()

        logger.info("教程管理器初始化完成")

    def _init_default_tutorials(self):
        """初始化默认教程"""
        # 基础教程
        basic_tutorial = [
            TutorialStep(
                "welcome",
                "欢迎使用 VirtualChemLab",
                "欢迎来到 VirtualChemLab！这是一个具有游戏化交互体验的虚拟化学实验室。\n\n"
                "在这个教程中，您将学习如何：\n"
                "• 选择和使用实验模板\n"
                "• 进行游戏化交互操作\n"
                "• 使用物理模拟功能\n"
                "• 查看实验结果和进度",
                action_hint="点击'下一步'开始教程",
            ),
            TutorialStep(
                "experiment_selection",
                "选择实验",
                "首先，让我们学习如何选择一个实验。\n\n"
                "在左侧的实验列表中，您可以看到各种类型的化学实验：\n"
                "• 滴定实验\n"
                "• 合成实验\n"
                "• 晶体生长实验\n"
                "• 电化学实验\n\n"
                "每个实验都有不同的难度等级和预计时长。",
                action_hint="尝试点击一个实验项目",
            ),
            TutorialStep(
                "game_mode",
                "游戏模式",
                "VirtualChemLab 提供了独特的游戏化体验！\n\n"
                "游戏模式特性：\n"
                "• 物理模拟引擎\n"
                "• 粒子效果系统\n"
                "• 分数和连击系统\n"
                "• 稀有度物品系统\n\n"
                "按 Ctrl+G 可以切换游戏模式。",
                action_hint="尝试切换游戏模式",
            ),
            TutorialStep(
                "interaction",
                "交互操作",
                "在游戏模式下，您可以进行各种交互操作：\n\n"
                "鼠标操作：\n"
                "• 拖拽：移动实验器材\n"
                "• 点击：与物品交互\n"
                "• 滑动：快速移动物品\n\n"
                "键盘快捷键：\n"
                "• 空格键：震动所有物品\n"
                "• G键：切换重力\n"
                "• R键：重置所有物品",
                action_hint="尝试拖拽一个实验器材",
            ),
            TutorialStep(
                "completion",
                "完成实验",
                "恭喜！您已经完成了基础教程。\n\n"
                "现在您可以：\n"
                "• 开始您的第一个实验\n"
                "• 探索不同的实验类型\n"
                "• 享受游戏化的学习体验\n\n"
                "如果您需要帮助，可以随时查看帮助文档或重新运行教程。",
                action_hint="点击'完成'开始您的实验之旅",
            ),
        ]

        self.tutorials["basic"] = basic_tutorial

        # 高级功能教程
        advanced_tutorial = [
            TutorialStep(
                "physics_settings",
                "物理设置",
                "您可以自定义物理模拟参数：\n\n"
                "• 重力强度：控制物品下落速度\n"
                "• 摩擦力：影响物品滑动阻力\n"
                "• 弹跳系数：决定碰撞反弹程度\n"
                "• 碰撞检测：启用/禁用碰撞检测\n\n"
                "这些设置可以让您创建不同的实验环境。",
                action_hint="尝试调整物理参数",
            ),
            TutorialStep(
                "particle_effects",
                "粒子效果",
                "粒子效果系统为实验增添了视觉魅力：\n\n"
                "效果类型：\n"
                "• 闪烁：物品交互时的光效\n"
                "• 发光：物品激活时的光环\n"
                "• 爆炸：碰撞时的爆发效果\n"
                "• 轨迹：移动时的拖尾效果\n\n"
                "您可以在设置中调整粒子效果的数量和强度。",
                action_hint="观察粒子效果",
            ),
            TutorialStep(
                "performance_monitoring",
                "性能监控",
                "VirtualChemLab 内置了性能监控系统：\n\n"
                "监控指标：\n"
                "• CPU 使用率\n"
                "• 内存使用量\n"
                "• 帧率 (FPS)\n"
                "• 物理更新时间\n\n"
                "按 Ctrl+Shift+P 可以打开性能监控面板。",
                action_hint="打开性能监控面板",
            ),
        ]

        self.tutorials["advanced"] = advanced_tutorial

    def get_tutorial(self, tutorial_id: str) -> list[TutorialStep] | None:
        """获取教程"""
        return self.tutorials.get(tutorial_id)

    def start_tutorial(self, tutorial_id: str, parent: QWidget | None = None) -> bool:
        """开始教程"""
        tutorial_steps = self.get_tutorial(tutorial_id)
        if not tutorial_steps:
            logger.warning(f"教程不存在: {tutorial_id}")
            return False

        dialog = TutorialDialog(parent)
        dialog.set_tutorial_steps(tutorial_steps)

        # 连接信号
        dialog.step_completed.connect(self._on_step_completed)
        dialog.tutorial_completed.connect(
            lambda: self._on_tutorial_completed(tutorial_id)
        )
        dialog.tutorial_skipped.connect(lambda: self._on_tutorial_skipped(tutorial_id))

        self.current_tutorial = tutorial_id
        dialog.exec()

        return True

    def _on_step_completed(self, step_id: str):
        """处理步骤完成"""
        logger.info(f"教程步骤完成: {step_id}")

    def _on_tutorial_completed(self, tutorial_id: str):
        """处理教程完成"""
        self.completed_tutorials.add(tutorial_id)
        self.current_tutorial = None
        logger.info(f"教程完成: {tutorial_id}")

    def _on_tutorial_skipped(self, tutorial_id: str):
        """处理教程跳过"""
        self.current_tutorial = None
        logger.info(f"教程跳过: {tutorial_id}")

    def is_tutorial_completed(self, tutorial_id: str) -> bool:
        """检查教程是否已完成"""
        return tutorial_id in self.completed_tutorials

    def get_available_tutorials(self) -> list[str]:
        """获取可用教程列表"""
        return list(self.tutorials.keys())

    def reset_tutorial(self, tutorial_id: str):
        """重置教程"""
        if tutorial_id in self.completed_tutorials:
            self.completed_tutorials.remove(tutorial_id)
            logger.info(f"教程已重置: {tutorial_id}")

    def reset_all_tutorials(self):
        """重置所有教程"""
        self.completed_tutorials.clear()
        self.progress = TutorialProgress()
        self._save_progress()
        logger.info("所有教程已重置")

    def _load_progress(self):
        """加载进度"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.progress = TutorialProgress.from_dict(data)
                    logger.info("教程进度已加载")
        except Exception as e:
            logger.warning(f"加载教程进度失败: {e}")

    def _save_progress(self):
        """保存进度"""
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("教程进度已保存")
        except Exception as e:
            logger.error(f"保存教程进度失败: {e}")

    def get_recommended_tutorials(self) -> list[str]:
        """获取推荐教程"""
        # 基于用户进度和偏好推荐教程
        recommendations = []

        # 根据难度级别过滤
        for tutorial_id, steps in self.tutorials.items():
            if not steps:
                continue

            # 检查是否已完成
            if tutorial_id in self.completed_tutorials:
                continue

            # 检查难度匹配
            avg_difficulty = self._calculate_average_difficulty(steps)
            if self._is_difficulty_suitable(avg_difficulty):
                recommendations.append(tutorial_id)

        # 按优先级排序
        recommendations.sort(key=lambda x: self._get_tutorial_priority(x))
        return recommendations

    def _calculate_average_difficulty(self, steps: list[TutorialStep]) -> str:
        """计算平均难度"""
        difficulty_values = {"easy": 1, "medium": 2, "hard": 3}
        total_difficulty = sum(
            difficulty_values.get(step.difficulty, 2) for step in steps
        )
        avg_difficulty = total_difficulty / len(steps)

        if avg_difficulty <= 1.5:
            return "easy"
        elif avg_difficulty <= 2.5:
            return "medium"
        else:
            return "hard"

    def _is_difficulty_suitable(self, tutorial_difficulty: str) -> bool:
        """检查难度是否适合"""
        user_level = self.progress.difficulty_level
        difficulty_order = ["easy", "medium", "hard"]

        user_index = difficulty_order.index(user_level)
        tutorial_index = difficulty_order.index(tutorial_difficulty)

        # 允许同级或高一级的难度
        return tutorial_index <= user_index + 1

    def _get_tutorial_priority(self, tutorial_id: str) -> int:
        """获取教程优先级"""
        # 基于完成度和重要性计算优先级
        completion_rate = self.get_tutorial_completion_rate(tutorial_id)
        importance = self._get_tutorial_importance(tutorial_id)

        # 优先级 = 重要性 - 完成度（已完成的不推荐）
        return importance - completion_rate

    def get_tutorial_completion_rate(self, tutorial_id: str) -> float:
        """获取教程完成率"""
        if tutorial_id not in self.tutorials:
            return 0.0

        total_steps = len(self.tutorials[tutorial_id])
        completed_steps = len(self.progress.completed_steps.get(tutorial_id, []))

        return completed_steps / total_steps if total_steps > 0 else 0.0

    def _get_tutorial_importance(self, tutorial_id: str) -> int:
        """获取教程重要性"""
        importance_map = {
            "basic": 10,
            "advanced": 7,
            "experiment": 8,
            "physics": 6,
            "particles": 5,
        }
        return importance_map.get(tutorial_id, 5)

    def update_user_preferences(self, preferences: dict[str, Any]):
        """更新用户偏好"""
        self.progress.user_preferences.update(preferences)
        self._save_progress()
        logger.info("用户偏好已更新")

    def get_personalized_content(self, step: TutorialStep) -> str:
        """获取个性化内容"""
        content = step.content

        # 根据学习风格调整内容
        if self.progress.learning_style == "visual":
            # 添加视觉提示
            content = f"👀 {content}"
        elif self.progress.learning_style == "auditory":
            # 添加听觉提示
            content = f"🔊 {content}"
        elif self.progress.learning_style == "kinesthetic":
            # 添加动手提示
            content = f"✋ {content}"

        return content


# 全局教程管理器实例
_tutorial_manager: TutorialManager | None = None


def get_tutorial_manager() -> TutorialManager:
    """获取全局教程管理器"""
    global _tutorial_manager
    if _tutorial_manager is None:
        _tutorial_manager = TutorialManager()
    return _tutorial_manager
