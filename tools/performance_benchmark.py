#!/usr/bin/env python3
"""
性能基准测试工具
测试系统性能并验证是否达到SLO/SLA目标
"""

import asyncio
import json
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@dataclass
class BenchmarkResult:
    """基准测试结果"""

    name: str
    iterations: int
    duration_seconds: float
    operations_per_second: float
    latencies_ms: list[float]
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    meets_target: bool
    target_ms: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """性能报告"""

    timestamp: str
    overall_status: str
    total_duration_seconds: float
    benchmarks: list[BenchmarkResult]
    system_metrics: dict[str, Any]
    slo_compliance: dict[str, bool]


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.config_dir = PROJECT_ROOT / "config"
        self.results: list[BenchmarkResult] = []

        # 加载配置
        self.perf_config = self._load_config("performance.json")
        self.sla_config = self._load_config("sla_config.json")

    def _load_config(self, filename: str) -> dict:
        """加载配置文件"""
        try:
            config_path = self.config_dir / filename
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def measure_latency(
        self, func: Callable, iterations: int = 100, warmup: int = 10
    ) -> list[float]:
        """测量延迟"""
        latencies = []

        # 预热
        for _ in range(warmup):
            func()

        # 测量
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # 转换为毫秒

        return latencies

    async def measure_async_latency(
        self, func: Callable, iterations: int = 100, warmup: int = 10
    ) -> list[float]:
        """测量异步函数延迟"""
        latencies = []

        # 预热
        for _ in range(warmup):
            await func()

        # 测量
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        return latencies

    def analyze_latencies(
        self, name: str, latencies: list[float], target_ms: float
    ) -> BenchmarkResult:
        """分析延迟数据"""
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        p50 = sorted_latencies[int(n * 0.50)]
        p95 = sorted_latencies[int(n * 0.95)]
        p99 = sorted_latencies[int(n * 0.99)]

        min_latency = min(sorted_latencies)
        max_latency = max(sorted_latencies)
        mean_latency = statistics.mean(sorted_latencies)
        median_latency = statistics.median(sorted_latencies)

        total_duration = sum(latencies) / 1000  # 转换为秒
        ops_per_second = n / total_duration if total_duration > 0 else 0

        meets_target = p95 <= target_ms

        return BenchmarkResult(
            name=name,
            iterations=n,
            duration_seconds=total_duration,
            operations_per_second=ops_per_second,
            latencies_ms=latencies,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            min_ms=min_latency,
            max_ms=max_latency,
            mean_ms=mean_latency,
            median_ms=median_latency,
            meets_target=meets_target,
            target_ms=target_ms,
        )

    def benchmark_data_structure_operations(self) -> BenchmarkResult:
        """基准测试：数据结构操作"""
        test_data = list(range(1000))

        def operation():
            # 模拟常见数据操作
            result = []
            for item in test_data:
                if item % 2 == 0:
                    result.append(item * 2)
            return sum(result)

        latencies = self.measure_latency(operation, iterations=1000)

        # 目标：简单操作应该在1ms内完成
        return self.analyze_latencies("数据结构操作", latencies, target_ms=1.0)

    def benchmark_json_serialization(self) -> BenchmarkResult:
        """基准测试：JSON序列化"""
        test_data = {
            "experiment_id": "exp_001",
            "user_id": "user_123",
            "steps": [{"id": i, "name": f"Step {i}", "data": list(range(10))} for i in range(50)],
            "metadata": {"created_at": "2025-10-06T10:00:00", "tags": ["test", "benchmark"]},
        }

        def operation():
            json_str = json.dumps(test_data)
            json.loads(json_str)

        latencies = self.measure_latency(operation, iterations=500)

        # 目标：JSON操作应该在5ms内完成
        return self.analyze_latencies("JSON序列化/反序列化", latencies, target_ms=5.0)

    def benchmark_file_io(self) -> BenchmarkResult:
        """基准测试：文件I/O"""
        import tempfile

        test_data = {"test": "data" * 100}

        def operation():
            with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
                json.dump(test_data, f)
                f.flush()

        latencies = self.measure_latency(operation, iterations=100)

        # 目标：小文件I/O应该在10ms内完成
        return self.analyze_latencies("文件I/O操作", latencies, target_ms=10.0)

    def benchmark_computation(self) -> BenchmarkResult:
        """基准测试：计算密集型操作"""

        def operation():
            # 模拟化学计算
            result = 0
            for i in range(1000):
                result += (i**2) * 0.5 - (i * 0.3) + 10
            return result

        latencies = self.measure_latency(operation, iterations=500)

        # 目标：计算操作应该在2ms内完成
        return self.analyze_latencies("计算密集型操作", latencies, target_ms=2.0)

    async def benchmark_async_operations(self) -> BenchmarkResult:
        """基准测试：异步操作"""

        async def operation():
            await asyncio.sleep(0.001)  # 模拟异步I/O
            return sum(range(100))

        latencies = await self.measure_async_latency(operation, iterations=200)

        # 目标：异步操作开销应该在5ms内
        return self.analyze_latencies("异步操作", latencies, target_ms=5.0)

    def benchmark_cache_operations(self) -> BenchmarkResult:
        """基准测试：缓存操作"""
        try:
            from src.core.cache import MemoryCache

            cache = MemoryCache(max_size=1000)
            test_keys = [f"key_{i}" for i in range(100)]
            test_values = [{"data": f"value_{i}"} for i in range(100)]

            # 预填充缓存
            for key, value in zip(test_keys, test_values, strict=False):
                cache.set(key, value)

            def operation():
                # 50% 读取，50% 写入
                for i in range(10):
                    if i % 2 == 0:
                        cache.get(test_keys[i % len(test_keys)])
                    else:
                        cache.set(test_keys[i % len(test_keys)], test_values[i % len(test_values)])

            latencies = self.measure_latency(operation, iterations=500)

            return self.analyze_latencies("缓存操作", latencies, target_ms=0.5)

        except ImportError:
            # 如果缓存模块不可用，返回跳过的结果
            return BenchmarkResult(
                name="缓存操作",
                iterations=0,
                duration_seconds=0,
                operations_per_second=0,
                latencies_ms=[],
                p50_ms=0,
                p95_ms=0,
                p99_ms=0,
                min_ms=0,
                max_ms=0,
                mean_ms=0,
                median_ms=0,
                meets_target=True,
                target_ms=0.5,
                details={"status": "skipped", "reason": "cache module not available"},
            )

    def benchmark_memory_allocation(self) -> BenchmarkResult:
        """基准测试：内存分配"""

        def operation():
            # 创建和销毁对象
            data = []
            for i in range(1000):
                data.append({"id": i, "value": i * 2})
            del data

        latencies = self.measure_latency(operation, iterations=200)

        return self.analyze_latencies("内存分配/释放", latencies, target_ms=5.0)

    def get_system_metrics(self) -> dict[str, Any]:
        """获取系统指标"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024**2),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "cpu_count": psutil.cpu_count(),
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            return {"status": "unavailable", "reason": "psutil not installed"}

    def check_slo_compliance(self, results: list[BenchmarkResult]) -> dict[str, bool]:
        """检查SLO合规性"""
        slo = self.sla_config.get("sla", {}).get("performance_slo", {})
        response_time = slo.get("response_time", {})

        ui_operations = response_time.get("ui_operations", {})
        ui_operations.get("render_ms", 100)

        compliance = {}

        for result in results:
            # 检查是否满足目标
            compliance[result.name] = result.meets_target

        # 总体合规性
        compliance["overall"] = all(compliance.values())

        return compliance

    async def run_all_benchmarks(self) -> PerformanceReport:
        """运行所有基准测试"""
        print("\n" + "=" * 70)
        print("⚡ VirtualChemLab 性能基准测试")
        print("=" * 70 + "\n")

        start_time = time.perf_counter()

        # 运行同步基准测试
        benchmarks = [
            self.benchmark_data_structure_operations(),
            self.benchmark_json_serialization(),
            self.benchmark_file_io(),
            self.benchmark_computation(),
            self.benchmark_cache_operations(),
            self.benchmark_memory_allocation(),
        ]

        # 运行异步基准测试
        async_result = await self.benchmark_async_operations()
        benchmarks.append(async_result)

        end_time = time.perf_counter()
        total_duration = end_time - start_time

        # 获取系统指标
        system_metrics = self.get_system_metrics()

        # 检查SLO合规性
        slo_compliance = self.check_slo_compliance(benchmarks)

        # 确定总体状态
        if all(b.meets_target for b in benchmarks if b.iterations > 0):
            overall_status = "pass"
        elif any(not b.meets_target for b in benchmarks if b.iterations > 0):
            overall_status = "fail"
        else:
            overall_status = "warning"

        report = PerformanceReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            total_duration_seconds=total_duration,
            benchmarks=benchmarks,
            system_metrics=system_metrics,
            slo_compliance=slo_compliance,
        )

        return report

    def print_report(self, report: PerformanceReport):
        """打印报告"""
        print("\n📊 基准测试结果\n")

        for benchmark in report.benchmarks:
            if benchmark.iterations == 0:
                print(f"⏭️  {benchmark.name}: 已跳过")
                if benchmark.details.get("reason"):
                    print(f"   原因: {benchmark.details['reason']}")
                print()
                continue

            icon = "✅" if benchmark.meets_target else "❌"
            print(f"{icon} {benchmark.name}")
            print(f"   迭代次数: {benchmark.iterations}")
            print(f"   吞吐量: {benchmark.operations_per_second:.2f} ops/s")
            print("   延迟统计 (ms):")
            print(f"      P50: {benchmark.p50_ms:.2f}")
            print(f"      P95: {benchmark.p95_ms:.2f} (目标: ≤{benchmark.target_ms:.2f})")
            print(f"      P99: {benchmark.p99_ms:.2f}")
            print(f"      最小: {benchmark.min_ms:.2f}")
            print(f"      最大: {benchmark.max_ms:.2f}")
            print(f"      平均: {benchmark.mean_ms:.2f}")

            if not benchmark.meets_target:
                print(
                    f"   ⚠️  未达到性能目标 (P95: {benchmark.p95_ms:.2f}ms > {benchmark.target_ms:.2f}ms)"
                )
            print()

        # 系统指标
        print("=" * 70)
        print("🖥️  系统指标")
        print("=" * 70)
        metrics = report.system_metrics
        if metrics.get("status") != "unavailable":
            print(f"CPU使用率: {metrics['cpu_percent']:.1f}%")
            print(f"内存使用率: {metrics['memory_percent']:.1f}%")
            print(f"可用内存: {metrics['memory_available_mb']:.0f} MB")
            print(f"磁盘使用率: {metrics['disk_percent']:.1f}%")
            print(f"CPU核心数: {metrics['cpu_count']}")
        else:
            print("系统指标不可用 (需要安装 psutil)")

        # SLO合规性
        print("\n" + "=" * 70)
        print("📋 SLO合规性")
        print("=" * 70)

        for name, compliant in report.slo_compliance.items():
            if name != "overall":
                icon = "✅" if compliant else "❌"
                print(f"{icon} {name}: {'合规' if compliant else '不合规'}")

        print("\n" + "=" * 70)
        print("📊 测试总结")
        print("=" * 70)
        print(f"总体状态: {report.overall_status.upper()}")
        print(f"测试耗时: {report.total_duration_seconds:.2f} 秒")
        print(f"测试时间: {report.timestamp}")

        passed = sum(1 for b in report.benchmarks if b.meets_target and b.iterations > 0)
        failed = sum(1 for b in report.benchmarks if not b.meets_target and b.iterations > 0)
        skipped = sum(1 for b in report.benchmarks if b.iterations == 0)

        print(f"\n✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⏭️  跳过: {skipped}")
        print("=" * 70 + "\n")

    def save_report(self, report: PerformanceReport, filepath: Path):
        """保存报告到JSON文件"""
        report_data = {
            "timestamp": report.timestamp,
            "overall_status": report.overall_status,
            "total_duration_seconds": report.total_duration_seconds,
            "system_metrics": report.system_metrics,
            "slo_compliance": report.slo_compliance,
            "benchmarks": [
                {
                    "name": b.name,
                    "iterations": b.iterations,
                    "duration_seconds": b.duration_seconds,
                    "operations_per_second": b.operations_per_second,
                    "p50_ms": b.p50_ms,
                    "p95_ms": b.p95_ms,
                    "p99_ms": b.p99_ms,
                    "min_ms": b.min_ms,
                    "max_ms": b.max_ms,
                    "mean_ms": b.mean_ms,
                    "median_ms": b.median_ms,
                    "meets_target": b.meets_target,
                    "target_ms": b.target_ms,
                    "details": b.details,
                }
                for b in report.benchmarks
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"📄 详细报告已保存到: {filepath}")


async def main():
    """主函数"""
    # 设置UTF-8输出
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    benchmark = PerformanceBenchmark()
    report = await benchmark.run_all_benchmarks()
    benchmark.print_report(report)

    # 保存报告
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"performance_benchmark_{timestamp}.json"
    benchmark.save_report(report, report_file)

    # 返回退出码
    return 0 if report.overall_status != "fail" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
