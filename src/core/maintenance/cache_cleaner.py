"""
缓存清理器实现

提供全面的缓存清理功能，支持多种缓存类型
"""

import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ...contracts.maintenance_service import CacheType
from ...interfaces.maintenance import (
    ICacheCleaner,
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceTaskType,
)

logger = logging.getLogger(__name__)


class CacheCleaner(ICacheCleaner):
    """缓存清理器实现"""

    def __init__(
        self,
        cache_manager=None,
        redis_cache=None,
        base_path: str = ".",
    ):
        """
        初始化缓存清理器

        Args:
            cache_manager: 缓存管理器实例
            redis_cache: Redis缓存实例
            base_path: 基础路径
        """
        self.cache_manager = cache_manager
        self.redis_cache = redis_cache
        self.base_path = Path(base_path)

        # 缓存路径映射
        self.cache_paths = {
            CacheType.DISK: self.base_path / ".cache",
            CacheType.TEMPLATE: self.base_path / ".cache" / "templates",
            CacheType.ASSET: self.base_path / ".cache" / "assets",
        }

    def scan_cache(self) -> dict[str, Any]:
        """
        扫描缓存

        Returns:
            缓存信息字典
        """
        cache_info = {}

        try:
            # 扫描内存缓存
            if self.cache_manager:
                memory_info = self._scan_memory_cache()
                cache_info[CacheType.MEMORY.value] = memory_info

            # 扫描Redis缓存
            if self.redis_cache:
                redis_info = self._scan_redis_cache()
                cache_info[CacheType.REDIS.value] = redis_info

            # 扫描磁盘缓存
            for cache_type, cache_path in self.cache_paths.items():
                if cache_path.exists():
                    disk_info = self._scan_disk_cache(cache_path)
                    cache_info[cache_type.value] = disk_info

            # 计算总计
            cache_info["total"] = {
                "item_count": sum(
                    info.get("item_count", 0)
                    for info in cache_info.values()
                    if isinstance(info, dict)
                ),
                "size_bytes": sum(
                    info.get("size_bytes", 0)
                    for info in cache_info.values()
                    if isinstance(info, dict)
                ),
                "expired_count": sum(
                    info.get("expired_count", 0)
                    for info in cache_info.values()
                    if isinstance(info, dict)
                ),
            }

        except Exception as e:
            logger.error(f"扫描缓存失败: {e}", exc_info=True)
            cache_info["error"] = str(e)

        return cache_info

    def clear_cache(self, cache_types: list[str] | None = None) -> MaintenanceResult:
        """
        清理缓存

        Args:
            cache_types: 缓存类型列表，None表示清理所有

        Returns:
            维护结果
        """
        start_time = time.time()
        items_processed = 0
        bytes_freed = 0
        errors = []

        try:
            # 确定要清理的缓存类型
            if cache_types is None or CacheType.ALL.value in cache_types:
                types_to_clear = [t for t in CacheType if t != CacheType.ALL]
            else:
                types_to_clear = [
                    CacheType(t) for t in cache_types if t != CacheType.ALL.value
                ]

            # 清理各类缓存
            for cache_type in types_to_clear:
                try:
                    result = self._clear_cache_by_type(cache_type)
                    items_processed += result["items"]
                    bytes_freed += result["bytes"]
                except Exception as e:
                    error_msg = f"清理{cache_type.value}缓存失败: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            duration = time.time() - start_time
            success = len(errors) == 0

            return MaintenanceResult(
                task_type=MaintenanceTaskType.CACHE_CLEAR,
                status=MaintenanceStatus.COMPLETED
                if success
                else MaintenanceStatus.FAILED,
                success=success,
                message=f"缓存清理完成，处理{items_processed}项，释放{self._format_bytes(bytes_freed)}",
                items_processed=items_processed,
                items_fixed=items_processed,
                bytes_freed=bytes_freed,
                duration_seconds=duration,
                details={
                    "cache_types": [t.value for t in types_to_clear],
                },
                errors=errors,
            )

        except Exception as e:
            error_msg = f"缓存清理失败: {e}"
            logger.error(error_msg, exc_info=True)
            return MaintenanceResult(
                task_type=MaintenanceTaskType.CACHE_CLEAR,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=error_msg,
                duration_seconds=time.time() - start_time,
                errors=[error_msg],
            )

    def clear_expired_cache(self) -> MaintenanceResult:
        """
        清理过期缓存

        Returns:
            维护结果
        """
        start_time = time.time()
        items_processed = 0
        bytes_freed = 0
        errors = []

        try:
            # 清理内存缓存中的过期项
            if self.cache_manager:
                try:
                    result = self._clear_expired_memory_cache()
                    items_processed += result["items"]
                    bytes_freed += result["bytes"]
                except Exception as e:
                    errors.append(f"清理过期内存缓存失败: {e}")

            # 清理磁盘缓存中的过期文件(超过24小时)
            for cache_type, cache_path in self.cache_paths.items():
                if cache_path.exists():
                    try:
                        result = self._clear_old_files(cache_path, max_age_hours=24)
                        items_processed += result["items"]
                        bytes_freed += result["bytes"]
                    except Exception as e:
                        errors.append(f"清理过期{cache_type.value}缓存失败: {e}")

            duration = time.time() - start_time
            success = len(errors) == 0

            return MaintenanceResult(
                task_type=MaintenanceTaskType.CACHE_CLEAR,
                status=MaintenanceStatus.COMPLETED
                if success
                else MaintenanceStatus.FAILED,
                success=success,
                message=f"过期缓存清理完成，处理{items_processed}项，释放{self._format_bytes(bytes_freed)}",
                items_processed=items_processed,
                items_fixed=items_processed,
                bytes_freed=bytes_freed,
                duration_seconds=duration,
                errors=errors,
            )

        except Exception as e:
            error_msg = f"清理过期缓存失败: {e}"
            logger.error(error_msg, exc_info=True)
            return MaintenanceResult(
                task_type=MaintenanceTaskType.CACHE_CLEAR,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=error_msg,
                duration_seconds=time.time() - start_time,
                errors=[error_msg],
            )

    def get_cache_size(self) -> int:
        """
        获取缓存总大小

        Returns:
            缓存大小（字节）
        """
        total_size = 0

        try:
            # 内存缓存大小(估算)
            if self.cache_manager:
                # 假设每个缓存项平均1KB
                memory_size = self.cache_manager.size() * 1024
                total_size += memory_size

            # 磁盘缓存大小
            for cache_path in self.cache_paths.values():
                if cache_path.exists():
                    size = self._get_directory_size(cache_path)
                    total_size += size

        except Exception as e:
            logger.error(f"计算缓存大小失败: {e}", exc_info=True)

        return total_size

    def _clear_cache_by_type(self, cache_type: CacheType) -> dict[str, int]:
        """
        按类型清理缓存

        Args:
            cache_type: 缓存类型

        Returns:
            清理结果字典 {"items": int, "bytes": int}
        """
        if cache_type == CacheType.MEMORY:
            return self._clear_memory_cache()
        elif cache_type == CacheType.REDIS:
            return self._clear_redis_cache()
        elif cache_type in self.cache_paths:
            return self._clear_disk_cache(self.cache_paths[cache_type])
        else:
            return {"items": 0, "bytes": 0}

    def _clear_memory_cache(self) -> dict[str, int]:
        """清理内存缓存"""
        if not self.cache_manager:
            return {"items": 0, "bytes": 0}

        try:
            item_count = self.cache_manager.size()
            estimated_bytes = item_count * 1024  # 估算

            # 清理所有缓存
            for cache_name in self.cache_manager.list_caches():
                cache = self.cache_manager.get_cache(cache_name)
                cache.clear()

            logger.info(f"清理内存缓存: {item_count}项")
            return {"items": item_count, "bytes": estimated_bytes}

        except Exception as e:
            logger.error(f"清理内存缓存失败: {e}", exc_info=True)
            return {"items": 0, "bytes": 0}

    def _clear_redis_cache(self) -> dict[str, int]:
        """清理Redis缓存"""
        if not self.redis_cache:
            return {"items": 0, "bytes": 0}

        try:
            item_count = self.redis_cache.size()
            estimated_bytes = item_count * 1024  # 估算

            self.redis_cache.clear()

            logger.info(f"清理Redis缓存: {item_count}项")
            return {"items": item_count, "bytes": estimated_bytes}

        except Exception as e:
            logger.error(f"清理Redis缓存失败: {e}", exc_info=True)
            return {"items": 0, "bytes": 0}

    def _clear_disk_cache(self, cache_path: Path) -> dict[str, int]:
        """清理磁盘缓存"""
        if not cache_path.exists():
            return {"items": 0, "bytes": 0}

        try:
            size_before = self._get_directory_size(cache_path)
            item_count = sum(1 for _ in cache_path.rglob("*") if _.is_file())

            # 删除目录内容
            shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, exist_ok=True)

            logger.info(
                f"清理磁盘缓存 {cache_path}: {item_count}项, {self._format_bytes(size_before)}"
            )
            return {"items": item_count, "bytes": size_before}

        except Exception as e:
            logger.error(f"清理磁盘缓存失败: {e}", exc_info=True)
            return {"items": 0, "bytes": 0}

    def _clear_expired_memory_cache(self) -> dict[str, int]:
        """清理过期内存缓存"""
        if not self.cache_manager:
            return {"items": 0, "bytes": 0}

        try:
            items_cleared = 0
            # 这里需要根据实际的缓存管理器API来实现
            # 假设缓存管理器会自动处理过期项
            logger.info("清理过期内存缓存")
            return {"items": items_cleared, "bytes": items_cleared * 1024}

        except Exception as e:
            logger.error(f"清理过期内存缓存失败: {e}", exc_info=True)
            return {"items": 0, "bytes": 0}

    def _clear_old_files(self, directory: Path, max_age_hours: int) -> dict[str, int]:
        """
        清理旧文件

        Args:
            directory: 目录
            max_age_hours: 最大年龄(小时)

        Returns:
            清理结果
        """
        if not directory.exists():
            return {"items": 0, "bytes": 0}

        items_cleared = 0
        bytes_cleared = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_time:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        items_cleared += 1
                        bytes_cleared += size

            logger.info(
                f"清理旧文件 {directory}: {items_cleared}项, {self._format_bytes(bytes_cleared)}"
            )
            return {"items": items_cleared, "bytes": bytes_cleared}

        except Exception as e:
            logger.error(f"清理旧文件失败: {e}", exc_info=True)
            return {"items": items_cleared, "bytes": bytes_cleared}

    def _scan_memory_cache(self) -> dict[str, Any]:
        """扫描内存缓存"""
        if not self.cache_manager:
            return {"item_count": 0, "size_bytes": 0}

        try:
            item_count = self.cache_manager.size()
            return {
                "item_count": item_count,
                "size_bytes": item_count * 1024,  # 估算
                "expired_count": 0,
            }
        except Exception as e:
            logger.error(f"扫描内存缓存失败: {e}")
            return {"item_count": 0, "size_bytes": 0, "error": str(e)}

    def _scan_redis_cache(self) -> dict[str, Any]:
        """扫描Redis缓存"""
        if not self.redis_cache:
            return {"item_count": 0, "size_bytes": 0}

        try:
            item_count = self.redis_cache.size()
            return {
                "item_count": item_count,
                "size_bytes": item_count * 1024,  # 估算
                "expired_count": 0,
            }
        except Exception as e:
            logger.error(f"扫描Redis缓存失败: {e}")
            return {"item_count": 0, "size_bytes": 0, "error": str(e)}

    def _scan_disk_cache(self, cache_path: Path) -> dict[str, Any]:
        """扫描磁盘缓存"""
        if not cache_path.exists():
            return {"item_count": 0, "size_bytes": 0}

        try:
            item_count = sum(1 for _ in cache_path.rglob("*") if _.is_file())
            size_bytes = self._get_directory_size(cache_path)

            # 统计过期文件(超过24小时)
            expired_count = 0
            cutoff_time = datetime.now() - timedelta(hours=24)
            for file_path in cache_path.rglob("*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_time:
                        expired_count += 1

            return {
                "item_count": item_count,
                "size_bytes": size_bytes,
                "expired_count": expired_count,
            }
        except Exception as e:
            logger.error(f"扫描磁盘缓存失败: {e}")
            return {"item_count": 0, "size_bytes": 0, "error": str(e)}

    def _get_directory_size(self, directory: Path) -> int:
        """
        获取目录大小

        Args:
            directory: 目录路径

        Returns:
            大小(字节)
        """
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"计算目录大小失败: {e}")
        return total_size

    @staticmethod
    def _format_bytes(bytes_size: int) -> str:
        """
        格式化字节大小

        Args:
            bytes_size: 字节大小

        Returns:
            格式化字符串
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
