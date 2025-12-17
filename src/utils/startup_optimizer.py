"""
启动优化器
提供启动性能优化和异步资源加载
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DependencyCheckResult:
    """依赖检查结果"""

    name: str
    available: bool
    version: str | None = None
    check_time: float = 0.0
    error: str | None = None


@dataclass
class CachedCheckResult:
    """缓存的检查结果"""

    results: list[DependencyCheckResult]
    timestamp: datetime
    checksum: str  # 环境校验和


class StartupOptimizer:
    """启动优化器"""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "dependency_check_cache.json"

        # 缓存有效期：7 天
        self.cache_validity = timedelta(days=7)

        logger.info("启动优化器初始化完成")

    def get_environment_checksum(self) -> str:
        """获取环境校验和（用于检测环境变化）"""
        import sys

        env_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "executable": sys.executable,
        }

        env_str = json.dumps(env_info, sort_keys=True)
        return hashlib.sha256(env_str.encode()).hexdigest()

    def load_cached_results(self) -> CachedCheckResult | None:
        """加载缓存的检查结果"""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            timestamp = datetime.fromisoformat(data["timestamp"])
            checksum = data["checksum"]

            # 检查缓存是否过期
            if datetime.now() - timestamp > self.cache_validity:
                logger.info("依赖检查缓存已过期")
                return None

            # 检查环境是否变化
            current_checksum = self.get_environment_checksum()
            if checksum != current_checksum:
                logger.info("环境已变化，缓存无效")
                return None

            results = [
                DependencyCheckResult(
                    name=r["name"],
                    available=r["available"],
                    version=r.get("version"),
                    check_time=r.get("check_time", 0.0),
                    error=r.get("error"),
                )
                for r in data["results"]
            ]

            logger.info(f"加载缓存的依赖检查结果 ({len(results)} 项)")
            return CachedCheckResult(
                results=results, timestamp=timestamp, checksum=checksum
            )

        except Exception as e:
            logger.warning(f"加载依赖检查缓存失败: {e}")
            return None

    def save_cached_results(self, results: list[DependencyCheckResult]) -> None:
        """保存检查结果到缓存"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "checksum": self.get_environment_checksum(),
                "results": [
                    {
                        "name": r.name,
                        "available": r.available,
                        "version": r.version,
                        "check_time": r.check_time,
                        "error": r.error,
                    }
                    for r in results
                ],
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"依赖检查结果已缓存 ({len(results)} 项)")

        except Exception as e:
            logger.warning(f"保存依赖检查缓存失败: {e}")

    def check_dependency(
        self, module_name: str, package_name: str | None = None
    ) -> DependencyCheckResult:
        """检查单个依赖"""
        start_time = time.time()
        package_name = package_name or module_name

        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", None)

            check_time = time.time() - start_time
            return DependencyCheckResult(
                name=package_name,
                available=True,
                version=version,
                check_time=check_time,
            )

        except ImportError as e:
            check_time = time.time() - start_time
            return DependencyCheckResult(
                name=package_name, available=False, check_time=check_time, error=str(e)
            )

    def check_dependencies_fast(
        self, dependencies: dict[str, str], force_check: bool = False
    ) -> list[DependencyCheckResult]:
        """快速检查依赖（使用缓存）"""
        # 尝试从缓存加载
        if not force_check:
            cached = self.load_cached_results()
            if cached:
                # 验证缓存的依赖列表是否匹配
                cached_names = {r.name for r in cached.results}
                required_names = set(dependencies.values())

                if cached_names == required_names:
                    logger.info("使用缓存的依赖检查结果")
                    return cached.results

        # 执行完整检查
        logger.info("执行完整的依赖检查...")
        results = []

        for module_name, package_name in dependencies.items():
            result = self.check_dependency(module_name, package_name)
            results.append(result)
            logger.debug(
                f"检查 {package_name}: {'✅' if result.available else '❌'} ({result.check_time:.3f}s)"
            )

        # 保存到缓存
        self.save_cached_results(results)

        return results

    async def load_resource_async(
        self, resource_name: str, loader_func: Callable, priority: int = 0
    ) -> tuple[str, Any, float]:
        """异步加载资源

        Args:
            resource_name: 资源名称
            loader_func: 加载函数
            priority: 优先级（数字越小优先级越高）

        Returns:
            (资源名称, 加载结果, 耗时)
        """
        start_time = time.time()
        logger.debug(f"开始加载资源: {resource_name} (priority={priority})")

        try:
            # 在线程池中执行加载函数（避免阻塞）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, loader_func)

            elapsed = time.time() - start_time
            logger.info(f"✅ 异步加载 {resource_name} 完成 ({elapsed:.3f}s)")

            return resource_name, result, elapsed

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 异步加载 {resource_name} 失败: {e} ({elapsed:.3f}s)")
            return resource_name, None, elapsed


