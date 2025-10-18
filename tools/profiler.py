"""
性能分析和优化工具

提供代码性能分析、瓶颈检测、优化建议等功能
"""

import cProfile
import functools
import io
import json
import pstats
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ProfileResult:
    """性能分析结果"""
    function_name: str
    total_time: float
    calls: int
    avg_time: float
    memory_peak_mb: float
    memory_current_mb: float


@dataclass
class BottleneckInfo:
    """瓶颈信息"""
    location: str
    description: str
    impact: str  # high, medium, low
    suggestion: str
    metrics: dict[str, Any]


class FunctionProfiler:
    """函数性能分析器"""

    def __init__(self):
        self.results: list[ProfileResult] = []
        self.profiler = cProfile.Profile()

    def profile_function(self, func: Callable) -> Callable:
        """装饰器：分析函数性能"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 开始内存追踪
            tracemalloc.start()

            # 开始性能分析
            self.profiler.enable()
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # 停止性能分析
                end_time = time.perf_counter()
                self.profiler.disable()

                # 获取内存信息
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                # 获取调用统计
                stats = pstats.Stats(self.profiler)
                stats.calc_callees()

                # 记录结果
                func_stats = None
                for stat in stats.stats.items():
                    if func.__name__ in stat[0][2]:
                        func_stats = stat[1]
                        break

                if func_stats:
                    self.results.append(ProfileResult(
                        function_name=func.__name__,
                        total_time=end_time - start_time,
                        calls=func_stats[0],
                        avg_time=(end_time - start_time) / func_stats[0] if func_stats[0] > 0 else 0,
                        memory_peak_mb=peak / 1024 / 1024,
                        memory_current_mb=current / 1024 / 1024
                    ))

        return wrapper

    def print_stats(self, sort_by: str = 'cumulative', top_n: int = 20):
        """打印性能统计"""
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats(sort_by)
        stats.print_stats(top_n)
        print(stream.getvalue())

    def get_results(self) -> list[ProfileResult]:
        """获取分析结果"""
        return self.results

    def export_results(self, output_path: Path):
        """导出分析结果"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'results': [asdict(r) for r in self.results]
        }
        output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')


class MemoryProfiler:
    """内存分析器"""

    @staticmethod
    def get_top_memory_consumers(top_n: int = 10) -> list[dict[str, Any]]:
        """获取内存占用最多的代码行"""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        results = []
        for stat in top_stats[:top_n]:
            results.append({
                'file': stat.traceback.format()[0],
                'size_mb': stat.size / 1024 / 1024,
                'count': stat.count
            })

        return results

    @staticmethod
    def compare_snapshots(snapshot1, snapshot2) -> list[dict[str, Any]]:
        """比较两个内存快照"""
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')

        results = []
        for stat in top_stats[:10]:
            results.append({
                'file': stat.traceback.format()[0],
                'size_diff_mb': stat.size_diff / 1024 / 1024,
                'count_diff': stat.count_diff
            })

        return results


