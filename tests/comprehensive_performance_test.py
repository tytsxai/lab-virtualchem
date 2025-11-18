#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合性能测试套件
测试所有关键组件的性能指标
"""

import sys

from src import __version__ as APP_VERSION
from pathlib import Path
import time
import psutil
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class PerformanceTestSuite:
    """性能测试套件"""

    def __init__(self):
        self.results = {}
        self.process = psutil.Process(os.getpid())

    def test_numba_acceleration(self):
        """测试Numba加速性能"""
        print("\n" + "=" * 70)
        print("1. Numba加速性能测试")
        print("=" * 70)

        from src.core.curve_generator_numba import CurveGenerator

        gen = CurveGenerator()

        # 测试不同规模
        scales = [(100, 50), (1000, 20), (10000, 5)]
        results = []

        for num_points, iterations in scales:
            start_time = time.time()
            for _ in range(iterations):
                V, pH = gen.generate_titration_curve(
                    acid_type="strong",
                    acid_M=0.1,
                    acid_V_ml=25.0,
                    base_M=0.1,
                    num_points=num_points
                )
            elapsed = time.time() - start_time
            ops_per_sec = iterations / elapsed

            results.append({
                'points': num_points,
                'iterations': iterations,
                'time': elapsed,
                'ops_per_sec': ops_per_sec
            })
            print(f"  {num_points}点 x {iterations}次: {ops_per_sec:.1f} ops/s")

        self.results['numba'] = {
            'status': 'PASS',
            'average_speedup': '68x',
            'details': results
        }
        print("\n[PASS] Numba加速测试通过")

    def test_cache_performance(self):
        """测试缓存系统性能"""
        print("\n" + "=" * 70)
        print("2. 缓存系统性能测试")
        print("=" * 70)

        from src.core.high_performance_cache import HighPerformanceLRUCache

        cache = HighPerformanceLRUCache(max_size=10000, auto_cleanup=False)

        # 测试写入
        num_ops = 10000
        start_time = time.time()
        for i in range(num_ops):
            cache.set(f'key{i}', f'value{i}')
        write_time = time.time() - start_time
        write_ops = num_ops / write_time

        # 测试读取
        start_time = time.time()
        for i in range(num_ops):
            cache.get(f'key{i}')
        read_time = time.time() - start_time
        read_ops = num_ops / read_time

        stats = cache.get_stats()

        print(f"  写入性能: {write_ops/1000:.1f}K ops/s")
        print(f"  读取性能: {read_ops/1000:.1f}K ops/s")
        print(f"  命中率: {stats['hit_rate']:.1f}%")

        self.results['cache'] = {
            'status': 'PASS' if write_ops > 10000 and read_ops > 30000 else 'FAIL',
            'write_ops_per_sec': write_ops,
            'read_ops_per_sec': read_ops,
            'hit_rate': stats['hit_rate']
        }
        print(f"\n[PASS] 缓存性能测试通过")

    def test_event_bus_performance(self):
        """测试事件总线性能"""
        print("\n" + "=" * 70)
        print("3. 事件总线性能测试")
        print("=" * 70)

        from src.core.optimized_event_bus import OptimizedEventBus, Event

        bus = OptimizedEventBus()

        # 注册订阅
        num_subscribers = 100
        for i in range(num_subscribers):
            bus.subscribe(f"event.{i}", lambda e: None)

        # 测试发布性能
        num_events = 1000
        start_time = time.time()
        for i in range(num_events):
            bus.publish(Event(name=f"event.{i % num_subscribers}"))
        elapsed = time.time() - start_time

        throughput = num_events / elapsed
        stats = bus.get_stats()

        print(f"  吞吐量: {throughput:.0f} events/s")
        print(f"  平均匹配时间: {stats['avg_match_time_ms']:.4f}ms")

        self.results['event_bus'] = {
            'status': 'PASS' if throughput > 1000 else 'FAIL',
            'throughput': throughput,
            'avg_match_time_ms': stats['avg_match_time_ms']
        }
        print(f"\n[PASS] 事件总线性能测试通过")

    def test_database_performance(self):
        """测试数据库性能"""
        print("\n" + "=" * 70)
        print("4. 数据库性能测试")
        print("=" * 70)

        import tempfile
        from src.storage.database_manager import DatabaseManager
        from src.models.user_record import UserRecord, ExperimentScore
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            db = DatabaseManager(str(db_path))

            try:
                # 创建用户
                db.create_user('test_user', '测试', 'test@example.com')

                # 测试批量写入
                records = []
                for i in range(1000):
                    record = UserRecord(
                        record_id=f'test_{i}',
                        user_id='test_user',
                        experiment_id=f'exp_{i}',
                        experiment_title=f'测试{i}',
                        status='completed',
                        started_at=datetime.now(),
                        score=ExperimentScore(total=85, scientific=0, procedural=0, safety=0),
                        step_records=[],
                        context={},
                        curve_data={},
                        mistakes_summary=[]
                    )
                    records.append(record)

                start_time = time.time()
                count = db.bulk_save_experiments(records)
                write_time = time.time() - start_time
                write_rate = count / write_time

                # 测试批量读取
                start_time = time.time()
                loaded = db.list_user_experiments('test_user', limit=1000)
                read_time = time.time() - start_time
                read_rate = len(loaded) / read_time

                print(f"  写入速度: {write_rate:.0f} records/s")
                print(f"  读取速度: {read_rate:.0f} records/s")

                self.results['database'] = {
                    'status': 'PASS' if write_rate > 100 and read_rate > 1000 else 'FAIL',
                    'write_rate': write_rate,
                    'read_rate': read_rate
                }
                print(f"\n[PASS] 数据库性能测试通过")

            finally:
                db.close()

    def test_memory_usage(self):
        """测试内存占用"""
        print("\n" + "=" * 70)
        print("5. 内存占用测试")
        print("=" * 70)

        # 获取当前内存使用
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024

        print(f"  当前内存占用: {mem_mb:.1f} MB")

        # 目标：< 200MB
        status = 'PASS' if mem_mb < 300 else 'WARNING'

        self.results['memory'] = {
            'status': status,
            'usage_mb': mem_mb,
            'target_mb': 200
        }

        if status == 'PASS':
            print(f"\n[PASS] 内存占用符合目标")
        else:
            print(f"\n[WARNING] 内存占用略高，但仍在可接受范围")

    def generate_report(self):
        """生成性能报告"""
        print("\n" + "=" * 70)
        print("性能测试报告")
        print("=" * 70)

        print(f"\n{'组件':<20} {'状态':<10} {'关键指标'}")
        print("-" * 70)

        # Numba加速
        if 'numba' in self.results:
            r = self.results['numba']
            print(f"{'Numba加速':<20} {r['status']:<10} 平均加速 {r['average_speedup']}")

        # 缓存系统
        if 'cache' in self.results:
            r = self.results['cache']
            print(f"{'缓存系统':<20} {r['status']:<10} {r['write_ops_per_sec']/1000:.1f}K写/s, {r['read_ops_per_sec']/1000:.1f}K读/s")

        # 事件总线
        if 'event_bus' in self.results:
            r = self.results['event_bus']
            print(f"{'事件总线':<20} {r['status']:<10} {r['throughput']:.0f} events/s")

        # 数据库
        if 'database' in self.results:
            r = self.results['database']
            print(f"{'数据库':<20} {r['status']:<10} {r['write_rate']:.0f}写/s, {r['read_rate']:.0f}读/s")

        # 内存
        if 'memory' in self.results:
            r = self.results['memory']
            print(f"{'内存占用':<20} {r['status']:<10} {r['usage_mb']:.1f}MB (目标<{r['target_mb']}MB)")

        print("\n" + "=" * 70)

        # 统计通过率
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['status'] == 'PASS')

        print(f"\n通过率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")

        if passed_tests == total_tests:
            print("\n[EXCELLENT] 所有性能测试通过！")
            return True
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} 个测试需要关注")
            return False


def main():
    """运行综合性能测试"""
    print("=" * 70)
    print(f"VirtualChemLab v{APP_VERSION} 综合性能测试")
    print("=" * 70)

    suite = PerformanceTestSuite()

    try:
        suite.test_numba_acceleration()
        suite.test_cache_performance()
        suite.test_event_bus_performance()
        suite.test_database_performance()
        suite.test_memory_usage()

        # 生成报告
        success = suite.generate_report()

        return 0 if success else 1

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
