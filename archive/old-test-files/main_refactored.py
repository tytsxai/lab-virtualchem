#!/usr/bin/env python3
"""
VirtualChemLab - 虚拟化学实验室 (重构版)
统一启动入口

版本: v2.0.0
作者: VirtualChemLab Team
"""

import os
import sys
from pathlib import Path

# 设置Python环境编码为UTF-8（Windows系统）
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # 如果reconfigure失败，忽略错误
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加项目根目录和src目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main() -> int:
    """主函数"""
    print("=" * 60)
    print("🧪 VirtualChemLab - 虚拟化学实验室 (重构版)")
    print("📦 版本: v2.0.0")
    print("=" * 60)
    print()

    try:
        # 使用重构后的启动引导器
        from src.core.refactored_bootstrap import create_bootstrap

        bootstrap = create_bootstrap()
        return bootstrap.run()

    except ImportError as e:
        print("\n❌ 启动失败: 缺少依赖库")
        print(f"   详情: {e}")
        print("\n💡 解决方案:")
        print("   1. 运行: pip install -r requirements.txt")
        print("   2. 确保使用 Python 3.10 或更高版本")
        input("\n按回车键退出...")
        return 1

    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
