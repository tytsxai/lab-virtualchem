#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能懒加载系统测试
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.smart_lazy_loader import SmartLazyLoader, lazy_import


def test_basic_loading():
    """测试基本加载"""
    print("\n=== 基本加载测试 ===")

    loader = SmartLazyLoader(enable_background_loading=False)

    # 注册模块
    loader.register('json')
    loader.register('time')
    loader.register('os')

    # 加载模块
    json_module = loader.load('json')
    assert json_module is not None
    assert hasattr(json_module, 'loads')
    print("[OK] 模块加载")

    # 检查缓存
    assert 'json' in loader.get_loaded_modules()
    print("[OK] 模块缓存")


def test_dependency_loading():
    """测试依赖加载"""
    print("\n=== 依赖加载测试 ===")

    loader = SmartLazyLoader(enable_background_loading=False)

    # 注册有依赖的模块
    loader.register('json', priority=1)
    loader.register('pathlib', priority=2, dependencies=['os'])

    # 加载带依赖的模块
    pathlib_module = loader.load('pathlib')
    assert pathlib_module is not None

    # 依赖应该也被加载了
    assert 'os' in loader.get_loaded_modules()
    print("[OK] 依赖自动加载")


def test_batch_loading():
    """测试批量加载"""
    print("\n=== 批量加载测试 ===")

    loader = SmartLazyLoader(enable_background_loading=False)

    # 注册模块
    for module_name in ['json', 'time', 'os', 'sys']:
        loader.register(module_name)

    # 批量加载
    modules = loader.load_many(['json', 'time', 'os'])
    assert len(modules) == 3
    assert all(m is not None for m in modules.values())
    print("[OK] 批量加载")


def test_background_loading():
    """测试后台预加载"""
    print("\n=== 后台预加载测试 ===")

    loader = SmartLazyLoader(enable_background_loading=True)

    # 注册模块
    loader.register('json', priority=10)
    loader.register('time', priority=9)
    loader.register('os', priority=8)
    loader.register('sys', priority=7)

    # 启动后台加载
    loader.start_background_loading()

    # 等待一段时间让后台加载完成
    time.sleep(0.5)

    # 检查是否有模块被后台加载
    loaded = loader.get_loaded_modules()
    assert len(loaded) > 0
    print(f"[OK] 后台加载了 {len(loaded)} 个模块")

    # 停止后台加载
    loader.stop_background_loading()
    print("[OK] 后台加载停止")


def test_statistics():
    """测试统计功能"""
    print("\n=== 统计功能测试 ===")

    loader = SmartLazyLoader(enable_background_loading=False)

    # 注册并加载模块
    loader.register('json')
    loader.register('time')
    loader.register('os')

    loader.load('json')
    loader.load('time')

    # 获取统计
    stats = loader.get_stats()
    assert stats['total_registered'] == 3
    assert stats['total_loaded'] == 2
    assert stats['avg_load_time_ms'] >= 0

    print(f"[OK] 统计: {stats}")

    # 检查未加载的模块
    unloaded = loader.get_unloaded_modules()
    assert 'os' in unloaded
    assert 'json' not in unloaded
    print("[OK] 未加载模块列表")


def benchmark_loading():
    """加载性能测试"""
    print("\n=== 加载性能测试 ===")

    # 测试正常导入
    start_time = time.time()
    import json as json1
    import time as time1
    import os as os1
    import sys as sys1
    import pathlib as pathlib1
    normal_time = time.time() - start_time
    print(f"  正常导入5个模块: {normal_time*1000:.2f}ms")

    # 测试懒加载（首次加载）
    loader = SmartLazyLoader(enable_background_loading=False)
    loader.register('json')
    loader.register('time')
    loader.register('os')
    loader.register('sys')
    loader.register('pathlib')

    start_time = time.time()
    loader.load_many(['json', 'time', 'os', 'sys', 'pathlib'])
    lazy_time = time.time() - start_time
    print(f"  懒加载5个模块: {lazy_time*1000:.2f}ms")

    # 测试缓存命中（再次加载）
    start_time = time.time()
    loader.load_many(['json', 'time', 'os', 'sys', 'pathlib'])
    cached_time = time.time() - start_time
    print(f"  缓存命中5个模块: {cached_time*1000:.2f}ms")

    # 统计
    stats = loader.get_stats()
    print(f"\n  统计信息:")
    print(f"    已注册: {stats['total_registered']}")
    print(f"    已加载: {stats['total_loaded']}")
    print(f"    平均加载时间: {stats['avg_load_time_ms']:.2f}ms")
    print(f"    缓存大小: {stats['cache_size']}")

    print("\n[OK] 性能测试完成")


def test_lazy_import_function():
    """测试便捷导入函数"""
    print("\n=== 便捷导入函数测试 ===")

    # 使用便捷函数
    json_module = lazy_import('json')
    assert json_module is not None
    assert hasattr(json_module, 'loads')
    print("[OK] lazy_import函数")


def main():
    """运行所有测试"""
    print("=" * 70)
    print("智能懒加载系统测试")
    print("=" * 70)

    try:
        test_basic_loading()
        test_dependency_loading()
        test_batch_loading()
        test_background_loading()
        test_statistics()
        test_lazy_import_function()

        print("\n" + "=" * 70)
        print("性能测试")
        print("=" * 70)
        benchmark_loading()

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
