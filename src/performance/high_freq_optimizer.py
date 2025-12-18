"""
高频操作场景优化器
针对实验加载、粒子系统、物理引擎等频繁操作的性能优化
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentLoadMetrics:
    """实验加载性能指标"""

    experiment_id: str
    load_time: float
    resource_count: int
    cache_hit: bool
    timestamp: float


class ExperimentLoadOptimizer(QObject):
    """实验加载优化器"""

    load_completed = Signal(str, float)  # experiment_id, load_time

    def __init__(self):
        super().__init__()
        self.experiment_cache: dict[str, Any] = {}
        self.load_metrics: list[ExperimentLoadMetrics] = []
        self.preload_queue: deque[str] = deque()
        self.max_cache_size = 10

        logger.info("实验加载优化器初始化完成")

    def load_experiment(self, experiment_id: str, force_reload: bool = False) -> Any:
        """加载实验（带缓存）"""
        start_time = time.time()

        # 检查缓存
        if not force_reload and experiment_id in self.experiment_cache:
            load_time = time.time() - start_time

            metrics = ExperimentLoadMetrics(
                experiment_id=experiment_id,
                load_time=load_time,
                resource_count=0,
                cache_hit=True,
                timestamp=time.time(),
            )

            self.load_metrics.append(metrics)
            self.load_completed.emit(experiment_id, load_time)

            logger.debug(f"从缓存加载实验: {experiment_id} ({load_time * 1000:.2f}ms)")
            return self.experiment_cache[experiment_id]

        # 实际加载
        experiment_data = self._load_experiment_data(experiment_id)
        load_time = time.time() - start_time

        # 缓存
        self._cache_experiment(experiment_id, experiment_data)

        # 记录指标
        metrics = ExperimentLoadMetrics(
            experiment_id=experiment_id,
            load_time=load_time,
            resource_count=self._count_resources(experiment_data),
            cache_hit=False,
            timestamp=time.time(),
        )

        self.load_metrics.append(metrics)
        self.load_completed.emit(experiment_id, load_time)

        logger.info(f"加载实验: {experiment_id} ({load_time * 1000:.2f}ms)")
        return experiment_data

    def preload_next_experiments(self, current_id: str, next_ids: list[str]):
        """预加载下一个实验"""
        for exp_id in next_ids:
            if exp_id != current_id and exp_id not in self.experiment_cache:
                self.preload_queue.append(exp_id)

        # 启动预加载
        if not hasattr(self, "_preload_timer"):
            self._preload_timer = QTimer(self)
            self._preload_timer.timeout.connect(self._process_preload)
            self._preload_timer.start(100)  # 100ms间隔

    def _process_preload(self):
        """处理预加载队列"""
        if not self.preload_queue:
            self._preload_timer.stop()
            return

        exp_id = self.preload_queue.popleft()
        logger.debug(f"预加载实验: {exp_id}")

        try:
            self.load_experiment(exp_id)
        except Exception as e:
            logger.error(f"预加载失败: {exp_id} - {e}")

    def _load_experiment_data(self, experiment_id: str) -> dict[str, Any]:
        """实际加载实验数据（需要实现）"""
        # 这里应该从文件或数据库加载
        return {"id": experiment_id, "steps": [], "resources": []}

    def _cache_experiment(self, experiment_id: str, data: Any):
        """缓存实验数据"""
        # 检查缓存大小
        if len(self.experiment_cache) >= self.max_cache_size:
            # 移除最早的
            oldest_id = next(iter(self.experiment_cache))
            del self.experiment_cache[oldest_id]

        self.experiment_cache[experiment_id] = data

    def _count_resources(self, experiment_data: dict[str, Any]) -> int:
        """统计资源数量"""
        return len(experiment_data.get("resources", []))

    def get_load_stats(self) -> dict[str, Any]:
        """获取加载统计"""
        if not self.load_metrics:
            return {"avg_load_time": 0, "cache_hit_rate": 0, "total_loads": 0}

        total = len(self.load_metrics)
        cache_hits = sum(1 for m in self.load_metrics if m.cache_hit)
        avg_time = sum(m.load_time for m in self.load_metrics) / total

        return {
            "avg_load_time": avg_time,
            "cache_hit_rate": cache_hits / total,
            "total_loads": total,
            "cached_experiments": len(self.experiment_cache),
        }


class ParticleSystemOptimizer:
    """粒子系统优化器"""

    def __init__(self, max_particles: int = 2000):
        self.max_particles = max_particles
        self.particle_pool: list[Any] = []
        self.active_particles: list[Any] = []
        self.update_batch_size = 50

        logger.info(f"粒子系统优化器初始化完成 (最大粒子数: {max_particles})")

    def acquire_particle(self) -> Any:
        """从对象池获取粒子"""
        if self.particle_pool:
            return self.particle_pool.pop()

        # 创建新粒子
        if len(self.active_particles) < self.max_particles:
            particle = self._create_particle()
            return particle

        # 达到上限，复用最早的粒子
        if self.active_particles:
            particle = self.active_particles.pop(0)
            self.reset_particle(particle)
            return particle

        return None

    def release_particle(self, particle: Any):
        """释放粒子回对象池"""
        if particle in self.active_particles:
            self.active_particles.remove(particle)

        self.reset_particle(particle)
        self.particle_pool.append(particle)

    def batch_update_particles(self, delta_time: float):
        """批量更新粒子（提升性能）"""
        # 分批更新，避免单次更新过多粒子造成卡顿
        for i in range(0, len(self.active_particles), self.update_batch_size):
            batch = self.active_particles[i : i + self.update_batch_size]

            for particle in batch:
                self._update_particle(particle, delta_time)

    def _create_particle(self) -> Any:
        """创建粒子（需要实现）"""
        # 这里应该创建实际的粒子对象
        return {"position": [0, 0], "velocity": [0, 0], "lifetime": 1.0}

    def reset_particle(self, particle: Any):
        """重置粒子"""
        particle["position"] = [0, 0]
        particle["velocity"] = [0, 0]
        particle["lifetime"] = 1.0

    def _update_particle(self, particle: Any, delta_time: float):
        """更新粒子"""
        particle["lifetime"] -= delta_time

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "active_particles": len(self.active_particles),
            "pooled_particles": len(self.particle_pool),
            "total_capacity": self.max_particles,
            "pool_utilization": len(self.active_particles) / self.max_particles,
        }


class PhysicsEngineOptimizer:
    """物理引擎优化器"""

    def __init__(self):
        self.spatial_grid: dict[tuple[int, int], list[Any]] = {}
        self.grid_cell_size = 100
        self.last_update_time = time.time()

        logger.info("物理引擎优化器初始化完成")

    def update_spatial_grid(self, objects: list[Any]):
        """更新空间网格（用于碰撞检测优化）"""
        self.spatial_grid.clear()

        for obj in objects:
            grid_pos = self._get_grid_position(obj)
            if grid_pos not in self.spatial_grid:
                self.spatial_grid[grid_pos] = []
            self.spatial_grid[grid_pos].append(obj)

    def get_nearby_objects(self, obj: Any, radius: int = 1) -> list[Any]:
        """获取附近的对象（优化碰撞检测）"""
        grid_pos = self._get_grid_position(obj)
        nearby = []

        # 检查周围的网格
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                check_pos = (grid_pos[0] + dx, grid_pos[1] + dy)
                if check_pos in self.spatial_grid:
                    nearby.extend(self.spatial_grid[check_pos])

        return nearby

    def batch_physics_update(self, objects: list[Any], delta_time: float):
        """批量物理更新"""
        # 更新空间网格
        self.update_spatial_grid(objects)

        # 批量更新物理状态
        for obj in objects:
            self._update_physics(obj, delta_time)

    def _get_grid_position(self, obj: Any) -> tuple[int, int]:
        """获取网格位置"""
        # 假设对象有position属性
        pos = getattr(obj, "position", (0, 0))
        return (int(pos[0] / self.grid_cell_size), int(pos[1] / self.grid_cell_size))

    def _update_physics(self, obj: Any, delta_time: float):
        """更新物理状态（需要实现）"""
        pass

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        total_objects = sum(len(objects) for objects in self.spatial_grid.values())

        return {
            "grid_cells": len(self.spatial_grid),
            "total_objects": total_objects,
            "avg_objects_per_cell": (
                total_objects / len(self.spatial_grid) if self.spatial_grid else 0
            ),
        }


class RenderingOptimizer:
    """渲染优化器"""

    def __init__(self):
        self.visible_objects: set[Any] = set()
        self.render_cache: dict[str, Any] = {}
        self.last_render_time = 0
        self.target_fps = 60
        self.frame_time_budget = 1.0 / self.target_fps

        logger.info(f"渲染优化器初始化完成 (目标FPS: {self.target_fps})")

    def culling_check(self, obj: Any, viewport_rect: tuple[int, int, int, int]) -> bool:
        """视锥剔除检查"""
        # 简化的边界检查
        obj_bounds = getattr(obj, "bounds", (0, 0, 100, 100))

        x1, y1, w1, h1 = viewport_rect
        x2, y2, w2, h2 = obj_bounds

        # 检查是否相交
        return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

    def update_visible_objects(
        self, all_objects: list[Any], viewport_rect: tuple[int, int, int, int]
    ):
        """更新可见对象列表"""
        self.visible_objects.clear()

        for obj in all_objects:
            if self.culling_check(obj, viewport_rect):
                self.visible_objects.add(obj)

        logger.debug(f"可见对象: {len(self.visible_objects)}/{len(all_objects)}")

    def should_render(self) -> bool:
        """检查是否应该渲染（帧率控制）"""
        current_time = time.time()
        elapsed = current_time - self.last_render_time

        if elapsed >= self.frame_time_budget:
            self.last_render_time = current_time
            return True

        return False

    def get_render_stats(self) -> dict[str, Any]:
        """获取渲染统计"""
        current_fps = (
            1.0 / (time.time() - self.last_render_time)
            if self.last_render_time > 0
            else 0
        )

        return {
            "visible_objects": len(self.visible_objects),
            "current_fps": current_fps,
            "target_fps": self.target_fps,
            "cache_size": len(self.render_cache),
        }


# 全局实例
_experiment_load_optimizer: ExperimentLoadOptimizer | None = None
_particle_system_optimizer: ParticleSystemOptimizer | None = None
_physics_engine_optimizer: PhysicsEngineOptimizer | None = None
_rendering_optimizer: RenderingOptimizer | None = None


def get_experiment_load_optimizer() -> ExperimentLoadOptimizer:
    """获取实验加载优化器"""
    global _experiment_load_optimizer
    if _experiment_load_optimizer is None:
        _experiment_load_optimizer = ExperimentLoadOptimizer()
    return _experiment_load_optimizer


def get_particle_system_optimizer() -> ParticleSystemOptimizer:
    """获取粒子系统优化器"""
    global _particle_system_optimizer
    if _particle_system_optimizer is None:
        _particle_system_optimizer = ParticleSystemOptimizer()
    return _particle_system_optimizer


def get_physics_engine_optimizer() -> PhysicsEngineOptimizer:
    """获取物理引擎优化器"""
    global _physics_engine_optimizer
    if _physics_engine_optimizer is None:
        _physics_engine_optimizer = PhysicsEngineOptimizer()
    return _physics_engine_optimizer


def get_rendering_optimizer() -> RenderingOptimizer:
    """获取渲染优化器"""
    global _rendering_optimizer
    if _rendering_optimizer is None:
        _rendering_optimizer = RenderingOptimizer()
    return _rendering_optimizer
