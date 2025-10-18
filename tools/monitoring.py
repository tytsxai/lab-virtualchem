"""
高级监控和分析系统

提供实时监控、性能分析、异常追踪等功能
"""

import json
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    tags: dict[str, str]


@dataclass
class Alert:
    """告警信息"""
    level: str  # info, warning, error, critical
    message: str
    timestamp: float
    context: dict[str, Any]


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_points: int = 10000):
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.lock = threading.Lock()

    def record(self, metric_name: str, value: float, tags: dict[str, str] | None = None):
        """记录指标"""
        with self.lock:
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            self.metrics[metric_name].append(point)

    def get_metrics(self, metric_name: str, last_seconds: int | None = None) -> list[MetricPoint]:
        """获取指标数据"""
        with self.lock:
            if metric_name not in self.metrics:
                return []

            points = list(self.metrics[metric_name])

            if last_seconds:
                cutoff = time.time() - last_seconds
                points = [p for p in points if p.timestamp >= cutoff]

            return points

    def get_stats(self, metric_name: str, last_seconds: int | None = None) -> dict[str, float]:
        """获取指标统计信息"""
        points = self.get_metrics(metric_name, last_seconds)

        if not points:
            return {}

        values = [p.value for p in points]

        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
            'p99': statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0]
        }


class SystemMonitor:
    """系统资源监控器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.running = False
        self.thread: threading.Thread | None = None
        self.interval = 5  # 采样间隔(秒)

    def start(self):
        """启动监控"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.collector.record('system.cpu.percent', cpu_percent)

                # 内存使用
                mem = psutil.virtual_memory()
                self.collector.record('system.memory.percent', mem.percent)
                self.collector.record('system.memory.used_mb', mem.used / 1024 / 1024)
                self.collector.record('system.memory.available_mb', mem.available / 1024 / 1024)

                # 磁盘使用
                disk = psutil.disk_usage('/')
                self.collector.record('system.disk.percent', disk.percent)
                self.collector.record('system.disk.free_gb', disk.free / 1024 / 1024 / 1024)

                # 进程信息
                process = psutil.Process()
                self.collector.record('process.cpu.percent', process.cpu_percent())
                self.collector.record('process.memory.rss_mb', process.memory_info().rss / 1024 / 1024)
                self.collector.record('process.threads.count', process.num_threads())

                time.sleep(self.interval)
            except Exception as e:
                print(f"监控错误: {e}")
                time.sleep(self.interval)


class AlertManager:
    """告警管理器"""

    def __init__(self, max_alerts: int = 1000):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.lock = threading.Lock()
        self.rules: list[dict] = []

    def add_rule(self, metric_name: str, threshold: float, operator: str, level: str, message: str):
        """添加告警规则

        Args:
            metric_name: 指标名称
            threshold: 阈值
            operator: 操作符 (>, <, >=, <=, ==)
            level: 告警级别
            message: 告警消息
        """
        self.rules.append({
            'metric_name': metric_name,
            'threshold': threshold,
            'operator': operator,
            'level': level,
            'message': message
        })

    def check_rules(self, collector: MetricsCollector):
        """检查告警规则"""
        for rule in self.rules:
            stats = collector.get_stats(rule['metric_name'], last_seconds=60)

            if not stats:
                continue

            value = stats.get('mean', 0)

            if self._evaluate_condition(value, rule['operator'], rule['threshold']):
                self.create_alert(
                    level=rule['level'],
                    message=rule['message'].format(value=value),
                    context={'metric': rule['metric_name'], 'value': value, 'threshold': rule['threshold']}
                )

    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """评估条件"""
        ops = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b
        }
        return ops.get(operator, lambda _a, _b: False)(value, threshold)

    def create_alert(self, level: str, message: str, context: dict[str, Any] | None = None):
        """创建告警"""
        with self.lock:
            alert = Alert(
                level=level,
                message=message,
                timestamp=time.time(),
                context=context or {}
            )
            self.alerts.append(alert)

    def get_alerts(self, level: str | None = None, last_seconds: int | None = None) -> list[Alert]:
        """获取告警列表"""
        with self.lock:
            alerts = list(self.alerts)

            if level:
                alerts = [a for a in alerts if a.level == level]

            if last_seconds:
                cutoff = time.time() - last_seconds
                alerts = [a for a in alerts if a.timestamp >= cutoff]

            return alerts


