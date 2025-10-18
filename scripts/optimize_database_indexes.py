#!/usr/bin/env python3
"""
数据库索引优化脚本

自动分析查询模式并创建推荐的索引
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.db_optimizer import IndexAnalyzer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_query_patterns(pattern_file: str | None = None) -> dict[str, list[str]]:  # noqa: UP007
    """
    加载查询模式

    Args:
        pattern_file: 模式文件路径（可选）

    Returns:
        表名到查询模式列表的映射
    """
    # 默认常见查询模式
    default_patterns = {
        "experiments": [
            "SELECT * FROM experiments WHERE user_id = ?",
            "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC",
            "SELECT * FROM experiments WHERE experiment_type = ? AND user_id = ?",
            "SELECT COUNT(*) FROM experiments WHERE user_id = ? GROUP BY status",
        ],
        "users": [
            "SELECT * FROM users WHERE username = ?",
            "SELECT * FROM users WHERE email = ?",
            "SELECT * FROM users WHERE role = ? ORDER BY created_at DESC",
        ],
        "records": [
            "SELECT * FROM records WHERE experiment_id = ?",
            "SELECT * FROM records WHERE user_id = ? ORDER BY timestamp DESC",
            "SELECT * FROM records WHERE experiment_id = ? AND step_number = ?",
        ],
        "licenses": [
            "SELECT * FROM licenses WHERE user_id = ?",
            "SELECT * FROM licenses WHERE license_key = ?",
            "SELECT * FROM licenses WHERE status = ? AND expire_date > ?",
        ],
    }

    if pattern_file and Path(pattern_file).exists():
        try:
            with open(pattern_file, encoding="utf-8") as f:
                custom_patterns = json.load(f)
                default_patterns.update(custom_patterns)
                logger.info(f"已加载自定义查询模式: {pattern_file}")
        except Exception as e:
            logger.warning(f"加载查询模式文件失败: {e}，使用默认模式")

    return default_patterns


def analyze_database(db_path: str, pattern_file: str | None = None) -> None:
    """
    分析数据库并生成索引建议

    Args:
        db_path: 数据库路径
        pattern_file: 查询模式文件路径（可选）
    """
    logger.info(f"开始分析数据库: {db_path}")

    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        analyzer = IndexAnalyzer(conn)
    except Exception as e:
        logger.error(f"连接数据库失败: {e}")
        return

    # 加载查询模式
    query_patterns = load_query_patterns(pattern_file)

    # 分析每个表
    results = {}
    for table_name, patterns in query_patterns.items():
        logger.info(f"\n分析表: {table_name}")
        logger.info("=" * 60)

        # 检查表是否存在
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        if not cursor.fetchone():
            logger.warning(f"表 {table_name} 不存在，跳过")
            continue

        # 分析表结构
        table_info = analyzer.analyze_table(table_name)
        logger.info(f"列: {', '.join(table_info.get('columns', []))}")
        logger.info(f"现有索引: {', '.join(table_info.get('indexes', [])) or '无'}")

        # 获取索引建议
        suggestions = analyzer.suggest_indexes(table_name, patterns)

        results[table_name] = {"table_info": table_info, "suggestions": suggestions}

        if suggestions:
            logger.info(f"\n索引建议 ({len(suggestions)}个):")
            for i, suggestion in enumerate(suggestions, 1):
                logger.info(f"\n  {i}. 列: {suggestion['column']}")
                logger.info(f"     原因: {suggestion['reason']}")
                logger.info(f"     优先级: {suggestion['priority']}")
                logger.info(f"     预估收益: {suggestion['estimated_benefit']}")
        else:
            logger.info("\n✓ 无需额外索引")

    # 生成报告
    report_path = project_root / "reports" / "index_optimization_report.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n详细报告已保存到: {report_path}")

    # 生成SQL脚本
    sql_path = project_root / "reports" / "create_indexes.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- 自动生成的索引创建脚本\n")
        f.write(f"-- 生成时间: {Path(__file__).stat().st_mtime}\n\n")

        for table_name, result in results.items():
            suggestions = result.get("suggestions", [])
            if suggestions:
                f.write(f"-- 表: {table_name}\n")
                for suggestion in suggestions:
                    if suggestion["priority"] == "high":
                        col = suggestion["column"]
                        idx_name = f"idx_{table_name}_{col}"
                        f.write(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({col});\n")
                        f.write(f"-- {suggestion['reason']}\n\n")

    logger.info(f"SQL脚本已保存到: {sql_path}")

    conn.close()
    logger.info("\n分析完成！")


def auto_create_indexes(
    db_path: str, pattern_file: str | None = None, priority: str = "high"
) -> None:
    """
    自动创建推荐的索引

    Args:
        db_path: 数据库路径
        pattern_file: 查询模式文件路径（可选）
        priority: 创建的索引优先级 (high/medium/low)
    """
    logger.info(f"开始自动优化数据库: {db_path}")
    logger.info(f"创建优先级: {priority}")

    try:
        conn = sqlite3.connect(db_path)
        analyzer = IndexAnalyzer(conn)
    except Exception as e:
        logger.error(f"连接数据库失败: {e}")
        return

    query_patterns = load_query_patterns(pattern_file)

    total_created = 0
    total_failed = 0

    for table_name, patterns in query_patterns.items():
        # 检查表是否存在
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        if not cursor.fetchone():
            continue

        # 自动优化表
        report = analyzer.auto_optimize_table(table_name, patterns)

        created = report.get("created", [])
        failed = report.get("failed", [])

        if created:
            logger.info(f"\n表 {table_name}:")
            for item in created:
                logger.info(f"  ✓ 已创建索引: {item['column']} ({item['reason']})")
                total_created += 1

        if failed:
            for item in failed:
                logger.error(f"  ✗ 创建失败: {item['column']} - {item['error']}")
                total_failed += 1

    logger.info("\n优化完成！")
    logger.info(f"成功创建: {total_created} 个索引")
    if total_failed > 0:
        logger.warning(f"创建失败: {total_failed} 个索引")

    conn.close()


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库索引优化工具")
    parser.add_argument(
        "action",
        choices=["analyze", "auto-create"],
        help="操作类型: analyze=仅分析, auto-create=自动创建索引",
    )
    parser.add_argument(
        "--db", default="data/virtualchemlab.db", help="数据库路径 (默认: data/virtualchemlab.db)"
    )
    parser.add_argument("--patterns", help="查询模式文件路径 (JSON格式)")
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        default="high",
        help="自动创建索引的优先级 (默认: high)",
    )

    args = parser.parse_args()

    db_path = project_root / args.db
    if not db_path.exists():
        logger.error(f"数据库不存在: {db_path}")
        return

    if args.action == "analyze":
        analyze_database(str(db_path), args.patterns)
    elif args.action == "auto-create":
        auto_create_indexes(str(db_path), args.patterns, args.priority)


if __name__ == "__main__":
    main()
