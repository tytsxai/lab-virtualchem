"""
实验数据分析工具

提供实验数据的统计分析、可视化、报告生成等功能
"""

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class ExperimentStats:
    """实验统计数据"""
    experiment_id: str
    total_attempts: int
    avg_score: float
    avg_duration: float
    completion_rate: float
    common_mistakes: list[tuple[str, int]]
    difficulty_rating: float


@dataclass
class UserAnalytics:
    """用户分析数据"""
    user_id: str
    total_experiments: int
    avg_score: float
    total_time_spent: float
    improvement_trend: float
    strengths: list[str]
    weaknesses: list[str]


class ExperimentDataAnalyzer:
    """实验数据分析器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.records: list[dict[str, Any]] = []
        self._load_records()

    def _load_records(self):
        """加载所有实验记录"""
        records_dir = self.data_dir / 'records'

        if not records_dir.exists():
            return

        # 遍历所有用户目录
        for user_dir in records_dir.iterdir():
            if not user_dir.is_dir():
                continue

            # 加载用户的所有记录
            for record_file in user_dir.glob('*.json'):
                try:
                    data = json.loads(record_file.read_text(encoding='utf-8'))
                    self.records.append(data)
                except Exception as e:
                    print(f"加载记录失败 {record_file}: {e}")

    def analyze_experiment(self, experiment_id: str) -> ExperimentStats | None:
        """分析特定实验"""
        # 筛选该实验的记录
        exp_records = [r for r in self.records if r.get('experiment_id') == experiment_id]

        if not exp_records:
            return None

        # 统计数据
        total_attempts = len(exp_records)
        scores = [r.get('score', {}).get('total', 0) for r in exp_records]
        avg_score = statistics.mean(scores) if scores else 0

        # 计算平均时长
        durations = []
        for r in exp_records:
            start = datetime.fromisoformat(r.get('started_at', ''))
            end = datetime.fromisoformat(r.get('completed_at', ''))
            durations.append((end - start).total_seconds())

        avg_duration = statistics.mean(durations) if durations else 0

        # 完成率 (假设分数>60为完成)
        completed = len([s for s in scores if s >= 60])
        completion_rate = (completed / total_attempts * 100) if total_attempts > 0 else 0

        # 常见错误
        all_mistakes = []
        for r in exp_records:
            mistakes = r.get('mistakes_summary', [])
            for mistake in mistakes:
                all_mistakes.append(mistake.get('checkpoint_id', 'unknown'))

        mistake_counter = Counter(all_mistakes)
        common_mistakes = mistake_counter.most_common(5)

        # 难度评分 (基于平均分和完成率)
        difficulty_rating = 100 - (avg_score * 0.6 + completion_rate * 0.4)

        return ExperimentStats(
            experiment_id=experiment_id,
            total_attempts=total_attempts,
            avg_score=avg_score,
            avg_duration=avg_duration,
            completion_rate=completion_rate,
            common_mistakes=common_mistakes,
            difficulty_rating=difficulty_rating
        )

    def analyze_user(self, user_id: str) -> UserAnalytics | None:
        """分析特定用户"""
        user_records = [r for r in self.records if r.get('user_id') == user_id]

        if not user_records:
            return None

        # 基本统计
        total_experiments = len(user_records)
        scores = [r.get('score', {}).get('total', 0) for r in user_records]
        avg_score = statistics.mean(scores) if scores else 0

        # 总用时
        total_time = 0
        for r in user_records:
            start = datetime.fromisoformat(r.get('started_at', ''))
            end = datetime.fromisoformat(r.get('completed_at', ''))
            total_time += (end - start).total_seconds()

        # 进步趋势 (比较前后分数)
        improvement_trend = 0
        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            improvement_trend = statistics.mean(second_half) - statistics.mean(first_half)

        # 强项和弱项分析
        experiment_scores = defaultdict(list)
        for r in user_records:
            exp_id = r.get('experiment_id', 'unknown')
            score = r.get('score', {}).get('total', 0)
            experiment_scores[exp_id].append(score)

        avg_by_experiment = {
            exp_id: statistics.mean(scores)
            for exp_id, scores in experiment_scores.items()
        }

        sorted_exps = sorted(avg_by_experiment.items(), key=lambda x: x[1], reverse=True)
        strengths = [exp_id for exp_id, _ in sorted_exps[:3]]
        weaknesses = [exp_id for exp_id, _ in sorted_exps[-3:]]

        return UserAnalytics(
            user_id=user_id,
            total_experiments=total_experiments,
            avg_score=avg_score,
            total_time_spent=total_time,
            improvement_trend=improvement_trend,
            strengths=strengths,
            weaknesses=weaknesses
        )

    def get_trending_experiments(self, days: int = 7) -> list[tuple[str, int]]:
        """获取最近N天的热门实验"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_records = [
            r for r in self.records
            if datetime.fromisoformat(r.get('started_at', '')) >= cutoff_date
        ]

        experiment_counts = Counter([r.get('experiment_id') for r in recent_records])

        return experiment_counts.most_common(10)

    def get_performance_trends(self, days: int = 30) -> dict[str, list[float]]:
        """获取性能趋势"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # 按日期分组
        daily_scores = defaultdict(list)

        for r in self.records:
            started_at = datetime.fromisoformat(r.get('started_at', ''))
            if started_at >= cutoff_date:
                date_key = started_at.strftime('%Y-%m-%d')
                score = r.get('score', {}).get('total', 0)
                daily_scores[date_key].append(score)

        # 计算每日平均分
        trends = {}
        for date, scores in sorted(daily_scores.items()):
            trends[date] = statistics.mean(scores) if scores else 0

        return trends

    def identify_problem_areas(self) -> list[dict[str, Any]]:
        """识别问题区域"""
        problem_areas = []

        # 分析每个检查点的错误率
        checkpoint_errors = defaultdict(int)
        checkpoint_total = defaultdict(int)

        for r in self.records:
            mistakes = r.get('mistakes_summary', [])

            # 统计所有检查点
            for step in r.get('steps', []):
                checkpoint_id = step.get('checkpoint_id', '')
                if checkpoint_id:
                    checkpoint_total[checkpoint_id] += 1

            # 统计错误
            for mistake in mistakes:
                checkpoint_id = mistake.get('checkpoint_id', '')
                if checkpoint_id:
                    checkpoint_errors[checkpoint_id] += 1

        # 计算错误率
        for checkpoint_id in checkpoint_total:
            error_count = checkpoint_errors.get(checkpoint_id, 0)
            total_count = checkpoint_total[checkpoint_id]
            error_rate = (error_count / total_count * 100) if total_count > 0 else 0

            if error_rate > 30:  # 错误率超过30%
                problem_areas.append({
                    'checkpoint_id': checkpoint_id,
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'total_count': total_count
                })

        return sorted(problem_areas, key=lambda x: x['error_rate'], reverse=True)


class AnalyticsReportGenerator:
    """分析报告生成器"""

    @staticmethod
    def generate_experiment_report(stats: ExperimentStats, output_path: Path):
        """生成实验分析报告"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{stats.experiment_id} 实验分析报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #2c3e50; margin-bottom: 30px; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .difficulty {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .difficulty-bar {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #f39c12, #e74c3c);
            transition: width 0.5s ease;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #667eea;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {stats.experiment_id} 实验分析报告</h1>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">尝试次数</div>
                <div class="metric-value">{stats.total_attempts}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均分数</div>
                <div class="metric-value">{stats.avg_score:.1f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均时长</div>
                <div class="metric-value">{stats.avg_duration/60:.1f}<span style="font-size: 0.5em;">分钟</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">完成率</div>
                <div class="metric-value">{stats.completion_rate:.1f}%</div>
            </div>
        </div>

        <h2>难度评估</h2>
        <div class="difficulty">
            <div class="difficulty-bar" style="width: {stats.difficulty_rating}%"></div>
        </div>
        <p style="text-align: center; color: #7f8c8d;">
            难度指数: {stats.difficulty_rating:.1f}/100
        </p>

        <h2>常见错误</h2>
        <table>
            <tr>
                <th>检查点ID</th>
                <th>错误次数</th>
            </tr>
"""

        for checkpoint_id, count in stats.common_mistakes:
            html += f"""
            <tr>
                <td>{checkpoint_id}</td>
                <td>{count}</td>
            </tr>
"""

        html += """
        </table>

        <p style="margin-top: 30px; color: #7f8c8d; text-align: center;">
            生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </p>
    </div>
</body>
</html>"""

        output_path.write_text(html, encoding='utf-8')
        print(f"已生成实验报告: {output_path}")

    @staticmethod
    def generate_user_report(analytics: UserAnalytics, output_path: Path):
        """生成用户分析报告"""
        trend_emoji = "📈" if analytics.improvement_trend > 0 else "📉" if analytics.improvement_trend < 0 else "➡️"
        trend_text = "进步中" if analytics.improvement_trend > 0 else "退步中" if analytics.improvement_trend < 0 else "稳定"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{analytics.user_id} 学习分析报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #2c3e50; }}
        .summary {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .stat {{
            display: inline-block;
            margin: 15px 30px;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .trend {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .skill-list {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .skill-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .skill-card h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .skill-item {{
            padding: 8px;
            margin: 5px 0;
            background: white;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>👤 {analytics.user_id} 学习分析报告</h1>

        <div class="summary">
            <div class="stat">
                <div class="stat-label">完成实验数</div>
                <div class="stat-value">{analytics.total_experiments}</div>
            </div>
            <div class="stat">
                <div class="stat-label">平均分数</div>
                <div class="stat-value">{analytics.avg_score:.1f}</div>
            </div>
            <div class="stat">
                <div class="stat-label">总学习时长</div>
                <div class="stat-value">{analytics.total_time_spent/3600:.1f}<span style="font-size: 0.6em;">小时</span></div>
            </div>
        </div>

        <div class="trend">
            <h2>{trend_emoji} 学习趋势: {trend_text}</h2>
            <p style="font-size: 1.2em;">分数变化: {analytics.improvement_trend:+.1f}分</p>
        </div>

        <div class="skill-list">
            <div class="skill-card">
                <h3>💪 优势实验</h3>
"""

        for exp in analytics.strengths:
            html += f'                <div class="skill-item">✅ {exp}</div>\n'

        html += """
            </div>
            <div class="skill-card">
                <h3>📚 需要加强</h3>
"""

        for exp in analytics.weaknesses:
            html += f'                <div class="skill-item">🔄 {exp}</div>\n'

        html += """
            </div>
        </div>

        <p style="margin-top: 30px; color: #7f8c8d; text-align: center;">
            生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </p>
    </div>
</body>
</html>"""

        output_path.write_text(html, encoding='utf-8')
        print(f"已生成用户报告: {output_path}")


# 使用示例
if __name__ == '__main__':
    data_dir = Path('data')

    # 创建分析器
    analyzer = ExperimentDataAnalyzer(data_dir)

    print(f"已加载 {len(analyzer.records)} 条实验记录\n")

    # 分析热门实验
    print("=== 热门实验 (最近7天) ===")
    trending = analyzer.get_trending_experiments(days=7)
    for exp_id, count in trending:
        print(f"{exp_id}: {count}次")

    # 分析特定实验
    if trending:
        exp_id = trending[0][0]
        print(f"\n=== 分析实验: {exp_id} ===")
        stats = analyzer.analyze_experiment(exp_id)

        if stats:
            print(f"尝试次数: {stats.total_attempts}")
            print(f"平均分数: {stats.avg_score:.2f}")
            print(f"平均时长: {stats.avg_duration/60:.2f}分钟")
            print(f"完成率: {stats.completion_rate:.2f}%")
            print(f"难度指数: {stats.difficulty_rating:.2f}/100")

            # 生成报告
            AnalyticsReportGenerator.generate_experiment_report(
                stats,
                Path(f'experiment_report_{exp_id}.html')
            )

    # 识别问题区域
    print("\n=== 问题区域识别 ===")
    problems = analyzer.identify_problem_areas()
    for problem in problems[:5]:
        print(f"{problem['checkpoint_id']}: 错误率 {problem['error_rate']:.1f}% ({problem['error_count']}/{problem['total_count']})")

    # 性能趋势
    print("\n=== 性能趋势 (最近7天) ===")
    trends = analyzer.get_performance_trends(days=7)
    for date, avg_score in list(trends.items())[-7:]:
        print(f"{date}: {avg_score:.2f}分")


