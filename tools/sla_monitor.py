#!/usr/bin/env python3
"""
SLA监控工具
持续监控系统可用性和性能，生成SLA合规报告
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@dataclass
class DowntimeRecord:
    """停机记录"""

    start_time: datetime
    end_time: datetime | None
    duration_minutes: float
    reason: str
    severity: str  # "maintenance", "incident", "outage"


@dataclass
class PerformanceMetric:
    """性能指标"""

    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    within_target: bool
    target: float


@dataclass
class SLAReport:
    """SLA报告"""

    period_start: datetime
    period_end: datetime
    target_uptime_percent: float
    actual_uptime_percent: float
    total_downtime_minutes: float
    allowed_downtime_minutes: float
    downtime_records: list[DowntimeRecord]
    performance_metrics: list[PerformanceMetric]
    sla_met: bool
    sla_breach_percentage: float
    recommendations: list[str]


class SLAMonitor:
    """SLA监控器"""

    def __init__(self):
        self.config_dir = PROJECT_ROOT / "config"
        self.data_dir = PROJECT_ROOT / "data" / "sla_monitoring"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self.sla_config = self._load_config("sla_config.json")
        self.perf_config = self._load_config("performance.json")

        # 初始化监控数据
        self.downtime_records: list[DowntimeRecord] = []
        self.performance_metrics: list[PerformanceMetric] = []

        # 加载历史数据
        self._load_monitoring_data()

    def _load_config(self, filename: str) -> dict:
        """加载配置文件"""
        try:
            config_path = self.config_dir / filename
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _load_monitoring_data(self):
        """加载监控数据"""
        data_file = self.data_dir / "monitoring_data.json"
        if data_file.exists():
            try:
                with open(data_file, encoding="utf-8") as f:
                    data = json.load(f)

                # 加载停机记录
                for record in data.get("downtime_records", []):
                    self.downtime_records.append(
                        DowntimeRecord(
                            start_time=datetime.fromisoformat(record["start_time"]),
                            end_time=datetime.fromisoformat(record["end_time"])
                            if record["end_time"]
                            else None,
                            duration_minutes=record["duration_minutes"],
                            reason=record["reason"],
                            severity=record["severity"],
                        )
                    )

                # 加载性能指标
                for metric in data.get("performance_metrics", []):
                    self.performance_metrics.append(
                        PerformanceMetric(
                            timestamp=datetime.fromisoformat(metric["timestamp"]),
                            metric_name=metric["metric_name"],
                            value=metric["value"],
                            unit=metric["unit"],
                            within_target=metric["within_target"],
                            target=metric["target"],
                        )
                    )

            except Exception as e:
                print(f"警告: 无法加载监控数据: {e}")

    def _save_monitoring_data(self):
        """保存监控数据"""
        data = {
            "downtime_records": [
                {
                    "start_time": record.start_time.isoformat(),
                    "end_time": record.end_time.isoformat() if record.end_time else None,
                    "duration_minutes": record.duration_minutes,
                    "reason": record.reason,
                    "severity": record.severity,
                }
                for record in self.downtime_records
            ],
            "performance_metrics": [
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "metric_name": metric.metric_name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "within_target": metric.within_target,
                    "target": metric.target,
                }
                for metric in self.performance_metrics
            ],
        }

        data_file = self.data_dir / "monitoring_data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_downtime(
        self,
        start_time: datetime,
        end_time: datetime | None = None,
        reason: str = "Unknown",
        severity: str = "incident",
    ):
        """记录停机时间"""
        if end_time is None:
            end_time = datetime.now()

        duration_minutes = (end_time - start_time).total_seconds() / 60

        record = DowntimeRecord(
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            reason=reason,
            severity=severity,
        )

        self.downtime_records.append(record)
        self._save_monitoring_data()

        print(f"📝 记录停机: {duration_minutes:.2f}分钟 ({reason})")

    def record_performance_metric(self, metric_name: str, value: float, unit: str, target: float):
        """记录性能指标"""
        within_target = value <= target if "latency" in metric_name.lower() else value >= target

        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            within_target=within_target,
            target=target,
        )

        self.performance_metrics.append(metric)
        self._save_monitoring_data()

    def check_system_health(self) -> dict[str, Any]:
        """检查系统健康状况"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 获取告警阈值
            alerts = self.perf_config.get("monitoring", {}).get("alerts", {})

            health = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                },
                "issues": [],
            }

            # 检查CPU
            cpu_threshold = alerts.get("cpu_threshold", 80)
            if cpu_percent > cpu_threshold:
                health["status"] = "degraded"
                health["issues"].append(f"CPU使用率过高: {cpu_percent:.1f}%")

            # 检查内存
            memory_threshold = alerts.get("memory_threshold", 85)
            if memory.percent > memory_threshold:
                health["status"] = "degraded"
                health["issues"].append(f"内存使用率过高: {memory.percent:.1f}%")

            # 检查响应时间
            response_time_threshold = alerts.get("response_time_threshold", 1000)
            recent_metrics = [
                m
                for m in self.performance_metrics
                if m.timestamp > datetime.now() - timedelta(minutes=5)
                and "response_time" in m.metric_name.lower()
            ]

            if recent_metrics:
                avg_response_time = sum(m.value for m in recent_metrics) / len(recent_metrics)
                if avg_response_time > response_time_threshold:
                    health["status"] = "degraded"
                    health["issues"].append(f"平均响应时间过高: {avg_response_time:.0f}ms")

            return health

        except ImportError:
            return {
                "status": "unknown",
                "timestamp": datetime.now().isoformat(),
                "message": "无法检查系统健康 (需要 psutil)",
            }

    def generate_report(
        self, period_start: datetime | None = None, period_end: datetime | None = None
    ) -> SLAReport:
        """生成SLA报告"""
        # 默认报告周期为最近30天
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        # 获取SLA配置
        sla = self.sla_config.get("sla", {})
        availability = sla.get("availability", {})
        target_uptime_percent = availability.get("target_uptime_percentage", 99.5)

        # 计算周期内的停机时间
        period_downtime_records = [
            record
            for record in self.downtime_records
            if period_start <= record.start_time <= period_end
        ]

        total_downtime_minutes = sum(record.duration_minutes for record in period_downtime_records)

        # 计算总时间（分钟）
        total_period_minutes = (period_end - period_start).total_seconds() / 60

        # 计算实际可用性
        actual_uptime_minutes = total_period_minutes - total_downtime_minutes
        actual_uptime_percent = (
            (actual_uptime_minutes / total_period_minutes * 100)
            if total_period_minutes > 0
            else 100.0
        )

        # 允许的停机时间
        allowed_downtime_minutes = total_period_minutes * (1 - target_uptime_percent / 100)

        # 是否满足SLA
        sla_met = actual_uptime_percent >= target_uptime_percent

        # SLA违约百分比
        if not sla_met:
            sla_breach_percentage = target_uptime_percent - actual_uptime_percent
        else:
            sla_breach_percentage = 0.0

        # 生成建议
        recommendations = []

        if not sla_met:
            recommendations.append(
                f"未达到SLA目标 ({actual_uptime_percent:.2f}% < {target_uptime_percent}%)"
            )
            recommendations.append(
                f"需要减少停机时间 {total_downtime_minutes - allowed_downtime_minutes:.2f}分钟"
            )

        if total_downtime_minutes > 0:
            # 分析停机原因
            by_severity = {}
            for record in period_downtime_records:
                by_severity[record.severity] = (
                    by_severity.get(record.severity, 0) + record.duration_minutes
                )

            for severity, minutes in sorted(by_severity.items(), key=lambda x: x[1], reverse=True):
                recommendations.append(f"减少{severity}类型停机 (当前: {minutes:.2f}分钟)")

        # 性能指标建议
        period_metrics = [
            metric
            for metric in self.performance_metrics
            if period_start <= metric.timestamp <= period_end
        ]

        failing_metrics = [m for m in period_metrics if not m.within_target]
        if failing_metrics:
            recommendations.append(f"改善性能指标: {len(failing_metrics)}个指标未达标")

        if actual_uptime_percent < 99.0:
            recommendations.append("考虑实施高可用性架构")
            recommendations.append("增加监控和告警覆盖")

        return SLAReport(
            period_start=period_start,
            period_end=period_end,
            target_uptime_percent=target_uptime_percent,
            actual_uptime_percent=actual_uptime_percent,
            total_downtime_minutes=total_downtime_minutes,
            allowed_downtime_minutes=allowed_downtime_minutes,
            downtime_records=period_downtime_records,
            performance_metrics=period_metrics,
            sla_met=sla_met,
            sla_breach_percentage=sla_breach_percentage,
            recommendations=recommendations,
        )

    def print_report(self, report: SLAReport):
        """打印SLA报告"""
        print("\n" + "=" * 70)
        print("📊 SLA合规报告")
        print("=" * 70)
        print(f"报告周期: {report.period_start.date()} 至 {report.period_end.date()}")
        print(f"报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")

        # 可用性指标
        print("🎯 可用性指标\n")
        print(f"目标可用性: {report.target_uptime_percent}%")
        print(f"实际可用性: {report.actual_uptime_percent:.4f}%")
        print(f"总停机时间: {report.total_downtime_minutes:.2f}分钟")
        print(f"允许停机时间: {report.allowed_downtime_minutes:.2f}分钟")

        status_icon = "✅" if report.sla_met else "❌"
        status_text = "达标" if report.sla_met else "未达标"
        print(f"\nSLA状态: {status_icon} {status_text}")

        if not report.sla_met:
            print(f"违约幅度: {report.sla_breach_percentage:.4f}%")

        # 停机记录
        if report.downtime_records:
            print("\n" + "=" * 70)
            print("📋 停机记录")
            print("=" * 70 + "\n")

            for i, record in enumerate(report.downtime_records, 1):
                print(f"{i}. {record.start_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"   持续时间: {record.duration_minutes:.2f}分钟")
                print(f"   严重程度: {record.severity}")
                print(f"   原因: {record.reason}")
                print()

            # 按严重程度统计
            by_severity = {}
            for record in report.downtime_records:
                by_severity[record.severity] = (
                    by_severity.get(record.severity, 0) + record.duration_minutes
                )

            print("按严重程度统计:")
            for severity, minutes in sorted(by_severity.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {severity}: {minutes:.2f}分钟")

        # 性能指标
        if report.performance_metrics:
            print("\n" + "=" * 70)
            print("⚡ 性能指标")
            print("=" * 70 + "\n")

            # 按指标名称分组
            by_metric = {}
            for metric in report.performance_metrics:
                if metric.metric_name not in by_metric:
                    by_metric[metric.metric_name] = []
                by_metric[metric.metric_name].append(metric)

            for metric_name, metrics in by_metric.items():
                values = [m.value for m in metrics]
                if values:
                    avg_value = sum(values) / len(values)
                    min_value = min(values)
                    max_value = max(values)
                    target = metrics[0].target
                    unit = metrics[0].unit

                    within_target_count = sum(1 for m in metrics if m.within_target)
                    compliance_rate = (within_target_count / len(metrics) * 100) if metrics else 0

                    icon = "✅" if compliance_rate >= 95 else "⚠️" if compliance_rate >= 80 else "❌"

                    print(f"{icon} {metric_name}")
                    print(f"   平均: {avg_value:.2f} {unit} (目标: {target} {unit})")
                    print(f"   范围: {min_value:.2f} - {max_value:.2f} {unit}")
                    print(
                        f"   达标率: {compliance_rate:.1f}% ({within_target_count}/{len(metrics)})"
                    )
                    print()

        # 建议
        if report.recommendations:
            print("=" * 70)
            print("💡 改进建议")
            print("=" * 70 + "\n")

            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")

        print("\n" + "=" * 70 + "\n")

    def save_report(self, report: SLAReport, filepath: Path):
        """保存报告到JSON文件"""
        report_data = {
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "target_uptime_percent": report.target_uptime_percent,
            "actual_uptime_percent": report.actual_uptime_percent,
            "total_downtime_minutes": report.total_downtime_minutes,
            "allowed_downtime_minutes": report.allowed_downtime_minutes,
            "sla_met": report.sla_met,
            "sla_breach_percentage": report.sla_breach_percentage,
            "downtime_records": [
                {
                    "start_time": record.start_time.isoformat(),
                    "end_time": record.end_time.isoformat() if record.end_time else None,
                    "duration_minutes": record.duration_minutes,
                    "reason": record.reason,
                    "severity": record.severity,
                }
                for record in report.downtime_records
            ],
            "performance_metrics": [
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "metric_name": metric.metric_name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "within_target": metric.within_target,
                    "target": metric.target,
                }
                for metric in report.performance_metrics
            ],
            "recommendations": report.recommendations,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"📄 详细报告已保存到: {filepath}")

    def simulate_monitoring_data(self):
        """模拟一些监控数据（用于演示）"""
        print("🔄 生成模拟监控数据...\n")

        # 模拟一些停机事件
        now = datetime.now()

        # 10天前的维护窗口
        self.record_downtime(
            start_time=now - timedelta(days=10, hours=2),
            end_time=now - timedelta(days=10, hours=1, minutes=45),
            reason="计划维护：系统升级",
            severity="maintenance",
        )

        # 5天前的小故障
        self.record_downtime(
            start_time=now - timedelta(days=5, hours=14),
            end_time=now - timedelta(days=5, hours=14, minutes=5),
            reason="数据库连接超时",
            severity="incident",
        )

        # 模拟性能指标
        import random

        for day in range(30):
            for hour in range(0, 24, 2):  # 每2小时一次
                now - timedelta(days=day, hours=hour)

                # API响应时间
                response_time = random.gauss(150, 50)  # 平均150ms，标准差50ms
                self.record_performance_metric(
                    metric_name="api_response_time", value=response_time, unit="ms", target=200
                )

                # CPU使用率
                cpu_usage = random.gauss(45, 15)
                self.record_performance_metric(
                    metric_name="cpu_usage", value=cpu_usage, unit="%", target=70
                )

        print("✅ 模拟数据生成完成\n")


def main():
    """主函数"""
    # 设置UTF-8输出
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    monitor = SLAMonitor()

    # 检查是否有监控数据
    if not monitor.downtime_records and not monitor.performance_metrics:
        print("ℹ️  未找到历史监控数据，生成模拟数据用于演示...")
        monitor.simulate_monitoring_data()

    # 生成报告
    report = monitor.generate_report()
    monitor.print_report(report)

    # 保存报告
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"sla_report_{timestamp}.json"
    monitor.save_report(report, report_file)

    # 检查系统健康
    print("\n" + "=" * 70)
    print("🏥 当前系统健康状态")
    print("=" * 70 + "\n")

    health = monitor.check_system_health()
    if health.get("status") == "healthy":
        print("✅ 系统运行正常")
    elif health.get("status") == "degraded":
        print("⚠️  系统性能下降")
        for issue in health.get("issues", []):
            print(f"   - {issue}")
    else:
        print("❓ 无法确定系统状态")
        print(f"   {health.get('message', '')}")

    print()

    # 返回退出码
    return 0 if report.sla_met else 1


if __name__ == "__main__":
    sys.exit(main())
