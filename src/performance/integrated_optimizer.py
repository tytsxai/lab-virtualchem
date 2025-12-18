"""
集成性能优化器
整合所有性能优化功能，提供统一的优化接口
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger
from .backend_optimizer import get_api_cache, get_query_optimizer
from .frontend_optimizer import (
    get_lazy_component_loader,
    get_resource_loader,
    get_ui_render_optimizer,
)
from .high_freq_optimizer import (
    get_experiment_load_optimizer,
    get_particle_system_optimizer,
    get_physics_engine_optimizer,
    get_rendering_optimizer,
)

logger = get_logger(__name__)


@dataclass
class PerformanceReport:
    """性能报告"""

    timestamp: float
    frontend_stats: dict[str, Any]
    backend_stats: dict[str, Any]
    high_freq_stats: dict[str, Any]
    overall_score: float


class IntegratedPerformanceOptimizer(QObject):
    """集成性能优化器"""

    performance_updated = Signal(PerformanceReport)

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__()

        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

        # 子优化器
        self.resource_loader = get_resource_loader()
        self.ui_optimizer = get_ui_render_optimizer()
        self.lazy_loader = get_lazy_component_loader()
        self.query_optimizer = get_query_optimizer()
        self.api_cache = get_api_cache()
        self.experiment_optimizer = get_experiment_load_optimizer()
        self.particle_optimizer = get_particle_system_optimizer()
        self.physics_optimizer = get_physics_engine_optimizer()
        self.rendering_optimizer = get_rendering_optimizer()

        # 性能监控
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._collect_performance_metrics)
        self.monitor_interval = self.config.get("monitor_interval", 5000)  # 5秒

        # 性能历史
        self.performance_history: list[PerformanceReport] = []
        self.max_history_size = 100

        logger.info("集成性能优化器初始化完成")

    def start_monitoring(self):
        """启动性能监控"""
        if self.enabled:
            self.monitor_timer.start(self.monitor_interval)
            logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        self.monitor_timer.stop()
        logger.info("性能监控已停止")

    def apply_all_optimizations(self):
        """应用所有优化"""
        if not self.enabled:
            logger.info("性能优化已禁用")
            return

        logger.info("应用所有性能优化...")

        # 前端优化
        self._apply_frontend_optimizations()

        # 后端优化
        self._apply_backend_optimizations()

        # 高频操作优化
        self._apply_high_freq_optimizations()

        logger.info("所有性能优化已应用")

    def _apply_frontend_optimizations(self):
        """应用前端优化"""
        frontend_config = self.config.get("frontend", {})

        # 配置资源加载器
        if frontend_config.get("lazy_loading", {}).get("enabled", True):
            logger.info("  启用懒加载")

        # 配置图片优化
        if frontend_config.get("image_optimization", {}).get("enabled", True):
            logger.info("  启用图片优化")

        # 预加载关键资源
        if frontend_config.get("preload_critical", True):
            critical_resources = frontend_config.get("critical_resources", [])
            if critical_resources:
                self.resource_loader.preload_resources(critical_resources)
                logger.info(f"  预加载 {len(critical_resources)} 个关键资源")

    def _apply_backend_optimizations(self):
        """应用后端优化"""
        backend_config = self.config.get("backend", {})

        # 配置查询缓存
        if backend_config.get("query_cache", {}).get("enabled", True):
            cache_ttl = backend_config.get("query_cache", {}).get("ttl", 300)
            self.query_optimizer.cache_ttl = cache_ttl
            logger.info(f"  启用查询缓存 (TTL: {cache_ttl}s)")

        # 配置API缓存
        if backend_config.get("api_cache", {}).get("enabled", True):
            api_ttl = backend_config.get("api_cache", {}).get("ttl", 300)
            self.api_cache.ttl = api_ttl
            logger.info(f"  启用API缓存 (TTL: {api_ttl}s)")

    def _apply_high_freq_optimizations(self):
        """应用高频操作优化"""
        high_freq_config = self.config.get("high_freq", {})

        # 实验加载优化
        if high_freq_config.get("experiment_loading", {}).get("enabled", True):
            cache_size = high_freq_config.get("experiment_loading", {}).get(
                "cache_size", 10
            )
            self.experiment_optimizer.max_cache_size = cache_size
            logger.info(f"  启用实验加载优化 (缓存: {cache_size})")

        # 粒子系统优化
        if high_freq_config.get("particle_system", {}).get("enabled", True):
            max_particles = high_freq_config.get("particle_system", {}).get(
                "max_particles", 2000
            )
            self.particle_optimizer.max_particles = max_particles
            logger.info(f"  启用粒子系统优化 (最大粒子: {max_particles})")

        # 物理引擎优化
        if high_freq_config.get("physics_engine", {}).get("enabled", True):
            logger.info("  启用物理引擎优化")

        # 渲染优化
        if high_freq_config.get("rendering", {}).get("enabled", True):
            target_fps = high_freq_config.get("rendering", {}).get("target_fps", 60)
            self.rendering_optimizer.target_fps = target_fps
            logger.info(f"  启用渲染优化 (目标FPS: {target_fps})")

    def _collect_performance_metrics(self):
        """收集性能指标"""
        # 前端指标
        frontend_stats = {
            "lazy_loaded_components": len(self.lazy_loader.loaded_components),
            "resource_cache_size": len(self.resource_loader.resource_cache),
        }

        # 后端指标
        backend_stats = {
            "query_stats": self.query_optimizer.get_cache_stats(),
            "api_cache_stats": self.api_cache.get_stats(),
        }

        # 高频操作指标
        high_freq_stats = {
            "experiment_load_stats": self.experiment_optimizer.get_load_stats(),
            "particle_stats": self.particle_optimizer.get_stats(),
            "physics_stats": self.physics_optimizer.get_stats(),
            "rendering_stats": self.rendering_optimizer.get_render_stats(),
        }

        # 计算总体性能分数
        overall_score = self._calculate_performance_score(
            frontend_stats, backend_stats, high_freq_stats
        )

        # 创建报告
        report = PerformanceReport(
            timestamp=time.time(),
            frontend_stats=frontend_stats,
            backend_stats=backend_stats,
            high_freq_stats=high_freq_stats,
            overall_score=overall_score,
        )

        # 保存历史
        self.performance_history.append(report)
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)

        # 发送信号
        self.performance_updated.emit(report)

    def _calculate_performance_score(
        self,
        _frontend_stats: dict[str, Any],
        backend_stats: dict[str, Any],
        high_freq_stats: dict[str, Any],
    ) -> float:
        """计算性能分数（0-100）"""
        score = 100.0

        # 前端评分
        # 无评分项，保持100分

        # 后端评分
        query_hit_rate = backend_stats.get("query_stats", {}).get("cache_hit_rate", 0)
        api_hit_rate = backend_stats.get("api_cache_stats", {}).get("hit_rate", 0)

        # 缓存命中率影响分数（最多扣20分）
        cache_score = (query_hit_rate + api_hit_rate) / 2 * 20
        score -= 20 - cache_score

        # 高频操作评分
        exp_cache_rate = high_freq_stats.get("experiment_load_stats", {}).get(
            "cache_hit_rate", 0
        )
        particle_util = high_freq_stats.get("particle_stats", {}).get(
            "pool_utilization", 0
        )

        # 高频操作效率影响分数（最多扣20分）
        high_freq_score = (exp_cache_rate + (1 - particle_util)) / 2 * 20
        score -= 20 - high_freq_score

        return max(0, min(100, score))

    def get_performance_report(self) -> PerformanceReport | None:
        """获取最新性能报告"""
        return self.performance_history[-1] if self.performance_history else None

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_history:
            return {
                "status": "no_data",
                "message": "暂无性能数据",
            }

        recent_reports = self.performance_history[-10:]  # 最近10个报告
        avg_score = sum(r.overall_score for r in recent_reports) / len(recent_reports)

        # 确定性能等级
        if avg_score >= 90:
            performance_level = "excellent"
            level_text = "优秀"
        elif avg_score >= 70:
            performance_level = "good"
            level_text = "良好"
        elif avg_score >= 50:
            performance_level = "fair"
            level_text = "一般"
        else:
            performance_level = "poor"
            level_text = "需要优化"

        latest_report = recent_reports[-1]

        return {
            "status": "ok",
            "performance_level": performance_level,
            "level_text": level_text,
            "avg_score": avg_score,
            "latest_score": latest_report.overall_score,
            "frontend_stats": latest_report.frontend_stats,
            "backend_stats": latest_report.backend_stats,
            "high_freq_stats": latest_report.high_freq_stats,
            "recommendations": self._get_recommendations(latest_report),
        }

    def _get_recommendations(self, report: PerformanceReport) -> list[str]:
        """获取优化建议"""
        recommendations = []

        # 检查查询缓存命中率
        query_hit_rate = report.backend_stats.get("query_stats", {}).get(
            "cache_hit_rate", 0
        )
        if query_hit_rate < 0.5:
            recommendations.append("查询缓存命中率较低，建议增加缓存TTL或预热常用查询")

        # 检查API缓存
        api_hit_rate = report.backend_stats.get("api_cache_stats", {}).get(
            "hit_rate", 0
        )
        if api_hit_rate < 0.5:
            recommendations.append("API缓存命中率较低，建议检查缓存策略")

        # 检查实验加载
        exp_cache_rate = report.high_freq_stats.get("experiment_load_stats", {}).get(
            "cache_hit_rate", 0
        )
        if exp_cache_rate < 0.6:
            recommendations.append("实验缓存命中率较低，建议启用预加载相关实验")

        # 检查粒子系统
        particle_util = report.high_freq_stats.get("particle_stats", {}).get(
            "pool_utilization", 0
        )
        if particle_util > 0.9:
            recommendations.append(
                "粒子系统接近容量上限，建议增加粒子池大小或优化粒子回收"
            )

        # 检查渲染FPS
        current_fps = report.high_freq_stats.get("rendering_stats", {}).get(
            "current_fps", 60
        )
        if current_fps < 30:
            recommendations.append("渲染帧率较低，建议启用视锥剔除或减少渲染对象")

        if not recommendations:
            recommendations.append("性能表现良好，无需特别优化")

        return recommendations

    def clear_all_caches(self):
        """清空所有缓存"""
        self.resource_loader.clear_cache()
        self.query_optimizer.clear_cache()
        self.api_cache.clear()

        logger.info("所有缓存已清空")

    def export_performance_report(self, filepath: str):
        """导出性能报告"""
        import json

        if not self.performance_history:
            logger.warning("无性能数据可导出")
            return

        data = {
            "generated_at": time.time(),
            "total_reports": len(self.performance_history),
            "summary": self.get_performance_summary(),
            "history": [
                {
                    "timestamp": r.timestamp,
                    "frontend_stats": r.frontend_stats,
                    "backend_stats": r.backend_stats,
                    "high_freq_stats": r.high_freq_stats,
                    "overall_score": r.overall_score,
                }
                for r in self.performance_history
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"性能报告已导出: {filepath}")


# 全局实例
_integrated_optimizer: IntegratedPerformanceOptimizer | None = None


def get_integrated_optimizer(
    config: dict[str, Any] | None = None,
) -> IntegratedPerformanceOptimizer:
    """获取集成性能优化器"""
    global _integrated_optimizer
    if _integrated_optimizer is None:
        _integrated_optimizer = IntegratedPerformanceOptimizer(config)
    return _integrated_optimizer


def init_performance_optimizations(config: dict[str, Any] | None = None):
    """初始化性能优化"""
    optimizer = get_integrated_optimizer(config)
    optimizer.apply_all_optimizations()
    optimizer.start_monitoring()
    logger.info("性能优化系统已启动")


def get_performance_summary() -> dict[str, Any]:
    """获取性能摘要（便捷函数）"""
    optimizer = get_integrated_optimizer()
    return optimizer.get_performance_summary()
