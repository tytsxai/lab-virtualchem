"""VirtualChemLab 开发CLI工具

提供开发、测试和调试相关的命令行工具
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.experiment_controller import ExperimentController
from src.core.template_engine import TemplateEngine
from src.storage.json_store import JSONStore
from src.utils.config import Config


class DevCLI:
    """开发CLI工具类"""

    def __init__(self):
        self.config = Config()
        self.template_engine = TemplateEngine(self.config.get("paths.templates_dir"))

    # ============ 模板命令 ============

    def list_templates(self):
        """列出所有模板"""
        experiments = self.template_engine.list_available_experiments()

        print(f"\n📋 找到 {len(experiments)} 个实验模板:\n")
        print(f"{'ID':<30} {'标题':<30} {'难度':<12} {'时长':<8}")
        print("=" * 85)

        for exp in experiments:
            exp_id = exp.get('id', 'N/A')
            title = exp.get('title', 'N/A')
            level = exp.get('level', 'N/A')
            duration = exp.get('duration_min', 'N/A')
            print(f"{exp_id:<30} {title:<30} {level:<12} {duration}分钟")

        print()

    def validate_template(self, template_id: str):
        """验证模板"""
        print(f"\n🔍 验证模板: {template_id}")

        try:
            template = self.template_engine.load_experiment_by_id(template_id)

            print("✅ 模板加载成功")
            print(f"   标题: {template.title}")
            print(f"   步骤数: {len(template.steps)}")
            print(f"   难度: {template.difficulty}")

            # 验证步骤
            for i, step in enumerate(template.steps, 1):
                print(f"\n   步骤 {i}: {step.text}")
                print(f"   - 类型: {step.check.type}")
                print(f"   - 指令: {step.instruction[:50]}...")

            print("\n✅ 模板验证通过!\n")
            return True

        except Exception as e:
            print(f"❌ 模板验证失败: {e}\n")
            return False

    def show_template(self, template_id: str):
        """显示模板详情"""
        try:
            template = self.template_engine.load_experiment_by_id(template_id)

            print(f"\n{'='*60}")
            print(f"实验模板详情: {template.id}")
            print(f"{'='*60}\n")

            print(f"标题: {template.title}")
            print(f"描述: {template.description}")
            print(f"难度: {template.difficulty}")
            print(f"预计时长: {template.duration_minutes}分钟")
            print(f"总分: {template.score_rule.total_score}")
            print(f"评分公式: {template.score_rule.formula}")

            print(f"\n步骤列表 ({len(template.steps)}个):")
            print(f"{'-'*60}")

            for i, step in enumerate(template.steps, 1):
                print(f"\n{i}. {step.text} [{step.id}]")
                print(f"   指令: {step.instruction}")
                print(f"   检查点类型: {step.check.type}")
                print(f"   期望值: {step.check.correct_value}")

                if step.hints:
                    print(f"   提示: {', '.join(step.hints)}")

            if template.knowledge_cards:
                print(f"\n知识点 ({len(template.knowledge_cards)}个):")
                print(f"   {', '.join(template.knowledge_cards)}")

            if template.curves:
                print(f"\n曲线配置 ({len(template.curves)}个):")
                for curve in template.curves:
                    print(f"   - {curve.type}: {curve.title}")

            print(f"\n{'='*60}\n")

        except Exception as e:
            print(f"❌ 无法加载模板: {e}\n")

    # ============ 实验命令 ============

    def run_experiment(self, template_id: str, user_id: str = "dev_user", interactive: bool = True):
        """运行实验(交互式或自动)"""
        try:
            template = self.template_engine.load_experiment_by_id(template_id)
            controller = ExperimentController(template, user_id)

            print(f"\n{'='*60}")
            print(f"🧪 开始实验: {template.title}")
            print(f"{'='*60}\n")

            controller.start_experiment()

            if interactive:
                self._run_interactive_experiment(controller)
            else:
                self._run_auto_experiment(controller)

            # 完成实验
            controller.complete_experiment()
            record = controller.get_record()

            print(f"\n{'='*60}")
            print("🎉 实验完成!")
            print(f"{'='*60}")
            print(f"最终得分: {record.score.total:.2f}")
            print(f"错误次数: {len(record.mistakes_summary)}")
            print(f"用时: {(record.completed_at - record.started_at).total_seconds():.2f}秒")
            print(f"记录ID: {record.record_id}")
            print()

            return record

        except Exception as e:
            print(f"❌ 实验运行失败: {e}\n")
            import traceback
            traceback.print_exc()

    def _run_interactive_experiment(self, controller: ExperimentController):
        """交互式运行实验"""
        while True:
            step = controller.get_current_step()
            if not step:
                break

            progress = controller.get_progress()

            print(f"\n步骤 {progress['current_step'] + 1}/{progress['total_steps']}")
            print(f"{'─'*60}")
            print(f"📌 {step.text}")
            print(f"📝 {step.instruction}")
            print(f"🔍 检查点类型: {step.check.type}")

            if step.hints:
                print(f"💡 提示: {step.hints[0]}")

            # 获取用户输入
            user_data = self._get_user_input(step.check.type, step.check)

            # 提交步骤
            passed, message, score = controller.submit_step(user_data)

            if passed:
                print(f"✅ {message} (得分: {score:.2f})")
                controller.next_step()
            else:
                print(f"❌ {message}")
                retry = input("重试? (y/n): ").lower()
                if retry != 'y':
                    break

    def _run_auto_experiment(self, controller: ExperimentController):
        """自动运行实验(使用期望值)"""
        while True:
            step = controller.get_current_step()
            if not step:
                break

            print(f"\n步骤: {step.text}")

            # 构造正确答案
            if step.check.type == "confirm":
                user_data = {"confirmed": True}
            elif step.check.type == "input":
                user_data = {"value": str(step.check.correct_value)}
            elif step.check.type == "select":
                user_data = {"selected": step.check.correct_value}
            elif step.check.type == "sequence":
                user_data = {"sequence": step.check.correct_value}
            else:
                user_data = {}

            passed, message, score = controller.submit_step(user_data)
            print(f"  {'✅' if passed else '❌'} {message}")

            if passed:
                controller.next_step()
            else:
                break

    def _get_user_input(self, check_type: str, check) -> dict:
        """获取用户输入"""
        if check_type == "confirm":
            response = input("\n确认? (y/n): ").lower()
            return {"confirmed": response == 'y'}

        elif check_type == "input":
            value = input(f"\n输入 {check.message}: ")
            return {"value": value}

        elif check_type == "select":
            print("\n选项:")
            for i, option in enumerate(check.options, 1):
                print(f"  {i}. {option}")

            choice = input("选择 (序号或内容): ")

            # 尝试解析序号
            try:
                index = int(choice) - 1
                selected = check.options[index] if 0 <= index < len(check.options) else choice
            except ValueError:
                selected = choice

            return {"selected": selected}

        elif check_type == "sequence":
            print("\n选项:")
            for option in check.options:
                print(f"  - {option}")

            print("\n输入排序(用逗号分隔):")
            sequence_str = input()
            sequence = [s.strip() for s in sequence_str.split(',')]

            return {"sequence": sequence}

        else:
            return {}

    # ============ 数据命令 ============

    def list_records(self, user_id: str | None = None):
        """列出实验记录"""
        data_dir = self.config.get("paths.data_dir", "data/records")
        store = JSONStore(data_dir)

        if user_id:
            records = store.find_by_user(user_id)
            print(f"\n📊 用户 {user_id} 的记录 ({len(records)}条):\n")
        else:
            records = store.list_all()
            print(f"\n📊 所有记录 ({len(records)}条):\n")

        if not records:
            print("  (无记录)\n")
            return

        print(f"{'记录ID':<40} {'用户':<15} {'实验ID':<25} {'得分':<8} {'时间'}")
        print("=" * 110)

        for record in records:
            time_str = record.start_time.strftime("%Y-%m-%d %H:%M")
            print(f"{record.record_id:<40} {record.user_id:<15} {record.experiment_id:<25} {record.score.total:<8.2f} {time_str}")

        print()

    def show_record(self, record_id: str):
        """显示记录详情"""
        data_dir = self.config.get("paths.data_dir", "data/records")
        store = JSONStore(data_dir)

        record = store.load_by_id(record_id)

        if not record:
            print(f"❌ 找不到记录: {record_id}\n")
            return

        print(f"\n{'='*60}")
        print("实验记录详情")
        print(f"{'='*60}\n")

        print(f"记录ID: {record.record_id}")
        print(f"用户ID: {record.user_id}")
        print(f"实验ID: {record.experiment_id}")
        print(f"最终得分: {record.score.total:.2f}")
        print(f"开始时间: {record.start_time}")
        print(f"结束时间: {record.end_time}")

        duration = (record.completed_at - record.started_at).total_seconds()
        print(f"用时: {duration:.2f}秒")

        print(f"\n步骤记录 ({len(record.step_records)}个):")
        print(f"{'-'*60}")

        for i, sr in enumerate(record.step_records, 1):
            print(f"{i}. {sr.step_id}: {'✅' if sr.passed else '❌'} (得分: {sr.score:.2f})")

        if record.mistakes:
            print(f"\n错误记录 ({len(record.mistakes_summary)}个):")
            print(f"{'-'*60}")

            for i, mistake in enumerate(record.mistakes, 1):
                print(f"{i}. 步骤 {mistake.step_id}")
                print(f"   用户输入: {mistake.user_input}")
                print(f"   期望值: {mistake.expected}")

        print(f"\n{'='*60}\n")

    def export_records(self, output_file: str, user_id: str | None = None):
        """导出记录到JSON"""
        data_dir = self.config.get("paths.data_dir", "data/records")
        store = JSONStore(data_dir)

        records = store.find_by_user(user_id) if user_id else store.list_all()

        # 转换为JSON
        records_data = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "experiment_id": r.experiment_id,
                "final_score": r.final_score,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "mistakes_count": len(r.mistakes)
            }
            for r in records
        ]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(records_data, f, indent=2, ensure_ascii=False)

        print(f"✅ 已导出 {len(records)} 条记录到: {output_file}\n")

    # ============ 测试命令 ============

    def run_tests(self, pattern: str = "test_*.py"):
        """运行测试"""
        import pytest

        print(f"\n🧪 运行测试: {pattern}\n")

        exit_code = pytest.main([
            "-v",
            "--tb=short",
            "-k", pattern.replace(".py", "")
        ])

        print()
        return exit_code == 0

    def check_coverage(self):
        """检查代码覆盖率"""
        import pytest

        print("\n📊 运行覆盖率测试...\n")

        exit_code = pytest.main([
            "--cov=src",
            "--cov-report=term",
            "--cov-report=html",
            "-v"
        ])

        print("\n📄 HTML报告已生成: htmlcov/index.html\n")
        return exit_code == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VirtualChemLab 开发CLI工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有模板
  python dev_cli.py templates list

  # 验证模板
  python dev_cli.py templates validate titration_naoh_hcl

  # 运行实验(交互式)
  python dev_cli.py experiment run titration_naoh_hcl

  # 运行实验(自动)
  python dev_cli.py experiment run titration_naoh_hcl --auto

  # 列出记录
  python dev_cli.py records list

  # 导出记录
  python dev_cli.py records export output.json

  # 运行测试
  python dev_cli.py test run
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 模板命令
    templates_parser = subparsers.add_parser('templates', help='模板管理')
    templates_sub = templates_parser.add_subparsers(dest='subcommand')

    templates_sub.add_parser('list', help='列出所有模板')

    validate_parser = templates_sub.add_parser('validate', help='验证模板')
    validate_parser.add_argument('template_id', help='模板ID')

    show_parser = templates_sub.add_parser('show', help='显示模板详情')
    show_parser.add_argument('template_id', help='模板ID')

    # 实验命令
    experiment_parser = subparsers.add_parser('experiment', help='实验运行')
    experiment_sub = experiment_parser.add_subparsers(dest='subcommand')

    run_parser = experiment_sub.add_parser('run', help='运行实验')
    run_parser.add_argument('template_id', help='模板ID')
    run_parser.add_argument('--user', default='dev_user', help='用户ID')
    run_parser.add_argument('--auto', action='store_true', help='自动模式')

    # 记录命令
    records_parser = subparsers.add_parser('records', help='记录管理')
    records_sub = records_parser.add_subparsers(dest='subcommand')

    list_records_parser = records_sub.add_parser('list', help='列出记录')
    list_records_parser.add_argument('--user', help='用户ID')

    show_record_parser = records_sub.add_parser('show', help='显示记录详情')
    show_record_parser.add_argument('record_id', help='记录ID')

    export_parser = records_sub.add_parser('export', help='导出记录')
    export_parser.add_argument('output_file', help='输出文件')
    export_parser.add_argument('--user', help='用户ID')

    # 测试命令
    test_parser = subparsers.add_parser('test', help='测试工具')
    test_sub = test_parser.add_subparsers(dest='subcommand')

    run_test_parser = test_sub.add_parser('run', help='运行测试')
    run_test_parser.add_argument('--pattern', default='test_*', help='测试文件模式')

    test_sub.add_parser('coverage', help='检查覆盖率')

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = DevCLI()

    # 执行命令
    try:
        if args.command == 'templates':
            if args.subcommand == 'list':
                cli.list_templates()
            elif args.subcommand == 'validate':
                cli.validate_template(args.template_id)
            elif args.subcommand == 'show':
                cli.show_template(args.template_id)

        elif args.command == 'experiment':
            if args.subcommand == 'run':
                cli.run_experiment(args.template_id, args.user, not args.auto)

        elif args.command == 'records':
            if args.subcommand == 'list':
                cli.list_records(args.user if hasattr(args, 'user') else None)
            elif args.subcommand == 'show':
                cli.show_record(args.record_id)
            elif args.subcommand == 'export':
                cli.export_records(args.output_file, args.user if hasattr(args, 'user') else None)

        elif args.command == 'test':
            if args.subcommand == 'run':
                cli.run_tests(args.pattern)
            elif args.subcommand == 'coverage':
                cli.check_coverage()

    except KeyboardInterrupt:
        print("\n\n⏹️  操作已取消\n")
    except Exception as e:
        print(f"\n❌ 错误: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
