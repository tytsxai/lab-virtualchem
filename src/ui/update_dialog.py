"""
更新对话框
显示更新信息和下载进度
"""

import logging

try:
    from PySide6.QtCore import QThread, Signal
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )

    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

from ..core.auto_updater import AutoUpdater, VersionInfo
from .security_utils import force_plain_text, set_plain_text

logger = logging.getLogger(__name__)


if PYSIDE6_AVAILABLE:

    class UpdateDownloadThread(QThread):
        """更新下载线程"""

        progress = Signal(int, int)  # 已下载, 总大小
        finished = Signal(bool, str)  # 成功, 文件路径或错误信息

        def __init__(self, updater: AutoUpdater, version_info: VersionInfo):
            super().__init__()
            self.updater = updater
            self.version_info = version_info

        def run(self):
            """运行下载"""
            try:

                def progress_callback(downloaded, total):
                    self.progress.emit(downloaded, total)

                file_path = self.updater.download_update(
                    self.version_info, progress_callback
                )

                if file_path:
                    self.finished.emit(True, str(file_path))
                else:
                    self.finished.emit(False, "下载失败")

            except Exception as e:
                logger.error(f"下载线程错误: {e}")
                self.finished.emit(False, str(e))

    class UpdateDialog(QDialog):
        """更新对话框"""

        def __init__(
            self, version_info: VersionInfo, updater: AutoUpdater, parent=None
        ):
            super().__init__(parent)
            self.version_info = version_info
            self.updater = updater
            self.download_thread: UpdateDownloadThread | None = None
            self.downloaded_file: str | None = None

            self.setWindowTitle("软件更新")
            self.setMinimumWidth(500)
            self.setMinimumHeight(400)

            self._setup_ui()

        def _setup_ui(self):
            """设置UI"""
            layout = QVBoxLayout(self)

            # 标题
            title = QLabel()
            force_plain_text(title)
            set_plain_text(title, f"发现新版本 v{self.version_info.version}")
            title.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(title)

            # 版本信息
            info_layout = QVBoxLayout()

            for line in (
                f"当前版本: v{self.updater.current_version}",
                f"最新版本: v{self.version_info.version}",
                f"发布日期: {self.version_info.release_date}",
            ):
                label = QLabel()
                force_plain_text(label)
                set_plain_text(label, line)
                info_layout.addWidget(label)

            size_mb = self.version_info.size_bytes / 1024 / 1024
            size_label = QLabel()
            force_plain_text(size_label)
            set_plain_text(size_label, f"文件大小: {size_mb:.1f} MB")
            info_layout.addWidget(size_label)

            if self.version_info.is_critical:
                critical_label = QLabel("⚠ 关键更新 - 强烈建议安装")
                force_plain_text(critical_label)
                critical_label.setStyleSheet("color: red; font-weight: bold;")
                info_layout.addWidget(critical_label)

            layout.addLayout(info_layout)

            # 更新日志
            changelog_title = QLabel("更新内容:")
            force_plain_text(changelog_title)
            layout.addWidget(changelog_title)

            self.changelog_text = QTextEdit()
            self.changelog_text.setReadOnly(True)
            self.changelog_text.setPlainText(self.version_info.changelog)
            self.changelog_text.setMaximumHeight(150)
            layout.addWidget(self.changelog_text)

            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)

            # 状态标签
            self.status_label = QLabel("")
            force_plain_text(self.status_label)
            layout.addWidget(self.status_label)

            # 按钮
            button_layout = QHBoxLayout()

            self.download_btn = QPushButton("下载更新")
            self.download_btn.clicked.connect(self._start_download)
            button_layout.addWidget(self.download_btn)

            self.install_btn = QPushButton("安装")
            self.install_btn.setEnabled(False)
            self.install_btn.clicked.connect(self._install_update)
            button_layout.addWidget(self.install_btn)

            self.cancel_btn = QPushButton("稍后提醒")
            self.cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_btn)

            layout.addLayout(button_layout)

        def _start_download(self):
            """开始下载"""
            self.download_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            set_plain_text(self.status_label, "正在下载...")

            # 创建下载线程
            self.download_thread = UpdateDownloadThread(self.updater, self.version_info)
            self.download_thread.progress.connect(self._on_download_progress)
            self.download_thread.finished.connect(self._on_download_finished)
            self.download_thread.start()

        def _on_download_progress(self, downloaded: int, total: int):
            """更新下载进度"""
            if total > 0:
                progress = int(downloaded / total * 100)
                self.progress_bar.setValue(progress)

                downloaded_mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024
                set_plain_text(
                    self.status_label,
                    f"正在下载... {downloaded_mb:.1f} / {total_mb:.1f} MB ({progress}%)",
                )

        def _on_download_finished(self, success: bool, result: str):
            """下载完成"""
            if success:
                self.downloaded_file = result
                self.progress_bar.setValue(100)
                set_plain_text(self.status_label, "下载完成！")
                self.install_btn.setEnabled(True)
                logger.info(f"更新已下载: {result}")
            else:
                self.progress_bar.setVisible(False)
                set_plain_text(self.status_label, f"下载失败: {result}")
                self.download_btn.setEnabled(True)
                logger.error(f"下载失败: {result}")

        def _install_update(self):
            """安装更新"""
            if not self.downloaded_file:
                return

            from pathlib import Path

            success = self.updater.install_update(Path(self.downloaded_file))

            if success:
                set_plain_text(self.status_label, "正在安装更新，应用将重启...")
                # 关闭对话框和应用
                self.accept()
                # 应用将自动退出，安装程序接管
            else:
                set_plain_text(self.status_label, "安装失败，请手动安装")
                logger.error("安装更新失败")


def show_update_dialog(
    version_info: VersionInfo, updater: AutoUpdater, parent=None
) -> bool:
    """显示更新对话框

    Args:
        version_info: 版本信息
        updater: 更新器
        parent: 父窗口

    Returns:
        用户是否确认更新
    """
    if not PYSIDE6_AVAILABLE:
        logger.warning("PySide6不可用，无法显示更新对话框")
        return False

    dialog = UpdateDialog(version_info, updater, parent)
    return dialog.exec() == QDialog.Accepted
