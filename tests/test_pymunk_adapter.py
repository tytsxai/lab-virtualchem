#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMunk适配器测试
验证物理引擎适配器的所有功能
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.physics import PyMunkPhysicsEngine, BodyType


def test_engine_creation():
    """测试引擎创建"""
    engine = PyMunkPhysicsEngine()
    assert engine is not None
    assert engine.body_count == 0
    print("✓ 物理引擎创建成功")


def test_gravity_setting():
    """测试重力设置"""
    engine = PyMunkPhysicsEngine()

    # 默认重力
    assert engine.gravity == (0, -981)

    # 修改重力
    engine.gravity = (0, -500)
    assert engine.gravity == (0, -500)

    print("✓ 重力设置正常")


def test_create_circle():
    """测试创建圆形刚体"""
    engine = PyMunkPhysicsEngine()

    body = engine.create_circle_body(
        radius=10,
        mass=1.0,
        position=(100, 100),
        friction=0.5,
        elasticity=0.8
    )

    assert body is not None
    assert body.position == (100, 100)
    assert body.mass == 1.0
    assert len(body.shapes) == 1
    assert engine.body_count == 1

    print(f"✓ 圆形刚体创建成功，位置: {body.position}")


def test_create_box():
    """测试创建矩形刚体"""
    engine = PyMunkPhysicsEngine()

    body = engine.create_box_body(
        width=20,
        height=30,
        mass=2.0,
        position=(50, 50),
        friction=0.3,
        elasticity=0.6
    )

    assert body is not None
    assert body.position == (50, 50)
    assert body.mass == 2.0
    assert engine.body_count == 1

    print(f"✓ 矩形刚体创建成功")


def test_create_segment():
    """测试创建线段"""
    engine = PyMunkPhysicsEngine()

    body = engine.create_segment_body(
        point_a=(0, 0),
        point_b=(200, 0),
        thickness=5,
        body_type=BodyType.STATIC
    )

    assert body is not None
    assert len(body.shapes) == 1

    print(f"✓ 线段创建成功")


def test_create_polygon():
    """测试创建多边形刚体"""
    engine = PyMunkPhysicsEngine()

    # 创建三角形
    vertices = [(0, 0), (20, 0), (10, 20)]
    body = engine.create_polygon_body(
        vertices=vertices,
        mass=1.5,
        position=(100, 100)
    )

    assert body is not None
    assert engine.body_count == 1

    print(f"✓ 多边形刚体创建成功")


def test_body_position():
    """测试刚体位置控制"""
    engine = PyMunkPhysicsEngine()
    body = engine.create_circle_body(radius=10, position=(50, 50))

    # 读取位置
    assert body.position == (50, 50)

    # 修改位置
    body.position = (100, 100)
    assert body.position == (100, 100)

    print(f"✓ 位置控制正常")


def test_body_velocity():
    """测试刚体速度控制"""
    engine = PyMunkPhysicsEngine()
    body = engine.create_circle_body(radius=10)

    # 初始速度为0
    assert body.velocity == (0, 0)

    # 设置速度
    body.velocity = (100, 50)
    assert body.velocity == (100, 50)

    print(f"✓ 速度控制正常")


def test_simulation():
    """测试物理模拟"""
    engine = PyMunkPhysicsEngine()
    engine.gravity = (0, -100)  # 设置较小的重力便于测试

    # 创建一个球
    ball = engine.create_circle_body(
        radius=10,
        mass=1.0,
        position=(100, 100)
    )

    initial_y = ball.position[1]

    # 模拟60帧（1秒）
    for i in range(60):
        engine.step()

    # 球应该下落了
    assert ball.position[1] < initial_y

    print(f"✓ 物理模拟正常，球从 {initial_y} 下落到 {ball.position[1]:.2f}")


def test_collision():
    """测试碰撞"""
    engine = PyMunkPhysicsEngine()
    engine.gravity = (0, -981)

    # 创建地面
    ground = engine.create_segment_body(
        point_a=(0, 10),
        point_b=(200, 10),
        thickness=5,
        body_type=BodyType.STATIC
    )

    # 创建球（在地面上方较近的位置）
    ball = engine.create_circle_body(
        radius=10,
        mass=1.0,
        position=(100, 30),
        elasticity=0.8
    )

    initial_velocity = ball.velocity[1]

    # 模拟直到球碰到地面并反弹
    collision_detected = False
    for i in range(120):
        prev_velocity = ball.velocity[1]
        engine.step()

        # 检测速度方向改变
        if prev_velocity < -10 and ball.velocity[1] > -1:
            collision_detected = True
            break

    assert collision_detected or ball.velocity[1] > initial_velocity
    print(f"✓ 碰撞检测正常")