class ExperimentAnalyzer:
    """实验数据分析器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def analyze_performance(self, experiment_id: str) -> dict[str, Any]:
        """分析实验性能"""
        # 获取实验相关指标
        duration_stats = self.collector.get_stats(f'experiment.{experiment_id}.duration')
        error_count = len(self.collector.get_metrics(f'experiment.{experiment_id}.error'))
        success_count = len(self.collector.get_metrics(f'experiment.{experiment_id}.success'))

        total = error_count + success_count
        success_rate = (success_count / total * 100) if total > 0 else 0

        return {
            'experiment_id': experiment_id,
            'performance': duration_stats,
            'success_rate': success_rate,
            'total_runs': total,
            'error_count': error_count,
            'success_count': success_count
        }

    def analyze_user_patterns(self, user_id: str) -> dict[str, Any]:
        """分析用户行为模式"""
        # 用户完成的实验
        completed = self.collector.get_metrics(f'user.{user_id}.experiment.completed')

        # 平均分数
        scores = self.collector.get_metrics(f'user.{user_id}.score')
        avg_score = statistics.mean([p.value for p in scores]) if scores else 0

        # 常见错误类型
        errors = self.collector.get_metrics(f'user.{user_id}.errors')
        error_types = defaultdict(int)
        for error in errors:
            error_type = error.tags.get('type', 'unknown')
            error_types[error_type] += 1

        return {
            'user_id': user_id,
            'experiments_completed': len(completed),
            'average_score': avg_score,
            'common_errors': dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5])
        }

    def get_trending_experiments(self, last_days: int = 7) -> list[dict[str, Any]]:
        """获取热门实验"""
        cutoff = time.time() - (last_days * 86400)

        experiment_counts = defaultdict(int)

        # 统计所有实验的运行次数
        for metric_name in self.collector.metrics:
            if '.experiment.' in metric_name and '.started' in metric_name:
                points = [p for p in self.collector.metrics[metric_name] if p.timestamp >= cutoff]
                exp_id = metric_name.split('.')[1]
                experiment_counts[exp_id] = len(points)

        # 排序
        trending = [
            {'experiment_id': exp_id, 'runs': count}
            for exp_id, count in sorted(experiment_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return trending[:10]


class MonitoringDashboard:
    """监控仪表板"""

    def __init__(self, collector: MetricsCollector, alert_manager: AlertManager):
        self.collector = collector
        self.alert_manager = alert_manager
        self.analyzer = ExperimentAnalyzer(collector)

    def get_overview(self) -> dict[str, Any]:
        """获取系统概览"""
        return {
            'system': {
                'cpu': self.collector.get_stats('system.cpu.percent', last_seconds=300),
                'memory': self.collector.get_stats('system.memory.percent', last_seconds=300),
                'disk': self.collector.get_stats('system.disk.percent', last_seconds=300)
            },
            'process': {
                'cpu': self.collector.get_stats('process.cpu.percent', last_seconds=300),
                'memory_mb': self.collector.get_stats('process.memory.rss_mb', last_seconds=300),
                'threads': self.collector.get_stats('process.threads.count', last_seconds=300)
            },
            'alerts': {
                'critical': len(self.alert_manager.get_alerts('critical', last_seconds=3600)),
                'error': len(self.alert_manager.get_alerts('error', last_seconds=3600)),
                'warning': len(self.alert_manager.get_alerts('warning', last_seconds=3600))
            }
        }

    def export_report(self, output_path: Path, format: str = 'json'):
        """导出监控报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'overview': self.get_overview(),
            'trending_experiments': self.analyzer.get_trending_experiments(),
            'recent_alerts': [
                {
                    'level': a.level,
                    'message': a.message,
                    'timestamp': datetime.fromtimestamp(a.timestamp).isoformat(),
                    'context': a.context
                }
                for a in self.alert_manager.get_alerts(last_seconds=86400)
            ]
        }

        if format == 'json':
            output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        elif format == 'html':
            html = self._generate_html_report(report)
            output_path.write_text(html, encoding='utf-8')

    def _generate_html_report(self, report: dict[str, Any]) -> str:
        """生成HTML报告"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VirtualChemLab 监控报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        .alert-critical {{ background-color: #e74c3c; color: white; }}
        .alert-error {{ background-color: #e67e22; color: white; }}
        .alert-warning {{ background-color: #f39c12; color: white; }}
        .metric {{ background-color: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🔍 VirtualChemLab 监控报告</h1>
    <p>生成时间: {report['generated_at']}</p>

    <h2>📊 系统概览</h2>
    <div class="metric">
        <h3>CPU使用率</h3>
        <p>平均: {report['overview']['system']['cpu'].get('mean', 0):.2f}%</p>
        <p>最大: {report['overview']['system']['cpu'].get('max', 0):.2f}%</p>
    </div>

    <div class="metric">
        <h3>内存使用</h3>
        <p>平均: {report['overview']['system']['memory'].get('mean', 0):.2f}%</p>
        <p>最大: {report['overview']['system']['memory'].get('max', 0):.2f}%</p>
    </div>

    <h2>🔥 热门实验</h2>
    <table>
        <tr><th>实验ID</th><th>运行次数</th></tr>
        {''.join(f'<tr><td>{exp["experiment_id"]}</td><td>{exp["runs"]}</td></tr>'
                 for exp in report['trending_experiments'])}
    </table>

    <h2>⚠️ 最近告警</h2>
    <table>
        <tr><th>级别</th><th>消息</th><th>时间</th></tr>
        {''.join(f'<tr class="alert-{alert["level"]}"><td>{alert["level"]}</td><td>{alert["message"]}</td><td>{alert["timestamp"]}</td></tr>'
                 for alert in report['recent_alerts'][:20])}
    </table>
</body>
</html>"""


