"""
实验视图
显示实验步骤、操作界面、曲线等
"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.di_container import DIContainer
from ..core.experiment_controller import ExperimentController
from ..core.security.input_validator import validate_and_sanitize_input
from ..models.experiment import CheckPoint, ExperimentTemplate
from ..models.user_record import UserRecord
from ..utils.i18n import I18n
from ..utils.logger import get_logger
from .equipment_library import CompactEquipmentLibrary
from .interactive_scene import (
    ExperimentSceneBuilder,
    InteractiveExperimentScene,
    InteractiveExperimentView,
)

logger = get_logger(__name__)


class ExperimentView(QWidget):
    """实验视图类"""

    experiment_finished = Signal(UserRecord)
    exp_gained = Signal(int)  # 经验获得信号

    def __init__(
        self,
        template: ExperimentTemplate,
        container: DIContainer | None = None,
        user_id: str = "student_001",
        enable_interactive: bool = True,
    ):
        super().__init__()
        self.template = template
        self.user_id = user_id
        self.enable_interactive = enable_interactive

        # 使用DI容器
        if container is None:
            from ..core.service_registration import get_configured_container

            container = get_configured_container()

        self.container = container
        self.i18n = container.resolve(I18n)

        # 创建实验控制器（瞬态，不从容器解析）
        self.controller = ExperimentController(template, user_id=user_id)

        self.input_widgets: dict[str, Any] = {}

        # 交互式场景组件
        self.interactive_scene: InteractiveExperimentScene | None = None
        self.interactive_view: InteractiveExperimentView | None = None
        self.equipment_library: CompactEquipmentLibrary | None = None

        self.init_ui()
        self._bind_shortcuts()
        self.controller.start_experiment()
        self.update_step_display()

    def init_ui(self) -> None:
        """初始化用户界面"""
        # 设置样式
        self.setStyleSheet(
            """
            QWidget {
                background-color: #f5f6fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
            QTextEdit {
                border: 1px solid #d1d8e0;
                border-radius: 6px;
                padding: 8px;
                background-color: #ffffff;
                font-size: 11pt;
            }
            QLineEdit {
                border: 2px solid #d1d8e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QComboBox {
                border: 2px solid #d1d8e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QProgressBar {
                border: 2px solid #d1d8e0;
                border-radius: 8px;
                text-align: center;
                height: 30px;
                background-color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 6px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 11pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
            QPushButton:pressed {
                background-color: #bdc3c7;
            }
        """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 实验信息区
        info_box = self.create_info_box()
        main_layout.addWidget(info_box)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("进度: %p% (%v/%m)")
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 13px;
                background-color: #f8f9fa;
                color: #212529;
                height: 28px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #00a2e8);
                border-radius: 6px;
            }
        """
        )
        main_layout.addWidget(self.progress_bar)

        # 可观测状态条（时间/步骤/错误/完成率）
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        # 主内容区域 - 使用分割器分为左右两部分
        if self.enable_interactive and self._should_show_interactive():
            content_splitter = QSplitter(Qt.Orientation.Horizontal)

            # 左侧：交互式场景
            self.interactive_view = self._create_interactive_scene()
            if self.interactive_view:
                content_splitter.addWidget(self.interactive_view)

            # 右侧：步骤内容和器材库
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(10)

            # 步骤内容区(可滚动)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(300)
            scroll.setStyleSheet(
                """
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background-color: #ecf0f1;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #bdc3c7;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #95a5a6;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
            """
            )

            self.step_content = QWidget()
            self.step_content.setStyleSheet("background-color: transparent;")
            self.step_layout = QVBoxLayout(self.step_content)
            self.step_layout.setSpacing(15)
            self.step_layout.setContentsMargins(5, 5, 5, 5)
            scroll.setWidget(self.step_content)
            right_layout.addWidget(scroll)

            # 器材库（紧凑型）
            self.equipment_library = self._create_equipment_library()
            if self.equipment_library:
                right_layout.addWidget(self.equipment_library)

            content_splitter.addWidget(right_widget)

            # 设置分割比例（约65%场景，35%步骤）
            content_splitter.setStretchFactor(0, 13)
            content_splitter.setStretchFactor(1, 7)
            content_splitter.setSizes([650, 350])

            main_layout.addWidget(content_splitter)
        else:
            # 传统模式：只有步骤内容区
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(400)
            scroll.setStyleSheet(
                """
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background-color: #ecf0f1;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #bdc3c7;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #95a5a6;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
            """
            )

            self.step_content = QWidget()
            self.step_content.setStyleSheet("background-color: transparent;")
            self.step_layout = QVBoxLayout(self.step_content)
            self.step_layout.setSpacing(15)
            self.step_layout.setContentsMargins(5, 5, 5, 5)
            scroll.setWidget(self.step_content)

            main_layout.addWidget(scroll)

        # 导航按钮区
        nav_box = self.create_navigation_box()
        main_layout.addWidget(nav_box)

        # 🆕 增强反馈区域
        from .widgets.enhanced_feedback_widget import EnhancedFeedbackWidget

        self.enhanced_feedback = EnhancedFeedbackWidget(self)
        main_layout.addWidget(self.enhanced_feedback)

        # 旧反馈标签（保留兼容性，但隐藏）
        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet("padding: 10px; border-radius: 5px;")
        self.feedback_label.hide()  # 隐藏，使用增强反馈
        # main_layout.addWidget(self.feedback_label)  # 不添加到布局

    def create_status_bar(self) -> QWidget:
        """创建实验可观测状态条"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self.status_time = QLabel("⏱️ 0s")
        self.status_time.setFont(font)
        self.status_steps = QLabel("📋 0/0")
        self.status_steps.setFont(font)
        self.status_mistakes = QLabel("⚠️ 0")
        self.status_mistakes.setFont(font)
        self.status_completion = QLabel("✅ 0%")
        self.status_completion.setFont(font)

        for w in (
            self.status_time,
            self.status_steps,
            self.status_mistakes,
            self.status_completion,
        ):
            w.setStyleSheet(
                "padding: 6px 10px; background: #ffffff; border: 1px solid #e1dfdd; border-radius: 6px;"
            )

        layout.addWidget(self.status_time)
        layout.addWidget(self.status_steps)
        layout.addWidget(self.status_mistakes)
        layout.addWidget(self.status_completion)
        layout.addStretch()

        # 初始化一次
        self.update_status_bar()
        return widget

    def update_status_bar(self) -> None:
        """更新状态条数据"""
        try:
            # 进度信息
            progress = self.controller.get_progress()
            duration = int(self.controller.get_experiment_duration())

            self.status_time.setText(f"⏱️ {duration}s")
            self.status_steps.setText(
                f"📋 {progress['current_step'] + 1}/{progress['total_steps']}"
            )
            if "total_mistakes" in progress:
                self.status_mistakes.setText(f"⚠️ {progress['total_mistakes']}")
            if "completion_rate" in progress:
                self.status_completion.setText(f"✅ {progress['completion_rate']:.0f}%")
        except Exception:
            # 发生异常时不影响主流程
            pass

    def create_info_box(self) -> QGroupBox:
        """创建实验信息框"""
        group = QGroupBox(self.i18n.t("ui.experiment_info"))
        layout = QVBoxLayout()

        title_label = QLabel(f"<b>{self.template.title}</b>")
        title_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(title_label)

        desc_label = QLabel(self.template.description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        meta_text = f"{self.i18n.t('ui.difficulty')}: {self.i18n.t(f'difficulty.{self.template.difficulty}')} | "
        meta_text += f"{self.i18n.t('ui.duration')}: {self.template.duration_minutes} {self.i18n.t('ui.minutes')}"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: gray;")
        layout.addWidget(meta_label)

        group.setLayout(layout)
        return group

    def create_navigation_box(self) -> QWidget:
        """创建导航按钮区"""
        widget = QWidget()
        widget.setStyleSheet(
            """
            QWidget {
                background-color: transparent;
                border: none;
            }
        """
        )
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 10, 0, 0)

        self.prev_btn = QPushButton("⬅️ " + self.i18n.t("ui.previous"))
        self.prev_btn.clicked.connect(self.on_previous)
        self.prev_btn.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border: 2px solid #95a5a6;
                color: #2c3e50;
                font-weight: bold;
                padding: 12px 24px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
                border-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #bdc3c7;
            }
            QPushButton:disabled {
                background-color: #ecf0f1;
                color: #95a5a6;
                border-color: #d1d8e0;
            }
        """
        )
        layout.addWidget(self.prev_btn)

        layout.addStretch()

        self.submit_btn = QPushButton("✓ " + self.i18n.t("ui.submit"))
        self.submit_btn.clicked.connect(self.on_submit)
        self.submit_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 12px 32px;
                min-width: 150px;
                border: none;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """
        )
        layout.addWidget(self.submit_btn)

        layout.addStretch()

        self.next_btn = QPushButton(self.i18n.t("ui.next") + " ➡️")
        self.next_btn.clicked.connect(self.on_next)
        self.next_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                min-width: 120px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """
        )
        layout.addWidget(self.next_btn)

        return widget

    def _bind_shortcuts(self) -> None:
        """绑定快捷键: Enter=提交, Ctrl+→ 下一步, Ctrl+← 上一步"""
        try:
            from PySide6.QtGui import QKeySequence, QShortcut

            submit_shortcut = QShortcut(QKeySequence("Return"), self)
            submit_shortcut.activated.connect(self.on_submit)

            submit_shortcut2 = QShortcut(QKeySequence("Enter"), self)
            submit_shortcut2.activated.connect(self.on_submit)

            next_shortcut = QShortcut(QKeySequence("Ctrl+Right"), self)
            next_shortcut.activated.connect(self.on_next)

            prev_shortcut = QShortcut(QKeySequence("Ctrl+Left"), self)
            prev_shortcut.activated.connect(self.on_previous)
        except Exception:
            pass

    def update_step_display(self) -> None:
        """更新步骤显示

        清理旧的控件，创建新的步骤界面，并更新进度显示。

        Note:
            使用deleteLater()确保Qt对象正确清理，避免内存泄漏。
        """
        try:
            # 显示加载指示器
            self.feedback_label.setText("⏳ 加载中...")
            self.feedback_label.setStyleSheet("color: #666; padding: 10px;")

            # 清除旧内容
            while self.step_layout.count():
                item = self.step_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                    widget.deleteLater()

            self.input_widgets.clear()

            # 获取当前步骤
            step = self.controller.get_current_step()
            if not step:
                self.feedback_label.setText("⚠️ 无法加载步骤")
                self.feedback_label.setStyleSheet(
                    "color: #856404; padding: 10px; background-color: #fff3cd;"
                )
                logger.warning("update_step_display: 无法获取当前步骤")
                return

            # 步骤标题（使用步骤ID作为标题）
            step_title = f"步骤 {self.controller.record.current_step_index + 1}: {step.id.replace('_', ' ').title()}"
            title = QLabel(f"<h2>{step_title}</h2>")
            title.setStyleSheet("color: #2c3e50; margin: 10px 0;")
            self.step_layout.addWidget(title)

            # 显示图片（如果有）
            if step.media and "image" in step.media:
                image_widget = self.create_image_widget(step.media["image"])
                if image_widget:
                    self.step_layout.addWidget(image_widget)

            # 步骤说明（Step模型使用text字段，不是instruction）
            instruction_box = QGroupBox("📋 实验说明")
            instruction_box.setStyleSheet(
                """
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #3498db;
                    border-radius: 8px;
                    margin-top: 15px;
                    padding: 15px;
                    background-color: #f8f9fa;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 8px;
                    color: #3498db;
                }
            """
            )
            instruction_layout = QVBoxLayout()

            instruction = QTextEdit()
            instruction.setPlainText(step.text)
            instruction.setReadOnly(True)
            instruction.setMaximumHeight(120)
            instruction.setStyleSheet(
                """
                QTextEdit {
                    border: none;
                    background-color: transparent;
                    font-size: 12pt;
                    line-height: 1.6;
                }
            """
            )
            instruction_layout.addWidget(instruction)
            instruction_box.setLayout(instruction_layout)
            self.step_layout.addWidget(instruction_box)

            # 根据检查点类型创建输入控件
            if step.check:
                checkpoint_box = self.create_checkpoint_widget(step.check)
                self.step_layout.addWidget(checkpoint_box)

            # 更新进度
            progress = self.controller.get_progress()
            self.progress_bar.setMaximum(progress["total_steps"])
            self.progress_bar.setValue(progress["current_step"])

            # 更新可观测状态条
            self.update_status_bar()

            # 更新按钮状态
            self.prev_btn.setEnabled(self.controller.record.current_step_index > 0)

            # 清除加载指示器
            self.feedback_label.setText("")
            self.feedback_label.setStyleSheet("")

            logger.debug(
                f"步骤显示已更新: {step.id} ({self.controller.record.current_step_index + 1}/{progress['total_steps']})"
            )

        except Exception as e:
            logger.error(f"更新步骤显示失败: {e}", exc_info=True)
            self.feedback_label.setText(f"❌ 加载步骤失败: {e!s}")
            self.feedback_label.setStyleSheet(
                "color: #721c24; padding: 10px; background-color: #f8d7da; border-radius: 5px;"
            )
            # 禁用提交按钮以防止在错误状态下提交
            self.submit_btn.setEnabled(False)

    def create_image_widget(self, image_path: str) -> QWidget | None:
        """创建图片显示控件

        Args:
            image_path: 图片路径（相对路径或绝对路径）

        Returns:
            包含图片的QWidget，如果加载失败返回None
        """
        try:
            from pathlib import Path

            # 如果是相对路径，相对于项目根目录
            if not Path(image_path).is_absolute():
                # 尝试在 data/images 目录查找
                image_path = str(Path("data/images") / image_path)

            # 加载图片
            pixmap = QPixmap(str(image_path))

            if pixmap.isNull():
                logger.warning(f"无法加载图片: {image_path}")
                return None

            # 创建容器
            widget = QWidget()
            widget.setStyleSheet(
                """
                QWidget {
                    background-color: white;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 10px;
                }
            """
            )
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(15, 15, 15, 15)

            # 创建图片标签
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 缩放图片以适应显示（保持宽高比，最大宽度600px）
            max_width = 600
            if pixmap.width() > max_width:
                pixmap = pixmap.scaledToWidth(
                    max_width, Qt.TransformationMode.SmoothTransformation
                )

            image_label.setPixmap(pixmap)
            image_label.setStyleSheet("border: none; padding: 5px;")
            layout.addWidget(image_label)

            # 添加图片说明文字（可选）
            caption = QLabel("🔬 实验示意图")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setStyleSheet(
                """
                color: #7f8c8d;
                font-size: 10pt;
                font-style: italic;
                border: none;
                padding: 5px;
            """
            )
            layout.addWidget(caption)

            logger.debug(f"成功加载图片: {image_path}")
            return widget

        except Exception as e:
            logger.error(f"创建图片控件失败: {e}", exc_info=True)
            return None

    def create_checkpoint_widget(self, checkpoint: CheckPoint) -> QGroupBox:
        """根据检查点类型创建输入控件"""
        group = QGroupBox(self.i18n.t("ui.checkpoint"))
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #f0f8f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #27ae60;
            }
        """
        )
        layout = QVBoxLayout()

        # 检查点消息
        if checkpoint.fail_hint:
            msg_label = QLabel(checkpoint.fail_hint)
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(msg_label)

        # 转换枚举类型为字符串进行比较
        check_type_str = (
            checkpoint.type.value
            if hasattr(checkpoint.type, "value")
            else str(checkpoint.type)
        )

        if check_type_str == "confirm":
            # 确认框
            checkbox = QCheckBox(self.i18n.t("ui.confirmed"))
            self.input_widgets["confirmed"] = checkbox
            layout.addWidget(checkbox)

        elif check_type_str == "input":
            # 输入框（使用input字段中的配置）
            input_layout = QHBoxLayout()

            # 显示标签
            if checkpoint.input and checkpoint.input.label:
                label = QLabel(checkpoint.input.label + ":")
                input_layout.addWidget(label)

            line_edit = QLineEdit()
            line_edit.setPlaceholderText(self.i18n.t("ui.enter_value"))
            self.input_widgets["value"] = line_edit
            input_layout.addWidget(line_edit)

            # 单位标签
            if checkpoint.input and checkpoint.input.unit:
                unit_label = QLabel(checkpoint.input.unit)
                input_layout.addWidget(unit_label)

            layout.addLayout(input_layout)

        elif check_type_str == "select":
            # 选择框（使用input字段中的options）
            if checkpoint.input and checkpoint.input.options:
                # 显示标签
                if checkpoint.input.label:
                    label = QLabel(checkpoint.input.label + ":")
                    layout.addWidget(label)

                # 单选下拉框
                combo = QComboBox()
                combo.addItem(self.i18n.t("ui.please_select"))
                for opt in checkpoint.input.options:
                    # 兼容字典/对象两种结构
                    opt_label = (
                        opt.get("label")
                        if isinstance(opt, dict)
                        else getattr(opt, "label", str(opt))
                    )
                    opt_value = (
                        opt.get("value")
                        if isinstance(opt, dict)
                        else getattr(opt, "value", opt)
                    )
                    combo.addItem(str(opt_label), opt_value)
                self.input_widgets["selected"] = combo
                layout.addWidget(combo)

        elif check_type_str == "sequence":
            # 顺序选择(拖拽排序界面)
            label = QLabel(self.i18n.t("ui.sequence_hint"))
            layout.addWidget(label)

            # 创建拖拽排序列表
            sequence_list = QListWidget()
            sequence_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            sequence_list.setDefaultDropAction(Qt.DropAction.MoveAction)
            sequence_list.setMinimumHeight(150)

            # 添加选项（如果有的话）
            if checkpoint.input and checkpoint.input.options:
                for option in checkpoint.input.options:
                    # 兼容字典/对象两种结构
                    option_label = (
                        option.get("label")
                        if isinstance(option, dict)
                        else getattr(option, "label", str(option))
                    )
                    option_value = (
                        option.get("value")
                        if isinstance(option, dict)
                        else getattr(option, "value", option)
                    )
                    item = QListWidgetItem(str(option_label))
                    item.setData(Qt.ItemDataRole.UserRole, option_value)
                    sequence_list.addItem(item)

            # 设置样式
            sequence_list.setStyleSheet(
                """
                QListWidget {
                    border: 2px solid #27ae60;
                    border-radius: 6px;
                    background-color: #f0f8f4;
                    padding: 5px;
                }
                QListWidget::item {
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin: 2px;
                    background-color: white;
                }
                QListWidget::item:selected {
                    background-color: #3498db;
                    color: white;
                }
                QListWidget::item:hover {
                    background-color: #ecf0f1;
                }
            """
            )

            layout.addWidget(sequence_list)
            self.input_widgets["sequence"] = sequence_list

            # 添加说明标签
            hint_label = QLabel("💡 拖拽项目来重新排序")
            hint_label.setStyleSheet(
                "color: #666; font-style: italic; font-size: 10pt;"
            )
            layout.addWidget(hint_label)

        group.setLayout(layout)
        return group

    def on_multi_select_changed(self, option: str, state: int) -> None:
        """多选框状态改变"""
        if "selected" not in self.input_widgets:
            selected_list: list[str] = []
            self.input_widgets["selected"] = selected_list

        selected = self.input_widgets["selected"]
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            if isinstance(selected, list) and option not in selected:
                selected.append(option)
        elif isinstance(selected, list) and option in selected:
            selected.remove(option)

    def get_user_input(self) -> dict[str, Any]:
        """获取用户输入（带验证）

        遍历所有输入控件，提取用户输入的数据。
        只收集非空的有效输入，并记录验证日志。

        Returns:
            dict: 键值对形式的用户输入数据，空值会被过滤

        Raises:
            Exception: 当获取输入数据失败时
        """
        user_data: dict[str, Any] = {}

        try:
            for key, widget in self.input_widgets.items():
                if isinstance(widget, QCheckBox):
                    user_data[key] = widget.isChecked()
                elif isinstance(widget, QLineEdit):
                    text = widget.text().strip()
                    if text:  # 只添加非空值
                        user_data[key] = text
                    else:
                        logger.debug(f"输入项 {key} 为空，已跳过")
                elif isinstance(widget, QComboBox):
                    text = widget.currentText()
                    if text and text != self.i18n.t("ui.please_select"):
                        user_data[key] = text
                    else:
                        logger.debug(f"下拉框 {key} 未选择有效值，已跳过")
                elif isinstance(widget, list):
                    user_data[key] = widget
                elif isinstance(widget, QListWidget):
                    # 处理拖拽排序列表
                    sequence_data = []
                    for i in range(widget.count()):
                        item = widget.item(i)
                        if item:
                            sequence_data.append(item.data(Qt.ItemDataRole.UserRole))
                    user_data[key] = sequence_data
                else:
                    logger.warning(f"未知的控件类型: {type(widget)} for key {key}")

            logger.debug(f"成功获取用户输入，包含 {len(user_data)} 个字段")

        except Exception as e:
            logger.error(f"获取用户输入失败: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "输入错误",
                f"获取输入数据时发生错误:\n{e!s}\n\n请检查您的输入并重试。",
            )
            raise  # 重新抛出异常以便调用者处理

        return user_data

    def on_submit(self) -> None:
        """提交按钮点击（带增强反馈）

        处理用户提交的步骤数据，进行验证并显示增强反馈。

        流程:
            1. 禁用提交按钮防止重复提交
            2. 显示验证中状态
            3. 获取并验证用户输入
            4. 提交到控制器验证
            5. 显示增强的验证结果反馈
            6. 提供帮助建议（失败时）
            7. 自动前进或重试
        """
        # 防止重复提交
        self.submit_btn.setEnabled(False)

        # 🆕 显示验证中状态
        self.show_validating_status()

        try:
            user_data = self.get_user_input()

            # 使用全局输入验证与清洗
            sanitized_payload: dict[str, Any] = {}
            for key, value in user_data.items():
                expected_type = "general"
                if key == "value":
                    current_step = self.controller.get_current_step()
                    if (
                        current_step
                        and getattr(current_step, "check", None)
                        and getattr(current_step.check, "input", None)
                    ):
                        # 根据InputSpec.input_type选择类型
                        input_spec = current_step.check.input
                        expected_type = (
                            getattr(input_spec, "input_type", "general") or "general"
                        )

                ok, msg, sanitized = validate_and_sanitize_input(
                    value, input_type=expected_type
                )
                if not ok:
                    raise ValueError(msg)
                sanitized_payload[key] = sanitized

            # 验证输入完整性
            if not sanitized_payload:
                # 🆕 使用增强反馈
                from .widgets.enhanced_feedback_widget import FeedbackType

                self.enhanced_feedback.show_feedback(
                    self.i18n.t("ui.incomplete_input"),
                    FeedbackType.WARNING,
                    help_text="请确保所有必填字段都已填写",
                )
                return

            # 提交到控制器验证
            passed, message, score = self.controller.submit_step(sanitized_payload)

            # 🆕 显示增强反馈
            if passed:
                self.show_success_feedback(message, score)
                logger.info(f"步骤验证通过: {message}, 得分: {score}")

                # 自动前进到下一步（如果不是最后一步）
                if (
                    self.controller.record.current_step_index
                    < len(self.template.steps) - 1
                ):
                    # 延迟前进，让用户看到反馈
                    from PySide6.QtCore import QTimer

                    QTimer.singleShot(1500, self.advance_to_next_step)
            else:
                self.show_error_feedback(message)
                logger.warning(f"步骤验证失败: {message}, 得分: {score}")

        except ValueError as e:
            # 🆕 输入验证错误 - 使用增强反馈
            logger.warning(f"输入验证错误: {e}")
            from .widgets.enhanced_feedback_widget import FeedbackType

            self.enhanced_feedback.show_feedback(
                self.i18n.t("ui.input_error", error=str(e)),
                FeedbackType.WARNING,
                help_text="请检查输入格式是否正确",
                help_callback=self.show_input_help,
            )

        except Exception as e:
            # 🆕 严重错误 - 显示详细错误对话框
            logger.error(f"提交步骤失败: {e}", exc_info=True)
            self.show_critical_error(e)

        finally:
            # 重新启用提交按钮
            self.submit_btn.setEnabled(True)

    def show_validating_status(self) -> None:
        """显示验证中状态"""
        from .widgets.enhanced_feedback_widget import FeedbackType

        self.enhanced_feedback.show_feedback(
            "正在验证您的答案...", FeedbackType.VALIDATING, auto_hide=False
        )

    def show_success_feedback(self, message: str, score: float | None = None) -> None:
        """显示成功反馈"""
        from .widgets.enhanced_feedback_widget import FeedbackType

        # 构建消息
        full_message = f"✓ {message}"
        if score is not None:
            full_message += f" (得分: {score:.1f})"

        self.enhanced_feedback.show_feedback(
            full_message, FeedbackType.SUCCESS, auto_hide=True, duration=2000
        )

        # 播放成功音效（如果启用）
        # self._play_success_sound()

    def show_error_feedback(self, message: str) -> None:
        """显示错误反馈"""
        from .widgets.enhanced_feedback_widget import FeedbackType

        # 获取帮助建议
        help_text = self.get_error_help_text(message)

        self.enhanced_feedback.show_feedback(
            f"✗ {message}",
            FeedbackType.ERROR,
            auto_hide=False,  # 不自动隐藏，让用户阅读
            help_text=help_text,
            help_callback=self.show_contextual_help,
        )

        # 播放失败音效（如果启用）
        # self._play_error_sound()

    def show_critical_error(self, error: Exception) -> None:
        """显示严重错误"""
        from .widgets.enhanced_feedback_widget import FeedbackType

        self.enhanced_feedback.show_feedback(
            f"系统错误: {str(error)}",
            FeedbackType.ERROR,
            auto_hide=False,
            help_text="请尝试重新提交，如果问题持续请联系支持",
            help_callback=lambda: QMessageBox.critical(
                self, "错误详情", f"发生错误:\n{error}\n\n请查看日志文件获取更多信息"
            ),
        )

    def get_error_help_text(self, error_message: str) -> str:
        """根据错误消息获取帮助文本"""
        error_lower = error_message.lower()

        if "范围" in error_lower or "range" in error_lower:
            return "请检查输入值是否在有效范围内"
        elif "格式" in error_lower or "format" in error_lower:
            return "请确保输入格式符合要求"
        elif "类型" in error_lower or "type" in error_lower:
            return "请输入正确类型的值（如数字、文本等）"
        elif "未选择" in error_lower:
            return "请选择一个有效的选项"
        else:
            return "请查看步骤说明，确保操作正确"

    def show_contextual_help(self) -> None:
        """显示上下文相关帮助"""
        current_step = self.controller.get_current_step()
        if not current_step:
            return

        # 构建帮助内容
        help_content = f"<h3>{current_step.text}</h3>"

        # 添加提示
        if current_step.hints:
            help_content += "<h4>💡 提示:</h4><ul>"
            for hint in current_step.hints:
                help_content += f"<li>{hint.content}</li>"
            help_content += "</ul>"

        # 添加检查点说明
        if current_step.check:
            help_content += "<h4>📝 检查点:</h4>"
            help_content += f"<p>类型: {current_step.check.type}</p>"
            if current_step.check.input:
                help_content += f"<p>预期输入: {current_step.check.input.label}</p>"
                if current_step.check.input.unit:
                    help_content += f"<p>单位: {current_step.check.input.unit}</p>"

        # 显示帮助对话框
        from PySide6.QtWidgets import QDialog, QTextBrowser

        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("步骤帮助")
        help_dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(help_dialog)

        browser = QTextBrowser()
        browser.setHtml(help_content)
        layout.addWidget(browser)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)

        help_dialog.exec()

    def show_input_help(self) -> None:
        """显示输入帮助"""
        current_step = self.controller.get_current_step()
        if not current_step or not current_step.check or not current_step.check.input:
            return

        input_spec = current_step.check.input

        help_text = "<h3>输入要求</h3>"
        help_text += f"<p><b>字段:</b> {input_spec.label}</p>"
        help_text += f"<p><b>类型:</b> {input_spec.input_type or '文本'}</p>"

        if input_spec.unit:
            help_text += f"<p><b>单位:</b> {input_spec.unit}</p>"

        if input_spec.placeholder:
            help_text += f"<p><b>示例:</b> {input_spec.placeholder}</p>"

        # 显示帮助
        QMessageBox.information(self, "输入帮助", help_text)

    def advance_to_next_step(self) -> None:
        """前进到下一步"""
        self.controller.next_step()
        self.update_step_display()

    def on_previous(self) -> None:
        """上一步按钮点击"""
        self.controller.previous_step()
        self.update_step_display()

    def on_next(self) -> None:
        """下一步按钮点击"""
        # 检查是否是最后一步
        if self.controller.record.current_step_index >= len(self.template.steps) - 1:
            # 完成实验
            self.finish_experiment()
        else:
            self.controller.next_step()
            self.update_step_display()

    def finish_experiment(self) -> None:
        """完成实验"""
        self.controller.complete_experiment()
        record = self.controller.get_record()

        # 发射实验完成信号
        self.experiment_finished.emit(record)

        # 计算并发射经验值信号（用于游戏化系统）
        exp = int(record.score.total)
        if record.total_mistakes == 0:
            exp = int(exp * 1.2)  # 零失误奖励
        self.exp_gained.emit(exp)

        # 禁用所有按钮
        self.submit_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)

    def restart_experiment(self) -> None:
        """重新开始实验"""
        reply = QMessageBox.question(
            self,
            self.i18n.t("ui.confirm"),
            self.i18n.t("ui.restart_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.controller.start_experiment()
            self.submit_btn.setEnabled(True)
            self.next_btn.setEnabled(True)

            # 重置交互式场景
            if self.interactive_scene:
                self.interactive_scene.reset_scene()

            self.update_step_display()

    def _should_show_interactive(self) -> bool:
        """判断是否应该显示交互式场景"""
        # 检查模板是否配置了交互式场景
        if hasattr(self.template, "metadata") and isinstance(
            self.template.metadata, dict
        ):
            return bool(self.template.metadata.get("interactive_mode", False))
        return False

    def _create_interactive_scene(self) -> InteractiveExperimentView | None:
        """创建交互式实验场景"""
        try:
            # 从模板获取场景配置
            scene_config = None
            if hasattr(self.template, "metadata") and isinstance(
                self.template.metadata, dict
            ):
                scene_config = self.template.metadata.get("scene_config")

            # 如果没有配置，使用默认场景
            if not scene_config:
                from .interactive_scene import PRESET_SCENES

                # 根据实验类型选择预设场景
                experiment_type = getattr(self.template, "category", "default")
                if experiment_type in PRESET_SCENES:
                    scene_config = PRESET_SCENES[experiment_type]
                else:
                    scene_config = PRESET_SCENES.get("titration", {})

            # 创建场景
            self.interactive_scene = ExperimentSceneBuilder.build_from_config(
                scene_config
            )

            # 连接信号
            self.interactive_scene.item_dropped.connect(self._on_item_dropped)
            self.interactive_scene.item_clicked.connect(self._on_item_clicked)
            self.interactive_scene.action_completed.connect(self._on_action_completed)

            # 创建视图
            view = InteractiveExperimentView(self.interactive_scene)
            view.setMinimumSize(500, 400)

            logger.info("交互式实验场景创建成功")
            return view

        except Exception as e:
            logger.error(f"创建交互式场景失败: {e}", exc_info=True)
            return None

    def _create_equipment_library(self) -> CompactEquipmentLibrary | None:
        """创建器材库"""
        try:
            # 从模板获取试剂信息
            equipment_data = {}

            if hasattr(self.template, "reagents") and self.template.reagents:
                for reagent in self.template.reagents:
                    equipment_data[reagent.id] = {
                        "name": reagent.name,
                        "type": "reagent",
                        "category": "试剂",
                        "amount": reagent.amount,
                        "hazard_level": reagent.hazard_level,
                    }

            # 如果没有试剂，使用默认器材
            if not equipment_data:
                logger.info("模板中没有试剂信息，跳过器材库创建")
                return None

            library = CompactEquipmentLibrary(equipment_data)
            library.setMaximumHeight(200)
            library.equipment_selected.connect(self._on_equipment_selected)

            logger.info(f"器材库创建成功，包含 {len(equipment_data)} 个物品")
            return library

        except Exception as e:
            logger.error(f"创建器材库失败: {e}", exc_info=True)
            return None

    def _on_item_dropped(self, item_id: str, zone_id: str) -> None:
        """物品被放置到区域"""
        logger.info(f"物品 {item_id} 被放置到 {zone_id}")

        # 记录到控制器上下文
        self.controller.record.context[f"dropped_{item_id}"] = zone_id

        # 显示反馈
        self.feedback_label.setText(f"✓ 已将 {item_id} 放置到 {zone_id}")
        self.feedback_label.setStyleSheet(
            "background-color: #d4edda; color: #155724; padding: 8px; border-radius: 5px;"
        )

    def _on_item_clicked(self, item_id: str) -> None:
        """物品被点击"""
        logger.info(f"物品 {item_id} 被点击")

        # 记录到控制器上下文
        self.controller.record.context[f"clicked_{item_id}"] = True

        # 显示反馈
        self.feedback_label.setText(f"✓ 已选择 {item_id}")
        self.feedback_label.setStyleSheet(
            "background-color: #cce5ff; color: #004085; padding: 8px; border-radius: 5px;"
        )

    def _on_action_completed(
        self, action_name: str, result_data: dict[str, Any]
    ) -> None:
        """动作完成"""
        logger.info(f"动作完成: {action_name}, 结果: {result_data}")

        # 记录到控制器上下文
        self.controller.record.context[f"action_{action_name}"] = result_data

    def _on_equipment_selected(
        self, equipment_id: str, equipment_info: dict[str, Any]
    ) -> None:
        """器材被选择"""
        logger.info(f"选择器材: {equipment_id}")

        # 如果有交互式场景，可以将器材添加到场景中
        if self.interactive_scene:
            try:
                # 获取器材的基本信息
                equipment_name = equipment_info.get("name", equipment_id)
                equipment_type = equipment_info.get("type", "equipment")
                image_path = equipment_info.get("image")

                # 在场景中心位置添加器材
                scene_rect = self.interactive_scene.sceneRect()
                center_x = scene_rect.center().x()
                center_y = scene_rect.center().y()

                # 添加可拖拽的器材到场景
                self.interactive_scene.add_draggable_item(
                    item_id=equipment_id,
                    item_type=equipment_type,
                    position=(center_x, center_y),
                    image_path=image_path,
                    size=(80, 80),  # 默认大小
                )

                logger.info(f"器材 {equipment_name} 已添加到交互式场景")
            except Exception as e:
                logger.warning(f"添加器材到场景失败: {e}")

        # 显示反馈
        self.feedback_label.setText(
            f"✓ 已选择器材: {equipment_info.get('name', equipment_id)}"
        )
        self.feedback_label.setStyleSheet(
            "background-color: #fff3cd; color: #856404; padding: 8px; border-radius: 5px;"
        )