class ResourceLoader:
    """资源加载器"""

    def __init__(self):
        self.loaded_resources: dict[str, Any] = {}
        self.load_times: dict[str, float] = {}

    async def load_multiple_resources(
        self, resources: list[tuple[str, Callable, int]]
    ) -> dict[str, Any]:
        """并行加载多个资源

        Args:
            resources: [(资源名称, 加载函数, 优先级), ...]

        Returns:
            {资源名称: 加载结果}
        """
        optimizer = StartupOptimizer()

        # 按优先级排序
        sorted_resources = sorted(resources, key=lambda x: x[2])

        # 创建异步任务
        tasks = [
            optimizer.load_resource_async(name, loader, priority)
            for name, loader, priority in sorted_resources
        ]

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        loaded = {}
        total_time = 0.0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"资源加载异常: {result}")
                continue

            name, data, elapsed = result
            loaded[name] = data
            self.load_times[name] = elapsed
            total_time += elapsed

        logger.info(
            f"资源加载完成: {len(loaded)}/{len(resources)} 项，总耗时: {total_time:.3f}s"
        )
        self.loaded_resources.update(loaded)

        return loaded

    def get_resource(self, name: str) -> Any:
        """获取已加载的资源"""
        return self.loaded_resources.get(name)

    def get_load_time(self, name: str) -> float:
        """获取资源加载时间"""
        return self.load_times.get(name, 0.0)

    def get_load_summary(self) -> dict[str, Any]:
        """获取加载摘要"""
        return {
            "total_resources": len(self.loaded_resources),
            "total_time": sum(self.load_times.values()),
            "average_time": sum(self.load_times.values()) / len(self.load_times)
            if self.load_times
            else 0.0,
            "resources": {
                name: self.load_times.get(name, 0.0)
                for name in self.loaded_resources.keys()
            },
        }


class ProgressEstimator:
    """进度估算器"""

    def __init__(self):
        self.steps: list[tuple[str, float]] = []  # (步骤名, 预估耗时)
        self.total_weight = 0.0
        self.completed_weight = 0.0
        self.start_time: float | None = None

    def add_step(self, name: str, estimated_time: float = 1.0) -> None:
        """添加步骤

        Args:
            name: 步骤名称
            estimated_time: 预估耗时（秒）
        """
        self.steps.append((name, estimated_time))
        self.total_weight += estimated_time

    def start(self) -> None:
        """开始计时"""
        self.start_time = time.time()

    def complete_step(self, name: str) -> float:
        """完成步骤，返回进度百分比"""
        for step_name, weight in self.steps:
            if step_name == name:
                self.completed_weight += weight
                break

        return self.get_progress()

    def get_progress(self) -> float:
        """获取当前进度 (0-100)"""
        if self.total_weight == 0:
            return 0.0

        return min(100.0, (self.completed_weight / self.total_weight) * 100)

    def get_estimated_remaining_time(self) -> float:
        """获取预估剩余时间（秒）"""
        if not self.start_time or self.completed_weight == 0:
            return 0.0

        elapsed = time.time() - self.start_time
        progress = self.completed_weight / self.total_weight

        if progress == 0:
            return 0.0

        total_estimated = elapsed / progress
        remaining = total_estimated - elapsed

        return max(0.0, remaining)

    def get_status(self) -> dict[str, Any]:
        """获取状态信息"""
        return {
            "progress": self.get_progress(),
            "completed_steps": self.completed_weight,
            "total_steps": self.total_weight,
            "remaining_time": self.get_estimated_remaining_time(),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0.0,
        }


# 单例实例
_startup_optimizer_instance: StartupOptimizer | None = None
_resource_loader_instance: ResourceLoader | None = None


def get_startup_optimizer() -> StartupOptimizer:
    """获取启动优化器单例"""
    global _startup_optimizer_instance
    if _startup_optimizer_instance is None:
        _startup_optimizer_instance = StartupOptimizer()
    return _startup_optimizer_instance


def get_resource_loader() -> ResourceLoader:
    """获取资源加载器单例"""
    global _resource_loader_instance
    if _resource_loader_instance is None:
        _resource_loader_instance = ResourceLoader()
    return _resource_loader_instance
