#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba性能对比测试
对比原始版本和Numba加速版本的性能差异
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.curve_generator import CurveGenerator as OriginalGenerator
from src.core.curve_generator_numba import CurveGenerator as NumbaGenerator


def benchmark_titration_curve(num_points: int = 1000, iterations: int = 100):
    """测试滴定曲线生成性能"""
    params = {
        "acid_type": "strong",
        "acid_M": 0.1,
        "acid_V_ml": 25.0,
        "base_M": 0.1
    }

    print(f"\n=== 滴定曲线生成性能测试 ===")
    print(f"数据点数: {num_points}")
    print(f"迭代次数: {iterations}")
    print()

    # 测试原始版本
    print("[TEST] 测试原始版本...")
    original_gen = OriginalGenerator()
    start_time = time.time()
    for _ in range(iterations):
        x, y = original_gen.generate_titration_curve(
            acid_type="strong",
            acid_M=0.1,
            acid_V_ml=25.0,
            base_M=0.1,
            num_points=num_points
        )
    original_time = time.time() - start_time
    print(f"  原始版本耗时: {original_time:.3f}秒")

    # 测试Numba版本（第一次调用会编译，所以预热一次）
    print("\n[TEST] 测试Numba版本（包含预热）...")
    numba_gen = NumbaGenerator()
    # 预热
    x, y = numba_gen.generate_titration_curve(
        acid_type="strong",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=100
    )

    start_time = time.time()
    for _ in range(iterations):
        x, y = numba_gen.generate_titration_curve(
            acid_type="strong",
            acid_M=0.1,
            acid_V_ml=25.0,
            base_M=0.1,
            num_points=num_points
        )
    numba_time = time.time() - start_time
    print(f"  Numba版本耗时: {numba_time:.3f}秒")

    # 计算性能提升
    speedup = original_time / numba_time if numba_time > 0 else 0
    print(f"\n[RESULT] 性能提升: {speedup:.1f}x")
    print(f"         加速比例: {(speedup - 1) * 100:.1f}%")

    return speedup


def benchmark_temperature_curve(num_points: int = 1000, iterations: int = 100):
    """测试温度曲线生成性能"""
    params = {
        "mode": "heating",
        "initial_temp": 25.0,
        "power_W": 100,
        "mass_g": 100,
        "specific_heat": 4.18,
        "boiling_point": 100,
        "total_time_s": 600
    }

    print(f"\n=== 温度曲线生成性能测试 ===")
    print(f"数据点数: {num_points}")
    print(f"迭代次数: {iterations}")
    print()

    # 测试原始版本
    print("[TEST] 测试原始版本...")
    original_gen = OriginalGenerator()
    start_time = time.time()
    for _ in range(iterations):
        x, y = original_gen.generate_temperature_curve(
            mode="heating",
            initial_temp=25.0,
            params=params,
            num_points=num_points
        )
    original_time = time.time() - start_time
    print(f"  原始版本耗时: {original_time:.3f}秒")

    # 测试Numba版本
    print("\n[TEST] 测试Numba版本（包含预热）...")
    numba_gen = NumbaGenerator()
    # 预热
    x, y = numba_gen.generate_temperature_curve(
        mode="heating",
        initial_temp=25.0,
        params=params,
        num_points=100
    )

    start_time = time.time()
    for _ in range(iterations):
        x, y = numba_gen.generate_temperature_curve(
            mode="heating",
            initial_temp=25.0,
            params=params,
            num_points=num_points
        )
    numba_time = time.time() - start_time
    print(f"  Numba版本耗时: {numba_time:.3f}秒")

    # 计算性能提升
    speedup = original_time / numba_time if numba_time > 0 else 0
    print(f"\n[RESULT] 性能提升: {speedup:.1f}x")
    print(f"         加速比例: {(speedup - 1) * 100:.1f}%")

    return speedup


def test_correctness():
    """验证Numba版本和原始版本的结果一致性"""
    import numpy as np

    print(f"\n=== 正确性验证测试 ===")

    params = {
        "acid_type": "strong",
        "acid_M": 0.1,
        "acid_V_ml": 25.0,
        "base_M": 0.1
    }

    # 生成曲线
    original_gen = OriginalGenerator()
    numba_gen = NumbaGenerator()

    # 为了比较，不添加噪声
    np.random.seed(42)
    x1, y1 = original_gen.generate_titration_curve(
        acid_type="strong",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=100
    )

    np.random.seed(42)
    x2, y2 = numba_gen.generate_titration_curve(
        acid_type="strong",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=100
    )

    # 比较结果（因为有随机噪声，所以只检查趋势是否一致）
    max_diff = np.max(np.abs(y1 - y2))
    mean_diff = np.mean(np.abs(y1 - y2))

    print(f"  最大差异: {max_diff:.6f} pH")
    print(f"  平均差异: {mean_diff:.6f} pH")

    # 应该非常接近（差异主要来自随机噪声）
    assert max_diff < 0.5, f"结果差异过大: {max_diff}"
    print("[OK] 正确性验证通过")


def main():
    """运行所有性能测试"""
    print("=" * 70)
    print("Numba性能加速测试")
    print("=" * 70)

    # 验证正确性
    test_correctness()

    # 性能测试 - 不同数据规模
    print("\n" + "=" * 70)
    print("性能基准测试")
    print("=" * 70)

    # 小规模测试
    print("\n【小规模数据集】")
    speedup_small = benchmark_titration_curve(num_points=100, iterations=50)

    # 中规模测试
    print("\n" + "-" * 70)
    print("\n【中规模数据集】")
    speedup_medium = benchmark_titration_curve(num_points=1000, iterations=20)

    # 大规模测试
    print("\n" + "-" * 70)
    print("\n【大规模数据集】")
    speedup_large = benchmark_titration_curve(num_points=10000, iterations=5)

    # 温度曲线测试
    print("\n" + "-" * 70)
    speedup_temp = benchmark_temperature_curve(num_points=1000, iterations=20)

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"\n{'测试项目':<20} {'加速比':<15} {'结论'}")
    print("-" * 70)
    print(f"{'小规模(100点)':<20} {speedup_small:<15.1f}x {'良好' if speedup_small > 5 else '一般'}")
    print(f"{'中规模(1000点)':<20} {speedup_medium:<15.1f}x {'优秀' if speedup_medium > 20 else '良好'}")
    print(f"{'大规模(10000点)':<20} {speedup_large:<15.1f}x {'优秀' if speedup_large > 50 else '良好'}")
    print(f"{'温度曲线':<20} {speedup_temp:<15.1f}x {'优秀' if speedup_temp > 20 else '良好'}")

    avg_speedup = (speedup_small + speedup_medium + speedup_large + speedup_temp) / 4
    print(f"\n平均加速比: {avg_speedup:.1f}x")

    if avg_speedup >= 30:
        print("\n[EXCELLENT] 优秀！Numba加速效果显著，性能提升达到预期目标！")
    elif avg_speedup >= 15:
        print("\n[GOOD] 良好！Numba加速效果明显，性能显著提升！")
    else:
        print("\n[WARNING] 一般。Numba加速有效，但提升幅度可能需要进一步优化。")


if __name__ == '__main__':
    main()
