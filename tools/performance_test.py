#!/usr/bin/env python3
"""
性能测试工具
测试和验证各项性能优化的效果
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.performance import (
    get_api_cache,
    get_experiment_load_optimizer,
    get_integrated_optimizer,
    get_particle_system_optimizer,
    get_physics_engine_optimizer,
    get_query_optimizer,
    get_rendering_optimizer,
    get_resource_loader,
    init_performance_optimizations,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(name: str, value: str | float, unit: str = ""):
    """打印测试结果"""
    if isinstance(value, float):
        print(f"  ✓ {name}: {value:.2f}{unit}")
    else:
        print(f"  ✓ {name}: {value}{unit}")


def test_resource_loading():
    """测试资源加载性能"""
    print_header("资源加载性能测试")

    loader = get_resource_loader()

    # 测试图片加载
    test_images = [f"test_image_{i}.png" for i in range(10)]

    start_time = time.time()
    for img_path in test_images:
        loader.load_image(img_path, (200, 200))
    load_time = (time.time() - start_time) * 1000

    print_result("10张图片加载时间", load_time, "ms")
    print_result("平均每张", load_time / 10, "ms")
    print_result("缓存大小", len(loader.resource_cache))

    # 测试缓存命中
    start_time = time.time()
    for img_path in test_images:
        loader.load_image(img_path, (200, 200))
    cached_time = (time.time() - start_time) * 1000

    print_result("缓存命中加载时间", cached_time, "ms")
    print_result("性能提升", (load_time / cached_time if cached_time > 0 else 0), "x")


def test_query_optimization():
    """测试查询优化"""
    print_header("数据库查询优化测试")

    optimizer = get_query_optimizer()

    # 测试查询
    test_queries = [
        ("SELECT * FROM experiments WHERE id = ?", (1,)),
        ("SELECT * FROM users WHERE email = ?", ("test@example.com",)),
        ("SELECT * FROM records WHERE experiment_id = ?", (1,)),
    ]

    # 首次查询
    total_time = 0
    for query, params in test_queries:
        _, metrics = optimizer.execute_query(query, params)
        total_time += metrics.execution_time

    print_result("首次查询总时间", total_time * 1000, "ms")

    # 缓存命中查询
    cached_time = 0
    for query, params in test_queries:
        _, metrics = optimizer.execute_query(query, params)
        cached_time += metrics.execution_time

    print_result("缓存命中总时间", cached_time * 1000, "ms")
    print_result("性能提升", (total_time / cached_time if cached_time > 0 else 0), "x")

    # 缓存统计
    stats = optimizer.get_cache_stats()
    print_result("缓存命中率", stats["cache_hit_rate"] * 100, "%")
    print_result("平均执行时间", stats["avg_execution_time"] * 1000, "ms")


def test_api_caching():
    """测试API缓存"""
    print_header("API缓存测试")

    cache = get_api_cache()

    # 模拟API响应
    test_data = {"data": [i for i in range(1000)]}

    # 测试缓存设置和获取
    start_time = time.time()
    for i in range(100):
        cache.set(f"api_key_{i}", test_data)
    set_time = (time.time() - start_time) * 1000

    print_result("100次缓存写入", set_time, "ms")

    start_time = time.time()
    for i in range(100):
        cache.get(f"api_key_{i}")
    get_time = (time.time() - start_time) * 1000

    print_result("100次缓存读取", get_time, "ms")

    # 统计信息
    stats = cache.get_stats()
    print_result("缓存命中率", stats["hit_rate"] * 100, "%")
    print_result("缓存大小", stats["cache_size"])


def test_experiment_loading():
    """测试实验加载优化"""
    print_header("实验加载优化测试")

    optimizer = get_experiment_load_optimizer()

    test_experiments = [f"exp_{i:03d}" for i in range(20)]

    # 首次加载
    start_time = time.time()
    for exp_id in test_experiments:
        optimizer.load_experiment(exp_id)
    first_load_time = (time.time() - start_time) * 1000

    print_result("20个实验首次加载", first_load_time, "ms")
    print_result("平均每个", first_load_time / 20, "ms")

    # 缓存命中
    start_time = time.time()
    for exp_id in test_experiments[:10]:  # 只加载缓存中的
        optimizer.load_experiment(exp_id)
    cached_load_time = (time.time() - start_time) * 1000

    print_result("10个实验缓存加载", cached_load_time, "ms")
    print_result("平均每个", cached_load_time / 10, "ms")

    # 统计
    stats = optimizer.get_load_stats()
    print_result("缓存命中率", stats["cache_hit_rate"] * 100, "%")
    print_result("缓存的实验数", stats["cached_experiments"])


def test_particle_system():
    """测试粒子系统优化"""
    print_header("粒子系统优化测试")

    optimizer = get_particle_system_optimizer()

    # 测试粒子获取和释放
    particles = []

    start_time = time.time()
    for _ in range(1000):
        particle = optimizer.acquire_particle()
        if particle:
            particles.append(particle)
    acquire_time = (time.time() - start_time) * 1000

    print_result("1000个粒子获取", acquire_time, "ms")
    print_result("平均每个", acquire_time / 1000, "ms")

    start_time = time.time()
    for particle in particles:
        optimizer.release_particle(particle)
    release_time = (time.time() - start_time) * 1000

    print_result("1000个粒子释放", release_time, "ms")

    # 测试批量更新
    particles = [optimizer.acquire_particle() for _ in range(500)]

    start_time = time.time()
    optimizer.batch_update_particles(0.016)  # 16ms (60 FPS)
    update_time = (time.time() - start_time) * 1000

    print_result("500个粒子批量更新", update_time, "ms")

    # 统计
    stats = optimizer.get_stats()
    print_result("活跃粒子", stats["active_particles"])
    print_result("对象池大小", stats["pooled_particles"])
    print_result("池利用率", stats["pool_utilization"] * 100, "%")


def test_physics_engine():
    """测试物理引擎优化"""
    print_header("物理引擎优化测试")

    optimizer = get_physics_engine_optimizer()

    # 创建测试对象
    class MockObject:
        def __init__(self, x, y):
            self.position = (x, y)

    objects = [MockObject(i * 10, i * 10) for i in range(100)]

    # 测试空间网格更新
    start_time = time.time()
    optimizer.update_spatial_grid(objects)
    grid_time = (time.time() - start_time) * 1000

    print_result("100个对象空间网格更新", grid_time, "ms")

    # 测试邻近对象查询
    start_time = time.time()
    for obj in objects[:10]:
        nearby = optimizer.get_nearby_objects(obj, radius=1)
    query_time = (time.time() - start_time) * 1000

    print_result("10次邻近查询", query_time, "ms")

    # 统计
    stats = optimizer.get_stats()
    print_result("网格单元数", stats["grid_cells"])
    print_result("平均每单元对象数", stats["avg_objects_per_cell"])


def test_rendering_optimization():
    """测试渲染优化"""
    print_header("渲染优化测试")

    optimizer = get_rendering_optimizer()

    # 创建测试对象
    class MockRenderable:
        def __init__(self, x, y, w, h):
            self.bounds = (x, y, w, h)

    objects = [MockRenderable(i * 50, i * 50, 100, 100) for i in range(100)]

    # 测试视锥剔除
    viewport = (0, 0, 800, 600)

    start_time = time.time()
    optimizer.update_visible_objects(objects, viewport)
    culling_time = (time.time() - start_time) * 1000

    print_result("100个对象视锥剔除", culling_time, "ms")

    # 统计
    stats = optimizer.get_render_stats()
    print_result("可见对象", stats["visible_objects"])
    print_result("目标FPS", stats["target_fps"])


def test_integrated_performance():
    """测试集成性能"""
    print_header("集成性能测试")

    # 加载性能配置
    config = {
        "enabled": True,
        "monitor_interval": 1000,
        "frontend": {
            "lazy_loading": {"enabled": True},
            "preload_critical": True,
            "critical_resources": [],
        },
        "backend": {
            "query_cache": {"enabled": True, "ttl": 300},
            "api_cache": {"enabled": True, "ttl": 300},
        },
        "high_freq": {
            "experiment_loading": {"enabled": True, "cache_size": 10},
            "particle_system": {"enabled": True, "max_particles": 2000},
            "physics_engine": {"enabled": True},
            "rendering": {"enabled": True, "target_fps": 60},
        },
    }

    optimizer = get_integrated_optimizer(config)

    # 应用优化
    start_time = time.time()
    optimizer.apply_all_optimizations()
    apply_time = (time.time() - start_time) * 1000

    print_result("优化应用时间", apply_time, "ms")

    # 模拟一些操作以生成指标
    time.sleep(0.5)

    # 获取性能摘要
    summary = optimizer.get_performance_summary()

    if summary["status"] == "ok":
        print_result("性能等级", summary["level_text"])
        print_result("平均分数", summary["avg_score"], "/100")
        print_result("最新分数", summary["latest_score"], "/100")

        print("\n  优化建议:")
        for i, recommendation in enumerate(summary["recommendations"], 1):
            print(f"    {i}. {recommendation}")


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "VirtualChemLab 性能优化测试" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        # 初始化性能优化
        init_performance_optimizations()

        # 运行各项测试
        test_resource_loading()
        test_query_optimization()
        test_api_caching()
        test_experiment_loading()
        test_particle_system()
        test_physics_engine()
        test_rendering_optimization()
        test_integrated_performance()

        # 总结
        print_header("测试完成")
        print("  ✓ 所有性能测试已完成")
        print("  ✓ 建议查看详细报告以了解优化建议")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        print(f"\n  ✗ 测试失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())

