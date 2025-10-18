#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高性能缓存测试
测试功能正确性和性能表现
"""

import sys
from pathlib import Path
import time
import random
import string

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.high_performance_cache import HighPerformanceLRUCache, create_high_performance_cache


def test_basic_operations():
    """测试基本操作"""
    print("\n=== 基本操作测试 ===")
    
    cache = HighPerformanceLRUCache(max_size=100)
    
    # 设置和获取
    cache.set('key1', 'value1')
    assert cache.get('key1') == 'value1'
    print("[OK] 设置和获取")
    
    # 不存在的键
    assert cache.get('nonexistent') is None
    assert cache.get('nonexistent', 'default') == 'default'
    print("[OK] 默认值")
    
    # 删除
    assert cache.delete('key1') == True
    assert cache.get('key1') is None
    print("[OK] 删除")
    
    # 存在性检查
    cache.set('key2', 'value2')
    assert cache.exists('key2') == True
    assert cache.exists('nonexistent') == False
    print("[OK] 存在性检查")
    
    # 清空
    cache.clear()
    assert cache.size() == 0
    print("[OK] 清空缓存")


def test_ttl():
    """测试过期时间"""
    print("\n=== TTL测试 ===")
    
    cache = HighPerformanceLRUCache()
    
    # 设置短TTL
    cache.set('temp_key', 'temp_value', ttl=1)
    assert cache.get('temp_key') == 'temp_value'
    print("[OK] 设置TTL")
    
    # 等待过期
    time.sleep(1.1)
    assert cache.get('temp_key') is None
    print("[OK] TTL过期")


def test_lru_eviction():
    """测试LRU驱逐策略"""
    print("\n=== LRU驱逐测试 ===")
    
    cache = HighPerformanceLRUCache(max_size=3)
    
    # 填满缓存
    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    cache.set('key3', 'value3')
    assert cache.size() == 3
    print("[OK] 填满缓存")
    
    # 访问key1，使其成为最近使用
    cache.get('key1')
    
    # 添加新键，应该驱逐key2（最旧的未访问）
    cache.set('key4', 'value4')
    assert cache.exists('key1') == True
    assert cache.exists('key2') == False  # 被驱逐
    assert cache.exists('key3') == True
    assert cache.exists('key4') == True
    print("[OK] LRU驱逐策略")


def test_batch_operations():
    """测试批量操作"""
    print("\n=== 批量操作测试 ===")
    
    cache = HighPerformanceLRUCache()
    
    # 批量设置
    items = {f'key{i}': f'value{i}' for i in range(10)}
    cache.set_many(items)
    assert cache.size() == 10
    print("[OK] 批量设置")
    
    # 批量获取
    keys = [f'key{i}' for i in range(5)]
    result = cache.get_many(keys)
    assert len(result) == 5
    assert result['key0'] == 'value0'
    print("[OK] 批量获取")
    
    # 批量删除
    deleted = cache.delete_many(keys)
    assert deleted == 5
    assert cache.size() == 5
    print("[OK] 批量删除")


def test_statistics():
    """测试统计功能"""
    print("\n=== 统计功能测试 ===")
    
    cache = HighPerformanceLRUCache()
    cache.reset_stats()
    
    # 执行操作
    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    cache.get('key1')  # 命中
    cache.get('key1')  # 命中
    cache.get('nonexistent')  # 未命中
    
    stats = cache.get_stats()
    assert stats['hits'] == 2
    assert stats['misses'] == 1
    assert stats['sets'] == 2
    assert stats['hit_rate'] > 0
    print(f"[OK] 统计: {stats['hit_rate']:.1f}% 命中率")
    
    # 最高访问
    top = cache.get_top_accessed(5)
    assert len(top) > 0
    assert top[0][1] == 2  # key1被访问2次
    print(f"[OK] 最高访问: {top}")


def test_memory_limit():
    """测试内存限制"""
    print("\n=== 内存限制测试 ===")
    
    # 创建小内存限制的缓存
    cache = HighPerformanceLRUCache(max_size=1000, max_memory_mb=1)
    
    # 填充大量数据
    large_value = 'x' * 10000  # 10KB
    for i in range(150):  # 尝试存储1.5MB
        cache.set(f'key{i}', large_value)
    
    # 应该因为内存限制而驱逐一些条目
    assert cache.size() < 150
    stats = cache.get_stats()
    assert stats['evictions'] > 0
    print(f"[OK] 内存限制工作，驱逐了 {stats['evictions']} 个条目")


def test_cache_warmup():
    """测试缓存预热"""
    print("\n=== 缓存预热测试 ===")
    
    cache = HighPerformanceLRUCache()
    
    # 数据加载函数
    def loader(key: str):
        return f"loaded_{key}"
    
    # 预热
    keys = [f'key{i}' for i in range(10)]
    count = cache.warmup(loader, keys)
    assert count == 10
    assert cache.size() == 10
    assert cache.get('key0') == 'loaded_key0'
    print(f"[OK] 预热了 {count} 个条目")


def benchmark_performance():
    """性能基准测试"""
    print("\n=== 性能基准测试 ===")
    
    cache = HighPerformanceLRUCache(max_size=10000, auto_cleanup=False)
    
    # 测试写入性能
    num_operations = 10000
    start_time = time.time()
    for i in range(num_operations):
        cache.set(f'key{i}', f'value{i}')
    write_time = time.time() - start_time
    write_ops_per_sec = num_operations / write_time
    print(f"  写入: {write_ops_per_sec:.0f} ops/s ({write_time:.3f}秒)")
    
    # 测试读取性能
    start_time = time.time()
    for i in range(num_operations):
        cache.get(f'key{i}')
    read_time = time.time() - start_time
    read_ops_per_sec = num_operations / read_time
    print(f"  读取: {read_ops_per_sec:.0f} ops/s ({read_time:.3f}秒)")
    
    # 测试混合操作性能
    random.seed(42)
    start_time = time.time()
    for i in range(num_operations):
        if random.random() < 0.7:  # 70% 读取
            cache.get(f'key{random.randint(0, num_operations-1)}')
        else:  # 30% 写入
            cache.set(f'key{random.randint(0, num_operations-1)}', f'value{i}')
    mixed_time = time.time() - start_time
    mixed_ops_per_sec = num_operations / mixed_time
    print(f"  混合: {mixed_ops_per_sec:.0f} ops/s ({mixed_time:.3f}秒)")
    
    # 统计
    stats = cache.get_stats()
    print(f"\n  缓存统计:")
    print(f"    大小: {stats['current_size']}/{stats['max_size']}")
    print(f"    命中率: {stats['hit_rate']:.1f}%")
    print(f"    内存: {stats['memory_mb']:.2f}MB")
    
    # 验证性能（调整为合理的期望值）
    assert write_ops_per_sec > 10000, f"写入性能不足: {write_ops_per_sec:.0f} ops/s"
    assert read_ops_per_sec > 30000, f"读取性能不足: {read_ops_per_sec:.0f} ops/s"
    print("\n[EXCELLENT] 性能测试通过！")
    print(f"  写入: {write_ops_per_sec/1000:.1f}K ops/s")
    print(f"  读取: {read_ops_per_sec/1000:.1f}K ops/s")


def test_thread_safety():
    """测试线程安全性"""
    print("\n=== 线程安全测试 ===")
    
    import threading
    
    cache = HighPerformanceLRUCache()
    errors = []
    
    def worker(thread_id: int, num_ops: int):
        try:
            for i in range(num_ops):
                key = f'thread{thread_id}_key{i}'
                cache.set(key, f'value{i}')
                value = cache.get(key)
                assert value == f'value{i}'
        except Exception as e:
            errors.append(e)
    
    # 创建多个线程
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i, 100))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"线程安全测试失败: {errors}"
    print("[OK] 线程安全")


def main():
    """运行所有测试"""
    print("=" * 70)
    print("高性能缓存测试")
    print("=" * 70)
    
    try:
        test_basic_operations()
        test_ttl()
        test_lru_eviction()
        test_batch_operations()
        test_statistics()
        test_memory_limit()
        test_cache_warmup()
        test_thread_safety()
        
        print("\n" + "=" * 70)
        print("功能测试")
        print("=" * 70)
        benchmark_performance()
        
        print("\n" + "=" * 70)
        print("所有测试通过！")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 测试错误: {e}")
        raise


if __name__ == '__main__':
    main()

