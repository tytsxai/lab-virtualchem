"""报告服务契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..models.user_record import UserRecord


class ReportType(str, Enum):
    """报告类型"""

    EXPERIMENT = "experiment"  # 实验报告
    SUMMARY = "summary"  # 汇总报告
    ANALYSIS = "analysis"  # 分析报告
    COMPARISON = "comparison"  # 对比报告
    PROGRESS = "progress"  # 进度报告


class ExportFormat(str, Enum):
    """导出格式"""

    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"


@dataclass
class ReportServiceConfig:
    """报告服务配置"""

    template_dir: str = "templates/reports"  # 模板目录
    output_dir: str = "outputs/reports"  # 输出目录
    default_format: ExportFormat = ExportFormat.PDF  # 默认格式
    include_charts: bool = True  # 是否包含图表
    include_raw_data: bool = False  # 是否包含原始数据
    watermark: str | None = None  # 水印文本
    page_size: str = "A4"  # 页面大小
    language: str = "zh_CN"  # 语言


@dataclass
class ReportRequest:
    """报告请求DTO"""

    report_type: ReportType  # 报告类型
    record_id: str | None = None  # 记录ID
    record_ids: list[str] = field(default_factory=list)  # 记录ID列表(用于对比报告)
    format: ExportFormat = ExportFormat.PDF  # 导出格式
    template_name: str | None = None  # 模板名称
    options: dict[str, Any] = field(default_factory=dict)  # 额外选项
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class ReportResponse:
    """报告响应DTO"""

    success: bool  # 是否成功
    report_id: str | None = None  # 报告ID
    file_path: Path | None = None  # 文件路径
    content: str | None = None  # 内容(如果不保存为文件)
    message: str = ""  # 消息
    warnings: list[str] = field(default_factory=list)  # 警告列表


@dataclass
class ChartData:
    """图表数据DTO"""

    chart_type: str  # 图表类型
    title: str  # 标题
    x_data: list[Any]  # X轴数据
    y_data: list[Any]  # Y轴数据
    x_label: str = ""  # X轴标签
    y_label: str = ""  # Y轴标签
    options: dict[str, Any] = field(default_factory=dict)  # 额外选项


@dataclass
class ReportSection:
    """报告章节DTO"""

    title: str  # 章节标题
    content: str  # 章节内容
    level: int = 1  # 标题级别
    charts: list[ChartData] = field(default_factory=list)  # 图表列表
    tables: list[dict[str, Any]] = field(default_factory=list)  # 表格列表


class ReportService(ABC):
    """报告服务抽象类"""

    @abstractmethod
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """生成报告

        Args:
            request: 报告请求

        Returns:
            报告响应
        """
        pass

    @abstractmethod
    def generate_experiment_report(
        self,
        record: UserRecord,
        format: ExportFormat = ExportFormat.PDF,
        options: dict[str, Any] | None = None,
        template_name: str | None = None,
    ) -> ReportResponse:
        """生成实验报告

        Args:
            record: 用户记录
            format: 导出格式
            options: 额外选项
            template_name: 指定模板

        Returns:
            报告响应
        """
        pass

    @abstractmethod
    def generate_summary_report(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        format: ExportFormat = ExportFormat.PDF,
    ) -> ReportResponse:
        """生成汇总报告

        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            format: 导出格式

        Returns:
            报告响应
        """
        pass

    @abstractmethod
    def generate_comparison_report(
        self, record_ids: list[str], format: ExportFormat = ExportFormat.PDF
    ) -> ReportResponse:
        """生成对比报告

        Args:
            record_ids: 记录ID列表
            format: 导出格式

        Returns:
            报告响应
        """
        pass

    @abstractmethod
    def export_report(
        self, report_id: str, output_path: Path, format: ExportFormat
    ) -> bool:
        """导出报告

        Args:
            report_id: 报告ID
            output_path: 输出路径
            format: 导出格式

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def get_available_templates(
        self, report_type: ReportType | None = None
    ) -> list[str]:
        """获取可用模板

        Args:
            report_type: 报告类型(可选)

        Returns:
            模板名称列表
        """
        pass

    @abstractmethod
    def preview_report(self, request: ReportRequest) -> str:
        """预览报告(HTML)

        Args:
            request: 报告请求

        Returns:
            HTML内容
        """
        pass
