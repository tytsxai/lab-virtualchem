#!/usr/bin/env python
"""
自动化测试运行脚本
支持多种测试类型和报告生成
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class TestRunner:
    """测试运行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results: dict[str, dict] = {}

    def run_command(self, cmd: list[str], name: str) -> bool:
        """运行命令并记录结果"""
        print(f"\n{'=' * 60}")
        print(f"运行: {name}")
        print(f"{'=' * 60}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            elapsed = time.time() - start_time

            # 输出结果
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            success = result.returncode == 0
            self.results[name] = {
                "success": success,
                "returncode": result.returncode,
                "elapsed": elapsed,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            status = "✅ 成功" if success else "❌ 失败"
            print(f"\n{status} - 耗时: {elapsed:.2f}秒")

            return success

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 错误: {e}")
            self.results[name] = {"success": False, "error": str(e), "elapsed": elapsed}
            return False

    def run_code_quality_checks(self) -> bool:
        """运行代码质量检查"""
        print("\n" + "=" * 60)
        print("🔍 代码质量检查")
        print("=" * 60)

        success = True

        # Ruff 检查
        success &= self.run_command(
            ["ruff", "check", "src/", "tests/", "--output-format=full"], "Ruff 代码检查"
        )

        # Black 格式检查
        success &= self.run_command(["black", "--check", "src/", "tests/"], "Black 格式检查")

        # isort 导入排序检查
        success &= self.run_command(
            ["isort", "--check-only", "src/", "tests/"], "isort 导入排序检查"
        )

        return success

    def run_type_checks(self) -> bool:
        """运行类型检查"""
        return self.run_command(["mypy", "src/", "--no-error-summary"], "MyPy 类型检查")

    def run_unit_tests(self, coverage: bool = True) -> bool:
        """运行单元测试"""
        cmd = ["pytest", "tests/unit", "-v", "--tb=short"]

        if coverage:
            cmd.extend(
                [
                    "--cov=src",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                    "--cov-report=json",
                    f"--cov-report=html:htmlcov/unit_{self.timestamp}",
                ]
            )

        return self.run_command(cmd, "单元测试")

    def run_integration_tests(self, coverage: bool = True) -> bool:
        """运行集成测试"""
        cmd = ["pytest", "tests/integration", "-v", "--tb=short"]

        if coverage:
            cmd.extend(["--cov=src", "--cov-append", "--cov-report=term-missing"])

        return self.run_command(cmd, "集成测试")

    def run_ui_tests(self) -> bool:
        """运行UI测试"""
        return self.run_command(["pytest", "tests/ui", "-v", "--tb=short"], "UI测试")

    def run_performance_tests(self) -> bool:
        """运行性能测试"""
        return self.run_command(["pytest", "tests/performance", "-v", "--tb=short"], "性能测试")

    def run_specific_test(self, test_path: str) -> bool:
        """运行特定测试"""
        return self.run_command(["pytest", test_path, "-v", "--tb=short"], f"特定测试: {test_path}")

    def run_security_checks(self) -> bool:
        """运行安全检查"""
        print("\n" + "=" * 60)
        print("🔒 安全检查")
        print("=" * 60)

        success = True

        # Bandit 安全扫描
        success &= self.run_command(
            [
                "bandit",
                "-r",
                "src/",
                "-ll",
                "-f",
                "json",
                "-o",
                str(self.reports_dir / f"bandit_{self.timestamp}.json"),
            ],
            "Bandit 安全扫描",
        )

        # Safety 依赖检查
        success &= self.run_command(
            [
                "safety",
                "check",
                "--json",
                "--output",
                str(self.reports_dir / f"safety_{self.timestamp}.json"),
            ],
            "Safety 依赖安全检查",
        )

        return success

    def generate_report(self) -> None:
        """生成测试报告"""
        report_path = self.reports_dir / f"test_report_{self.timestamp}.json"

        # 读取覆盖率数据
        coverage_data = None
        coverage_json = self.project_root / "coverage.json"
        if coverage_json.exists():
            with open(coverage_json, encoding="utf-8") as f:
                coverage_data = json.load(f)

        # 生成报告
        report = {
            "timestamp": self.timestamp,
            "date": datetime.now().isoformat(),
            "results": self.results,
            "coverage": coverage_data,
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results.values() if r.get("success", False)),
                "failed": sum(1 for r in self.results.values() if not r.get("success", False)),
                "total_time": sum(r.get("elapsed", 0) for r in self.results.values()),
            },
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📊 测试报告已保存到: {report_path}")

        # 生成简单的文本报告
        text_report_path = self.reports_dir / f"test_report_{self.timestamp}.txt"
        with open(text_report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("VirtualChemLab 自动化测试报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            f.write("测试摘要:\n")
            f.write(f"  总测试数: {report['summary']['total_tests']}\n")
            f.write(f"  通过: {report['summary']['passed']} ✅\n")
            f.write(f"  失败: {report['summary']['failed']} ❌\n")
            f.write(f"  总耗时: {report['summary']['total_time']:.2f}秒\n\n")

            f.write("详细结果:\n")
            for name, result in self.results.items():
                status = "✅" if result.get("success", False) else "❌"
                elapsed = result.get("elapsed", 0)
                f.write(f"  {status} {name} ({elapsed:.2f}秒)\n")

            if coverage_data:
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                f.write(f"\n代码覆盖率: {total_coverage:.2f}%\n")

        print(f"📄 文本报告已保存到: {text_report_path}")

    def print_summary(self) -> None:
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("📊 测试摘要")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get("success", False))
        failed = total - passed
        total_time = sum(r.get("elapsed", 0) for r in self.results.values())

        print(f"\n总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"总耗时: {total_time:.2f}秒")

        if failed > 0:
            print("\n失败的测试:")
            for name, result in self.results.items():
                if not result.get("success", False):
                    print(f"  ❌ {name}")


def main():
    parser = argparse.ArgumentParser(description="VirtualChemLab 自动化测试运行器")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "ui", "performance", "quality", "security"],
        default="all",
        help="测试类型",
    )
    parser.add_argument("--no-coverage", action="store_true", help="不生成覆盖率报告")
    parser.add_argument("--fast", action="store_true", help="快速模式（跳过耗时检查）")
    parser.add_argument("--test-path", help="运行特定测试文件")
    parser.add_argument("--report", action="store_true", help="生成详细报告")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)

    print("=" * 60)
    print("🧪 VirtualChemLab 自动化测试系统")
    print("=" * 60)

    overall_success = True

    try:
        if args.test_path:
            # 运行特定测试
            overall_success = runner.run_specific_test(args.test_path)

        elif args.type == "all":
            # 运行所有测试
            if not args.fast:
                overall_success &= runner.run_code_quality_checks()
                overall_success &= runner.run_type_checks()

            overall_success &= runner.run_unit_tests(coverage=not args.no_coverage)
            overall_success &= runner.run_integration_tests(coverage=not args.no_coverage)

            if not args.fast:
                overall_success &= runner.run_ui_tests()
                overall_success &= runner.run_performance_tests()
                overall_success &= runner.run_security_checks()

        elif args.type == "unit":
            overall_success = runner.run_unit_tests(coverage=not args.no_coverage)

        elif args.type == "integration":
            overall_success = runner.run_integration_tests(coverage=not args.no_coverage)

        elif args.type == "ui":
            overall_success = runner.run_ui_tests()

        elif args.type == "performance":
            overall_success = runner.run_performance_tests()

        elif args.type == "quality":
            overall_success = runner.run_code_quality_checks()
            overall_success &= runner.run_type_checks()

        elif args.type == "security":
            overall_success = runner.run_security_checks()

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        overall_success = False

    # 打印摘要
    runner.print_summary()

    # 生成报告
    if args.report or args.type == "all":
        runner.generate_report()

    # 返回退出码
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
