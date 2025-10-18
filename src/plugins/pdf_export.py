"""
PDF导出模块 - ReportLab/WeasyPrint 适配层
用于生成专业的实验报告PDF
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from . import registry, require_plugin

logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF导出器"""

    def __init__(self):
        self.reportlab = registry.get_module("reportlab")
        self.weasyprint = registry.get_module("weasyprint")

    @require_plugin("reportlab")
    def export_with_reportlab(
        self,
        output_path: Path,
        title: str,
        content: list[dict[str, Any]],
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """使用ReportLab导出PDF

        Args:
            output_path: 输出路径
            title: 文档标题
            content: 内容列表，每项为 {'type': 'text'/'image'/'table', 'data': ...}
            metadata: 元数据（作者、主题等）

        Returns:
            是否成功
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        try:
            # 创建文档
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                title=title,
                author=metadata.get("author", "VirtualChemLab") if metadata else "VirtualChemLab",
            )

            # 准备样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=30,
            )

            # 构建内容
            story = []

            # 标题
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))

            # 元数据
            if metadata:
                meta_text = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                if "author" in metadata:
                    meta_text += f" | 作者: {metadata['author']}"
                story.append(Paragraph(meta_text, styles["Normal"]))
                story.append(Spacer(1, 20))

            # 内容块
            for item in content:
                item_type = item.get("type")

                if item_type == "text":
                    story.append(Paragraph(item["data"], styles["Normal"]))
                    story.append(Spacer(1, 12))

                elif item_type == "heading":
                    story.append(Paragraph(item["data"], styles["Heading2"]))
                    story.append(Spacer(1, 12))

                elif item_type == "image":
                    img = Image(item["path"], width=item.get("width", 15 * cm))
                    story.append(img)
                    if "caption" in item:
                        story.append(Paragraph(f"图: {item['caption']}", styles["Italic"]))
                    story.append(Spacer(1, 12))

                elif item_type == "table":
                    table = Table(item["data"])
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 12),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ]
                        )
                    )
                    story.append(table)
                    story.append(Spacer(1, 12))

            # 生成PDF
            doc.build(story)
            logger.info(f"PDF导出成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"ReportLab导出失败: {e}")
            return False

    @require_plugin("weasyprint")
    def export_with_weasyprint(self, output_path: Path, html_content: str, base_url: str | None = None) -> bool:
        """使用WeasyPrint从HTML导出PDF

        Args:
            output_path: 输出路径
            html_content: HTML内容
            base_url: 基础URL（用于解析相对路径）

        Returns:
            是否成功
        """
        from weasyprint import CSS, HTML

        try:
            html = HTML(string=html_content, base_url=base_url)

            # 自定义CSS样式
            css = CSS(
                string="""
                @page {
                    size: A4;
                    margin: 2cm;
                }
                body {
                    font-family: "Microsoft YaHei", "SimSun", sans-serif;
                    line-height: 1.6;
                }
                h1 {
                    color: #1a1a1a;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }
                table, th, td {
                    border: 1px solid #ddd;
                }
                th {
                    background-color: #4CAF50;
                    color: white;
                    padding: 8px;
                }
                td {
                    padding: 8px;
                }
            """
            )

            html.write_pdf(str(output_path), stylesheets=[css])
            logger.info(f"PDF导出成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"WeasyPrint导出失败: {e}")
            return False

    def export(self, output_path: Path, content: Any, method: str = "auto", **kwargs) -> bool:
        """智能选择导出方法

        Args:
            output_path: 输出路径
            content: 内容（HTML字符串或结构化数据）
            method: 'reportlab', 'weasyprint', 'auto'

        Returns:
            是否成功
        """
        if method == "auto":
            # 优先使用ReportLab
            if registry.is_available("reportlab"):
                method = "reportlab"
            elif registry.is_available("weasyprint"):
                method = "weasyprint"
            else:
                return self._fallback_export(output_path, content, **kwargs)

        if method == "reportlab" and registry.is_available("reportlab"):
            if isinstance(content, str):
                # HTML转结构化数据（简化）
                content = [{"type": "text", "data": content}]
            return self.export_with_reportlab(
                output_path, kwargs.get("title", "实验报告"), content, kwargs.get("metadata")
            )

        elif method == "weasyprint" and registry.is_available("weasyprint"):
            if not isinstance(content, str):
                # 结构化数据转HTML（简化）
                content = "<html><body><h1>实验报告</h1></body></html>"
            return self.export_with_weasyprint(output_path, content, kwargs.get("base_url"))

        return False

    def _fallback_export(self, output_path: Path, content: Any, **_kwargs) -> bool:
        """回退：使用基础方法导出"""
        logger.warning("PDF库未安装，使用基础导出")

        # 导出为文本文件
        try:
            text_path = output_path.with_suffix(".txt")
            with open(text_path, "w", encoding="utf-8") as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    f.write("实验报告\n\n")
                    for item in content:
                        if item.get("type") == "text":
                            f.write(item["data"] + "\n\n")

            logger.info(f"导出为文本文件: {text_path}")
            return True
        except Exception as e:
            logger.error(f"回退导出失败: {e}")
            return False


# 注册插件
registry.register(
    name="reportlab",
    description="PDF报告生成（ReportLab）",
    module_name="reportlab",
    license="BSD",
)

registry.register(
    name="weasyprint",
    description="HTML转PDF（WeasyPrint）",
    module_name="weasyprint",
    license="BSD",
)


def get_exporter() -> PDFExporter:
    """获取PDF导出器实例"""
    return PDFExporter()


def is_available() -> bool:
    """检查是否有可用的PDF导出器"""
    return registry.is_available("reportlab") or registry.is_available("weasyprint")
