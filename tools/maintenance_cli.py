#!/usr/bin/env python
"""
系统维护工具 - 命令行界面

提供命令行方式进行缓存清理和错误修复
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.contracts.maintenance_service import (
    CacheType,
    CleanupRequest,
    DiagnosisRequest,
    FixRequest,
)
from src.core.maintenance import MaintenanceServiceImpl
from src.interfaces.maintenance import IssueSeverity


def format_bytes(bytes_size: int) -> str:
    """格式化字节大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def cleanup_cache(args):
    """清理缓存"""
    print("🧹 开始清理缓存...")

    # 解析缓存类型
    cache_types = []
    if args.all:
        cache_types = [CacheType.ALL]
    else:
        if args.memory:
            cache_types.append(CacheType.MEMORY)
        if args.disk:
            cache_types.append(CacheType.DISK)
        if args.redis:
            cache_types.append(CacheType.REDIS)
        if args.template:
            cache_types.append(CacheType.TEMPLATE)

        if not cache_types:
            cache_types = [CacheType.ALL]

    # 创建请求
    request = CleanupRequest(
        cache_types=cache_types,
        include_expired_only=args.expired_only,
        dry_run=args.dry_run,
    )

    # 执行清理
    service = MaintenanceServiceImpl()
    response = service.cleanup_cache(request)

    # 显示结果
    if response.success:
        print("\n✅ 清理成功!")
        print(f"   清理项目数: {response.total_items_cleaned}")
        print(f"   释放空间: {format_bytes(response.total_bytes_freed)}")
        print(f"   耗时: {response.duration_seconds:.2f} 秒")

        if response.cache_infos:
            print("\n   缓存详情:")
            for info in response.cache_infos:
                print(f"     {info.cache_type.value}: {info.item_count}项, {format_bytes(info.size_bytes)}")
    else:
        print(f"\n❌ 清理失败: {response.message}")
        if response.errors:
            print("   错误:")
            for error in response.errors:
                print(f"     - {error}")


def diagnose_system(args):
    """诊断系统"""
    print("🔍 开始诊断系统...")

    # 创建请求
    request = DiagnosisRequest(
        severity_threshold=IssueSeverity(args.severity) if args.severity else IssueSeverity.LOW,
    )

    # 执行诊断
    service = MaintenanceServiceImpl()
    response = service.diagnose_system(request)

    # 显示结果
    if response.success:
        print("\n✅ 诊断完成!")
        print(f"   发现问题: {len(response.issues)}个")
        print(f"   可修复: {response.fixable_count}个")
        print(f"   严重问题: {response.critical_count}个")
        print(f"   健康评分: {response.health_score:.1f}/100")

        if response.issues:
            print("\n   问题列表:")
            severity_icons = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "ℹ️",
            }

            for i, issue in enumerate(response.issues, 1):
                icon = severity_icons.get(issue.severity.value, "•")
                fix_marker = "✓" if issue.fix_available else "✗"
                print(
                    f"     {i}. {icon} [{issue.severity.value.upper()}] {issue.title} ({fix_marker})"
                )
                if args.verbose:
                    print(f"        ID: {issue.issue_id}")
                    print(f"        描述: {issue.description}")
                    if issue.fix_available:
                        print(f"        修复说明: {issue.fix_description}")
                    print()

    else:
        print(f"\n❌ 诊断失败: {response.message}")


def fix_issues(args):
    """修复问题"""
    print("🔧 开始修复问题...")

    # 创建请求
    if args.all:
        request = FixRequest(
            fix_all=True,
            severity_threshold=IssueSeverity(args.severity) if args.severity else IssueSeverity.MEDIUM,
            dry_run=args.dry_run,
        )
    else:
        if not args.issue_ids:
            print("❌ 错误: 请指定要修复的问题ID或使用 --all")
            return

        request = FixRequest(
            issue_ids=args.issue_ids,
            dry_run=args.dry_run,
        )

    # 执行修复
    service = MaintenanceServiceImpl()
    response = service.fix_issues(request)

    # 显示结果
    if response.success:
        print("\n✅ 修复成功!")
        print(f"   成功修复: {response.total_fixed}个")
        print(f"   修复失败: {response.total_failed}个")

        if response.fixed_issues:
            print("\n   已修复问题:")
            for issue_id in response.fixed_issues:
                print(f"     - {issue_id}")

        if response.failed_issues:
            print("\n   修复失败:")
            for issue_id in response.failed_issues:
                print(f"     - {issue_id}")

    else:
        print(f"\n❌ 修复失败: {response.message}")
        if response.errors:
            print("   错误:")
            for error in response.errors:
                print(f"     - {error}")


