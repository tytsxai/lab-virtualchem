"""
错误采样器

防止高频错误导致日志爆炸，提供智能采样机制
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .exceptions import BaseAppException

logger = logging.getLogger(__name__)


@dataclass
class SamplingRule:
    """采样规则"""

    # 采样阈值：每N次记录1次
    sample_rate: int = 10

    # 时间窗口（秒）：在时间窗口内应用采样
    time_window: int = 60

    # 最小记录间隔（秒）：两次记录之间的最小时间间隔
    min_interval: float = 1.0

    # 突发阈值：如果在短时间内超过此阈值，强制记录
    burst_threshold: int = 100
    burst_window: int = 10  # 秒


@dataclass
class ErrorStats:
    """错误统计信息"""

    count: int = 0  # 总计数
    sampled_count: int = 0  # 已采样计数
    first_seen: datetime | None = None  # 首次出现时间
    last_seen: datetime | None = None  # 最后出现时间
    last_logged: datetime | None = None  # 最后记录时间
    recent_burst_count: int = 0  # 最近突发计数
    burst_start_time: datetime | None = None  # 突发开始时间


class ErrorSampler:
    """错误采样器 - 智能采样高频错误"""

    def __init__(self, default_rule: SamplingRule | None = None):
        """
        初始化采样器

        Args:
            default_rule: 默认采样规则
        """
        self.default_rule = default_rule or SamplingRule()

        # 每个错误签名的统计信息
        self._stats: dict[str, ErrorStats] = defaultdict(ErrorStats)

        # 自定义规则（按错误码）
        self._custom_rules: dict[int, SamplingRule] = {}

        # 白名单（始终记录）
        self._whitelist: set[int] = set()

        # 黑名单（始终不记录）
        self._blacklist: set[int] = set()

    def register_rule(self, error_code: int, rule: SamplingRule) -> None:
        """
        注册自定义采样规则

        Args:
            error_code: 错误码
            rule: 采样规则
        """
        self._custom_rules[error_code] = rule

    def add_to_whitelist(self, error_code: int) -> None:
        """将错误码添加到白名单（始终记录）"""
        self._whitelist.add(error_code)
        if error_code in self._blacklist:
            self._blacklist.remove(error_code)

    def add_to_blacklist(self, error_code: int) -> None:
        """将错误码添加到黑名单（始终不记录）"""
        self._blacklist.add(error_code)
        if error_code in self._whitelist:
            self._whitelist.remove(error_code)

    def should_sample(self, exception: BaseAppException, context: str = "") -> tuple[bool, dict[str, Any]]:
        """
        判断是否应该采样此错误

        Args:
            exception: 异常对象
            context: 上下文

        Returns:
            (是否采样, 采样元数据) 元组
        """
        error_code = exception.error_code.code

        # 白名单 - 始终采样
        if error_code in self._whitelist:
            return True, {"reason": "whitelist"}

        # 黑名单 - 始终不采样
        if error_code in self._blacklist:
            return False, {"reason": "blacklist"}

        # 严重错误和不可恢复错误 - 始终采样
        if exception.error_code.severity == "critical" or not exception.error_code.recoverable:
            return True, {"reason": "critical_or_unrecoverable"}

        # 生成错误签名
        signature = self._generate_signature(exception, context)

        # 获取统计信息
        stats = self._stats[signature]
        now = datetime.now()

        # 更新统计
        stats.count += 1
        if stats.first_seen is None:
            stats.first_seen = now
        stats.last_seen = now

        # 获取采样规则
        rule = self._custom_rules.get(error_code, self.default_rule)

        # 检查突发情况
        if self._is_burst(stats, rule, now):
            # 突发情况 - 记录并重置
            stats.last_logged = now
            stats.sampled_count += 1
            stats.recent_burst_count = 0
            stats.burst_start_time = None

            metadata = {
                "reason": "burst_detected",
                "total_count": stats.count,
                "sampled_count": stats.sampled_count,
                "burst_count": stats.recent_burst_count,
            }

            logger.warning(f"Error burst detected: {signature}")
            return True, metadata

        # 检查首次出现
        if stats.count == 1:
            stats.last_logged = now
            stats.sampled_count += 1
            return True, {
                "reason": "first_occurrence",
                "total_count": stats.count,
                "sampled_count": stats.sampled_count,
            }

        # 检查最小时间间隔
        if stats.last_logged:
            elapsed = (now - stats.last_logged).total_seconds()
            if elapsed < rule.min_interval:
                return False, {
                    "reason": "min_interval_not_met",
                    "elapsed": elapsed,
                    "required": rule.min_interval,
                }

        # 按采样率采样
        if stats.count % rule.sample_rate == 0:
            stats.last_logged = now
            stats.sampled_count += 1

            metadata = {
                "reason": "sampled",
                "total_count": stats.count,
                "sampled_count": stats.sampled_count,
                "sample_rate": rule.sample_rate,
                "suppressed": stats.count - stats.sampled_count,
            }

            return True, metadata

        # 不采样
        return False, {
            "reason": "suppressed",
            "total_count": stats.count,
            "sampled_count": stats.sampled_count,
        }

    def _generate_signature(self, exception: BaseAppException, context: str) -> str:
        """
        生成错误签名

        Args:
            exception: 异常对象
            context: 上下文

        Returns:
            错误签名
        """
        # 使用错误码和上下文生成签名
        return f"{exception.error_code.code}:{exception.error_code.name}:{context}"

    def _is_burst(self, stats: ErrorStats, rule: SamplingRule, now: datetime) -> bool:
        """
        检查是否为突发错误

        Args:
            stats: 错误统计
            rule: 采样规则
            now: 当前时间

        Returns:
            是否为突发
        """
        # 初始化突发追踪
        if stats.burst_start_time is None:
            stats.burst_start_time = now
            stats.recent_burst_count = 1
            return False

        # 计算时间窗口内的突发数量
        elapsed = (now - stats.burst_start_time).total_seconds()

        if elapsed <= rule.burst_window:
            stats.recent_burst_count += 1

            # 检查是否达到突发阈值
            if stats.recent_burst_count >= rule.burst_threshold:
                return True
        else:
            # 时间窗口过期，重置
            stats.burst_start_time = now
            stats.recent_burst_count = 1

        return False

    def get_stats(self, signature: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """
        获取统计信息

        Args:
            signature: 错误签名（可选）

        Returns:
            统计信息
        """
        if signature:
            # 返回特定签名的统计
            stats = self._stats.get(signature)
            if not stats:
                return {}

            return {
                "signature": signature,
                "count": stats.count,
                "sampled_count": stats.sampled_count,
                "suppressed": stats.count - stats.sampled_count,
                "first_seen": stats.first_seen.isoformat() if stats.first_seen else None,
                "last_seen": stats.last_seen.isoformat() if stats.last_seen else None,
                "last_logged": stats.last_logged.isoformat() if stats.last_logged else None,
            }

        # 返回所有统计
        all_stats = []
        for sig, stats in self._stats.items():
            all_stats.append(
                {
                    "signature": sig,
                    "count": stats.count,
                    "sampled_count": stats.sampled_count,
                    "suppressed": stats.count - stats.sampled_count,
                    "first_seen": stats.first_seen.isoformat() if stats.first_seen else None,
                    "last_seen": stats.last_seen.isoformat() if stats.last_seen else None,
                    "last_logged": stats.last_logged.isoformat() if stats.last_logged else None,
                }
            )

        # 按计数排序
        all_stats.sort(key=lambda x: int(x.get("count", 0)), reverse=True)
        return all_stats

    def get_summary(self) -> dict[str, Any]:
        """获取采样摘要"""
        total_errors = sum(stats.count for stats in self._stats.values())
        total_sampled = sum(stats.sampled_count for stats in self._stats.values())
        total_suppressed = total_errors - total_sampled

        return {
            "total_errors": total_errors,
            "total_sampled": total_sampled,
            "total_suppressed": total_suppressed,
            "suppression_rate": f"{(total_suppressed / total_errors * 100):.2f}%" if total_errors > 0 else "0%",
            "unique_signatures": len(self._stats),
            "whitelist_size": len(self._whitelist),
            "blacklist_size": len(self._blacklist),
            "custom_rules": len(self._custom_rules),
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats.clear()
        logger.info("Error sampler stats reset")

    def cleanup_old_stats(self, max_age: timedelta = timedelta(hours=24)) -> None:
        """
        清理旧的统计信息

        Args:
            max_age: 最大保留时间
        """
        now = datetime.now()
        to_remove = []

        for signature, stats in self._stats.items():
            if stats.last_seen and (now - stats.last_seen) > max_age:
                to_remove.append(signature)

        for signature in to_remove:
            del self._stats[signature]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old error signatures")


# 全局采样器实例
error_sampler = ErrorSampler(
    default_rule=SamplingRule(
        sample_rate=10,  # 每10次记录1次
        time_window=60,  # 60秒时间窗口
        min_interval=1.0,  # 最小1秒间隔
        burst_threshold=100,  # 10秒内超过100次视为突发
        burst_window=10,
    )
)

# 预配置规则
# 严重错误和关键错误使用更低的采样率
error_sampler.register_rule(
    5000,  # SYS_INTERNAL_ERROR
    SamplingRule(sample_rate=5, time_window=60),
)

error_sampler.register_rule(
    5001,  # SYS_SERVICE_UNAVAILABLE
    SamplingRule(sample_rate=5, time_window=60),
)

# 网络错误采样率更高（更常见）
error_sampler.register_rule(
    6000,  # NET_CONNECTION_FAILED
    SamplingRule(sample_rate=20, time_window=60),
)

error_sampler.register_rule(
    6001,  # NET_TIMEOUT
    SamplingRule(sample_rate=20, time_window=60),
)
