"""
错误监控和分析系统

提供错误趋势分析、热点错误识别、错误聚合等功能
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ErrorMetrics:
    """错误指标"""

    total_errors: int
    unique_errors: int
    error_rate: float  # 错误率（每小时）
    most_frequent_error: str | None
    critical_errors: int
    recoverable_errors: int
    affected_users: int


class ErrorAnalytics:
    """错误分析器"""

    def __init__(
        self,
        error_history: list[dict[str, Any]],
        report_history: list[Any] | None = None,
    ):
        """
        初始化错误分析器

        Args:
            error_history: 错误历史记录
            report_history: 报告历史记录
        """
        self.error_history = error_history
        self.report_history = report_history or []

    def get_metrics(self) -> ErrorMetrics:
        """获取错误指标"""
        if not self.error_history:
            return ErrorMetrics(
                total_errors=0,
                unique_errors=0,
                error_rate=0.0,
                most_frequent_error=None,
                critical_errors=0,
                recoverable_errors=0,
                affected_users=0,
            )

        # 总错误数
        total_errors = len(self.error_history)

        # 唯一错误数
        unique_error_codes = {e["error_code"] for e in self.error_history}
        unique_errors = len(unique_error_codes)

        # 错误率（每小时）
        if self.error_history:
            first_time = self.error_history[0]["timestamp"]
            last_time = self.error_history[-1]["timestamp"]
            time_span_hours = (last_time - first_time).total_seconds() / 3600
            error_rate = total_errors / time_span_hours if time_span_hours > 0 else 0
        else:
            error_rate = 0

        # 最频繁的错误
        error_counts = defaultdict(int)
        for error in self.error_history:
            error_counts[error["error_type"]] += 1

        most_frequent_error = (
            max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None
        )

        # 严重错误数
        critical_errors = sum(
            1 for e in self.error_history if e["severity"] == "critical"
        )

        # 可恢复错误数
        recoverable_errors = sum(1 for e in self.error_history if e["recoverable"])

        # 受影响用户数
        unique_users = {e["user_id"] for e in self.error_history if e.get("user_id")}
        affected_users = len(unique_users)

        return ErrorMetrics(
            total_errors=total_errors,
            unique_errors=unique_errors,
            error_rate=error_rate,
            most_frequent_error=most_frequent_error,
            critical_errors=critical_errors,
            recoverable_errors=recoverable_errors,
            affected_users=affected_users,
        )

    def get_error_trends(
        self,
        time_window: timedelta = timedelta(hours=24),
        interval: timedelta = timedelta(hours=1),
    ) -> list[dict[str, Any]]:
        """
        获取错误趋势

        Args:
            time_window: 时间窗口
            interval: 时间间隔

        Returns:
            趋势数据列表
        """
        if not self.error_history:
            return []

        now = datetime.now()
        start_time = now - time_window

        # 过滤时间窗口内的错误
        recent_errors = [e for e in self.error_history if e["timestamp"] >= start_time]

        if not recent_errors:
            return []

        # 按时间间隔分组
        trends = []
        current_time = start_time

        while current_time <= now:
            next_time = current_time + interval

            # 统计此时间段的错误
            period_errors = [
                e for e in recent_errors if current_time <= e["timestamp"] < next_time
            ]

            trends.append(
                {
                    "timestamp": current_time.isoformat(),
                    "error_count": len(period_errors),
                    "critical_count": sum(
                        1 for e in period_errors if e["severity"] == "critical"
                    ),
                    "unique_errors": len({e["error_code"] for e in period_errors}),
                }
            )

            current_time = next_time

        return trends

    def get_hot_errors(self, top_n: int = 10) -> list[dict[str, Any]]:
        """
        获取热点错误（最频繁的错误）

        Args:
            top_n: 返回前N个

        Returns:
            热点错误列表
        """
        # 统计错误频次
        error_stats = defaultdict(lambda: {"count": 0, "severity": "", "message": ""})

        for error in self.error_history:
            error_code = error["error_code"]
            error_stats[error_code]["count"] += 1
            error_stats[error_code]["error_type"] = error["error_type"]
            error_stats[error_code]["severity"] = error["severity"]
            error_stats[error_code]["message"] = error["message"]

        # 排序
        hot_errors = [
            {"error_code": code, **stats} for code, stats in error_stats.items()
        ]
        hot_errors.sort(key=lambda x: x["count"], reverse=True)

        return hot_errors[:top_n]

    def get_error_distribution(self) -> dict[str, Any]:
        """获取错误分布"""
        # 按严重程度分布
        by_severity = defaultdict(int)
        for error in self.error_history:
            by_severity[error["severity"]] += 1

        # 按分类分布
        by_category = defaultdict(int)
        for error in self.error_history:
            if "exception" in error and hasattr(error["exception"], "error_code"):
                category = error["exception"].error_code.category.value
                by_category[category] += 1

        # 按时段分布（小时）
        by_hour = defaultdict(int)
        for error in self.error_history:
            hour = error["timestamp"].hour
            by_hour[hour] += 1

        # 按星期分布
        by_weekday = defaultdict(int)
        for error in self.error_history:
            weekday = error["timestamp"].strftime("%A")
            by_weekday[weekday] += 1

        return {
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "by_hour": dict(by_hour),
            "by_weekday": dict(by_weekday),
        }

    def get_user_error_stats(self) -> list[dict[str, Any]]:
        """获取用户错误统计"""
        user_stats = defaultdict(
            lambda: {"error_count": 0, "critical_errors": 0, "error_types": set()}
        )

        for error in self.error_history:
            user_id = error.get("user_id")
            if not user_id:
                continue

            user_stats[user_id]["error_count"] += 1
            if error["severity"] == "critical":
                user_stats[user_id]["critical_errors"] += 1
            user_stats[user_id]["error_types"].add(error["error_type"])

        # 转换为列表
        result = []
        for user_id, stats in user_stats.items():
            result.append(
                {
                    "user_id": user_id,
                    "error_count": stats["error_count"],
                    "critical_errors": stats["critical_errors"],
                    "unique_error_types": len(stats["error_types"]),
                }
            )

        # 按错误数排序
        result.sort(key=lambda x: x["error_count"], reverse=True)
        return result

    def generate_report(self, output_path: Path | None = None) -> str:
        """
        生成分析报告

        Args:
            output_path: 输出路径

        Returns:
            报告内容
        """
        metrics = self.get_metrics()
        self.get_error_trends()
        hot_errors = self.get_hot_errors()
        distribution = self.get_error_distribution()
        user_stats = self.get_user_error_stats()

        # 生成报告
        report_lines = [
            "=" * 80,
            "错误分析报告",
            "=" * 80,
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 总体指标\n",
            f"总错误数: {metrics.total_errors}",
            f"唯一错误数: {metrics.unique_errors}",
            f"错误率: {metrics.error_rate:.2f} 个/小时",
            f"最频繁错误: {metrics.most_frequent_error or 'N/A'}",
            f"严重错误数: {metrics.critical_errors}",
            f"可恢复错误数: {metrics.recoverable_errors}",
            f"受影响用户数: {metrics.affected_users}",
            "\n## 热点错误（Top 10）\n",
        ]

        for i, error in enumerate(hot_errors, 1):
            report_lines.append(
                f"{i}. [{error['error_type']}] {error['message'][:50]} "
                f"(出现 {error['count']} 次, 严重程度: {error['severity']})"
            )

        report_lines.extend(
            [
                "\n## 错误分布\n",
                "\n### 按严重程度:",
            ]
        )

        for severity, count in distribution["by_severity"].items():
            report_lines.append(f"  {severity}: {count}")

        report_lines.append("\n### 按分类:")
        for category, count in distribution["by_category"].items():
            report_lines.append(f"  {category}: {count}")

        if user_stats:
            report_lines.append("\n## 用户错误统计（Top 10）\n")
            for i, stats in enumerate(user_stats[:10], 1):
                report_lines.append(
                    f"{i}. 用户 {stats['user_id']}: {stats['error_count']} 个错误 "
                    f"(其中 {stats['critical_errors']} 个严重错误)"
                )

        report_lines.append("\n" + "=" * 80)

        report_content = "\n".join(report_lines)

        # 保存报告
        if output_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report_content)
                logger.info(f"分析报告已保存至: {output_path}")
            except Exception as e:
                logger.error(f"保存分析报告失败: {e}")

        return report_content


class ErrorMonitor:
    """错误监控器（实时监控）"""

    def __init__(self, alert_threshold: int = 10, time_window: int = 60):
        """
        初始化错误监控器

        Args:
            alert_threshold: 告警阈值（时间窗口内的错误数）
            time_window: 时间窗口（秒）
        """
        self.alert_threshold = alert_threshold
        self.time_window = time_window
        self._recent_errors: list[dict[str, Any]] = []
        self._alert_callbacks: list[Any] = []

    def record_error(self, error_record: dict[str, Any]):
        """
        记录错误

        Args:
            error_record: 错误记录
        """
        # 添加当前时间
        if "timestamp" not in error_record:
            error_record["timestamp"] = datetime.now()

        self._recent_errors.append(error_record)

        # 清理过期记录
        self._cleanup_old_errors()

        # 检查是否需要告警
        self._check_alert()

    def _cleanup_old_errors(self):
        """清理过期的错误记录"""
        cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
        self._recent_errors = [
            e for e in self._recent_errors if e["timestamp"] >= cutoff_time
        ]

    def _check_alert(self):
        """检查是否需要触发告警"""
        if len(self._recent_errors) >= self.alert_threshold:
            alert_data = {
                "timestamp": datetime.now(),
                "error_count": len(self._recent_errors),
                "time_window": self.time_window,
                "recent_errors": self._recent_errors[-10:],  # 最近10个错误
            }

            # 触发告警回调
            for callback in self._alert_callbacks:
                try:
                    callback(alert_data)
                except Exception as e:
                    logger.error(f"告警回调失败: {e}")

    def register_alert_callback(self, callback: Any):
        """
        注册告警回调

        Args:
            callback: 回调函数，签名为 (alert_data) -> None
        """
        self._alert_callbacks.append(callback)

    def get_current_stats(self) -> dict[str, Any]:
        """获取当前统计"""
        self._cleanup_old_errors()

        return {
            "error_count": len(self._recent_errors),
            "time_window": self.time_window,
            "alert_threshold": self.alert_threshold,
            "is_alerting": len(self._recent_errors) >= self.alert_threshold,
        }


# 全局错误监控器
error_monitor = ErrorMonitor()


# 默认告警处理器
def default_alert_handler(alert_data: dict[str, Any]):
    """默认告警处理器"""
    logger.critical(
        f"⚠️ 错误告警: 在过去 {alert_data['time_window']} 秒内发生了 "
        f"{alert_data['error_count']} 个错误！"
    )
    print(f"\n{'=' * 80}")
    print("⚠️  错误告警  ⚠️")
    print(f"{'=' * 80}")
    print(f"时间: {alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"错误数: {alert_data['error_count']}")
    print(f"时间窗口: {alert_data['time_window']} 秒")
    print("\n最近的错误:")
    for i, error in enumerate(alert_data["recent_errors"], 1):
        print(
            f"  {i}. [{error.get('error_type', 'UNKNOWN')}] {error.get('message', '')}"
        )
    print(f"{'=' * 80}\n")


# 注册默认告警处理器
error_monitor.register_alert_callback(default_alert_handler)