def check_health(_args):
    """检查健康"""
    print("💊 开始检查系统健康...")

    # 执行健康检查
    service = MaintenanceServiceImpl()
    response = service.check_health()

    # 显示结果
    status_icon = "✅" if response.healthy else "⚠️"
    print(f"\n{status_icon} 健康检查完成")
    print(f"   健康评分: {response.health_score:.1f}/100")
    print(f"   系统状态: {'健康' if response.healthy else '需要注意'}")

    # 缓存状态
    print("\n   📦 缓存状态:")
    print(f"     总大小: {format_bytes(response.cache_status.get('total_size', 0))}")
    print(f"     总项目数: {response.cache_status.get('total_items', 0)}")
    print(f"     过期项: {response.cache_status.get('expired_items', 0)}")

    # 错误状态
    print("\n   🐛 错误状态:")
    print(f"     总问题数: {response.error_status.get('total_issues', 0)}")
    print(f"     严重问题: {response.error_status.get('critical_issues', 0)}")
    print(f"     高优先级: {response.error_status.get('high_issues', 0)}")
    print(f"     可修复: {response.error_status.get('fixable_issues', 0)}")

    # 问题摘要
    if response.issues_summary:
        print("\n   📊 问题摘要:")
        for severity, count in response.issues_summary.items():
            if count > 0:
                print(f"     {severity}: {count}")

    # 建议
    if response.recommendations:
        print("\n   💡 建议:")
        for rec in response.recommendations:
            print(f"     - {rec}")


def get_cache_info(_args):
    """获取缓存信息"""
    print("📊 获取缓存信息...")

    service = MaintenanceServiceImpl()
    cache_infos = service.get_cache_info()

    if not cache_infos:
        print("没有缓存信息")
        return

    print("\n缓存信息:")
    total_size = 0
    total_items = 0

    for info in cache_infos:
        print(f"\n  {info.cache_type.value.upper()}:")
        print(f"    项目数: {info.item_count}")
        print(f"    大小: {format_bytes(info.size_bytes)}")
        print(f"    过期项: {info.expired_count}")

        if info.last_cleaned:
            print(f"    最后清理: {info.last_cleaned}")

        total_size += info.size_bytes
        total_items += info.item_count

    print("\n  总计:")
    print(f"    项目数: {total_items}")
    print(f"    大小: {format_bytes(total_size)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VirtualChemLab 系统维护工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 清理所有缓存
  python maintenance_cli.py cleanup --all

  # 仅清理过期缓存
  python maintenance_cli.py cleanup --expired-only

  # 诊断系统
  python maintenance_cli.py diagnose

  # 修复所有问题
  python maintenance_cli.py fix --all

  # 检查系统健康
  python maintenance_cli.py health

  # 获取缓存信息
  python maintenance_cli.py info
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 清理命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理缓存")
    cleanup_parser.add_argument("--all", action="store_true", help="清理所有缓存")
    cleanup_parser.add_argument("--memory", action="store_true", help="清理内存缓存")
    cleanup_parser.add_argument("--disk", action="store_true", help="清理磁盘缓存")
    cleanup_parser.add_argument("--redis", action="store_true", help="清理Redis缓存")
    cleanup_parser.add_argument("--template", action="store_true", help="清理模板缓存")
    cleanup_parser.add_argument("--expired-only", action="store_true", help="仅清理过期项")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="试运行(不实际删除)")

    # 诊断命令
    diagnose_parser = subparsers.add_parser("diagnose", help="诊断系统")
    diagnose_parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low", "info"],
        help="严重程度阈值",
    )
    diagnose_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # 修复命令
    fix_parser = subparsers.add_parser("fix", help="修复问题")
    fix_parser.add_argument("--all", action="store_true", help="修复所有问题")
    fix_parser.add_argument("--issue-ids", nargs="+", help="要修复的问题ID列表")
    fix_parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        default="medium",
        help="严重程度阈值(仅用于--all)",
    )
    fix_parser.add_argument("--dry-run", action="store_true", help="试运行")

    # 健康检查命令
    subparsers.add_parser("health", help="检查系统健康")

    # 信息命令
    subparsers.add_parser("info", help="获取缓存信息")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行命令
    try:
        if args.command == "cleanup":
            cleanup_cache(args)
        elif args.command == "diagnose":
            diagnose_system(args)
        elif args.command == "fix":
            fix_issues(args)
        elif args.command == "health":
            check_health(args)
        elif args.command == "info":
            get_cache_info(args)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n\n⚠️ 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
