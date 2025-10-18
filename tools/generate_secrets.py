"""
安全密钥生成工具
用于生成项目所需的所有安全密钥

使用方法:
    python tools/generate_secrets.py              # 生成所有密钥
    python tools/generate_secrets.py --show       # 显示当前密钥
    python tools/generate_secrets.py --check      # 检查硬编码密钥
"""

import io
import os
import re
import secrets
import sys
from pathlib import Path

# 设置Windows控制台UTF-8编码
if sys.platform == "win32":
    # 切换控制台代码页到UTF-8
    os.system("chcp 65001 >nul 2>&1")
    # 重新包装stdout和stderr以使用UTF-8
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SecretGenerator:
    """安全密钥生成器"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"

    def generate_secret(self, length: int = 32) -> str:
        """生成安全密钥"""
        return secrets.token_urlsafe(length)

    def generate_all_secrets(self) -> dict[str, str]:
        """生成所有必需的密钥"""
        return {
            "JWT_SECRET_KEY": self.generate_secret(32),
            "DEVELOPER_SECRET_KEY": self.generate_secret(32),
            "SESSION_SECRET_KEY": self.generate_secret(32),
            "CRYPTO_PAYMENT_API_KEY": self.generate_secret(32),
            "DATABASE_ENCRYPTION_KEY": self.generate_secret(32),
        }

    def create_env_file(self, secrets_dict: dict[str, str], force: bool = False) -> bool:
        """创建.env文件"""
        if self.env_file.exists() and not force:
            print(f"⚠️  .env文件已存在: {self.env_file}")
            response = input("是否覆盖? (yes/no): ").lower()
            if response not in ["yes", "y"]:
                print("❌ 操作已取消")
                return False

        # 生成.env内容
        env_content = self._generate_env_content(secrets_dict)

        # 写入文件
        self.env_file.write_text(env_content, encoding="utf-8")
        print(f"✅ .env文件已创建: {self.env_file}")

        # 创建.env.example
        self._create_env_example()

        return True

    def _generate_env_content(self, secrets_dict: dict[str, str]) -> str:
        """生成.env文件内容"""
        content = """# VirtualChemLab 安全配置
# ⚠️ 请勿提交到版本控制系统
# 生成时间: {timestamp}

# 环境配置
ENVIRONMENT=development

# JWT认证密钥 (用于用户认证)
JWT_SECRET_KEY={jwt_secret}

# 开发者模式密钥
DEVELOPER_SECRET_KEY={dev_secret}

# 会话密钥
SESSION_SECRET_KEY={session_secret}

# 加密货币支付API密钥
CRYPTO_PAYMENT_API_KEY={crypto_secret}

# 数据库加密密钥
DATABASE_ENCRYPTION_KEY={db_secret}

# 许可证私钥路径
LICENSE_PRIVATE_KEY_PATH=keys/private_key.pem

# 日志级别
LOG_LEVEL=INFO

# 数据库配置
DATABASE_TYPE=json
DATABASE_PATH=data/

# Redis配置 (可选)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=
"""
        from datetime import datetime

        return content.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            jwt_secret=secrets_dict["JWT_SECRET_KEY"],
            dev_secret=secrets_dict["DEVELOPER_SECRET_KEY"],
            session_secret=secrets_dict["SESSION_SECRET_KEY"],
            crypto_secret=secrets_dict["CRYPTO_PAYMENT_API_KEY"],
            db_secret=secrets_dict["DATABASE_ENCRYPTION_KEY"],
        )

    def _create_env_example(self):
        """创建.env.example示例文件"""
        example_content = """# VirtualChemLab 环境配置示例
# 复制此文件为 .env 并填入实际值

# 环境配置
ENVIRONMENT=development

# JWT认证密钥 (用于用户认证)
# 运行: python tools/generate_secrets.py
JWT_SECRET_KEY=your-jwt-secret-key-here

# 开发者模式密钥
DEVELOPER_SECRET_KEY=your-developer-secret-key-here

# 会话密钥
SESSION_SECRET_KEY=your-session-secret-key-here

# 加密货币支付API密钥
CRYPTO_PAYMENT_API_KEY=your-crypto-payment-api-key-here

# 数据库加密密钥
DATABASE_ENCRYPTION_KEY=your-database-encryption-key-here

# 许可证私钥路径
LICENSE_PRIVATE_KEY_PATH=keys/private_key.pem

# 日志级别
LOG_LEVEL=INFO

# 数据库配置
DATABASE_TYPE=json
DATABASE_PATH=data/

