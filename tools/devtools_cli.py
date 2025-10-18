"""
开发工具统一命令行界面

整合所有开发工具的CLI入口
"""

import sys
from pathlib import Path

import click

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.group()
@click.version_option(version="1.3.0", prog_name="VirtualChemLab DevTools")
def cli():
    """VirtualChemLab 开发工具集"""
    pass


@cli.group()
def monitor():
    """监控和分析工具"""
    pass


@monitor.command("start")
@click.option("--port", default=8888, help="服务器端口")
def monitor_start(_port):
    """启动监控系统"""
    from pathlib import Path

    from tools.monitoring import monitoring_dashboard, system_monitor

    click.echo("[*] 启动监控系统...")

    # 启动系统监控
    system_monitor.start()

    # 生成报告
    monitoring_dashboard.export_report(Path("monitoring_report.html"), format="html")

    click.echo("[OK] 监控系统已启动")
    click.echo("[*] 报告已生成: monitoring_report.html")

    try:
        click.echo("\n按 Ctrl+C 停止监控...")
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system_monitor.stop()
        click.echo("\n[OK] 监控已停止")


@monitor.command("report")
@click.option("--format", type=click.Choice(["html", "json"]), default="html", help="报告格式")
@click.option("--output", default="monitoring_report.html", help="输出文件")
def monitor_report(format, output):
    """生成监控报告"""
    from pathlib import Path

    from tools.monitoring import monitoring_dashboard

    click.echo(f"[*] 生成监控报告 ({format})...")
    monitoring_dashboard.export_report(Path(output), format=format)
    click.echo(f"[OK] 报告已生成: {output}")


@cli.group()
def profile():
    """性能分析工具"""
    pass


@profile.command("function")
@click.argument("module")
@click.argument("function")
def profile_function(module, function):
    """分析函数性能"""
    import importlib

    from tools.profiler import FunctionProfiler

    click.echo(f"[*] 分析函数: {module}.{function}")

    try:
        mod = importlib.import_module(module)
        func = getattr(mod, function)

        profiler = FunctionProfiler()
        wrapped = profiler.profile_function(func)
        wrapped()

        profiler.print_stats()

        results = profiler.get_results()
        if results:
            r = results[0]
            click.echo("\n[OK] 分析完成:")
            click.echo(f"   总时间: {r.total_time:.3f}秒")
            click.echo(f"   调用次数: {r.calls}")
            click.echo(f"   平均时间: {r.avg_time * 1000:.3f}ms")
            click.echo(f"   内存峰值: {r.memory_peak_mb:.2f}MB")
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)


@profile.command("complexity")
@click.option("--path", default="src", help="要分析的目录")
@click.option("--top", default=10, help="显示前N个最复杂文件")
def profile_complexity(path, top):
    """分析代码复杂度"""
    from pathlib import Path

    from tools.profiler import CodeComplexityAnalyzer

    click.echo(f"[*] 分析代码复杂度: {path}")

    results = CodeComplexityAnalyzer.analyze_directory(Path(path))

    click.echo(f"\n最复杂的 {top} 个文件:")
    click.echo("-" * 80)

    for i, result in enumerate(results[:top], 1):
        click.echo(f"\n{i}. {result['file']}")
        click.echo(f"   复杂度分数: {result['complexity_score']}/100")
        click.echo(f"   代码行数: {result['code_lines']}")
        click.echo(f"   类: {result['class_count']}, 函数: {result['function_count']}")
        click.echo(f"   最大嵌套: {result['max_nesting_level']}")


@profile.command("benchmark")
@click.argument("name")
@click.option("--runs", default=100, help="运行次数")
def profile_benchmark(name, runs):
    """运行基准测试"""
    click.echo(f"[*] 运行基准测试: {name} ({runs}次)")
    # TODO: 实现基准测试逻辑
    click.echo("[OK] 基准测试完成")


@cli.group()
def test():
    """测试工具"""
    pass


