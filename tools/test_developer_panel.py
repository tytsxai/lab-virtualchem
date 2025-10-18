#!/usr/bin/env python3
"""
开发者面板功能测试脚本
验证所有按钮对应的工具和命令是否存在
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


def test_files_exist():
    """测试所有工具文件是否存在"""
    tools_dir = project_root / "tools"

    required_tools = [
        # 主应用标签页
        "hot_reload_launcher.py",
        "license_generator.py",
        # 管理工具标签页
        "teacher_console.py",
        "admin_server_start.py",
        "experiment_manager_tool.py",
        # 许可证标签页
        "license_generator.py",
        "license_health_check.py",
        "license_backup_tool.py",
        # 开发工具标签页
        "generate_secrets.py",
        "test_coverage_tracker.py",
        "system_health_check.py",
        # 系统工具标签页
        "maintenance_tool.py",
        "maintenance_cli.py",
        "workflow_checker.py",
    ]

    print("=" * 60)
    print("开发者面板工具验证")
    print("=" * 60)
    print()

    missing_tools = []
    existing_tools = []

    for tool in required_tools:
        tool_path = tools_dir / tool
        if tool_path.exists():
            existing_tools.append(tool)
            print(f"✅ {tool}")
        else:
            missing_tools.append(tool)
            print(f"❌ {tool} - 未找到")

    print()
    print("=" * 60)
    print(f"检查完成: {len(existing_tools)}/{len(required_tools)} 个工具存在")

    if missing_tools:
        print("\n缺少的工具:")
        for tool in missing_tools:
            print(f"  - {tool}")
        print("\n⚠️  部分功能可能无法使用")
    else:
        print("✅ 所有必需工具都存在")

    print("=" * 60)

    return len(missing_tools) == 0


def test_main_files():
    """测试主程序文件"""
    print("\n检查主程序文件:")
    print("-" * 60)

    main_files = [
        "main.py",
        "VirtualChemLab.spec",
        "requirements.txt",
        "config.json",
    ]

    for file in main_files:
        file_path = project_root / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - 未找到")


def test_directories():
    """测试必要的目录"""
    print("\n检查必要的目录:")
    print("-" * 60)

    directories = [
        "src",
        "tools",
        "tests",
        "data",
        "config",
        "assets",
    ]

    for dir_name in directories:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - 未找到")


def test_import_dependencies():
    """测试Python依赖"""
    print("\n检查Python依赖:")
    print("-" * 60)

    dependencies = [
        ("tkinter", "图形界面"),
        ("watchdog", "热加载功能"),
    ]

    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✅ {module:20} - {description}")
        except ImportError:
            print(f"❌ {module:20} - {description} (未安装)")


def main():
    """主函数"""
    # 设置控制台编码为UTF-8
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("\n虚拟化学实验室 开发者面板测试")
    print()

    # 测试工具文件
    all_tools_exist = test_files_exist()

    # 测试主文件
    test_main_files()

    # 测试目录
    test_directories()

    # 测试依赖
    test_import_dependencies()

    print("\n" + "=" * 60)
    if all_tools_exist:
        print("✅ 测试完成: 开发者面板可以正常使用")
        return 0
    else:
        print("⚠️  测试完成: 部分功能可能受限")
        return 1


if __name__ == "__main__":
    sys.exit(main())
