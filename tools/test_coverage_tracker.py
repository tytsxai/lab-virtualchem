"""
测试覆盖率追踪工具
用于监控和改进测试覆盖率

使用方法:
    python tools/test_coverage_tracker.py                    # 生成覆盖率报告
    python tools/test_coverage_tracker.py --module core      # 检查特定模块
    python tools/test_coverage_tracker.py --compare          # 与上次比较
    python tools/test_coverage_tracker.py --target 80        # 设置目标覆盖率
"""

import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 设置Windows控制台UTF-8编码
if sys.platform == "win32":
    # 切换控制台代码页到UTF-8
    os.system("chcp 65001 >nul 2>&1")
    # 重新包装stdout和stderr以使用UTF-8
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class CoverageTracker:
    """测试覆盖率追踪器"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.reports_dir = self.project_root / "coverage_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.current_report = None

    def run_coverage(self, module: str = None) -> dict:
        """运行测试覆盖率检查"""
        print("🔍 运行测试覆盖率检查...")

        cmd = ["pytest", "--cov=src"]
        if module:
            cmd.extend(["--cov", f"src/{module}"])
        cmd.extend(["--cov-report=json", "--cov-report=term"])

        try:
            subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            # 读取JSON报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                return coverage_data
            else:
                print("❌ coverage.json未生成")
                return {}
        except Exception as e:
            print(f"❌ 运行覆盖率检查失败: {e}")
            return {}

    def analyze_coverage(self, coverage_data: dict) -> dict:
        """分析覆盖率数据"""
        if not coverage_data:
            return {}

        files = coverage_data.get("files", {})
        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

        # 按模块分组
        modules = {}
        for file_path, file_data in files.items():
            if "src/" not in file_path:
                continue

            # 提取模块名
            parts = file_path.split("src/")[1].split("/")
            module = parts[0] if len(parts) > 0 else "unknown"

            if module not in modules:
                modules[module] = {
                    "files": [],
                    "total_statements": 0,
                    "covered_statements": 0,
                }

            summary = file_data.get("summary", {})
            statements = summary.get("num_statements", 0)
            covered = summary.get("covered_lines", 0)

            modules[module]["files"].append(
                {
                    "path": file_path,
                    "statements": statements,
                    "covered": covered,
                    "coverage": summary.get("percent_covered", 0),
                }
            )
            modules[module]["total_statements"] += statements
            modules[module]["covered_statements"] += covered

        # 计算模块覆盖率
        for _module, data in modules.items():
            if data["total_statements"] > 0:
                data["coverage"] = (data["covered_statements"] / data["total_statements"]) * 100
            else:
                data["coverage"] = 0

        return {
            "total_coverage": total_coverage,
            "modules": modules,
            "timestamp": datetime.now().isoformat(),
        }

    def save_report(self, analysis: dict):
        """保存覆盖率报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"coverage_{timestamp}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        print(f"✅ 报告已保存: {report_file}")

        # 保存为最新报告
        latest_file = self.reports_dir / "latest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

    def compare_with_previous(self, current: dict) -> dict:
        """与上次报告比较"""
        latest_file = self.reports_dir / "latest.json"

        if not latest_file.exists():
            print("⚠️  没有历史报告可供比较")
            return {}

        with open(latest_file, encoding="utf-8") as f:
            previous = json.load(f)

        # 比较总体覆盖率
        current_total = current.get("total_coverage", 0)
        previous_total = previous.get("total_coverage", 0)
        diff_total = current_total - previous_total

        # 比较模块覆盖率
        module_diffs = {}
        for module, current_data in current.get("modules", {}).items():
            current_cov = current_data.get("coverage", 0)
            previous_data = previous.get("modules", {}).get(module, {})
            previous_cov = previous_data.get("coverage", 0)
            diff = current_cov - previous_cov

            if abs(diff) > 0.1:  # 只显示有明显变化的
                module_diffs[module] = {
                    "current": current_cov,
                    "previous": previous_cov,
                    "diff": diff,
                }

        return {
            "total": {"current": current_total, "previous": previous_total, "diff": diff_total},
            "modules": module_diffs,
            "timestamp": current.get("timestamp"),
        }

    def print_report(self, analysis: dict, target: float = 70.0):
        """打印格式化报告"""
        print("\n" + "=" * 70)
        print("📊 VirtualChemLab 测试覆盖率报告")
        print("=" * 70)

        total_coverage = analysis.get("total_coverage", 0)
        print(f"\n总体覆盖率: {total_coverage:.2f}%")

        # 进度条
        bar_length = 50
        filled = int(bar_length * total_coverage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}] {total_coverage:.1f}%")

        # 与目标比较
        if total_coverage < target:
            gap = target - total_coverage
            print(f"⚠️  距离目标 {target}% 还差 {gap:.2f}%")
        else:
            print(f"✅ 已达到目标 {target}%")

        # 模块覆盖率
        print("\n" + "-" * 70)
        print("📦 模块覆盖率:")
        print("-" * 70)

        modules = analysis.get("modules", {})
        sorted_modules = sorted(modules.items(), key=lambda x: x[1]["coverage"], reverse=True)

        for module, data in sorted_modules:
            coverage = data["coverage"]
            files_count = len(data["files"])

            # 状态图标
            if coverage >= 80:
                icon = "✅"
            elif coverage >= 60:
                icon = "🟡"
            else:
                icon = "🔴"

            print(f"{icon} {module:20s} {coverage:6.2f}%  ({files_count} files)")

        # 需要改进的模块
        print("\n" + "-" * 70)
        print("🎯 需要改进的模块 (<80%):")
        print("-" * 70)

        low_coverage_modules = [(m, d) for m, d in sorted_modules if d["coverage"] < 80]

        if not low_coverage_modules:
            print("✅ 所有模块都达到80%以上!")
        else:
            for module, data in low_coverage_modules:
                coverage = data["coverage"]
                gap = 80 - coverage
                print(f"  📦 {module:20s} {coverage:.2f}% (需提升 {gap:.2f}%)")

        # 优秀模块
        print("\n" + "-" * 70)
        print("⭐ 优秀模块 (≥80%):")
        print("-" * 70)

        high_coverage_modules = [(m, d) for m, d in sorted_modules if d["coverage"] >= 80]

        if not high_coverage_modules:
            print("⚠️  暂无模块达到80%")
        else:
            for module, data in high_coverage_modules:
                coverage = data["coverage"]
                print(f"  ✅ {module:20s} {coverage:.2f}%")

    def print_comparison(self, comparison: dict):
        """打印比较报告"""
        if not comparison:
            return

        print("\n" + "=" * 70)
        print("📈 覆盖率变化:")
        print("=" * 70)

        total = comparison.get("total", {})
        diff = total.get("diff", 0)

        if diff > 0:
            icon = "📈"
            direction = "提升"
        elif diff < 0:
            icon = "📉"
            direction = "下降"
        else:
            icon = "➡️"
            direction = "持平"

        print(
            f"\n{icon} 总体: {total.get('previous', 0):.2f}% → {total.get('current', 0):.2f}% ({direction} {abs(diff):.2f}%)"
        )

        # 模块变化
        module_diffs = comparison.get("modules", {})
        if module_diffs:
            print("\n模块变化:")
            for module, diff_data in module_diffs.items():
                diff = diff_data["diff"]
                if diff > 0:
                    icon = "📈"
                elif diff < 0:
                    icon = "📉"
                else:
                    icon = "➡️"

                print(
                    f"  {icon} {module:20s} {diff_data['previous']:.2f}% → {diff_data['current']:.2f}% ({diff:+.2f}%)"
                )

    def suggest_improvements(self, analysis: dict):
        """提供改进建议"""
        print("\n" + "=" * 70)
        print("💡 改进建议:")
        print("=" * 70)

        modules = analysis.get("modules", {})
        low_modules = [(m, d) for m, d in modules.items() if d["coverage"] < 80]
        low_modules.sort(key=lambda x: x[1]["coverage"])

        if not low_modules:
            print("\n✅ 所有模块覆盖率都很好!")
            return

        print("\n优先改进以下模块:\n")

        for i, (module, data) in enumerate(low_modules[:5], 1):
            coverage = data["coverage"]
            gap = 80 - coverage
            statements_needed = int(data["total_statements"] * gap / 100)

            print(f"{i}. 📦 {module}")
            print(f"   当前覆盖率: {coverage:.2f}%")
            print("   目标覆盖率: 80%")
            print(f"   需要测试约 {statements_needed} 行代码")
            print(f"   建议: pytest tests/unit/test_{module}.py --cov=src/{module}")
            print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab 测试覆盖率追踪工具")
    parser.add_argument("--module", type=str, help="检查特定模块")
    parser.add_argument("--compare", action="store_true", help="与上次比较")
    parser.add_argument("--target", type=float, default=70.0, help="目标覆盖率 (默认70%%)")
    parser.add_argument("--no-save", action="store_true", help="不保存报告")

    args = parser.parse_args()

    tracker = CoverageTracker()

    print("=" * 70)
    print("VirtualChemLab 测试覆盖率追踪工具")
    print("=" * 70)

    # 运行覆盖率检查
    coverage_data = tracker.run_coverage(args.module)

    if not coverage_data:
        print("❌ 无法获取覆盖率数据")
        return

    # 分析数据
    analysis = tracker.analyze_coverage(coverage_data)

    # 打印报告
    tracker.print_report(analysis, args.target)

    # 比较
    if args.compare:
        comparison = tracker.compare_with_previous(analysis)
        tracker.print_comparison(comparison)

    # 改进建议
    tracker.suggest_improvements(analysis)

    # 保存报告
    if not args.no_save:
        tracker.save_report(analysis)

    print("\n" + "=" * 70)
    print("📚 下一步:")
    print("=" * 70)
    print("1. 查看HTML报告: open htmlcov/index.html")
    print("2. 改进特定模块: pytest tests/unit/test_xxx.py --cov=src/xxx")
    print("3. 再次运行本工具查看进度: python tools/test_coverage_tracker.py --compare")
    print("=" * 70)


if __name__ == "__main__":
    main()
