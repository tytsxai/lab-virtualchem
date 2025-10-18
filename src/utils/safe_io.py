"""安全的文件I/O操作

提供带错误处理的文件读写操作
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

from .enhanced_error_handler import (
    ErrorSeverity,
    handle_errors,
)

logger = logging.getLogger(__name__)


class SafeFileIO:
    """安全的文件I/O操作类"""

    @staticmethod
    @handle_errors(
        context="读取文件",
        user_message="无法读取文件",
        severity=ErrorSeverity.ERROR,
        default_return=None,
    )
    def read_file(
        file_path: str | Path,
        encoding: str = "utf-8",
        default: str | None = None,
    ) -> str | None:
        """安全地读取文件

        Args:
            file_path: 文件路径
            encoding: 编码格式
            default: 出错时的默认值

        Returns:
            文件内容，失败返回默认值
        """
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"文件不存在: {path}")
            if default is not None:
                return default
            raise FileNotFoundError(f"文件不存在: {path}")

        try:
            with open(path, encoding=encoding) as f:
                content = f.read()
            logger.debug(f"成功读取文件: {path}")
            return content
        except PermissionError:
            raise PermissionError(f"没有权限读取文件: {path}")
        except UnicodeDecodeError as e:
            raise ValueError(f"文件编码错误，请尝试使用不同的编码: {e}")

    @staticmethod
    @handle_errors(
        context="写入文件",
        user_message="无法写入文件",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def write_file(
        file_path: str | Path,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
        backup: bool = False,
    ) -> bool:
        """安全地写入文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码格式
            create_dirs: 是否自动创建目录
            backup: 是否备份旧文件

        Returns:
            是否成功
        """
        path = Path(file_path)

        # 创建目录
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # 备份旧文件
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + ".backup")
            try:
                shutil.copy2(path, backup_path)
                logger.debug(f"已备份文件到: {backup_path}")
            except Exception as e:
                logger.warning(f"备份文件失败: {e}")

        # 先写入临时文件，然后原子性替换
        temp_file = None
        try:
            # 在同一目录下创建临时文件
            with tempfile.NamedTemporaryFile(
                mode="w", encoding=encoding, dir=path.parent, delete=False, suffix=".tmp"
            ) as f:
                f.write(content)
                temp_file = Path(f.name)

            # 原子性替换
            shutil.move(str(temp_file), str(path))
            logger.debug(f"成功写入文件: {path}")
            return True

        except PermissionError:
            if temp_file and temp_file.exists():
                temp_file.unlink()
            raise PermissionError(f"没有权限写入文件: {path}")
        except OSError as e:
            if temp_file and temp_file.exists():
                temp_file.unlink()
            if "No space left" in str(e):
                raise OSError("磁盘空间不足")
            raise

    @staticmethod
    @handle_errors(
        context="读取JSON文件",
        user_message="无法读取JSON文件",
        severity=ErrorSeverity.ERROR,
        default_return=None,
    )
    def read_json(
        file_path: str | Path,
        default: dict | None = None,
    ) -> dict | None:
        """安全地读取JSON文件

        Args:
            file_path: 文件路径
            default: 出错时的默认值

        Returns:
            JSON数据，失败返回默认值
        """
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"JSON文件不存在: {path}")
            if default is not None:
                return default
            raise FileNotFoundError(f"JSON文件不存在: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"成功读取JSON: {path}")
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误 (行{e.lineno}, 列{e.colno}): {e.msg}")
        except PermissionError:
            raise PermissionError(f"没有权限读取文件: {path}")

    @staticmethod
    @handle_errors(
        context="写入JSON文件",
        user_message="无法写入JSON文件",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def write_json(
        file_path: str | Path,
        data: dict | list,
        indent: int = 2,
        create_dirs: bool = True,
        backup: bool = False,
    ) -> bool:
        """安全地写入JSON文件

        Args:
            file_path: 文件路径
            data: JSON数据
            indent: 缩进空格数
            create_dirs: 是否自动创建目录
            backup: 是否备份旧文件

        Returns:
            是否成功
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return SafeFileIO.write_file(file_path, content, create_dirs=create_dirs, backup=backup)
        except TypeError as e:
            raise ValueError(f"无法序列化数据为JSON: {e}")

    @staticmethod
    @handle_errors(
        context="复制文件",
        user_message="无法复制文件",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def copy_file(
        src: str | Path,
        dst: str | Path,
        create_dirs: bool = True,
        overwrite: bool = True,
    ) -> bool:
        """安全地复制文件

        Args:
            src: 源文件路径
            dst: 目标文件路径
            create_dirs: 是否自动创建目录
            overwrite: 是否覆盖已存在的文件

        Returns:
            是否成功
        """
        src_path = Path(src)
        dst_path = Path(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src_path}")

        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在: {dst_path}")

        if create_dirs:
            dst_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src_path, dst_path)
            logger.debug(f"成功复制文件: {src_path} -> {dst_path}")
            return True
        except PermissionError:
            raise PermissionError(f"没有权限复制文件到: {dst_path}")

    @staticmethod
    @handle_errors(
        context="删除文件",
        user_message="无法删除文件",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def delete_file(
        file_path: str | Path,
        missing_ok: bool = True,
    ) -> bool:
        """安全地删除文件

        Args:
            file_path: 文件路径
            missing_ok: 文件不存在时是否报错

        Returns:
            是否成功
        """
        path = Path(file_path)

        if not path.exists():
            if missing_ok:
                logger.debug(f"文件不存在（忽略）: {path}")
                return True
            raise FileNotFoundError(f"文件不存在: {path}")

        try:
            path.unlink()
            logger.debug(f"成功删除文件: {path}")
            return True
        except PermissionError:
            raise PermissionError(f"没有权限删除文件: {path}")
        except IsADirectoryError:
            raise IsADirectoryError(f"这是一个目录，不是文件: {path}")

    @staticmethod
    @handle_errors(
        context="创建目录",
        user_message="无法创建目录",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def create_directory(
        dir_path: str | Path,
        exist_ok: bool = True,
    ) -> bool:
        """安全地创建目录

        Args:
            dir_path: 目录路径
            exist_ok: 目录已存在时是否报错

        Returns:
            是否成功
        """
        path = Path(dir_path)

        try:
            path.mkdir(parents=True, exist_ok=exist_ok)
            logger.debug(f"成功创建目录: {path}")
            return True
        except PermissionError:
            raise PermissionError(f"没有权限创建目录: {path}")
        except FileExistsError:
            if not exist_ok:
                raise FileExistsError(f"目录已存在: {path}")
            return True

    @staticmethod
    @handle_errors(
        context="检查磁盘空间",
        user_message="无法检查磁盘空间",
        severity=ErrorSeverity.WARNING,
        default_return=None,
    )
    def check_disk_space(
        path: str | Path,
        required_mb: int = 100,
    ) -> bool:
        """检查磁盘空间是否足够

        Args:
            path: 要检查的路径
            required_mb: 需要的空间（MB）

        Returns:
            是否有足够空间
        """
        import shutil as sh

        path = Path(path)
        # 确保路径存在
        if not path.exists():
            path = path.parent

        stat = sh.disk_usage(path)
        free_mb = stat.free / (1024 * 1024)

        if free_mb < required_mb:
            logger.warning(f"磁盘空间不足: 需要{required_mb}MB，可用{free_mb:.1f}MB")
            return False

        return True

    @staticmethod
    def read_with_retry(
        file_path: str | Path,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        **kwargs,
    ) -> str | None:
        """带重试的文件读取

        Args:
            file_path: 文件路径
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            **kwargs: 传递给read_file的其他参数

        Returns:
            文件内容
        """

        last_error = None
        for attempt in range(max_retries):
            try:
                return SafeFileIO.read_file(file_path, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"读取文件失败，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)

        # 所有重试都失败
        if last_error:
            raise last_error
        return None


# 便捷函数
def safe_read_text(file_path: str | Path, default: str = "") -> str:
    """安全读取文本文件"""
    result = SafeFileIO.read_file(file_path, default=default)
    return result if result is not None else default


def safe_read_json(file_path: str | Path, default: dict = None) -> dict:
    """安全读取JSON文件"""
    if default is None:
        default = {}
    result = SafeFileIO.read_json(file_path, default=default)
    return result if result is not None else default


def safe_write_text(file_path: str | Path, content: str, **kwargs) -> bool:
    """安全写入文本文件"""
    return SafeFileIO.write_file(file_path, content, **kwargs)


def safe_write_json(file_path: str | Path, data: dict | list, **kwargs) -> bool:
    """安全写入JSON文件"""
    return SafeFileIO.write_json(file_path, data, **kwargs)


__all__ = [
    "SafeFileIO",
    "safe_read_text",
    "safe_read_json",
    "safe_write_text",
    "safe_write_json",
]
