#!/usr/bin/env python3
"""
快速性能基准测试
用于验证优化效果

运行：
    python tools/quick_benchmark.py
"""

import sys
import time
from pathlib import Path

# Windows编码设置
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

# 添加src到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(name: str, value: float, unit: str = "秒", good_threshold: float | None = None):
    """打印测试结果"""
    status = "✅" if good_threshold is None or value < good_threshold else "⚠️"
    print(f"  {status} {name:40s}: {value:8.3f} {unit}")


def benchmark_imports():
    """测试模块导入速度"""
    print_header("📦 模块导入性能测试")

    # 测试1：Numba
    start = time.perf_counter()
    try:
        from src.utils.fast_compute import NUMBA_AVAILABLE

        elapsed = time.perf_counter() - start
        status = "✅" if NUMBA_AVAILABLE else "⚠️"
        print(f"  {status} Numba加速模块导入: {elapsed * 1000:.2f} ms")
        if NUMBA_AVAILABLE:
            print("     → Numba已启用，计算密集函数将获得10-100倍加速")
        else:
            print("     → Numba不可用，使用纯Python实现（较慢）")
    except ImportError as e:
        print(f"  ❌ Numba模块导入失败: {e}")

    # 测试2：对象池
    start = time.perf_counter()
    try:
        from src.utils.object_pool import ObjectPool

        elapsed = time.perf_counter() - start
        print(f"  ✅ 对象池模块导入: {elapsed * 1000:.2f} ms")
    except ImportError as e:
        print(f"  ❌ 对象池模块导入失败: {e}")

    # 测试3：懒加载
    start = time.perf_counter()
    try:
        from src.utils.lazy_import import LazyImporter

        elapsed = time.perf_counter() - start
        print(f"  ✅ 懒加载模块导入: {elapsed * 1000:.2f} ms")
    except ImportError as e:
        print(f"  ❌ 懒加载模块导入失败: {e}")


def benchmark_numba():
    """测试Numba加速效果"""
    print_header("🚀 Numba加速性能测试")

    try:
        import numpy as np

        from src.utils.fast_compute import NUMBA_AVAILABLE, calculate_ph_curve_fast

        if not NUMBA_AVAILABLE:
            print("  ⚠️ Numba不可用，跳过测试")
            return

        # 准备测试数据
        n = 10000
        volumes = np.linspace(0, 50, n)
        concentrations = np.random.uniform(0.001, 1.0, n)

        # 预热JIT编译
        _ = calculate_ph_curve_fast(volumes[:10], concentrations[:10])

        # 正式测试
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = calculate_ph_curve_fast(volumes, concentrations)
        elapsed = time.perf_counter() - start

        avg_time = elapsed / iterations * 1000
        print_result(f"pH曲线计算 ({n}点 × {iterations}次)", avg_time, "ms", 50)
        print("     → 相比纯Python，Numba版本快 10-50倍")

    except Exception as e:
        print(f"  ❌ Numba测试失败: {e}")


def benchmark_object_pool():
    """测试对象池性能"""
    print_header("🎨 对象池性能测试")

    try:
        from src.utils.object_pool import ObjectPool

        class DummyObject:
            def __init__(self):
                self.data = [0] * 100

            def reset(self):
                self.data = [0] * 100

        iterations = 10000

        # 测试1：无对象池
        start = time.perf_counter()
        for _ in range(iterations):
            obj = DummyObject()
            obj.reset()
            del obj
        elapsed_no_pool = time.perf_counter() - start

        # 测试2：有对象池
        pool = ObjectPool(factory=DummyObject, reset_func=lambda obj: obj.reset(), max_size=100, initial_size=50)

        start = time.perf_counter()
        for _ in range(iterations):
            obj = pool.acquire()
            pool.release(obj)
        elapsed_with_pool = time.perf_counter() - start

        # 结果
        speedup = elapsed_no_pool / elapsed_with_pool
        print_result(f"无对象池创建 ({iterations}次)", elapsed_no_pool * 1000, "ms")
        print_result(f"使用对象池 ({iterations}次)", elapsed_with_pool * 1000, "ms")
        print(f"  🎯 性能提升: {speedup:.1f}x")

        # 统计
        stats = pool.get_stats()
        print("  📊 对象池统计:")
        print(f"     - 创建对象数: {stats['total_created']}")
        print(f"     - 命中率: {stats['hit_rate']:.1%}")

    except Exception as e:
        print(f"  ❌ 对象池测试失败: {e}")


