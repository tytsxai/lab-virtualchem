"""VirtualChemLab API集成示例

展示如何使用API客户端与VirtualChemLab集成
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.client import VirtualChemLabClient


def example_basic_usage():
    """基础使用示例"""
    print("\n" + "="*60)
    print("示例1: 基础API使用")
    print("="*60 + "\n")

    # 创建客户端
    client = VirtualChemLabClient("http://localhost:8080")

    # 1. 健康检查
    print("1️⃣ 健康检查...")
    health = client.health_check()
    print(f"   服务器状态: {health['status']}")
    print(f"   版本: {health['version']}")

    # 2. 列出实验
    print("\n2️⃣ 获取实验列表...")
    experiments = client.list_experiments()
    print(f"   找到 {len(experiments)} 个实验:")
    for exp in experiments[:3]:  # 只显示前3个
        print(f"   - {exp['id']}: {exp['title']}")

    if not experiments:
        print("   ⚠️  没有可用的实验")
        return

    # 3. 获取实验详情
    exp_id = experiments[0]['id']
    print(f"\n3️⃣ 获取实验详情: {exp_id}")
    experiment = client.get_experiment(exp_id)
    print(f"   标题: {experiment['title']}")
    print(f"   难度: {experiment['difficulty']}")
    print(f"   步骤数: {len(experiment['steps'])}")

    # 4. 开始实验
    print("\n4️⃣ 开始实验...")
    session = client.start_experiment(exp_id, user_id="example_user")
    print(f"   会话ID: {session['session_id']}")
    print(f"   当前步骤: {session['current_step']['title']}")

    # 5. 提交步骤
    print("\n5️⃣ 提交步骤...")

    # 根据检查点类型提交不同数据
    checkpoint_type = session['current_step']['checkpoint_type']

    if checkpoint_type == "confirm":
        result = client.submit_step({"confirmed": True})
    elif checkpoint_type == "input":
        result = client.submit_step({"value": "25.0"})
    elif checkpoint_type == "select":
        result = client.submit_step({"selected": "选项A"})
    else:
        result = client.submit_step({})

    print(f"   结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"   消息: {result['message']}")
    print(f"   得分: {result.get('score', 0)}")

    # 6. 完成实验
    print("\n6️⃣ 完成实验...")
    final_result = client.finish_experiment()
    print(f"   记录ID: {final_result['record_id']}")
    print(f"   最终得分: {final_result['final_score']}")
    print(f"   错误次数: {final_result['total_mistakes']}")
    print(f"   用时: {final_result['duration_seconds']:.2f}秒")

    # 7. 生成报告
    print("\n7️⃣ 生成报告...")
    report = client.generate_report(final_result['record_id'])
    print(f"   报告URL: {report['url']}")


def example_complete_experiment():
    """完整实验流程示例"""
    print("\n" + "="*60)
    print("示例2: 完整实验流程")
    print("="*60 + "\n")

    client = VirtualChemLabClient("http://localhost:8080")

    # 获取第一个实验
    experiments = client.list_experiments()
    if not experiments:
        print("⚠️  没有可用的实验")
        return

    exp_id = experiments[0]['id']

    # 准备步骤数据(根据实验类型调整)
    steps_data = [
        {"confirmed": True},      # 步骤1: 确认
        {"value": "25.0"},        # 步骤2: 输入
        {"selected": "酚酞"},     # 步骤3: 选择
        # ... 根据实际实验添加更多步骤
    ]

    # 运行完整实验
    result = client.run_experiment(
        experiment_id=exp_id,
        steps_data=steps_data,
        user_id="complete_example"
    )

    print("\n📊 实验结果:")
    print(f"   记录ID: {result['record_id']}")
    print(f"   得分: {result['final_score']}")


def example_batch_processing():
    """批量处理示例"""
    print("\n" + "="*60)
    print("示例3: 批量处理多个用户")
    print("="*60 + "\n")

    client = VirtualChemLabClient("http://localhost:8080")

    # 获取实验
    experiments = client.list_experiments()
    if not experiments:
        print("⚠️  没有可用的实验")
        return

    exp_id = experiments[0]['id']

    # 模拟多个用户完成实验
    users = ["student_001", "student_002", "student_003"]
    results = []

    for user_id in users:
        print(f"处理用户: {user_id}...")

        # 开始实验
        client.start_experiment(exp_id, user_id)

        # 自动完成(使用正确答案)
        client.submit_step({"confirmed": True})

        # 完成实验
        result = client.finish_experiment()
        results.append({
            "user_id": user_id,
            "score": result['final_score']
        })

        print(f"   得分: {result['final_score']}")

    # 统计
    print("\n📊 批量处理统计:")
    avg_score = sum(r['score'] for r in results) / len(results)
    print(f"   处理用户数: {len(results)}")
    print(f"   平均分: {avg_score:.2f}")


def example_record_management():
    """记录管理示例"""
    print("\n" + "="*60)
    print("示例4: 记录管理")
    print("="*60 + "\n")

    client = VirtualChemLabClient("http://localhost:8080")

    # 1. 列出所有记录
    print("1️⃣ 列出所有记录...")
    all_records = client.list_records()
    print(f"   总记录数: {len(all_records)}")

    # 2. 按用户查询
    print("\n2️⃣ 查询特定用户记录...")
    user_records = client.list_records(user_id="example_user")
    print(f"   用户记录数: {len(user_records)}")

    # 3. 查看记录详情
    if all_records:
        record_id = all_records[0]['id']
        print(f"\n3️⃣ 查看记录详情: {record_id}")
        record = client.get_record(record_id)
        print(f"   用户: {record['user_id']}")
        print(f"   实验: {record['experiment_id']}")
        print(f"   得分: {record['final_score']}")
        print(f"   步骤数: {len(record['step_records'])}")
        print(f"   错误数: {len(record['mistakes'])}")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "="*60)
    print("示例5: 错误处理")
    print("="*60 + "\n")

    client = VirtualChemLabClient("http://localhost:8080")

    # 1. 处理不存在的实验
    print("1️⃣ 尝试加载不存在的实验...")
    try:
        client.get_experiment("invalid_experiment_id")
    except Exception as e:
        print(f"   ❌ 捕获错误: {e}")

    # 2. 处理无效的会话
    print("\n2️⃣ 尝试使用无效会话...")
    client.session_id = "invalid_session"
    try:
        client.submit_step({"confirmed": True})
    except Exception as e:
        print(f"   ❌ 捕获错误: {e}")

    # 3. 处理网络错误
    print("\n3️⃣ 尝试连接错误的服务器...")
    bad_client = VirtualChemLabClient("http://localhost:9999")
    try:
        bad_client.health_check()
    except Exception as e:
        print(f"   ❌ 捕获错误: {type(e).__name__}")


def example_custom_integration():
    """自定义集成示例(如LMS系统)"""
    print("\n" + "="*60)
    print("示例6: LMS系统集成")
    print("="*60 + "\n")

    class MyLMSIntegration:
        """模拟LMS系统集成"""

        def __init__(self, api_url: str):
            self.client = VirtualChemLabClient(api_url)
            self.lms_assignments = {}

        def create_assignment(self, course_id: str, experiment_id: str):
            """创建作业"""
            assignment_id = f"assignment_{course_id}_{experiment_id}"

            # 获取实验信息
            experiment = self.client.get_experiment(experiment_id)

            self.lms_assignments[assignment_id] = {
                "course_id": course_id,
                "experiment_id": experiment_id,
                "title": experiment['title'],
                "duration_minutes": experiment['duration_minutes'],
                "submissions": []
            }

            print(f"✅ 创建作业: {assignment_id}")
            print(f"   实验: {experiment['title']}")
            print(f"   预计时长: {experiment['duration_minutes']}分钟")

            return assignment_id

        def submit_assignment(self, assignment_id: str, student_id: str):
            """学生提交作业"""
            if assignment_id not in self.lms_assignments:
                raise ValueError(f"作业不存在: {assignment_id}")

            assignment = self.lms_assignments[assignment_id]
            exp_id = assignment['experiment_id']

            # 开始实验
            self.client.start_experiment(exp_id, student_id)

            print(f"📝 学生 {student_id} 开始作业...")

            # 这里应该是实际的学生操作
            # 为了演示,我们自动完成
            self.client.submit_step({"confirmed": True})
            result = self.client.finish_experiment()

            # 记录提交
            submission = {
                "student_id": student_id,
                "record_id": result['record_id'],
                "score": result['final_score'],
                "submitted_at": "2025-10-06T10:30:00"
            }

            assignment['submissions'].append(submission)

            print(f"   ✅ 提交成功! 得分: {result['final_score']}")

            return submission

        def get_assignment_stats(self, assignment_id: str):
            """获取作业统计"""
            if assignment_id not in self.lms_assignments:
                raise ValueError(f"作业不存在: {assignment_id}")

            assignment = self.lms_assignments[assignment_id]
            submissions = assignment['submissions']

            if not submissions:
                return {"submissions": 0, "avg_score": 0}

            avg_score = sum(s['score'] for s in submissions) / len(submissions)

            return {
                "title": assignment['title'],
                "submissions": len(submissions),
                "avg_score": avg_score,
                "max_score": max(s['score'] for s in submissions),
                "min_score": min(s['score'] for s in submissions)
            }

    # 使用示例
    lms = MyLMSIntegration("http://localhost:8080")

    # 创建作业
    experiments = lms.client.list_experiments()
    if experiments:
        assignment_id = lms.create_assignment("CHEM101", experiments[0]['id'])

        # 学生提交
        lms.submit_assignment(assignment_id, "student_001")
        lms.submit_assignment(assignment_id, "student_002")

        # 统计
        stats = lms.get_assignment_stats(assignment_id)
        print("\n📊 作业统计:")
        print(f"   作业: {stats['title']}")
        print(f"   提交数: {stats['submissions']}")
        print(f"   平均分: {stats['avg_score']:.2f}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab API集成示例")
    parser.add_argument('--example', type=int, choices=range(1, 7),
                       help='运行特定示例(1-6)')
    parser.add_argument('--all', action='store_true', help='运行所有示例')

    args = parser.parse_args()

    examples = {
        1: example_basic_usage,
        2: example_complete_experiment,
        3: example_batch_processing,
        4: example_record_management,
        5: example_error_handling,
        6: example_custom_integration
    }

    print("""
╔═══════════════════════════════════════════════════════════╗
║     VirtualChemLab API 集成示例                          ║
╚═══════════════════════════════════════════════════════════╝

请确保API服务器正在运行:
  python start_api_server.py

或使用模拟数据运行示例。
    """)

    try:
        if args.all:
            for i in range(1, 7):
                examples[i]()
        elif args.example:
            examples[args.example]()
        else:
            # 默认运行示例1
            example_basic_usage()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n💡 提示: 确保API服务器正在运行!")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()



