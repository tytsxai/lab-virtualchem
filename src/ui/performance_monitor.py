"""
性能监控工具
提供实时性能监控和缓存管理功能
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.smart_cache import get_cache_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor(QDialog):
    """性能监控器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache_manager = get_cache_manager()
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("性能监控器")
        self.setModal(False)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 缓存监控标签页
        self.cache_tab = self.create_cache_tab()
        self.tab_widget.addTab(self.cache_tab, "缓存监控")

        # 系统性能标签页
        self.system_tab = self.create_system_tab()
        self.tab_widget.addTab(self.system_tab, "系统性能")

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)

    def create_cache_tab(self) -> QWidget:
        """创建缓存监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 缓存操作组
        cache_ops_group = QGroupBox("缓存操作")
        cache_ops_layout = QHBoxLayout(cache_ops_group)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.update_cache_stats)
        cache_ops_layout.addWidget(refresh_btn)

        cleanup_btn = QPushButton("清理过期")
        cleanup_btn.clicked.connect(self.cleanup_expired)
        cache_ops_layout.addWidget(cleanup_btn)

        clear_all_btn = QPushButton("清空所有")
        clear_all_btn.clicked.connect(self.clear_all_caches)
        cache_ops_layout.addWidget(clear_all_btn)

        cache_ops_layout.addStretch()
        layout.addWidget(cache_ops_group)

        # 缓存统计表格
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(6)
        self.cache_table.setHorizontalHeaderLabels(
            ["缓存名称", "大小", "最大大小", "命中次数", "未命中次数", "命中率"]
        )
        layout.addWidget(self.cache_table)

        return widget

    def create_system_tab(self) -> QWidget:
        """创建系统性能标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 系统信息组
        system_info_group = QGroupBox("系统信息")
        system_info_layout = QFormLayout(system_info_group)

        self.memory_label = QLabel("0 MB")
        system_info_layout.addRow("内存使用:", self.memory_label)

        self.cpu_label = QLabel("0%")
        system_info_layout.addRow("CPU使用:", self.cpu_label)

        self.uptime_label = QLabel("0 秒")
        system_info_layout.addRow("运行时间:", self.uptime_label)

        layout.addWidget(system_info_group)

        # 性能图表区域（简化版）
        self.performance_label = QLabel("性能图表区域\n\n这里可以添加实时性能图表")
        self.performance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.performance_label.setStyleSheet(
            "border: 1px solid gray; background-color: #f0f0f0;"
        )
        layout.addWidget(self.performance_label)

        return widget

    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)  # 每2秒更新一次

        self.start_time = time.time()

    def update_stats(self):
        """更新统计信息"""
        self.update_cache_stats()
        self.update_system_stats()

    def update_cache_stats(self):
        """更新缓存统计"""
        try:
            stats = self.cache_manager.get_all_stats()

            self.cache_table.setRowCount(len(stats))

            for row, (name, stat) in enumerate(stats.items()):
                self.cache_table.setItem(row, 0, QTableWidgetItem(name))
                self.cache_table.setItem(row, 1, QTableWidgetItem(str(stat["size"])))
                self.cache_table.setItem(
                    row, 2, QTableWidgetItem(str(stat["max_size"]))
                )
                self.cache_table.setItem(row, 3, QTableWidgetItem(str(stat["hits"])))
                self.cache_table.setItem(row, 4, QTableWidgetItem(str(stat["misses"])))
                self.cache_table.setItem(
                    row, 5, QTableWidgetItem(f"{stat['hit_rate']:.2%}")
                )

        except Exception as e:
            logger.error(f"更新缓存统计失败: {e}")

    def update_system_stats(self):
        """更新系统统计"""
        try:
            import psutil

            # 内存使用
            memory = psutil.virtual_memory()
            self.memory_label.setText(
                f"{memory.used // 1024 // 1024} MB / {memory.total // 1024 // 1024} MB"
            )

            # CPU使用
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_label.setText(f"{cpu_percent:.1f}%")

            # 运行时间
            uptime = time.time() - self.start_time
            self.uptime_label.setText(f"{uptime:.0f} 秒")

        except ImportError:
            self.memory_label.setText("需要安装 psutil")
            self.cpu_label.setText("需要安装 psutil")
        except Exception as e:
            logger.error(f"更新系统统计失败: {e}")

    def cleanup_expired(self):
        """清理过期缓存"""
        try:
            cleaned = self.cache_manager.cleanup_all()
            logger.info(f"清理了 {cleaned} 个过期缓存条目")
            self.update_cache_stats()
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")

    def clear_all_caches(self):
        """清空所有缓存"""
        try:
            self.cache_manager.clear_all()
            logger.info("已清空所有缓存")
            self.update_cache_stats()
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")


class CacheDebugger(QDialog):
    """缓存调试器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache_manager = get_cache_manager()
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("缓存调试器")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # 缓存选择
        cache_group = QGroupBox("缓存操作")
        cache_layout = QFormLayout(cache_group)

        self.cache_name_combo = QComboBox()
        self.cache_name_combo.addItems(["default", "template", "experiment"])
        cache_layout.addRow("缓存名称:", self.cache_name_combo)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入缓存键")
        cache_layout.addRow("缓存键:", self.key_edit)

        # 操作按钮
        ops_layout = QHBoxLayout()

        get_btn = QPushButton("获取")
        get_btn.clicked.connect(self.get_cache_value)
        ops_layout.addWidget(get_btn)

        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_cache_value)
        ops_layout.addWidget(delete_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_cache)
        ops_layout.addWidget(clear_btn)

        cache_layout.addRow("操作:", ops_layout)
        layout.addWidget(cache_group)

        # 结果显示
        result_group = QGroupBox("结果")
        result_layout = QVBoxLayout(result_group)

        self.result_label = QLabel("结果将显示在这里")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
        result_layout.addWidget(self.result_label)

        layout.addWidget(result_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)

    def get_cache_value(self):
        """获取缓存值"""
        try:
            cache_name = self.cache_name_combo.currentText()
            key = self.key_edit.text().strip()

            if not key:
                self.result_label.setText("请输入缓存键")
                return

            cache = self.cache_manager.get_cache(cache_name)
            value = cache.get(key)

            if value is not None:
                self.result_label.setText(f"找到缓存值:\n{str(value)[:500]}...")
            else:
                self.result_label.setText("缓存键不存在")

        except Exception as e:
            self.result_label.setText(f"获取缓存值失败: {e}")

    def delete_cache_value(self):
        """删除缓存值"""
        try:
            cache_name = self.cache_name_combo.currentText()
            key = self.key_edit.text().strip()

            if not key:
                self.result_label.setText("请输入缓存键")
                return

            cache = self.cache_manager.get_cache(cache_name)
            success = cache.delete(key)

            if success:
                self.result_label.setText("缓存值已删除")
            else:
                self.result_label.setText("缓存键不存在")

        except Exception as e:
            self.result_label.setText(f"删除缓存值失败: {e}")

    def clear_cache(self):
        """清空缓存"""
        try:
            cache_name = self.cache_name_combo.currentText()
            cache = self.cache_manager.get_cache(cache_name)
            cache.clear()
            self.result_label.setText(f"缓存 '{cache_name}' 已清空")

        except Exception as e:
            self.result_label.setText(f"清空缓存失败: {e}")


if __name__ == "__main__":
    app = QApplication([])
    monitor = PerformanceMonitor()
    monitor.show()
    app.exec()