@test.command("run")
@click.option("--path", default="tests/", help="测试路径")
@click.option("--coverage/--no-coverage", default=True, help="启用覆盖率")
def test_run(path, coverage):
    """运行测试"""
    from pathlib import Path

    from tools.test_automation import CoverageAnalyzer, TestRunner

    project_root = Path(".")

    if coverage:
        click.echo("[*] 运行测试 (带覆盖率)...")
        analyzer = CoverageAnalyzer(project_root)
        report = analyzer.run_coverage(path)

        if report:
            click.echo("\n[OK] 测试完成")
            click.echo(f"   覆盖率: {report.coverage_percent:.2f}%")
            click.echo(f"   总语句: {report.total_statements}")
            click.echo(f"   已覆盖: {report.covered_statements}")
    else:
        click.echo("[*] 运行测试...")
        runner = TestRunner(project_root)
        runner.run_pytest(path)

        summary = runner.get_summary()
        click.echo("\n[OK] 测试完成")
        click.echo(f"   总测试: {summary['total_tests']}")
        click.echo(f"   通过: {summary['passed']}")
        click.echo(f"   失败: {summary['failed']}")
        click.echo(f"   通过率: {summary['pass_rate']:.2f}%")


@test.command("generate")
@click.argument("module_path")
@click.option("--output", help="输出路径")
@click.option("--type", type=click.Choice(["unit", "integration"]), default="unit")
def test_generate(module_path, output, type):
    """生成测试模板"""
    from pathlib import Path

    from tools.test_automation import TestGenerator

    module_path = Path(module_path)

    if not output:
        if type == "unit":
            output = f"tests/unit/test_{module_path.stem}.py"
        else:
            output = f"tests/integration/test_{module_path.stem}_integration.py"

    output_path = Path(output)

    click.echo(f"[*] 生成{type}测试: {output}")

    if type == "unit":
        TestGenerator.generate_unit_test(module_path, output_path)
    else:
        TestGenerator.generate_integration_test(module_path.stem, output_path)

    click.echo(f"[OK] 测试文件已生成: {output}")


@test.command("baseline")
@click.argument("name")
@click.option("--compare/--save", default=False, help="比较或保存基线")
def test_baseline(name, compare):
    """管理测试基线"""
    from pathlib import Path

    from tools.test_automation import (
        CoverageAnalyzer,
        RegressionTestManager,
        TestRunner,
    )

    project_root = Path(".")
    baseline_dir = project_root / "test_baselines"
    manager = RegressionTestManager(baseline_dir)

    if compare:
        click.echo(f"[*] 与基线比较: {name}")

        # 运行当前测试
        runner = TestRunner(project_root)
        runner.run_pytest("tests/")
        summary = runner.get_summary()

        coverage = CoverageAnalyzer(project_root)
        coverage_report = coverage.run_coverage("tests/")

        current_results = {
            "total_tests": summary["total_tests"],
            "pass_rate": summary["pass_rate"],
            "coverage_percent": coverage_report.coverage_percent if coverage_report else 0,
        }

        comparison = manager.compare_with_baseline(name, current_results)

        if comparison:
            click.echo("\n变化:")
            for metric, data in comparison.get("changes", {}).items():
                diff = data.get("diff", 0)
                regression = data.get("regression", False)
                symbol = "[-]" if regression else "[+]" if diff > 0 else "[=]"
                click.echo(f"  {symbol} {metric}: {data['baseline']:.2f} -> {data['current']:.2f} ({diff:+.2f})")
    else:
        click.echo(f"[*] 保存基线: {name}")

        # 运行测试并保存结果
        runner = TestRunner(project_root)
        runner.run_pytest("tests/")
        summary = runner.get_summary()

        coverage = CoverageAnalyzer(project_root)
        coverage_report = coverage.run_coverage("tests/")

        baseline_data = {
            "total_tests": summary["total_tests"],
            "pass_rate": summary["pass_rate"],
            "coverage_percent": coverage_report.coverage_percent if coverage_report else 0,
        }

        manager.save_baseline(name, baseline_data)
        click.echo("[OK] 基线已保存")


@cli.group()
def dashboard():
    """开发者仪表板"""
    pass


@dashboard.command("generate")
@click.option("--output", default="developer_dashboard.html", help="输出文件")
def dashboard_generate(output):
    """生成仪表板"""
    from pathlib import Path

    from tools.developer_dashboard import DashboardGenerator, ProjectMetrics

    project_root = Path(".")

    click.echo("[*] 收集项目指标...")
    collector = ProjectMetrics(project_root)

    metrics = {
        "code_stats": collector.get_code_stats(),
        "git_stats": collector.get_git_stats(),
        "test_stats": collector.get_test_stats(),
        "coverage_stats": collector.get_coverage_stats(),
        "dependency_stats": collector.get_dependency_stats(),
    }

    click.echo(f"[*] 生成仪表板: {output}")
    DashboardGenerator.generate_dashboard(metrics, Path(output))

    click.echo(f"[OK] 仪表板已生成: {output}")


