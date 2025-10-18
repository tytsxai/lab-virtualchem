"""修复文件中空白行的多余空格"""

import sys
from pathlib import Path


def fix_whitespace(file_path: Path) -> int:
    """移除文件中空白行的多余空格

    Args:
        file_path: 要处理的文件路径

    Returns:
        修复的行数
    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    fixed_count = 0
    new_lines = []

    for line in lines:
        if line.strip():  # 有内容的行
            new_lines.append(line.rstrip() + "\n")
        else:  # 空白行
            if line != "\n":
                fixed_count += 1
            new_lines.append("\n")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return fixed_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_whitespace.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)

    count = fix_whitespace(file_path)
    print(f"[OK] Fixed {count} lines with trailing whitespace")
