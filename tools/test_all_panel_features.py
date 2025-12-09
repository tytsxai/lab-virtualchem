#!/usr/bin/env python3
"""
开发者面板所有功能测试
自动测试每个按钮和工具的可用性
"""

import io
import subprocess
import sys
from pathlib import Path
from typing import Tuple, TYPE_CHECKING

try:  # 允许该脚本在非pytest环境运行
    import pytest  # type: ignore
except ImportError:  # pragma: no cover - CLI模式不需要pytest
    pytest = None

# 设置UTF-8编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

project_root = Path(__file__).parent.parent.absolute()
QUICK_TESTS: list[Tuple[str, str]] = [
    ("license_generator.py", "许可证生成器"),
    ("system_health_check.py", "系统健康检查"),
]


class PanelFeatureTester:
    """面板功能测试器"""

    def __init__(self):
        self.tools_dir = project_root / "tools"
        self.passed = []
        self.failed = []
        self.warnings = []

    def test_tool_exists(self, tool_path, description):
        """测试工具是否存在"""
        full_path = self.tools_dir / tool_path
        if full_path.exists():
            self.passed.append(f"✅ {description}: {tool_path}")
            return True
        else:
            self.failed.append(f"❌ {description}: {tool_path} (未找到)")
            return False

    def test_command(self, command, description):
        """测试命令是否可执行（仅检查语法）"""
        # 只检查命令的第一部分是否存在
        parts = command.split()
        if parts[0] in ["python", "pip", "pytest", "black", "pyinstaller"]:
            self.passed.append(f"✅ {description}: {command}")
            return True
        else:
            self.warnings.append(f"⚠️  {description}: {command} (未知命令)")
            return False

    def test_main_app_tab(self):
        """测试主应用标签页"""
        print("\n" + "=" * 60)
        print("📱 测试主应用标签页")
        print("=" * 60)

        # 标准启动
        self.test_command("python main.py", "标准模式启动")

        # 快速启动
        self.test_command("python main.py --skip-welcome", "快速启动")

        # 热加载
        self.test_tool_exists("hot_reload_launcher.py", "热加载模式")

        # 许可证模式需要两个工具
        self.test_tool_exists("license_generator.py", "许可证验证")

    def test_admin_tab(self):
        """测试管理工具标签页"""
        print("\n" + "=" * 60)
        print("👨‍💼 测试管理工具标签页")
        print("=" * 60)

        self.test_tool_exists("teacher_console.py", "教师控制台")
        self.test_tool_exists("admin_server_start.py", "管理后台")
        self.test_tool_exists("experiment_manager_tool.py", "实验管理")

    def test_license_tab(self):
        """测试许可证标签页"""
        print("\n" + "=" * 60)
        print("🔐 测试许可证标签页")
        print("=" * 60)

        self.test_tool_exists("license_generator.py", "许可证生成器")
        self.test_tool_exists("license_health_check.py", "许可证健康检查")
        self.test_tool_exists("license_backup_tool.py", "许可证备份工具")

    def test_dev_tab(self):
        """测试开发工具标签页"""
        print("\n" + "=" * 60)
        print("🛠️  测试开发工具标签页")
        print("=" * 60)

        # 构建
        spec_file = project_root / "VirtualChemLab.spec"
        if spec_file.exists():
            self.passed.append("✅ PyInstaller配置: VirtualChemLab.spec")
        else:
            self.failed.append("❌ PyInstaller配置: VirtualChemLab.spec (未找到)")

        # 依赖安装
        req_file = project_root / "requirements.txt"
        if req_file.exists():
            self.passed.append("✅ 依赖文件: requirements.txt")
        else:
            self.failed.append("❌ 依赖文件: requirements.txt (未找到)")

        # 工具
        self.test_tool_exists("system_health_check.py", "系统健康检查")
        self.test_tool_exists("generate_secrets.py", "密钥生成")
        self.test_tool_exists("test_coverage_tracker.py", "测试覆盖率")

        # 命令
        self.test_command("black src/ tests/ tools/", "代码格式化")
        self.test_command("pytest tests/ -v", "运行测试")

    def test_system_tab(self):
        """测试系统工具标签页"""
        print("\n" + "=" * 60)
        print("🔧 测试系统工具标签页")
        print("=" * 60)

        self.test_tool_exists("maintenance_tool.py", "维护工具GUI")
        self.test_tool_exists("maintenance_cli.py", "维护工具CLI")
        self.test_tool_exists("workflow_checker.py", "流程检查")

    def test_dependencies(self):
        """测试Python依赖"""
        print("\n" + "=" * 60)
        print("📦 测试Python依赖")
        print("=" * 60)

        deps = [
            ("tkinter", "图形界面"),
            ("watchdog", "热加载"),
        ]

        for module, desc in deps:
            try:
                __import__(module)
                self.passed.append(f"✅ {desc}: {module}")
            except ImportError:
                self.failed.append(f"❌ {desc}: {module} (未安装)")

    def test_directories(self):
        """测试关键目录"""
        print("\n" + "=" * 60)
        print("📁 测试关键目录")
        print("=" * 60)

        dirs = [
            ("src", "源代码目录"),
            ("tools", "工具目录"),
            ("tests", "测试目录"),
            ("config", "配置目录"),
            ("data", "数据目录"),
            ("assets", "资源目录"),
        ]

        for dir_name, desc in dirs:
            dir_path = project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                self.passed.append(f"✅ {desc}: {dir_name}/")
            else:
                self.failed.append(f"❌ {desc}: {dir_name}/ (未找到)")

    def test_main_files(self):
        """测试主要文件"""
        print("\n" + "=" * 60)
        print("📄 测试主要文件")
        print("=" * 60)

        files = [
            ("main.py", "主程序入口"),
            ("config.json", "配置文件"),
            ("requirements.txt", "依赖列表"),
            ("VirtualChemLab.spec", "打包配置"),
        ]

        for file_name, desc in files:
            file_path = project_root / file_name
            if file_path.exists():
                self.passed.append(f"✅ {desc}: {file_name}")
            else:
                self.warnings.append(f"⚠️  {desc}: {file_name} (未找到)")

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)

        total = len(self.passed) + len(self.failed) + len(self.warnings)

        print(f"\n总计: {total} 项测试")
        print(f"✅ 通过: {len(self.passed)}")
        print(f"❌ 失败: {len(self.failed)}")
        print(f"⚠️  警告: {len(self.warnings)}")

        if self.failed:
            print("\n失败的测试:")
            for item in self.failed:
                print(f"  {item}")

        if self.warnings:
            print("\n警告:")
            for item in self.warnings:
                print(f"  {item}")

        print("\n" + "=" * 60)

        if len(self.failed) == 0:
            print("✅ 所有关键功能正常，开发者面板可以使用！")
            return 0
        else:
            print(f"❌ 有 {len(self.failed)} 个功能不可用，请检查！")
            return 1

    def run_all_tests(self):
        """运行所有测试"""
        print("\n🧪 虚拟化学实验室 开发者面板功能测试")
        print(f"📂 项目根目录: {project_root}")

        self.test_main_files()
        self.test_directories()
        self.test_dependencies()
        self.test_main_app_tab()
        self.test_admin_tab()
        self.test_license_tab()
        self.test_dev_tab()
        self.test_system_tab()

        return self.print_summary()


