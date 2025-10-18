"""
自动化测试套件增强

提供测试生成、覆盖率分析、回归测试等功能
"""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """测试结果"""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: str | None = None
    traceback: str | None = None


@dataclass
class TestSuite:
    """测试套件结果"""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    duration: float
    test_results: list[TestResult]


@dataclass
class CoverageReport:
    """覆盖率报告"""
    total_statements: int
    covered_statements: int
    coverage_percent: float
    missing_lines: dict[str, list[int]]
    uncovered_files: list[str]


class TestRunner:
    """测试运行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: list[TestSuite] = []

    def run_pytest(self, test_path: str | None = None, options: list[str] | None = None) -> bool:
        """运行pytest测试"""
        cmd = ['pytest']

        if test_path:
            cmd.append(test_path)

        if options:
            cmd.extend(options)
        else:
            cmd.extend(['-v', '--tb=short'])

        # 添加XML输出用于解析
        junit_xml = self.project_root / 'test_results.xml'
        cmd.extend(['--junitxml', str(junit_xml)])

        print(f"运行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            print(result.stdout)

            if junit_xml.exists():
                self._parse_junit_xml(junit_xml)

            return result.returncode == 0

        except Exception as e:
            print(f"运行测试时出错: {e}")
            return False

    def _parse_junit_xml(self, xml_path: Path):
        """解析JUnit XML结果"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for testsuite in root.findall('.//testsuite'):
                test_results = []

                for testcase in testsuite.findall('testcase'):
                    name = testcase.get('name', '')
                    duration = float(testcase.get('time', 0))

                    # 检查测试状态
                    failure = testcase.find('failure')
                    error = testcase.find('error')
                    skipped = testcase.find('skipped')

                    if failure is not None:
                        status = 'failed'
                        message = failure.get('message', '')
                        traceback = failure.text
                    elif error is not None:
                        status = 'error'
                        message = error.get('message', '')
                        traceback = error.text
                    elif skipped is not None:
                        status = 'skipped'
                        message = skipped.get('message', '')
                        traceback = None
                    else:
                        status = 'passed'
                        message = None
                        traceback = None

                    test_results.append(TestResult(
                        name=name,
                        status=status,
                        duration=duration,
                        message=message,
                        traceback=traceback
                    ))

                suite = TestSuite(
                    name=testsuite.get('name', ''),
                    tests=int(testsuite.get('tests', 0)),
                    failures=int(testsuite.get('failures', 0)),
                    errors=int(testsuite.get('errors', 0)),
                    skipped=int(testsuite.get('skipped', 0)),
                    duration=float(testsuite.get('time', 0)),
                    test_results=test_results
                )

                self.results.append(suite)

        except Exception as e:
            print(f"解析测试结果时出错: {e}")

    def get_summary(self) -> dict[str, Any]:
        """获取测试总结"""
        total_tests = sum(suite.tests for suite in self.results)
        total_failures = sum(suite.failures for suite in self.results)
        total_errors = sum(suite.errors for suite in self.results)
        total_skipped = sum(suite.skipped for suite in self.results)
        total_passed = total_tests - total_failures - total_errors - total_skipped

        return {
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failures,
            'errors': total_errors,
            'skipped': total_skipped,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'suites': len(self.results)
        }


