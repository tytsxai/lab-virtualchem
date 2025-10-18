#!/usr/bin/env python3
"""
JWT密钥生成脚本

生成安全的JWT密钥并保存到.env文件
"""

import logging
import secrets
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_jwt_secret(length: int = 64) -> str:
    """生成JWT密钥

    Args:
        length: 密钥长度（字节数）

    Returns:
        十六进制格式的密钥
    """
    return secrets.token_hex(length)


def save_to_env(secret_key: str, env_path: Path | None = None) -> None:
    """保存密钥到.env文件

    Args:
        secret_key: JWT密钥
        env_path: .env文件路径，默认为项目根目录
    """
    if env_path is None:
        env_path = Path(__file__).parent.parent / ".env"

    # 读取现有内容
    existing_lines = []
    jwt_key_found = False

    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("JWT_SECRET_KEY="):
                    # 替换现有密钥
                    existing_lines.append(f"JWT_SECRET_KEY={secret_key}\n")
                    jwt_key_found = True
                else:
                    existing_lines.append(line)

    # 如果不存在，追加新密钥
    if not jwt_key_found:
        existing_lines.append(f"JWT_SECRET_KEY={secret_key}\n")

    # 写入文件
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(existing_lines)

    logger.info(f"✅ JWT密钥已保存到: {env_path}")


def main() -> None:
    """主函数"""
    logger.info("=== JWT密钥生成器 ===\n")

    # 生成密钥
    logger.info("生成新的JWT密钥...")
    secret_key = generate_jwt_secret(64)  # 128字符（64字节）

    logger.info(f"✅ 密钥已生成（长度: {len(secret_key)}）")
    logger.info(f"\n密钥预览: {secret_key[:20]}...{secret_key[-20:]}\n")

    # 保存到.env
    env_path = Path(__file__).parent.parent / ".env"
    logger.info(f"保存到: {env_path}")

    # 确认
    response = input("是否保存到.env文件？[y/N]: ").strip().lower()

    if response == "y":
        save_to_env(secret_key, env_path)
        logger.info("\n✅ 完成！请重启应用以使用新密钥。")
        logger.info("⚠️ 注意：请勿将.env文件提交到版本控制系统！")
    else:
        logger.info("\n❌ 已取消。")
        logger.info("如需手动配置，请在.env文件中添加：")
        logger.info(f"JWT_SECRET_KEY={secret_key}")


if __name__ == "__main__":
    main()