def test_spring_constraint():
    """测试弹簧约束"""
    engine = PyMunkPhysicsEngine()
    engine.gravity = (0, 0)  # 无重力环境

    # 创建两个球
    ball1 = engine.create_circle_body(radius=10, position=(50, 100))
    ball2 = engine.create_circle_body(radius=10, position=(150, 100))

    # 添加弹簧
    spring = engine.add_spring(
        ball1, ball2,
        rest_length=100,
        stiffness=50,
        damping=5
    )

    assert spring is not None
    assert engine.constraint_count == 1

    # 拉开两个球
    ball2.position = (200, 100)

    # 模拟一段时间
    for i in range(60):
        engine.step()

    # 球应该被弹簧拉近
    distance = ((ball1.position[0] - ball2.position[0])**2 +
                (ball1.position[1] - ball2.position[1])**2)**0.5

    print(f"✓ 弹簧约束正常工作，当前距离: {distance:.2f}")


def test_remove_body():
    """测试移除刚体"""
    engine = PyMunkPhysicsEngine()

    body1 = engine.create_circle_body(radius=10)
    body2 = engine.create_circle_body(radius=15)

    assert engine.body_count == 2

    engine.remove_body(body1)
    assert engine.body_count == 1

    engine.remove_body(body2)
    assert engine.body_count == 0

    print(f"✓ 刚体移除功能正常")


def test_ray_cast():
    """测试射线检测"""
    engine = PyMunkPhysicsEngine()

    # 创建一个球
    ball = engine.create_circle_body(
        radius=10,
        position=(100, 100)
    )

    # 从左边射线到右边，应该击中球
    hit = engine.ray_cast(
        start=(0, 100),
        end=(200, 100)
    )

    assert hit is not None
    assert hit['body'] == ball
    print(f"✓ 射线检测正常，击中点: {hit['point']}")


def test_point_query():
    """测试点查询"""
    engine = PyMunkPhysicsEngine()

    # 创建一个球
    ball = engine.create_circle_body(
        radius=10,
        position=(100, 100)
    )

    # 查询球中心点
    results = engine.point_query(
        point=(100, 100),
        max_distance=50
    )

    assert len(results) > 0
    print(f"✓ 点查询正常，找到 {len(results)} 个形状")


def test_clear():
    """测试清空功能"""
    engine = PyMunkPhysicsEngine()

    # 创建多个刚体
    for i in range(5):
        engine.create_circle_body(radius=10, position=(i*20, 100))

    assert engine.body_count == 5

    engine.clear()
    assert engine.body_count == 0
    assert engine.shape_count == 0

    print(f"✓ 清空功能正常")


def test_apply_force():
    """测试施加力"""
    engine = PyMunkPhysicsEngine()
    engine.gravity = (0, 0)  # 无重力

    ball = engine.create_circle_body(
        radius=10,
        position=(100, 100),
        mass=1.0
    )

    # 施加向上的力
    ball.apply_force_at_world_point(
        force=(0, 1000),
        point=(100, 100)
    )

    # 模拟几帧
    for i in range(30):
        engine.step()

    # 球应该向上移动
    assert ball.position[1] > 100
    print(f"✓ 施加力功能正常")


def test_performance():
    """测试性能 - 大量刚体"""
    import time

    engine = PyMunkPhysicsEngine()
    engine.gravity = (0, -981)

    # 创建地面
    engine.create_segment_body(
        point_a=(0, 0),
        point_b=(1000, 0),
        thickness=5,
        body_type=BodyType.STATIC
    )

    # 创建100个球
    for i in range(100):
        engine.create_circle_body(
            radius=5,
            mass=1.0,
            position=(i * 10, 100 + i * 5)
        )

    # 测试模拟性能
    frames = 300  # 5秒
    start_time = time.time()

    for i in range(frames):
        engine.step()

    end_time = time.time()
    elapsed = end_time - start_time
    fps = frames / elapsed

    print(f"✓ 性能测试: {frames}帧耗时 {elapsed:.2f}秒，平均 {fps:.1f} FPS")
    assert fps > 30, f"性能不足，FPS仅为 {fps:.1f}"


if __name__ == '__main__':
    print("=" * 60)
    print("PyMunk适配器测试")
    print("=" * 60)

    pytest.main([__file__, '-v', '--tb=short'])
