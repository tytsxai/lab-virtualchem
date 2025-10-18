"""
监控仪表板

提供实时监控数据的可视化展示
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MonitoringDashboard:
    """监控仪表板"""

    def __init__(
        self,
        frontend_monitor=None,
        behavior_tracker=None,
        backend_monitor=None,
        trace_manager=None,
        alert_manager=None,
    ):
        from .alerting import alert_manager as am
        from .backend_monitor import backend_monitor as bm
        from .distributed_tracing import get_trace_manager
        from .frontend_monitor import behavior_tracker as bt
        from .frontend_monitor import frontend_monitor as fm

        self.frontend_monitor = frontend_monitor or fm
        self.behavior_tracker = behavior_tracker or bt
        self.backend_monitor = backend_monitor or bm
        self.trace_manager = trace_manager or get_trace_manager()
        self.alert_manager = alert_manager or am

    def get_overview(self) -> dict[str, Any]:
        """获取总览数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "health": self.backend_monitor.get_health_status(),
            "alerts": {
                "active": len(self.alert_manager.get_active_alerts()),
                "by_severity": self.alert_manager.get_alert_stats()["by_severity"],
            },
            "errors": {
                "total": self.frontend_monitor.get_error_stats()["total_errors"],
                "by_level": self.frontend_monitor.get_error_stats()["by_level"],
            },
            "events": self.behavior_tracker.get_event_stats(),
            "performance": self.backend_monitor.get_performance_summary(),
        }

    def get_system_metrics(self) -> dict[str, Any]:
        """获取系统指标"""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
            "memory": {
                "total_gb": memory.total / 1024 / 1024 / 1024,
                "used_gb": memory.used / 1024 / 1024 / 1024,
                "available_gb": memory.available / 1024 / 1024 / 1024,
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": disk.total / 1024 / 1024 / 1024,
                "used_gb": disk.used / 1024 / 1024 / 1024,
                "free_gb": disk.free / 1024 / 1024 / 1024,
                "percent": disk.percent,
            },
        }

    def get_error_summary(self, limit: int = 100) -> dict[str, Any]:
        """获取错误摘要"""
        stats = self.frontend_monitor.get_error_stats()
        recent_errors = self.frontend_monitor.get_errors(limit=limit)

        return {
            "stats": stats,
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "level": e.level.value,
                    "message": e.message,
                    "component": e.component,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in recent_errors[-10:]
            ],
        }

    def get_trace_summary(self, since_minutes: int = 60) -> dict[str, Any]:
        """获取追踪摘要"""
        return self.trace_manager.get_statistics(since_minutes=since_minutes)

    def get_alert_summary(self) -> dict[str, Any]:
        """获取告警摘要"""
        stats = self.alert_manager.get_alert_stats()
        active_alerts = self.alert_manager.get_active_alerts()

        return {
            "stats": stats,
            "active_alerts": [
                {
                    "alert_id": a.alert_id,
                    "rule_name": a.rule_name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in active_alerts
            ],
        }

    def generate_html_report(self, output_file: Path) -> None:
        """生成HTML报告"""
        self.get_overview()
        self.get_system_metrics()
        self.get_error_summary()
        self.get_trace_summary()
        self.get_alert_summary()

        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VirtualChemLab 监控仪表板</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #666;
            font-size: 16px;
            text-transform: uppercase;
        }}
        .metric {{
            font-size: 36px;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }}
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .status.healthy {{ background: #4CAF50; color: white; }}
        .status.unhealthy {{ background: #f44336; color: white; }}
        .status.warning {{ background: #ff9800; color: white; }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: #4CAF50;
            transition: width 0.3s;
        }}
        .progress-fill.warning {{ background: #ff9800; }}
        .progress-fill.critical {{ background: #f44336; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f5f5f5;
            font-weight: bold;
        }}
        .timestamp {{
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 VirtualChemLab 监控仪表板</h1>
        <p class="timestamp">更新时间: {overview['timestamp']}</p>

        <div class="dashboard">
            <!-- 健康状态 -->
            <div class="card">
                <h2>系统健康</h2>
                <div class="metric">
                    <span class="status {overview['health']['status']}">
                        {overview['health']['status'].upper()}
                    </span>
                </div>
                <p>运行时间: {overview['health']['uptime_seconds']:.0f} 秒</p>
            </div>

            <!-- CPU -->
            <div class="card">
                <h2>CPU 使用率</h2>
                <div class="metric">{system_metrics['cpu']['percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {'warning' if system_metrics['cpu']['percent'] > 70 else 'critical' if system_metrics['cpu']['percent'] > 85 else ''}"
                         style="width: {system_metrics['cpu']['percent']}%"></div>
                </div>
            </div>

            <!-- 内存 -->
            <div class="card">
                <h2>内存使用率</h2>
                <div class="metric">{system_metrics['memory']['percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {'warning' if system_metrics['memory']['percent'] > 80 else 'critical' if system_metrics['memory']['percent'] > 90 else ''}"
                         style="width: {system_metrics['memory']['percent']}%"></div>
                </div>
                <p>{system_metrics['memory']['used_gb']:.1f} GB / {system_metrics['memory']['total_gb']:.1f} GB</p>
            </div>

            <!-- 磁盘 -->
            <div class="card">
                <h2>磁盘使用率</h2>
                <div class="metric">{system_metrics['disk']['percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {'warning' if system_metrics['disk']['percent'] > 80 else 'critical' if system_metrics['disk']['percent'] > 90 else ''}"
                         style="width: {system_metrics['disk']['percent']}%"></div>
                </div>
                <p>{system_metrics['disk']['used_gb']:.1f} GB / {system_metrics['disk']['total_gb']:.1f} GB</p>
            </div>

            <!-- 错误 -->
            <div class="card">
                <h2>错误统计</h2>
                <div class="metric">{error_summary['stats']['total_errors']}</div>
                <p>唯一错误: {error_summary['stats']['unique_errors']}</p>
            </div>

            <!-- 告警 -->
            <div class="card">
                <h2>活跃告警</h2>
                <div class="metric">{overview['alerts']['active']}</div>
            </div>

            <!-- 追踪 -->
            <div class="card">
                <h2>追踪统计</h2>
                <div class="metric">{trace_summary.get('total_traces', 0)}</div>
                <p>总跨度: {trace_summary.get('total_spans', 0)}</p>
            </div>

            <!-- 事件 -->
            <div class="card">
                <h2>用户事件</h2>
                <div class="metric">{overview['events']['total_events']}</div>
                <p>活跃会话: {overview['events']['active_sessions']}</p>
            </div>
        </div>

        <!-- 最近错误 -->
        <div class="card" style="margin-top: 20px;">
            <h2>最近错误</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>级别</th>
                        <th>组件</th>
                        <th>消息</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(""'
                    <tr>
                        <td>{e['timestamp']}</td>
                        <td>{e['level']}</td>
                        <td>{e['component'] or '-'}</td>
                        <td>{e['message']}</td>
                    </tr>
                    ''' for e in error_summary['recent_errors'])}
                </tbody>
            </table>
        </div>

        <!-- 活跃告警 -->
        {"" if not alert_summary['active_alerts'] else ""'
        <div class="card" style="margin-top: 20px;">
            <h2>活跃告警</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>级别</th>
                        <th>规则</th>
                        <th>消息</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f"<tr><td>{a['timestamp']}</td><td>{a['severity']}</td><td>{a['rule_name']}</td><td>{a['message']}</td></tr>" for a in alert_summary['active_alerts'])}
                </tbody>
            </table>
        </div>
        '''}
    </div>
</body>
</html>
        """

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    def export_json_report(self, output_file: Path) -> None:
        """导出JSON报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "overview": self.get_overview(),
            "system_metrics": self.get_system_metrics(),
            "error_summary": self.get_error_summary(),
            "trace_summary": self.get_trace_summary(),
            "alert_summary": self.get_alert_summary(),
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


# 全局仪表板实例
_dashboard: MonitoringDashboard | None = None


def get_dashboard() -> MonitoringDashboard:
    """获取全局仪表板"""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard
