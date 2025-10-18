#!/usr/bin/env python3
"""修复代码格式问题"""

import os


def fix_imports(content: str) -> str:
    """修复导入顺序"""
    lines = content.split("\n")
    import_lines = []
    other_lines = []
    in_imports = False

    for line in lines:
        if line.strip().startswith(("import ", "from ")):
            import_lines.append(line)
            in_imports = True
        elif in_imports and line.strip() == "":
            import_lines.append(line)
        elif in_imports and not line.strip().startswith(("import ", "from ")) and line.strip() != "":
            other_lines.append(line)
            in_imports = False
        else:
            other_lines.append(line)

    # 排序导入
    if import_lines:
        # 分离标准库、第三方库和本地导入
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for line in import_lines:
            if line.strip():
                if "src." in line or "tests." in line:
                    local_imports.append(line)
                elif any(
                    pkg in line
                    for pkg in ["pydantic", "fastapi", "aiohttp", "requests", "redis", "psycopg2", "pymysql"]
                ):
                    third_party_imports.append(line)
                else:
                    stdlib_imports.append(line)
            else:
                # 空行
                if stdlib_imports and not stdlib_imports[-1].strip():
                    continue
                if third_party_imports and not third_party_imports[-1].strip():
                    continue
                if local_imports and not local_imports[-1].strip():
                    continue

                if local_imports:
                    local_imports.append(line)
                elif third_party_imports:
                    third_party_imports.append(line)
                else:
                    stdlib_imports.append(line)

        # 重新组合
        import_lines = []
        if stdlib_imports:
            import_lines.extend(stdlib_imports)
            if third_party_imports or local_imports:
                import_lines.append("")
        if third_party_imports:
            import_lines.extend(third_party_imports)
            if local_imports:
                import_lines.append("")
        if local_imports:
            import_lines.extend(local_imports)

    return "\n".join(import_lines + other_lines)


def fix_whitespace(content: str) -> str:
    """修复空白行问题"""
    # 移除行尾空白
    lines = [line.rstrip() for line in content.split("\n")]

    # 移除多余的空行
    result = []
    prev_empty = False

    for line in lines:
        if line.strip() == "":
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return "\n".join(result)


def fix_file(file_path: str) -> None:
    """修复单个文件"""
    print(f"修复文件: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # 修复导入
    content = fix_imports(content)

    # 修复空白行
    content = fix_whitespace(content)

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    """主函数"""
    # 要修复的文件列表
    files_to_fix = [
        "src/core/security/input_validator.py",
        "src/core/security/rbac.py",
        "src/core/security/encryption.py",
        "src/core/security/__init__.py",
        "src/core/async_service.py",
        "src/core/cache_manager.py",
        "src/core/database_pool.py",
        "src/core/event_driven.py",
        "src/core/cqrs.py",
        "src/core/microservices.py",
        "src/core/api_docs.py",
        "src/core/testing_framework.py",
    ]

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fix_file(file_path)
        else:
            print(f"文件不存在: {file_path}")

    print("代码格式修复完成!")


if __name__ == "__main__":
    main()
