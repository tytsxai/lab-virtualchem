"""
性能监控对话框
提供性能监控和优化建议的用户界面
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.performance_monitor import (
    OptimizationSuggestion,
    PerformanceMetrics,
    get_performance_monitor,
)
from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class PerformanceDialog(QDialog):
    """性能监控对话框"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.performance_monitor = get_performance_monitor()
        self.theme_manager = ThemeManager()

        self.setWindowTitle("性能监控")
        self.setMinimumSize(800, 600)
        self.setModal(False)

        self.init_ui()
        self.connect_signals()
        self.apply_theme()

        # 启动实时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1秒更新一次

        logger.info("性能监控对话框初始化完成")

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("📊 性能监控")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 创建各个页面
        self.create_overview_tab()
        self.create_metrics_tab()
        self.create_optimization_tab()
        self.create_history_tab()

        # 按钮
        button_layout = QHBoxLayout()

        # 控制按钮
        self.start_button = ModernButton("▶️ 开始监控")
        self.start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_button)

        self.stop_button = ModernButton("⏸️ 停止监控")
        self.stop_button.clicked.connect(self.stop_monitoring)
        button_layout.addWidget(self.stop_button)

        self.clear_button = ModernButton("🗑️ 清理缓存")
        self.clear_button.clicked.connect(self.clear_caches)
        button_layout.addWidget(self.clear_button)

        self.gc_button = ModernButton("♻️ 垃圾回收")
        self.gc_button.clicked.connect(self.force_garbage_collection)
        button_layout.addWidget(self.gc_button)

        button_layout.addStretch()

        # 关闭按钮
        self.close_button = ModernButton("❌ 关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def create_overview_tab(self) -> None:
        """创建概览页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 当前性能指标
        current_group = QGroupBox("当前性能指标")
        current_layout = QVBoxLayout(current_group)

        # CPU使用率
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU使用率:"))
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_label = QLabel("0%")
        cpu_layout.addWidget(self.cpu_progress)
        cpu_layout.addWidget(self.cpu_label)
        current_layout.addLayout(cpu_layout)

        # 内存使用率
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("内存使用率:"))
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_label = QLabel("0%")
        memory_layout.addWidget(self.memory_progress)
        memory_layout.addWidget(self.memory_label)
        current_layout.addLayout(memory_layout)

        # FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率:"))
        self.fps_progress = QProgressBar()
        self.fps_progress.setRange(0, 60)
        self.fps_label = QLabel("0 FPS")
        fps_layout.addWidget(self.fps_progress)
        fps_layout.addWidget(self.fps_label)
        current_layout.addLayout(fps_layout)

        # 帧时间
        frame_time_layout = QHBoxLayout()
        frame_time_layout.addWidget(QLabel("帧时间:"))
        self.frame_time_label = QLabel("0 ms")
        frame_time_layout.addWidget(self.frame_time_label)
        frame_time_layout.addStretch()
        current_layout.addLayout(frame_time_layout)

        # 物理更新时间
        physics_layout = QHBoxLayout()
        physics_layout.addWidget(QLabel("物理更新时间:"))
        self.physics_time_label = QLabel("0 ms")
        physics_layout.addWidget(self.physics_time_label)
        physics_layout.addStretch()
        current_layout.addLayout(physics_layout)

        # 粒子数量
        particle_layout = QHBoxLayout()
        particle_layout.addWidget(QLabel("粒子数量:"))
        self.particle_count_label = QLabel("0")
        particle_layout.addWidget(self.particle_count_label)
        particle_layout.addStretch()
        current_layout.addLayout(particle_layout)

        # 活跃物品数量
        items_layout = QHBoxLayout()
        items_layout.addWidget(QLabel("活跃物品数量:"))
        self.active_items_label = QLabel("0")
        items_layout.addWidget(self.active_items_label)
        items_layout.addStretch()
        current_layout.addLayout(items_layout)

        # GPU使用率
        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(QLabel("GPU使用率:"))
        self.gpu_progress = QProgressBar()
        self.gpu_progress.setRange(0, 100)
        self.gpu_label = QLabel("0%")
        gpu_layout.addWidget(self.gpu_progress)
        gpu_layout.addWidget(self.gpu_label)
        current_layout.addLayout(gpu_layout)

        # 网络IO
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("网络IO:"))
        self.network_io_label = QLabel("0 B/s")
        network_layout.addWidget(self.network_io_label)
        network_layout.addStretch()
        current_layout.addLayout(network_layout)

        # 磁盘IO
        disk_layout = QHBoxLayout()
        disk_layout.addWidget(QLabel("磁盘IO:"))
        self.disk_io_label = QLabel("0 B/s")
        disk_layout.addWidget(self.disk_io_label)
        disk_layout.addStretch()
        current_layout.addLayout(disk_layout)

        # 线程数
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("线程数:"))
        self.thread_count_label = QLabel("0")
        thread_layout.addWidget(self.thread_count_label)
        thread_layout.addStretch()
        current_layout.addLayout(thread_layout)

        # 内存碎片率
        fragmentation_layout = QHBoxLayout()
        fragmentation_layout.addWidget(QLabel("内存碎片率:"))
        self.fragmentation_progress = QProgressBar()
        self.fragmentation_progress.setRange(0, 100)
        self.fragmentation_label = QLabel("0%")
        fragmentation_layout.addWidget(self.fragmentation_progress)
        fragmentation_layout.addWidget(self.fragmentation_label)
        current_layout.addLayout(fragmentation_layout)

        layout.addWidget(current_group)

        # 性能状态
        status_group = QGroupBox("性能状态")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("监控中...")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "概览")

    def create_metrics_tab(self) -> None:
        """创建指标页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 详细指标表格
        metrics_group = QGroupBox("详细指标")
        metrics_layout = QVBoxLayout(metrics_group)

        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "值"])
        self.metrics_table.setAlternatingRowColors(True)
        self.metrics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        metrics_layout.addWidget(self.metrics_table)
        layout.addWidget(metrics_group)

        # 平均值
        average_group = QGroupBox("平均值")
        average_layout = QVBoxLayout(average_group)

        self.average_table = QTableWidget()
        self.average_table.setColumnCount(2)
        self.average_table.setHorizontalHeaderLabels(["指标", "平均值"])
        self.average_table.setAlternatingRowColors(True)
        self.average_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        average_layout.addWidget(self.average_table)
        layout.addWidget(average_group)

        self.tab_widget.addTab(tab, "指标")

    def create_optimization_tab(self) -> None:
        """创建优化建议页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 优化建议表格
        optimization_group = QGroupBox("优化建议")
        optimization_layout = QVBoxLayout(optimization_group)

        self.optimization_table = QTableWidget()
        self.optimization_table.setColumnCount(5)
        self.optimization_table.setHorizontalHeaderLabels(["类别", "优先级", "标题", "描述", "影响"])
        self.optimization_table.setAlternatingRowColors(True)
        self.optimization_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        optimization_layout.addWidget(self.optimization_table)
        layout.addWidget(optimization_group)

        # 快速优化按钮
        quick_group = QGroupBox("快速优化")
        quick_layout = QHBoxLayout(quick_group)

        self.optimize_particles_button = ModernButton("优化粒子")
        self.optimize_particles_button.clicked.connect(self.optimize_particles)
        quick_layout.addWidget(self.optimize_particles_button)

        self.optimize_physics_button = ModernButton("优化物理")
        self.optimize_physics_button.clicked.connect(self.optimize_physics)
        quick_layout.addWidget(self.optimize_physics_button)

        self.optimize_memory_button = ModernButton("优化内存")
        self.optimize_memory_button.clicked.connect(self.optimize_memory)
        quick_layout.addWidget(self.optimize_memory_button)

        layout.addWidget(quick_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "优化")

    def create_history_tab(self) -> None:
        """创建历史记录页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 历史记录表格
        history_group = QGroupBox("性能历史")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels(
            ["时间", "CPU%", "内存%", "FPS", "帧时间", "物理时间", "粒子数", "物品数"]
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group)

        # 历史控制
        history_control_group = QGroupBox("历史控制")
        history_control_layout = QHBoxLayout(history_control_group)

        self.clear_history_button = ModernButton("清空历史")
        self.clear_history_button.clicked.connect(self.clear_history)
        history_control_layout.addWidget(self.clear_history_button)

        self.export_history_button = ModernButton("导出历史")
        self.export_history_button.clicked.connect(self.export_history)
        history_control_layout.addWidget(self.export_history_button)

        history_control_layout.addStretch()
        layout.addWidget(history_control_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "历史")

    def connect_signals(self) -> None:
        """连接信号"""
        # 连接性能监控器的信号
        try:
            # 如果性能监控器有信号，连接它们
            if hasattr(self.performance_monitor, "metrics_updated"):
                self.performance_monitor.metrics_updated.connect(self.on_metrics_updated)
            if hasattr(self.performance_monitor, "performance_warning"):
                self.performance_monitor.performance_warning.connect(self.on_performance_warning)
            if hasattr(self.performance_monitor, "optimization_suggested"):
                self.performance_monitor.optimization_suggested.connect(self.on_optimization_suggested)

            logger.debug("性能监控信号连接完成")
        except Exception as e:
            logger.warning(f"连接性能监控信号失败: {e}")

    def on_metrics_updated(self, metrics: PerformanceMetrics) -> None:
        """处理指标更新"""
        # 更新概览页面
        self.cpu_progress.setValue(int(metrics.cpu_percent))
        self.cpu_label.setText(f"{metrics.cpu_percent:.1f}%")

        self.memory_progress.setValue(int(metrics.memory_percent))
        self.memory_label.setText(f"{metrics.memory_percent:.1f}%")

        self.fps_progress.setValue(int(metrics.fps))
        self.fps_label.setText(f"{metrics.fps:.1f} FPS")

        self.frame_time_label.setText(f"{metrics.frame_time_ms:.1f} ms")
        self.physics_time_label.setText(f"{metrics.physics_update_time_ms:.1f} ms")
        self.particle_count_label.setText(str(metrics.particle_count))
        self.active_items_label.setText(str(metrics.active_items))

        # 更新新增指标
        self.gpu_progress.setValue(int(metrics.gpu_usage))
        self.gpu_label.setText(f"{metrics.gpu_usage:.1f}%")

        # 格式化IO数据
        network_io_str = self._format_bytes(metrics.network_io_bytes)
        self.network_io_label.setText(f"{network_io_str}/s")

        disk_io_str = self._format_bytes(metrics.disk_io_bytes)
        self.disk_io_label.setText(f"{disk_io_str}/s")

        self.thread_count_label.setText(str(metrics.thread_count))

        self.fragmentation_progress.setValue(int(metrics.memory_fragmentation))
        self.fragmentation_label.setText(f"{metrics.memory_fragmentation:.1f}%")

        # 更新状态
        if metrics.fps > 50:
            self.status_label.setText("性能良好 ✅")
            self.status_label.setStyleSheet("color: green;")
        elif metrics.fps > 30:
            self.status_label.setText("性能一般 ⚠️")
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("性能较差 ❌")
            self.status_label.setStyleSheet("color: red;")

    def on_performance_warning(self, category: str, message: str) -> None:
        """处理性能警告"""
        logger.warning(f"性能警告 [{category}]: {message}")

    def on_optimization_suggested(self, _suggestion: OptimizationSuggestion) -> None:
        """处理优化建议"""
        self.update_optimization_table()

    def update_display(self) -> None:
        """更新显示"""
        # 更新指标表格
        self.update_metrics_table()

        # 更新优化建议表格
        self.update_optimization_table()

        # 更新历史记录表格
        self.update_history_table()

    def update_metrics_table(self) -> None:
        """更新指标表格"""
        summary = self.performance_monitor.get_performance_summary()
        if not summary:
            return

        current = summary.get("current", {})
        average = summary.get("average", {})

        # 当前指标
        metrics_data = [
            ("CPU使用率", f"{current.get('cpu_percent', 0):.1f}%"),
            ("内存使用率", f"{current.get('memory_percent', 0):.1f}%"),
            ("内存使用量", f"{current.get('memory_mb', 0):.1f} MB"),
            ("帧率", f"{current.get('fps', 0):.1f} FPS"),
            ("帧时间", f"{current.get('frame_time_ms', 0):.1f} ms"),
            ("物理更新时间", f"{current.get('physics_update_time_ms', 0):.1f} ms"),
            ("粒子数量", str(current.get("particle_count", 0))),
            ("活跃物品数量", str(current.get("active_items", 0))),
        ]

        self.metrics_table.setRowCount(len(metrics_data))
        for i, (metric, value) in enumerate(metrics_data):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metric))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(value))

        # 平均值
        average_data = [
            ("CPU使用率", f"{average.get('cpu_percent', 0):.1f}%"),
            ("内存使用率", f"{average.get('memory_percent', 0):.1f}%"),
            ("帧率", f"{average.get('fps', 0):.1f} FPS"),
        ]

        self.average_table.setRowCount(len(average_data))
        for i, (metric, value) in enumerate(average_data):
            self.average_table.setItem(i, 0, QTableWidgetItem(metric))
            self.average_table.setItem(i, 1, QTableWidgetItem(value))

    def update_optimization_table(self) -> None:
        """更新优化建议表格"""
        recommendations = self.performance_monitor.get_optimization_recommendations()

        self.optimization_table.setRowCount(len(recommendations))
        for i, suggestion in enumerate(recommendations):
            self.optimization_table.setItem(i, 0, QTableWidgetItem(suggestion.category))
            self.optimization_table.setItem(i, 1, QTableWidgetItem(suggestion.priority))
            self.optimization_table.setItem(i, 2, QTableWidgetItem(suggestion.title))
            self.optimization_table.setItem(i, 3, QTableWidgetItem(suggestion.description))
            self.optimization_table.setItem(i, 4, QTableWidgetItem(suggestion.impact))

    def update_history_table(self) -> None:
        """更新历史记录表格"""
        history = list(self.performance_monitor.metrics_history)

        self.history_table.setRowCount(len(history))
        for i, metrics in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(metrics.timestamp.strftime("%H:%M:%S")))
            self.history_table.setItem(i, 1, QTableWidgetItem(f"{metrics.cpu_percent:.1f}"))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"{metrics.memory_percent:.1f}"))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"{metrics.fps:.1f}"))
            self.history_table.setItem(i, 4, QTableWidgetItem(f"{metrics.frame_time_ms:.1f}"))
            self.history_table.setItem(i, 5, QTableWidgetItem(f"{metrics.physics_update_time_ms:.1f}"))
            self.history_table.setItem(i, 6, QTableWidgetItem(str(metrics.particle_count)))
            self.history_table.setItem(i, 7, QTableWidgetItem(str(metrics.active_items)))

    def start_monitoring(self) -> None:
        """开始监控"""
        self.performance_monitor.start_monitoring()
        logger.info("性能监控已启动")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.performance_monitor.stop_monitoring()
        logger.info("性能监控已停止")

    def clear_caches(self) -> None:
        """清理缓存"""
        self.performance_monitor.clear_caches()
        logger.info("缓存已清理")

    def force_garbage_collection(self) -> None:
        """强制垃圾回收"""
        self.performance_monitor.force_garbage_collection()
        logger.info("垃圾回收已执行")

    def optimize_particles(self) -> None:
        """优化粒子"""
        try:
            # 获取当前粒子数量
            current_metrics = self.performance_monitor.get_performance_summary()
            if not current_metrics:
                logger.warning("无法获取当前性能指标")
                return

            particle_count = current_metrics.particle_count

            # 如果粒子数量过多，进行优化
            if particle_count > 1000:
                # 减少粒子效果强度
                from ..core.config_manager import get_config_manager

                config_manager = get_config_manager()

                # 获取当前粒子设置
                ui_config = config_manager.get_ui_config()
                current_intensity = ui_config.get("particle_intensity", 1.0)

                # 降低强度
                new_intensity = max(0.3, current_intensity * 0.7)
                ui_config["particle_intensity"] = new_intensity
                config_manager.update_ui_config(ui_config)

                # 强制垃圾回收
                self.performance_monitor.force_garbage_collection()

                logger.info(f"粒子优化完成: 强度从 {current_intensity:.2f} 降低到 {new_intensity:.2f}")

                # 显示优化结果
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    "优化完成",
                    f"粒子效果已优化\n强度: {current_intensity:.2f} → {new_intensity:.2f}\n粒子数量: {particle_count}",
                )
            else:
                logger.info("粒子数量正常，无需优化")
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(self, "无需优化", f"当前粒子数量: {particle_count}\n性能良好，无需优化")

        except Exception as e:
            logger.error(f"粒子优化失败: {e}")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "优化失败", f"粒子优化过程中发生错误:\n{e}")

    def optimize_physics(self) -> None:
        """优化物理"""
        try:
            # 获取当前物理性能指标
            current_metrics = self.performance_monitor.get_performance_summary()
            if not current_metrics:
                logger.warning("无法获取当前性能指标")
                return

            physics_time = current_metrics.physics_update_time_ms

            # 如果物理更新时间过长，进行优化
            if physics_time > 16.67:  # 超过一帧的时间(60fps)
                # 调整物理参数
                from ..core.config_manager import get_config_manager

                config_manager = get_config_manager()

                # 获取当前物理设置
                game_config = config_manager.get_game_config()

                # 优化物理参数
                optimizations = {
                    "physics_enabled": True,  # 保持物理启用
                    "collision_detection": True,  # 保持碰撞检测
                    "gravity_strength": min(0.8, game_config.get("gravity_strength", 0.5) * 1.2),  # 稍微增加重力
                    "friction": min(0.95, game_config.get("friction", 0.9) * 1.05),  # 稍微增加摩擦力
                    "bounce_factor": max(0.3, game_config.get("bounce_factor", 0.6) * 0.8),  # 减少弹跳
                }

                # 应用优化
                game_config.update(optimizations)
                config_manager.update_game_config(game_config)

                # 清理物理缓存
                self.performance_monitor.clear_caches()

                logger.info(f"物理优化完成: 更新时间 {physics_time:.2f}ms")

                # 显示优化结果
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self, "优化完成", f"物理引擎已优化\n更新时间: {physics_time:.2f}ms\n调整了重力、摩擦力和弹跳参数"
                )
            else:
                logger.info("物理性能正常，无需优化")
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(self, "无需优化", f"当前物理更新时间: {physics_time:.2f}ms\n性能良好，无需优化")

        except Exception as e:
            logger.error(f"物理优化失败: {e}")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "优化失败", f"物理优化过程中发生错误:\n{e}")

    def optimize_memory(self) -> None:
        """优化内存"""
        self.performance_monitor.force_garbage_collection()
        self.performance_monitor.clear_caches()
        logger.info("内存优化已执行")

    def clear_history(self) -> None:
        """清空历史"""
        self.performance_monitor.clear_caches()
        logger.info("历史记录已清空")

    def export_history(self) -> None:
        """导出历史"""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出性能数据", "performance_data.json", "JSON文件 (*.json)"
            )
            if file_path:
                success = self.performance_monitor.export_performance_data(file_path)
                if success:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.information(self, "成功", f"性能数据已导出到:\n{file_path}")
                else:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(self, "失败", "导出性能数据失败")
        except Exception as e:
            logger.error(f"导出历史失败: {e}")

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        if bytes_value == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(bytes_value)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def apply_theme(self) -> None:
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    margin-top: 1ex;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTabWidget::pane {
                    border: 1px solid #4a90e2;
                    background-color: #16213e;
                }
                QTabBar::tab {
                    background-color: #2d1b69;
                    color: #ffffff;
                    padding: 8px 12px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #4a90e2;
                }
                QProgressBar {
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4a90e2;
                    border-radius: 3px;
                }
                QTableWidget {
                    gridline-color: #4a90e2;
                    background-color: #16213e;
                    alternate-background-color: #2d1b69;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #4a90e2;
                }
            """
            )

            logger.info("主题应用成功")

        except Exception as e:
            logger.warning(f"应用主题失败: {e}")

    def closeEvent(self, event) -> None:
        """关闭事件"""
        self.update_timer.stop()
        super().closeEvent(event)
