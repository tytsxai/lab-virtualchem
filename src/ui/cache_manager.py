"""缓存管理器"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class CacheItem:
    """缓存项"""

    def __init__(self, key: str, value: Any, ttl: int = 3600) -> None:
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # 生存时间（秒）
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl

    def access(self) -> Any:
        """访问缓存项"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }


class CacheManager:
    """缓存管理器"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: dict[str, CacheItem] = {}
        self.hit_count = 0
        self.miss_count = 0

    def get(self, key: str) -> Any | None:
        """获取缓存项"""
        if key in self.cache:
            item = self.cache[key]
            if item.is_expired():
                del self.cache[key]
                self.miss_count += 1
                logger.debug(f"缓存项过期: {key}")
                return None
            else:
                self.hit_count += 1
                logger.debug(f"缓存命中: {key}")
                return item.access()
        else:
            self.miss_count += 1
            logger.debug(f"缓存未命中: {key}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存项"""
        if ttl is None:
            ttl = self.default_ttl

        # 检查缓存大小
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = CacheItem(key, value, ttl)
        logger.debug(f"缓存设置: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"缓存删除: {key}")
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        logger.info("缓存已清空")

    def cleanup_expired(self) -> int:
        """清理过期项"""
        expired_keys = []
        for key, item in self.cache.items():
            if item.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")

        return len(expired_keys)

    def _evict_oldest(self) -> None:
        """驱逐最旧的项"""
        if not self.cache:
            return

        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        del self.cache[oldest_key]
        logger.debug(f"驱逐最旧缓存项: {oldest_key}")

    def get_statistics(self) -> dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def save_to_file(self, file_path: str) -> None:
        """保存缓存到文件"""
        try:
            cache_data = {
                "items": [item.to_dict() for item in self.cache.values()],
                "statistics": self.get_statistics(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.info(f"缓存已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def load_from_file(self, file_path: str) -> None:
        """从文件加载缓存"""
        try:
            if not Path(file_path).exists():
                logger.warning(f"缓存文件不存在: {file_path}")
                return

            with open(file_path, encoding="utf-8") as f:
                cache_data = json.load(f)

            # 加载缓存项
            for item_data in cache_data.get("items", []):
                key = item_data["key"]
                value = item_data["value"]
                ttl = item_data.get("ttl", self.default_ttl)
                self.set(key, value, ttl)

            logger.info(f"缓存已从文件加载: {file_path}")
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")


class SceneCacheManager(CacheManager):
    """场景缓存管理器"""

    def __init__(self) -> None:
        super().__init__(max_size=100, default_ttl=7200)  # 2小时

    def cache_scene_state(self, scene_id: str, state: dict[str, Any]) -> None:
        """缓存场景状态"""
        key = f"scene_state:{scene_id}"
        self.set(key, state, ttl=3600)  # 1小时

    def get_scene_state(self, scene_id: str) -> dict[str, Any] | None:
        """获取场景状态"""
        key = f"scene_state:{scene_id}"
        return self.get(key)

    def cache_validation_result(self, check_id: str, result: dict[str, Any]) -> None:
        """缓存验证结果"""
        key = f"validation:{check_id}"
        self.set(key, result, ttl=1800)  # 30分钟

    def get_validation_result(self, check_id: str) -> dict[str, Any] | None:
        """获取验证结果"""
        key = f"validation:{check_id}"
        return self.get(key)


# 全局缓存管理器实例
cache_manager = CacheManager()
scene_cache_manager = SceneCacheManager()
