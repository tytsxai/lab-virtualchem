"""
反馈分析仪表板
提供可视化的用户反馈分析界面
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..analytics.feedback_analytics import FeedbackAnalytics
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetricCard(QWidget):
    """指标卡片"""

    def __init__(self, title: str, value: str, change: str = "", parent: QWidget | None = None):
        super().__init__(parent)

        self.init_ui(title, value, change)

    def init_ui(self, title: str, value: str, change: str) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(title_label)

        # 数值
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(value_label)

        # 变化
        if change:
            change_label = QLabel(change)
            if "↑" in change or "+" in change:
                change_label.setStyleSheet("font-size: 14px; color: #10b981;")
            elif "↓" in change or "-" in change:
                change_label.setStyleSheet("font-size: 14px; color: #ef4444;")
            else:
                change_label.setStyleSheet("font-size: 14px; color: #666;")
            layout.addWidget(change_label)

        # 样式
        self.setStyleSheet(
            """
            MetricCard {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
            }
        """
        )


class InsightWidget(QWidget):
    """洞察小部件"""

    def __init__(self, insight: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)

        self.insight = insight
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题栏
        header_layout = QHBoxLayout()

        # 类型图标
        icon_label = QLabel(self._get_type_icon(self.insight.get("insight_type", "trend")))
        icon_label.setStyleSheet("font-size: 20px;")
        header_layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(self.insight.get("title", ""))
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 影响分数
        impact_score = self.insight.get("impact_score", 0)
        score_label = QLabel(f"影响分: {impact_score:.0f}")
        score_label.setStyleSheet(f"color: {self._get_impact_color(impact_score)};")
        header_layout.addWidget(score_label)

        layout.addLayout(header_layout)

        # 描述
        desc_label = QLabel(self.insight.get("description", ""))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin: 8px 0;")
        layout.addWidget(desc_label)

        # 建议行动
        actions = self.insight.get("suggested_actions", [])
        if actions:
            actions_label = QLabel("建议行动:")
            actions_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(actions_label)

            for i, action in enumerate(actions[:3], 1):
                action_label = QLabel(f"{i}. {action}")
                action_label.setWordWrap(True)
                action_label.setStyleSheet("color: #444; margin-left: 16px;")
                layout.addWidget(action_label)

        # 样式
        self.setStyleSheet(
            """
            InsightWidget {
                background: #f9fafb;
                border-left: 4px solid #3b82f6;
                border-radius: 4px;
                padding: 12px;
                margin: 4px 0;
            }
        """
        )

    def _get_type_icon(self, insight_type: str) -> str:
        """获取类型图标"""
        icons = {
            "positive": "✅",
            "negative": "⚠️",
            "opportunity": "💡",
            "risk": "🚨",
            "trend": "📊",
        }
        return icons.get(insight_type, "📌")

    def _get_impact_color(self, score: float) -> str:
        """获取影响分数颜色"""
        if score >= 80:
            return "#dc2626"  # 红色 - 高影响
        elif score >= 60:
            return "#f59e0b"  # 橙色 - 中影响
        else:
            return "#10b981"  # 绿色 - 低影响


class FeedbackAnalyticsDashboard(QWidget):
    """反馈分析仪表板"""

    def __init__(self, analytics: FeedbackAnalytics, parent: QWidget | None = None):
        super().__init__(parent)

        self.analytics = analytics
        self.init_ui()

        # 连接信号
        self.analytics.insight_generated.connect(self.on_insight_generated)
        self.analytics.nps_updated.connect(self.on_nps_updated)
        self.analytics.trend_detected.connect(self.on_trend_detected)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("用户反馈分析仪表板")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 16px 0;")
        layout.addWidget(title)

        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # 指标卡片区域
        metrics_layout = self.create_metrics_section()
        layout.addLayout(metrics_layout)

        # 标签页
        tabs = QTabWidget()

        # 总览标签页
        overview_tab = self.create_overview_tab()
        tabs.addTab(overview_tab, "总览")

        # NPS分析标签页
        nps_tab = self.create_nps_tab()
        tabs.addTab(nps_tab, "NPS分析")

        # 趋势标签页
        trends_tab = self.create_trends_tab()
        tabs.addTab(trends_tab, "趋势分析")

        # 用户细分标签页
        segments_tab = self.create_segments_tab()
        tabs.addTab(segments_tab, "用户细分")

        # 洞察标签页
        insights_tab = self.create_insights_tab()
        tabs.addTab(insights_tab, "数据洞察")

        layout.addWidget(tabs)

        # 初始化数据
        self.refresh_dashboard()

    def create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)

        # 时间范围选择
        layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近7天", "最近30天", "最近90天", "全部"])
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        layout.addWidget(self.time_range_combo)

        layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn)

        # 导出按钮
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_report)
        layout.addWidget(export_btn)

        return toolbar

    def create_metrics_section(self) -> QHBoxLayout:
        """创建指标区域"""
        layout = QHBoxLayout()

        # 创建指标卡片
        self.nps_card = MetricCard("NPS分数", "0", "")
        self.satisfaction_card = MetricCard("平均满意度", "0.0", "")
        self.feedback_count_card = MetricCard("反馈总数", "0", "")
        self.response_rate_card = MetricCard("响应率", "0%", "")

        layout.addWidget(self.nps_card)
        layout.addWidget(self.satisfaction_card)
        layout.addWidget(self.feedback_count_card)
        layout.addWidget(self.response_rate_card)

        return layout

    def create_overview_tab(self) -> QWidget:
        """创建总览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 反馈分布图表
        self.feedback_dist_chart = self.create_feedback_distribution_chart()
        layout.addWidget(self.feedback_dist_chart)

        # 满意度趋势图表
        self.satisfaction_trend_chart = self.create_satisfaction_trend_chart()
        layout.addWidget(self.satisfaction_trend_chart)

        return tab

    def create_nps_tab(self) -> QWidget:
        """创建NPS标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # NPS组成图
        self.nps_composition_chart = self.create_nps_composition_chart()
        layout.addWidget(self.nps_composition_chart)

        # NPS详情
        details_group = QGroupBox("NPS详情")
        details_layout = QVBoxLayout()

        self.nps_details_text = QTextEdit()
        self.nps_details_text.setReadOnly(True)
        self.nps_details_text.setMaximumHeight(200)
        details_layout.addWidget(self.nps_details_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        return tab

    def create_trends_tab(self) -> QWidget:
        """创建趋势标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 趋势图表
        self.trends_chart = self.create_trends_chart()
        layout.addWidget(self.trends_chart)

        return tab

    def create_segments_tab(self) -> QWidget:
        """创建用户细分标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 细分列表
        self.segments_list = QListWidget()
        layout.addWidget(self.segments_list)

        # 细分详情
        self.segment_details = QTextEdit()
        self.segment_details.setReadOnly(True)
        self.segment_details.setMaximumHeight(200)
        layout.addWidget(self.segment_details)

        return tab

    def create_insights_tab(self) -> QWidget:
        """创建洞察标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 洞察过滤
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))

        self.insight_type_filter = QComboBox()
        self.insight_type_filter.addItems(["全部", "积极", "消极", "机会", "风险", "趋势"])
        self.insight_type_filter.currentTextChanged.connect(self.filter_insights)
        filter_layout.addWidget(self.insight_type_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 洞察列表（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.insights_container = QWidget()
        self.insights_layout = QVBoxLayout(self.insights_container)
        self.insights_layout.addStretch()

        scroll.setWidget(self.insights_container)
        layout.addWidget(scroll)

        return tab

    def create_feedback_distribution_chart(self) -> QChartView:
        """创建反馈分布图表"""
        # 创建饼图
        series = QPieSeries()
        series.append("Bug报告", 0)
        series.append("功能建议", 0)
        series.append("使用问题", 0)
        series.append("性能问题", 0)
        series.append("一般反馈", 0)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("反馈类型分布")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMaximumHeight(300)

        self.feedback_dist_series = series
        return chart_view

    def create_satisfaction_trend_chart(self) -> QChartView:
        """创建满意度趋势图表"""
        series = QLineSeries()
        series.setName("平均满意度")

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("满意度趋势")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # 坐标轴
        axis_x = QBarCategoryAxis()
        axis_y = QValueAxis()
        axis_y.setRange(0, 5)

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMaximumHeight(300)

        self.satisfaction_trend_series = series
        self.satisfaction_trend_axis_x = axis_x

        return chart_view

    def create_nps_composition_chart(self) -> QChartView:
        """创建NPS组成图表"""
        set0 = QBarSet("推荐者")
        set1 = QBarSet("中立者")
        set2 = QBarSet("贬损者")

        set0.setColor(QColor("#10b981"))
        set1.setColor(QColor("#f59e0b"))
        set2.setColor(QColor("#ef4444"))

        series = QBarSeries()
        series.append(set0)
        series.append(set1)
        series.append(set2)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("NPS组成")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # 坐标轴
        categories = ["用户分布"]
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMaximumHeight(300)

        self.nps_series = series
        self.nps_sets = (set0, set1, set2)

        return chart_view

    def create_trends_chart(self) -> QChartView:
        """创建趋势图表"""
        series = QLineSeries()
        series.setName("满意度变化")

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("关键指标趋势")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.trends_series = series

        return chart_view

    def refresh_dashboard(self) -> None:
        """刷新仪表板"""
        try:
            # 更新指标卡片
            self.update_metrics()

            # 更新反馈分布
            self.update_feedback_distribution()

            # 更新满意度趋势
            self.update_satisfaction_trend()

            # 更新NPS
            self.update_nps()

            # 更新用户细分
            self.update_segments()

            # 更新洞察
            self.update_insights()

            logger.info("仪表板已刷新")

        except Exception as e:
            logger.error(f"刷新仪表板失败: {e}")

    def update_metrics(self) -> None:
        """更新指标卡片"""
        feedbacks = self.analytics.feedbacks

        if not feedbacks:
            return

        # 计算指标
        avg_rating = sum(f.get("rating", 0) for f in feedbacks) / len(feedbacks)
        nps = self.analytics.calculate_nps()

        # 更新卡片
        self.nps_card.findChildren(QLabel)[1].setText(f"{nps.nps_score:.0f}")
        self.satisfaction_card.findChildren(QLabel)[1].setText(f"{avg_rating:.1f}/5.0")
        self.feedback_count_card.findChildren(QLabel)[1].setText(str(len(feedbacks)))

    def update_feedback_distribution(self) -> None:
        """更新反馈分布"""
        feedbacks = self.analytics.feedbacks

        if not feedbacks:
            return

        # 统计各类型数量
        type_counts: dict[str, int] = {}
        for feedback in feedbacks:
            fb_type = feedback.get("feedback_type", "general")
            type_counts[fb_type] = type_counts.get(fb_type, 0) + 1

        # 更新饼图
        self.feedback_dist_series.clear()
        for fb_type, count in type_counts.items():
            self.feedback_dist_series.append(fb_type, count)

    def update_satisfaction_trend(self) -> None:
        """更新满意度趋势"""
        trends = self.analytics.analyze_satisfaction_trends("week")

        if not trends:
            return

        trend = trends[0]

        # 更新折线图
        self.satisfaction_trend_series.clear()

        categories = []
        for i, (date, value) in enumerate(trend.data_points):
            self.satisfaction_trend_series.append(i, value)
            categories.append(date.strftime("%m-%d"))

        self.satisfaction_trend_axis_x.clear()
        self.satisfaction_trend_axis_x.append(categories)

    def update_nps(self) -> None:
        """更新NPS"""
        nps = self.analytics.calculate_nps()

        # 更新柱状图
        self.nps_sets[0].remove(0, self.nps_sets[0].count())
        self.nps_sets[1].remove(0, self.nps_sets[1].count())
        self.nps_sets[2].remove(0, self.nps_sets[2].count())

        self.nps_sets[0].append(nps.promoters_percentage)
        self.nps_sets[1].append(nps.passives_percentage)
        self.nps_sets[2].append(nps.detractors_percentage)

        # 更新详情
        details = f"""
NPS分数: {nps.nps_score:.1f}

推荐者 (9-10分): {nps.promoters_count} 人 ({nps.promoters_percentage:.1f}%)
中立者 (7-8分): {nps.passives_count} 人 ({nps.passives_percentage:.1f}%)
贬损者 (0-6分): {nps.detractors_count} 人 ({nps.detractors_percentage:.1f}%)

行业基准对比:
- 行业平均: {nps.benchmark_comparison.get("industry_average", 0)}
- 良好水平: {nps.benchmark_comparison.get("good_score", 0)}
- 优秀水平: {nps.benchmark_comparison.get("excellent_score", 0)}
        """.strip()

        self.nps_details_text.setText(details)

    def update_segments(self) -> None:
        """更新用户细分"""
        segments = self.analytics.segment_users()

        self.segments_list.clear()

        for segment in segments:
            item = QListWidgetItem(f"{segment.name} ({segment.user_count}人)")
            item.setData(Qt.ItemDataRole.UserRole, segment)
            self.segments_list.addItem(item)

        # 连接选择事件
        self.segments_list.itemClicked.connect(self.on_segment_selected)

    def update_insights(self) -> None:
        """更新洞察"""
        insights = self.analytics.generate_insights()

        # 清空现有洞察
        while self.insights_layout.count() > 1:
            item = self.insights_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新洞察
        for insight in insights:
            insight_widget = InsightWidget(self.analytics._insight_to_dict(insight))
            self.insights_layout.insertWidget(self.insights_layout.count() - 1, insight_widget)

    def on_time_range_changed(self, text: str):
        """时间范围变化"""
        # 根据选择的时间范围过滤数据
        days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90, "全部": None}

        days = days_map.get(text)
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            filtered = [
                f
                for f in self.analytics.feedbacks
                if datetime.fromisoformat(f.get("timestamp", "")) >= cutoff
                if isinstance(f.get("timestamp"), str)
            ]
            self.analytics.load_feedbacks(filtered)
        else:
            # 重新加载全部数据
            pass

        self.refresh_dashboard()

    def on_insight_generated(self, insight: dict[str, Any]) -> None:
        """新洞察生成"""
        insight_widget = InsightWidget(insight)
        self.insights_layout.insertWidget(0, insight_widget)

    def on_nps_updated(self, score: float) -> None:
        """NPS更新"""
        self.nps_card.findChildren(QLabel)[1].setText(f"{score:.0f}")

    def on_trend_detected(self, trend_name: str, trend_data: dict[str, Any]) -> None:
        """趋势检测"""
        logger.info(f"检测到趋势: {trend_name}, {trend_data}")

    def on_segment_selected(self, item: QListWidgetItem):
        """细分选中"""
        segment = item.data(Qt.ItemDataRole.UserRole)

        details = f"""
细分名称: {segment.name}
用户数量: {segment.user_count}
平均满意度: {segment.avg_satisfaction:.1f}

常见反馈类型:
{chr(10).join("- " + t for t in segment.common_feedback_types)}

关键问题:
{chr(10).join("- " + issue for issue in segment.key_issues)}
        """.strip()

        self.segment_details.setText(details)

    def filter_insights(self, filter_text: str) -> None:
        """过滤洞察"""
        type_map = {
            "积极": "positive",
            "消极": "negative",
            "机会": "opportunity",
            "风险": "risk",
            "趋势": "trend",
        }

        filter_type = type_map.get(filter_text)

        # 遍历所有洞察小部件
        for i in range(self.insights_layout.count() - 1):
            item = self.insights_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, InsightWidget):
                    if filter_text == "全部" or widget.insight.get("insight_type") == filter_type:
                        widget.show()
                    else:
                        widget.hide()

    def export_report(self) -> None:
        """导出报告"""
        output_path = self.analytics.export_analytics_report()
        if output_path:
            logger.info(f"报告已导出: {output_path}")
