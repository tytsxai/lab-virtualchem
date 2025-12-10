
"""
工具集成测试
验证所有工具能够正常工作
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

PROJECT_ROOT = Path(__file__).parent.parent

REQUIRED_DOCS = [
    "README.md",
    "INSTALL.md",
    "QUICK_START_GUIDE.md",
    "QUICK_START_COMPLETION.md",
    "PROJECT_COMPLETION_ROADMAP.md",
    "TASK_CHECKLIST.md",
]
OPTIONAL_DOCS = [
    "README_快速开始.md",
    "🔧项目修复清单.md",
    "📋修复清单总结.md",
    "📖修复资源索引.md",
    "✅修复清单已交付.md",
]
REQUIRED_TOOLS = [
    "tools/generate_secrets.py",
    "tools/test_coverage_tracker.py",
    "tools/system_health_check.py",
    "tools/license_generator.py",
    "tools/license_health_check.py",
    "tools/license_backup_tool.py",
    "tools/experiment_manager_tool.py",
    "tools/hot_reload_launcher.py",
    "tools/teacher_console.py",
    "tools/admin_server_start.py",
    "tools/maintenance_tool.py",
    "tools/maintenance_cli.py",
    "tools/workflow_checker.py",
]
OPTIONAL_TOOLS = [
    "tools/test_all_panel_features.py",
    "tools/test_developer_panel.py",
]
CONFIG_FILES = [
    "config/base.json",
    "config/development.json",
    "config/production.json",
    "config/test.json",
]


def run_command(cmd: Sequence[str], description: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print("⏱️  超时")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 异常: {exc}")
        return False

    if result.returncode == 0:
        print("✅ 成功")
        if result.stdout:
            print(f"\\n输出:\\n{result.stdout[:500]}")
    else:
        print(f"❌ 失败 (退出码: {result.returncode})")
        if result.stderr:
            print(f"\\n错误:\\n{result.stderr[:500]}")

    return result.returncode == 0


def _check_generate_secrets() -> bool:
    return run_command([sys.executable, "tools/generate_secrets.py", "--help"], "密钥生成器 - 帮助信息")


def _check_coverage_tracker() -> bool:
    return run_command([sys.executable, "tools/test_coverage_tracker.py", "--help"], "覆盖率追踪器 - 帮助信息")


def _check_config_management() -> bool:
    # Use module invocation so src imports resolve without manual PYTHONPATH hacks
    return run_command([sys.executable, "-m", "config.schemas.app_config"], "配置管理 - 加载配置")


def _check_imports() -> bool:
    print(f"\n{'=' * 60}")
    print("测试: 模块导入")
    print(f"{'=' * 60}")

    try:
        from config.schemas.app_config import Config, get_config

        config = Config()
        print(f"✅ 配置创建成功: {config.app.name}")
        singleton = get_config()
        assert singleton is get_config(), "get_config 未返回单例"
        print("✅ 单例模式工作正常")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 导入失败: {exc}")
        return False


def _check_config_files() -> list[str]:
    print(f"\n{'=' * 60}")
    print("测试: 配置文件")
    print(f"{'=' * 60}")

    missing: list[str] = []
    for config_file in CONFIG_FILES:
        path = PROJECT_ROOT / config_file
        if path.exists():
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            missing.append(config_file)
    return missing


def _check_documentation() -> list[str]:
    print(f"\\n{'=' * 60}")
    print("测试: 文档文件")
    print(f"{'=' * 60}")

    missing: list[str] = []
    print("\\n必需文档:")
    for doc in REQUIRED_DOCS:
        path = PROJECT_ROOT / doc
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {doc} ({size} bytes)")
        else:
            print(f"  ❌ {doc} 不存在")
            missing.append(doc)

    print("\\n可选文档:")
    for doc in OPTIONAL_DOCS:
        path = PROJECT_ROOT / doc
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {doc} ({size} bytes)")
        else:
            print(f"  ⚠️  {doc} 不存在 (可选)")
    return missing


def _check_tools() -> list[str]:
    print(f"\\n{'=' * 60}")
    print("测试: 工具文件")
    print(f"{'=' * 60}")

    missing: list[str] = []
    print("\\n必需工具:")
    for tool in REQUIRED_TOOLS:
        path = PROJECT_ROOT / tool
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {tool} ({size} bytes)")
        else:
            print(f"  ❌ {tool} 不存在")
            missing.append(tool)

    print("\\n可选工具:")
    for tool in OPTIONAL_TOOLS:
        path = PROJECT_ROOT / tool
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {tool} ({size} bytes)")
        else:
            print(f"  ⚠️  {tool} 不存在 (可选)")
    return missing


def main() -> int:
    print("=" * 60)
    print("VirtualChemLab 工具集成测试")
    print("=" * 60)

    results = {
        "配置文件": not _check_config_files(),
        "文档文件": not _check_documentation(),
        "工具文件": not _check_tools(),
        "模块导入": _check_imports(),
        "密钥生成器": _check_generate_secrets(),
        "覆盖率追踪器": _check_coverage_tracker(),
        "配置管理": _check_config_management(),
    }

    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")
    passed = sum(1 for v in results.values() if v)
    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")

    print(f"\n通过: {passed}/{len(results)}")
    if passed == len(results):
        print("\n🎉 所有测试通过!")
        return 0
    print(f"\n⚠️  {len(results) - passed} 个测试失败")
    return 1


def test_generate_secrets():
    assert _check_generate_secrets()


def test_coverage_tracker():
    assert _check_coverage_tracker()


def test_config_management():
    assert _check_config_management()


def test_imports():
    assert _check_imports()


def test_config_files():
    missing = _check_config_files()
    assert not missing, f"缺少配置文件: {missing}"


def test_documentation():
    missing = _check_documentation()
    assert not missing, f"缺少文档: {missing}"


def test_tools():
    missing = _check_tools()
    assert not missing, f"缺少工具: {missing}"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
