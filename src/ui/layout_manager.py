"""
布局管理器
支持多种布局模式的动态切换
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class LayoutMode(Enum):
    """布局模式"""
    CLASSIC = "classic"  # 经典布局 - 左侧实验列表，右侧实验区
    MODERN = "modern"    # 现代布局 - 顶部工具栏，中间实验区，底部信息
    COMPACT = "compact"  # 紧凑布局 - 最小化边栏，最大化实验区
    WIDE = "wide"        # 宽屏布局 - 适合宽屏显示器


class LayoutConfig:
    """布局配置"""

    def __init__(self):
        self.mode = LayoutMode.CLASSIC
        self.sidebar_width = 250
        self.toolbar_visible = True
        self.statusbar_visible = True
        self.sidebar_visible = True
        self.info_panel_height = 200

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mode": self.mode.value,
            "sidebar_width": self.sidebar_width,
            "toolbar_visible": self.toolbar_visible,
            "statusbar_visible": self.statusbar_visible,
            "sidebar_visible": self.sidebar_visible,
            "info_panel_height": self.info_panel_height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LayoutConfig:
        """从字典创建"""
        config = cls()
        config.mode = LayoutMode(data.get("mode", "classic"))
        config.sidebar_width = data.get("sidebar_width", 250)
        config.toolbar_visible = data.get("toolbar_visible", True)
        config.statusbar_visible = data.get("statusbar_visible", True)
        config.sidebar_visible = data.get("sidebar_visible", True)
        config.info_panel_height = data.get("info_panel_height", 200)
        return config


class LayoutManager(QObject):
    """布局管理器"""

    layout_changed = Signal(str)  # 布局模式改变

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.config = LayoutConfig()
        self.settings = QSettings("VirtualChemLab", "Layout")

        # 保存原始几何信息
        self.original_geometries = {}

        # 加载保存的布局
        self.load_layout()

        logger.info(f"布局管理器初始化完成，当前模式: {self.config.mode.value}")

    def switch_layout(self, mode: LayoutMode | str) -> bool:
        """切换布局模式

        Args:
            mode: 布局模式

        Returns:
            bool: 是否成功切换
        """
        try:
            if isinstance(mode, str):
                mode = LayoutMode(mode)

            logger.info(f"切换布局: {self.config.mode.value} -> {mode.value}")

            # 保存当前布局的几何信息
            self._save_current_geometries()

            # 应用新布局
            self.config.mode = mode
            self._apply_layout(mode)

            # 发出信号
            self.layout_changed.emit(mode.value)

            # 保存布局配置
            self.save_layout()

            return True

        except Exception as e:
            logger.error(f"切换布局失败: {e}", exc_info=True)
            return False

    def _apply_layout(self, mode: LayoutMode):
        """应用布局"""
        if mode == LayoutMode.CLASSIC:
            self._apply_classic_layout()
        elif mode == LayoutMode.MODERN:
            self._apply_modern_layout()
        elif mode == LayoutMode.COMPACT:
            self._apply_compact_layout()
        elif mode == LayoutMode.WIDE:
            self._apply_wide_layout()

    def _apply_classic_layout(self):
        """应用经典布局"""
        logger.info("应用经典布局")

        # 显示所有组件
        self._set_component_visible("sidebar", True)
        self._set_component_visible("toolbar", True)
        self._set_component_visible("statusbar", True)

        # 设置分割器比例 - 左侧窄，右侧宽
        self._set_splitter_ratio("main_splitter", [1, 3])

        # 侧边栏宽度
        self.config.sidebar_width = 250

    def _apply_modern_layout(self):
        """应用现代布局"""
        logger.info("应用现代布局")

        # 显示工具栏和状态栏
        self._set_component_visible("sidebar", True)
        self._set_component_visible("toolbar", True)
        self._set_component_visible("statusbar", True)

        # 设置分割器比例 - 更宽的实验区
        self._set_splitter_ratio("main_splitter", [1, 4])

        # 较窄的侧边栏
        self.config.sidebar_width = 200

    def _apply_compact_layout(self):
        """应用紧凑布局"""
        logger.info("应用紧凑布局")

        # 隐藏侧边栏，最大化实验区
        self._set_component_visible("sidebar", False)
        self._set_component_visible("toolbar", True)
        self._set_component_visible("statusbar", False)

        # 实验区占满整个窗口
        self._set_splitter_ratio("main_splitter", [0, 1])

    def _apply_wide_layout(self):
        """应用宽屏布局"""
        logger.info("应用宽屏布局")

        # 显示所有组件
        self._set_component_visible("sidebar", True)
        self._set_component_visible("toolbar", True)
        self._set_component_visible("statusbar", True)

        # 三栏布局 - 左侧较窄，中间宽，右侧中等
        self._set_splitter_ratio("main_splitter", [1, 5])

        # 较宽的侧边栏
        self.config.sidebar_width = 300

    def _set_component_visible(self, component_name: str, visible: bool):
        """设置组件可见性"""
        try:
            # 查找组件
            if component_name == "sidebar":
                widget = getattr(self.main_window, "sidebar", None)
                if widget:
                    widget.setVisible(visible)
                    self.config.sidebar_visible = visible

            elif component_name == "toolbar":
                # 主窗口的工具栏
                toolbar = self.main_window.findChild(QWidget, "toolbar")
                if toolbar:
                    toolbar.setVisible(visible)
                self.config.toolbar_visible = visible

            elif component_name == "statusbar":
                status_bar = getattr(self.main_window, "status_bar", None)
                if status_bar:
                    status_bar.setVisible(visible)
                self.config.statusbar_visible = visible

        except Exception as e:
            logger.warning(f"设置组件可见性失败 {component_name}: {e}")

    def _set_splitter_ratio(self, splitter_name: str, ratios: list[int]):
        """设置分割器比例"""
        try:
            splitter = getattr(self.main_window, splitter_name, None)
            if splitter and isinstance(splitter, QSplitter):
                # 计算实际尺寸
                total = sum(ratios)
                if total > 0:
                    total_size = splitter.width() if splitter.orientation() == 1 else splitter.height()
                    sizes = [int(total_size * r / total) for r in ratios]
                    splitter.setSizes(sizes)
                    logger.debug(f"设置分割器 {splitter_name} 比例: {ratios} -> {sizes}")

        except Exception as e:
            logger.warning(f"设置分割器比例失败 {splitter_name}: {e}")

    def _save_current_geometries(self):
        """保存当前几何信息"""
        try:
            # 保存分割器状态
            splitter = getattr(self.main_window, "main_splitter", None)
            if splitter and isinstance(splitter, QSplitter):
                self.original_geometries["main_splitter"] = splitter.saveState()

            # 保存窗口大小和位置
            self.original_geometries["window_geometry"] = self.main_window.saveGeometry()

        except Exception as e:
            logger.warning(f"保存几何信息失败: {e}")

    def save_layout(self):
        """保存布局配置"""
        try:
            config_dict = self.config.to_dict()

            # 保存到QSettings
            for key, value in config_dict.items():
                self.settings.setValue(key, value)

            # 同时保存到JSON文件
            config_file = Path("data/layout_config.json")
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"布局配置已保存: {self.config.mode.value}")

        except Exception as e:
            logger.error(f"保存布局配置失败: {e}")

    def load_layout(self):
        """加载布局配置"""
        try:
            # 优先从JSON文件加载
            config_file = Path("data/layout_config.json")
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config_dict = json.load(f)
                self.config = LayoutConfig.from_dict(config_dict)
                logger.info(f"从文件加载布局配置: {self.config.mode.value}")
            else:
                # 从QSettings加载
                mode_str = self.settings.value("mode", "classic")
                self.config.mode = LayoutMode(mode_str)
                self.config.sidebar_width = int(self.settings.value("sidebar_width", 250))
                self.config.toolbar_visible = self.settings.value("toolbar_visible", True, type=bool)
                self.config.statusbar_visible = self.settings.value("statusbar_visible", True, type=bool)
                self.config.sidebar_visible = self.settings.value("sidebar_visible", True, type=bool)
                logger.info(f"从设置加载布局配置: {self.config.mode.value}")

            # 应用加载的布局
            self._apply_layout(self.config.mode)

        except Exception as e:
            logger.warning(f"加载布局配置失败，使用默认: {e}")
            self.config = LayoutConfig()

    def get_current_mode(self) -> LayoutMode:
        """获取当前布局模式"""
        return self.config.mode

    def toggle_sidebar(self):
        """切换侧边栏显示"""
        self.config.sidebar_visible = not self.config.sidebar_visible
        self._set_component_visible("sidebar", self.config.sidebar_visible)
        self.save_layout()
        logger.info(f"侧边栏可见性: {self.config.sidebar_visible}")

    def toggle_toolbar(self):
        """切换工具栏显示"""
        self.config.toolbar_visible = not self.config.toolbar_visible
        self._set_component_visible("toolbar", self.config.toolbar_visible)
        self.save_layout()
        logger.info(f"工具栏可见性: {self.config.toolbar_visible}")

    def toggle_statusbar(self):
        """切换状态栏显示"""
        self.config.statusbar_visible = not self.config.statusbar_visible
        self._set_component_visible("statusbar", self.config.statusbar_visible)
        self.save_layout()
        logger.info(f"状态栏可见性: {self.config.statusbar_visible}")

