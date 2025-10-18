#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化的事件总线测试
对比原始版本和Trie树优化版本的性能
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.event_bus import EventBus as OriginalEventBus, Event as OriginalEvent
from src.core.optimized_event_bus import OptimizedEventBus, Event, EventPriority


def test_basic_functionality():
    """测试基本功能"""
    print("\n=== 基本功能测试 ===")
    
    bus = OptimizedEventBus()
    
    # 测试订阅和发布
    results = []
    def handler(event: Event):
        results.append(event.name)
    
    bus.subscribe("user.login", handler)
    bus.publish(Event(name="user.login", data={'user_id': 1}))
    
    assert len(results) == 1
    assert results[0] == "user.login"
    print("[OK] 基本订阅和发布")
    
    # 测试通配符
    results.clear()
    bus.subscribe("user.*", handler)
    bus.publish(Event(name="user.logout", data={'user_id': 1}))
    
    assert len(results) == 1
    print("[OK] 通配符订阅")
    
    # 测试全局订阅
    results.clear()
    bus.subscribe("*", handler)
    bus.publish(Event(name="system.startup"))
    
    assert len(results) == 1
    print("[OK] 全局订阅")


def test_pattern_matching():
    """测试模式匹配"""
    print("\n=== 模式匹配测试 ===")
    
    bus = OptimizedEventBus()
    results = []
    
    def handler(event: Event):
        results.append(event.name)
    
    # 注册多个模式
    bus.subscribe("user.login", handler)
    bus.subscribe("user.*", handler)
    bus.subscribe("system.*", handler)
    bus.subscribe("*", handler)
    
    # 测试匹配
    results.clear()
    bus.publish(Event(name="user.login"))
    # 应该匹配: user.login, user.*, *
    assert len(results) == 3
    print("[OK] 多模式匹配")
    
    results.clear()
    bus.publish(Event(name="system.startup"))
    # 应该匹配: system.*, *
    assert len(results) == 2
    print("[OK] 系统事件匹配")


def test_priority():
    """测试优先级"""
    print("\n=== 优先级测试 ===")
    
    bus = OptimizedEventBus()
    results = []
    
    bus.subscribe("test.event", lambda e: results.append("normal"), EventPriority.NORMAL)
    bus.subscribe("test.event", lambda e: results.append("high"), EventPriority.HIGH)
    bus.subscribe("test.event", lambda e: results.append("low"), EventPriority.LOW)
    bus.subscribe("test.event", lambda e: results.append("critical"), EventPriority.CRITICAL)
    
    bus.publish(Event(name="test.event"))
    
    # 应该按优先级排序: CRITICAL > HIGH > NORMAL > LOW
    assert results == ["critical", "high", "normal", "low"]
    print("[OK] 优先级排序")


def test_filter():
    """测试过滤器"""
    print("\n=== 过滤器测试 ===")
    
    bus = OptimizedEventBus()
    results = []
    
    def handler(event: Event):
        results.append(event.data.get('value'))
    
    # 只处理value > 10的事件
    bus.subscribe(
        "data.update",
        handler,
        filter_func=lambda e: e.data.get('value', 0) > 10
    )
    
    bus.publish(Event(name="data.update", data={'value': 5}))
    assert len(results) == 0
    print("[OK] 过滤器拦截")
    
    bus.publish(Event(name="data.update", data={'value': 15}))
    assert len(results) == 1
    assert results[0] == 15
    print("[OK] 过滤器通过")


def test_unsubscribe():
    """测试取消订阅"""
    print("\n=== 取消订阅测试 ===")
    
    bus = OptimizedEventBus()
    results = []
    
    def handler(event: Event):
        results.append(1)
    
    sub_id = bus.subscribe("test.event", handler)
    bus.publish(Event(name="test.event"))
    assert len(results) == 1
    print("[OK] 订阅生效")
    
    bus.unsubscribe(sub_id)
    bus.publish(Event(name="test.event"))
    assert len(results) == 1  # 不应该增加
    print("[OK] 取消订阅")


def test_statistics():
    """测试统计功能"""
    print("\n=== 统计功能测试 ===")
    
    bus = OptimizedEventBus()
    bus.subscribe("*", lambda e: None)
    
    # 发布事件
    for i in range(10):
        bus.publish(Event(name=f"event.{i}"))
    
    stats = bus.get_stats()
    assert stats['events_published'] == 10
    assert stats['events_processed'] == 10
    assert stats['subscribers_count'] == 1
    assert stats['avg_match_time_ms'] >= 0
    print(f"[OK] 统计: {stats}")


