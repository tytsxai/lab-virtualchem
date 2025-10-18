#!/usr/bin/env python
"""
开发者密钥设置工具
用于生成和设置开发者模式的访问密钥
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.dev_auth import DeveloperAuth  # noqa: E402


def main():
    """主函数"""
    print("=" * 60)
    print("VirtualChemLab - 开发者密钥设置工具")
    print("=" * 60)
    print()

    config_path = str(PROJECT_ROOT / "config.json")

    print(f"配置文件: {config_path}")
    print()

    # 选择操作
    print("请选择操作:")
    print("1. 生成新的随机密钥")
    print("2. 使用自定义密钥")
    print("3. 查看默认密钥")
    print("0. 退出")
    print()

    choice = input("请输入选项 (0-3): ").strip()

    if choice == "0":
        print("已取消。")
        return

    elif choice == "1":
        # 生成随机密钥
        print()
        print("正在生成随机密钥...")

        try:
            new_key = DeveloperAuth.setup_dev_key(config_path)

            print()
            print("✅ 成功！")
            print()
            print("=" * 60)
            print("新的开发者密钥:")
            print(f"  {new_key}")
            print("=" * 60)
            print()
            print("⚠️  重要提示:")
            print("  - 此密钥只会显示一次，请妥善保存！")
            print("  - 密钥已保存到配置文件（加密存储）")
            print("  - 请勿将密钥提交到版本控制系统")
            print()

        except Exception as e:
            print(f"❌ 设置失败: {e}")
            return 1

    elif choice == "2":
        # 自定义密钥
        print()
        custom_key = input("请输入自定义密钥（建议32字符以上）: ").strip()

        if not custom_key:
            print("❌ 密钥不能为空！")
            return 1

        if len(custom_key) < 8:
            print("⚠️  警告: 密钥长度过短，不够安全！")
            confirm = input("是否继续？(y/n): ").strip().lower()
            if confirm != 'y':
                print("已取消。")
                return

        try:
            DeveloperAuth.setup_dev_key(config_path, custom_key)

            print()
            print("✅ 自定义密钥已设置！")
            print()
            print("密钥已保存到配置文件（加密存储）")
            print()

        except Exception as e:
            print(f"❌ 设置失败: {e}")
            return 1

    elif choice == "3":
        # 查看默认密钥
        print()
        print("默认开发者密钥:")
        print(f"  {DeveloperAuth.DEFAULT_DEV_KEY}")
        print()
        print("⚠️  注意:")
        print("  - 默认密钥仅用于开发和测试")
        print("  - 生产环境必须更改为强密钥")
        print()

    else:
        print("❌ 无效的选项！")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

