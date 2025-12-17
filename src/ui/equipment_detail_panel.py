"""
实验器材详情面板
显示器材的详细信息、属性和操作按钮
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class EquipmentDetailPanel(QFrame):
    """器材详情面板"""

    use_clicked = Signal(str)  # 器材ID
    info_requested = Signal(str)  # 器材ID
    close_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_equipment_id: str | None = None

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 2px solid #d0d0d0;
                border-radius: 12px;
            }
        """
        )

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 标题栏
        title_layout = QHBoxLayout()

        title_label = QLabel("器材详情")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #2c3e50;
            }
        """
        )
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18pt;
                color: #95a5a6;
            }
            QPushButton:hover {
                color: #e74c3c;
                background-color: #f8f9fa;
                border-radius: 15px;
            }
        """
        )
        close_btn.clicked.connect(self.close_clicked.emit)
        title_layout.addWidget(close_btn)

        main_layout.addLayout(title_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        main_layout.addWidget(line)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
        """
        )

        # 内容容器
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(15)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 图片区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(200)
        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 10px;
            }
        """
        )
        self.content_layout.addWidget(self.image_label)

        # 名称
        self.name_label = QLabel()
        self.name_label.setStyleSheet(
            """
            QLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
            }
        """
        )
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.name_label)

        # 类型标签
        self.type_label = QLabel()
        self.type_label.setStyleSheet(
            """
            QLabel {
                background-color: #e8f4f8;
                color: #0078d4;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }
        """
        )
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.type_label)

        # 描述
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(
            """
            QLabel {
                color: #7f8c8d;
                font-size: 10pt;
                line-height: 1.5;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """
        )
        self.content_layout.addWidget(self.description_label)

        # 属性组
        self.properties_group = QGroupBox("属性")
        self.properties_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """
        )
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setSpacing(8)
        self.properties_group.setLayout(self.properties_layout)
        self.content_layout.addWidget(self.properties_group)

        # 规格组
        self.specs_group = QGroupBox("规格")
        self.specs_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """
        )
        self.specs_layout = QVBoxLayout()
        self.specs_layout.setSpacing(8)
        self.specs_group.setLayout(self.specs_layout)
        self.content_layout.addWidget(self.specs_group)

        # 危险性警告（如果有）
        self.hazard_widget = QFrame()
        self.hazard_widget.setStyleSheet(
            """
            QFrame {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 12px;
            }
        """
        )
        hazard_layout = QHBoxLayout(self.hazard_widget)
        hazard_layout.setContentsMargins(10, 10, 10, 10)

        hazard_icon = QLabel("⚠️")
        hazard_icon.setStyleSheet("font-size: 24pt;")
        hazard_layout.addWidget(hazard_icon)

        self.hazard_label = QLabel()
        self.hazard_label.setWordWrap(True)
        self.hazard_label.setStyleSheet(
            """
            QLabel {
                color: #856404;
                font-weight: bold;
                font-size: 10pt;
            }
        """
        )
        hazard_layout.addWidget(self.hazard_label, 1)

        self.hazard_widget.hide()
        self.content_layout.addWidget(self.hazard_widget)

        self.content_layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.info_btn = QPushButton("更多信息")
        self.info_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """
        )
        self.info_btn.clicked.connect(self._on_info_clicked)
        button_layout.addWidget(self.info_btn)

        self.use_btn = QPushButton("使用器材")
        self.use_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
        )
        self.use_btn.clicked.connect(self._on_use_clicked)
        button_layout.addWidget(self.use_btn)

        main_layout.addLayout(button_layout)

    def show_equipment(self, equipment_id: str, equipment_data: dict[str, Any]) -> None:
        """显示器材信息"""
        self.current_equipment_id = equipment_id

        # 名称
        name = equipment_data.get("name", equipment_id)
        self.name_label.setText(name)

        # 类型
        equipment_type = equipment_data.get("type", "器材")
        category = equipment_data.get("category", "")
        type_text = f"{category} - {equipment_type}" if category else equipment_type
        self.type_label.setText(type_text)

        # 描述
        description = equipment_data.get("description", "暂无描述")
        self.description_label.setText(description)

        # 图片
        image_path = equipment_data.get("image")
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    180,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("📦\n暂无图片")
                self.image_label.setStyleSheet(
                    self.image_label.styleSheet() + "font-size: 48pt;"
                )
        else:
            self.image_label.setText("📦\n暂无图片")
            self.image_label.setStyleSheet(
                self.image_label.styleSheet() + "font-size: 48pt;"
            )

        # 清空旧属性
        self._clear_layout(self.properties_layout)
        self._clear_layout(self.specs_layout)

        # 显示属性
        properties = equipment_data.get("properties", {})
        if properties:
            for key, value in properties.items():
                self._add_property_row(self.properties_layout, key, str(value))
        else:
            no_props = QLabel("暂无属性信息")
            no_props.setStyleSheet("color: #95a5a6; font-style: italic;")
            self.properties_layout.addWidget(no_props)

        # 显示规格
        specs = equipment_data.get("specs", {})
        if specs:
            for key, value in specs.items():
                self._add_property_row(self.specs_layout, key, str(value))
        else:
            # 如果有容量、浓度等信息，显示为规格
            if (
                "capacity" in equipment_data
                or "amount" in equipment_data
                or "concentration" in equipment_data
            ):
                if "capacity" in equipment_data:
                    self._add_property_row(
                        self.specs_layout, "容量", equipment_data["capacity"]
                    )
                if "amount" in equipment_data:
                    self._add_property_row(
                        self.specs_layout, "数量", equipment_data["amount"]
                    )
                if "concentration" in equipment_data:
                    self._add_property_row(
                        self.specs_layout, "浓度", equipment_data["concentration"]
                    )
            else:
                no_specs = QLabel("暂无规格信息")
                no_specs.setStyleSheet("color: #95a5a6; font-style: italic;")
                self.specs_layout.addWidget(no_specs)

        # 危险性警告
        hazard_level = equipment_data.get("hazard_level", 0)
        if hazard_level > 0:
            hazard_texts = {
                1: "低危险性 - 请按操作规程使用",
                2: "中等危险性 - 需要注意安全防护",
                3: "高危险性 - 必须严格遵守安全规范",
            }
            self.hazard_label.setText(hazard_texts.get(hazard_level, "请注意安全"))
            self.hazard_widget.show()
        else:
            self.hazard_widget.hide()

        logger.info(f"显示器材详情: {name} ({equipment_id})")

    def _add_property_row(self, layout: QVBoxLayout, key: str, value: str) -> None:
        """添加属性行"""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(5, 5, 5, 5)

        # 键
        key_label = QLabel(key + ":")
        key_label.setStyleSheet(
            """
            QLabel {
                color: #7f8c8d;
                font-weight: bold;
                font-size: 10pt;
            }
        """
        )
        row_layout.addWidget(key_label)

        row_layout.addStretch()

        # 值
        value_label = QLabel(str(value))
        value_label.setStyleSheet(
            """
            QLabel {
                color: #2c3e50;
                font-size: 10pt;
            }
        """
        )
        row_layout.addWidget(value_label)

        layout.addWidget(row)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """清空布局"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_use_clicked(self) -> None:
        """使用按钮点击"""
        if self.current_equipment_id:
            self.use_clicked.emit(self.current_equipment_id)
            logger.info(f"使用器材: {self.current_equipment_id}")

    def _on_info_clicked(self) -> None:
        """更多信息按钮点击"""
        if self.current_equipment_id:
            self.info_requested.emit(self.current_equipment_id)
            logger.info(f"请求器材详细信息: {self.current_equipment_id}")


