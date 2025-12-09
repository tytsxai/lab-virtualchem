#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
物理引擎模块
提供高性能的2D物理模拟功能
"""

from .pymunk_adapter import (
    BodyType,
    PhysicsBody,
    PhysicsShape,
    PyMunkPhysicsEngine,
    ShapeType,
)

__all__ = [
    'PyMunkPhysicsEngine',
    'PhysicsBody',
    'PhysicsShape',
    'BodyType',
    'ShapeType',
]

