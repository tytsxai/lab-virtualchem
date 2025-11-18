#!/usr/bin/env python
"""
开发者密钥设置工具
用于生成安全的开发者模式访问密钥，并写入 .env 文件
"""

import re
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.dev_auth import DeveloperAuth  # noqa: E402

ENV_VAR = "DEVELOPER_KEY_HASH"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def _prompt_env_file() -> Path:
    """提示用户选择要写入的环境变量文件"""
    default = str(DEFAULT_ENV_FILE)
    user_input = input(f"请输入要写入的环境变量文件路径 [{default}]: ").strip()
    if not user_input:
        return DEFAULT_ENV_FILE
    return Path(user_input).expanduser().resolve()


def _write_env_value(env_path: Path, key_hash: str) -> None:
    """统一写入逻辑，保留已有注释"""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text(f"# VirtualChemLab 环境变量\n{ENV_VAR}={key_hash}\n", encoding="utf-8")
        return

    content = env_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{ENV_VAR}=.*$", re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(f"{ENV_VAR}={key_hash}", content)
    else:
        new_content = content if content.endswith("\n") else content + "\n"
        new_content += f"{ENV_VAR}={key_hash}\n"

    env_path.write_text(new_content, encoding="utf-8")


def _handle_generated_key(key: str, env_path: Path) -> None:
    """写入环境文件并提示用户"""
    key_hash = DeveloperAuth._hash_key(key)
    _write_env_value(env_path, key_hash)

    print()
    print("✅ 密钥已写入环境变量文件")
    print(f"文件: {env_path}")
    print(f"变量: {ENV_VAR}")
    print()
    print("⚠️  提示:")
    print("  - 请妥善保存明文密钥，此处不会存储明文")
    print("  - 如需重置，请重新运行本工具")
    print()


def main():
    """主函数"""
    print("=" * 60)
    print("VirtualChemLab - 开发者密钥设置工具")
    print("=" * 60)
    print()

    env_path = DEFAULT_ENV_FILE

    # 选择操作
    print("请选择操作:")
    print("1. 生成新的随机密钥")
    print("2. 使用自定义密钥")
    print("0. 退出")
    print()

    choice = input("请输入选项 (0-2): ").strip()

    if choice == "0":
        print("已取消。")
        return 0

    env_path = _prompt_env_file()

    if choice == "1":
        print()
        print("正在生成随机密钥...")
        new_key = DeveloperAuth.generate_dev_key()
        print()
        print("=" * 60)
        print("新的开发者密钥:")
        print(f"  {new_key}")
        print("=" * 60)
        _handle_generated_key(new_key, env_path)
        return 0

    if choice == "2":
        print()
        custom_key = input("请输入自定义密钥（建议32字符以上）: ").strip()

        if not custom_key:
            print("❌ 密钥不能为空！")
            return 1

        if len(custom_key) < 8:
            print("⚠️  警告: 密钥长度过短，不够安全！")
            confirm = input("是否继续？(y/n): ").strip().lower()
            if confirm != "y":
                print("已取消。")
                return 1

        _handle_generated_key(custom_key, env_path)
        print("✅ 自定义密钥已写入环境变量文件")
        return 0

    print("❌ 无效的选项！")
    return 1


if __name__ == "__main__":
    sys.exit(main())