# Redis配置 (可选)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=
"""
        self.env_example.write_text(example_content, encoding="utf-8")
        print(f"✅ .env.example示例文件已创建: {self.env_example}")

    def check_hardcoded_secrets(self) -> list[dict[str, str]]:
        """检查代码中的硬编码密钥"""
        print("\n🔍 检查硬编码密钥...")

        patterns = [
            (r'secret.*=.*["\']([^"\']{16,})["\']', "Secret Key"),
            (r'password.*=.*["\']([^"\']{8,})["\']', "Password"),
            (r'key.*=.*["\']([^"\']{16,})["\']', "Key"),
            (r'token.*=.*["\']([^"\']{16,})["\']', "Token"),
        ]

        findings = []
        src_dir = self.project_root / "src"

        if not src_dir.exists():
            print("❌ src目录不存在")
            return findings

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern, key_type in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # 排除明显的示例/注释
                        line = content[max(0, match.start() - 50) : match.end() + 50]
                        if any(
                            x in line.lower()
                            for x in ["example", "your-", "change", "todo", "fixme"]
                        ):
                            continue

                        findings.append(
                            {
                                "file": str(py_file.relative_to(self.project_root)),
                                "type": key_type,
                                "value": match.group(1)[:20] + "...",
                                "line": content[: match.start()].count("\n") + 1,
                            }
                        )
            except Exception as e:
                print(f"⚠️  读取文件失败 {py_file}: {e}")

        return findings

    def show_current_secrets(self):
        """显示当前配置的密钥"""
        if not self.env_file.exists():
            print("❌ .env文件不存在")
            return

        print("\n📋 当前配置的密钥:")
        content = self.env_file.read_text(encoding="utf-8")

        for line in content.split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                if any(x in key.upper() for x in ["SECRET", "KEY", "PASSWORD", "TOKEN"]):
                    # 只显示前4和后4个字符
                    if len(value) > 8:
                        masked = value[:4] + "*" * (len(value) - 8) + value[-4:]
                    else:
                        masked = "*" * len(value)
                    print(f"  {key}: {masked}")

    def check_gitignore(self):
        """检查.gitignore是否包含.env"""
        gitignore = self.project_root / ".gitignore"

        if not gitignore.exists():
            print("⚠️  .gitignore文件不存在")
            return False

        content = gitignore.read_text(encoding="utf-8")
        if ".env" not in content:
            print("⚠️  .env未添加到.gitignore")
            response = input("是否添加? (yes/no): ").lower()
            if response in ["yes", "y"]:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n# Environment variables\n.env\n")
                print("✅ 已添加.env到.gitignore")
                return True
            return False

        print("✅ .env已在.gitignore中")
        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab 安全密钥生成工具")
    parser.add_argument("--show", action="store_true", help="显示当前密钥")
    parser.add_argument("--check", action="store_true", help="检查硬编码密钥")
    parser.add_argument("--force", action="store_true", help="强制覆盖现有.env文件")

    args = parser.parse_args()

    generator = SecretGenerator()

    print("=" * 60)
    print("VirtualChemLab 安全密钥生成工具")
    print("=" * 60)

    # 检查硬编码密钥
    if args.check:
        findings = generator.check_hardcoded_secrets()
        if findings:
            print(f"\n⚠️  发现 {len(findings)} 个可能的硬编码密钥:")
            for finding in findings:
                print(f"  📄 {finding['file']}:{finding['line']}")
                print(f"     类型: {finding['type']}, 值: {finding['value']}")
        else:
            print("\n✅ 未发现明显的硬编码密钥")
        return

    # 显示当前密钥
    if args.show:
        generator.show_current_secrets()
        return

    # 生成密钥
    print("\n🔐 生成安全密钥...")
    secrets_dict = generator.generate_all_secrets()

    print(f"\n生成了 {len(secrets_dict)} 个密钥:")
    for key in secrets_dict:
        print(f"  ✓ {key}")

    # 创建.env文件
    print("\n📝 创建.env文件...")
    if generator.create_env_file(secrets_dict, force=args.force):
        print("\n✅ 密钥生成完成!")

        # 检查gitignore
        print("\n🔍 检查.gitignore...")
        generator.check_gitignore()

        print("\n" + "=" * 60)
        print("⚠️  重要提示:")
        print("=" * 60)
        print("1. .env文件包含敏感信息,请勿提交到版本控制")
        print("2. 请妥善保管生产环境的密钥")
        print("3. 定期更换密钥以提高安全性")
        print("4. 在生产环境中使用更强的密钥")
        print("=" * 60)

        print("\n📚 下一步:")
        print("  1. 检查 .env 文件内容")
        print("  2. 根据需要调整配置")
        print("  3. 运行应用测试密钥是否正常工作")
        print("  4. 使用 --check 检查代码中的硬编码密钥")


if __name__ == "__main__":
    main()
