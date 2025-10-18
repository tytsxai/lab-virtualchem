"""实验管理工具 - 提供命令行界面管理实验

功能:
- 添加、更新、删除实验
- 列出和搜索实验
- 验证实验模板
- 编译自然语言描述为实验
- 实验热重载
- 批量操作
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.experiment_compiler import ExperimentCompiler, save_compiled_template  # noqa: E402
from src.core.enhanced_experiment_manager import EnhancedExperimentManager  # noqa: E402


def setup_manager(templates_dir: str = None, use_ai: bool = False):
    """设置实验管理器"""
    if templates_dir is None:
        templates_dir = project_root / "assets" / "templates"

    ai_assistant = None
    if use_ai:
        try:
            from src.ai.chemistry_assistant import ChemistryAI

            ai_assistant = ChemistryAI()
            print("✓ AI助手已启用")
        except Exception as e:
            print(f"⚠ 无法启用AI助手: {e}")

    manager = EnhancedExperimentManager(templates_dir=templates_dir, ai_assistant=ai_assistant)

    return manager


def cmd_list(args):
    """列出实验"""
    manager = setup_manager(args.templates_dir)

    experiments = manager.list_experiments(category=args.category, level=args.level)

    if not experiments:
        print("没有找到实验")
        return

    print(f"\n共找到 {len(experiments)} 个实验:\n")
    print(f"{'ID':<30} {'标题':<30} {'难度':<12} {'时长'}")
    print("-" * 90)

    for exp in experiments:
        exp_id = exp.get("id", "")[:28]
        title = exp.get("title", "")[:28]
        level = exp.get("level", "")
        duration = exp.get("duration_min", "")

        print(f"{exp_id:<30} {title:<30} {level:<12} {duration}分钟")


def cmd_info(args):
    """显示实验详细信息"""
    manager = setup_manager(args.templates_dir)

    try:
        info = manager.get_experiment_info(args.experiment_id)

        if not info:
            print(f"实验 {args.experiment_id} 不存在")
            return

        print(f"\n实验信息: {args.experiment_id}")
        print("=" * 60)
        print(f"标题: {info.get('title')}")
        if info.get("title_en"):
            print(f"英文标题: {info.get('title_en')}")
        print(f"描述: {info.get('description', '无')}")
        print(f"分类: {info.get('category', '未分类')}")
        print(f"难度: {info.get('level')}")
        print(f"预计时长: {info.get('duration_min')} 分钟")
        print(f"步骤数: {info.get('steps_count')}")
        print(f"试剂数: {info.get('reagents_count')}")

        if info.get("prerequisites"):
            print(f"前置实验: {', '.join(info['prerequisites'])}")

        print(f"版本: {info.get('version')}")
        print(f"包含曲线: {'是' if info.get('has_curves') else '否'}")
        print(f"包含目标: {'是' if info.get('has_goals') else '否'}")

    except Exception as e:
        print(f"获取信息失败: {e}")


def cmd_add(args):
    """添加新实验"""
    manager = setup_manager(args.templates_dir, use_ai=args.use_ai)

    source_path = Path(args.source)

    if not source_path.exists():
        print(f"文件不存在: {source_path}")
        return

    print(f"正在编译实验: {source_path}")

    success, template, messages = manager.add_experiment(
        source=source_path, format_type=args.format, save=not args.no_save
    )

    # 显示消息
    for msg in messages:
        print(f"  {msg}")

    if success:
        print(f"\n✓ 实验添加成功: {template.id}")
        print(f"  标题: {template.title}")
        print(f"  步骤数: {len(template.steps)}")
    else:
        print("\n✗ 实验添加失败")
        return 1


def cmd_update(args):
    """更新实验"""
    manager = setup_manager(args.templates_dir)

    # 解析更新数据
    try:
        if args.field and args.value:
            updates = {args.field: args.value}
        elif args.json_file:
            with open(args.json_file, encoding="utf-8") as f:
                updates = json.load(f)
        else:
            print("请提供 --field/--value 或 --json-file")
            return 1

    except Exception as e:
        print(f"解析更新数据失败: {e}")
        return 1

    print(f"正在更新实验: {args.experiment_id}")

    success, messages = manager.update_experiment(args.experiment_id, updates)

    for msg in messages:
        print(f"  {msg}")

    if success:
        print("\n✓ 更新成功")
    else:
        print("\n✗ 更新失败")
        return 1


def cmd_delete(args):
    """删除实验"""
    manager = setup_manager(args.templates_dir)

    if not args.yes:
        confirm = input(f"确认删除实验 {args.experiment_id}? (y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            return

    print(f"正在删除实验: {args.experiment_id}")

    success, messages = manager.delete_experiment(args.experiment_id, force=args.force)

    for msg in messages:
        print(f"  {msg}")

    if success:
        print("\n✓ 删除成功")
    else:
        print("\n✗ 删除失败")
        return 1


def cmd_validate(args):
    """验证实验模板"""
    manager = setup_manager(args.templates_dir)

    try:
        template = manager.load_experiment(args.experiment_id)

        result = manager.compiler.validate_and_fix(template)

        print(f"\n验证结果: {args.experiment_id}")
        print("=" * 60)

        if result.success:
            print("✓ 模板有效")
        else:
            print("✗ 模板存在错误")

        if result.errors:
            print("\n错误:")
            for error in result.errors:
                print(f"  - {error}")

        if result.warnings:
            print("\n警告:")
            for warning in result.warnings:
                print(f"  - {warning}")

        if result.suggestions:
            print("\n改进建议:")
            for suggestion in result.suggestions:
                print(f"  - {suggestion}")

    except Exception as e:
        print(f"验证失败: {e}")
        return 1


def cmd_compile(args):
    """编译实验"""
    compiler = ExperimentCompiler()

    source_path = Path(args.source)

    if not source_path.exists():
        print(f"文件不存在: {source_path}")
        return 1

    print(f"正在编译: {source_path}")

    result = compiler.compile_from_file(source_path)

    print("\n编译结果:")
    print("=" * 60)

    if result.success:
        print("✓ 编译成功")
        print(f"\n实验ID: {result.template.id}")
        print(f"标题: {result.template.title}")
        print(f"步骤数: {len(result.template.steps)}")

        # 保存
        if args.output:
            output_path = Path(args.output)
            format_type = "yaml" if output_path.suffix in [".yaml", ".yml"] else "json"

            if save_compiled_template(result, output_path, format_type=format_type):
                print(f"\n✓ 已保存至: {output_path}")
            else:
                print("\n✗ 保存失败")

    else:
        print("✗ 编译失败")

    if result.errors:
        print("\n错误:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("\n警告:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.suggestions:
        print("\n建议:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")


def cmd_stats(args):
    """显示统计信息"""
    manager = setup_manager(args.templates_dir)

    stats = manager.get_experiment_statistics()

    print("\n实验统计信息")
    print("=" * 60)
    print(f"总实验数: {stats['total_experiments']}")
    print(f"活动会话: {stats['active_sessions']}")
    print(f"总记录数: {stats['total_records']}")

    print("\n按难度分布:")
    for level, count in stats["by_level"].items():
        print(f"  {level}: {count}")

    print("\n按分类分布:")
    for category, count in stats["by_category"].items():
        print(f"  {category}: {count}")


def cmd_reload(args):
    """重新加载实验"""
    manager = setup_manager(args.templates_dir)

    print("检查实验更新...")

    count = manager.reload_updated_experiments()

    print(f"\n✓ 已重新加载 {count} 个实验")


def main():
    parser = argparse.ArgumentParser(
        description="实验管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--templates-dir", help="模板目录路径", default=None)

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list命令
    parser_list = subparsers.add_parser("list", help="列出实验")
    parser_list.add_argument("--category", help="按分类筛选")
    parser_list.add_argument("--level", help="按难度筛选")
    parser_list.set_defaults(func=cmd_list)

    # info命令
    parser_info = subparsers.add_parser("info", help="显示实验信息")
    parser_info.add_argument("experiment_id", help="实验ID")
    parser_info.set_defaults(func=cmd_info)

    # add命令
    parser_add = subparsers.add_parser("add", help="添加实验")
    parser_add.add_argument("source", help="源文件路径")
    parser_add.add_argument("--format", default="auto", help="格式类型")
    parser_add.add_argument("--use-ai", action="store_true", help="使用AI辅助")
    parser_add.add_argument("--no-save", action="store_true", help="不保存到文件")
    parser_add.set_defaults(func=cmd_add)

    # update命令
    parser_update = subparsers.add_parser("update", help="更新实验")
    parser_update.add_argument("experiment_id", help="实验ID")
    parser_update.add_argument("--field", help="字段名")
    parser_update.add_argument("--value", help="字段值")
    parser_update.add_argument("--json-file", help="JSON更新文件")
    parser_update.set_defaults(func=cmd_update)

    # delete命令
    parser_delete = subparsers.add_parser("delete", help="删除实验")
    parser_delete.add_argument("experiment_id", help="实验ID")
    parser_delete.add_argument("--force", action="store_true", help="强制删除")
    parser_delete.add_argument("-y", "--yes", action="store_true", help="跳过确认")
    parser_delete.set_defaults(func=cmd_delete)

    # validate命令
    parser_validate = subparsers.add_parser("validate", help="验证实验")
    parser_validate.add_argument("experiment_id", help="实验ID")
    parser_validate.set_defaults(func=cmd_validate)

    # compile命令
    parser_compile = subparsers.add_parser("compile", help="编译实验")
    parser_compile.add_argument("source", help="源文件路径")
    parser_compile.add_argument("-o", "--output", help="输出文件路径")
    parser_compile.set_defaults(func=cmd_compile)

    # stats命令
    parser_stats = subparsers.add_parser("stats", help="显示统计信息")
    parser_stats.set_defaults(func=cmd_stats)

    # reload命令
    parser_reload = subparsers.add_parser("reload", help="重新加载实验")
    parser_reload.set_defaults(func=cmd_reload)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print("\n\n已中断")
        return 130
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
