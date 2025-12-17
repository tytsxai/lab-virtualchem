"""
实验指标收集器
专门用于收集和分析实验相关的指标
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExperimentMetrics:
    """实验指标汇总"""

    experiment_id: str
    experiment_title: str
    experiment_type: str

    # 执行指标
    total_runs: int = 0
    completed_runs: int = 0
    abandoned_runs: int = 0

    # 性能指标
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0

    # 评分指标
    avg_score: float = 0.0
    min_score: int = 0
    max_score: int = 0
    score_distribution: dict[str, int] = field(default_factory=dict)

    # 错误指标
    total_mistakes: int = 0
    avg_mistakes_per_run: float = 0.0
    mistake_types: dict[str, int] = field(default_factory=dict)

    # 步骤指标
    total_steps: int = 0
    step_pass_rates: dict[str, float] = field(default_factory=dict)
    step_avg_attempts: dict[str, float] = field(default_factory=dict)

    # 时间戳
    first_run_at: datetime | None = None
    last_run_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "experiment_id": self.experiment_id,
            "experiment_title": self.experiment_title,
            "experiment_type": self.experiment_type,
            "execution": {
                "total_runs": self.total_runs,
                "completed_runs": self.completed_runs,
                "abandoned_runs": self.abandoned_runs,
                "completion_rate": self.completion_rate,
            },
            "performance": {
                "avg_duration_seconds": self.avg_duration_seconds,
                "min_duration_seconds": self.min_duration_seconds,
                "max_duration_seconds": self.max_duration_seconds,
            },
            "scores": {
                "avg_score": self.avg_score,
                "min_score": self.min_score,
                "max_score": self.max_score,
                "distribution": self.score_distribution,
            },
            "errors": {
                "total_mistakes": self.total_mistakes,
                "avg_mistakes_per_run": self.avg_mistakes_per_run,
                "mistake_types": self.mistake_types,
            },
            "steps": {
                "total_steps": self.total_steps,
                "pass_rates": self.step_pass_rates,
                "avg_attempts": self.step_avg_attempts,
            },
            "timestamps": {
                "first_run_at": self.first_run_at.isoformat()
                if self.first_run_at
                else None,
                "last_run_at": self.last_run_at.isoformat()
                if self.last_run_at
                else None,
            },
        }

    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_runs == 0:
            return 0.0
        return (self.completed_runs / self.total_runs) * 100


class ExperimentMetricsCollector:
    """实验指标收集器"""

    def __init__(self):
        self._experiment_data: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._cached_metrics: dict[str, ExperimentMetrics] = {}
        self._cache_timestamp: dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)

    def record_experiment_run(
        self,
        experiment_id: str,
        experiment_title: str,
        experiment_type: str,
        user_id: str,
        record_data: dict[str, Any],
    ) -> None:
        """
        记录实验运行数据

        Args:
            experiment_id: 实验ID
            experiment_title: 实验标题
            experiment_type: 实验类型
            user_id: 用户ID
            record_data: 记录数据,包含status, score, duration等
        """
        run_data = {
            "experiment_id": experiment_id,
            "experiment_title": experiment_title,
            "experiment_type": experiment_type,
            "user_id": user_id,
            "timestamp": datetime.now(),
            **record_data,
        }

        self._experiment_data[experiment_id].append(run_data)

        # 清除缓存
        if experiment_id in self._cached_metrics:
            del self._cached_metrics[experiment_id]
            del self._cache_timestamp[experiment_id]

        logger.debug(
            f"记录实验运行: {experiment_id}, 用户: {user_id}, 状态: {record_data.get('status')}"
        )

    def get_experiment_metrics(
        self,
        experiment_id: str,
        experiment_title: str = "",
        experiment_type: str = "",
        use_cache: bool = True,
    ) -> ExperimentMetrics:
        """
        获取实验指标

        Args:
            experiment_id: 实验ID
            experiment_title: 实验标题
            experiment_type: 实验类型
            use_cache: 是否使用缓存

        Returns:
            实验指标
        """
        # 检查缓存
        if use_cache and experiment_id in self._cached_metrics:
            cache_time = self._cache_timestamp[experiment_id]
            if datetime.now() - cache_time < self._cache_ttl:
                return self._cached_metrics[experiment_id]

        # 计算指标
        metrics = self._calculate_metrics(
            experiment_id, experiment_title, experiment_type
        )

        # 缓存结果
        self._cached_metrics[experiment_id] = metrics
        self._cache_timestamp[experiment_id] = datetime.now()

        return metrics

    def _calculate_metrics(
        self, experiment_id: str, experiment_title: str, experiment_type: str
    ) -> ExperimentMetrics:
        """计算实验指标"""
        runs = self._experiment_data.get(experiment_id, [])

        if not runs:
            return ExperimentMetrics(
                experiment_id=experiment_id,
                experiment_title=experiment_title,
                experiment_type=experiment_type,
            )

        metrics = ExperimentMetrics(
            experiment_id=experiment_id,
            experiment_title=experiment_title or runs[0].get("experiment_title", ""),
            experiment_type=experiment_type or runs[0].get("experiment_type", ""),
        )

        # 统计执行指标
        metrics.total_runs = len(runs)
        metrics.completed_runs = sum(1 for r in runs if r.get("status") == "completed")
        metrics.abandoned_runs = sum(1 for r in runs if r.get("status") == "abandoned")

        # 只统计已完成的实验
        completed_runs = [r for r in runs if r.get("status") == "completed"]

        if completed_runs:
            # 性能指标
            durations = [
                r.get("duration_seconds", 0)
                for r in completed_runs
                if r.get("duration_seconds")
            ]
            if durations:
                metrics.avg_duration_seconds = sum(durations) / len(durations)
                metrics.min_duration_seconds = min(durations)
                metrics.max_duration_seconds = max(durations)

            # 评分指标
            scores = [r.get("score", {}).get("total", 0) for r in completed_runs]
            if scores:
                metrics.avg_score = sum(scores) / len(scores)
                metrics.min_score = min(scores)
                metrics.max_score = max(scores)

                # 评分分布 (0-59, 60-79, 80-89, 90-100)
                metrics.score_distribution = {
                    "0-59": sum(1 for s in scores if 0 <= s < 60),
                    "60-79": sum(1 for s in scores if 60 <= s < 80),
                    "80-89": sum(1 for s in scores if 80 <= s < 90),
                    "90-100": sum(1 for s in scores if 90 <= s <= 100),
                }

            # 错误指标
            total_mistakes = 0
            mistake_types: dict[str, int] = defaultdict(int)

            for run in completed_runs:
                mistakes = run.get("mistakes_summary", [])
                total_mistakes += len(mistakes)
                for mistake in mistakes:
                    error_type = mistake.get("error_type", "unknown")
                    mistake_types[error_type] += 1

            metrics.total_mistakes = total_mistakes
            metrics.avg_mistakes_per_run = (
                total_mistakes / len(completed_runs) if completed_runs else 0
            )
            metrics.mistake_types = dict(mistake_types)

            # 步骤指标
            step_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"passed": 0, "total": 0, "attempts": []}
            )

            for run in completed_runs:
                step_records = run.get("step_records", [])
                metrics.total_steps = len(step_records)

                for step in step_records:
                    step_id = step.get("step_id", "")
                    step_stats[step_id]["total"] += 1
                    if step.get("passed"):
                        step_stats[step_id]["passed"] += 1
                    step_stats[step_id]["attempts"].append(step.get("attempts", 0))

            # 计算步骤通过率和平均尝试次数
            for step_id, stats in step_stats.items():
                if stats["total"] > 0:
                    metrics.step_pass_rates[step_id] = (
                        stats["passed"] / stats["total"]
                    ) * 100
                if stats["attempts"]:
                    metrics.step_avg_attempts[step_id] = sum(stats["attempts"]) / len(
                        stats["attempts"]
                    )

        # 时间戳
        if runs:
            timestamps: list[datetime] = [
                r.get("timestamp") for r in runs if r.get("timestamp")
            ]  # type: ignore
            if timestamps:
                metrics.first_run_at = min(timestamps)
                metrics.last_run_at = max(timestamps)

        return metrics

    def get_all_experiments_summary(self) -> list[dict[str, Any]]:
        """获取所有实验的汇总信息"""
        summary = []

        for experiment_id in self._experiment_data:
            metrics = self.get_experiment_metrics(experiment_id)
            summary.append(
                {
                    "experiment_id": metrics.experiment_id,
                    "experiment_title": metrics.experiment_title,
                    "experiment_type": metrics.experiment_type,
                    "total_runs": metrics.total_runs,
                    "completed_runs": metrics.completed_runs,
                    "completion_rate": metrics.completion_rate,
                    "avg_score": metrics.avg_score,
                    "avg_duration_seconds": metrics.avg_duration_seconds,
                    "last_run_at": metrics.last_run_at.isoformat()
                    if metrics.last_run_at
                    else None,
                }
            )

        # 按最后运行时间排序
        summary.sort(key=lambda x: x.get("last_run_at") or "", reverse=True)  # type: ignore[misc]

        return summary

    def get_user_experiment_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        获取用户的实验历史

        Args:
            user_id: 用户ID
            limit: 返回记录数限制

        Returns:
            用户实验历史记录列表
        """
        history = []

        for _experiment_id, runs in self._experiment_data.items():
            user_runs = [r for r in runs if r.get("user_id") == user_id]
            history.extend(user_runs)

        # 按时间戳排序
        history.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)  # type: ignore[arg-type]

        return history[:limit]

    def get_popular_experiments(self, limit: int = 10) -> list[dict[str, Any]]:  # type: ignore[misc]
        """
        获取最受欢迎的实验

        Args:
            limit: 返回数量限制

        Returns:
            热门实验列表
        """
        popularity = []

        for experiment_id in self._experiment_data:
            metrics = self.get_experiment_metrics(experiment_id)
            popularity.append(
                {
                    "experiment_id": metrics.experiment_id,
                    "experiment_title": metrics.experiment_title,
                    "total_runs": metrics.total_runs,
                    "avg_score": metrics.avg_score,
                    "completion_rate": metrics.completion_rate,
                }
            )

        # 按运行次数排序
        popularity.sort(key=lambda x: x["total_runs"], reverse=True)

        return popularity[:limit]

    def clear_old_data(self, days: int = 30) -> int:
        """
        清理旧数据

        Args:
            days: 保留天数

        Returns:
            清理的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        total_cleared = 0

        for _exp_id in list(self._experiment_data.keys()):  # 使用_前缀避免未使用警告
            runs = self._experiment_data[_exp_id]
            original_count = len(runs)

            # 保留最近的数据
            self._experiment_data[_exp_id] = [
                r
                for r in runs
                if r.get("timestamp", datetime.min) > cutoff_date  # type: ignore[arg-type]
            ]

            cleared = original_count - len(self._experiment_data[_exp_id])
            total_cleared += cleared

            # 如果没有数据了,删除实验记录
            if not self._experiment_data[_exp_id]:
                del self._experiment_data[_exp_id]

        # 清除缓存
        self._cached_metrics.clear()
        self._cache_timestamp.clear()

        logger.info(f"清理了 {total_cleared} 条超过 {days} 天的实验记录")
        return total_cleared


# 全局实例
_experiment_metrics_collector: ExperimentMetricsCollector | None = None


def get_experiment_metrics_collector() -> ExperimentMetricsCollector:
    """获取全局实验指标收集器实例"""
    global _experiment_metrics_collector
    if _experiment_metrics_collector is None:
        _experiment_metrics_collector = ExperimentMetricsCollector()  # type: ignore[misc]
    return _experiment_metrics_collector
