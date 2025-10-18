#!/usr/bin/env python3
"""
验证紧急修复

快速验证UI测试依赖、连接池等待和索引优化修复
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_ui_tests() -> bool:
    """验证UI测试依赖"""
    print("\n=== 验证1: UI测试依赖 ===")

    try:
        # 检查README.md
        readme_path = project_root / "tests" / "ui" / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()

        if "PyQt5" in content:
            print("[FAIL] README.md中仍包含PyQt5")
            return False

        if "PySide6" not in content:
            print("[FAIL] README.md中缺少PySide6")
            return False

        print("[PASS] UI测试文档已更新为PySide6")
        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def verify_connection_pool() -> bool:
    """验证连接池等待机制"""
    print("\n=== 验证2: 连接池等待机制 ===")

    try:
        import sqlite3
        import threading
        import time

        from src.backend.db_optimizer import ConnectionPool

        # 创建测试连接池
        pool = ConnectionPool(
            creator=lambda: sqlite3.connect(":memory:"),
            max_connections=2,
            min_connections=1,
            timeout=5.0,
        )

        # 测试1: 基本功能
        conn1 = pool.get_connection()
        pool.return_connection(conn1)
        print("✓ 基本连接获取和归还")

        # 测试2: 等待机制
        result = {"success": False}

        def thread_func():
            time.sleep(0.5)
            conn = pool.get_connection()
            result["success"] = True
            pool.return_connection(conn)

        conn1 = pool.get_connection()
        conn2 = pool.get_connection()

        t = threading.Thread(target=thread_func)
        t.start()

        time.sleep(1.0)
        pool.return_connection(conn1)
        t.join(timeout=5.0)

        if not result["success"]:
            print("❌ 失败: 等待机制未正常工作")
            pool.close_all()
            return False

        print("✓ 等待和通知机制")

        # 测试3: 超时
        try:
            conn1 = pool.get_connection()  # conn2已在使用中
            pool.get_connection()  # 应该超时
            print("❌ 失败: 应该抛出TimeoutError")
            pool.close_all()
            return False
        except TimeoutError:
            print("✓ 超时机制")

        pool.return_connection(conn1)
        pool.return_connection(conn2)
        pool.close_all()

        print("✅ 通过: 连接池等待机制正常工作")
        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_index_optimizer() -> bool:
    """验证索引优化功能"""
    print("\n=== 验证3: 索引优化功能 ===")

    try:
        import sqlite3
        import tempfile

        from src.backend.db_optimizer import IndexAnalyzer

        # 创建测试数据库
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))

            # 创建测试表
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    email TEXT,
                    created_at TIMESTAMP
                )
            """)
            conn.commit()

            # 创建分析器
            analyzer = IndexAnalyzer(conn)

            # 测试1: 表分析
            result = analyzer.analyze_table("users")
            if "username" not in result.get("columns", []):
                print("❌ 失败: 表分析不正确")
                conn.close()
                return False
            print("✓ 表结构分析")

            # 测试2: 索引建议
            query_patterns = [
                "SELECT * FROM users WHERE username = ?",
                "SELECT * FROM users ORDER BY created_at DESC",
            ]
            suggestions = analyzer.suggest_indexes("users", query_patterns)

            if not suggestions:
                print("❌ 失败: 未生成索引建议")
                conn.close()
                return False

            # 验证建议格式
            for s in suggestions:
                if not all(k in s for k in ["column", "reason", "priority", "estimated_benefit"]):
                    print("❌ 失败: 索引建议格式不完整")
                    conn.close()
                    return False
            print("✓ 索引建议生成")

            # 测试3: 创建索引
            success = analyzer.create_index("users", "username")
            if not success:
                print("❌ 失败: 索引创建失败")
                conn.close()
                return False
            print("✓ 索引创建")

            # 测试4: 自动优化
            report = analyzer.auto_optimize_table("users", query_patterns)
            if "suggestions" not in report:
                print("❌ 失败: 自动优化报告不完整")
                conn.close()
                return False
            print("✓ 自动优化")

            conn.close()

        print("✅ 通过: 索引优化功能正常工作")
        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_config() -> bool:
    """验证配置文件更新"""
    print("\n=== 验证4: 配置文件 ===")

    try:
        import json

        config_path = project_root / "config" / "performance.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # 检查连接池配置
        pool_config = config.get("backend", {}).get("database", {}).get("connection_pool", {})
        if "wait_timeout" not in pool_config:
            print("❌ 失败: 缺少wait_timeout配置")
            return False
        print("✓ 连接池配置已更新")

        # 检查优化配置
        opt_config = config.get("backend", {}).get("database", {}).get("optimization", {})
        if "auto_create_indexes" not in opt_config:
            print("❌ 失败: 缺少auto_create_indexes配置")
            return False
        print("✓ 优化配置已更新")

        print("✅ 通过: 配置文件已正确更新")
        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("VirtualChemLab 紧急修复验证")
    print("=" * 60)

    results = []

    # 验证各项修复
    results.append(("UI测试依赖", verify_ui_tests()))
    results.append(("连接池等待", verify_connection_pool()))
    results.append(("索引优化", verify_index_optimizer()))
    results.append(("配置文件", verify_config()))

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证通过！修复成功！")
        print("=" * 60)
        return 0
    else:
        print("⚠️  部分验证失败，请检查！")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
