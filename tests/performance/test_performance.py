#!/usr/bin/env python
"""
性能测试脚本
测试VirtualChemLab的性能指标：启动时间、内存占用、响应速度等
"""

import sys
import time
from pathlib import Path

import psutil

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.curve_generator import CurveGenerator
from src.core.experiment_controller import ExperimentController
from src.core.template_engine import TemplateEngine
from src.storage.json_store import JSONStore


class PerformanceTest:
    """性能测试类"""

    def __init__(self):
        self.results: dict[str, any] = {}
        self.process = psutil.Process()

    def test_startup_time(self) -> float:
        """测试启动时间"""
        print("测试启动时间...")
        start = time.time()

        # 模拟应用启动流程
        template_engine = TemplateEngine(Path("assets/templates"))
        _ = template_engine.list_available_experiments()

        elapsed = time.time() - start
        self.results["startup_time"] = elapsed
        print(f"  启动时间: {elapsed:.3f}秒")
        return elapsed

    def test_memory_usage(self) -> float:
        """测试内存占用"""
        print("\n测试内存占用...")

        # 加载所有模板
        template_engine = TemplateEngine(Path("assets/templates"))
        experiments = template_engine.list_available_experiments()

        # 加载所有实验
        for exp in experiments:
            _ = template_engine.load_experiment_by_id(exp["id"])

        # 获取内存使用
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        self.results["memory_usage_mb"] = memory_mb
        print(f"  内存占用: {memory_mb:.2f} MB")
        return memory_mb

    def test_template_loading(self) -> dict[str, float]:
        """测试模板加载速度"""
        print("\n测试模板加载速度...")
        template_engine = TemplateEngine(Path("assets/templates"))
        experiments = template_engine.list_available_experiments()

        loading_times = {}
        for exp in experiments:
            start = time.time()
            _ = template_engine.load_experiment_by_id(exp["id"])
            elapsed = time.time() - start
            loading_times[exp["id"]] = elapsed
            print(f"  {exp['id']}: {elapsed * 1000:.2f}ms")

        avg_time = sum(loading_times.values()) / len(loading_times)
        self.results["avg_template_load_ms"] = avg_time * 1000
        print(f"  平均加载时间: {avg_time * 1000:.2f}ms")
        return loading_times

    def test_curve_generation(self) -> dict[str, float]:
        """测试曲线生成速度"""
        print("\n测试曲线生成速度...")
        generator = CurveGenerator()

        tests = {
            "强酸强碱滴定": lambda: generator.generate_titration_curve(
                "strong_strong", acid_M=0.1, acid_V_ml=25, base_M=0.1
            ),
            "弱酸强碱滴定": lambda: generator.generate_titration_curve(
                "weak_strong", acid_M=0.1, acid_V_ml=25, base_M=0.1
            ),
            "温度曲线": lambda: generator.generate_temperature_curve(
                "heating", 25, {"target_temp": 100, "heating_rate": 5.0}
            ),
        }

        curve_times = {}
        for name, func in tests.items():
            start = time.time()
            _ = func()
            elapsed = time.time() - start
            curve_times[name] = elapsed
            print(f"  {name}: {elapsed * 1000:.2f}ms")

        avg_time = sum(curve_times.values()) / len(curve_times)
        self.results["avg_curve_gen_ms"] = avg_time * 1000
        print(f"  平均生成时间: {avg_time * 1000:.2f}ms")
        return curve_times

    def test_controller_performance(self) -> float:
        """测试实验控制器性能"""
        print("\n测试实验控制器性能...")
        template_engine = TemplateEngine(Path("assets/templates"))
        template = template_engine.load_experiment_by_id("titration_naoh_hcl")

        start = time.time()
        ExperimentController(template, user_id="perf_test")
        elapsed = time.time() - start

        self.results["controller_init_ms"] = elapsed * 1000
        print(f"  控制器初始化: {elapsed * 1000:.2f}ms")
        return elapsed

    def test_storage_performance(self) -> dict[str, float]:
        """测试存储系统性能"""
        print("\n测试存储系统性能...")
        import shutil
        import tempfile

        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())

        try:
            store = JSONStore(temp_dir)
            template_engine = TemplateEngine(Path("assets/templates"))
            template = template_engine.load_experiment_by_id("titration_naoh_hcl")

            from datetime import datetime

            from src.models.user_record import ExperimentScore, UserRecord

            # 测试保存
            start = time.time()
            for i in range(10):
                record = UserRecord(
                    record_id=f"perf_test_{i}",
                    user_id="test_user",
                    experiment_id=template.id,
                    experiment_title=template.title,
                    started_at=datetime.now(),
                    score=ExperimentScore(correctness=80, procedure=90, safety=85),
                )
                store.save_record(record)
            save_time = (time.time() - start) / 10
            print(f"  平均保存时间: {save_time * 1000:.2f}ms")

            # 测试查询
            start = time.time()
            _ = store.list_records()
            query_time = time.time() - start
            print(f"  查询所有记录: {query_time * 1000:.2f}ms")

            # 测试搜索
            start = time.time()
            _ = store.list_records(experiment_id=template.id)
            search_time = time.time() - start
            print(f"  搜索记录: {search_time * 1000:.2f}ms")

            self.results["storage_save_ms"] = save_time * 1000
            self.results["storage_query_ms"] = query_time * 1000
            self.results["storage_search_ms"] = search_time * 1000

            return {"save": save_time, "query": query_time, "search": search_time}
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir)

    def run_all_tests(self):
        """运行所有性能测试"""
        print("=" * 60)
        print("VirtualChemLab 性能测试")
        print("=" * 60)

        self.test_startup_time()
        self.test_memory_usage()
        self.test_template_loading()
        self.test_curve_generation()
        self.test_controller_performance()
        self.test_storage_performance()

        print("\n" + "=" * 60)
        print("性能测试总结")
        print("=" * 60)

        # 检查是否满足目标
        goals = {
            "startup_time": ("启动时间", 3.0, "s", "<="),
            "memory_usage_mb": ("内存占用", 400, "MB", "<="),
            "avg_template_load_ms": ("模板加载", 100, "ms", "<="),
            "avg_curve_gen_ms": ("曲线生成", 50, "ms", "<="),
        }

        print("\n目标达成情况:")
        all_passed = True
        for key, (name, target, unit, op) in goals.items():
            if key in self.results:
                value = self.results[key]
                passed = value <= target if op == "<=" else value >= target

                status = "✓ 通过" if passed else "✗ 未达标"
                print(f"  {name}: {value:.2f}{unit} (目标{op}{target}{unit}) {status}")

                if not passed:
                    all_passed = False

        print(f"\n总体评价: {'所有指标达标 ✓' if all_passed else '部分指标需优化 ⚠'}")

        return self.results


def main():
    """主函数"""
    tester = PerformanceTest()
    results = tester.run_all_tests()

    # 保存结果到文件
    import json

    output_file = Path("tests/performance/results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存至: {output_file}")


if __name__ == "__main__":
    main()
