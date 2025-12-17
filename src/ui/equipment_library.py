"""
实验器材库组件
提供可视化的实验器材和试剂选择界面
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class EquipmentCard(QFrame):
    """器材卡片 - 显示单个器材的信息"""

    clicked = Signal(str, dict)  # 器材ID, 器材信息

    def __init__(
        self,
        equipment_id: str,
        equipment_info: dict[str, Any],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.equipment_id = equipment_id
        self.equipment_info = equipment_info

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 样式
        self.setStyleSheet(
            """
            EquipmentCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
            }
            EquipmentCard:hover {
                border-color: #3498db;
                background-color: #f0f8ff;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # 图片
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedSize(80, 80)

        # 加载图片或显示占位符
        if "image" in self.equipment_info:
            pixmap = QPixmap(self.equipment_info["image"])
            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        80,
                        80,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                image_label.setText("🧪")
                image_label.setStyleSheet("font-size: 40px;")
        else:
            # 使用emoji作为默认图标
            icon_map = {
                "beaker": "🧪",
                "flask": "⚗️",
                "test_tube": "🧫",
                "burette": "💧",
                "pipette": "💉",
                "reagent": "🧴",
                "indicator": "🎨",
            }
            icon = icon_map.get(self.equipment_info.get("type", ""), "🔬")
            image_label.setText(icon)
            image_label.setStyleSheet("font-size: 40px;")

        layout.addWidget(image_label)

        # 名称
        name_label = QLabel(self.equipment_info.get("name", self.equipment_id))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        name_label.setFont(font)
        layout.addWidget(name_label)

        # 规格（如果有）
        if "spec" in self.equipment_info:
            spec_label = QLabel(self.equipment_info["spec"])
            spec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spec_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(spec_label)

        # 数量（如果有）
        if "amount" in self.equipment_info:
            amount_label = QLabel(f"数量: {self.equipment_info['amount']}")
            amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_label.setStyleSheet("color: #27ae60; font-size: 9pt;")
            layout.addWidget(amount_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.equipment_id, self.equipment_info)
            logger.info(f"选择器材: {self.equipment_id}")
        super().mousePressEvent(event)


class EquipmentLibrary(QWidget):
    """实验器材库 - 展示所有可用的器材和试剂"""

    equipment_selected = Signal(str, dict)  # 器材ID, 器材信息

    def __init__(
        self,
        equipment_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.equipment_data = equipment_data or self._get_default_equipment()

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("🔬 实验器材库")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
            }
        """
        )
        layout.addWidget(title_label)

        # 分类标签页
        tabs = QTabWidget()
        tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #d5dbdb;
            }
        """
        )

        # 按分类组织器材
        categories = self._organize_by_category()

        for category_name, items in categories.items():
            tab = self._create_category_tab(category_name, items)
            tabs.addTab(tab, category_name)

        layout.addWidget(tabs)

        logger.info(f"器材库初始化完成: {len(categories)} 个分类")

    def _organize_by_category(self) -> dict[str, dict[str, dict[str, Any]]]:
        """按分类组织器材"""
        categories: dict[str, dict[str, dict[str, Any]]] = {}

        for item_id, item_info in self.equipment_data.items():
            category = item_info.get("category", "其他")
            if category not in categories:
                categories[category] = {}
            categories[category][item_id] = item_info

        return categories

    def _create_category_tab(
        self, _category_name: str, items: dict[str, dict[str, Any]]
    ) -> QWidget:
        """创建分类标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # 可滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """
        )

        # 网格布局显示器材卡片
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)
        grid.setContentsMargins(10, 10, 10, 10)

        row, col = 0, 0
        max_cols = 3

        for item_id, item_info in items.items():
            card = EquipmentCard(item_id, item_info)
            card.clicked.connect(self.on_equipment_clicked)
            card.setFixedSize(120, 160)
            grid.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # 填充空白
        grid.setRowStretch(row + 1, 1)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        return widget

    def on_equipment_clicked(self, equipment_id: str, equipment_info: dict[str, Any]):
        """器材被点击"""
        self.equipment_selected.emit(equipment_id, equipment_info)
        logger.info(f"器材被选择: {equipment_id}")

    def _get_default_equipment(self) -> dict[str, dict[str, Any]]:
        """获取默认器材配置"""
        return {
            # 玻璃器皿
            "beaker_50ml": {
                "name": "烧杯 50mL",
                "type": "beaker",
                "category": "玻璃器皿",
                "spec": "50mL",
                "amount": 5,
            },
            "beaker_100ml": {
                "name": "烧杯 100mL",
                "type": "beaker",
                "category": "玻璃器皿",
                "spec": "100mL",
                "amount": 5,
            },
            "beaker_250ml": {
                "name": "烧杯 250mL",
                "type": "beaker",
                "category": "玻璃器皿",
                "spec": "250mL",
                "amount": 3,
            },
            "flask_erlenmeyer_250ml": {
                "name": "锥形瓶",
                "type": "flask",
                "category": "玻璃器皿",
                "spec": "250mL",
                "amount": 5,
            },
            "test_tube": {
                "name": "试管",
                "type": "test_tube",
                "category": "玻璃器皿",
                "spec": "18×180mm",
                "amount": 10,
            },
            "burette": {
                "name": "滴定管",
                "type": "burette",
                "category": "玻璃器皿",
                "spec": "50mL 精度0.1mL",
                "amount": 2,
            },
            "pipette_25ml": {
                "name": "移液管",
                "type": "pipette",
                "category": "玻璃器皿",
                "spec": "25mL",
                "amount": 3,
            },
            "volumetric_flask_100ml": {
                "name": "容量瓶",
                "type": "flask",
                "category": "玻璃器皿",
                "spec": "100mL",
                "amount": 3,
            },
            # 试剂
            "hcl_01m": {
                "name": "盐酸溶液",
                "type": "reagent",
                "category": "试剂",
                "spec": "0.1 mol/L",
                "amount": "500mL",
                "hazard_level": "warning",
            },
            "naoh_01m": {
                "name": "氢氧化钠溶液",
                "type": "reagent",
                "category": "试剂",
                "spec": "0.1 mol/L",
                "amount": "500mL",
                "hazard_level": "warning",
            },
            "h2so4_01m": {
                "name": "硫酸溶液",
                "type": "reagent",
                "category": "试剂",
                "spec": "0.1 mol/L",
                "amount": "500mL",
                "hazard_level": "danger",
            },
            "agno3_01m": {
                "name": "硝酸银溶液",
                "type": "reagent",
                "category": "试剂",
                "spec": "0.1 mol/L",
                "amount": "100mL",
                "hazard_level": "warning",
            },
            "nacl_saturated": {
                "name": "氯化钠饱和溶液",
                "type": "reagent",
                "category": "试剂",
                "spec": "饱和溶液",
                "amount": "250mL",
                "hazard_level": "safe",
            },
            # 指示剂
            "phenolphthalein": {
                "name": "酚酞指示剂",
                "type": "indicator",
                "category": "指示剂",
                "spec": "1%醇溶液",
                "amount": "50mL",
                "hazard_level": "info",
            },
            "methyl_orange": {
                "name": "甲基橙指示剂",
                "type": "indicator",
                "category": "指示剂",
                "spec": "0.1%水溶液",
                "amount": "50mL",
                "hazard_level": "info",
            },
            "universal_indicator": {
                "name": "广泛pH试纸",
                "type": "indicator",
                "category": "指示剂",
                "spec": "pH 1-14",
                "amount": "1盒",
                "hazard_level": "safe",
            },
            # 其他设备
            "alcohol_lamp": {
                "name": "酒精灯",
                "type": "heating",
                "category": "加热设备",
                "spec": "150mL",
                "amount": 3,
            },
            "thermometer": {
                "name": "温度计",
                "type": "measurement",
                "category": "测量仪器",
                "spec": "0-100℃",
                "amount": 5,
            },
            "stirring_rod": {
                "name": "玻璃棒",
                "type": "tool",
                "category": "辅助工具",
                "spec": "长20cm",
                "amount": 10,
            },
            "funnel": {
                "name": "漏斗",
                "type": "tool",
                "category": "辅助工具",
                "spec": "直径10cm",
                "amount": 5,
            },
            "watch_glass": {
                "name": "表面皿",
                "type": "tool",
                "category": "辅助工具",
                "spec": "直径8cm",
                "amount": 5,
            },
        }


class CompactEquipmentLibrary(QWidget):
    """紧凑型器材库 - 用于侧边栏"""

    equipment_selected = Signal(str, dict)

    def __init__(
        self,
        equipment_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.equipment_data = equipment_data or {}

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题
        title = QLabel("器材库")
        title.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(5)

        # 添加器材按钮
        for item_id, item_info in self.equipment_data.items():
            btn = QPushButton(item_info.get("name", item_id))
            btn.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e8f4f8;
                    border-color: #3498db;
                }
                QPushButton:pressed {
                    background-color: #d4e9f7;
                }
            """
            )
            btn.clicked.connect(
                lambda _checked=False,
                eid=item_id,
                info=item_info: self.equipment_selected.emit(eid, info)
            )
            container_layout.addWidget(btn)

        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)