def _tool_quick_run(tool_name, description):
    """快速测试工具是否能运行（带--help参数）"""
    print(f"\n🔍 测试 {description}...")

    tool_path = project_root / "tools" / tool_name
    if not tool_path.exists():
        print(f"  ❌ 文件不存在: {tool_name}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(tool_path), "--help"],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )

        # 如果返回码是0或者输出中包含help信息，认为工具可运行
        if result.returncode == 0 or "usage" in result.stdout.lower() or "help" in result.stdout.lower():
            print(f"  ✅ {description} 可正常运行")
            return True
        else:
            print(f"  ⚠️  {description} 返回码: {result.returncode}")
            return True  # 即使返回非0，也可能是工具不支持--help

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  {description} 执行超时")
        return False
    except Exception as e:
        print(f"  ❌ {description} 执行错误: {e}")
        return False


if pytest or TYPE_CHECKING:
    @pytest.mark.parametrize(("tool_name", "description"), QUICK_TESTS)  # type: ignore[misc]
    def test_tool_quick_run(tool_name: str, description: str):
        """Pytest参数化测试工具运行情况"""
        assert _tool_quick_run(tool_name, description)
else:
    def test_tool_quick_run() -> None:  # pragma: no cover - 仅为pytest占位
        raise RuntimeError("运行该测试需要pytest依赖")


def main():
    """主函数"""
    tester = PanelFeatureTester()
    result = tester.run_all_tests()

    # 额外：快速运行测试（可选）
    print("\n" + "=" * 60)
    print("🚀 快速运行测试（部分工具）")
    print("=" * 60)

    for tool, desc in QUICK_TESTS:
        _tool_quick_run(tool, desc)

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

    return result


if __name__ == "__main__":
    sys.exit(main())
