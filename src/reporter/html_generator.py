"""HTML报告生成器

该模块不依赖第三方模板库, 提供两个层次的接口:
1. HTMLReportGenerator: 直接接收字典数据生成HTML报告(供报告测试使用)
2. HTMLGenerator: 兼容旧接口, 接收UserRecord与ExperimentTemplate并输出HTML
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from ..models.experiment import ExperimentTemplate
from ..models.user_record import UserRecord
from ..utils.i18n import I18n
from ..utils.logger import get_logger

logger = get_logger(__name__)

_STYLE_BLOCK = """
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

        .step-data {
            margin-top: 10px;
            padding-left: 20px;
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
"""


class HTMLReportGenerator:
    """通用HTML报告生成器"""

    def __init__(self, report_title: str | None = None) -> None:
        self.report_title = report_title or "VirtualChemLab 实验报告"

    def generate(self, experiment_data: dict[str, Any], output_path: str | Path | None = None) -> str:
        """根据提供的数据生成HTML报告"""
        context = self._build_context(experiment_data)
        html_content = self._render_html(context)

        if output_path:
            path = Path(output_path)
            path.write_text(html_content, encoding="utf-8")
            logger.info("HTML报告已生成: %s", path)

        return html_content

    def _build_context(self, data: dict[str, Any]) -> dict[str, Any]:
        start_dt = self._to_datetime(data.get("start_time") or data.get("started_at"))
        end_dt = self._to_datetime(data.get("end_time") or data.get("completed_at"))

        steps = self._normalize_steps(data.get("steps", []))
        passed_steps = sum(1 for step in steps if step["is_correct"])
        total_mistakes = data.get("total_mistakes")
        if total_mistakes is None:
            total_mistakes = sum(len(step["mistakes"]) for step in steps)

        metadata = data.get("metadata") or {}
        description = metadata.get("description") or data.get("description") or ""
        difficulty = (
            metadata.get("difficulty_label")
            or metadata.get("difficulty")
            or data.get("difficulty")
            or "N/A"
        )

        total_score = data.get("total_score")
        if total_score is None:
            total_score = data.get("final_score", 0)

        return {
            "experiment_name": data.get("experiment_name") or data.get("experiment_title") or self.report_title,
            "experiment_id": data.get("experiment_id") or data.get("id") or "--",
            "user_id": data.get("user_id") or data.get("student_id") or "N/A",
            "description": description,
            "start_time": self._format_datetime(start_dt),
            "end_time": self._format_datetime(end_dt),
            "duration": self._humanize_duration(start_dt, end_dt),
            "difficulty": difficulty,
            "total_score": total_score,
            "steps": steps,
            "summary": {
                "total_steps": len(steps),
                "passed_steps": passed_steps,
                "total_mistakes": total_mistakes,
            },
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _normalize_steps(self, steps_input: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for index, raw_step in enumerate(steps_input, start=1):
            if not isinstance(raw_step, dict):
                continue

            data_block = raw_step.get("data")
            if isinstance(data_block, dict):
                step_data = data_block
            elif isinstance(data_block, list):
                step_data = {f"item_{i + 1}": item for i, item in enumerate(data_block)}
            elif data_block is None:
                step_data = {}
            else:
                step_data = {"value": data_block}

            raw_mistakes = raw_step.get("mistakes") or []
            mistakes = []
            for mistake in raw_mistakes:
                if isinstance(mistake, str):
                    mistakes.append(mistake)
                elif isinstance(mistake, dict):
                    mistakes.append(mistake.get("description") or str(mistake))
                else:
                    mistakes.append(getattr(mistake, "description", str(mistake)))

            normalized.append(
                {
                    "step_id": raw_step.get("step_id") or f"step_{index}",
                    "title": raw_step.get("title") or raw_step.get("step_id") or f"步骤 {index}",
                    "description": raw_step.get("description") or raw_step.get("text") or "",
                    "data": step_data,
                    "is_correct": bool(raw_step.get("is_correct") or raw_step.get("passed")),
                    "score": raw_step.get("score"),
                    "attempts": int(raw_step.get("attempts", 1) or 1),
                    "mistakes": mistakes,
                }
            )

        return normalized

    def _render_html(self, context: dict[str, Any]) -> str:
        info_items = [
            ("实验ID", context["experiment_id"]),
            ("学生ID", context["user_id"]),
            ("开始时间", context["start_time"]),
            ("结束时间", context["end_time"]),
            ("用时", context["duration"]),
            ("难度", context["difficulty"]),
        ]
        info_html = "".join(self._render_info_item(label, value) for label, value in info_items)

        summary = context["summary"]
        summary_html = "".join(
            self._render_summary_item(label, value)
            for label, value in [
                ("总步骤数", summary["total_steps"]),
                ("通过步骤", summary["passed_steps"]),
                ("总错误数", summary["total_mistakes"]),
            ]
        )

        steps_html = "".join(self._render_step(step) for step in context["steps"])
        if not steps_html:
            steps_html = "<p>暂无步骤数据</p>"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(context['experiment_name'])} - 实验报告</title>
{_STYLE_BLOCK}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{escape(context['experiment_name'])}</h1>
            <p class="subtitle">{escape(context['description'])}</p>
        </div>
        <div class="info-section">
            {info_html}
        </div>
        <div class="score-box">
            <h2>最终得分</h2>
            <div class="score">{escape(str(context['total_score']))}</div>
        </div>
        <div class="summary">
            <h2 class="section-title">实验摘要</h2>
            <div class="summary-grid">
                {summary_html}
            </div>
        </div>
        <div class="steps-section">
            <h2 class="section-title">步骤详情</h2>
            {steps_html}
        </div>
        <div class="footer">
            <p>VirtualChemLab - 虚拟化学实验室</p>
            <p>报告生成时间: {escape(context['report_time'])}</p>
        </div>
    </div>
</body>
</html>"""

    def _render_info_item(self, label: str, value: Any) -> str:
        return f"""
            <div class="info-item">
                <span class="info-label">{escape(str(label))}:</span>
                <span class="info-value">{escape(self._format_value(value))}</span>
            </div>
        """

    def _render_summary_item(self, label: str, value: Any) -> str:
        return f"""
            <div class="summary-item">
                <div class="summary-value">{escape(self._format_value(value))}</div>
                <div class="summary-label">{escape(str(label))}</div>
            </div>
        """

    def _render_step(self, step: dict[str, Any]) -> str:
        status_class = "status-pass" if step["is_correct"] else "status-fail"
        status_label = "通过" if step["is_correct"] else "失败"

        description_html = ""
        if step["description"]:
            description_html = f"<p><strong>操作:</strong> {escape(step['description'])}</p>"

        score_html = ""
        if step["score"] is not None:
            score_html = f"<p><strong>得分:</strong> {escape(self._format_value(step['score']))}</p>"

        attempts_html = ""
        if step["attempts"] > 1:
            attempts_html = f"<p><strong>尝试次数:</strong> {step['attempts']}</p>"

        data_html = self._render_step_data(step["data"])
        mistakes_html = self._render_mistakes(step["mistakes"])

        return f"""
            <div class="step-card">
                <div class="step-header">
                    <span class="step-title">{escape(step['title'])}</span>
                    <span class="step-status {status_class}">{status_label}</span>
                </div>
                <div class="step-details">
                    {description_html}
                    {score_html}
                    {attempts_html}
                    {data_html}
                </div>
                {mistakes_html}
            </div>
        """

    def _render_step_data(self, data: Any) -> str:
        if not data:
            return "<p>无输入记录</p>"

        if isinstance(data, dict):
            items_html = "".join(
                f"<li><strong>{escape(str(key))}:</strong> {escape(self._format_value(value))}</li>"
                for key, value in data.items()
            )
            return f"<ul class=\"step-data\">{items_html}</ul>"

        return f"<p>{escape(self._format_value(data))}</p>"

    def _render_mistakes(self, mistakes: Iterable[str]) -> str:
        items = [f"<div class=\"mistake-item\">• {escape(str(m))}</div>" for m in mistakes if m]
        if not items:
            return ""
        return f"""
            <div class="mistakes">
                <div class="mistakes-title">错误记录:</div>
                {''.join(items)}
            </div>
        """

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".") or "0"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "N/A"
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _humanize_duration(start: datetime | None, end: datetime | None) -> str:
        if not start or not end:
            return "N/A"
        seconds = int((end - start).total_seconds())
        if seconds < 0:
            return "N/A"
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f"{hours}小时")
        if minutes:
            parts.append(f"{minutes}分")
        parts.append(f"{sec}秒")
        return "".join(parts)

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            iso_value = value.replace("Z", "+00:00")
            with contextlib.suppress(ValueError):
                return datetime.fromisoformat(iso_value)
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                with contextlib.suppress(ValueError):
                    return datetime.strptime(value, fmt)
        return None


