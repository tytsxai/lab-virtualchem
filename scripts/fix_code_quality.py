#!/usr/bin/env python3
"""
代码质量自动修复脚本

主要修复:
1. 日志格式问题 (f-string -> lazy %)
2. 文件尾部空行
3. 简单的代码风格问题
"""

import re
import sys
from pathlib import Path


def fix_logging_fstring(content: str) -> tuple[str, int]:
    """修复日志中的f-string问题"""
    count = 0

    # 匹配 logger.xxx(f"text {var}" 模式
    pattern = r'(logger\.(debug|info|warning|error|critical|exception))\(f"([^"]*?{\w+[^}]*}[^"]*)"\)'

    def replacer(match: re.Match) -> str:
        nonlocal count
        logger_call = match.group(1)
        message = match.group(3)

        # 将 {var} 转换为 %s，并提取变量
        variables = []

        def extract_var(m: re.Match) -> str:
            var_name = m.group(0)[1:-1]  # 去掉 { }
            variables.append(var_name)
            return "%s"

        new_message = re.sub(r"{[^}]+}", extract_var, message)

        if variables:
            count += 1
            vars_str = ", ".join(variables)
            return f'{logger_call}("{new_message}", {vars_str})'
        return match.group(0)

    new_content = re.sub(pattern, replacer, content)
    return new_content, count


def fix_trailing_newlines(content: str) -> tuple[str, bool]:
    """修复文件尾部多余空行"""
    if content.endswith("\n\n\n"):
        return content.rstrip("\n") + "\n", True
    return content, False


def remove_unused_imports(content: str, _filepath: Path) -> tuple[str, int]:
    """移除明显未使用的导入（保守策略）"""
    # 这个功能较复杂，暂时跳过
    return content, 0


def fix_file(filepath: Path, dry_run: bool = True) -> dict:
    """修复单个文件"""
    try:
        content = filepath.read_text(encoding="utf-8")
        original = content
        changes = []

        # 1. 修复日志格式
        content, log_fixes = fix_logging_fstring(content)
        if log_fixes > 0:
            changes.append(f"日志格式: {log_fixes}处")

        # 2. 修复尾部空行
        content, trailing_fixed = fix_trailing_newlines(content)
        if trailing_fixed:
            changes.append("尾部空行")

        # 如果有修改
        if content != original:
            if not dry_run:
                filepath.write_text(content, encoding="utf-8")

            return {"filepath": str(filepath), "status": "fixed" if not dry_run else "would_fix", "changes": changes}

        return {"filepath": str(filepath), "status": "ok", "changes": []}

    except Exception as e:
        return {"filepath": str(filepath), "status": "error", "error": str(e)}


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="自动修复代码质量问题")
    parser.add_argument("--apply", action="store_true", help="实际应用修复（默认为dry-run）")
    parser.add_argument("--path", default="src", help="要扫描的路径（默认: src）")
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "APPLYING FIXES"

    print(f"🔧 代码质量自动修复工具 - {mode}")
    print("=" * 60)

    # 扫描所有Python文件
    root = Path(args.path)
    python_files = list(root.rglob("*.py"))

    print(f"\n📁 找到 {len(python_files)} 个Python文件")

    results = []
    for filepath in python_files:
        result = fix_file(filepath, dry_run)
        if result["status"] in ("fixed", "would_fix"):
            results.append(result)

    # 输出结果
    print(f"\n{'=' * 60}")
    print("📊 修复结果:")
    print(f"{'=' * 60}")

    if results:
        for result in results:
            status_icon = "✓" if result["status"] == "fixed" else "⚡"
            print(f"{status_icon} {result['filepath']}")
            for change in result["changes"]:
                print(f"  - {change}")
    else:
        print("✨ 没有需要修复的文件")

    print(f"\n总计: {len(results)} 个文件需要修复")

    if dry_run and results:
        print("\n💡 使用 --apply 参数来实际应用这些修复")

    return 0


if __name__ == "__main__":
    sys.exit(main())
