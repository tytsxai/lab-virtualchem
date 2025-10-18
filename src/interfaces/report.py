"""报告相关接口定义"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from ..models.user_record import UserRecord


class ReportFormat(str, Enum):
    """报告格式"""

    HTML = "html"
    PDF = "pd"
    MARKDOWN = "markdown"
    JSON = "json"


class IReportGenerator(ABC):
    """报告生成器接口"""

    @abstractmethod
    def generate(self, record: UserRecord, template: str | None = None, options: dict[str, Any] | None = None) -> str:
        """生成报告内容

        Args:
            record: 用户记录
            template: 模板名称(可选)
            options: 生成选项(可选)

        Returns:
            报告内容(字符串)
        """
        pass

    @abstractmethod
    def set_template(self, template_name: str, template_content: str) -> None:
        """设置模板

        Args:
            template_name: 模板名称
            template_content: 模板内容
        """
        pass

    @abstractmethod
    def list_templates(self) -> list[str]:
        """列出可用模板

        Returns:
            模板名称列表
        """
        pass


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
        """导出报告

        Args:
            content: 报告内容
            output_path: 输出路径
            format: 报告格式
            metadata: 元数据(可选)

        Returns:
            是否导出成功
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[ReportFormat]:
        """获取支持的格式

        Returns:
            格式列表
        """
        pass

    @abstractmethod
    def validate_export(self, output_path: Path, format: ReportFormat) -> tuple[bool, str]:
        """验证导出参数

        Args:
            output_path: 输出路径
            format: 报告格式

        Returns:
            (是否有效, 错误信息)
        """
        pass


class IReportBuilder(ABC):
    """报告构建器接口 - Builder模式"""

    @abstractmethod
    def add_header(self, title: str, subtitle: str | None = None) -> "IReportBuilder":
        """添加标题

        Args:
            title: 主标题
            subtitle: 副标题(可选)

        Returns:
            自身(支持链式调用)
        """
        pass

    @abstractmethod
    def add_section(self, section_name: str, content: Any) -> "IReportBuilder":
        """添加章节

        Args:
            section_name: 章节名
            content: 章节内容

        Returns:
            自身(支持链式调用)
        """
        pass

    @abstractmethod
    def add_table(self, headers: list[str], rows: list[list[Any]]) -> "IReportBuilder":
        """添加表格

        Args:
            headers: 表头
            rows: 行数据

        Returns:
            自身(支持链式调用)
        """
        pass

    @abstractmethod
    def add_chart(self, chart_type: str, data: dict[str, Any], title: str | None = None) -> "IReportBuilder":
        """添加图表

        Args:
            chart_type: 图表类型
            data: 图表数据
            title: 图表标题(可选)

        Returns:
            自身(支持链式调用)
        """
        pass

    @abstractmethod
    def build(self) -> str:
        """构建报告

        Returns:
            报告内容
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """重置构建器"""
        pass
