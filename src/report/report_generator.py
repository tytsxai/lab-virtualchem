"""
实验报告生成器
支持HTML和PDF格式导出
"""

import logging
from datetime import datetime
from pathlib import Path

from src.models.user_record import UserRecord
from src.utils.i18n import I18n

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器类"""

    def __init__(self, i18n_dir: str = "assets/i18n"):
        """
        初始化报告生成器

        Args:
            i18n_dir: 国际化文件目录
        """
        self.i18n = I18n(i18n_dir)

    def generate_html_report(self, record: UserRecord, output_path: str | None = None) -> str:
        """
        生成HTML格式报告

        Args:
            record: 用户记录
            output_path: 输出文件路径（可选）

        Returns:
            生成的HTML内容或文件路径
        """
        html_content = self._build_html(record)

        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(html_content, encoding="utf-8")
                logger.info(f"HTML报告已生成: {output_path}")
                return str(output_file)
            except Exception as e:
                logger.error(f"保存HTML报告失败: {e}")
                raise
        else:
            return html_content

    def generate_pdf_report(self, record: UserRecord, output_path: str) -> str:
        """
        生成PDF格式报告

        Args:
            record: 用户记录
            output_path: 输出文件路径

        Returns:
            生成的PDF文件路径
        """
        try:
            from weasyprint import HTML
        except ImportError as e:
            logger.error("未安装weasyprint，无法生成PDF。请运行: pip install weasyprint")
            raise ImportError("需要安装weasyprint才能生成PDF报告。请运行: pip install weasyprint") from e

        html_content = self._build_html(record)

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            HTML(string=html_content).write_pdf(str(output_file))
            logger.info(f"PDF报告已生成: {output_path}")
            return str(output_file)
        except Exception as e:
            logger.error(f"生成PDF报告失败: {e}")
            raise

    def _build_html(self, record: UserRecord) -> str:
        """
        构建HTML内容

        Args:
            record: 用户记录

        Returns:
            HTML内容字符串
        """
        # 基本样式
        self._get_styles()

        # 构建HTML各部分
        self._build_header(record)
        self._build_summary(record)
        self._build_step_details(record)
        self._build_mistakes(record)
        self._build_footer()

        html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.i18n.t('report.title')} - {record.experiment_title}</title>
    <style>{styles}</style>
</head>
<body>
    {header}
    {summary}
    {step_details}
    {mistakes}
    {footer}
</body>
</html>
"""
        return html

    def _get_styles(self) -> str:
        """获取CSS样式"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }

        .header {
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #2c3e50;
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: #7f8c8d;
            font-size: 18px;
        }

        .section {
            margin-bottom: 30px;
        }

        .section-title {
            color: #2c3e50;
            font-size: 24px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }

        .info-item {
            padding: 15px;
            background: #ecf0f1;
            border-radius: 5px;
        }

        .info-label {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 5px;
        }

        .info-value {
            color: #2c3e50;
            font-size: 18px;
            font-weight: 600;
        }

        .score-box {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin: 20px 0;
        }

        .score-box .label {
            font-size: 18px;
            opacity: 0.9;
        }

        .score-box .value {
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }

        .step-list {
            list-style: none;
        }

        .step-item {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 4px solid #95a5a6;
        }

        .step-item.passed {
            border-left-color: #27ae60;
        }

        .step-item.failed {
            border-left-color: #e74c3c;
        }

        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .step-title {
            font-weight: 600;
            color: #2c3e50;
        }

        .step-score {
            font-weight: bold;
        }

        .step-score.passed {
            color: #27ae60;
        }

        .step-score.failed {
            color: #e74c3c;
        }

        .step-content {
            color: #555;
            font-size: 14px;
        }

        .mistake-item {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 12px;
            margin-bottom: 10px;
        }

        .mistake-item.severe {
            background: #f8d7da;
            border-color: #dc3545;
        }

        .mistake-header {
            font-weight: 600;
            color: #856404;
            margin-bottom: 5px;
        }

        .mistake-item.severe .mistake-header {
            color: #721c24;
        }

        .no-mistakes {
            text-align: center;
            padding: 30px;
            color: #27ae60;
            font-size: 18px;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }

        @media print {
            body {
                background: white;
                padding: 0;
            }
            .container {
                box-shadow: none;
            }
        }
        """

    def _build_header(self, _record: UserRecord) -> str:
        """构建报告头部"""
        return """
    <div class="container">
        <div class="header">
            <h1>{self.i18n.t('report.title')}</h1>
            <div class="subtitle">{record.experiment_title}</div>
        </div>
        """

    def _build_summary(self, record: UserRecord) -> str:
        """构建摘要部分"""
        record.started_at.strftime("%Y-%m-%d %H:%M:%S") if record.started_at else "N/A"
        record.finished_at.strftime("%Y-%m-%d %H:%M:%S") if record.finished_at else "N/A"

        if record.started_at and record.finished_at:
            delta = record.finished_at - record.started_at
            minutes = int(delta.total_seconds() / 60)
            f"{minutes} {self.i18n.t('ui.minutes')}"

        return """
        <div class="section">
            <h2 class="section-title">{self.i18n.t('report.experiment_info')}</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.record_id')}</div>
                    <div class="info-value">{record.record_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.user_id')}</div>
                    <div class="info-value">{record.user_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.started_at')}</div>
                    <div class="info-value">{started}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.finished_at')}</div>
                    <div class="info-value">{finished}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.duration')}</div>
                    <div class="info-value">{duration}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">{self.i18n.t('ui.total_errors')}</div>
                    <div class="info-value">{len(record.mistakes)}</div>
                </div>
            </div>

            <div class="score-box">
                <div class="label">{self.i18n.t('ui.final_score')}</div>
                <div class="value">{record.final_score}</div>
            </div>
        </div>
        """

    def _build_step_details(self, record: UserRecord) -> str:
        """构建步骤详情"""
        steps_html = ""
        for step_record in record.step_records:
            self.i18n.t("step.passed") if step_record.passed else self.i18n.t("step.failed")

            str(step_record.user_input) if step_record.user_input else ""

            steps_html += """
            <li class="step-item {status_class}">
                <div class="step-header">
                    <span class="step-title">{step_record.step_id}</span>
                    <span class="step-score {status_class}">
                        {status_text} | {self.i18n.t('ui.score')}: {step_record.score}
                    </span>
                </div>
                <div class="step-content">
                    {f'<div><strong>{self.i18n.t("ui.user_input")}:</strong> {user_input}</div>' if user_input else ''}
                    {f'<div><strong>{self.i18n.t("ui.feedback")}:</strong> {feedback}</div>' if feedback else ''}
                </div>
            </li>
            """

        return """
        <div class="section">
            <h2 class="section-title">{self.i18n.t('report.step_details')}</h2>
            <ul class="step-list">
                {steps_html}
            </ul>
        </div>
        """

    def _build_mistakes(self, record: UserRecord) -> str:
        """构建错误汇总"""
        if not record.mistakes:
            mistakes_html = f"<div class='no-mistakes'>✅ {self.i18n.t('ui.no_errors')}</div>"
        else:
            mistakes_html = ""
            for _mistake in record.mistakes:
                mistakes_html += """
                <div class="mistake-item {severity_class}">
                    <div class="mistake-header">{mistake.step_id} - {mistake.severity.upper()}</div>
                    <div>{mistake.message}</div>
                </div>
                """

        return """
        <div class="section">
            <h2 class="section-title">{self.i18n.t('report.mistakes_summary')}</h2>
            {mistakes_html}
        </div>
        """

    def _build_footer(self) -> str:
        """构建报告底部"""
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return """
        <div class="footer">
            <p>VirtualChemLab - {self.i18n.t('app.title')}</p>
            <p>{self.i18n.t('ui.generated_at')}: {now}</p>
        </div>
    </div>
        """
