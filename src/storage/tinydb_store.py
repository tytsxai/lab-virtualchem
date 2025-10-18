"""TinyDB存储实现

使用TinyDB替代纯JSON存储,提供更高效的查询和索引功能。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tinydb import Query, TinyDB, where
    from tinydb.middlewares import CachingMiddleware
    from tinydb.storages import JSONStorage

    TINYDB_AVAILABLE = True
except ImportError:
    TINYDB_AVAILABLE = False
    TinyDB = None
    Query = None
    where = None

import contextlib

from ..interfaces.storage import StorageInterface
from ..models.user_record import UserRecord

logger = logging.getLogger(__name__)


class TinyDBStore(StorageInterface):
    """TinyDB存储实现"""

    def __init__(self, db_path: Path) -> None:
        """初始化TinyDB存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.available = TINYDB_AVAILABLE

        if not self.available:
            logger.warning("TinyDB未安装,将回退到JSON存储. 安装: pip install tinydb")
            self.db = None
            self.records_table = None
            self._fallback_data: dict[str, Any] = {"records": []}
        else:
            # 确保目录存在
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用缓存中间件提升性能
            self.db = TinyDB(db_path, storage=CachingMiddleware(JSONStorage))
            self.records_table = self.db.table("records")
            logger.info(f"TinyDB已初始化: {db_path}")

    def save(self, record_id: str, data: UserRecord) -> None:
        """保存记录

        Args:
            record_id: 记录ID
            data: 用户记录对象
        """
        if not self.available:
            self._fallback_save(record_id, data)
            return

        record_dict = data.model_dump()
        record_dict["id"] = record_id
        record_dict["updated_at"] = datetime.now().isoformat()

        # 检查是否存在
        Record = Query()
        existing = self.records_table.get(Record.id == record_id)

        if existing:
            # 更新
            self.records_table.update(record_dict, Record.id == record_id)
            logger.debug(f"更新记录: {record_id}")
        else:
            # 插入
            self.records_table.insert(record_dict)
            logger.debug(f"插入记录: {record_id}")

    def load(self, record_id: str) -> UserRecord | None:
        """加载记录

        Args:
            record_id: 记录ID

        Returns:
            用户记录对象,不存在返回None
        """
        if not self.available:
            return self._fallback_load(record_id)

        Record = Query()
        result = self.records_table.get(Record.id == record_id)

        if not result:
            return None

        # 移除内部字段
        result.pop("id", None)
        result.pop("updated_at", None)

        try:
            return UserRecord(**result)
        except Exception as e:
            logger.error(f"反序列化记录失败 {record_id}: {e}")
            return None

    def delete(self, record_id: str) -> bool:
        """删除记录

        Args:
            record_id: 记录ID

        Returns:
            是否成功删除
        """
        if not self.available:
            return self._fallback_delete(record_id)

        Record = Query()
        removed = self.records_table.remove(Record.id == record_id)

        success = len(removed) > 0
        if success:
            logger.info(f"删除记录: {record_id}")
        return success

    def list_all(self) -> list[str]:
        """列出所有记录ID

        Returns:
            记录ID列表
        """
        if not self.available:
            return self._fallback_list_all()

        all_records = self.records_table.all()
        return [r["id"] for r in all_records if "id" in r]

    def exists(self, record_id: str) -> bool:
        """检查记录是否存在

        Args:
            record_id: 记录ID

        Returns:
            是否存在
        """
        if not self.available:
            return self._fallback_exists(record_id)

        Record = Query()
        return self.records_table.contains(Record.id == record_id)

    # TinyDB特有的高级查询方法

    def search(self, **criteria: Any) -> list[UserRecord]:
        """搜索记录

        Args:
            **criteria: 搜索条件 (字段名=值)

        Returns:
            匹配的记录列表
        """
        if not self.available:
            logger.warning("TinyDB不可用,搜索功能受限")
            return []

        Record = Query()

        # 构建查询条件
        query = None
        for key, value in criteria.items():
            condition = Record[key] == value
            query = condition if query is None else (query & condition)

        results = self.records_table.all() if query is None else self.records_table.search(query)

        # 转换为UserRecord对象
        records = []
        for r in results:
            r.pop("id", None)
            r.pop("updated_at", None)
            try:
                records.append(UserRecord(**r))
            except Exception as e:
                logger.error(f"反序列化搜索结果失败: {e}")

        return records

    def search_by_student(self, student_id: str) -> list[UserRecord]:
        """按学生ID搜索记录"""
        return self.search(student_id=student_id)

    def search_by_experiment(self, experiment_id: str) -> list[UserRecord]:
        """按实验ID搜索记录"""
        return self.search(experiment_id=experiment_id)

    def search_by_date_range(self, start_date: str, end_date: str) -> list[UserRecord]:
        """按日期范围搜索

        Args:
            start_date: 开始日期 (ISO格式)
            end_date: 结束日期 (ISO格式)

        Returns:
            匹配的记录列表
        """
        if not self.available:
            return []

        Record = Query()
        results = self.records_table.search((Record.start_time >= start_date) & (Record.start_time <= end_date))

        records = []
        for r in results:
            r.pop("id", None)
            r.pop("updated_at", None)
            with contextlib.suppress(Exception):
                records.append(UserRecord(**r))

        return records

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计数据字典
        """
        if not self.available:
            return {"total_records": len(self._fallback_data.get("records", []))}

        all_records = self.records_table.all()

        # 计算统计
        total = len(all_records)
        scores = [r.get("score", 0) for r in all_records if "score" in r]

        stats = {
            "total_records": total,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        }

        # 按实验分组统计
        experiments: dict[str, int] = {}
        for r in all_records:
            exp_id = r.get("experiment_id", "unknown")
            experiments[exp_id] = experiments.get(exp_id, 0) + 1

        stats["experiments"] = experiments

        return stats

    def clear_all(self) -> None:
        """清空所有记录(危险操作)"""
        if not self.available:
            self._fallback_data = {"records": []}
            self._save_fallback()
            return

        self.records_table.truncate()
        logger.warning("已清空所有记录")

    def close(self) -> None:
        """关闭数据库连接"""
        if self.available and self.db:
            self.db.close()
            logger.info("TinyDB已关闭")

    # Fallback方法 (当TinyDB不可用时)

    def _fallback_save(self, record_id: str, data: UserRecord) -> None:
        """Fallback保存方法"""
        records = self._fallback_data.get("records", [])

        # 查找是否存在
        existing_idx = None
        for i, r in enumerate(records):
            if r.get("id") == record_id:
                existing_idx = i
                break

        record_dict = data.model_dump()
        record_dict["id"] = record_id

        if existing_idx is not None:
            records[existing_idx] = record_dict
        else:
            records.append(record_dict)

        self._fallback_data["records"] = records
        self._save_fallback()

    def _fallback_load(self, record_id: str) -> UserRecord | None:
        """Fallback加载方法"""
        self._load_fallback()
        records = self._fallback_data.get("records", [])

        for r in records:
            if r.get("id") == record_id:
                r_copy = r.copy()
                r_copy.pop("id", None)
                try:
                    return UserRecord(**r_copy)
                except Exception:
                    return None
        return None

    def _fallback_delete(self, record_id: str) -> bool:
        """Fallback删除方法"""
        self._load_fallback()
        records = self._fallback_data.get("records", [])

        new_records = [r for r in records if r.get("id") != record_id]
        removed = len(records) != len(new_records)

        self._fallback_data["records"] = new_records
        if removed:
            self._save_fallback()

        return removed

    def _fallback_list_all(self) -> list[str]:
        """Fallback列表方法"""
        self._load_fallback()
        records = self._fallback_data.get("records", [])
        return [r["id"] for r in records if "id" in r]

    def _fallback_exists(self, record_id: str) -> bool:
        """Fallback存在检查"""
        self._load_fallback()
        records = self._fallback_data.get("records", [])
        return any(r.get("id") == record_id for r in records)

    def _load_fallback(self) -> None:
        """加载fallback数据"""
        if self.db_path.exists():
            try:
                with open(self.db_path, encoding="utf-8") as f:
                    self._fallback_data = json.load(f)
            except Exception as e:
                logger.error(f"加载fallback数据失败: {e}")
                self._fallback_data = {"records": []}
        else:
            self._fallback_data = {"records": []}

    def _save_fallback(self) -> None:
        """保存fallback数据"""
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self._fallback_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存fallback数据失败: {e}")