@dashboard.command("serve")
@click.option("--port", default=8888, help="服务器端口")
def dashboard_serve(port):
    """启动仪表板服务器"""
    import time
    from pathlib import Path

    from tools.developer_dashboard import (
        DashboardGenerator,
        DashboardServer,
        ProjectMetrics,
    )

    project_root = Path(".")
    dashboard_path = project_root / "developer_dashboard.html"

    # 生成最新仪表板
    click.echo("[*] 生成仪表板...")
    collector = ProjectMetrics(project_root)

    metrics = {
        "code_stats": collector.get_code_stats(),
        "git_stats": collector.get_git_stats(),
        "test_stats": collector.get_test_stats(),
        "coverage_stats": collector.get_coverage_stats(),
        "dependency_stats": collector.get_dependency_stats(),
    }

    DashboardGenerator.generate_dashboard(metrics, dashboard_path)

    # 启动服务器
    click.echo(f"[*] 启动仪表板服务器 (端口: {port})...")
    server = DashboardServer(dashboard_path, port=port)
    server.start()

    try:
        click.echo("\n按 Ctrl+C 停止服务器...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        click.echo("\n[OK] 服务器已停止")


@cli.group()
def ci():
    """CI/CD工具"""
    pass


@ci.command("generate-workflows")
def ci_generate_workflows():
    """生成GitHub Actions工作流"""
    from pathlib import Path

    from tools.ci_cd_tools import GitHubActionsGenerator

    project_root = Path(".")

    click.echo("[*] 生成GitHub Actions工作流...")

    GitHubActionsGenerator.generate_ci_workflow(project_root / ".github" / "workflows" / "ci.yml")

    GitHubActionsGenerator.generate_release_workflow(project_root / ".github" / "workflows" / "release.yml")

    click.echo("[OK] 工作流文件已生成")


@ci.command("pipeline")
def ci_pipeline():
    """运行完整CI/CD pipeline"""
    from pathlib import Path

    from tools.ci_cd_tools import PipelineRunner

    project_root = Path(".")

    click.echo("[*] 运行CI/CD Pipeline...")

    pipeline = PipelineRunner(project_root)
    results = pipeline.run_full_pipeline()

    # 打印摘要
    click.echo("\n[*] Pipeline摘要:")
    for stage, result in results.items():
        status = "[OK]" if result["success"] else "[FAIL]"
        click.echo(f"{status} {stage}: {result['duration']:.2f}秒")

        if result["errors"]:
            for error in result["errors"]:
                click.echo(f"  [ERROR] {error}")


@ci.command("build")
def ci_build():
    """构建可执行文件"""
    from pathlib import Path

    from tools.ci_cd_tools import BuildAutomation

    project_root = Path(".")

    click.echo("[*] 构建可执行文件...")

    builder = BuildAutomation(project_root)
    result = builder.build_executable()

    if result.success:
        click.echo("[OK] 构建成功!")
        click.echo(result.output)
    else:
        click.echo("[FAIL] 构建失败!")
        for error in result.errors:
            click.echo(f"  [ERROR] {error}")


@cli.group()
def analytics():
    """实验数据分析"""
    pass


@analytics.command("experiment")
@click.argument("experiment_id")
@click.option("--output", help="输出报告路径")
def analytics_experiment(experiment_id, output):
    """分析实验数据"""
    from pathlib import Path

    from tools.experiment_analytics import (
        AnalyticsReportGenerator,
        ExperimentDataAnalyzer,
    )

    data_dir = Path("data")
    analyzer = ExperimentDataAnalyzer(data_dir)

    click.echo(f"[*] 分析实验: {experiment_id}")

    stats = analyzer.analyze_experiment(experiment_id)

    if not stats:
        click.echo(f"[ERROR] 未找到实验数据: {experiment_id}", err=True)
        return

    click.echo("\n实验统计:")
    click.echo(f"  尝试次数: {stats.total_attempts}")
    click.echo(f"  平均分数: {stats.avg_score:.2f}")
    click.echo(f"  平均时长: {stats.avg_duration / 60:.2f}分钟")
    click.echo(f"  完成率: {stats.completion_rate:.2f}%")
    click.echo(f"  难度指数: {stats.difficulty_rating:.2f}/100")

    # 生成报告
    if not output:
        output = f"experiment_report_{experiment_id}.html"

    AnalyticsReportGenerator.generate_experiment_report(stats, Path(output))
    click.echo(f"\n[OK] 报告已生成: {output}")


@analytics.command("user")
@click.argument("user_id")
@click.option("--output", help="输出报告路径")
def analytics_user(user_id, output):
    """分析用户数据"""
    from pathlib import Path

    from tools.experiment_analytics import (
        AnalyticsReportGenerator,
        ExperimentDataAnalyzer,
    )

    data_dir = Path("data")
    analyzer = ExperimentDataAnalyzer(data_dir)

    click.echo(f"[*] 分析用户: {user_id}")

    analytics = analyzer.analyze_user(user_id)

    if not analytics:
        click.echo(f"[ERROR] 未找到用户数据: {user_id}", err=True)
        return

    trend_symbol = "[+]" if analytics.improvement_trend > 0 else "[-]"

    click.echo("\n用户统计:")
    click.echo(f"  完成实验: {analytics.total_experiments}")
    click.echo(f"  平均分数: {analytics.avg_score:.2f}")
    click.echo(f"  总学习时长: {analytics.total_time_spent / 3600:.2f}小时")
    click.echo(f"  进步趋势: {trend_symbol} {analytics.improvement_trend:+.2f}分")

    # 生成报告
    if not output:
        output = f"user_report_{user_id}.html"

    AnalyticsReportGenerator.generate_user_report(analytics, Path(output))
    click.echo(f"\n[OK] 报告已生成: {output}")


@analytics.command("trending")
@click.option("--days", default=7, help="统计天数")
def analytics_trending(days):
    """查看热门实验"""
    from pathlib import Path

    from tools.experiment_analytics import ExperimentDataAnalyzer

    data_dir = Path("data")
    analyzer = ExperimentDataAnalyzer(data_dir)

    click.echo(f"[*] 热门实验 (最近{days}天):\n")

    trending = analyzer.get_trending_experiments(days=days)

    for i, (exp_id, count) in enumerate(trending, 1):
        click.echo(f"{i}. {exp_id}: {count}次")


@cli.command("all")
@click.option("--quick/--full", default=True, help="快速或完整运行")
def run_all(quick):
    """运行所有工具检查"""
    from pathlib import Path

    click.echo("=" * 60)
    click.echo("[*] 运行完整开发工具检查")
    click.echo("=" * 60 + "\n")

    # 1. 代码复杂度
    click.echo("[1] 代码复杂度分析...")
    from tools.profiler import CodeComplexityAnalyzer

    results = CodeComplexityAnalyzer.analyze_directory(Path("src"))
    click.echo(f"   最复杂文件: {results[0]['file'] if results else 'N/A'}")

    # 2. 测试
    if not quick:
        click.echo("\n[2] 运行测试...")
        from tools.test_automation import TestRunner

        runner = TestRunner(Path("."))
        runner.run_pytest("tests/")
        summary = runner.get_summary()
        click.echo(f"   通过率: {summary['pass_rate']:.2f}%")

    # 3. 生成仪表板
    click.echo("\n[3] 生成开发者仪表板...")
    from tools.developer_dashboard import DashboardGenerator, ProjectMetrics

    collector = ProjectMetrics(Path("."))
    metrics = {
        "code_stats": collector.get_code_stats(),
        "git_stats": collector.get_git_stats(),
        "test_stats": collector.get_test_stats(),
        "coverage_stats": collector.get_coverage_stats(),
        "dependency_stats": collector.get_dependency_stats(),
    }
    DashboardGenerator.generate_dashboard(metrics, Path("developer_dashboard.html"))
    click.echo("   仪表板: developer_dashboard.html")

    click.echo("\n" + "=" * 60)
    click.echo("[OK] 检查完成!")
    click.echo("=" * 60)


if __name__ == "__main__":
    cli()
