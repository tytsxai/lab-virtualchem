"""VirtualChemLab 测试工具集

提供便捷的测试工具和辅助函数
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.experiment_controller import ExperimentController
from src.models.experiment import CheckPoint, ExperimentTemplate, ScoreRule, Step
from src.models.user_record import UserRecord


class TestHarness:
    """测试工具集"""

    @staticmethod
    def create_simple_template(
        exp_id: str = "test_exp",
        num_steps: int = 3
    ) -> ExperimentTemplate:
        """创建简单测试模板

        Args:
            exp_id: 实验ID
            num_steps: 步骤数量

        Returns:
            实验模板
        """
        steps = []

        for i in range(num_steps):
            if i % 3 == 0:
                # 确认型
                checkpoint = CheckPoint(
                    type="confirm",
                    message=f"确认步骤{i+1}?"
                )
            elif i % 3 == 1:
                # 输入型
                checkpoint = CheckPoint(
                    type="input",
                    expected="25.0",
                    tolerance=0.5,
                    unit="mL",
                    message=f"输入步骤{i+1}的值"
                )
            else:
                # 选择型
                checkpoint = CheckPoint(
                    type="select",
                    options=["选项A", "选项B", "选项C"],
                    expected="选项A",
                    message=f"选择步骤{i+1}的选项"
                )

            steps.append(Step(
                id=f"step{i+1}",
                title=f"步骤{i+1}",
                instruction=f"这是步骤{i+1}的说明",
                checkpoint=checkpoint
            ))

        return ExperimentTemplate(
            id=exp_id,
            title=f"测试实验 - {exp_id}",
            description="用于测试的简单实验",
            difficulty="beginner",
            duration_minutes=10,
            steps=steps,
            score_rule=ScoreRule(
                total_score=100,
                formula="100 - total_mistakes * 10"
            )
        )

    @staticmethod
    def create_test_controller(
        template: ExperimentTemplate | None = None,
        user_id: str = "test_user"
    ) -> ExperimentController:
        """创建测试控制器

        Args:
            template: 实验模板(可选,默认创建简单模板)
            user_id: 用户ID

        Returns:
            实验控制器
        """
        if template is None:
            template = TestHarness.create_simple_template()

        controller = ExperimentController(template, user_id)
        controller.start_experiment()

        return controller

    @staticmethod
    def auto_complete_experiment(
        controller: ExperimentController,
        make_mistakes: bool = False
    ) -> UserRecord:
        """自动完成实验

        Args:
            controller: 实验控制器
            make_mistakes: 是否故意犯错

        Returns:
            用户记录
        """
        mistake_count = 0

        while True:
            step = controller.get_current_step()
            if not step:
                break

            # 构造答案
            if step.checkpoint.type == "confirm":
                # 确认型 - 偶尔拒绝
                if make_mistakes and mistake_count < 2:
                    user_data = {"confirmed": False}
                    mistake_count += 1
                else:
                    user_data = {"confirmed": True}

            elif step.checkpoint.type == "input":
                # 输入型 - 偶尔输错
                if make_mistakes and mistake_count < 2:
                    user_data = {"value": "99.9"}  # 错误值
                    mistake_count += 1
                else:
                    user_data = {"value": str(step.checkpoint.expected)}

            elif step.checkpoint.type == "select":
                # 选择型 - 偶尔选错
                if make_mistakes and mistake_count < 2:
                    options = step.checkpoint.options or []
                    if len(options) > 1:
                        # 选择错误选项
                        wrong_option = [o for o in options if o != step.checkpoint.expected][0]
                        user_data = {"selected": wrong_option}
                        mistake_count += 1
                    else:
                        user_data = {"selected": step.checkpoint.expected}
                else:
                    user_data = {"selected": step.checkpoint.expected}

            elif step.checkpoint.type == "sequence":
                # 顺序型
                if make_mistakes and mistake_count < 2:
                    # 错误顺序
                    wrong_seq = list(reversed(step.checkpoint.expected))
                    user_data = {"sequence": wrong_seq}
                    mistake_count += 1
                else:
                    user_data = {"sequence": step.checkpoint.expected}

            else:
                user_data = {}

            # 提交步骤
            passed, message, score = controller.submit_step(user_data)

            # 如果通过,前进到下一步
            if passed and not controller.next_step():
                break

        return controller.finish_experiment()

    @staticmethod
    def run_experiment_scenario(
        template: ExperimentTemplate,
        steps_data: list[dict[str, Any]],
        user_id: str = "test_user"
    ) -> dict[str, Any]:
        """运行实验场景

        Args:
            template: 实验模板
            steps_data: 步骤数据列表
            user_id: 用户ID

        Returns:
            结果字典
        """
        controller = ExperimentController(template, user_id)
        controller.start_experiment()

        results = {
            "user_id": user_id,
            "experiment_id": template.id,
            "steps": [],
            "final_score": 0,
            "total_mistakes": 0
        }

        for _i, data in enumerate(steps_data):
            step = controller.get_current_step()
            if not step:
                break

            passed, message, score = controller.submit_step(data)

            results["steps"].append({
                "step_id": step.id,
                "passed": passed,
                "message": message,
                "score": score,
                "user_data": data
            })

            if passed:
                controller.next_step()

        record = controller.finish_experiment()
        results["final_score"] = record.final_score
        results["total_mistakes"] = len(record.mistakes)
        results["record_id"] = record.id

        return results

    @staticmethod
    def benchmark_experiment(
        template: ExperimentTemplate,
        num_runs: int = 100
    ) -> dict[str, Any]:
        """基准测试实验性能

        Args:
            template: 实验模板
            num_runs: 运行次数

        Returns:
            性能统计
        """
        import time

        durations = []

        for i in range(num_runs):
            controller = TestHarness.create_test_controller(template, f"bench_user_{i}")

            start_time = time.time()
            TestHarness.auto_complete_experiment(controller)
            duration = time.time() - start_time

            durations.append(duration)

        return {
            "num_runs": num_runs,
            "total_time": sum(durations),
            "avg_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations),
            "times": durations
        }

    @staticmethod
    def validate_template_file(template_path: str) -> dict[str, Any]:
        """验证模板文件

        Args:
            template_path: 模板文件路径

        Returns:
            验证结果
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {}
        }

        try:
            # 尝试加载模板
            import yaml

            with open(template_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 检查必需字段
            required_fields = ['id', 'title', 'description', 'difficulty', 'duration_minutes', 'steps', 'score_rule']

            for field in required_fields:
                if field not in data:
                    result["errors"].append(f"缺少必需字段: {field}")

            # 检查步骤
            if 'steps' in data:
                if not data['steps']:
                    result["errors"].append("步骤列表为空")
                else:
                    for i, step in enumerate(data['steps']):
                        if 'id' not in step:
                            result["errors"].append(f"步骤{i+1}缺少id")
                        if 'checkpoint' not in step:
                            result["errors"].append(f"步骤{i+1}缺少checkpoint")

            # 检查评分规则
            if 'score_rule' in data and 'total_score' not in data['score_rule']:
                result["errors"].append("评分规则缺少total_score")

            # 如果没有错误,尝试创建模板对象
            if not result["errors"]:
                try:
                    # 这里可以添加更详细的验证
                    result["valid"] = True
                    result["info"] = {
                        "id": data.get('id'),
                        "title": data.get('title'),
                        "num_steps": len(data.get('steps', [])),
                        "difficulty": data.get('difficulty'),
                        "duration_minutes": data.get('duration_minutes')
                    }
                except Exception as e:
                    result["errors"].append(f"模板对象创建失败: {str(e)}")

        except FileNotFoundError:
            result["errors"].append(f"文件不存在: {template_path}")
        except yaml.YAMLError as e:
            result["errors"].append(f"YAML解析错误: {str(e)}")
        except Exception as e:
            result["errors"].append(f"未知错误: {str(e)}")

        return result

    @staticmethod
    def compare_records(
        record1: UserRecord,
        record2: UserRecord
    ) -> dict[str, Any]:
        """比较两个实验记录

        Args:
            record1: 记录1
            record2: 记录2

        Returns:
            比较结果
        """
        return {
            "same_experiment": record1.experiment_id == record2.experiment_id,
            "score_diff": record1.final_score - record2.final_score,
            "mistakes_diff": len(record1.mistakes) - len(record2.mistakes),
            "duration_diff": (
                (record1.end_time - record1.start_time).total_seconds() -
                (record2.end_time - record2.start_time).total_seconds()
            ),
            "record1": {
                "id": record1.id,
                "user_id": record1.user_id,
                "score": record1.final_score,
                "mistakes": len(record1.mistakes)
            },
            "record2": {
                "id": record2.id,
                "user_id": record2.user_id,
                "score": record2.final_score,
                "mistakes": len(record2.mistakes)
            }
        }

    @staticmethod
    def generate_test_report(results: list[dict[str, Any]]) -> str:
        """生成测试报告

        Args:
            results: 测试结果列表

        Returns:
            Markdown格式的报告
        """
        report = ["# VirtualChemLab 测试报告\n"]
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"测试数量: {len(results)}\n\n")

        # 统计
        total_passed = sum(1 for r in results if all(s["passed"] for s in r.get("steps", [])))
        total_failed = len(results) - total_passed
        avg_score = sum(r.get("final_score", 0) for r in results) / len(results) if results else 0

        report.append("## 统计摘要\n\n")
        report.append(f"- 通过: {total_passed}\n")
        report.append(f"- 失败: {total_failed}\n")
        report.append(f"- 平均分: {avg_score:.2f}\n\n")

        # 详细结果
        report.append("## 详细结果\n\n")

        for i, result in enumerate(results, 1):
            report.append(f"### 测试 {i}: {result.get('experiment_id', 'unknown')}\n\n")
            report.append(f"- 用户: {result.get('user_id', 'unknown')}\n")
            report.append(f"- 得分: {result.get('final_score', 0):.2f}\n")
            report.append(f"- 错误: {result.get('total_mistakes', 0)}\n\n")

            if "steps" in result:
                report.append("#### 步骤详情\n\n")
                for step in result["steps"]:
                    status = "✅" if step["passed"] else "❌"
                    report.append(f"- {status} {step['step_id']}: {step['message']}\n")
                report.append("\n")

        return "".join(report)