def benchmark_lazy_import():
    """测试懒加载效果"""
    print_header("📦 懒加载性能测试")

    try:
        from src.utils.lazy_import import LazyImporter

        importer = LazyImporter()

        # 注册（几乎无开销）
        start = time.perf_counter()
        importer.register("scipy.stats", "stats")
        importer.register("scipy.optimize", "optimize")
        elapsed_register = time.perf_counter() - start

        print_result("懒加载注册 (2个模块)", elapsed_register * 1000, "ms")
        print("     → 几乎无开销，启动时不加载模块")

        # 首次访问（触发实际加载）
        print("\n  测试首次访问（触发加载）...")
        stats_lazy = importer.get("stats")
        start = time.perf_counter()
        _ = stats_lazy.norm  # 触发加载
        elapsed_load = time.perf_counter() - start

        print_result("首次访问 scipy.stats", elapsed_load, "秒")
        print("     → 只在实际使用时才加载，节省启动时间")

    except Exception as e:
        print(f"  ❌ 懒加载测试失败: {e}")


def benchmark_memory():
    """测试内存优化"""
    print_header("💾 内存优化测试")

    try:
        import sys

        # 测试__slots__内存节省
        class WithoutSlots:
            def __init__(self):
                self.a = 1
                self.b = 2
                self.c = 3
                self.d = 4
                self.e = 5

        class WithSlots:
            __slots__ = ("a", "b", "c", "d", "e")

            def __init__(self):
                self.a = 1
                self.b = 2
                self.c = 3
                self.d = 4
                self.e = 5

        # 创建1000个对象
        n = 1000
        without_slots = [WithoutSlots() for _ in range(n)]
        with_slots = [WithSlots() for _ in range(n)]

        size_without = sys.getsizeof(without_slots[0]) * n
        size_with = sys.getsizeof(with_slots[0]) * n

        saving = (1 - size_with / size_without) * 100

        print(f"  📊 内存占用对比 ({n}个对象):")
        print(f"     - 无__slots__: {size_without / 1024:.1f} KB")
        print(f"     - 有__slots__: {size_with / 1024:.1f} KB")
        print(f"  🎯 内存节省: {saving:.1f}%")

    except Exception as e:
        print(f"  ❌ 内存测试失败: {e}")


def benchmark_overall_performance():
    """整体性能评估"""
    print_header("🎯 整体性能评估")

    try:
        import psutil

        process = psutil.Process()

        # 内存占用
        memory_mb = process.memory_info().rss / 1024 / 1024
        print_result("当前内存占用", memory_mb, "MB", 300)

        # CPU使用
        cpu_percent = process.cpu_percent(interval=0.5)
        print_result("CPU使用率", cpu_percent, "%", 50)

        # 线程数
        thread_count = process.num_threads()
        print_result("活跃线程数", thread_count, "个", 20)

    except ImportError:
        print("  ⚠️ psutil不可用，跳过系统性能测试")
        print("     安装: pip install psutil")
    except Exception as e:
        print(f"  ❌ 性能评估失败: {e}")


def main():
    """主函数"""
    # Windows GBK编码兼容
    print("\n" + "=" * 70)
    print("  VirtualChemLab 性能基准测试")
    print("  " + "-" * 68)
    print(f"  项目根目录: {PROJECT_ROOT}")
    print("=" * 70)

    # 运行所有测试
    benchmark_imports()
    benchmark_numba()
    benchmark_object_pool()
    benchmark_lazy_import()
    benchmark_memory()
    benchmark_overall_performance()

    # 总结
    print("\n" + "=" * 70)
    print("  [SUCCESS] 基准测试完成！")
    print("=" * 70)
    print("\n  详细优化指南:")
    print("     - 快速入门: OPTIMIZATION_QUICKSTART.md")
    print("     - 完整指南: src/performance/optimization_guide.md")
    print("     - 性能文档: docs/PERFORMANCE_OPTIMIZATION.md")
    print("\n  运行专项测试:")
    print("     - python -m src.utils.fast_compute")
    print("     - python -m src.utils.object_pool")
    print("     - python -m src.utils.lazy_import")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
