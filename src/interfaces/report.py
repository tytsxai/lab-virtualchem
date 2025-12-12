"""报告相关接口与默认实现"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..models.user_record import UserRecord


class ReportFormat(str, Enum):
    """报告格式"""

    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    JSON = "json"


class IReportGenerator(ABC):
    """报告生成器接口"""

    @abstractmethod
    def generate(self, record: UserRecord, template: str | None = None, options: dict[str, Any] | None = None) -> str:
        """生成报告内容"""

    @abstractmethod
    def set_template(self, template_name: str, template_content: str) -> None:
        """设置模板"""

    @abstractmethod
    def list_templates(self) -> list[str]:
        """列出可用模板"""


class IReportExporter(ABC):
    """报告导出器接口"""

    @abstractmethod
    def export(
        self,
        content: str,
        output_path: Path,
        format: ReportFormat,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """导出报告"""

    @abstractmethod
    def get_supported_formats(self) -> list[ReportFormat]:
        """获取支持的格式"""

    @abstractmethod
    def validate_export(self, output_path: Path, format: ReportFormat) -> tuple[bool, str]:
        """验证导出参数"""


class IReportBuilder(ABC):
    """报告构建器接口 - Builder模式"""

    @abstractmethod
    def add_header(self, title: str, subtitle: str | None = None) -> IReportBuilder:
        """添加标题"""

    @abstractmethod
    def add_section(self, section_name: str, content: Any) -> IReportBuilder:
        """添加章节"""

    @abstractmethod
    def add_table(self, headers: list[str], rows: list[list[Any]]) -> IReportBuilder:
        """添加表格"""

    @abstractmethod
    def add_chart(self, chart_type: str, data: dict[str, Any], title: str | None = None) -> IReportBuilder:
        """添加图表"""

    @abstractmethod
    def build(self) -> str:
        """构建报告"""

    @abstractmethod
    def reset(self) -> None:
        """重置构建器"""


# --------- 轻量级默认实现，便于在无完整依赖时兜底使用 ---------


class SimpleReportGenerator(IReportGenerator):
    """简单的报告生成器，输出 JSON 字符串"""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {"default": "{title} ({user_id})"}

    def generate(
        self, record: UserRecord, template: str | None = None, options: dict[str, Any] | None = None
    ) -> str:
        tpl_name = template or "default"
        tpl = self._templates.get(tpl_name, "{title} ({user_id})")
        data = {
            "record_id": record.record_id,
            "user_id": record.user_id,
            "experiment_id": record.experiment_id,
            "experiment_title": record.experiment_title,
            "status": record.status,
            "score": record.score.total,
            "started_at": record.started_at.isoformat(),
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "steps": [
                {
                    "step_id": s.step_id,
                    "passed": s.passed,
                    "mistakes": [m.model_dump() for m in s.mistakes],
                    "duration_seconds": s.duration_seconds,
                }
                for s in record.step_records
            ],
            "mistakes_summary": [m.model_dump() for m in record.mistakes_summary],
            "metadata": options or {},
        }
        header = tpl.format(title=record.experiment_title, user_id=record.user_id)
        data["title"] = header
        return json.dumps(data, ensure_ascii=False)

    def set_template(self, template_name: str, template_content: str) -> None:
        self._templates[template_name] = template_content

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())


class SimpleReportExporter(IReportExporter):
    """简单导出器，在缺少第三方依赖时也可落盘"""

    def __init__(self) -> None:
        self._supported = [ReportFormat.PDF, ReportFormat.HTML, ReportFormat.MARKDOWN, ReportFormat.JSON]

    def export(
        self,
        content: str,
        output_path: Path,
        format: ReportFormat,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        metadata = metadata or {}
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == ReportFormat.JSON:
            try:
                obj = json.loads(content)
            except json.JSONDecodeError:
                obj = {"content": content}
            output_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            return True

        if format == ReportFormat.HTML:
            html = content
            if "<html" not in content.lower():
                html = f"<html><body><pre>{content}</pre></body></html>"
            output_path.write_text(html, encoding="utf-8")
            return True

        if format == ReportFormat.MARKDOWN:
            output_path.write_text(content, encoding="utf-8")
            return True

        if format == ReportFormat.PDF:
            placeholder = f"PDF export placeholder generated at {datetime.now().isoformat()}\n{content}"
            output_path.write_text(placeholder, encoding="utf-8")
            return True

        return False

    def get_supported_formats(self) -> list[ReportFormat]:
        return list(self._supported)

    def validate_export(self, output_path: Path, format: ReportFormat) -> tuple[bool, str]:
        if format not in self._supported:
            return False, f"不支持的格式: {format.value}"
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover
            return False, f"创建输出目录失败: {exc}"
        return True, ""


@dataclass
class SimpleReportBuilder(IReportBuilder):
    """简单的文本构建器，使用 Markdown 片段组装"""

    sections: list[str] = field(default_factory=list)
    title: str | None = None
    subtitle: str | None = None

    def add_header(self, title: str, subtitle: str | None = None) -> SimpleReportBuilder:
        self.title = title
        self.subtitle = subtitle
        return self

    def add_section(self, section_name: str, content: Any) -> SimpleReportBuilder:
        self.sections.append(f"# {section_name}\n{content}")
        return self

    def add_table(self, headers: list[str], rows: list[list[Any]]) -> SimpleReportBuilder:
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        body = "\n".join("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
        self.sections.append("\n".join([header_line, sep_line, body]))
        return self

    def add_chart(self, chart_type: str, data: dict[str, Any], title: str | None = None) -> SimpleReportBuilder:
        chart_title = title or chart_type
        self.sections.append(f"![{chart_title}](chart://{chart_type})\n{json.dumps(data)}")
        return self

    def build(self) -> str:
        header = f"{self.title or ''}\n"
        if self.subtitle:
            header += f"{self.subtitle}\n"
        body = "\n\n".join(self.sections)
        return f"{header}\n{body}".strip()

    def reset(self) -> None:
        self.sections.clear()
        self.title = None
        self.subtitle = None


def get_default_report_components() -> tuple[IReportGenerator, IReportExporter, IReportBuilder]:
    """工厂方法：提供简单可用的报告组件集合"""
    return SimpleReportGenerator(), SimpleReportExporter(), SimpleReportBuilder()