class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run_coverage(self, test_path: str | None = None) -> CoverageReport | None:
        """运行覆盖率测试"""
        cmd = ['pytest']

        if test_path:
            cmd.append(test_path)

        cmd.extend([
            '--cov=src',
            '--cov-report=json',
            '--cov-report=html',
            '--cov-report=term'
        ])

        print(f"运行覆盖率测试: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            print(result.stdout)

            # 解析coverage.json
            coverage_json = self.project_root / 'coverage.json'
            if coverage_json.exists():
                return self._parse_coverage_json(coverage_json)

            return None

        except Exception as e:
            print(f"运行覆盖率测试时出错: {e}")
            return None

    def _parse_coverage_json(self, json_path: Path) -> CoverageReport:
        """解析覆盖率JSON"""
        data = json.loads(json_path.read_text(encoding='utf-8'))

        total_statements = data['totals']['num_statements']
        covered_statements = data['totals']['covered_lines']
        coverage_percent = data['totals']['percent_covered']

        missing_lines = {}
        uncovered_files = []

        for file_path, file_data in data['files'].items():
            if file_data['summary']['percent_covered'] < 100:
                missing_lines[file_path] = file_data['missing_lines']

                if file_data['summary']['percent_covered'] == 0:
                    uncovered_files.append(file_path)

        return CoverageReport(
            total_statements=total_statements,
            covered_statements=covered_statements,
            coverage_percent=coverage_percent,
            missing_lines=missing_lines,
            uncovered_files=uncovered_files
        )


class TestGenerator:
    """测试用例生成器"""

    @staticmethod
    def generate_unit_test(module_path: Path, output_path: Path):
        """为模块生成单元测试模板"""
        module_name = module_path.stem

        # 读取模块内容
        content = module_path.read_text(encoding='utf-8')

        # 提取函数和类
        functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)\s*[\(:]', content, re.MULTILINE)

        # 生成测试代码
        test_code = f'''"""
{module_name} 模块的单元测试
自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import pytest
from src.{module_name} import *


'''

        # 为每个类生成测试
        for class_name in classes:
            test_code += f'''
class Test{class_name}:
    """测试 {class_name} 类"""

    def test_init(self):
        """测试初始化"""
        # TODO: 实现测试
        assert True

    def test_basic_functionality(self):
        """测试基本功能"""
        # TODO: 实现测试
        assert True


'''

        # 为每个函数生成测试
        for func_name in functions:
            if not func_name.startswith('_'):  # 跳过私有函数
                test_code += f'''
def test_{func_name}():
    """测试 {func_name} 函数"""
    # TODO: 实现测试
    assert True


'''

        # 写入测试文件
        output_path.write_text(test_code, encoding='utf-8')
        print(f"已生成测试文件: {output_path}")

    @staticmethod
    def generate_integration_test(feature_name: str, output_path: Path):
        """生成集成测试模板"""
        test_code = f'''"""
{feature_name} 集成测试
自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import pytest


class TestIntegration{feature_name.replace('_', '').title()}:
    """测试 {feature_name} 的集成场景"""

    def test_complete_flow(self):
        """测试完整流程"""
        # TODO: 实现端到端测试
        assert True

    def test_error_handling(self):
        """测试错误处理"""
        # TODO: 实现错误处理测试
        assert True

    def test_edge_cases(self):
        """测试边界情况"""
        # TODO: 实现边界测试
        assert True
'''

        output_path.write_text(test_code, encoding='utf-8')
        print(f"已生成集成测试文件: {output_path}")


class RegressionTestManager:
    """回归测试管理器"""

    def __init__(self, baseline_dir: Path):
        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(self, name: str, results: dict[str, Any]):
        """保存基线测试结果"""
        baseline_file = self.baseline_dir / f"{name}_baseline.json"

        data = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'results': results
        }

        baseline_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"已保存基线: {baseline_file}")

    def compare_with_baseline(self, name: str, current_results: dict[str, Any]) -> dict[str, Any]:
        """与基线比较"""
        baseline_file = self.baseline_dir / f"{name}_baseline.json"

        if not baseline_file.exists():
            print(f"基线文件不存在: {baseline_file}")
            return {}

        baseline_data = json.loads(baseline_file.read_text(encoding='utf-8'))
        baseline_results = baseline_data['results']

        # 比较结果
        comparison = {
            'baseline_timestamp': baseline_data['timestamp'],
            'current_timestamp': datetime.now().isoformat(),
            'changes': {}
        }

        # 比较测试数量
        if 'total_tests' in baseline_results and 'total_tests' in current_results:
            baseline_total = baseline_results['total_tests']
            current_total = current_results['total_tests']

            comparison['changes']['total_tests'] = {
                'baseline': baseline_total,
                'current': current_total,
                'diff': current_total - baseline_total
            }

        # 比较通过率
        if 'pass_rate' in baseline_results and 'pass_rate' in current_results:
            baseline_rate = baseline_results['pass_rate']
            current_rate = current_results['pass_rate']

            comparison['changes']['pass_rate'] = {
                'baseline': baseline_rate,
                'current': current_rate,
                'diff': current_rate - baseline_rate,
                'regression': current_rate < baseline_rate
            }

        # 比较覆盖率
        if 'coverage_percent' in baseline_results and 'coverage_percent' in current_results:
            baseline_cov = baseline_results['coverage_percent']
            current_cov = current_results['coverage_percent']

            comparison['changes']['coverage'] = {
                'baseline': baseline_cov,
                'current': current_cov,
                'diff': current_cov - baseline_cov,
                'regression': current_cov < baseline_cov
            }

        return comparison