class HTMLGenerator(HTMLReportGenerator):
    """兼容实验控制器的HTML生成器"""

    def __init__(self) -> None:
        super().__init__()
        self.i18n = I18n()

    def generate(
        self, record: UserRecord, template: ExperimentTemplate, output_path: str | Path | None = None
    ) -> str:
        """将UserRecord转换为HTML报告"""
        experiment_data = self._convert_record_to_data(record, template)
        return super().generate(experiment_data, output_path)

    def _convert_record_to_data(self, record: UserRecord, template: ExperimentTemplate) -> dict[str, Any]:
        template_steps = {step.id: step for step in template.steps}

        steps = []
        for step_record in record.step_records:
            step_template = template_steps.get(step_record.step_id)
            title = step_template.text if step_template else step_record.step_id
            if step_template and hasattr(step_template, "title"):
                title = step_template.title or step_template.text

            description = ""
            if step_template:
                description = getattr(step_template, "text", "") or getattr(step_template, "instruction", "")

            steps.append(
                {
                    "step_id": step_record.step_id,
                    "title": title,
                    "description": description,
                    "data": step_record.user_input or {},
                    "is_correct": step_record.passed,
                    "score": None,
                    "attempts": step_record.attempts,
                    "mistakes": [m.description for m in step_record.mistakes],
                }
            )

        difficulty_code = getattr(template, "difficulty", None) or getattr(template, "level", None)
        difficulty_label = self.i18n.t(f"difficulty.{difficulty_code}") if difficulty_code else "N/A"

        return {
            "experiment_id": record.experiment_id,
            "experiment_name": template.title or record.experiment_title,
            "user_id": record.user_id,
            "start_time": record.started_at,
            "end_time": record.completed_at,
            "total_score": record.score.total if record.score else 0,
            "total_mistakes": record.total_mistakes,
            "steps": steps,
            "description": template.description,
            "difficulty": difficulty_label,
        }
