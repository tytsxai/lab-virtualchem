"""
虚拟列表组件
只渲染可见区域的列表项，大幅提升长列表性能
"""

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class VirtualListWidget(QScrollArea):
    """虚拟列表组件 - 只渲染可见项"""

    item_clicked = Signal(int, object)  # 索引, 数据

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 数据
        self._data: list[Any] = []
        self._item_height: int = 50
        self._visible_items: dict = {}  # 索引: Widget

        # 渲染器
        self._item_renderer: Callable | None = None

        # 性能优化 - 防抖
        self._render_timer = QTimer()
        self._render_timer.timeout.connect(self._update_visible_items)
        self._render_timer.setInterval(50)  # 50ms防抖
        self._render_timer.setSingleShot(True)  # 单次触发

        # 渲染节流
        self._last_render_time = 0
        self._min_render_interval = 16  # 最小16ms间隔（约60fps）

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 内容容器
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)

        self.setWidget(self._container)

        # 滚动事件
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def set_data(self, data: list[Any]) -> None:
        """
        设置数据

        Args:
            data: 数据列表
        """
        self._data = data
        self._clear_visible_items()

        # 设置容器高度
        total_height = len(data) * self._item_height
        self._container.setMinimumHeight(total_height)

        # 初始渲染
        self._update_visible_items()

        logger.info(f"虚拟列表设置数据: {len(data)} 项")

    def set_item_height(self, height: int) -> None:
        """设置项高度"""
        self._item_height = height

    def set_item_renderer(self, renderer: Callable[[Any, int], QWidget]) -> None:
        """
        设置项渲染器

        Args:
            renderer: 渲染函数 (data, index) -> QWidget
        """
        self._item_renderer = renderer

    def _get_visible_range(self) -> tuple[int, int]:
        """
        获取可见范围

        Returns:
            (start_index, end_index)
        """
        viewport = self.viewport()
        viewport_height = viewport.height()
        scroll_y = self.verticalScrollBar().value()

        # 计算可见索引范围(带缓冲)
        buffer = 3  # 上下各缓冲3项
        start_index = max(0, (scroll_y // self._item_height) - buffer)
        end_index = min(len(self._data), ((scroll_y + viewport_height) // self._item_height) + buffer + 1)

        return start_index, end_index

    def _update_visible_items(self) -> None:
        """更新可见项（带节流）"""
        if not self._item_renderer or not self._data:
            return

        # 节流检查
        import time

        current_time = time.time() * 1000  # 转为毫秒
        if current_time - self._last_render_time < self._min_render_interval:
            return

        self._last_render_time = current_time

        try:
            start, end = self._get_visible_range()

            # 移除不可见的项
            to_remove = []
            for idx in self._visible_items:
                if idx < start or idx >= end:
                    to_remove.append(idx)

            for idx in to_remove:
                widget = self._visible_items.pop(idx)
                widget.deleteLater()

            # 添加新可见项
            for idx in range(start, end):
                if idx not in self._visible_items:
                    self._render_item(idx)

        except Exception as e:
            logger.error(f"更新可见项失败: {e}", exc_info=True)

    def _render_item(self, index: int) -> None:
        """
        渲染单个项

        Args:
            index: 项索引
        """
        if index >= len(self._data):
            return

        data = self._data[index]

        # 创建组件
        widget = self._item_renderer(data, index)
        widget.setFixedHeight(self._item_height)

        # 设置位置
        y = index * self._item_height
        widget.move(0, y)
        widget.setParent(self._container)
        widget.show()

        # 绑定点击事件
        widget.mousePressEvent = lambda _e, i=index, d=data: self.item_clicked.emit(i, d)

        self._visible_items[index] = widget

    def _clear_visible_items(self) -> None:
        """清空可见项"""
        for widget in self._visible_items.values():
            widget.deleteLater()
        self._visible_items.clear()

    def _on_scroll(self, _value: int) -> None:
        """滚动事件处理（防抖）"""
        # 重启防抖定时器
        self._render_timer.stop()
        self._render_timer.start()

    def refresh(self) -> None:
        """刷新列表"""
        self._clear_visible_items()
        self._update_visible_items()


class VirtualTreeWidget(QWidget):
    """虚拟树形列表 - 支持展开/折叠的树形结构"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._tree_data: list[dict] = []  # 树形数据
        self._flat_data: list[dict] = []  # 扁平化后的数据
        self._expanded: set = set()  # 展开的节点

        self._list = VirtualListWidget(self)

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        # 设置渲染器
        self._list.set_item_renderer(self._render_tree_item)
        self._list.item_clicked.connect(self._on_item_clicked)

    def set_tree_data(self, data: list[dict]) -> None:
        """
        设置树形数据

        Args:
            data: 树形数据，每项包含 {id, text, children: []}
        """
        self._tree_data = data
        self._flatten_tree()
        self._list.set_data(self._flat_data)

    def _flatten_tree(self, nodes: list[dict] | None = None, level: int = 0) -> None:
        """
        扁平化树形数据

        Args:
            nodes: 节点列表
            level: 层级
        """
        if nodes is None:
            nodes = self._tree_data
            self._flat_data = []

        for node in nodes:
            # 添加节点
            self._flat_data.append(
                {
                    "id": node["id"],
                    "text": node.get("text", ""),
                    "level": level,
                    "has_children": bool(node.get("children")),
                    "expanded": node["id"] in self._expanded,
                }
            )

            # 如果展开，添加子节点
            if node["id"] in self._expanded and node.get("children"):
                self._flatten_tree(node["children"], level + 1)

    def _render_tree_item(self, data: dict, _index: int) -> QWidget:
        """
        渲染树形项

        Args:
            data: 项数据
            index: 索引

        Returns:
            Widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(data["level"] * 20, 5, 5, 5)

        # 展开/折叠图标
        prefix = ""
        if data["has_children"]:
            prefix = "▼ " if data["expanded"] else "▶ "

        label = QLabel(f"{prefix}{data['text']}")
        layout.addWidget(label)

        return widget

    def _on_item_clicked(self, _index: int, data: dict) -> None:
        """项点击事件"""
        if not data["has_children"]:
            return

        node_id = data["id"]

        # 切换展开状态
        if node_id in self._expanded:
            self._expanded.remove(node_id)
        else:
            self._expanded.add(node_id)

        # 重新扁平化并刷新
        self._flatten_tree()
        self._list.set_data(self._flat_data)


class InfiniteScrollList(VirtualListWidget):
    """无限滚动列表 - 自动加载更多"""

    load_more = Signal()  # 触发加载更多

    def __init__(self, parent=None):
        super().__init__(parent)

        self._loading = False
        self._has_more = True
        self._threshold = 100  # 距离底部多少像素触发加载

        self.verticalScrollBar().valueChanged.connect(self._check_load_more)

    def _check_load_more(self, value: int) -> None:
        """检查是否需要加载更多"""
        if self._loading or not self._has_more:
            return

        scrollbar = self.verticalScrollBar()
        if scrollbar.maximum() - value < self._threshold:
            self._loading = True
            self.load_more.emit()

    def append_data(self, data: list[Any]) -> None:
        """
        追加数据

        Args:
            data: 新数据
        """
        self._data.extend(data)
        total_height = len(self._data) * self._item_height
        self._container.setMinimumHeight(total_height)
        self._loading = False

    def set_has_more(self, has_more: bool) -> None:
        """设置是否还有更多数据"""
        self._has_more = has_more


if __name__ == "__main__":
    # 演示使用
    import sys

    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("虚拟列表演示")
    window.resize(400, 600)

    # 创建虚拟列表
    vlist = VirtualListWidget()

    # 设置渲染器
    def render_item(data, index):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"Item {index}: {data}")
        layout.addWidget(label)
        return widget

    vlist.set_item_renderer(render_item)

    # 设置数据(10000项)
    large_data = [f"数据项 {i}" for i in range(10000)]
    vlist.set_data(large_data)

    window.setCentralWidget(vlist)
    window.show()

    sys.exit(app.exec())