class TestReportGenerator:
    """测试报告生成器"""

    @staticmethod
    def generate_html_report(
        test_summary: dict[str, Any],
        coverage_report: CoverageReport | None,
        output_path: Path
    ):
        """生成HTML测试报告"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .stat {{
            display: inline-block;
            margin: 10px 20px;
            font-size: 1.2em;
        }}
        .passed {{ color: #27ae60; }}
        .failed {{ color: #e74c3c; }}
        .skipped {{ color: #95a5a6; }}
        .coverage {{
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border-radius: 3px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background-color: #3498db; color: white; }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background-color: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #27ae60;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <h1>📊 测试报告</h1>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="summary">
        <h2>测试总结</h2>
        <div class="stat">总测试数: <strong>{test_summary.get('total_tests', 0)}</strong></div>
        <div class="stat passed">通过: <strong>{test_summary.get('passed', 0)}</strong></div>
        <div class="stat failed">失败: <strong>{test_summary.get('failed', 0)}</strong></div>
        <div class="stat skipped">跳过: <strong>{test_summary.get('skipped', 0)}</strong></div>
        <br>
        <div class="stat">通过率: <strong>{test_summary.get('pass_rate', 0):.2f}%</strong></div>

        <h3>通过率</h3>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {test_summary.get('pass_rate', 0)}%"></div>
        </div>
    </div>
"""

        if coverage_report:
            html += f"""
    <div class="summary">
        <h2>覆盖率报告</h2>
        <div class="coverage">
            总覆盖率: {coverage_report.coverage_percent:.2f}%
            ({coverage_report.covered_statements}/{coverage_report.total_statements} 语句)
        </div>

        <h3>覆盖率</h3>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {coverage_report.coverage_percent}%"></div>
        </div>

        <h3>未覆盖文件</h3>
        <ul>
"""

            for file in coverage_report.uncovered_files[:10]:
                html += f"            <li>{file}</li>\n"

            html += """        </ul>
    </div>
"""

        html += """
</body>
</html>"""

        output_path.write_text(html, encoding='utf-8')
        print(f"已生成测试报告: {output_path}")


# 使用示例
if __name__ == '__main__':
    project_root = Path('.')

    # 1. 运行测试
    print("=== 运行测试 ===")
    runner = TestRunner(project_root)
    success = runner.run_pytest('tests/', options=['-v'])

    # 获取测试总结
    summary = runner.get_summary()
    print("\n测试总结:")
    print(f"  总测试数: {summary['total_tests']}")
    print(f"  通过: {summary['passed']}")
    print(f"  失败: {summary['failed']}")
    print(f"  通过率: {summary['pass_rate']:.2f}%")

    # 2. 运行覆盖率测试
    print("\n=== 运行覆盖率测试 ===")
    coverage = CoverageAnalyzer(project_root)
    coverage_report = coverage.run_coverage('tests/')

    if coverage_report:
        print(f"覆盖率: {coverage_report.coverage_percent:.2f}%")
        print(f"未覆盖文件数: {len(coverage_report.uncovered_files)}")

    # 3. 生成测试报告
    print("\n=== 生成测试报告 ===")
    TestReportGenerator.generate_html_report(
        summary,
        coverage_report,
        project_root / 'test_report.html'
    )

    # 4. 保存基线
    regression = RegressionTestManager(project_root / 'test_baselines')
    baseline_data = {
        'total_tests': summary['total_tests'],
        'pass_rate': summary['pass_rate'],
        'coverage_percent': coverage_report.coverage_percent if coverage_report else 0
    }
    regression.save_baseline('main', baseline_data)


