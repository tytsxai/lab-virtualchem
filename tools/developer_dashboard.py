"""
开发者仪表板

提供实时项目状态、代码质量、性能指标的可视化界面
"""

import http.server
import json
import socketserver
import subprocess
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


class ProjectMetrics:
    """项目指标收集器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_code_stats(self) -> dict[str, Any]:
        """获取代码统计"""
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "python_files": 0,
            "python_lines": 0,
            "test_files": 0,
            "test_lines": 0,
        }

        # 统计Python文件
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file) or "build" in str(py_file) or "dist" in str(py_file):
                continue

            stats["total_files"] += 1

            lines = py_file.read_text(encoding="utf-8").split("\n")
            line_count = len(lines)
            stats["total_lines"] += line_count

            if "test" in str(py_file):
                stats["test_files"] += 1
                stats["test_lines"] += line_count
            else:
                stats["python_files"] += 1
                stats["python_lines"] += line_count

        return stats

    def get_git_stats(self) -> dict[str, Any]:
        """获取Git统计"""
        try:
            # 获取提交数
            commit_count = subprocess.check_output(
                ["git", "rev-list", "--count", "HEAD"], cwd=self.project_root, text=True
            ).strip()

            # 获取贡献者数
            contributors = (
                subprocess.check_output(["git", "shortlog", "-sn", "--all"], cwd=self.project_root, text=True)
                .strip()
                .split("\n")
            )

            # 获取最近提交
            recent_commit = (
                subprocess.check_output(
                    ["git", "log", "-1", "--pretty=format:%h|%an|%ar|%s"], cwd=self.project_root, text=True
                )
                .strip()
                .split("|")
            )

            return {
                "total_commits": int(commit_count),
                "contributors_count": len(contributors),
                "last_commit": {
                    "hash": recent_commit[0] if len(recent_commit) > 0 else "",
                    "author": recent_commit[1] if len(recent_commit) > 1 else "",
                    "time": recent_commit[2] if len(recent_commit) > 2 else "",
                    "message": recent_commit[3] if len(recent_commit) > 3 else "",
                },
            }
        except Exception:  # noqa: BLE001
            return {"total_commits": 0, "contributors_count": 0, "last_commit": {}}

    def get_dependency_stats(self) -> dict[str, Any]:
        """获取依赖统计"""
        requirements_file = self.project_root / "requirements.txt"

        if not requirements_file.exists():
            return {"total_dependencies": 0, "dependencies": []}

        dependencies = []
        for line in requirements_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                dependencies.append(line)

        return {"total_dependencies": len(dependencies), "dependencies": dependencies}

    def get_test_stats(self) -> dict[str, Any]:
        """获取测试统计"""
        test_results_file = self.project_root / "test_results.xml"

        if not test_results_file.exists():
            return {"total_tests": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0}

        # 简单解析XML (实际应使用XML解析器)
        content = test_results_file.read_text(encoding="utf-8")

        import re

        tests_match = re.search(r'tests="(\d+)"', content)
        failures_match = re.search(r'failures="(\d+)"', content)
        errors_match = re.search(r'errors="(\d+)"', content)
        skipped_match = re.search(r'skipped="(\d+)"', content)

        total = int(tests_match.group(1)) if tests_match else 0
        failures = int(failures_match.group(1)) if failures_match else 0
        errors = int(errors_match.group(1)) if errors_match else 0
        skipped = int(skipped_match.group(1)) if skipped_match else 0
        passed = total - failures - errors - skipped

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failures + errors,
            "skipped": skipped,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
        }

    def get_coverage_stats(self) -> dict[str, Any]:
        """获取覆盖率统计"""
        coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            return {"coverage_percent": 0, "total_statements": 0, "covered_statements": 0}

        data = json.loads(coverage_file.read_text(encoding="utf-8"))

        return {
            "coverage_percent": data["totals"]["percent_covered"],
            "total_statements": data["totals"]["num_statements"],
            "covered_statements": data["totals"]["covered_lines"],
        }


class DashboardGenerator:
    """仪表板HTML生成器"""

    @staticmethod
    def generate_dashboard(metrics: dict[str, Any], output_path: Path):
        """生成仪表板HTML"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VirtualChemLab 开发者仪表板</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            color: white;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .subtitle {{
            color: rgba(255,255,255,0.9);
            margin-bottom: 30px;
            font-size: 1.1em;
        }}

        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}

        .card-icon {{
            font-size: 2em;
            margin-right: 15px;
        }}

        .card-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
        }}

        .metric {{
            margin: 15px 0;
        }}

        .metric-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .metric-small {{
            font-size: 1.2em;
        }}

        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .status-good {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-bad {{ color: #e74c3c; }}

        .commit-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
        }}

        .commit-hash {{
            font-family: monospace;
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 10px;
        }}

        .stat-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .stat-number {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-label {{
            color: #7f8c8d;
            font-size: 0.85em;
            margin-top: 5px;
        }}

        .refresh-time {{
            color: rgba(255,255,255,0.8);
            text-align: center;
            margin-top: 30px;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .dashboard {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 VirtualChemLab 开发者仪表板</h1>
        <p class="subtitle">实时项目状态与指标监控</p>

        <div class="dashboard">
            <!-- 代码统计 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📝</div>
                    <div class="card-title">代码统计</div>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number">{metrics["code_stats"]["python_files"]}</div>
                        <div class="stat-label">源代码文件</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{metrics["code_stats"]["python_lines"]:,}</div>
                        <div class="stat-label">代码行数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{metrics["code_stats"]["test_files"]}</div>
                        <div class="stat-label">测试文件</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{metrics["code_stats"]["test_lines"]:,}</div>
                        <div class="stat-label">测试行数</div>
                    </div>
                </div>
            </div>

            <!-- Git统计 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🔧</div>
                    <div class="card-title">Git 仓库</div>
                </div>
                <div class="metric">
                    <div class="metric-label">总提交数</div>
                    <div class="metric-value metric-small">{metrics["git_stats"]["total_commits"]}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">贡献者</div>
                    <div class="metric-value metric-small">{metrics["git_stats"]["contributors_count"]}</div>
                </div>
"""

        if metrics["git_stats"].get("last_commit"):
            commit = metrics["git_stats"]["last_commit"]
            html += f"""
                <div class="commit-info">
                    <div><strong>最后提交:</strong></div>
                    <div style="margin-top: 8px;">
                        <span class="commit-hash">{commit.get("hash", "")}</span>
                    </div>
                    <div style="margin-top: 8px; color: #7f8c8d;">
                        {commit.get("author", "")} • {commit.get("time", "")}
                    </div>
                    <div style="margin-top: 8px;">
                        {commit.get("message", "")}
                    </div>
                </div>
"""

        html += f"""
            </div>

            <!-- 测试状态 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🧪</div>
                    <div class="card-title">测试状态</div>
                </div>
                <div class="metric">
                    <div class="metric-label">总测试数</div>
                    <div class="metric-value">{metrics["test_stats"]["total_tests"]}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">通过率</div>
                    <div class="metric-value {DashboardGenerator._get_status_class(metrics["test_stats"]["pass_rate"], 90, 70)}">
                        {metrics["test_stats"]["pass_rate"]:.1f}%
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {metrics["test_stats"]["pass_rate"]}%">
                        {metrics["test_stats"]["pass_rate"]:.0f}%
                    </div>
                </div>
                <div class="stats-grid" style="margin-top: 15px;">
                    <div class="stat-item">
                        <div class="stat-number status-good">{metrics["test_stats"]["passed"]}</div>
                        <div class="stat-label">通过</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number status-bad">{metrics["test_stats"]["failed"]}</div>
                        <div class="stat-label">失败</div>
                    </div>
                </div>
            </div>

            <!-- 代码覆盖率 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📊</div>
                    <div class="card-title">代码覆盖率</div>
                </div>
                <div class="metric">
                    <div class="metric-label">覆盖率</div>
                    <div class="metric-value {DashboardGenerator._get_status_class(metrics["coverage_stats"]["coverage_percent"], 80, 60)}">
                        {metrics["coverage_stats"]["coverage_percent"]:.1f}%
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {metrics["coverage_stats"]["coverage_percent"]}%">
                        {metrics["coverage_stats"]["coverage_percent"]:.0f}%
                    </div>
                </div>
                <div class="metric" style="margin-top: 15px;">
                    <div class="metric-label">已覆盖 / 总语句</div>
                    <div class="metric-value metric-small">
                        {metrics["coverage_stats"]["covered_statements"]} / {metrics["coverage_stats"]["total_statements"]}
                    </div>
                </div>
            </div>

            <!-- 依赖管理 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📦</div>
                    <div class="card-title">依赖管理</div>
                </div>
                <div class="metric">
                    <div class="metric-label">依赖包数量</div>
                    <div class="metric-value">{metrics["dependency_stats"]["total_dependencies"]}</div>
                </div>
                <div style="max-height: 200px; overflow-y: auto; margin-top: 15px;">
"""

        for dep in metrics["dependency_stats"]["dependencies"][:10]:
            html += f'                    <div style="padding: 5px 0; border-bottom: 1px solid #ecf0f1; font-size: 0.9em;">{dep}</div>\n'

        if len(metrics["dependency_stats"]["dependencies"]) > 10:
            html += f'                    <div style="padding: 10px 0; color: #7f8c8d; font-size: 0.9em;">...还有 {len(metrics["dependency_stats"]["dependencies"]) - 10} 个依赖</div>\n'

        html += f"""
                </div>
            </div>

            <!-- 项目健康度 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">💚</div>
                    <div class="card-title">项目健康度</div>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number status-{DashboardGenerator._get_health_status(metrics["test_stats"]["pass_rate"])}">
                            {DashboardGenerator._get_health_emoji(metrics["test_stats"]["pass_rate"])}
                        </div>
                        <div class="stat-label">测试健康度</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number status-{DashboardGenerator._get_health_status(metrics["coverage_stats"]["coverage_percent"])}">
                            {DashboardGenerator._get_health_emoji(metrics["coverage_stats"]["coverage_percent"])}
                        </div>
                        <div class="stat-label">覆盖率健康度</div>
                    </div>
                </div>
                <div class="metric" style="margin-top: 20px;">
                    <div class="metric-label">总体评分</div>
                    <div class="metric-value {DashboardGenerator._get_status_class(DashboardGenerator._calculate_overall_score(metrics), 80, 60)}">
                        {DashboardGenerator._calculate_overall_score(metrics):.0f}/100
                    </div>
                </div>
            </div>
        </div>

        <p class="refresh-time">
            📅 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
            <a href="javascript:location.reload()" style="color: white; text-decoration: none;">🔄 刷新</a>
        </p>
    </div>

    <script>
        // 自动刷新 (每5分钟)
        setTimeout(() => location.reload(), 300000);
    </script>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")

    @staticmethod
    def _get_status_class(value: float, good_threshold: float, warning_threshold: float) -> str:
        """获取状态CSS类"""
        if value >= good_threshold:
            return "status-good"
        elif value >= warning_threshold:
            return "status-warning"
        else:
            return "status-bad"

    @staticmethod
    def _get_health_status(value: float) -> str:
        """获取健康状态"""
        if value >= 80:
            return "good"
        elif value >= 60:
            return "warning"
        else:
            return "bad"

    @staticmethod
    def _get_health_emoji(value: float) -> str:
        """获取健康表情"""
        if value >= 80:
            return "✅"
        elif value >= 60:
            return "⚠️"
        else:
            return "❌"

    @staticmethod
    def _calculate_overall_score(metrics: dict[str, Any]) -> float:
        """计算总体评分"""
        test_score = metrics["test_stats"]["pass_rate"] * 0.4
        coverage_score = metrics["coverage_stats"]["coverage_percent"] * 0.4

        # 代码质量分数 (基于测试覆盖率)
        test_ratio = metrics["code_stats"]["test_lines"] / max(metrics["code_stats"]["python_lines"], 1)
        quality_score = min(test_ratio * 100, 20)

        return test_score + coverage_score + quality_score


class DashboardServer:
    """仪表板Web服务器"""

    def __init__(self, dashboard_path: Path, port: int = 8888):
        self.dashboard_path = dashboard_path
        self.port = port
        self.server: socketserver.TCPServer | None = None
        self.server_thread: threading.Thread | None = None

    def start(self):
        """启动服务器"""
        # 切换到仪表板目录
        os.chdir(self.dashboard_path.parent)

        # 创建HTTP服务器
        Handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.TCPServer(("", self.port), Handler)

        # 在新线程中运行
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        print(f"仪表板服务器启动成功: http://localhost:{self.port}/{self.dashboard_path.name}")

        # 自动打开浏览器
        webbrowser.open(f"http://localhost:{self.port}/{self.dashboard_path.name}")

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("仪表板服务器已停止")


# 使用示例
if __name__ == "__main__":
    import os

    project_root = Path(".")

    # 收集指标
    print("收集项目指标...")
    collector = ProjectMetrics(project_root)

    metrics = {
        "code_stats": collector.get_code_stats(),
        "git_stats": collector.get_git_stats(),
        "test_stats": collector.get_test_stats(),
        "coverage_stats": collector.get_coverage_stats(),
        "dependency_stats": collector.get_dependency_stats(),
    }

    # 生成仪表板
    dashboard_path = project_root / "developer_dashboard.html"
    print(f"生成仪表板: {dashboard_path}")
    DashboardGenerator.generate_dashboard(metrics, dashboard_path)

    # 启动服务器
    server = DashboardServer(dashboard_path, port=8888)
    server.start()

    try:
        print("\n按 Ctrl+C 停止服务器...")
        input()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
