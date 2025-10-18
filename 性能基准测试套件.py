#!/usr/bin/env python3
"""
VirtualChemLab 性能基准测试套件
用于验证优化效果和监控性能指标
"""

import time
import statistics
import psutil
import threading
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path

# 项目导入
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.core.cache_manager import CacheManager
from src.core.memory_manager import MemoryManager
from src.core.event_bus import EventBus, Event
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    mean_time: float
    median_time: float
    min_time: float
    max_time: float
    std_dev: float
    iterations: int
    memory_before: float
    memory_after: float
    memory_delta: float
    timestamp: datetime


class PerformanceBenchmark:
    """性能基准测试框架"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()

    def get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        return self.process.memory_info().rss / 1024 / 1024

    def benchmark_function(self,
                          name: str,
                          func: Callable,
                          iterations: int = 100,
                          warmup: int = 10,
                          *args, **kwargs) -> BenchmarkResult:
        """基准测试函数性能"""

        logger.info(f"开始基准测试: {name}")

        # 获取测试前内存
        memory_before = self.get_memory_usage()

        # 预热
        for _ in range(warmup):
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"预热阶段错误: {e}")

        # 正式测试
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"测试迭代 {i} 错误: {e}")
                continue
            end = time.perf_counter()
            times.append(end - start)

            # 每10次迭代报告进度
            if (i + 1) % 10 == 0:
                logger.info(f"进度: {i + 1}/{iterations}")

        # 获取测试后内存
        memory_after = self.get_memory_usage()

        if not times:
            logger.error(f"测试 {name} 没有有效结果")
            return None

        # 计算统计信息
        result = BenchmarkResult(
            name=name,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            iterations=len(times),
            memory_before=memory_before,
            memory_after=memory_after,
            memory_delta=memory_after - memory_before,
            timestamp=datetime.now()
        )

        self.results.append(result)
        logger.info(f"基准测试完成: {name}")
        logger.info(f"  平均时间: {result.mean_time:.6f}s")
        logger.info(f"  内存变化: {result.memory_delta:.2f}MB")

        return result

    def benchmark_cache_performance(self):
        """测试缓存性能"""
        logger.info("=" * 60)
        logger.info("缓存性能基准测试")
        logger.info("=" * 60)

        # 测试数据
        test_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        # 创建缓存管理器
        cache = CacheManager(max_size=500, default_ttl=3600)

        # 测试1: 缓存写入性能
        def write_test():
            for key, value in test_data.items():
                cache.set(key, value)

        self.benchmark_function("cache_write", write_test, iterations=50)

        # 测试2: 缓存读取性能
        def read_test():
            for key in test_data.keys():
                cache.get(key)

        self.benchmark_function("cache_read", read_test, iterations=100)

        # 测试3: 缓存命中率测试
        cache_hits = 0
        cache_misses = 0

        for key in test_data.keys():
            if cache.get(key) is not None:
                cache_hits += 1
            else:
                cache_misses += 1

        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        logger.info(f"缓存命中率: {hit_rate:.2%}")

        # 清理
        cache.clear()

    def benchmark_memory_manager(self):
        """测试内存管理器性能"""
        logger.info("=" * 60)
        logger.info("内存管理器性能基准测试")
        logger.info("=" * 60)

        memory_manager = MemoryManager()

        # 测试1: 对象跟踪性能
        def track_objects():
            for i in range(1000):
                obj = {"id": i, "data": f"data_{i}"}
                memory_manager.track_object(obj, f"category_{i % 10}")

        self.benchmark_function("memory_track", track_objects, iterations=20)

        # 测试2: 内存清理性能
        def cleanup_memory():
            memory_manager.cleanup_memory(force=True)

        self.benchmark_function("memory_cleanup", cleanup_memory, iterations=10)

        # 测试3: 内存指标获取性能
        def get_metrics():
            memory_manager.get_memory_metrics()

        self.benchmark_function("memory_metrics", get_metrics, iterations=100)

    def benchmark_event_bus(self):
        """测试事件总线性能"""
        logger.info("=" * 60)
        logger.info("事件总线性能基准测试")
        logger.info("=" * 60)

        event_bus = EventBus()

        # 注册事件处理器
        def event_handler(event: Event):
            return f"processed_{event.name}"

        event_bus.subscribe("test.event", event_handler)
        event_bus.subscribe("test.*", event_handler)
        event_bus.subscribe("*", event_handler)

        # 测试1: 事件发布性能
        def publish_event():
            event = Event(name="test.event", data={"test": "data"})
            event_bus.publish(event)

        self.benchmark_function("event_publish", publish_event, iterations=200)

        # 测试2: 事件订阅性能
        def subscribe_event():
            event_bus.subscribe(f"test.event.{time.time()}", event_handler)

        self.benchmark_function("event_subscribe", subscribe_event, iterations=100)

        # 清理
        event_bus.clear()

    def benchmark_concurrent_performance(self):
        """测试并发性能"""
        logger.info("=" * 60)
        logger.info("并发性能基准测试")
        logger.info("=" * 60)

        cache = CacheManager(max_size=1000)
        results = []

        def worker(worker_id: int):
            """工作线程"""
            start_time = time.perf_counter()

            # 模拟工作负载
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                cache.set(key, value)
                cache.get(key)

            end_time = time.perf_counter()
            results.append(end_time - start_time)

        # 测试不同线程数的性能
        for thread_count in [1, 2, 4, 8]:
            logger.info(f"测试 {thread_count} 个线程")

            threads = []
            results.clear()

            start_time = time.perf_counter()

            for i in range(thread_count):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            end_time = time.perf_counter()

            total_time = end_time - start_time
            avg_time = statistics.mean(results) if results else 0

            logger.info(f"  总时间: {total_time:.3f}s")
            logger.info(f"  平均线程时间: {avg_time:.3f}s")
            logger.info(f"  吞吐量: {thread_count * 100 / total_time:.1f} ops/s")

        cache.clear()

    def benchmark_memory_leak_detection(self):
        """测试内存泄漏检测"""
        logger.info("=" * 60)
        logger.info("内存泄漏检测基准测试")
        logger.info("=" * 60)

        memory_manager = MemoryManager()

        # 模拟内存泄漏场景
        def create_objects():
            objects = []
            for i in range(1000):
                obj = {"id": i, "data": "x" * 1000}  # 1KB数据
                memory_manager.track_object(obj, "leak_test")
                objects.append(obj)
            return objects

        # 测试内存增长
        initial_memory = self.get_memory_usage()

        for round_num in range(5):
            logger.info(f"第 {round_num + 1} 轮测试")

            objects = create_objects()
            current_memory = self.get_memory_usage()
            memory_delta = current_memory - initial_memory

            logger.info(f"  内存增长: {memory_delta:.2f}MB")

            # 清理对象（但保留跟踪信息）
            del objects

            # 强制垃圾回收
            import gc
            gc.collect()

            # 检查内存泄漏
            leaks = memory_manager._detect_memory_leaks()
            if leaks > 0:
                logger.warning(f"  检测到 {leaks} 个内存泄漏")
            else:
                logger.info("  未检测到内存泄漏")

        # 清理
        memory_manager.cleanup_memory(force=True)

    def generate_report(self) -> str:
        """生成基准测试报告"""
        if not self.results:
            return "没有基准测试结果"

        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 性能基准测试报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试结果数量: {len(self.results)}")
        report.append("")

        # 按类别分组
        categories = {}
        for result in self.results:
            category = result.name.split('_')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category, results in categories.items():
            report.append(f"## {category.upper()} 性能测试")
            report.append("-" * 40)

            for result in results:
                report.append(f"### {result.name}")
                report.append(f"  平均时间: {result.mean_time:.6f}s")
                report.append(f"  中位数时间: {result.median_time:.6f}s")
                report.append(f"  最小时间: {result.min_time:.6f}s")
                report.append(f"  最大时间: {result.max_time:.6f}s")
                report.append(f"  标准差: {result.std_dev:.6f}s")
                report.append(f"  迭代次数: {result.iterations}")
                report.append(f"  内存变化: {result.memory_delta:.2f}MB")
                report.append("")

        # 性能建议
        report.append("## 性能建议")
        report.append("-" * 40)

        # 分析缓存性能
        cache_results = [r for r in self.results if 'cache' in r.name]
        if cache_results:
            avg_cache_time = statistics.mean([r.mean_time for r in cache_results])
            if avg_cache_time > 0.001:  # 1ms
                report.append("- 缓存性能需要优化，考虑实现更高效的LRU算法")
            else:
                report.append("- 缓存性能良好")

        # 分析内存性能
        memory_results = [r for r in self.results if 'memory' in r.name]
        if memory_results:
            avg_memory_delta = statistics.mean([r.memory_delta for r in memory_results])
            if avg_memory_delta > 10:  # 10MB
                report.append("- 内存使用需要优化，检查内存泄漏")
            else:
                report.append("- 内存使用正常")

        # 分析事件性能
        event_results = [r for r in self.results if 'event' in r.name]
        if event_results:
            avg_event_time = statistics.mean([r.mean_time for r in event_results])
            if avg_event_time > 0.0001:  # 0.1ms
                report.append("- 事件处理性能需要优化，考虑缓存正则表达式")
            else:
                report.append("- 事件处理性能良好")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def save_results(self, filename: str = "benchmark_results.json"):
        """保存测试结果到文件"""
        results_data = []

        for result in self.results:
            results_data.append({
                "name": result.name,
                "mean_time": result.mean_time,
                "median_time": result.median_time,
                "min_time": result.min_time,
                "max_time": result.max_time,
                "std_dev": result.std_dev,
                "iterations": result.iterations,
                "memory_before": result.memory_before,
                "memory_after": result.memory_after,
                "memory_delta": result.memory_delta,
                "timestamp": result.timestamp.isoformat()
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        logger.info(f"测试结果已保存到: {filename}")

    def run_all_benchmarks(self):
        """运行所有基准测试"""
        logger.info("开始运行所有基准测试")
        logger.info("=" * 60)

        try:
            # 运行各项测试
            self.benchmark_cache_performance()
            self.benchmark_memory_manager()
            self.benchmark_event_bus()
            self.benchmark_concurrent_performance()
            self.benchmark_memory_leak_detection()

            # 生成报告
            report = self.generate_report()
            print(report)

            # 保存结果
            self.save_results()

            logger.info("所有基准测试完成")

        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    print("VirtualChemLab 性能基准测试套件")
    print("=" * 60)

    # 创建基准测试实例
    benchmark = PerformanceBenchmark()

    # 运行所有测试
    benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()
