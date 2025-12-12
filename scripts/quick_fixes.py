#!/usr/bin/env python3
"""
快速修复脚本 - 自动修复常见问题

使用方法:
    python scripts/quick_fixes.py --all
    python scripts/quick_fixes.py --print-to-logger
    python scripts/quick_fixes.py --fix-imports
    python scripts/quick_fixes.py --version-sync
"""

import argparse
import re
from pathlib import Path


class QuickFixer:
    """快速修复器"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixed_files: list[str] = []
        self.errors: list[str] = []
        self.project_root = Path(__file__).parent.parent

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""

        prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "WARNING": "[WARN]",
            "ERROR": "[ERROR]",
        }.get(level, "[*]")

        # 处理编码问题
        try:
            print(f"{prefix} {message}")
        except UnicodeEncodeError:
            # Windows GBK编码问题，使用ASCII字符
            print(f"{prefix} {message}".encode("gbk", errors="ignore").decode("gbk"))

    def fix_print_to_logger(self) -> int:
        """替换print为logger调用"""
        self.log("开始修复: print语句 -> logger", "INFO")

        src_dir = self.project_root / "src"
        count = 0

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                original_content = content

                # 检查是否已有logger导入
                has_logger = "import logging" in content or "from logging import" in content

                if not has_logger and "print(" in content:
                    # 添加logger导入
                    if "import " in content:
                        # 在第一个import后添加
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if line.startswith("import ") or line.startswith("from "):
                                lines.insert(i + 1, "import logging")
                                lines.insert(i + 2, "")
                                lines.insert(i + 3, "logger = logging.getLogger(__name__)")
                                content = "\n".join(lines)
                                break
                    else:
                        # 在文件开头添加
                        content = (
                            "import logging\n\nlogger = logging.getLogger(__name__)\n\n" + content
                        )

                # 替换print语句
                replacements = [
                    (r'print\("错误[:\s]+([^"]+)"\)', r'logger.error("\1")'),
                    (r'print\("警告[:\s]+([^"]+)"\)', r'logger.warning("\1")'),
                    (r'print\("调试[:\s]+([^"]+)"\)', r'logger.debug("\1")'),
                    (r'print\(f"错误[:\s]+([^"]+)"\)', r'logger.error(f"\1")'),
                    (r'print\(f"警告[:\s]+([^"]+)"\)', r'logger.warning(f"\1")'),
                    (r'print\("([^"]+)"\)', r'logger.info("\1")'),
                    (r'print\(f"([^"]+)"\)', r'logger.info(f"\1")'),
                ]

                for pattern, replacement in replacements:
                    content = re.sub(pattern, replacement, content)

                if content != original_content:
                    if not self.dry_run:
                        py_file.write_text(content, encoding="utf-8")
                    count += 1
                    self.fixed_files.append(str(py_file.relative_to(self.project_root)))
                    self.log(f"已修复: {py_file.relative_to(self.project_root)}", "SUCCESS")

            except Exception as e:
                self.errors.append(f"{py_file}: {e}")
                self.log(f"修复失败: {py_file.relative_to(self.project_root)} - {e}", "ERROR")

        self.log(f"完成! 共修复 {count} 个文件", "SUCCESS" if count > 0 else "INFO")
        return count

    def _read_current_version(self) -> str | None:
        """从 src/__init__.py 读取当前应用版本号。"""
        init_file = self.project_root / "src" / "__init__.py"
        if not init_file.exists():
            return None
        try:
            text = init_file.read_text(encoding="utf-8")
        except Exception:
            return None
        match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else None

    def fix_version_sync(self, target_version: str | None = None) -> bool:
        """同步版本号到当前应用版本或指定版本。"""
        self.log("开始同步版本号", "INFO")

        version = target_version or self._read_current_version()
        if not version:
            self.log(
                "无法解析当前版本号，请检查 src/__init__.py 或使用 --target-version 指定",
                "ERROR",
            )
            return False

        files_to_update = {
            "README.md": (r"version-\d+\.\d+\.\d+", f"version-{version}"),
            "config.json": (r'"version": "\d+\.\d+\.\d+"', f'"version": "{version}"'),
            "pyproject.toml": (r'version = "\d+\.\d+\.\d+"', f'version = "{version}"'),
        }

        count = 0
        for file_name, (pattern, replacement) in files_to_update.items():
            file_path = self.project_root / file_name
            if not file_path.exists():
                self.log(f"文件不存在: {file_name}", "WARNING")
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                new_content = re.sub(pattern, replacement, content)

                if content != new_content:
                    if not self.dry_run:
                        file_path.write_text(new_content, encoding="utf-8")
                    count += 1
                    self.log(f"已更新版本号: {file_name}", "SUCCESS")
                else:
                    self.log(f"版本号已是最新: {file_name}", "INFO")

            except Exception as e:
                self.errors.append(f"{file_name}: {e}")
                self.log(f"更新失败: {file_name} - {e}", "ERROR")

        return count > 0

    def fix_import_star(self) -> int:
        """修复通配符导入"""
        self.log("开始修复: import *", "INFO")

        src_dir = self.project_root / "src"
        count = 0

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                original_content = content

                # 检查是否有import *
                if "import *" in content:
                    # 注释掉import *
                    content = re.sub(
                        r"^from .+ import \*$",
                        r"# \g<0>  # TODO: 使用显式导入",
                        content,
                        flags=re.MULTILINE,
                    )

                if content != original_content:
                    if not self.dry_run:
                        py_file.write_text(content, encoding="utf-8")
                    count += 1
                    self.fixed_files.append(str(py_file.relative_to(self.project_root)))
                    self.log(f"已修复: {py_file.relative_to(self.project_root)}", "SUCCESS")

            except Exception as e:
                self.errors.append(f"{py_file}: {e}")
                self.log(f"修复失败: {py_file.relative_to(self.project_root)} - {e}", "ERROR")

        self.log(f"完成! 共修复 {count} 个文件", "SUCCESS" if count > 0 else "INFO")
        return count

    def fix_indentation(self) -> int:
        """修复明显的缩进错误"""
        self.log("开始修复: 缩进错误", "INFO")

        # 特定已知的缩进问题
        problem_files = {
            "src/utils/error_handler.py": {
                "line": 48,
                "pattern": r"^@staticmethod",
                "replacement": "    @staticmethod",
            }
        }

        count = 0
        for file_path_str, fix_info in problem_files.items():
            file_path = self.project_root / file_path_str
            if not file_path.exists():
                continue

            try:
                lines = file_path.read_text(encoding="utf-8").split("\n")
                line_num = fix_info["line"] - 1  # 转为0-based索引

                if line_num < len(lines):
                    original_line = lines[line_num]
                    fixed_line = re.sub(fix_info["pattern"], fix_info["replacement"], original_line)

                    if original_line != fixed_line:
                        lines[line_num] = fixed_line
                        if not self.dry_run:
                            file_path.write_text("\n".join(lines), encoding="utf-8")
                        count += 1
                        self.log(
                            f"已修复: {file_path.relative_to(self.project_root)}:{line_num + 1}",
                            "SUCCESS",
                        )

            except Exception as e:
                self.errors.append(f"{file_path}: {e}")
                self.log(f"修复失败: {file_path.relative_to(self.project_root)} - {e}", "ERROR")

        self.log(f"完成! 共修复 {count} 个文件", "SUCCESS" if count > 0 else "INFO")
        return count

    def generate_report(self) -> str:
        """生成修复报告"""
        report = ["", "=" * 60, "[Report] Quick Fix Report", "=" * 60, ""]

        report.append(f"[OK] Fixed files: {len(self.fixed_files)}")
        if self.fixed_files:
            report.append("\nFixed files:")
            for f in self.fixed_files[:10]:  # 只显示前10个
                report.append(f"  - {f}")
            if len(self.fixed_files) > 10:
                report.append(f"  ... and {len(self.fixed_files) - 10} more files")

        if self.errors:
            report.append(f"\n[ERROR] Errors: {len(self.errors)}")
            report.append("\nError details:")
            for e in self.errors[:5]:  # 只显示前5个
                report.append(f"  - {e}")
            if len(self.errors) > 5:
                report.append(f"  ... and {len(self.errors) - 5} more errors")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="VirtualChemLab 快速修复工具")
    parser.add_argument("--all", action="store_true", help="执行所有修复")
    parser.add_argument("--print-to-logger", action="store_true", help="替换print为logger")
    parser.add_argument("--fix-imports", action="store_true", help="修复通配符导入")
    parser.add_argument("--version-sync", action="store_true", help="同步版本号")
    parser.add_argument(
        "--target-version",
        help="同步到指定版本号（默认读取 src/__init__.py 的 __version__）",
    )
    parser.add_argument("--fix-indentation", action="store_true", help="修复缩进错误")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不实际修改")

    args = parser.parse_args()

    fixer = QuickFixer(dry_run=args.dry_run)

    if args.dry_run:
        fixer.log("🔍 DRY RUN 模式 - 仅预览，不会实际修改文件", "WARNING")

    # 执行修复
    if args.all or args.print_to_logger:
        fixer.fix_print_to_logger()

    if args.all or args.version_sync:
        fixer.fix_version_sync(target_version=args.target_version)

    if args.all or args.fix_imports:
        fixer.fix_import_star()

    if args.all or args.fix_indentation:
        fixer.fix_indentation()

    # 生成报告
    print(fixer.generate_report())

    if args.dry_run:
        fixer.log("\n💡 提示: 去掉 --dry-run 参数以实际执行修复", "INFO")


if __name__ == "__main__":
    main()