def benchmark_event_matching():
    """性能基准测试 - 事件匹配"""
    print("\n=== 事件匹配性能测试 ===")
    
    # 测试配置
    num_patterns = 1000  # 订阅模式数量
    num_events = 10000   # 发布事件数量
    
    # 原始版本
    print("\n[TEST] 原始版本...")
    original_bus = OriginalEventBus()
    
    # 注册订阅
    for i in range(num_patterns):
        original_bus.subscribe(f"category{i % 10}.event{i}", lambda e: None)
    
    # 测试发布性能
    start_time = time.time()
    for i in range(num_events):
        event = OriginalEvent(name=f"category{i % 10}.event{i % num_patterns}")
        original_bus.publish(event)
    original_time = time.time() - start_time
    print(f"  耗时: {original_time:.3f}秒")
    
    # 优化版本
    print("\n[TEST] Trie树优化版本...")
    optimized_bus = OptimizedEventBus()
    
    # 注册订阅
    for i in range(num_patterns):
        optimized_bus.subscribe(f"category{i % 10}.event{i}", lambda e: None)
    
    # 测试发布性能
    start_time = time.time()
    for i in range(num_events):
        event = Event(name=f"category{i % 10}.event{i % num_patterns}")
        optimized_bus.publish(event)
    optimized_time = time.time() - start_time
    print(f"  耗时: {optimized_time:.3f}秒")
    
    # 计算性能提升
    if optimized_time > 0:
        speedup = original_time / optimized_time
        print(f"\n[RESULT] 性能提升: {speedup:.1f}x")
        print(f"         加速比例: {(speedup - 1) * 100:.1f}%")
        
        # 获取详细统计
        stats = optimized_bus.get_stats()
        print(f"\n  匹配统计:")
        print(f"    平均匹配时间: {stats['avg_match_time_ms']:.4f}ms")
        print(f"    事件处理: {stats['events_processed']}")
        
        return speedup
    else:
        print("\n[WARNING] 优化版本耗时过短，无法准确计算加速比")
        return 0


def benchmark_wildcard_matching():
    """性能基准测试 - 通配符匹配"""
    print("\n=== 通配符匹配性能测试 ===")
    
    num_patterns = 500
    num_events = 5000
    
    # 优化版本
    print("\n[TEST] Trie树优化版本...")
    optimized_bus = OptimizedEventBus()
    
    # 注册通配符订阅
    for i in range(num_patterns):
        optimized_bus.subscribe(f"category{i % 10}.*", lambda e: None)
    
    start_time = time.time()
    for i in range(num_events):
        event = Event(name=f"category{i % 10}.action{i % 50}")
        optimized_bus.publish(event)
    optimized_time = time.time() - start_time
    
    stats = optimized_bus.get_stats()
    print(f"  耗时: {optimized_time:.3f}秒")
    print(f"  处理事件: {stats['events_processed']}")
    print(f"  平均匹配: {stats['avg_match_time_ms']:.4f}ms")
    
    # 计算吞吐量
    throughput = num_events / optimized_time
    print(f"\n[RESULT] 吞吐量: {throughput:.0f} events/s")
    
    return 1.0  # 返回1作为标记（不对比原始版本）


def main():
    """运行所有测试"""
    print("=" * 70)
    print("优化的事件总线测试")
    print("=" * 70)
    
    try:
        # 功能测试
        test_basic_functionality()
        test_pattern_matching()
        test_priority()
        test_filter()
        test_unsubscribe()
        test_statistics()
        
        print("\n" + "=" * 70)
        print("性能基准测试")
        print("=" * 70)
        
        # 性能测试
        speedup1 = benchmark_event_matching()
        speedup2 = benchmark_wildcard_matching()
        
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)
        
        if speedup1 > 0:
            print(f"\n事件匹配性能提升: {speedup1:.1f}x")
            
            if speedup1 >= 10:
                print("\n[EXCELLENT] 优秀！性能提升显著达到预期目标！")
            elif speedup1 >= 5:
                print("\n[GOOD] 良好！性能明显提升！")
            else:
                print("\n[OK] 性能有提升")
        
        print("\n所有测试通过！")
        
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 测试错误: {e}")
        raise


if __name__ == '__main__':
    main()

