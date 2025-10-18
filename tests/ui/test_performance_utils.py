"""
性能工具测试
"""

from __future__ import annotations

import time

import pytest

from src.ui.performance_utils import (
    BatchUpdater,
    Debouncer,
    MemoryMonitor,
    PerformanceTimer,
    RequestAnimationFrame,
    Throttler,
    debounce,
    get_memory_monitor,
    get_raf,
    throttle,
)


@pytest.fixture
def debouncer(qtbot):
    """创建防抖器实例"""
    return Debouncer(delay_ms=100)


@pytest.fixture
def throttler(qtbot):
    """创建节流器实例"""
    return Throttler(interval_ms=100)


def test_debouncer_creation(debouncer):
    """测试防抖器创建"""
    assert debouncer is not None
    assert debouncer.delay_ms == 100


def test_debouncer_delays_execution(debouncer, qtbot):
    """测试防抖器延迟执行"""
    call_count = []

    def callback():
        call_count.append(1)

    # 快速调用多次
    for _ in range(5):
        debouncer.call(callback)

    # 立即检查 - 不应执行
    assert len(call_count) == 0

    # 等待延迟后检查 - 应只执行一次
    qtbot.wait(200)
    assert len(call_count) == 1


def test_debouncer_cancel(debouncer, qtbot):
    """测试防抖器取消"""
    call_count = []

    def callback():
        call_count.append(1)

    debouncer.call(callback)
    debouncer.cancel()

    qtbot.wait(200)
    assert len(call_count) == 0


def test_throttler_creation(throttler):
    """测试节流器创建"""
    assert throttler is not None
    assert throttler.interval_ms == 100


def test_throttler_limits_execution(throttler, qtbot):
    """测试节流器限制执行频率"""
    call_count = []

    def callback():
        call_count.append(1)

    # 快速调用多次
    for _ in range(10):
        throttler.call(callback)
        time.sleep(0.01)  # 10ms间隔

    # 等待处理
    qtbot.wait(300)

    # 应该执行少于10次
    assert len(call_count) < 10


def test_debounce_decorator():
    """测试防抖装饰器"""
    call_count = []

    @debounce(delay_ms=50)
    def decorated_func():
        call_count.append(1)

    # 快速调用
    for _ in range(5):
        decorated_func()

    # 应该被延迟
    assert len(call_count) == 0


def test_throttle_decorator():
    """测试节流装饰器"""
    call_count = []

    @throttle(interval_ms=50)
    def decorated_func():
        call_count.append(1)

    # 快速调用
    for _ in range(5):
        decorated_func()
        time.sleep(0.01)

    # 应该被限流
    assert len(call_count) < 5


def test_memory_monitor_creation(qtbot):
    """测试内存监控器创建"""
    monitor = MemoryMonitor(threshold_mb=100, check_interval_ms=1000)
    assert monitor is not None
    assert monitor.threshold_mb == 100

    monitor.stop()


def test_memory_monitor_singleton():
    """测试内存监控器单例"""
    monitor1 = get_memory_monitor()
    monitor2 = get_memory_monitor()

    assert monitor1 is monitor2


def test_performance_timer():
    """测试性能计时器"""
    with PerformanceTimer("测试操作") as timer:
        time.sleep(0.05)

    assert timer.elapsed_ms >= 50
    assert timer.elapsed_ms < 100


def test_performance_timer_threshold(caplog):
    """测试性能计时器阈值"""
    with PerformanceTimer("快速操作", log_threshold_ms=1000):
        time.sleep(0.01)

    # 不应该有警告
    assert "WARNING" not in caplog.text


def test_request_animation_frame_creation(qtbot):
    """测试动画帧调度器创建"""
    raf = RequestAnimationFrame(fps=60)
    assert raf is not None
    assert raf.fps == 60
    assert raf.interval_ms == 16  # 1000 / 60


def test_request_animation_frame_callback(qtbot):
    """测试动画帧回调"""
    raf = RequestAnimationFrame(fps=60)
    call_count = []

    def callback(timestamp):
        call_count.append(timestamp)
        if len(call_count) >= 3:
            raf.cancel(callback)

    raf.request(callback)

    qtbot.wait(100)
    assert len(call_count) >= 3


def test_request_animation_frame_singleton():
    """测试动画帧调度器单例"""
    raf1 = get_raf()
    raf2 = get_raf()

    assert raf1 is raf2


def test_batch_updater_creation(qtbot):
    """测试批量更新器创建"""
    updater = BatchUpdater(delay_ms=50)
    assert updater is not None
    assert updater.delay_ms == 50


def test_batch_updater_batches_updates(qtbot):
    """测试批量更新器合并更新"""
    updater = BatchUpdater(delay_ms=50)
    signal_count = []

    def on_update():
        signal_count.append(1)

    updater.updated.connect(on_update)

    # 调度多个更新
    for i in range(10):
        updater.schedule_update(f"item_{i}")

    # 立即检查 - 不应触发
    assert len(signal_count) == 0

    # 等待延迟
    qtbot.wait(100)

    # 应该只触发一次
    assert len(signal_count) == 1


def test_batch_updater_get_pending():
    """测试获取待更新项"""
    updater = BatchUpdater(delay_ms=50)

    updater.schedule_update("item1")
    updater.schedule_update("item2")
    updater.schedule_update("item3")

    pending = updater.get_pending()
    assert len(pending) == 3
    assert "item1" in pending
    assert "item2" in pending
    assert "item3" in pending


def test_batch_updater_clear():
    """测试清空待更新项"""
    updater = BatchUpdater(delay_ms=50)

    updater.schedule_update("item1")
    updater.schedule_update("item2")

    updater.clear()

    pending = updater.get_pending()
    assert len(pending) == 0


def test_debouncer_signal(debouncer, qtbot):
    """测试防抖器信号"""
    with qtbot.waitSignal(debouncer.triggered, timeout=200):
        debouncer.call(lambda: None)


def test_throttler_signal(throttler, qtbot):
    """测试节流器信号"""
    with qtbot.waitSignal(throttler.triggered, timeout=200):
        throttler.call(lambda: None)