# 全局实例
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
alert_manager = AlertManager()
monitoring_dashboard = MonitoringDashboard(metrics_collector, alert_manager)

# 配置默认告警规则
alert_manager.add_rule('system.cpu.percent', 80, '>', 'warning', 'CPU使用率过高: {value:.2f}%')
alert_manager.add_rule('system.cpu.percent', 95, '>', 'critical', 'CPU使用率严重过高: {value:.2f}%')
alert_manager.add_rule('system.memory.percent', 85, '>', 'warning', '内存使用率过高: {value:.2f}%')
alert_manager.add_rule('system.memory.percent', 95, '>', 'critical', '内存使用率严重过高: {value:.2f}%')
alert_manager.add_rule('system.disk.percent', 90, '>', 'warning', '磁盘使用率过高: {value:.2f}%')


if __name__ == '__main__':
    # 启动监控
    system_monitor.start()

    try:
        print("监控系统已启动，按 Ctrl+C 停止...")

        # 模拟一些指标
        for i in range(10):
            metrics_collector.record('experiment.test.duration', 100 + i * 10)
            metrics_collector.record('user.student1.score', 80 + i)
            time.sleep(2)

            # 检查告警
            alert_manager.check_rules(metrics_collector)

            # 打印概览
            overview = monitoring_dashboard.get_overview()
            print(f"\n系统状态: CPU={overview['system']['cpu'].get('mean', 0):.1f}% "
                  f"内存={overview['system']['memory'].get('mean', 0):.1f}%")

        # 导出报告
        monitoring_dashboard.export_report(Path('monitoring_report.html'), format='html')
        print("\n监控报告已导出到 monitoring_report.html")

    except KeyboardInterrupt:
        print("\n正在停止监控...")
    finally:
        system_monitor.stop()
        print("监控已停止")


