"""
HTML报告生成器
将实验记录转换为HTML报告
"""

from datetime import datetime

from jinja2 import Template

from ..models.experiment import ExperimentTemplate
from ..models.user_record import UserRecord
from ..utils.i18n import I18n
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HTMLGenerator:
    """HTML报告生成器"""

    def __init__(self):
        self.i18n = I18n()
        self.template_html = self._get_default_template()

    def _get_default_template(self) -> str:
        """获取默认HTML模板"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - 实验报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }

        .header {
            text-align: center;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: #7f8c8d;
            font-size: 14px;
        }

        .info-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }

        .info-item {
            display: flex;
        }

        .info-label {
            font-weight: bold;
            color: #555;
            min-width: 100px;
        }

        .info-value {
            color: #333;
        }

        .score-box {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 30px;
        }

        .score-box h2 {
            font-size: 18px;
            margin-bottom: 10px;
        }

        .score-box .score {
            font-size: 48px;
            font-weight: bold;
        }

        .steps-section {
            margin-bottom: 30px;
        }

        .section-title {
            color: #2c3e50;
            border-left: 4px solid #4CAF50;
            padding-left: 15px;
            margin-bottom: 20px;
            font-size: 20px;
        }

        .step-card {
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 15px;
        }

        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .step-title {
            font-weight: bold;
            color: #2c3e50;
        }

        .step-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        .status-pass {
            background-color: #d4edda;
            color: #155724;
        }

        .status-fail {
            background-color: #f8d7da;
            color: #721c24;
        }

        .step-details {
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }

        .mistakes {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px 15px;
            margin-top: 10px;
        }

        .mistakes-title {
            font-weight: bold;
            color: #856404;
            margin-bottom: 5px;
        }

        .mistake-item {
            color: #856404;
            margin-left: 20px;
        }

        .summary {
            background-color: #e3f2fd;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            text-align: center;
        }

        .summary-item {
            background: white;
            padding: 15px;
            border-radius: 5px;
        }

        .summary-value {
            font-size: 32px;
            font-weight: bold;
            color: #1976d2;
        }

        .summary-label {
            color: #666;
            margin-top: 5px;
        }

        .footer {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }

        @media print {
            body {
                background: white;
                padding: 0;
            }

            .container {
                box-shadow: none;
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>{{ title }}</h1>
            <p class="subtitle">{{ description }}</p>
        </div>

        <!-- 基本信息 -->
        <div class="info-section">
            <div class="info-item">
                <span class="info-label">实验ID:</span>
                <span class="info-value">{{ experiment_id }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">学生ID:</span>
                <span class="info-value">{{ user_id }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">开始时间:</span>
                <span class="info-value">{{ start_time }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">结束时间:</span>
                <span class="info-value">{{ end_time }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">用时:</span>
                <span class="info-value">{{ duration }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">难度:</span>
                <span class="info-value">{{ difficulty }}</span>
            </div>
        </div>

        <!-- 最终得分 -->
        <div class="score-box">
            <h2>最终得分</h2>
            <div class="score">{{ final_score }}</div>
        </div>

        <!-- 实验摘要 -->
        <div class="summary">
            <h2 class="section-title">实验摘要</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{{ total_steps }}</div>
                    <div class="summary-label">总步骤数</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{{ passed_steps }}</div>
                    <div class="summary-label">通过步骤</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{{ total_mistakes }}</div>
                    <div class="summary-label">总错误数</div>
                </div>
            </div>
        </div>

        <!-- 步骤详情 -->
        <div class="steps-section">
            <h2 class="section-title">步骤详情</h2>
            {% for step in steps %}
            <div class="step-card">
                <div class="step-header">
                    <span class="step-title">{{ step.title }}</span>
                    <span class="step-status {{ 'status-pass' if step.passed else 'status-fail' }}">
                        {{ '通过' if step.passed else '失败' }}
                    </span>
                </div>
                <div class="step-details">
                    <p><strong>操作:</strong> {{ step.instruction }}</p>
                    <p><strong>得分:</strong> {{ step.score }}</p>
                    {% if step.attempts > 1 %}
                    <p><strong>尝试次数:</strong> {{ step.attempts }}</p>
                    {% endif %}
                </div>
                {% if step.mistakes %}
                <div class="mistakes">
                    <div class="mistakes-title">错误记录:</div>
                    {% for mistake in step.mistakes %}
                    <div class="mistake-item">• {{ mistake }}</div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <p>VirtualChemLab - 虚拟化学实验室</p>
            <p>报告生成时间: {{ report_time }}</p>
        </div>
    </div>
</body>
</html>
        """

    def generate(self, record: UserRecord, template: ExperimentTemplate, output_path: str | None = None) -> str:
        """
        生成HTML报告

        Args:
            record: 实验记录
            template: 实验模板
            output_path: 输出路径(可选,不提供则返回HTML字符串)

        Returns:
            HTML字符串
        """
        try:
            # 准备数据
            context = self._prepare_context(record, template)

            # 渲染模板
            jinja_template = Template(self.template_html)
            html_content = jinja_template.render(**context)

            # 保存到文件
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"HTML报告已生成: {output_path}")

            return html_content

        except Exception as e:
            logger.error(f"生成HTML报告失败: {e}")
            raise

    def _prepare_context(self, record: UserRecord, template: ExperimentTemplate) -> dict:
        """准备模板上下文"""
        # 计算统计数据
        total_steps = len(record.step_records)
        passed_steps = sum(1 for sr in record.step_records if sr.passed)
        total_mistakes = sum(len(sr.mistakes) for sr in record.step_records)

        # 计算用时
        duration = ""
        if record.start_time and record.end_time:
            delta = record.end_time - record.start_time
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            duration = f"{minutes}分{seconds}秒"

        # 格式化时间
        def format_time(dt: datetime | None) -> str:
            if dt:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return "N/A"

        # 准备步骤数据
        steps_data = []
        for sr in record.step_records:
            # 查找对应的步骤模板
            step_template = next((s for s in template.steps if s.id == sr.step_id), None)

            step_info = {
                "title": step_template.title if step_template else sr.step_id,
                "instruction": step_template.instruction if step_template else "",
                "passed": sr.passed,
                "score": sr.score or 0,
                "attempts": sr.attempts,
                "mistakes": [m.description for m in sr.mistakes],
            }
            steps_data.append(step_info)

        return {
            "title": template.title,
            "description": template.description,
            "experiment_id": record.experiment_id,
            "user_id": record.user_id,
            "start_time": format_time(record.start_time),
            "end_time": format_time(record.end_time),
            "duration": duration,
            "difficulty": self.i18n.t(f"difficulty.{template.difficulty}"),
            "final_score": record.final_score or 0,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "total_mistakes": total_mistakes,
            "steps": steps_data,
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
