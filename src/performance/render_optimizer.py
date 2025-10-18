"""
渲染优化器
提供渲染性能优化和帧率控制
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RenderStrategy(Enum):
    """渲染策略"""

    IMMEDIATE = "immediate"  # 立即渲染
    BATCHED = "batched"  # 批处理渲染
    LAZY = "lazy"  # 懒渲染
    ADAPTIVE = "adaptive"  # 自适应渲染


@dataclass
class RenderMetrics:
    """渲染指标"""

    fps: float
    frame_time: float
    draw_calls: int
    triangles: int
    timestamp: float


class RenderOptimizer(QObject):
    """渲染优化器"""

    metrics_updated = Signal(RenderMetrics)

    def __init__(self):
        super().__init__()
        self.target_fps = 60
        self.strategy = RenderStrategy.ADAPTIVE
        self.frame_times: list[float] = []
        self.max_frame_history = 60

        # 监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)

        logger.info("渲染优化器初始化完成")

    def start_monitoring(self, interval: int = 1000):
        """启动性能监控"""
        self.monitor_timer.start(interval)
        logger.info("渲染性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        self.monitor_timer.stop()
        logger.info("渲染性能监控已停止")

    def set_target_fps(self, fps: int):
        """设置目标帧率"""
        self.target_fps = max(1, min(120, fps))
        logger.info(f"目标帧率设置为: {self.target_fps}")

    def set_strategy(self, strategy: RenderStrategy):
        """设置渲染策略"""
        self.strategy = strategy
        logger.info(f"渲染策略设置为: {strategy.value}")

    def optimize_frame(self, frame_data: dict[str, Any]) -> dict[str, Any]:
        """优化帧渲染"""
        if self.strategy == RenderStrategy.IMMEDIATE:
            return self._optimize_immediate(frame_data)
        elif self.strategy == RenderStrategy.BATCHED:
            return self._optimize_batched(frame_data)
        elif self.strategy == RenderStrategy.LAZY:
            return self._optimize_lazy(frame_data)
        else:  # ADAPTIVE
            return self._optimize_adaptive(frame_data)

    def _optimize_immediate(self, frame_data: dict[str, Any]) -> dict[str, Any]:
        """立即渲染优化"""
        # 立即渲染，无特殊优化
        return frame_data

    def _optimize_batched(self, frame_data: dict[str, Any]) -> dict[str, Any]:
        """批处理渲染优化"""
        # 合并绘制调用
        optimized = frame_data.copy()
        if "draw_calls" in frame_data:
            optimized["draw_calls"] = max(1, frame_data["draw_calls"] // 2)
        return optimized

    def _optimize_lazy(self, frame_data: dict[str, Any]) -> dict[str, Any]:
        """懒渲染优化"""
        # 减少不必要的渲染
        optimized = frame_data.copy()
        if "off_screen_objects" in frame_data:
            optimized["off_screen_objects"] = 0
        return optimized

    def _optimize_adaptive(self, frame_data: dict[str, Any]) -> dict[str, Any]:
        """自适应渲染优化"""
        current_fps = self._calculate_current_fps()

        if current_fps < self.target_fps * 0.8:
            # 性能不足，启用激进优化
            return self._optimize_lazy(frame_data)
        elif current_fps > self.target_fps * 1.2:
            # 性能过剩，可以渲染更多细节
            return self._optimize_immediate(frame_data)
        else:
            # 正常范围，使用批处理
            return self._optimize_batched(frame_data)

    def _collect_metrics(self):
        """收集性能指标"""
        current_fps = self._calculate_current_fps()
        frame_time = 1000.0 / current_fps if current_fps > 0 else 0

        # 这里应该是实际的渲染指标收集
        # 暂时使用模拟数据
        metrics = RenderMetrics(
            fps=current_fps,
            frame_time=frame_time,
            draw_calls=100,
            triangles=5000,
            timestamp=time.time()
        )

        # 保存帧时间历史
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)

        # 发送信号
        self.metrics_updated.emit(metrics)

    def _calculate_current_fps(self) -> float:
        """计算当前帧率"""
        if len(self.frame_times) < 2:
            return self.target_fps

        # 基于最近的帧时间计算平均帧率
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1000.0 / avg_frame_time if avg_frame_time > 0 else self.target_fps

    def get_render_stats(self) -> dict[str, Any]:
        """获取渲染统计"""
        if not self.frame_times:
            return {"fps": 0, "frame_time": 0, "draw_calls": 0}

        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        avg_fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0

        return {
            "fps": avg_fps,
            "frame_time": avg_frame_time,
            "draw_calls": 100,  # 模拟数据
            "triangles": 5000,  # 模拟数据
        }

    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        self.frame_times.clear()
        logger.info("渲染优化器已清理")


def get_render_optimizer() -> RenderOptimizer:
    """获取渲染优化器实例"""
    return RenderOptimizer()
