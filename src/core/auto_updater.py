"""
自动更新系统
检查、下载和安装应用更新
"""

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from urllib.parse import urljoin

from .. import __version__ as APP_VERSION

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """版本信息"""
    version: str
    build_number: int
    release_date: str
    download_url: str
    checksum: str
    size_bytes: int
    changelog: str = ""
    is_critical: bool = False  # 是否为关键更新


class AutoUpdater:
    """自动更新器

    特性：
    - 版本检查
    - 增量下载
    - 完整性校验
    - 自动安装
    - 回滚支持
    """

    def __init__(
        self,
        current_version: Optional[str] = None,
        update_url: str = "https://api.virtualchemlab.com/updates",
        check_interval: int = 86400  # 24小时
    ):
        """初始化自动更新器

        Args:
            current_version: 当前版本
            update_url: 更新服务器URL
            check_interval: 检查间隔（秒）
        """
        self.current_version = current_version or APP_VERSION
        self.update_url = update_url
        self.check_interval = check_interval

        # 更新信息
        self.latest_version: Optional[VersionInfo] = None
        self.last_check_time: Optional[datetime] = None

        # 下载进度回调
        self.progress_callback: Optional[Callable[[int, int], None]] = None

        # 平台信息
        self.platform = self._detect_platform()

        # 临时目录
        self.temp_dir = Path(tempfile.gettempdir()) / 'virtualchemlab_updates'
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info("自动更新器初始化完成 (当前版本: %s)", self.current_version)

    def _detect_platform(self) -> str:
        """检测平台"""
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            return 'unknown'

    def check_for_updates(self, force: bool = False) -> Optional[VersionInfo]:
        """检查更新

        Args:
            force: 强制检查（忽略时间间隔）

        Returns:
            如果有更新返回版本信息，否则返回None
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests库不可用，无法检查更新")
            return None

        # 检查时间间隔
        if not force and self.last_check_time:
            elapsed = (datetime.now() - self.last_check_time).total_seconds()
            if elapsed < self.check_interval:
                logger.debug(f"距离上次检查仅 {elapsed:.0f} 秒，跳过")
                return self.latest_version

        try:
            # 请求更新信息
            url = f"{self.update_url}/check"
            params = {
                'version': self.current_version,
                'platform': self.platform
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 记录检查时间
            self.last_check_time = datetime.now()

            # 解析版本信息
            if data.get('has_update'):
                update_info = data.get('update_info', {})
                self.latest_version = VersionInfo(
                    version=update_info['version'],
                    build_number=update_info['build_number'],
                    release_date=update_info['release_date'],
                    download_url=update_info['download_url'],
                    checksum=update_info['checksum'],
                    size_bytes=update_info['size_bytes'],
                    changelog=update_info.get('changelog', ''),
                    is_critical=update_info.get('is_critical', False)
                )

                logger.info(f"发现新版本: {self.latest_version.version}")
                return self.latest_version
            else:
                logger.info("当前已是最新版本")
                return None

        except requests.RequestException as e:
            logger.error(f"检查更新失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析更新信息失败: {e}")
            return None

    def download_update(
        self,
        version_info: VersionInfo,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """下载更新

        Args:
            version_info: 版本信息
            progress_callback: 进度回调 (已下载, 总大小)

        Returns:
            下载的文件路径，失败返回None
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests库不可用")
            return None

        try:
            # 下载文件
            logger.info(f"开始下载更新: {version_info.version}")

            response = requests.get(version_info.download_url, stream=True, timeout=30)
            response.raise_for_status()

            # 确定文件名
            filename = f"VirtualChemLab-{version_info.version}-{self.platform}.exe"
            if self.platform == 'macos':
                filename = f"VirtualChemLab-{version_info.version}.dmg"

            file_path = self.temp_dir / filename

            # 流式下载
            total_size = version_info.size_bytes
            downloaded = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 调用进度回调
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            logger.info(f"下载完成: {file_path}")

            # 验证校验和
            if not self._verify_checksum(file_path, version_info.checksum):
                logger.error("文件校验失败！")
                file_path.unlink()
                return None

            logger.info("文件校验成功")
            return file_path

        except Exception as e:
            logger.error(f"下载更新失败: {e}")
            return None

    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """验证文件校验和

        Args:
            file_path: 文件路径
            expected_checksum: 期望的SHA256校验和

        Returns:
            是否匹配
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # 分块读取，避免大文件占用过多内存
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            calculated = sha256_hash.hexdigest()
            return calculated == expected_checksum

        except Exception as e:
            logger.error(f"计算校验和失败: {e}")
            return False

    def install_update(self, update_file: Path) -> bool:
        """安装更新

        Args:
            update_file: 更新文件路径

        Returns:
            是否成功
        """
        try:
            if self.platform == 'windows':
                # Windows: 启动安装程序
                logger.info("启动Windows安装程序...")
                subprocess.Popen([str(update_file)], shell=True)
                return True

            elif self.platform == 'macos':
                # macOS: 打开DMG
                logger.info("打开macOS DMG镜像...")
                subprocess.Popen(['open', str(update_file)])
                return True

            else:
                logger.error(f"不支持的平台: {self.platform}")
                return False

        except Exception as e:
            logger.error(f"安装更新失败: {e}")
            return False

    def auto_update(
        self,
        auto_install: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """自动更新流程

        Args:
            auto_install: 是否自动安装（否则只下载）
            progress_callback: 进度回调

        Returns:
            是否成功
        """
        # 检查更新
        version_info = self.check_for_updates()
        if not version_info:
            logger.info("没有可用更新")
            return False

        # 下载更新
        update_file = self.download_update(version_info, progress_callback)
        if not update_file:
            logger.error("下载失败")
            return False

        # 自动安装
        if auto_install:
            return self.install_update(update_file)
        else:
            logger.info(f"更新已下载到: {update_file}")
            return True

    def get_changelog(self, version: Optional[str] = None) -> str:
        """获取更新日志

        Args:
            version: 版本号，None获取最新版本

        Returns:
            更新日志内容
        """
        if not REQUESTS_AVAILABLE:
            return "无法获取更新日志（requests库不可用）"

        try:
            url = f"{self.update_url}/changelog"
            params = {'version': version} if version else {}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('changelog', '无更新日志')

        except Exception as e:
            logger.error(f"获取更新日志失败: {e}")
            return f"获取失败: {e}"

    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("已清理临时文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