class PerformanceOptimizer:
    """性能优化建议器"""

    def __init__(self):
        self.bottlenecks: list[BottleneckInfo] = []

    def analyze_profile_results(self, results: list[ProfileResult]) -> list[BottleneckInfo]:
        """分析性能结果并提供优化建议"""
        bottlenecks = []

        for result in results:
            # 检查执行时间
            if result.total_time > 1.0:
                bottlenecks.append(BottleneckInfo(
                    location=result.function_name,
                    description=f"函数执行时间过长: {result.total_time:.2f}秒",
                    impact='high',
                    suggestion="考虑使用缓存、异步处理或算法优化",
                    metrics={'total_time': result.total_time, 'calls': result.calls}
                ))

            # 检查调用次数
            if result.calls > 1000:
                bottlenecks.append(BottleneckInfo(
                    location=result.function_name,
                    description=f"函数调用次数过多: {result.calls}次",
                    impact='medium',
                    suggestion="考虑批处理或减少不必要的调用",
                    metrics={'calls': result.calls, 'avg_time': result.avg_time}
                ))

            # 检查内存使用
            if result.memory_peak_mb > 100:
                bottlenecks.append(BottleneckInfo(
                    location=result.function_name,
                    description=f"内存峰值过高: {result.memory_peak_mb:.2f}MB",
                    impact='high',
                    suggestion="检查是否有内存泄漏，考虑使用生成器或流式处理",
                    metrics={'memory_peak_mb': result.memory_peak_mb}
                ))

        self.bottlenecks = bottlenecks
        return bottlenecks

    def generate_optimization_report(self, output_path: Path):
        """生成优化建议报告"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>性能优化建议报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .bottleneck {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }}
        .impact-high {{ border-left: 5px solid #e74c3c; }}
        .impact-medium {{ border-left: 5px solid #f39c12; }}
        .impact-low {{ border-left: 5px solid #3498db; }}
        .suggestion {{
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
        }}
        .metrics {{ color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>🚀 性能优化建议报告</h1>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>发现 {len(self.bottlenecks)} 个性能问题</p>

    <h2>瓶颈分析</h2>
"""

        for i, bottleneck in enumerate(self.bottlenecks, 1):
            html += f"""
    <div class="bottleneck impact-{bottleneck.impact}">
        <h3>{i}. {bottleneck.location}</h3>
        <p><strong>问题:</strong> {bottleneck.description}</p>
        <p><strong>影响级别:</strong> {bottleneck.impact.upper()}</p>
        <div class="suggestion">
            <strong>💡 优化建议:</strong> {bottleneck.suggestion}
        </div>
        <p class="metrics">指标: {json.dumps(bottleneck.metrics, ensure_ascii=False)}</p>
    </div>
"""

        html += """
</body>
</html>"""

        output_path.write_text(html, encoding='utf-8')


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self):
        self.benchmarks: dict[str, list[float]] = {}

    def benchmark(self, name: str, func: Callable, *args, runs: int = 100, **kwargs):
        """运行基准测试"""
        times = []

        for _ in range(runs):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # 转换为毫秒

        self.benchmarks[name] = times

        return {
            'name': name,
            'runs': runs,
            'min_ms': min(times),
            'max_ms': max(times),
            'avg_ms': sum(times) / len(times),
            'median_ms': sorted(times)[len(times) // 2]
        }

    def compare_benchmarks(self, name1: str, name2: str) -> dict[str, Any]:
        """比较两个基准测试"""
        if name1 not in self.benchmarks or name2 not in self.benchmarks:
            return {}

        avg1 = sum(self.benchmarks[name1]) / len(self.benchmarks[name1])
        avg2 = sum(self.benchmarks[name2]) / len(self.benchmarks[name2])

        faster = name1 if avg1 < avg2 else name2
        speedup = max(avg1, avg2) / min(avg1, avg2)

        return {
            'benchmark1': name1,
            'benchmark2': name2,
            'avg1_ms': avg1,
            'avg2_ms': avg2,
            'faster': faster,
            'speedup': f"{speedup:.2f}x"
        }

    def export_results(self, output_path: Path):
        """导出基准测试结果"""
        results = {}
        for name, times in self.benchmarks.items():
            results[name] = {
                'runs': len(times),
                'min_ms': min(times),
                'max_ms': max(times),
                'avg_ms': sum(times) / len(times),
                'median_ms': sorted(times)[len(times) // 2]
            }

        data = {
            'generated_at': datetime.now().isoformat(),
            'benchmarks': results
        }

        output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')


class CodeComplexityAnalyzer:
    """代码复杂度分析器"""

    @staticmethod
    def analyze_file(file_path: Path) -> dict[str, Any]:
        """分析文件的复杂度"""
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # 基本统计
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        blank_lines = len([line for line in lines if not line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])

        # 复杂度指标
        import_count = len([line for line in lines if line.strip().startswith('import') or line.strip().startswith('from')])
        class_count = len([line for line in lines if line.strip().startswith('class ')])
        function_count = len([line for line in lines if line.strip().startswith('def ')])
        max_nesting = CodeComplexityAnalyzer._calculate_max_nesting(lines)

        return {
            'file': str(file_path),
            'total_lines': total_lines,
            'code_lines': code_lines,
            'blank_lines': blank_lines,
            'comment_lines': comment_lines,
            'import_count': import_count,
            'class_count': class_count,
            'function_count': function_count,
            'max_nesting_level': max_nesting,
            'complexity_score': CodeComplexityAnalyzer._calculate_complexity_score(
                code_lines, class_count, function_count, max_nesting
            )
        }

    @staticmethod
    def _calculate_max_nesting(lines: list[str]) -> int:
        """计算最大嵌套层级"""
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent // 4)
        return max_indent

    @staticmethod
    def _calculate_complexity_score(code_lines: int, classes: int, functions: int, nesting: int) -> int:
        """计算复杂度分数 (0-100)"""
        # 简单的复杂度评分算法
        score = 0

        # 代码行数贡献
        if code_lines > 1000:
            score += 30
        elif code_lines > 500:
            score += 20
        elif code_lines > 200:
            score += 10

        # 类和函数数量
        if classes > 10:
            score += 20
        elif classes > 5:
            score += 10

        if functions > 50:
            score += 20
        elif functions > 20:
            score += 10

        # 嵌套层级
        if nesting > 5:
            score += 30
        elif nesting > 3:
            score += 20
        elif nesting > 2:
            score += 10

        return min(score, 100)

    @staticmethod
    def analyze_directory(directory: Path) -> list[dict[str, Any]]:
        """分析目录下所有Python文件的复杂度"""
        results = []

        for py_file in directory.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                try:
                    results.append(CodeComplexityAnalyzer.analyze_file(py_file))
                except Exception as e:
                    print(f"分析文件 {py_file} 时出错: {e}")

        return sorted(results, key=lambda x: x['complexity_score'], reverse=True)


# 使用示例
if __name__ == '__main__':
    # 1. 函数性能分析
    profiler = FunctionProfiler()

    @profiler.profile_function
    def test_function():
        """测试函数"""
        total = 0
        for i in range(1000000):
            total += i
        return total

    result = test_function()
    profiler.print_stats()

    # 2. 基准测试
    benchmark = BenchmarkRunner()

    def method_a():
        return sum(range(10000))

    def method_b():
        return sum(list(range(10000)))

    print("\n=== 基准测试 ===")
    result_a = benchmark.benchmark('method_a', method_a, runs=100)
    result_b = benchmark.benchmark('method_b', method_b, runs=100)

    print(f"Method A: {result_a['avg_ms']:.3f}ms")
    print(f"Method B: {result_b['avg_ms']:.3f}ms")

    comparison = benchmark.compare_benchmarks('method_a', 'method_b')
    print(f"更快的方法: {comparison['faster']} (快 {comparison['speedup']})")

    # 3. 代码复杂度分析
    print("\n=== 代码复杂度分析 ===")
    src_path = Path('src')
    if src_path.exists():
        complexity_results = CodeComplexityAnalyzer.analyze_directory(src_path)

        print("\n最复杂的5个文件:")
        for result in complexity_results[:5]:
            print(f"{result['file']}: 复杂度分数 {result['complexity_score']}/100")
            print(f"  代码行数: {result['code_lines']}, 类: {result['class_count']}, "
                  f"函数: {result['function_count']}, 最大嵌套: {result['max_nesting_level']}")

    # 4. 性能优化建议
    optimizer = PerformanceOptimizer()
    bottlenecks = optimizer.analyze_profile_results(profiler.get_results())

    if bottlenecks:
        print(f"\n=== 发现 {len(bottlenecks)} 个性能问题 ===")
        for bottleneck in bottlenecks:
            print(f"\n位置: {bottleneck.location}")
            print(f"问题: {bottleneck.description}")
            print(f"影响: {bottleneck.impact}")
            print(f"建议: {bottleneck.suggestion}")

        # 导出报告
        optimizer.generate_optimization_report(Path('optimization_report.html'))
        print("\n优化建议报告已导出到 optimization_report.html")


