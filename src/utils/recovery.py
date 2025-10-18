"""
数据恢复和备份工具
提供自动备份和恢复功能
"""

import hashlib
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from .error_handler import safe_execute

logger = logging.getLogger(__name__)


class RecoveryManager:
    """数据恢复管理器(增强版)"""

    def __init__(self, backup_dir: str = "backups"):
        """初始化恢复管理器

        Args:
            backup_dir: 备份目录路径
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 备份元数据文件
        self.metadata_file = self.backup_dir / "backup_metadata.json"

        # 线程锁
        self._lock = Lock()

        # 备份策略配置
        self.max_backups_per_name = 10  # 每个备份名称保留的最大数量
        self.backup_retention_days = 30  # 备份保留天数

        # 加载元数据
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """加载备份元数据"""
        if not self.metadata_file.exists():
            return {"backups": []}

        try:
            with open(self.metadata_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载备份元数据失败: {e}")
            return {"backups": []}

    def _save_metadata(self) -> None:
        """保存备份元数据"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存备份元数据失败: {e}")

    def _calculate_checksum(self, filepath: Path) -> str:
        """计算文件校验和

        Args:
            filepath: 文件路径

        Returns:
            MD5校验和
        """
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算校验和失败: {e}")
            return ""

    @safe_execute(context="创建备份", default_return=False)
    def create_backup(self, data: dict[str, Any], backup_name: str) -> bool:
        """创建数据备份(带校验和和元数据)

        Args:
            data: 要备份的数据
            backup_name: 备份名称

        Returns:
            是否成功
        """
        if not backup_name or not backup_name.strip():
            raise ValidationError(field="backup_name", message="备份名称不能为空")

        if not isinstance(data, dict):
            raise ValidationError(field="data", message="备份数据必须是字典类型")

        with self._lock:
            # 使用微秒级时间戳避免冲突
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_file = self.backup_dir / f"{backup_name}_{timestamp}.json"
            temp_file = backup_file.with_suffix(".tmp")

            # 先写入临时文件
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

            # 原子性重命名
            try:
                temp_file.replace(backup_file)
            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

            # 计算校验和
            checksum = self._calculate_checksum(backup_file)

            # 更新元数据
            backup_info = {
                "name": backup_name,
                "filename": backup_file.name,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "size_bytes": backup_file.stat().st_size,
                "checksum": checksum,
            }

            self._metadata["backups"].append(backup_info)
            self._save_metadata()

            # 清理旧备份
            self._cleanup_old_backups(backup_name)

            logger.info(f"备份创建成功: {backup_file} (校验和: {checksum[:8]}...)")
            return True

    def restore_latest(self, backup_name: str) -> dict[str, Any] | None:
        """恢复最新备份

        Args:
            backup_name: 备份名称前缀

        Returns:
            恢复的数据,失败返回None
        """
        try:
            # 查找所有匹配的备份文件
            backup_files = list(self.backup_dir.glob(f"{backup_name}_*.json"))

            if not backup_files:
                logger.warning(f"未找到备份: {backup_name}")
                return None

            # 获取最新的备份
            latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)

            with open(latest_backup, encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"成功恢复备份: {latest_backup}")
            return data

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return None

    def list_backups(self, backup_name: str | None = None) -> list:
        """列出所有备份

        Args:
            backup_name: 可选的备份名称前缀

        Returns:
            备份文件列表
        """
        try:
            pattern = f"{backup_name}_*.json" if backup_name else "*.json"

            backup_files = list(self.backup_dir.glob(pattern))

            # 排除元数据文件
            backup_files = [f for f in backup_files if f.name != "backup_metadata.json"]

            # 按修改时间倒序排列
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            return [
                {
                    "file": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                }
                for f in backup_files
            ]

        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []

    def _cleanup_old_backups(self, backup_name: str) -> None:
        """清理旧备份

        Args:
            backup_name: 备份名称
        """
        try:
            # 获取该名称的所有备份
            name_backups = [b for b in self._metadata["backups"] if b["name"] == backup_name]

            # 按时间排序
            name_backups.sort(key=lambda x: x["created_at"], reverse=True)

            # 删除超过数量限制的备份
            if len(name_backups) > self.max_backups_per_name:
                for old_backup in name_backups[self.max_backups_per_name :]:
                    backup_path = self.backup_dir / old_backup["filename"]
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"删除超出数量限制的备份: {backup_path}")

                    # 从元数据中移除
                    self._metadata["backups"].remove(old_backup)

            # 删除过期的备份
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
            expired_backups = [
                b for b in self._metadata["backups"] if datetime.fromisoformat(b["created_at"]) < cutoff_date
            ]

            for expired in expired_backups:
                backup_path = self.backup_dir / expired["filename"]
                if backup_path.exists():
                    backup_path.unlink()
                    logger.info(f"删除过期备份: {backup_path}")

                self._metadata["backups"].remove(expired)

            if expired_backups:
                self._save_metadata()

        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")

    def delete_old_backups(self, backup_name: str, keep_count: int = 5) -> int:
        """删除旧备份,保留最新的N个

        Args:
            backup_name: 备份名称前缀
            keep_count: 保留数量

        Returns:
            删除的备份数量
        """
        with self._lock:
            try:
                backup_files = list(self.backup_dir.glob(f"{backup_name}_*.json"))

                if len(backup_files) <= keep_count:
                    return 0

                # 按修改时间排序
                backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

                # 删除旧备份
                deleted_count = 0
                for old_backup in backup_files[keep_count:]:
                    try:
                        old_backup.unlink()
                        deleted_count += 1
                        logger.info(f"删除旧备份: {old_backup}")

                        # 从元数据中移除
                        self._metadata["backups"] = [
                            b for b in self._metadata["backups"] if b["filename"] != old_backup.name
                        ]
                    except Exception as e:
                        logger.error(f"删除备份文件失败 {old_backup}: {e}")

                if deleted_count > 0:
                    self._save_metadata()

                return deleted_count

            except Exception as e:
                logger.error(f"删除旧备份失败: {e}")
                return 0

    def export_backup(self, backup_name: str, export_path: str) -> bool:
        """导出备份到指定位置

        Args:
            backup_name: 备份名称前缀
            export_path: 导出路径

        Returns:
            是否成功
        """
        try:
            backup_files = list(self.backup_dir.glob(f"{backup_name}_*.json"))

            if not backup_files:
                logger.warning(f"未找到备份: {backup_name}")
                return False

            # 获取最新备份
            latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)

            # 复制到导出路径
            shutil.copy2(latest_backup, export_path)

            logger.info(f"备份导出成功: {export_path}")
            return True

        except Exception as e:
            logger.error(f"导出备份失败: {e}")
            return False


class AutoSave:
    """自动保存管理器"""

    def __init__(self, save_interval: int = 300):
        """初始化自动保存

        Args:
            save_interval: 自动保存间隔(秒)
        """
        self.save_interval = save_interval
        self.last_save_time = datetime.now()
        self.unsaved_changes = False

    def mark_changed(self):
        """标记有未保存的更改"""
        self.unsaved_changes = True

    def should_save(self) -> bool:
        """检查是否应该保存

        Returns:
            是否需要保存
        """
        if not self.unsaved_changes:
            return False

        elapsed = (datetime.now() - self.last_save_time).total_seconds()
        return elapsed >= self.save_interval

    def mark_saved(self):
        """标记已保存"""
        self.unsaved_changes = False
        self.last_save_time = datetime.now()

    def has_unsaved_changes(self) -> bool:
        """检查是否有未保存的更改

        Returns:
            是否有未保存更改
        """
        return self.unsaved_changes
