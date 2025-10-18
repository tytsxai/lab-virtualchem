#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMunk物理引擎适配器
为VirtualChemLab提供统一的物理引擎接口，底层使用PyMunk实现
"""

from typing import Optional, Tuple, List, Callable, Any
from enum import Enum
import pymunk
from pymunk import Vec2d


class BodyType(Enum):
    """刚体类型"""
    DYNAMIC = "dynamic"  # 动态刚体（受力影响）
    STATIC = "static"    # 静态刚体（不受力影响）
    KINEMATIC = "kinematic"  # 运动学刚体（速度控制）


class ShapeType(Enum):
    """形状类型"""
    CIRCLE = "circle"
    BOX = "box"
    SEGMENT = "segment"
    POLYGON = "polygon"


class PhysicsShape:
    """物理形状包装类"""

    def __init__(self, pymunk_shape: pymunk.Shape):
        self._shape = pymunk_shape
        self.shape_type = self._determine_shape_type()

    def _determine_shape_type(self) -> ShapeType:
        """确定形状类型"""
        if isinstance(self._shape, pymunk.Circle):
            return ShapeType.CIRCLE
        elif isinstance(self._shape, pymunk.Poly):
            # 检查是否是矩形
            if len(self._shape.get_vertices()) == 4:
                return ShapeType.BOX
            return ShapeType.POLYGON
        elif isinstance(self._shape, pymunk.Segment):
            return ShapeType.SEGMENT
        return ShapeType.POLYGON

    @property
    def friction(self) -> float:
        """摩擦系数"""
        return self._shape.friction

    @friction.setter
    def friction(self, value: float):
        self._shape.friction = value

    @property
    def elasticity(self) -> float:
        """弹性系数"""
        return self._shape.elasticity

    @elasticity.setter
    def elasticity(self, value: float):
        self._shape.elasticity = value

    @property
    def density(self) -> float:
        """密度"""
        return self._shape.density

    @density.setter
    def density(self, value: float):
        self._shape.density = value

    @property
    def mass(self) -> float:
        """质量"""
        return self._shape.mass

    @property
    def sensor(self) -> bool:
        """是否为传感器（不产生碰撞响应）"""
        return self._shape.sensor

    @sensor.setter
    def sensor(self, value: bool):
        self._shape.sensor = value


class PhysicsBody:
    """物理刚体包装类"""

    def __init__(self, pymunk_body: pymunk.Body):
        self._body = pymunk_body
        self.shapes: List[PhysicsShape] = []

    @property
    def position(self) -> Tuple[float, float]:
        """位置"""
        return (self._body.position.x, self._body.position.y)

    @position.setter
    def position(self, value: Tuple[float, float]):
        self._body.position = Vec2d(value[0], value[1])

    @property
    def velocity(self) -> Tuple[float, float]:
        """速度"""
        return (self._body.velocity.x, self._body.velocity.y)

    @velocity.setter
    def velocity(self, value: Tuple[float, float]):
        self._body.velocity = Vec2d(value[0], value[1])

    @property
    def angle(self) -> float:
        """角度（弧度）"""
        return self._body.angle

    @angle.setter
    def angle(self, value: float):
        self._body.angle = value

    @property
    def angular_velocity(self) -> float:
        """角速度"""
        return self._body.angular_velocity

    @angular_velocity.setter
    def angular_velocity(self, value: float):
        self._body.angular_velocity = value

    @property
    def mass(self) -> float:
        """质量"""
        return self._body.mass

    @mass.setter
    def mass(self, value: float):
        self._body.mass = value

    @property
    def force(self) -> Tuple[float, float]:
        """作用力"""
        return (self._body.force.x, self._body.force.y)

    @force.setter
    def force(self, value: Tuple[float, float]):
        self._body.force = Vec2d(value[0], value[1])

    def apply_force_at_world_point(self, force: Tuple[float, float], point: Tuple[float, float]):
        """在世界坐标的某点施加力"""
        self._body.apply_force_at_world_point(Vec2d(force[0], force[1]), Vec2d(point[0], point[1]))

    def apply_force_at_local_point(self, force: Tuple[float, float], point: Tuple[float, float]):
        """在本地坐标的某点施加力"""
        self._body.apply_force_at_local_point(Vec2d(force[0], force[1]), Vec2d(point[0], point[1]))

    def apply_impulse_at_world_point(self, impulse: Tuple[float, float], point: Tuple[float, float]):
        """在世界坐标的某点施加冲量"""
        self._body.apply_impulse_at_world_point(Vec2d(impulse[0], impulse[1]), Vec2d(point[0], point[1]))


class PyMunkPhysicsEngine:
    """PyMunk物理引擎适配器"""

    def __init__(self):
        """初始化物理引擎"""
        self._space = pymunk.Space()
        self._space.gravity = Vec2d(0, -981)  # 默认重力 981 cm/s²
        self._bodies: List[PhysicsBody] = []
        self._collision_handlers = {}
        self._time_step = 1.0 / 60.0  # 默认60 FPS

    @property
    def gravity(self) -> Tuple[float, float]:
        """重力加速度"""
        return (self._space.gravity.x, self._space.gravity.y)

    @gravity.setter
    def gravity(self, value: Tuple[float, float]):
        """设置重力加速度"""
        self._space.gravity = Vec2d(value[0], value[1])

    @property
    def damping(self) -> float:
        """阻尼系数"""
        return self._space.damping

    @damping.setter
    def damping(self, value: float):
        """设置阻尼系数"""
        self._space.damping = value

    @property
    def iterations(self) -> int:
        """求解器迭代次数"""
        return self._space.iterations

    @iterations.setter
    def iterations(self, value: int):
        """设置求解器迭代次数（越高越精确但越慢）"""
        self._space.iterations = value

    def create_circle_body(
        self,
        radius: float,
        mass: float = 1.0,
        position: Tuple[float, float] = (0, 0),
        body_type: BodyType = BodyType.DYNAMIC,
        friction: float = 0.5,
        elasticity: float = 0.5
    ) -> PhysicsBody:
        """创建圆形刚体"""
        # 计算转动惯量
        if body_type == BodyType.DYNAMIC:
            moment = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, moment)
        elif body_type == BodyType.STATIC:
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

        body.position = Vec2d(position[0], position[1])

        # 创建形状
        shape = pymunk.Circle(body, radius)
        shape.friction = friction
        shape.elasticity = elasticity

        # 添加到空间
        self._space.add(body, shape)

        # 创建包装对象
        physics_body = PhysicsBody(body)
        physics_shape = PhysicsShape(shape)
        physics_body.shapes.append(physics_shape)
        self._bodies.append(physics_body)

        return physics_body

    def create_box_body(
        self,
        width: float,
        height: float,
        mass: float = 1.0,
        position: Tuple[float, float] = (0, 0),
        body_type: BodyType = BodyType.DYNAMIC,
        friction: float = 0.5,
        elasticity: float = 0.5
    ) -> PhysicsBody:
        """创建矩形刚体"""
        # 计算转动惯量
        if body_type == BodyType.DYNAMIC:
            moment = pymunk.moment_for_box(mass, (width, height))
            body = pymunk.Body(mass, moment)
        elif body_type == BodyType.STATIC:
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

        body.position = Vec2d(position[0], position[1])

        # 创建形状
        shape = pymunk.Poly.create_box(body, (width, height))
        shape.friction = friction
        shape.elasticity = elasticity

        # 添加到空间
        self._space.add(body, shape)

        # 创建包装对象
        physics_body = PhysicsBody(body)
        physics_shape = PhysicsShape(shape)
        physics_body.shapes.append(physics_shape)
        self._bodies.append(physics_body)

        return physics_body

    def create_segment_body(
        self,
        point_a: Tuple[float, float],
        point_b: Tuple[float, float],
        thickness: float = 1.0,
        body_type: BodyType = BodyType.STATIC,
        friction: float = 1.0,
        elasticity: float = 0.5
    ) -> PhysicsBody:
        """创建线段刚体（通常用于墙壁、地面等）"""
        if body_type == BodyType.STATIC:
            body = self._space.static_body
        else:
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            self._space.add(body)

        # 创建形状
        shape = pymunk.Segment(body, Vec2d(point_a[0], point_a[1]), Vec2d(point_b[0], point_b[1]), thickness)
        shape.friction = friction
        shape.elasticity = elasticity

        # 添加到空间
        self._space.add(shape)

        # 创建包装对象
        physics_body = PhysicsBody(body)
        physics_shape = PhysicsShape(shape)
        physics_body.shapes.append(physics_shape)

        return physics_body

    def create_polygon_body(
        self,
        vertices: List[Tuple[float, float]],
        mass: float = 1.0,
        position: Tuple[float, float] = (0, 0),
        body_type: BodyType = BodyType.DYNAMIC,
        friction: float = 0.5,
        elasticity: float = 0.5
    ) -> PhysicsBody:
        """创建多边形刚体"""
        # 转换顶点格式
        pymunk_vertices = [Vec2d(v[0], v[1]) for v in vertices]

        # 计算转动惯量
        if body_type == BodyType.DYNAMIC:
            moment = pymunk.moment_for_poly(mass, pymunk_vertices)
            body = pymunk.Body(mass, moment)
        elif body_type == BodyType.STATIC:
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

        body.position = Vec2d(position[0], position[1])

        # 创建形状
        shape = pymunk.Poly(body, pymunk_vertices)
        shape.friction = friction
        shape.elasticity = elasticity

        # 添加到空间
        self._space.add(body, shape)

        # 创建包装对象
        physics_body = PhysicsBody(body)
        physics_shape = PhysicsShape(shape)
        physics_body.shapes.append(physics_shape)
        self._bodies.append(physics_body)

        return physics_body

    def remove_body(self, body: PhysicsBody):
        """移除刚体"""
        if body in self._bodies:
            self._bodies.remove(body)

        # 移除所有形状
        for shape in body.shapes:
            if shape._shape in self._space.shapes:
                self._space.remove(shape._shape)

        # 移除刚体
        if body._body in self._space.bodies:
            self._space.remove(body._body)

    def add_spring(
        self,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
        anchor_a: Tuple[float, float] = (0, 0),
        anchor_b: Tuple[float, float] = (0, 0),
        rest_length: float = 0,
        stiffness: float = 10.0,
        damping: float = 1.0
    ) -> pymunk.Constraint:
        """在两个刚体之间添加弹簧约束"""
        spring = pymunk.DampedSpring(
            body_a._body, body_b._body,
            Vec2d(anchor_a[0], anchor_a[1]),
            Vec2d(anchor_b[0], anchor_b[1]),
            rest_length,
            stiffness,
            damping
        )
        self._space.add(spring)
        return spring

    def add_pin_joint(
        self,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
        anchor_a: Tuple[float, float] = (0, 0),
        anchor_b: Tuple[float, float] = (0, 0)
    ) -> pymunk.Constraint:
        """在两个刚体之间添加钉住关节"""
        joint = pymunk.PinJoint(
            body_a._body, body_b._body,
            Vec2d(anchor_a[0], anchor_a[1]),
            Vec2d(anchor_b[0], anchor_b[1])
        )
        self._space.add(joint)
        return joint

    def add_pivot_joint(
        self,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
        pivot: Tuple[float, float]
    ) -> pymunk.Constraint:
        """在两个刚体之间添加枢轴关节"""
        joint = pymunk.PivotJoint(
            body_a._body, body_b._body,
            Vec2d(pivot[0], pivot[1])
        )
        self._space.add(joint)
        return joint

    def remove_constraint(self, constraint: pymunk.Constraint):
        """移除约束"""
        if constraint in self._space.constraints:
            self._space.remove(constraint)

    def ray_cast(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> Optional[dict]:
        """射线检测

        Returns:
            如果击中返回字典包含：
            - body: PhysicsBody
            - point: (x, y)
            - normal: (x, y)
            - alpha: 击中点的参数值 (0-1)
        """
        hit_info = self._space.segment_query_first(
            Vec2d(start[0], start[1]),
            Vec2d(end[0], end[1]),
            0,
            pymunk.ShapeFilter()
        )

        if hit_info:
            # 查找对应的PhysicsBody
            for body in self._bodies:
                if body._body == hit_info.shape.body:
                    return {
                        'body': body,
                        'point': (hit_info.point.x, hit_info.point.y),
                        'normal': (hit_info.normal.x, hit_info.normal.y),
                        'alpha': hit_info.alpha
                    }

        return None

    def point_query(
        self,
        point: Tuple[float, float],
        max_distance: float = 0
    ) -> List[dict]:
        """点查询 - 查找距离某点最近的形状"""
        results = []

        query_result = self._space.point_query_nearest(
            Vec2d(point[0], point[1]),
            max_distance,
            pymunk.ShapeFilter()
        )

        if query_result:
            # 查找对应的PhysicsBody
            for body in self._bodies:
                if body._body == query_result.shape.body:
                    results.append({
                        'body': body,
                        'point': (query_result.point.x, query_result.point.y),
                        'distance': query_result.distance
                    })
                    break

        return results

    def step(self, dt: Optional[float] = None):
        """推进物理模拟一帧

        Args:
            dt: 时间步长（秒），如果为None则使用默认值
        """
        if dt is None:
            dt = self._time_step
        self._space.step(dt)

    def clear(self):
        """清空物理世界"""
        # 移除所有约束
        for constraint in list(self._space.constraints):
            self._space.remove(constraint)

        # 移除所有形状和刚体
        for body in self._bodies:
            for shape in body.shapes:
                if shape._shape in self._space.shapes:
                    self._space.remove(shape._shape)
            if body._body in self._space.bodies:
                self._space.remove(body._body)

        self._bodies.clear()

    @property
    def body_count(self) -> int:
        """刚体数量"""
        return len(self._bodies)

    @property
    def shape_count(self) -> int:
        """形状数量"""
        return len(self._space.shapes)

    @property
    def constraint_count(self) -> int:
        """约束数量"""
        return len(self._space.constraints)
