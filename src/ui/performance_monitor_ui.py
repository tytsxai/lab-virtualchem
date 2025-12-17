"""
性能监控UI组件
提供实时性能监控和优化建议的用户界面
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
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
from .memory_manager import get_memory_manager, optimize_memory
from .themes import ThemeManager

logger = get_logger(__name__)


class PerformanceChartWidget(QWidget):
    """性能图表组件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)

        # 数据存储
        self._data_points: list[float] = []
        self._max_points = 100
        self._title = "性能指标"
        self._unit = "%"

        # 样式设置
        self._background_color = "#2b2b2b"
        self._line_color = "#00ff00"
        self._grid_color = "#404040"

    def set_title(self, title: str) -> None:
        """设置图表标题"""
        self._title = title

    def set_unit(self, unit: str) -> None:
        """设置单位"""
        self._unit = unit

    def add_data_point(self, value: float) -> None:
        """添加数据点"""
        self._data_points.append(value)
        if len(self._data_points) > self._max_points:
            self._data_points.pop(0)
        self.update()

    def paintEvent(self, _event) -> None:
        """绘制图表"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 绘制背景
            painter.fillRect(self.rect(), self._background_color)

            if not self._data_points:
                return

            # 计算绘制区域
            margin = 40
            chart_rect = self.rect().adjusted(margin, margin, -margin, -margin)

            # 绘制网格
            self._draw_grid(painter, chart_rect)

            # 绘制数据线
            self._draw_data_line(painter, chart_rect)

            # 绘制标题
            self._draw_title(painter)

        except Exception as e:
            logger.error(f"绘制图表失败: {e}", exc_info=True)

    def _draw_grid(self, painter: QPainter, rect) -> None:
        """绘制网格"""
        try:
            pen = QPen(self._grid_color, 1)
            painter.setPen(pen)

            # 水平网格线
            for i in range(5):
                y = rect.top() + (rect.height() * i / 4)
                painter.drawLine(rect.left(), y, rect.right(), y)

            # 垂直网格线
            for i in range(10):
                x = rect.left() + (rect.width() * i / 9)
                painter.drawLine(x, rect.top(), x, rect.bottom())

        except Exception as e:
            logger.error(f"绘制网格失败: {e}", exc_info=True)

    def _draw_data_line(self, painter: QPainter, rect) -> None:
        """绘制数据线"""
        try:
            if len(self._data_points) < 2:
                return

            # 计算数据范围
            min_val = min(self._data_points)
            max_val = max(self._data_points)
            val_range = max_val - min_val if max_val > min_val else 1

            # 绘制数据线
            pen = QPen(self._line_color, 2)
            painter.setPen(pen)

            points = []
            for i, value in enumerate(self._data_points):
                x = rect.left() + (rect.width() * i / (len(self._data_points) - 1))
                y = rect.bottom() - (rect.height() * (value - min_val) / val_range)
                points.append((x, y))

            for i in range(len(points) - 1):
                painter.drawLine(
                    points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]
                )

        except Exception as e:
            logger.error(f"绘制数据线失败: {e}", exc_info=True)

    def _draw_title(self, painter: QPainter) -> None:
        """绘制标题"""
        try:
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)

            title_rect = self.rect().adjusted(10, 10, -10, -10)
            painter.drawText(
                title_rect,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                self._title,
            )

        except Exception as e:
            logger.error(f"绘制标题失败: {e}", exc_info=True)


class PerformanceMonitorDialog(QDialog):
    """性能监控对话框"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.performance_monitor = get_performance_monitor()
        self.memory_manager = get_memory_manager()
        self.theme_manager = ThemeManager()

        self.setWindowTitle("性能监控")
        self.setMinimumSize(1000, 700)
        self.setModal(False)

        # 图表组件
        self.cpu_chart = PerformanceChartWidget()
        self.memory_chart = PerformanceChartWidget()
        self.fps_chart = PerformanceChartWidget()

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

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 实时监控标签页
        self.realtime_tab = self.create_realtime_tab()
        self.tab_widget.addTab(self.realtime_tab, "实时监控")

        # 内存管理标签页
        self.memory_tab = self.create_memory_tab()
        self.tab_widget.addTab(self.memory_tab, "内存管理")

        # 优化建议标签页
        self.optimization_tab = self.create_optimization_tab()
        self.tab_widget.addTab(self.optimization_tab, "优化建议")

    def create_realtime_tab(self) -> QWidget:
        """创建实时监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 概览信息
        overview_group = QGroupBox("系统概览")
        overview_layout = QHBoxLayout(overview_group)

        # CPU使用率
        cpu_group = QGroupBox("CPU使用率")
        cpu_layout = QVBoxLayout(cpu_group)

        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_label = QLabel("0%")
        cpu_layout.addWidget(self.cpu_progress)
        cpu_layout.addWidget(self.cpu_label)

        # 内存使用率
        memory_group = QGroupBox("内存使用率")
        memory_layout = QVBoxLayout(memory_group)

        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_label = QLabel("0%")
        memory_layout.addWidget(self.memory_progress)
        memory_layout.addWidget(self.memory_label)

        # FPS
        fps_group = QGroupBox("帧率")
        fps_layout = QVBoxLayout(fps_group)

        self.fps_progress = QProgressBar()
        self.fps_progress.setRange(0, 120)
        self.fps_label = QLabel("0 FPS")
        fps_layout.addWidget(self.fps_progress)
        fps_layout.addWidget(self.fps_label)

        overview_layout.addWidget(cpu_group)
        overview_layout.addWidget(memory_group)
        overview_layout.addWidget(fps_group)

        layout.addWidget(overview_group)

        # 图表区域
        charts_group = QGroupBox("性能图表")
        charts_layout = QHBoxLayout(charts_group)

        # 设置图表标题
        self.cpu_chart.set_title("CPU使用率")
        self.memory_chart.set_title("内存使用率")
        self.fps_chart.set_title("帧率")

        charts_layout.addWidget(self.cpu_chart)
        charts_layout.addWidget(self.memory_chart)
        charts_layout.addWidget(self.fps_chart)

        layout.addWidget(charts_group)

        return widget

    def create_memory_tab(self) -> QWidget:
        """创建内存管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 内存信息
        info_group = QGroupBox("内存信息")
        info_layout = QVBoxLayout(info_group)

        self.memory_info_label = QLabel("正在加载内存信息...")
        info_layout.addWidget(self.memory_info_label)

        layout.addWidget(info_group)

        # 操作按钮
        actions_group = QGroupBox("内存操作")
        actions_layout = QHBoxLayout(actions_group)

        self.gc_button = QPushButton("垃圾回收")
        self.gc_button.clicked.connect(self.force_garbage_collect)

        self.optimize_button = QPushButton("内存优化")
        self.optimize_button.clicked.connect(self.optimize_memory_usage)

        actions_layout.addWidget(self.gc_button)
        actions_layout.addWidget(self.optimize_button)

        layout.addWidget(actions_group)

        return widget

    def create_optimization_tab(self) -> QWidget:
        """创建优化建议标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 优化建议
        suggestions_group = QGroupBox("优化建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_label = QLabel("正在分析性能数据...")
        self.suggestions_label.setWordWrap(True)
        suggestions_layout.addWidget(self.suggestions_label)

        layout.addWidget(suggestions_group)

        # 优化操作
        optimize_group = QGroupBox("优化操作")
        optimize_layout = QHBoxLayout(optimize_group)

        self.auto_optimize_button = QPushButton("自动优化")
        self.auto_optimize_button.clicked.connect(self.auto_optimize)

        self.reset_button = QPushButton("重置设置")
        self.reset_button.clicked.connect(self.reset_settings)

        optimize_layout.addWidget(self.auto_optimize_button)
        optimize_layout.addWidget(self.reset_button)

        layout.addWidget(optimize_group)

        return widget

    def connect_signals(self) -> None:
        """连接信号"""
        self.performance_monitor.metrics_updated.connect(self.on_metrics_updated)
        self.performance_monitor.optimization_suggested.connect(
            self.on_optimization_suggested
        )

    def apply_theme(self) -> None:
        """应用主题"""
        try:
            # 应用深色主题样式
            self.setStyleSheet(
                """
                QWidget {
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
                QProgressBar {
                    border: 2px solid #4a90e2;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #16213e;
                }
                QProgressBar::chunk {
                    background-color: #4a90e2;
                    border-radius: 3px;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #4a90e2;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #5aa0f2;
                }
                QPushButton:pressed {
                    background-color: #3a80d2;
                }
            """
            )

            logger.info("性能监控UI主题应用成功")
        except Exception as e:
            logger.error(f"应用主题失败: {e}", exc_info=True)

    def update_display(self) -> None:
        """更新显示"""
        try:
            # 获取最新指标
            metrics = self.performance_monitor.get_current_metrics()
            if metrics:
                self.on_metrics_updated(metrics)

            # 更新内存信息
            self.update_memory_info()

        except Exception as e:
            logger.error(f"更新显示失败: {e}", exc_info=True)

    def on_metrics_updated(self, metrics: PerformanceMetrics) -> None:
        """处理指标更新"""
        try:
            # 更新概览信息
            self.cpu_progress.setValue(int(metrics.cpu_percent))
            self.cpu_label.setText(f"{metrics.cpu_percent:.1f}%")

            self.memory_progress.setValue(int(metrics.memory_percent))
            self.memory_label.setText(f"{metrics.memory_percent:.1f}%")

            self.fps_progress.setValue(int(metrics.fps))
            self.fps_label.setText(f"{metrics.fps:.1f} FPS")

            # 更新图表
            self.cpu_chart.add_data_point(metrics.cpu_percent)
            self.memory_chart.add_data_point(metrics.memory_percent)
            self.fps_chart.add_data_point(metrics.fps)

        except Exception as e:
            logger.error(f"处理指标更新失败: {e}", exc_info=True)

    def on_optimization_suggested(self, suggestion: OptimizationSuggestion) -> None:
        """处理优化建议"""
        try:
            suggestion_text = f"建议: {suggestion.description}\n优先级: {suggestion.priority}\n类型: {suggestion.category}"
            self.suggestions_label.setText(suggestion_text)

        except Exception as e:
            logger.error(f"处理优化建议失败: {e}", exc_info=True)

    def update_memory_info(self) -> None:
        """更新内存信息"""
        try:
            memory_info = self.memory_manager.get_memory_info()
            if memory_info:
                info_text = f"""
系统内存使用率: {memory_info.get("system_memory_percent", 0):.1f}%
可用内存: {memory_info.get("system_memory_available", 0) / (1024**3):.1f} GB
总内存: {memory_info.get("system_memory_total", 0) / (1024**3):.1f} GB
进程内存: {memory_info.get("process_memory_rss", 0) / (1024**2):.1f} MB
弱引用数量: {memory_info.get("weak_refs_count", 0)}
垃圾回收计数: {memory_info.get("gc_counts", (0, 0, 0))}
                """.strip()
                self.memory_info_label.setText(info_text)

        except Exception as e:
            logger.error(f"更新内存信息失败: {e}", exc_info=True)

    def force_garbage_collect(self) -> None:
        """强制垃圾回收"""
        try:
            collected = self.memory_manager.force_garbage_collect()
            logger.info(f"强制垃圾回收完成: 回收对象 {collected} 个")

        except Exception as e:
            logger.error(f"强制垃圾回收失败: {e}", exc_info=True)

    def optimize_memory_usage(self) -> None:
        """优化内存使用"""
        try:
            result = optimize_memory()
            if result:
                logger.info("内存优化完成")

        except Exception as e:
            logger.error(f"内存优化失败: {e}", exc_info=True)

    def auto_optimize(self) -> None:
        """自动优化"""
        try:
            # 执行内存优化
            self.optimize_memory_usage()

            # 执行垃圾回收
            self.force_garbage_collect()

            logger.info("自动优化完成")

        except Exception as e:
            logger.error(f"自动优化失败: {e}", exc_info=True)

    def reset_settings(self) -> None:
        """重置设置"""
        try:
            # 重置性能监控设置
            self.performance_monitor.reset_settings()

            # 重置内存管理器设置
            self.memory_manager.stop_monitoring()
            self.memory_manager.start_monitoring()

            logger.info("设置已重置")

        except Exception as e:
            logger.error(f"重置设置失败: {e}", exc_info=True)
