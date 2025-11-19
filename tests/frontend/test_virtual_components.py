"""
前端虚拟化组件测试
"""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.frontend.virtual_list import InfiniteScrollList, VirtualListWidget, VirtualTreeWidget


def _simple_renderer():
    """创建简单的项渲染器"""

    def _renderer(data, index):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"{index}: {data}"))
        return widget

    return _renderer


def _build_sample_tree():
    return [
        {
            "id": "root",
            "text": "Root",
            "children": [
                {"id": "child_1", "text": "Child 1"},
                {"id": "child_2", "text": "Child 2", "children": [{"id": "grand", "text": "Grand Child"}]},
            ],
        }
    ]


class TestVirtualListWidget:
    """VirtualListWidget 行为测试"""

    def test_renders_only_visible_items(self, qtbot):
        widget = VirtualListWidget()
        qtbot.addWidget(widget)
        widget.set_item_height(20)
        widget.set_item_renderer(_simple_renderer())
        widget.resize(300, 120)
        widget.show()
        qtbot.waitExposed(widget)

        data = [f"Item {i}" for i in range(200)]
        widget.set_data(data)
        qtbot.wait(20)

        assert 0 < len(widget._visible_items) < len(data)
        assert len(widget._visible_items) <= 20

    def test_scroll_updates_visible_items(self, qtbot):
        widget = VirtualListWidget()
        qtbot.addWidget(widget)
        widget.set_item_height(20)
        widget.set_item_renderer(_simple_renderer())
        widget.resize(300, 150)
        widget.show()
        qtbot.waitExposed(widget)

        data = list(range(300))
        widget.set_data(data)
        qtbot.wait(20)

        scrollbar = widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        qtbot.wait(100)

        max_visible_index = max(widget._visible_items.keys())
        assert max_visible_index >= len(data) - 10

    def test_item_clicked_signal(self, qtbot):
        widget = VirtualListWidget()
        qtbot.addWidget(widget)
        widget.set_item_renderer(_simple_renderer())
        widget.set_item_height(25)
        widget.resize(200, 100)
        widget.show()
        qtbot.waitExposed(widget)

        payload = [("chemical", i) for i in range(50)]
        widget.set_data(payload)
        qtbot.wait(20)

        with qtbot.waitSignal(widget.item_clicked, timeout=1000) as blocker:
            widget._visible_items[0].mousePressEvent(None)

        assert blocker.args == [0, payload[0]]


class TestVirtualTreeWidget:
    """虚拟树形组件测试"""

    def test_tree_flatten_and_expand(self, qtbot):
        widget = VirtualTreeWidget()
        qtbot.addWidget(widget)
        widget.set_tree_data(_build_sample_tree())

        assert len(widget._flat_data) == 1
        assert widget._flat_data[0]["text"] == "Root"

        root = widget._flat_data[0]
        widget._on_item_clicked(0, root)

        assert any(node["id"] == "child_1" for node in widget._flat_data)
        assert any(node["id"] == "child_2" for node in widget._flat_data)

    def test_leaf_click_does_not_expand(self, qtbot):
        widget = VirtualTreeWidget()
        qtbot.addWidget(widget)
        widget.set_tree_data(_build_sample_tree())
        widget._on_item_clicked(0, widget._flat_data[0])

        before = list(widget._flat_data)
        leaf = next(node for node in widget._flat_data if node["id"] == "child_1")
        widget._on_item_clicked(1, leaf)

        assert widget._flat_data == before


class TestInfiniteScrollList:
    """测试无限滚动列表"""

    def _setup_list(self, qtbot):
        widget = InfiniteScrollList()
        qtbot.addWidget(widget)
        widget.set_item_height(15)
        widget.set_item_renderer(_simple_renderer())
        widget.resize(250, 160)
        widget.show()
        qtbot.waitExposed(widget)
        widget.set_data(list(range(500)))
        qtbot.wait(20)
        return widget

    def test_emits_load_more_near_bottom(self, qtbot):
        widget = self._setup_list(qtbot)
        widget._threshold = 40

        with qtbot.waitSignal(widget.load_more, timeout=1000):
            widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

    def test_has_more_flag_blocks_signal(self, qtbot):
        widget = self._setup_list(qtbot)
        widget.set_has_more(False)
        triggered = []
        widget.load_more.connect(lambda: triggered.append(True))

        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())
        qtbot.wait(100)

        assert not triggered

    def test_append_data_resets_loading_state(self, qtbot):
        widget = self._setup_list(qtbot)
        widget._loading = True
        original_length = len(widget._data)

        widget.append_data([999, 1000])

        assert len(widget._data) == original_length + 2
        assert widget._loading is False
