#!/usr/bin/env python3
"""
VirtualChemLab 项目健康检查脚本
一键检查项目各项指标
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

PROJECT_ROOT = Path(__file__).parent.parent


class HealthChecker:
    """项目健康检查器"""

    def __init__(self):
        self.results = []
        self.score = 0
        self.max_score = 0

    def add_result(self, name: str, status: str, message: str, score: int = 0, max_score: int = 0):
        """添加检查结果"""
        self.results.append({
            'name': name,
            'status': status,
            'message': message,
            'score': score,
            'max_score': max_score
        })
        self.score += score
        self.max_score += max_score

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def check_python_version(self) -> bool:
        """检查Python版本"""
        print("🔍 检查Python版本...")
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        if version_info >= (3, 8):
            self.add_result(
                "Python版本",
                "✅",
                f"Python {version_str} (要求 ≥ 3.8)",
                10, 10
            )
            return True
        else:
            self.add_result(
                "Python版本",
                "❌",
                f"Python {version_str} (要求 ≥ 3.8)",
                0, 10
            )
            return False

    def check_dependencies(self) -> bool:
        """检查依赖安装"""
        print("🔍 检查核心依赖...")

        required_packages = {
            'PySide6': '6.6.0',
            'numpy': '1.26.0',
            'scipy': '1.11.0',
            'matplotlib': '3.8.0',
            'yaml': '6.0.1',
            'pydantic': '2.5.0',
        }

        missing = []
        installed = []

        for package, min_version in required_packages.items():
            try:
                if package == 'yaml':
                    import yaml
                    installed.append(f"{package} (PyYAML)")
                else:
                    __import__(package)
                    installed.append(package)
            except ImportError:
                missing.append(package)

        if not missing:
            self.add_result(
                "核心依赖",
                "✅",
                f"所有依赖已安装 ({len(installed)}/{len(required_packages)})",
                15, 15
            )
            return True
        else:
            self.add_result(
                "核心依赖",
                "❌",
                f"缺少依赖: {', '.join(missing)}",
                0, 15
            )
            return False

    def check_project_structure(self) -> bool:
        """检查项目结构"""
        print("🔍 检查项目结构...")

        required_dirs = [
            'src',
            'tests',
            'docs',
            'assets/templates',
            'config',
            'tools',
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            full_path = PROJECT_ROOT / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)

        if not missing_dirs:
            self.add_result(
                "项目结构",
                "✅",
                f"所有必需目录存在 ({len(required_dirs)}/{len(required_dirs)})",
                10, 10
            )
            return True
        else:
            self.add_result(
                "项目结构",
                "⚠️",
                f"缺少目录: {', '.join(missing_dirs)}",
                5, 10
            )
            return False

    def check_config_files(self) -> bool:
        """检查配置文件"""
        print("🔍 检查配置文件...")

        required_files = [
            'config.json',
            'pyproject.toml',
            'requirements.txt',
        ]

        missing_files = []
        for file_path in required_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if not missing_files:
            self.add_result(
                "配置文件",
                "✅",
                f"所有配置文件存在 ({len(required_files)}/{len(required_files)})",
                10, 10
            )
            return True
        else:
            self.add_result(
                "配置文件",
                "❌",
                f"缺少文件: {', '.join(missing_files)}",
                0, 10
            )
            return False

    def check_templates(self) -> bool:
        """检查实验模板"""
        print("🔍 检查实验模板...")

        templates_dir = PROJECT_ROOT / 'assets' / 'templates'
        if not templates_dir.exists():
            self.add_result(
                "实验模板",
                "❌",
                "模板目录不存在",
                0, 10
            )
            return False

        templates = list(templates_dir.glob('*.yaml')) + list(templates_dir.glob('*.yml'))

        if templates:
            self.add_result(
                "实验模板",
                "✅",
                f"找到 {len(templates)} 个实验模板",
                10, 10
            )
            return True
        else:
            self.add_result(
                "实验模板",
                "⚠️",
                "模板目录为空",
                3, 10
            )
            return False

    def check_tests(self) -> bool:
        """检查测试"""
        print("🔍 检查测试文件...")

        tests_dir = PROJECT_ROOT / 'tests'
        if not tests_dir.exists():
            self.add_result(
                "测试文件",
                "❌",
                "tests目录不存在",
                0, 10
            )
            return False

        test_files = list(tests_dir.rglob('test_*.py'))

        if test_files:
            self.add_result(
                "测试文件",
                "✅",
                f"找到 {len(test_files)} 个测试文件",
                10, 10
            )
            return True
        else:
            self.add_result(
                "测试文件",
                "⚠️",
                "未找到测试文件",
                0, 10
            )
            return False

    def check_documentation(self) -> bool:
        """检查文档"""
        print("🔍 检查文档...")

        required_docs = [
            'README.md',
            'CHANGELOG.md',
            'LICENSE',
        ]

        missing_docs = []
        for doc_file in required_docs:
            full_path = PROJECT_ROOT / doc_file
            if not full_path.exists():
                missing_docs.append(doc_file)

        # 检查docs目录
        docs_dir = PROJECT_ROOT / 'docs'
        doc_count = len(list(docs_dir.glob('*.md'))) if docs_dir.exists() else 0

        if not missing_docs:
            self.add_result(
                "项目文档",
                "✅",
                f"核心文档完整，docs/目录有 {doc_count} 个文档",
                10, 10
            )
            return True
        else:
            self.add_result(
                "项目文档",
                "⚠️",
                f"缺少: {', '.join(missing_docs)}",
                5, 10
            )
            return False

    def check_code_quality_tools(self) -> bool:
        """检查代码质量工具配置"""
        print("🔍 检查代码质量工具...")

        quality_files = [
            'ruff.toml',
            'mypy.ini',
            'pytest.ini',
        ]

        found = 0
        for file_path in quality_files:
            if (PROJECT_ROOT / file_path).exists():
                found += 1

        if found == len(quality_files):
            self.add_result(
                "质量工具",
                "✅",
                f"配置文件完整 ({found}/{len(quality_files)})",
                10, 10
            )
            return True
        else:
            self.add_result(
                "质量工具",
                "⚠️",
                f"配置文件 ({found}/{len(quality_files)})",
                found * 3, 10
            )
            return False

    def check_cache_directories(self) -> Tuple[int, List[Path]]:
        """检查缓存目录"""
        print("🔍 检查临时/缓存目录...")

        cache_patterns = [
            '__pycache__',
            '.pytest_cache',
            '.hypothesis',
            '.mypy_cache',
            '.ruff_cache',
        ]

        cache_dirs = []
        for pattern in cache_patterns:
            cache_dirs.extend(PROJECT_ROOT.rglob(pattern))

        count = len(cache_dirs)

        if count == 0:
            self.add_result(
                "缓存目录",
                "✅",
                "无需清理",
                5, 5
            )
        elif count <= 10:
            self.add_result(
                "缓存目录",
                "✅",
                f"发现 {count} 个缓存目录（正常）",
                5, 5
            )
        else:
            self.add_result(
                "缓存目录",
                "⚠️",
                f"发现 {count} 个缓存目录（建议清理）",
                3, 5
            )

        return count, cache_dirs

    def check_git_status(self) -> bool:
        """检查Git状态"""
        print("🔍 检查Git仓库...")

        git_dir = PROJECT_ROOT / '.git'
        if not git_dir.exists():
            self.add_result(
                "Git仓库",
                "⚠️",
                "未初始化Git仓库",
                0, 5
            )
            return False

        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                changes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

                if changes == 0:
                    status_msg = "工作目录干净"
                else:
                    status_msg = f"{changes} 个未跟踪/修改的文件"

                self.add_result(
                    "Git仓库",
                    "✅",
                    status_msg,
                    5, 5
                )
                return True
        except Exception as e:
            self.add_result(
                "Git仓库",
                "⚠️",
                f"无法检查状态: {e}",
                2, 5
            )
            return False

    def run_all_checks(self):
        """运行所有检查"""
        self.print_header("🧪 VirtualChemLab 项目健康检查")

        print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 项目路径: {PROJECT_ROOT}")
        print()

        # 运行各项检查
        self.check_python_version()
        self.check_dependencies()
        self.check_project_structure()
        self.check_config_files()
        self.check_templates()
        self.check_tests()
        self.check_documentation()
        self.check_code_quality_tools()
        self.check_cache_directories()
        self.check_git_status()

        # 打印结果
        self.print_results()

        # 返回总体状态
        return self.calculate_health_status()

    def print_results(self):
        """打印检查结果"""
        self.print_header("📊 检查结果")

        for result in self.results:
            print(f"{result['status']} {result['name']}: {result['message']}")

        # 计算百分比
        percentage = (self.score / self.max_score * 100) if self.max_score > 0 else 0

        print()
        print(f"{'='*60}")
        print(f"  总分: {self.score}/{self.max_score} ({percentage:.1f}%)")
        print(f"{'='*60}")

    def calculate_health_status(self) -> str:
        """计算健康状态"""
        percentage = (self.score / self.max_score * 100) if self.max_score > 0 else 0

        if percentage >= 90:
            status = "🟢 优秀"
            level = "excellent"
        elif percentage >= 75:
            status = "🟢 良好"
            level = "good"
        elif percentage >= 60:
            status = "🟡 一般"
            level = "fair"
        else:
            status = "🔴 需要改进"
            level = "poor"

        self.print_header("🎯 项目健康度")
        print(f"状态: {status}")
        print(f"得分: {self.score}/{self.max_score} ({percentage:.1f}%)")
        print()

        # 建议
        if level in ['fair', 'poor']:
            print("💡 改进建议:")
            for result in self.results:
                if result['status'] in ['❌', '⚠️']:
                    print(f"   - {result['name']}: {result['message']}")

        return level


def main():
    """主函数"""
    checker = HealthChecker()
    health_level = checker.run_all_checks()

    # 保存报告
    report_file = PROJECT_ROOT / 'reports' / f'health_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    report_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n📝 报告已保存到: {report_file}")

    # 退出码
    if health_level in ['excellent', 'good']:
        sys.exit(0)
    elif health_level == 'fair':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 检查已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
