#!/usr/bin/env python3
"""
VirtualChemLab 临时文件清理工具

自动清理项目中的临时文件、缓存、日志等
可以作为定期维护任务或 pre-commit hook 使用
"""

import shutil
import sys
from pathlib import Path

# 设置 UTF-8 编码输出
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 需要清理的目录模式
DIRS_TO_CLEAN = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

# 需要清理的文件模式
FILES_TO_CLEAN = [
    "*.pyc",
    "*.pyo",
    "*.log",
    ".coverage",
    "coverage.json",
    "output_*.png",
    "output_*.txt",
]

# 需要清理的特定目录的内容
DIRS_TO_CLEAN_CONTENTS = [
    "logs",
    "temp",
    "reports",
    "coverage_reports",
]


def clean_dirs(pattern: str) -> int:
    """清理匹配模式的目录"""
    count = 0
    for dirpath in ROOT_DIR.rglob(pattern):
        if dirpath.is_dir():
            try:
                shutil.rmtree(dirpath)
                print(f"  [OK] 删除目录: {dirpath.relative_to(ROOT_DIR)}")
                count += 1
            except Exception as e:
                print(f"  [FAIL] 删除失败: {dirpath.relative_to(ROOT_DIR)} - {e}")
    return count


def clean_files(pattern: str) -> int:
    """清理匹配模式的文件"""
    count = 0
    for filepath in ROOT_DIR.rglob(pattern):
        if filepath.is_file():
            try:
                filepath.unlink()
                print(f"  [OK] 删除文件: {filepath.relative_to(ROOT_DIR)}")
                count += 1
            except Exception as e:
                print(f"  [FAIL] 删除失败: {filepath.relative_to(ROOT_DIR)} - {e}")
    return count


def clean_dir_contents(dirname: str) -> int:
    """清理指定目录的内容"""
    dir_path = ROOT_DIR / dirname
    if not dir_path.exists():
        return 0

    count = 0
    for item in dir_path.iterdir():
        try:
            if item.is_file():
                item.unlink()
                print(f"  [OK] 删除文件: {item.relative_to(ROOT_DIR)}")
                count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                print(f"  [OK] 删除目录: {item.relative_to(ROOT_DIR)}")
                count += 1
        except Exception as e:
            print(f"  [FAIL] 删除失败: {item.relative_to(ROOT_DIR)} - {e}")
    return count


def get_dir_size(path: Path) -> int:
    """获取目录大小（字节）"""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def main():
    """主函数"""
    print("=" * 60)
    print("  VirtualChemLab 临时文件清理工具")
    print("=" * 60)
    print()

    # 计算清理前的大小
    total_size_before = get_dir_size(ROOT_DIR)

    total_deleted = 0

    # 清理目录
    print("[1/3] 清理缓存目录...")
    for pattern in DIRS_TO_CLEAN:
        count = clean_dirs(pattern)
        total_deleted += count

    print()

    # 清理文件
    print("[2/3] 清理临时文件...")
    for pattern in FILES_TO_CLEAN:
        count = clean_files(pattern)
        total_deleted += count

    print()

    # 清理特定目录内容
    print("[3/3] 清理特定目录内容...")
    for dirname in DIRS_TO_CLEAN_CONTENTS:
        print(f"  清理目录: {dirname}/")
        count = clean_dir_contents(dirname)
        total_deleted += count

    print()

    # 计算清理后的大小
    total_size_after = get_dir_size(ROOT_DIR)
    size_freed = total_size_before - total_size_after

    # 输出总结
    print("=" * 60)
    print("  清理完成！")
    print("=" * 60)
    print()
    print(f"  删除项目数: {total_deleted}")
    print(f"  释放空间: {format_size(size_freed)}")
    print()
    print("已清理内容：")
    print("  - Python 缓存文件 (__pycache__, *.pyc)")
    print("  - 测试缓存 (.pytest_cache, .mypy_cache)")
    print("  - 日志文件 (logs/*.log)")
    print("  - 临时报告 (reports/*)")
    print("  - 覆盖率报告 (coverage_reports/*)")
    print("  - 临时输出文件 (output_*.*)")
    print()
    print("建议每周运行一次此脚本以保持项目整洁")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n清理已取消")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback

        traceback.print_exc()
