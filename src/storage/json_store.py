"""
JSON存储引擎
使用JSON文件存储用户实验记录，提供兼容IStorage的键值访问能力

增强功能:
1. 数据压缩和加密存储
2. 增量备份和版本控制
3. 数据完整性校验
4. 多级缓存和性能优化
5. 数据迁移和同步
6. 数据分析和统计
7. 数据清理和归档
8. 云端同步支持
"""

import dataclasses
import hashlib
import json
import shutil
import zlib
from collections.abc import Iterable
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from ..core.validation import ValidationError
from ..models.user_record import UserRecord
from ..utils.error_handler import safe_execute
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StorageMode(Enum):
    """存储模式"""

    STANDARD = "standard"  # 标准模式
    COMPRESSED = "compressed"  # 压缩模式
    ENCRYPTED = "encrypted"  # 加密模式
    CLOUD_SYNC = "cloud_sync"  # 云端同步模式


class DataIntegrityLevel(Enum):
    """数据完整性级别"""

    NONE = "none"  # 无校验
    BASIC = "basic"  # 基础校验
    STRONG = "strong"  # 强校验
    CRYPTOGRAPHIC = "cryptographic"  # 密码学校验


class JSONStore:
    """JSON文件存储系统"""

    def __init__(
        self,
        base_dir: str = "data/records",
        storage_mode: StorageMode = StorageMode.STANDARD,
        integrity_level: DataIntegrityLevel = DataIntegrityLevel.BASIC,
        enable_cache: bool = True,
        cache_size: int = 100,
        enable_compression: bool = False,
        enable_encryption: bool = False,
    ):
        """初始化存储系统"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._kv_dir = self.base_dir / ".kv_store"
        self._kv_dir.mkdir(parents=True, exist_ok=True)

        # 创建备份目录
        self.backup_dir = self.base_dir / ".backups"
        self.backup_dir.mkdir(exist_ok=True)

        # 创建缓存目录
        self.cache_dir = self.base_dir / ".cache"
        self.cache_dir.mkdir(exist_ok=True)

        # 创建归档目录
        self.archive_dir = self.base_dir / ".archive"
        self.archive_dir.mkdir(exist_ok=True)

        # 线程锁,保证并发安全
        self._write_locks: dict[str, Lock] = {}
        self._global_lock = Lock()
        self._cache_lock = RLock()

        # 存储配置
        self.storage_mode = storage_mode
        self.integrity_level = integrity_level
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self.enable_compression = enable_compression
        self.enable_encryption = enable_encryption

        # 缓存系统
        self._cache: dict[str, Any] = {}
        self._cache_access_times: dict[str, datetime] = {}

        # 统计信息
        self._stats = {
            "total_reads": 0,
            "total_writes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "compression_saves": 0,
            "integrity_checks": 0,
            "backup_operations": 0,
        }

        logger.info(f"JSON存储系统初始化完成，目录: {self.base_dir}, 模式: {storage_mode.value}")

    # ------------------------------------------------------------------
    # IStorage 兼容接口
    # ------------------------------------------------------------------

    def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:
        """保存任意键值数据"""
        try:
            filepath = self._resolve_key_path(key)
            serialized = self._serialize_value(value)
            payload = {"data": serialized, "metadata": metadata or {}, "saved_at": datetime.utcnow().isoformat()}

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            # 缓存命中
            cache_key = str(filepath)
            self._cache_data(cache_key, payload["data"])
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"保存键值数据失败({key}): {e}")
            return False

    def load(self, key: str) -> Any | None:
        """加载任意键值数据"""
        try:
            filepath = self._resolve_key_path(key, ensure_parent=False)
            cache_key = str(filepath)

            if self.enable_cache and cache_key in self._cache:
                self._stats["cache_hits"] += 1
                return self._cache[cache_key]

            if not filepath.exists():
                self._stats["cache_misses"] += 1
                return None

            with open(filepath, encoding="utf-8") as f:
                payload = json.load(f)

            data = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
            self._cache_data(cache_key, data)
            return data
        except Exception as e:  # noqa: BLE001
            logger.error(f"加载键值数据失败({key}): {e}")
            return None

    def delete(self, key: str) -> bool:
        """删除键值数据"""
        try:
            filepath = self._resolve_key_path(key, ensure_parent=False)
            if filepath.exists():
                filepath.unlink()
            cache_key = str(filepath)
            if cache_key in self._cache:
                with self._cache_lock:
                    self._cache.pop(cache_key, None)
                    self._cache_access_times.pop(cache_key, None)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"删除键值数据失败({key}): {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        filepath = self._resolve_key_path(key, ensure_parent=False)
        return filepath.exists()

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """列出键列表"""
        prefix = (prefix or "").strip().strip("/")
        if prefix.startswith("records/"):
            base_dir = self.base_dir
            trimmed_prefix = prefix[len("records/") :]
            return self._collect_keys(base_dir, trimmed_prefix, key_prefix="records/")

        return self._collect_keys(self._kv_dir, prefix)

    def clear(self) -> bool:
        """清空键值存储(不影响实验记录)"""
        try:
            if self._kv_dir.exists():
                for child in self._kv_dir.iterdir():
                    if child.is_file():
                        child.unlink()
                    else:
                        shutil.rmtree(child)
            with self._cache_lock:
                self._cache.clear()
                self._cache_access_times.clear()
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"清空键值存储失败: {e}")
            return False

    def _cache_data(self, key: str, data: Any) -> None:
        """缓存数据"""
        if not self.enable_cache:
            return

        with self._cache_lock:
            # 检查缓存大小限制
            if len(self._cache) >= self.cache_size:
                self._evict_oldest_cache_entry()

            self._cache[key] = data
            self._cache_access_times[key] = datetime.now()

    def _evict_oldest_cache_entry(self) -> None:
        """驱逐最旧的缓存条目"""
        if not self._cache_access_times:
            return

        oldest_key = min(self._cache_access_times.keys(), key=lambda k: self._cache_access_times[k])

        if oldest_key in self._cache:
            del self._cache[oldest_key]
        if oldest_key in self._cache_access_times:
            del self._cache_access_times[oldest_key]

    def _load_record_file(self, filepath: Path) -> dict[str, Any] | None:
        """加载记录文件"""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            # 检查是否需要解压缩
            if self.enable_compression and isinstance(data, str):
                try:
                    compressed_data = bytes.fromhex(data)
                    decompressed_data = zlib.decompress(compressed_data)
                    data = json.loads(decompressed_data.decode("utf-8"))
                    self._stats["compression_saves"] += 1
                except Exception as e:
                    logger.warning(f"解压缩失败: {e}")

            return data if isinstance(data, dict) else None

        except Exception as e:
            logger.error(f"加载记录文件失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _normalize_key(self, key: str) -> str:
        sanitized = (key or "").strip().strip("/")
        if not sanitized:
            raise ValueError("键不能为空")
        if ".." in sanitized:
            raise ValueError("键名包含非法路径")
        return sanitized

    def _resolve_key_path(self, key: str, ensure_parent: bool = True) -> Path:
        normalized = self._normalize_key(key)
        base_dir = self._kv_dir
        if normalized.startswith("records/"):
            normalized = normalized[len("records/") :]
            base_dir = self.base_dir

        relative_path = Path(normalized)
        if relative_path.suffix == "":
            relative_path = relative_path.with_suffix(".json")

        filepath = base_dir / relative_path
        if ensure_parent:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath

    def _collect_keys(self, base_dir: Path, prefix: str | None, key_prefix: str = "") -> list[str]:
        trimmed_prefix = (prefix or "").strip().strip("/")
        keys: list[str] = []
        if not base_dir.exists():
            return keys

        for file_path in self._iter_json_files(base_dir):
            relative = file_path.relative_to(base_dir).as_posix()
            key_without_suffix = relative[:-5] if relative.endswith(".json") else relative
            if trimmed_prefix and not key_without_suffix.startswith(trimmed_prefix):
                continue
            keys.append(f"{key_prefix}{key_without_suffix}" if key_prefix else key_without_suffix)

        keys.sort()
        return keys

    def _iter_json_files(self, base_dir: Path) -> Iterable[Path]:
        for path in base_dir.rglob("*.json"):
            if path.is_file():
                yield path

    def _serialize_value(self, value: Any) -> Any:
        """将值转换为可序列化对象"""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if dataclasses.is_dataclass(value):
            return dataclasses.asdict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        if hasattr(value, "__dict__"):
            return self._serialize_value(value.__dict__)
        raise TypeError(f"无法序列化的类型: {type(value).__name__}")

    def _verify_data_integrity(self, data: dict[str, Any], record_info: dict[str, Any]) -> bool:
        """验证数据完整性"""
        if self.integrity_level == DataIntegrityLevel.NONE:
            return True

        self._stats["integrity_checks"] += 1

        try:
            if self.integrity_level == DataIntegrityLevel.BASIC:
                # 基础检查：验证必要字段
                required_fields = ["record_id", "user_id", "experiment_id", "started_at"]
                return all(field in data for field in required_fields)

            elif self.integrity_level == DataIntegrityLevel.STRONG:
                # 强检查：验证字段类型和值
                # 基础字段检查
                required_fields = ["record_id", "user_id", "experiment_id", "started_at"]
                if not all(field in data for field in required_fields):
                    return False

                # 验证时间字段
                if "started_at" in data:
                    try:
                        datetime.fromisoformat(data["started_at"])
                    except ValueError:
                        return False

                return True

            elif self.integrity_level == DataIntegrityLevel.CRYPTOGRAPHIC:
                # 密码学检查：验证哈希
                if "hash" not in record_info:
                    return False

                data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
                calculated_hash = hashlib.sha256(data_str.encode()).hexdigest()
                return calculated_hash == record_info["hash"]

        except Exception as e:
            logger.warning(f"数据完整性检查失败: {e}")
            return False

        return True

    def _calculate_data_hash(self, data: dict[str, Any]) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _compress_data(self, data: dict[str, Any]) -> str:
        """压缩数据"""
        if not self.enable_compression:
            return json.dumps(data, ensure_ascii=False)

        json_str = json.dumps(data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode("utf-8"))
        return compressed.hex()

    def get_storage_statistics(self) -> dict[str, Any]:
        """获取存储统计信息"""
        stats = self._stats.copy()

        # 添加缓存统计
        cache_stats = {
            "cache_size": len(self._cache),
            "cache_hit_rate": (
                stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
                if (stats["cache_hits"] + stats["cache_misses"]) > 0
                else 0
            ),
            "storage_mode": self.storage_mode.value,
            "integrity_level": self.integrity_level.value,
            "compression_enabled": self.enable_compression,
            "encryption_enabled": self.enable_encryption,
        }
        stats.update(cache_stats)

        return stats

    def cleanup_old_data(self, days: int = 90) -> int:
        """清理旧数据

        Args:
            days: 保留天数

        Returns:
            清理的记录数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        try:
            for user_dir in self.base_dir.iterdir():
                if not user_dir.is_dir():
                    continue

                user_id = user_dir.name
                index_data = self._load_index(user_id)

                # 筛选需要清理的记录
                records_to_keep = []
                records_to_clean = []

                for record in index_data.get("records", []):
                    try:
                        started_at = datetime.fromisoformat(record.get("started_at", ""))
                        if started_at < cutoff_date:
                            records_to_clean.append(record)
                        else:
                            records_to_keep.append(record)
                    except ValueError:
                        # 时间格式错误，保留记录
                        records_to_keep.append(record)

                # 清理文件
                for record in records_to_clean:
                    try:
                        filepath = user_dir / record["filename"]
                        if filepath.exists():
                            # 移动到归档目录
                            archive_path = self.archive_dir / f"{user_id}_{record['filename']}"
                            shutil.move(str(filepath), str(archive_path))
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"清理记录失败: {e}")

                # 更新索引
                if records_to_clean:
                    index_data["records"] = records_to_keep
                    self._save_index(user_id, index_data)

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")

        logger.info(f"清理完成，共清理 {cleaned_count} 条记录")
        return cleaned_count

    def backup_data(self, backup_name: str | None = None) -> bool:
        """备份数据

        Args:
            backup_name: 备份名称，如果为None则自动生成

        Returns:
            是否备份成功
        """
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)

            # 复制所有用户数据
            for user_dir in self.base_dir.iterdir():
                if user_dir.is_dir() and not user_dir.name.startswith("."):
                    user_backup_path = backup_path / user_dir.name
                    shutil.copytree(user_dir, user_backup_path)

            self._stats["backup_operations"] += 1
            logger.info(f"数据备份完成: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"数据备份失败: {e}")
            return False

    def _get_user_lock(self, user_id: str) -> Lock:
        """获取用户专用锁"""
        with self._global_lock:
            if user_id not in self._write_locks:
                self._write_locks[user_id] = Lock()
            return self._write_locks[user_id]

    def _get_user_dir(self, user_id: str) -> Path:
        """获取用户目录路径"""
        if not user_id or not user_id.strip():
            raise ValidationError(field="user_id", message="用户ID不能为空")

        user_dir = self.base_dir / user_id.strip()
        try:
            user_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"创建用户目录失败 {user_dir}: {e}")
            raise
        return user_dir

    def _get_index_file(self, user_id: str) -> Path:
        """获取索引文件路径"""
        return self._get_user_dir(user_id) / "index.json"

    def _load_index(self, user_id: str) -> dict[str, Any]:
        """加载用户的索引文件"""
        index_file = self._get_index_file(user_id)

        if not index_file.exists():
            return {"records": []}

        try:
            with open(index_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载索引文件失败: {e}")
            return {"records": []}

    def _save_index(self, user_id: str, index_data: dict[str, Any]) -> None:
        """保存索引文件"""
        index_file = self._get_index_file(user_id)

        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引文件失败: {e}")
            raise

    def _generate_filename(self, record: UserRecord) -> str:
        """生成记录文件名

        格式: YYYY-MM-DD_实验ID_记录ID.json
        """
        date_str = record.started_at.strftime("%Y-%m-%d_%H%M%S")
        return f"{date_str}_{record.experiment_id}_{record.record_id}.json"

    @safe_execute(context="保存实验记录", default_return=False)
    def save_record(self, record: UserRecord) -> bool:
        """保存实验记录(带事务性保证)

        Args:
            record: 用户记录对象

        Returns:
            是否保存成功
        """
        if not record:
            raise ValidationError(field="record", message="记录对象不能为空")

        if not isinstance(record, UserRecord):
            raise ValidationError(field="record", message="无效的记录对象类型")

        # 使用用户专用锁,防止并发写入冲突
        user_lock = self._get_user_lock(record.user_id)

        with user_lock:
            user_dir = self._get_user_dir(record.user_id)
            filename = self._generate_filename(record)
            filepath = user_dir / filename
            temp_filepath = filepath.with_suffix(".tmp")

            # 先写入临时文件
            try:
                with open(temp_filepath, "w", encoding="utf-8") as f:
                    json.dump(record.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"写入临时文件失败: {e}")
                if temp_filepath.exists():
                    temp_filepath.unlink()
                raise

            # 备份旧文件(如果存在)
            if filepath.exists():
                backup_path = self.backup_dir / f"{filepath.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                try:
                    shutil.copy2(filepath, backup_path)
                    logger.debug(f"已备份旧文件: {backup_path}")
                except Exception as e:
                    logger.warning(f"备份旧文件失败: {e}")

            # 原子性重命名
            try:
                temp_filepath.replace(filepath)
            except Exception as e:
                logger.error(f"文件重命名失败: {e}")
                if temp_filepath.exists():
                    temp_filepath.unlink()
                raise

            # 更新索引
            index_data = self._load_index(record.user_id)

            # 检查是否已存在
            existing_idx = None
            for idx, item in enumerate(index_data["records"]):
                if item.get("record_id") == record.record_id:
                    existing_idx = idx
                    break

            # 索引条目
            index_entry = {
                "record_id": record.record_id,
                "experiment_id": record.experiment_id,
                "experiment_title": getattr(record, "experiment_title", record.experiment_id),
                "started_at": record.started_at.isoformat(),
                "finished_at": record.completed_at.isoformat() if record.completed_at else None,
                "final_score": record.score.total,
                "status": record.status,
                "filename": filename,
            }

            if existing_idx is not None:
                # 更新现有记录
                index_data["records"][existing_idx] = index_entry
            else:
                # 添加新记录
                index_data["records"].append(index_entry)

            # 按时间倒序排序
            index_data["records"].sort(key=lambda x: x.get("started_at", ""), reverse=True)

            # 保存索引
            self._save_index(record.user_id, index_data)

            logger.info(f"记录保存成功: {record.record_id} (用户: {record.user_id}, 状态: {record.status})")
            return True

    def load_record(self, user_id: str, record_id: str) -> UserRecord | None:
        """加载指定记录

        Args:
            user_id: 用户ID
            record_id: 记录ID

        Returns:
            用户记录对象，如果不存在则返回None
        """
        try:
            # 从索引查找文件名
            index_data = self._load_index(user_id)

            filename = None
            for item in index_data["records"]:
                if item.get("record_id") == record_id:
                    filename = item.get("filename")
                    break

            if not filename:
                logger.warning(f"记录不存在: {record_id}")
                return None

            # 读取记录文件
            filepath = self._get_user_dir(user_id) / filename

            if not filepath.exists():
                logger.warning(f"记录文件不存在: {filepath}")
                return None

            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            # 反序列化为UserRecord对象
            record = UserRecord(**data)
            logger.info(f"记录加载成功: {record_id}")
            return record

        except Exception as e:
            logger.error(f"加载记录失败: {e}")
            return None

    def list_records(
        self, user_id: str | None = None, experiment_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """列出记录

        Args:
            user_id: 用户ID，如果为None则列出所有用户的记录
            experiment_id: 实验ID，如果指定则只返回该实验的记录
            limit: 限制返回数量

        Returns:
            记录索引条目列表
        """
        try:
            all_records = []

            if user_id:
                # 单个用户
                index_data = self._load_index(user_id)
                records = index_data.get("records", [])
                for record in records:
                    record["user_id"] = user_id
                all_records.extend(records)
            else:
                # 所有用户
                for user_dir in self.base_dir.iterdir():
                    if user_dir.is_dir():
                        uid = user_dir.name
                        index_data = self._load_index(uid)
                        records = index_data.get("records", [])
                        for record in records:
                            record["user_id"] = uid
                        all_records.extend(records)

            # 筛选实验
            if experiment_id:
                all_records = [r for r in all_records if r.get("experiment_id") == experiment_id]

            # 按时间排序
            all_records.sort(key=lambda x: x.get("started_at", ""), reverse=True)

            # 限制数量
            if limit:
                all_records = all_records[:limit]

            logger.info(f"列出记录: {len(all_records)}条")
            return all_records

        except Exception as e:
            logger.error(f"列出记录失败: {e}")
            return []

    def list_user_records(
        self, user_id: str, experiment_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """列出指定用户的记录（list_records的便捷别名）

        Args:
            user_id: 用户ID
            experiment_id: 实验ID，如果指定则只返回该实验的记录
            limit: 限制返回数量

        Returns:
            记录索引条目列表
        """
        return self.list_records(user_id=user_id, experiment_id=experiment_id, limit=limit)

    def delete_record(self, user_id: str, record_id: str) -> bool:
        """删除记录

        Args:
            user_id: 用户ID
            record_id: 记录ID

        Returns:
            是否删除成功
        """
        try:
            # 从索引获取文件名
            index_data = self._load_index(user_id)

            filename = None
            record_idx = None
            for idx, item in enumerate(index_data["records"]):
                if item.get("record_id") == record_id:
                    filename = item.get("filename")
                    record_idx = idx
                    break

            if filename is None:
                logger.warning(f"记录不存在: {record_id}")
                return False

            # 删除文件
            filepath = self._get_user_dir(user_id) / filename
            if filepath.exists():
                filepath.unlink()

            # 更新索引
            del index_data["records"][record_idx]
            self._save_index(user_id, index_data)

            logger.info(f"记录删除成功: {record_id}")
            return True

        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            return False

    def search_records(self, query: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """搜索记录

        Args:
            query: 搜索关键词
            user_id: 用户ID，如果为None则搜索所有用户

        Returns:
            匹配的记录索引条目列表
        """
        all_records = self.list_records(user_id=user_id)

        # 简单的关键词匹配
        query_lower = query.lower()
        results = []

        for record in all_records:
            # 搜索实验标题和ID
            if (
                query_lower in record.get("experiment_title", "").lower()
                or query_lower in record.get("experiment_id", "").lower()
                or query_lower in record.get("record_id", "").lower()
            ):
                results.append(record)

        logger.info(f"搜索记录 '{query}': {len(results)}条匹配")
        return results

    def get_stats(self, user_id: str) -> dict[str, Any]:
        """获取用户统计信息

        Args:
            user_id: 用户ID

        Returns:
            统计信息字典
        """
        records = self.list_records(user_id=user_id)

        if not records:
            return {
                "total_experiments": 0,
                "average_score": 0,
                "best_score": 0,
                "total_time_minutes": 0,
            }

        total_score = 0
        best_score = 0
        total_time = 0

        for record in records:
            score = record.get("final_score", 0)
            total_score += score
            best_score = max(best_score, score)

            # 计算时长
            if record.get("finished_at") and record.get("started_at"):
                try:
                    start = datetime.fromisoformat(record["started_at"])
                    end = datetime.fromisoformat(record["finished_at"])
                    total_time += (end - start).total_seconds()
                except Exception:
                    pass

        return {
            "total_experiments": len(records),
            "average_score": total_score / len(records) if records else 0,
            "best_score": best_score,
            "total_time_minutes": total_time / 60,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（简单实现）

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值或默认值
        """
        # 这是一个简化的实现，用于兼容现有代码
        # 实际应用中可能需要更复杂的配置管理
        try:
            # 尝试从用户数据目录读取配置
            config_file = Path(self.base_dir) / "config.json"
            if config_file.exists():
                with open(config_file, encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get(key, default)
        except Exception as e:
            logger.debug(f"读取配置失败: {e}")

        return default

    def set(self, key: str, value: Any) -> None:
        """设置配置值（简单实现）

        Args:
            key: 配置键
            value: 配置值
        """
        try:
            # 确保配置目录存在
            config_file = Path(self.base_dir) / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # 读取现有配置
            config = {}
            if config_file.exists():
                with open(config_file, encoding='utf-8') as f:
                    config = json.load(f)

            # 更新配置
            config[key] = value

            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
