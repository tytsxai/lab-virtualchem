#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VirtualChemLab 教师控制台
用于管理学生实验、查看记录和生成报告
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.user_record import UserRecord  # noqa: E402
from src.storage.json_store import JSONStore  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger("teacher_console")


class TeacherConsole:
    """教师控制台主类"""
    
    def __init__(self, data_dir: Path = None):
        """
        初始化教师控制台
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir or PROJECT_ROOT / "data"
        self.records_dir = self.data_dir / "records"
        self.reports_dir = self.data_dir / "reports"
        
        # 创建必要的目录
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化存储
        self.store = JSONStore(str(self.records_dir))
        
        logger.info(f"教师控制台初始化完成，数据目录: {self.data_dir}")
    
    def list_students(self):
        """列出所有学生"""
        print("\n" + "=" * 80)
        print("📚 学生列表")
        print("=" * 80)
        
        user_dirs = [d for d in self.records_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        if not user_dirs:
            print("暂无学生记录")
            return
        
        print(f"\n找到 {len(user_dirs)} 个学生:\n")
        print(f"{'学生ID':<20} {'实验数量':<12} {'最近活动':<20}")
        print("-" * 80)
        
        for user_dir in sorted(user_dirs):
            user_id = user_dir.name
            records = self.store.list_records(user_id)
            
            # 找最近的活动时间
            latest_time = None
            if records:
                for record in records:
                    if isinstance(record, dict):
                        started_at = record.get('started_at')
                        if started_at:
                            if isinstance(started_at, str):
                                try:
                                    record_time = datetime.fromisoformat(started_at)
                                    if latest_time is None or record_time > latest_time:
                                        latest_time = record_time
                                except:
                                    pass
            
            latest_str = latest_time.strftime("%Y-%m-%d %H:%M") if latest_time else "未知"
            print(f"{user_id:<20} {len(records):<12} {latest_str:<20}")
        
        print()
    
    def show_student_details(self, user_id: str):
        """显示学生详细信息"""
        print("\n" + "=" * 80)
        print(f"👤 学生详细信息: {user_id}")
        print("=" * 80)
        
        records = self.store.list_records(user_id)
        
        if not records:
            print("该学生暂无实验记录")
            return
        
        print(f"\n实验记录总数: {len(records)}\n")
        print(f"{'实验ID':<30} {'状态':<12} {'得分':<8} {'完成时间':<20}")
        print("-" * 80)
        
        completed_count = 0
        total_score = 0
        
        for record_data in records:
            if isinstance(record_data, dict):
                exp_id = record_data.get('experiment_id', 'N/A')
                status = record_data.get('status', 'N/A')
                score_data = record_data.get('score', {})
                
                if isinstance(score_data, dict):
                    score = score_data.get('score', 0)
                else:
                    score = 0
                
                completed_at = record_data.get('completed_at', 'N/A')
                if completed_at and completed_at != 'N/A':
                    try:
                        completed_dt = datetime.fromisoformat(completed_at)
                        completed_str = completed_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        completed_str = str(completed_at)[:20]
                else:
                    completed_str = "-"
                
                print(f"{exp_id:<30} {status:<12} {score:<8.1f} {completed_str:<20}")
                
                if status == "completed":
                    completed_count += 1
                    total_score += score
        
        print()
        print(f"完成实验数: {completed_count}/{len(records)}")
        if completed_count > 0:
            avg_score = total_score / completed_count
            print(f"平均得分: {avg_score:.1f}")
        print()
    
    def show_experiment_stats(self, experiment_id: str = None):
        """显示实验统计信息"""
        print("\n" + "=" * 80)
        if experiment_id:
            print(f"📊 实验统计: {experiment_id}")
        else:
            print("📊 所有实验统计")
        print("=" * 80 + "\n")
        
        # 收集所有记录
        all_records = []
        user_dirs = [d for d in self.records_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        for user_dir in user_dirs:
            user_id = user_dir.name
            records = self.store.list_records(user_id)
            
            for record_data in records:
                if isinstance(record_data, dict):
                    if experiment_id is None or record_data.get('experiment_id') == experiment_id:
                        all_records.append(record_data)
        
        if not all_records:
            print("暂无相关实验记录")
            return
        
        # 统计数据
        total_attempts = len(all_records)
        completed_count = sum(1 for r in all_records if r.get('status') == 'completed')
        in_progress_count = sum(1 for r in all_records if r.get('status') == 'in_progress')
        abandoned_count = sum(1 for r in all_records if r.get('status') == 'abandoned')
        
        # 分数统计
        completed_records = [r for r in all_records if r.get('status') == 'completed']
        if completed_records:
            scores = []
            for r in completed_records:
                score_data = r.get('score', {})
                if isinstance(score_data, dict):
                    scores.append(score_data.get('score', 0))
            
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                
                print(f"总尝试次数: {total_attempts}")
                print(f"  - 已完成: {completed_count}")
                print(f"  - 进行中: {in_progress_count}")
                print(f"  - 已放弃: {abandoned_count}")
                print()
                print(f"完成率: {completed_count/total_attempts*100:.1f}%")
                print()
                print(f"得分统计 (基于 {len(scores)} 个完成记录):")
                print(f"  - 平均分: {avg_score:.1f}")
                print(f"  - 最高分: {max_score:.1f}")
                print(f"  - 最低分: {min_score:.1f}")
        else:
            print(f"总尝试次数: {total_attempts}")
            print(f"  - 已完成: {completed_count}")
            print(f"  - 进行中: {in_progress_count}")
            print(f"  - 已放弃: {abandoned_count}")
            print()
            print("暂无完成的实验记录")
        
        print()
    
    def export_report(self, output_file: str = None, format: str = "json"):
        """导出报告"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.reports_dir / f"report_{timestamp}.{format}"
        else:
            output_file = Path(output_file)
        
        print(f"\n正在生成报告...")
        
        # 收集所有数据
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "students": []
        }
        
        user_dirs = [d for d in self.records_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        for user_dir in sorted(user_dirs):
            user_id = user_dir.name
            records = self.store.list_records(user_id)
            
            student_data = {
                "user_id": user_id,
                "total_experiments": len(records),
                "completed_experiments": sum(1 for r in records if isinstance(r, dict) and r.get('status') == 'completed'),
                "records": records
            }
            
            report_data["students"].append(student_data)
        
        # 保存报告
        if format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            # 简单的CSV格式
            import csv
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["学生ID", "实验总数", "完成数", "完成率"])
                
                for student in report_data["students"]:
                    total = student["total_experiments"]
                    completed = student["completed_experiments"]
                    rate = f"{completed/total*100:.1f}%" if total > 0 else "0%"
                    writer.writerow([student["user_id"], total, completed, rate])
        
        print(f"✅ 报告已导出到: {output_file}")
        print()
    
    def show_recent_activity(self, days: int = 7):
        """显示最近活动"""
        print("\n" + "=" * 80)
        print(f"📅 最近 {days} 天的活动")
        print("=" * 80 + "\n")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_activities = []
        
        user_dirs = [d for d in self.records_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        for user_dir in user_dirs:
            user_id = user_dir.name
            records = self.store.list_records(user_id)
            
            for record_data in records:
                if isinstance(record_data, dict):
                    started_at = record_data.get('started_at')
                    if started_at:
                        try:
                            if isinstance(started_at, str):
                                record_time = datetime.fromisoformat(started_at)
                            else:
                                record_time = started_at
                            
                            if record_time >= cutoff_date:
                                recent_activities.append({
                                    "user_id": user_id,
                                    "experiment_id": record_data.get('experiment_id', 'N/A'),
                                    "status": record_data.get('status', 'N/A'),
                                    "started_at": record_time
                                })
                        except Exception as e:
                            logger.warning(f"解析时间失败: {e}")
        
        if not recent_activities:
            print("最近没有活动记录")
            return
        
        # 按时间排序
        recent_activities.sort(key=lambda x: x['started_at'], reverse=True)
        
        print(f"{'时间':<20} {'学生ID':<20} {'实验ID':<30} {'状态':<12}")
        print("-" * 80)
        
        for activity in recent_activities[:50]:  # 最多显示50条
            time_str = activity['started_at'].strftime("%Y-%m-%d %H:%M")
            print(f"{time_str:<20} {activity['user_id']:<20} {activity['experiment_id']:<30} {activity['status']:<12}")
        
        if len(recent_activities) > 50:
            print(f"\n(还有 {len(recent_activities) - 50} 条记录未显示)")
        
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VirtualChemLab 教师控制台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有学生
  python teacher_console.py list
  
  # 查看学生详细信息
  python teacher_console.py student <user_id>
  
  # 查看实验统计
  python teacher_console.py stats [experiment_id]
  
  # 导出报告
  python teacher_console.py export --format json
  
  # 查看最近活动
  python teacher_console.py activity --days 7
        """
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="数据目录路径 (默认: data)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # list命令
    subparsers.add_parser("list", help="列出所有学生")
    
    # student命令
    student_parser = subparsers.add_parser("student", help="查看学生详细信息")
    student_parser.add_argument("user_id", help="学生ID")
    
    # stats命令
    stats_parser = subparsers.add_parser("stats", help="查看实验统计")
    stats_parser.add_argument("experiment_id", nargs="?", help="实验ID (可选)")
    
    # export命令
    export_parser = subparsers.add_parser("export", help="导出报告")
    export_parser.add_argument("--output", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="输出格式")
    
    # activity命令
    activity_parser = subparsers.add_parser("activity", help="查看最近活动")
    activity_parser.add_argument("--days", type=int, default=7, help="天数 (默认: 7)")
    
    args = parser.parse_args()
    
    # 创建控制台实例
    data_dir = Path(args.data_dir) if args.data_dir else None
    console = TeacherConsole(data_dir)
    
    # 执行命令
    if args.command == "list":
        console.list_students()
    elif args.command == "student":
        console.show_student_details(args.user_id)
    elif args.command == "stats":
        console.show_experiment_stats(args.experiment_id)
    elif args.command == "export":
        console.export_report(args.output, args.format)
    elif args.command == "activity":
        console.show_recent_activity(args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序错误: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

