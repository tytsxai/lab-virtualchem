#!/usr/bin/env python3
"""
修复导入顺序问题

将logging.getLogger之后的导入移到文件顶部
"""

from pathlib import Path


def fix_import_order(file_path: Path) -> bool:
    """修复单个文件的导入顺序

    Returns:
        是否进行了修改
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # 找到docstring结束位置
        docstring_end = 0
        quote_count = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote_count += 1
                if quote_count == 2:
                    docstring_end = i + 1
                    break

        # 找到logger定义位置
        logger_line = None
        for i in range(docstring_end, len(lines)):
            if "logger = logging.getLogger" in lines[i]:
                logger_line = i
                break

        if logger_line is None:
            return False

        # 收集logger之后的导入语句
        late_imports = []
        late_import_lines = []
        i = logger_line + 1

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            # 检查是否是导入语句
            if stripped.startswith("import ") or stripped.startswith("from "):
                late_imports.append(line)
                late_import_lines.append(i)
                i += 1
            else:
                # 遇到非导入语句，停止
                break

        if not late_imports:
            return False

        # 找到应该插入导入的位置（在docstring和logger之前）
        # 查找现有导入块的结束位置
        for i in range(docstring_end, logger_line):
            if lines[i].strip():
                i + 1

        # 移除迟到的导入
        for line_no in reversed(late_import_lines):
            del lines[line_no]

        # 在合适位置插入
        # 重新计算logger行位置（因为删除了一些行）
        new_logger_line = None
        for i, line in enumerate(lines):
            if "logger = logging.getLogger" in line:
                new_logger_line = i
                break

        # 在logger定义前插入导入
        if new_logger_line:
            lines[new_logger_line:new_logger_line] = late_imports

        # 写回文件
        new_content = "\n".join(lines)
        file_path.write_text(new_content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main() -> None:
    """主函数"""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src" / "core"

    if not src_dir.exists():
        print(f"[ERROR] Directory not found: {src_dir}")
        return

    print("开始修复导入顺序...")
    fixed_count = 0

    for py_file in src_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        if fix_import_order(py_file):
            print(f"[OK] Fixed: {py_file.name}")
            fixed_count += 1

    print(f"\nDone! Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
