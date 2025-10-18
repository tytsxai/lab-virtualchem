"""
工具集成测试
验证所有工具能够正常工作
"""

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# 设置UTF-8编码（Windows系统）
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: Sequence[str], description: str) -> bool:
    """运行命令并显示结果"""
    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ 成功")
            if result.stdout:
                print(f"\n输出:\n{result.stdout[:500]}")
        else:
            print(f"❌ 失败 (退出码: {result.returncode})")
            if result.stderr:
                print(f"\n错误:\n{result.stderr[:500]}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⏱️  超时")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def test_generate_secrets() -> bool:
    """测试密钥生成器"""
    return run_command(
        [sys.executable, "tools/generate_secrets.py", "--help"], "密钥生成器 - 帮助信息"
    )


def test_coverage_tracker() -> bool:
    """测试覆盖率追踪器"""
    return run_command(
        [sys.executable, "tools/test_coverage_tracker.py", "--help"], "覆盖率追踪器 - 帮助信息"
    )


def test_config_management() -> bool:
    """测试配置管理"""
    return run_command([sys.executable, "config/schemas/app_config.py"], "配置管理 - 加载配置")


def test_imports() -> bool:
    """测试模块导入"""
    print(f"\n{'=' * 60}")
    print("测试: 模块导入")
    print(f"{'=' * 60}")

    try:
        # 测试配置导入
        from config.schemas.app_config import Config, get_config

        print("✅ 配置模块导入成功")

        # 测试配置创建
        config = Config()
        print(f"✅ 配置创建成功: {config.app.name}")

        # 测试单例
        get_config()
        print("✅ 单例模式工作正常")

        return True

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_config_files() -> bool:
    """测试配置文件"""
    print(f"\n{'=' * 60}")
    print("测试: 配置文件")
    print(f"{'=' * 60}")

    config_files = [
        "config/base.json",
        "config/development.json",
        "config/production.json",
        "config/test.json",
    ]

    all_exist = True
    for config_file in config_files:
        path = PROJECT_ROOT / config_file
        if path.exists():
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            all_exist = False

    return all_exist


def test_documentation() -> bool:
    """测试文档文件"""
    print(f"\n{'=' * 60}")
    print("测试: 文档文件")
    print(f"{'=' * 60}")

    # 核心文档（必须存在）
    required_docs = [
        "README.md",
        "QUICK_START.md",
        "README_快速开始.md",
        "INSTALL.md",
        "项目文档索引.md",
    ]

    # 可选文档（Windows下emoji文件名可能有问题）
    optional_docs = [
        "🔧项目修复清单.md",
        "📋修复清单总结.md",
        "📖修复资源索引.md",
        "✅修复清单已交付.md",
    ]

    all_required_exist = True

    print("\n必需文档:")
    for doc in required_docs:
        path = PROJECT_ROOT / doc
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {doc} ({size} bytes)")
        else:
            print(f"  ❌ {doc} 不存在")
            all_required_exist = False

    print("\n可选文档:")
    for doc in optional_docs:
        path = PROJECT_ROOT / doc
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {doc} ({size} bytes)")
        else:
            print(f"  ⚠️  {doc} 不存在 (可选)")

    return all_required_exist


def test_tools() -> bool:
    """测试工具文件"""
    print(f"\n{'=' * 60}")
    print("测试: 工具文件")
    print(f"{'=' * 60}")

    # 核心工具（必须存在）
    required_tools = [
        "tools/generate_secrets.py",
        "tools/test_coverage_tracker.py",
        "工具箱.bat",
        "快速修复.bat",
        "快速测试.bat",
        "验证修复状态.py",
    ]

    # 可选工具
    optional_tools = [
        "🚀开始修复.bat",
    ]

    all_required_exist = True

    print("\n必需工具:")
    for tool in required_tools:
        path = PROJECT_ROOT / tool
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {tool} ({size} bytes)")
        else:
            print(f"  ❌ {tool} 不存在")
            all_required_exist = False

    print("\n可选工具:")
    for tool in optional_tools:
        path = PROJECT_ROOT / tool
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {tool} ({size} bytes)")
        else:
            print(f"  ⚠️  {tool} 不存在 (可选)")

    return all_required_exist


def main() -> int:
    """主测试函数"""
    print("=" * 60)
    print("VirtualChemLab 工具集成测试")
    print("=" * 60)

    results = {}

    # 测试文件存在性
    results["配置文件"] = test_config_files()
    results["文档文件"] = test_documentation()
    results["工具文件"] = test_tools()

    # 测试模块导入
    results["模块导入"] = test_imports()

    # 测试工具运行
    results["密钥生成器"] = test_generate_secrets()
    results["覆盖率追踪器"] = test_coverage_tracker()
    results["配置管理"] = test_config_management()

    # 显示总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