# ============ 命令行接口 ============

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab 测试工具")
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 创建测试模板
    create_parser = subparsers.add_parser('create', help='创建测试模板')
    create_parser.add_argument('--id', default='test_exp', help='实验ID')
    create_parser.add_argument('--steps', type=int, default=3, help='步骤数')
    create_parser.add_argument('--output', help='输出文件')

    # 验证模板
    validate_parser = subparsers.add_parser('validate', help='验证模板文件')
    validate_parser.add_argument('template_path', help='模板文件路径')

    # 运行基准测试
    bench_parser = subparsers.add_parser('benchmark', help='基准测试')
    bench_parser.add_argument('template_id', help='模板ID')
    bench_parser.add_argument('--runs', type=int, default=100, help='运行次数')

    # 自动测试
    auto_parser = subparsers.add_parser('auto', help='自动测试实验')
    auto_parser.add_argument('template_id', help='模板ID')
    auto_parser.add_argument('--mistakes', action='store_true', help='故意犯错')

    args = parser.parse_args()

    if args.command == 'create':
        template = TestHarness.create_simple_template(args.id, args.steps)

        if args.output:
            import yaml
            with open(args.output, 'w', encoding='utf-8') as f:
                yaml.dump(template.model_dump(), f, allow_unicode=True)
            print(f"✅ 模板已保存到: {args.output}")
        else:
            print(json.dumps(template.model_dump(), indent=2, ensure_ascii=False))

    elif args.command == 'validate':
        result = TestHarness.validate_template_file(args.template_path)

        print(f"\n{'='*60}")
        print(f"模板验证结果: {args.template_path}")
        print(f"{'='*60}\n")

        if result["valid"]:
            print("✅ 模板有效")
            print("\n信息:")
            for key, value in result["info"].items():
                print(f"  {key}: {value}")
        else:
            print("❌ 模板无效")
            print("\n错误:")
            for error in result["errors"]:
                print(f"  - {error}")

        if result["warnings"]:
            print("\n警告:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        print()

    elif args.command == 'benchmark':
        from src.core.template_engine import TemplateEngine
        from src.utils.config import Config

        config = Config()
        engine = TemplateEngine(config.get("paths.templates_dir"))
        template = engine.load_experiment_by_id(args.template_id)

        print(f"\n🔬 开始基准测试: {args.template_id}")
        print(f"运行次数: {args.runs}\n")

        stats = TestHarness.benchmark_experiment(template, args.runs)

        print(f"{'='*60}")
        print("基准测试结果")
        print(f"{'='*60}")
        print(f"总时间: {stats['total_time']:.2f}秒")
        print(f"平均时间: {stats['avg_time']*1000:.2f}毫秒")
        print(f"最快: {stats['min_time']*1000:.2f}毫秒")
        print(f"最慢: {stats['max_time']*1000:.2f}毫秒")
        print()

    elif args.command == 'auto':
        from src.core.template_engine import TemplateEngine
        from src.utils.config import Config

        config = Config()
        engine = TemplateEngine(config.get("paths.templates_dir"))
        template = engine.load_experiment_by_id(args.template_id)

        controller = TestHarness.create_test_controller(template)

        print(f"\n🧪 自动运行实验: {template.title}")
        print(f"故意犯错: {'是' if args.mistakes else '否'}\n")

        record = TestHarness.auto_complete_experiment(controller, args.mistakes)

        print(f"{'='*60}")
        print("实验完成")
        print(f"{'='*60}")
        print(f"得分: {record.final_score:.2f}")
        print(f"错误: {len(record.mistakes)}")
        print(f"记录ID: {record.id}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()