class CompactEquipmentCard(QFrame):
    """紧凑型器材卡片"""

    clicked = Signal(str, dict)  # 器材ID, 器材数据

    def __init__(
        self,
        equipment_id: str,
        equipment_data: dict[str, Any],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.equipment_id = equipment_id
        self.equipment_data = equipment_data

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 图标/图片
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(64, 64)

        image_path = self.equipment_data.get("image")
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("📦")
                icon_label.setStyleSheet("font-size: 32pt;")
        else:
            # 根据类型显示不同图标
            equipment_type = self.equipment_data.get("type", "")
            type_icons = {
                "beaker": "🧪",
                "flask": "⚗️",
                "burette": "🔬",
                "reagent": "🧪",
                "indicator": "💧",
                "equipment": "🔧",
                "instrument": "📏",
                "heater": "🔥",
                "tool": "🔨",
            }
            icon = type_icons.get(equipment_type, "📦")
            icon_label.setText(icon)
            icon_label.setStyleSheet("font-size: 32pt;")

        layout.addWidget(icon_label)

        # 名称
        name = self.equipment_data.get("name", self.equipment_id)
        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                font-size: 10pt;
                color: #2c3e50;
            }
        """
        )
        layout.addWidget(name_label)

        # 类型
        category = self.equipment_data.get("category", "")
        if category:
            category_label = QLabel(category)
            category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            category_label.setStyleSheet(
                """
                QLabel {
                    background-color: #e8f4f8;
                    color: #0078d4;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 8pt;
                    font-weight: bold;
                }
            """
            )
            layout.addWidget(category_label)

    def mousePressEvent(self, event) -> None:
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.equipment_id, self.equipment_data)
        super().mousePressEvent(event)
