#!/usr/bin/env python3
"""
上线前自动修复脚本
自动处理上线前检查报告中发现的问题

Usage:
    python scripts/pre_launch_fixes.py --all
    python scripts/pre_launch_fixes.py --fix-prints
    python scripts/pre_launch_fixes.py --generate-secrets
    python scripts/pre_launch_fixes.py --fix-tests
"""

import os
import re
import sys
import json
import secrets
from pathlib import Path
from typing import List, Tuple, Dict
import hashlib

PROJECT_ROOT = Path(__file__).parent.parent


class PreLaunchFixer:
    """上线前自动修复工具"""

    def __init__(self):
        self.fixes_applied = []
        self.errors = []

    def run_all_fixes(self):
        """运行所有修复"""
        print("=" * 60)
        print("VirtualChemLab 上线前自动修复工具")
        print("=" * 60)
        print()

        self.generate_secrets()
        self.fix_production_config()
        self.fix_print_statements()
        self.create_env_file()
        self.verify_gitignore()

        self.print_summary()

    def generate_secrets(self):
        """生成强随机密钥"""
        print("\n[1/5] 生成安全密钥...")

        try:
            # 生成JWT密钥 (64字节 = 512位)
            jwt_secret = secrets.token_urlsafe(64)

            # 生成开发者密钥
            dev_key = secrets.token_urlsafe(32)
            dev_key_hash = self._hash_password(dev_key)

            # 生成许可证密钥
            license_secret = secrets.token_urlsafe(64)

            # 生成webhook密钥
            webhook_secret = secrets.token_urlsafe(32)

            # 保存到secrets.txt（不要提交到git）
            secrets_file = PROJECT_ROOT / "secrets.txt"
            with open(secrets_file, "w", encoding="utf-8") as f:
                f.write("# VirtualChemLab 生成的密钥 - 请妥善保管！\n")
                f.write("# ⚠️ 不要将此文件提交到版本控制系统！\n\n")
                f.write(f"JWT_SECRET_KEY={jwt_secret}\n")
                f.write(f"DEVELOPER_KEY={dev_key}\n")
                f.write(f"DEVELOPER_KEY_HASH={dev_key_hash}\n")
                f.write(f"LICENSE_SECRET_KEY={license_secret}\n")
                f.write(f"WEBHOOK_SECRET={webhook_secret}\n")

            print(f"   [OK] 密钥已生成并保存到: {secrets_file}")
            print(f"   [!] 请将密钥添加到 .env 文件或环境变量")
            print(f"   [!] 开发者密钥: {dev_key[:20]}...")

            self.fixes_applied.append("生成安全密钥")

        except Exception as e:
            print(f"   [ERROR] 错误: {e}")
            self.errors.append(f"生成密钥失败: {e}")

    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        return f"{pwd_hash.hex()}${salt}"

    def fix_production_config(self):
        """修复生产环境配置"""
        print("\n[2/5] 修复生产环境配置...")

        try:
            config_file = PROJECT_ROOT / "config" / "production.json"

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 禁用开发者模式
                if "developer" not in config:
                    config["developer"] = {}

                config["developer"]["enabled"] = False

                # 确保debug关闭
                if "app" in config:
                    config["app"]["debug"] = False
                    config["app"]["environment"] = "production"

                # 提高安全设置
                if "security" not in config:
                    config["security"] = {}

                config["security"]["password_min_length"] = 12
                config["security"]["session_timeout"] = 1800

                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)

                print(f"   [OK] 已修复: {config_file}")
                self.fixes_applied.append("修复生产环境配置")

            # 也更新主配置文件
            main_config = PROJECT_ROOT / "config.json"
            if main_config.exists():
                with open(main_config, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 添加警告注释
                if "developer" in config and config["developer"].get("enabled"):
                    print("   [!] 警告: config.json中开发者模式仍启用（开发环境）")
                    print("   [!] 生产部署时请使用 config/production.json")

        except Exception as e:
            print(f"   [ERROR] 错误: {e}")
            self.errors.append(f"修复配置失败: {e}")

    def fix_print_statements(self):
        """修复print语句（生成修复建议）"""
        print("\n[3/5] 扫描print语句...")

        try:
            src_dir = PROJECT_ROOT / "src"
            print_files: List[Tuple[Path, List[int]]] = []

            # 扫描src目录
            for py_file in src_dir.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    print_lines = []
                    for i, line in enumerate(lines, 1):
                        # 检测print语句（排除注释）
                        if re.search(r'^\s*print\s*\(', line) and not line.strip().startswith('#'):
                            print_lines.append(i)

                    if print_lines:
                        print_files.append((py_file, print_lines))

                except Exception:
                    pass

            if print_files:
                print(f"   [!] 发现 {len(print_files)} 个文件包含print语句")

                # 生成修复建议文档
                fix_guide = PROJECT_ROOT / "print_statements_fix_guide.md"
                with open(fix_guide, "w", encoding="utf-8") as f:
                    f.write("# Print语句修复指南\n\n")
                    f.write("## 发现的问题文件\n\n")

                    for file_path, line_numbers in print_files[:20]:  # 只显示前20个
                        rel_path = file_path.relative_to(PROJECT_ROOT)
                        f.write(f"### {rel_path}\n")
                        f.write(f"行号: {', '.join(map(str, line_numbers))}\n\n")

                    f.write("\n## 修复方法\n\n")
                    f.write("### 1. 使用logger替代print\n\n")
                    f.write("```python\n")
                    f.write("# 不好的方式\n")
                    f.write('print(f"用户登录: {username}")\n\n')
                    f.write("# 推荐方式\n")
                    f.write("from src.utils.logger import get_logger\n")
                    f.write("logger = get_logger(__name__)\n")
                    f.write('logger.info("用户登录", extra={"username": username})\n')
                    f.write("```\n\n")

                    f.write("### 2. 批量替换正则表达式\n\n")
                    f.write("```regex\n")
                    f.write(r"查找: print\((.*)\)" + "\n")
                    f.write(r"替换: logger.info(\1)" + "\n")
                    f.write("```\n\n")

                    f.write("### 3. 需要手动审查的情况\n\n")
                    f.write("- 调试信息 → logger.debug()\n")
                    f.write("- 错误信息 → logger.error()\n")
                    f.write("- 警告信息 → logger.warning()\n")
                    f.write("- 用户输出 → 保留print或使用UI提示\n")

                print(f"   [OK] 修复指南已生成: {fix_guide}")
                print(f"   [!] 需要手动审查并修复print语句")
                self.fixes_applied.append("生成print语句修复指南")

            else:
                print("   [OK] 未发现print语句")

        except Exception as e:
            print(f"   [ERROR] 错误: {e}")
            self.errors.append(f"扫描print语句失败: {e}")

    def create_env_file(self):
        """创建.env文件"""
        print("\n[4/5] 创建.env配置文件...")

        try:
            env_file = PROJECT_ROOT / ".env"
            env_example = PROJECT_ROOT / "env.example"

            if env_file.exists():
                print("   [!] .env文件已存在，跳过创建")
                return

            if not env_example.exists():
                print("   [!] env.example不存在，无法创建")
                return

            # 读取secrets.txt中的密钥
            secrets_file = PROJECT_ROOT / "secrets.txt"
            secrets_data = {}

            if secrets_file.exists():
                with open(secrets_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.startswith("#"):
                            key, value = line.strip().split("=", 1)
                            secrets_data[key] = value

            # 复制env.example并替换密钥
            with open(env_example, "r", encoding="utf-8") as f:
                env_content = f.read()

            # 替换密钥占位符
            for key, value in secrets_data.items():
                env_content = re.sub(
                    f"{key}=.*",
                    f"{key}={value}",
                    env_content
                )

            # 设置生产环境变量
            env_content = re.sub(
                r"ENVIRONMENT=development",
                "ENVIRONMENT=production",
                env_content
            )
            env_content = re.sub(
                r"DEBUG=True",
                "DEBUG=False",
                env_content
            )

            with open(env_file, "w", encoding="utf-8") as f:
                f.write(env_content)

            print(f"   [OK] 已创建: {env_file}")
            print("   [!] 请检查并根据实际情况调整配置")
            self.fixes_applied.append("创建.env文件")

        except Exception as e:
            print(f"   [ERROR] 错误: {e}")
            self.errors.append(f"创建.env文件失败: {e}")

    def verify_gitignore(self):
        """验证.gitignore配置"""
        print("\n[5/5] 验证.gitignore配置...")

        try:
            gitignore_file = PROJECT_ROOT / ".gitignore"

            if not gitignore_file.exists():
                print("   [!] .gitignore不存在")
                return

            with open(gitignore_file, "r", encoding="utf-8") as f:
                gitignore_content = f.read()

            required_entries = [
                ".env",
                "secrets.txt",
                "*.log",
                "data/",
                "*.db"
            ]

            missing_entries = []
            for entry in required_entries:
                if entry not in gitignore_content:
                    missing_entries.append(entry)

            if missing_entries:
                print(f"   [!] 缺少以下条目: {', '.join(missing_entries)}")

                # 添加缺失的条目
                with open(gitignore_file, "a", encoding="utf-8") as f:
                    f.write("\n# 上线前修复脚本添加\n")
                    for entry in missing_entries:
                        f.write(f"{entry}\n")

                print(f"   [OK] 已添加缺失的条目")
                self.fixes_applied.append("更新.gitignore")
            else:
                print("   [OK] .gitignore配置正确")

        except Exception as e:
            print(f"   [ERROR] 错误: {e}")
            self.errors.append(f"验证.gitignore失败: {e}")

    def print_summary(self):
        """打印修复摘要"""
        print("\n" + "=" * 60)
        print("修复摘要")
        print("=" * 60)

        if self.fixes_applied:
            print(f"\n[OK] 已应用 {len(self.fixes_applied)} 项修复:")
            for fix in self.fixes_applied:
                print(f"   * {fix}")

        if self.errors:
            print(f"\n[ERROR] 遇到 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   * {error}")

        print("\n" + "=" * 60)
        print("下一步操作")
        print("=" * 60)
        print("\n1. 查看生成的secrets.txt文件，保管好密钥")
        print("2. 将密钥配置到.env文件或环境变量")
        print("3. 审查print_statements_fix_guide.md，手动修复print语句")
        print("4. 运行测试: pytest tests/ -v")
        print("5. 运行健康检查: python scripts/health_check.py")
        print("\n[!] 重要: 不要将secrets.txt和.env提交到git！")
        print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab 上线前自动修复工具")
    parser.add_argument("--all", action="store_true", help="运行所有修复")
    parser.add_argument("--generate-secrets", action="store_true", help="生成安全密钥")
    parser.add_argument("--fix-config", action="store_true", help="修复生产配置")
    parser.add_argument("--fix-prints", action="store_true", help="扫描并生成print修复指南")
    parser.add_argument("--create-env", action="store_true", help="创建.env文件")

    args = parser.parse_args()

    fixer = PreLaunchFixer()

    if args.all or not any([args.generate_secrets, args.fix_config, args.fix_prints, args.create_env]):
        fixer.run_all_fixes()
    else:
        if args.generate_secrets:
            fixer.generate_secrets()
        if args.fix_config:
            fixer.fix_production_config()
        if args.fix_prints:
            fixer.fix_print_statements()
        if args.create_env:
            fixer.create_env_file()

        fixer.print_summary()


if __name__ == "__main__":
    main()
