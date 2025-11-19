"""
前端懒加载与资源加载相关测试
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QWidget

from src.frontend.lazy_loader import (
    AsyncLoader,
    CodeSplitter,
    ImageLazyLoader,
    LazyLoader,
    ViewportLoader,
    lazy_load,
)


def test_lazy_loader_reuses_cached_widgets(qtbot):
    loader = LazyLoader()
    loader.register("heavy", lambda: QWidget())

    widget1 = loader.load("heavy")
    widget2 = loader.load("heavy")

    assert widget1 is widget2

    widget3 = loader.load("heavy", force=True)
    assert widget3 is not widget1


def test_lazy_loader_reports_errors(qtbot):
    loader = LazyLoader(max_retries=1)

    def broken_widget():
        raise RuntimeError("broken component")

    loader.register("broken", broken_widget)

    with qtbot.waitSignal(loader.load_failed, timeout=1000) as blocker:
        result = loader.load("broken")
        assert result is None

    assert "broken component" in blocker.args[1]
    assert loader._retry_count["broken"] == 1


def test_lazy_loader_unload_clears_cache(qtbot):
    loader = LazyLoader()
    loader.register("panel", lambda: QWidget())

    widget = loader.load("panel")
    assert widget is not None

    loader.unload("panel")
    assert "panel" not in loader._cache


def test_image_lazy_loader_caches_and_scales(tmp_path):
    image = QImage(32, 32, QImage.Format_RGB32)
    image.fill(Qt.white)

    img_path = tmp_path / "sample.png"
    assert image.save(str(img_path))

    loader = ImageLazyLoader()

    pixmap1 = loader.load(str(img_path))
    pixmap2 = loader.load(str(img_path))

    assert pixmap1 is not None
    assert pixmap2 is not None
    assert pixmap1.cacheKey() == pixmap2.cacheKey()

    scaled = loader.load(str(img_path), (10, 20))
    assert scaled.width() == 10
    assert 0 < scaled.height() <= 20


def test_async_loader_emits_loaded_signal(qtbot):
    loader = AsyncLoader(lambda x: x * 2, 21)

    with qtbot.waitSignal(loader.loaded, timeout=1000) as blocker:
        loader.start()
    loader.wait()

    assert blocker.args[0] == 42


def test_async_loader_emits_error_signal(qtbot):
    def raising_loader():
        raise ValueError("boom")

    loader = AsyncLoader(raising_loader)
    with qtbot.waitSignal(loader.error, timeout=1000) as blocker:
        loader.start()
    loader.wait()

    assert "boom" in blocker.args[0]


def test_lazy_load_decorator_delays_execution(qtbot):
    calls = []

    @lazy_load(threshold=10)
    def expensive_task(value):
        calls.append(value)

    expensive_task("chemistry")
    qtbot.waitUntil(lambda: calls, timeout=1000)

    assert calls == ["chemistry"]


def test_code_splitter_caches_modules():
    math_module = CodeSplitter.import_module("math")
    assert math_module is not None

    cached = CodeSplitter.import_module("math")
    assert cached is math_module

    missing = CodeSplitter.import_module("nonexistent.module")
    assert missing is None

    CodeSplitter.clear_cache()
    assert not CodeSplitter._modules


def test_viewport_loader_only_loads_visible_widgets():
    viewport = QWidget()
    viewport.setGeometry(0, 0, 100, 100)

    visible_top = QWidget(parent=viewport)
    visible_top.setGeometry(0, 0, 50, 40)

    hidden = QWidget(parent=viewport)
    hidden.setGeometry(0, 150, 50, 40)

    partially_visible = QWidget(parent=viewport)
    partially_visible.setGeometry(0, 80, 50, 40)

    loader = ViewportLoader()
    loaded = []

    def load_item(item):
        loaded.append(item)

    loader.load_visible([visible_top, hidden, partially_visible], viewport, load_item)

    assert visible_top in loaded
    assert partially_visible in loaded
    assert hidden not in loaded

    loader.load_visible([visible_top], viewport, load_item)
    assert loaded.count(visible_top) == 1
