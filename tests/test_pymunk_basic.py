#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMunk基础功能测试
测试PyMunk物理引擎的基本功能是否正常工作
"""

import pytest
import pymunk
import math


def test_pymunk_import():
    """测试PyMunk能否正常导入"""
    assert pymunk is not None
    print(f"✓ PyMunk版本: {pymunk.version}")


def test_create_space():
    """测试创建物理空间"""
    space = pymunk.Space()
    assert space is not None
    
    # 设置重力
    space.gravity = (0, -981)  # 重力加速度 981 cm/s²
    assert space.gravity == pymunk.Vec2d(0, -981)
    print(f"✓ 物理空间创建成功，重力: {space.gravity}")


def test_create_static_body():
    """测试创建静态刚体（如地面）"""
    space = pymunk.Space()
    
    # 创建静态地面
    static_body = space.static_body
    static_shape = pymunk.Segment(static_body, (0, 0), (100, 0), 5)
    static_shape.friction = 1.0
    space.add(static_shape)
    
    assert static_shape in space.shapes
    print(f"✓ 静态刚体创建成功")


def test_create_dynamic_body():
    """测试创建动态刚体（如球体）"""
    space = pymunk.Space()
    space.gravity = (0, -981)
    
    # 创建球体
    mass = 1.0
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    
    body = pymunk.Body(mass, moment)
    body.position = (50, 100)
    
    shape = pymunk.Circle(body, radius)
    shape.friction = 0.5
    shape.elasticity = 0.8
    
    space.add(body, shape)
    
    assert body in space.bodies
    assert shape in space.shapes
    print(f"✓ 动态刚体创建成功，位置: {body.position}")


def test_simulation_step():
    """测试物理模拟步进"""
    space = pymunk.Space()
    space.gravity = (0, -981)
    
    # 创建地面
    static_body = space.static_body
    ground = pymunk.Segment(static_body, (0, 0), (200, 0), 5)
    ground.friction = 1.0
    space.add(ground)
    
    # 创建球体
    mass = 1.0
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    ball = pymunk.Body(mass, moment)
    ball.position = (100, 100)
    
    shape = pymunk.Circle(ball, radius)
    shape.friction = 0.5
    shape.elasticity = 0.8
    space.add(ball, shape)
    
    # 记录初始位置
    initial_y = ball.position.y
    
    # 模拟60帧（1秒）
    dt = 1.0 / 60.0
    for i in range(60):
        space.step(dt)
    
    # 球应该已经下落
    assert ball.position.y < initial_y
    print(f"✓ 物理模拟正常，球从 {initial_y} 下落到 {ball.position.y:.2f}")


def test_collision_detection():
    """测试碰撞检测"""
    space = pymunk.Space()
    space.gravity = (0, -981)
    
    # 创建地面
    static_body = space.static_body
    ground = pymunk.Segment(static_body, (0, 10), (200, 10), 5)
    ground.friction = 1.0
    space.add(ground)
    
    # 创建球体（位置较低，会很快碰到地面）
    mass = 1.0
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    ball = pymunk.Body(mass, moment)
    ball.position = (100, 30)  # 距离地面较近
    
    shape = pymunk.Circle(ball, radius)
    shape.friction = 0.5
    shape.elasticity = 0.8
    space.add(ball, shape)
    
    # 记录初始速度
    initial_velocity = ball.velocity.y
    
    # 模拟直到球碰到地面并反弹
    dt = 1.0 / 60.0
    collision_detected = False
    for i in range(120):  # 最多2秒
        prev_velocity = ball.velocity.y
        space.step(dt)
        
        # 检测速度方向改变（表示发生了碰撞）
        if prev_velocity < -10 and ball.velocity.y > -1:
            collision_detected = True
            break
    
    # 应该已经检测到碰撞（球反弹）
    assert collision_detected or ball.velocity.y > initial_velocity
    print(f"✓ 碰撞检测正常，球已碰到地面")


def test_constraint_system():
    """测试约束系统（关节）"""
    space = pymunk.Space()
    
    # 创建两个刚体
    mass = 1.0
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    
    body1 = pymunk.Body(mass, moment)
    body1.position = (50, 100)
    shape1 = pymunk.Circle(body1, radius)
    space.add(body1, shape1)
    
    body2 = pymunk.Body(mass, moment)
    body2.position = (100, 100)
    shape2 = pymunk.Circle(body2, radius)
    space.add(body2, shape2)
    
    # 创建距离约束（类似弹簧）
    joint = pymunk.DampedSpring(
        body1, body2,
        (0, 0), (0, 0),  # 锚点
        50,  # 静止长度
        10,  # 刚度
        0.5  # 阻尼
    )
    space.add(joint)
    
    assert joint in space.constraints
    print(f"✓ 约束系统正常工作")


def test_performance():
    """测试性能 - 模拟大量刚体"""
    import time
    
    space = pymunk.Space()
    space.gravity = (0, -981)
    
    # 创建地面
    static_body = space.static_body
    ground = pymunk.Segment(static_body, (0, 0), (1000, 0), 5)
    ground.friction = 1.0
    space.add(ground)
    
    # 创建100个球体
    for i in range(100):
        mass = 1.0
        radius = 5
        moment = pymunk.moment_for_circle(mass, 0, radius)
        
        body = pymunk.Body(mass, moment)
        body.position = (i * 10, 100 + i * 5)
        
        shape = pymunk.Circle(body, radius)
        shape.friction = 0.5
        shape.elasticity = 0.8
        
        space.add(body, shape)
    
    # 测试模拟性能
    dt = 1.0 / 60.0
    frames = 300  # 5秒
    
    start_time = time.time()
    for i in range(frames):
        space.step(dt)
    end_time = time.time()
    
    elapsed = end_time - start_time
    fps = frames / elapsed
    
    print(f"✓ 性能测试: {frames}帧耗时 {elapsed:.2f}秒，平均 {fps:.1f} FPS")
    assert fps > 30, f"性能不足，FPS仅为 {fps:.1f}"


def test_query_system():
    """测试查询系统（射线检测等）"""
    space = pymunk.Space()
    
    # 创建一个球体
    mass = 1.0
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    
    body = pymunk.Body(mass, moment)
    body.position = (100, 100)
    
    shape = pymunk.Circle(body, radius)
    space.add(body, shape)
    
    # 射线检测
    start = pymunk.Vec2d(0, 100)
    end = pymunk.Vec2d(200, 100)
    
    hit_info = space.segment_query_first(start, end, 0, pymunk.ShapeFilter())
    
    assert hit_info is not None
    print(f"✓ 射线检测成功，击中点: {hit_info.point}")


def test_shape_types():
    """测试不同形状类型"""
    space = pymunk.Space()
    
    # 圆形
    circle_body = pymunk.Body(1, pymunk.moment_for_circle(1, 0, 10))
    circle_shape = pymunk.Circle(circle_body, 10)
    space.add(circle_body, circle_shape)
    
    # 矩形
    box_body = pymunk.Body(1, pymunk.moment_for_box(1, (20, 20)))
    box_shape = pymunk.Poly.create_box(box_body, (20, 20))
    space.add(box_body, box_shape)
    
    # 线段
    segment_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    segment_shape = pymunk.Segment(segment_body, (0, 0), (50, 0), 2)
    space.add(segment_body, segment_shape)  # 需要同时添加body和shape
    
    # 多边形
    vertices = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    poly_body = pymunk.Body(1, pymunk.moment_for_poly(1, vertices))
    poly_shape = pymunk.Poly(poly_body, vertices)
    space.add(poly_body, poly_shape)
    
    assert len(space.shapes) == 4
    print(f"✓ 支持多种形状类型: 圆形、矩形、线段、多边形")


if __name__ == '__main__':
    print("=" * 60)
    print("PyMunk 物理引擎基础测试")
    print("=" * 60)
    
    # 运行所有测试
    pytest.main([__file__, '-v', '--tb=short'])

