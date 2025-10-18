"""
实验数据分析器
提供实验数据的统计分析和可视化功能
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    import matplotlib

    matplotlib.use("Qt5Agg")  # 设置后端
    import matplotlib.pyplot as plt  # noqa: F401
    import numpy as np
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

    # 创建占位符类
    class FigureCanvas:
        def __init__(self, figure):
            pass

    class Figure:
        def __init__(self, figsize=None):
            pass

        def add_subplot(self, *_args, **_kwargs):
            return None

        def clear(self):
            pass

        def tight_layout(self):
            pass


from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..storage.json_store import JSONStore
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentAnalyzer(QDialog):
    """实验数据分析器"""

    def __init__(self, parent=None, store: JSONStore = None, user_id: str = None):
        super().__init__(parent)
        self.store = store
        self.user_id = user_id
        self.records = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("实验数据分析")
        self.setModal(True)
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 概览标签页
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "概览")

        # 趋势分析标签页
        self.trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(self.trends_tab, "趋势分析")

        # 成绩分析标签页
        self.scores_tab = self.create_scores_tab()
        self.tab_widget.addTab(self.scores_tab, "成绩分析")

        # 错误分析标签页
        self.mistakes_tab = self.create_mistakes_tab()
        self.tab_widget.addTab(self.mistakes_tab, "错误分析")

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)

    def create_overview_tab(self) -> QWidget:
        """创建概览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息组
        stats_group = QGroupBox("统计信息")
        stats_layout = QFormLayout(stats_group)

        self.total_experiments_label = QLabel("0")
        stats_layout.addRow("总实验数:", self.total_experiments_label)

        self.completed_experiments_label = QLabel("0")
        stats_layout.addRow("已完成实验:", self.completed_experiments_label)

        self.average_score_label = QLabel("0")
        stats_layout.addRow("平均分数:", self.average_score_label)

        self.total_time_label = QLabel("0 分钟")
        stats_layout.addRow("总实验时间:", self.total_time_label)

        layout.addWidget(stats_group)

        # 图表区域
        self.overview_canvas = self.create_chart_canvas()
        layout.addWidget(self.overview_canvas)

        return widget

    def create_trends_tab(self) -> QWidget:
        """创建趋势分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 控制组
        control_group = QGroupBox("分析设置")
        control_layout = QFormLayout(control_group)

        self.trend_period_combo = QComboBox()
        self.trend_period_combo.addItems(["最近7天", "最近30天", "最近90天", "全部"])
        control_layout.addRow("时间范围:", self.trend_period_combo)

        self.trend_metric_combo = QComboBox()
        self.trend_metric_combo.addItems(["分数", "用时", "错误数"])
        control_layout.addRow("分析指标:", self.trend_metric_combo)

        refresh_btn = QPushButton("刷新图表")
        refresh_btn.clicked.connect(self.update_trends_chart)
        control_layout.addRow("", refresh_btn)

        layout.addWidget(control_group)

        # 图表区域
        self.trends_canvas = self.create_chart_canvas()
        layout.addWidget(self.trends_canvas)

        return widget

    def create_scores_tab(self) -> QWidget:
        """创建成绩分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 成绩分布组
        distribution_group = QGroupBox("成绩分布")
        distribution_layout = QVBoxLayout(distribution_group)

        self.scores_canvas = self.create_chart_canvas()
        distribution_layout.addWidget(self.scores_canvas)

        layout.addWidget(distribution_group)

        # 成绩统计组
        score_stats_group = QGroupBox("成绩统计")
        score_stats_layout = QFormLayout(score_stats_group)

        self.highest_score_label = QLabel("0")
        score_stats_layout.addRow("最高分:", self.highest_score_label)

        self.lowest_score_label = QLabel("0")
        score_stats_layout.addRow("最低分:", self.lowest_score_label)

        self.score_std_label = QLabel("0")
        score_stats_layout.addRow("标准差:", self.score_std_label)

        layout.addWidget(score_stats_group)

        return widget

    def create_mistakes_tab(self) -> QWidget:
        """创建错误分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 错误统计组
        mistake_stats_group = QGroupBox("错误统计")
        mistake_stats_layout = QFormLayout(mistake_stats_group)

        self.total_mistakes_label = QLabel("0")
        mistake_stats_layout.addRow("总错误数:", self.total_mistakes_label)

        self.average_mistakes_label = QLabel("0")
        mistake_stats_layout.addRow("平均错误数:", self.average_mistakes_label)

        self.most_common_mistake_label = QLabel("无")
        mistake_stats_layout.addRow("最常见错误:", self.most_common_mistake_label)

        layout.addWidget(mistake_stats_group)

        # 错误趋势图表
        self.mistakes_canvas = self.create_chart_canvas()
        layout.addWidget(self.mistakes_canvas)

        return widget

    def create_chart_canvas(self) -> FigureCanvas:
        """创建图表画布"""
        figure = Figure(figsize=(8, 6))
        canvas = FigureCanvas(figure)
        return canvas

    def load_data(self):
        """加载实验数据"""
        try:
            if self.store and self.user_id:
                self.records = self.store.list_user_records(self.user_id)
                self.update_overview()
                self.update_trends_chart()
                self.update_scores_chart()
                self.update_mistakes_chart()

        except Exception as e:
            logger.error(f"加载实验数据失败: {e}")

    def update_overview(self):
        """更新概览信息"""
        if not self.records:
            return

        total_experiments = len(self.records)
        completed_experiments = sum(1 for r in self.records if r.get("is_completed", False))

        scores = [r.get("final_score", 0) for r in self.records if r.get("final_score") is not None]
        average_score = sum(scores) / len(scores) if scores else 0

        total_time = sum(r.get("total_duration_seconds", 0) for r in self.records) // 60

        self.total_experiments_label.setText(str(total_experiments))
        self.completed_experiments_label.setText(str(completed_experiments))
        self.average_score_label.setText(f"{average_score:.1f}")
        self.total_time_label.setText(f"{total_time} 分钟")

        # 更新概览图表
        self.update_overview_chart()

    def update_overview_chart(self):
        """更新概览图表"""
        if not self.records or not MATPLOTLIB_AVAILABLE:
            return

        figure = self.overview_canvas.figure
        figure.clear()

        # 创建子图
        ax1 = figure.add_subplot(221)
        ax2 = figure.add_subplot(222)
        ax3 = figure.add_subplot(223)
        ax4 = figure.add_subplot(224)

        # 实验完成状态饼图
        completed = sum(1 for r in self.records if r.get("is_completed", False))
        incomplete = len(self.records) - completed

        if completed + incomplete > 0:
            ax1.pie([completed, incomplete], labels=["已完成", "未完成"], autopct="%1.1f%%")
            ax1.set_title("实验完成状态")

        # 分数分布直方图
        scores = [r.get("final_score", 0) for r in self.records if r.get("final_score") is not None]
        if scores:
            ax2.hist(scores, bins=10, alpha=0.7, color="skyblue", edgecolor="black")
            ax2.set_title("分数分布")
            ax2.set_xlabel("分数")
            ax2.set_ylabel("频次")

        # 实验时长分布
        durations = [r.get("total_duration_seconds", 0) / 60 for r in self.records]
        if durations:
            ax3.hist(durations, bins=10, alpha=0.7, color="lightgreen", edgecolor="black")
            ax3.set_title("实验时长分布")
            ax3.set_xlabel("时长 (分钟)")
            ax3.set_ylabel("频次")

        # 错误数分布
        mistakes = [r.get("total_mistakes", 0) for r in self.records]
        if mistakes:
            ax4.hist(mistakes, bins=10, alpha=0.7, color="lightcoral", edgecolor="black")
            ax4.set_title("错误数分布")
            ax4.set_xlabel("错误数")
            ax4.set_ylabel("频次")

        figure.tight_layout()
        self.overview_canvas.draw()

    def update_trends_chart(self):
        """更新趋势分析图表"""
        if not self.records or not MATPLOTLIB_AVAILABLE:
            return

        figure = self.trends_canvas.figure
        figure.clear()

        # 根据时间范围过滤数据
        period = self.trend_period_combo.currentText()
        now = datetime.now()

        if period == "最近7天":
            cutoff = now - timedelta(days=7)
        elif period == "最近30天":
            cutoff = now - timedelta(days=30)
        elif period == "最近90天":
            cutoff = now - timedelta(days=90)
        else:
            cutoff = datetime.min

        filtered_records = []
        for record in self.records:
            record_date = record.get("created_at")
            if record_date:
                if isinstance(record_date, str):
                    record_date = datetime.fromisoformat(record_date.replace("Z", "+00:00"))
                if record_date >= cutoff:
                    filtered_records.append(record)

        if not filtered_records:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "所选时间范围内无数据", ha="center", va="center", transform=ax.transAxes)
            self.trends_canvas.draw()
            return

        # 按日期分组数据
        dates = []
        values = []

        metric = self.trend_metric_combo.currentText()

        for record in filtered_records:
            record_date = record.get("created_at")
            if record_date:
                if isinstance(record_date, str):
                    record_date = datetime.fromisoformat(record_date.replace("Z", "+00:00"))
                dates.append(record_date.date())

                if metric == "分数":
                    values.append(record.get("final_score", 0))
                elif metric == "用时":
                    values.append(record.get("total_duration_seconds", 0) / 60)
                else:  # 错误数
                    values.append(record.get("total_mistakes", 0))

        if dates and values:
            ax = figure.add_subplot(111)
            ax.plot(dates, values, marker="o", linewidth=2, markersize=6)
            ax.set_title(f"{metric}趋势")
            ax.set_xlabel("日期")
            ax.set_ylabel(metric)
            ax.grid(True, alpha=0.3)

            # 旋转x轴标签
            figure.autofmt_xdate()

        self.trends_canvas.draw()

    def update_scores_chart(self):
        """更新成绩分析图表"""
        if not self.records or not MATPLOTLIB_AVAILABLE:
            return

        figure = self.scores_canvas.figure
        figure.clear()

        scores = [r.get("final_score", 0) for r in self.records if r.get("final_score") is not None]

        if scores:
            ax = figure.add_subplot(111)
            ax.hist(scores, bins=15, alpha=0.7, color="skyblue", edgecolor="black")
            ax.axvline(np.mean(scores), color="red", linestyle="--", label=f"平均值: {np.mean(scores):.1f}")
            ax.axvline(np.median(scores), color="green", linestyle="--", label=f"中位数: {np.median(scores):.1f}")
            ax.set_title("成绩分布")
            ax.set_xlabel("分数")
            ax.set_ylabel("频次")
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 更新统计信息
            self.highest_score_label.setText(f"{max(scores):.1f}")
            self.lowest_score_label.setText(f"{min(scores):.1f}")
            self.score_std_label.setText(f"{np.std(scores):.1f}")

        self.scores_canvas.draw()

    def update_mistakes_chart(self):
        """更新错误分析图表"""
        if not self.records or not MATPLOTLIB_AVAILABLE:
            return

        figure = self.mistakes_canvas.figure
        figure.clear()

        mistakes = [r.get("total_mistakes", 0) for r in self.records]

        if mistakes:
            total_mistakes = sum(mistakes)
            average_mistakes = total_mistakes / len(mistakes)

            self.total_mistakes_label.setText(str(total_mistakes))
            self.average_mistakes_label.setText(f"{average_mistakes:.1f}")

            # 错误趋势图
            ax = figure.add_subplot(111)
            dates = []
            mistake_counts = []

            for record in self.records:
                record_date = record.get("created_at")
                if record_date:
                    if isinstance(record_date, str):
                        record_date = datetime.fromisoformat(record_date.replace("Z", "+00:00"))
                    dates.append(record_date.date())
                    mistake_counts.append(record.get("total_mistakes", 0))

            if dates and mistake_counts:
                ax.plot(dates, mistake_counts, marker="o", linewidth=2, markersize=6, color="red")
                ax.set_title("错误数趋势")
                ax.set_xlabel("日期")
                ax.set_ylabel("错误数")
                ax.grid(True, alpha=0.3)

                # 旋转x轴标签
                figure.autofmt_xdate()

            # 更新最常见错误
            self.most_common_mistake_label.setText("需要实现错误类型统计")

        self.mistakes_canvas.draw()


if __name__ == "__main__":
    app = QApplication([])
    analyzer = ExperimentAnalyzer()
    analyzer.show()
    app.exec()
