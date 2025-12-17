"""
PDF导出器
将HTML报告转换为PDF
"""

import os

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFExporter:
    """PDF导出器"""

    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            logger.warning(
                "WeasyPrint未安装,PDF导出功能不可用。请运行: pip install weasyprint"
            )

    def export_from_html(self, html_content: str, output_path: str) -> bool:
        """
        从HTML内容生成PDF

        Args:
            html_content: HTML字符串
            output_path: PDF输出路径

        Returns:
            是否成功
        """
        if not WEASYPRINT_AVAILABLE:
            logger.error("WeasyPrint未安装,无法导出PDF")
            return False

        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 生成PDF
            HTML(string=html_content).write_pdf(output_path)

            logger.info(f"PDF报告已生成: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出PDF失败: {e}")
            return False

    def export_from_html_file(self, html_path: str, output_path: str) -> bool:
        """
        从HTML文件生成PDF

        Args:
            html_path: HTML文件路径
            output_path: PDF输出路径

        Returns:
            是否成功
        """
        if not WEASYPRINT_AVAILABLE:
            logger.error("WeasyPrint未安装,无法导出PDF")
            return False

        try:
            if not os.path.exists(html_path):
                logger.error(f"HTML文件不存在: {html_path}")
                return False

            # 读取HTML
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()

            # 导出PDF
            return self.export_from_html(html_content, output_path)

        except Exception as e:
            logger.error(f"从HTML文件导出PDF失败: {e}")
            return False


# 替代方案:使用ReportLab(如果WeasyPrint不可用)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics  # noqa: F401
    from reportlab.pdfbase.ttfonts import TTFont  # noqa: F401
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFExporterSimple:
    """简单PDF导出器(使用ReportLab)"""

    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab未安装,简单PDF导出功能不可用")
            return

        # 注册中文字体
        self._register_chinese_fonts()

    def export_simple_report(
        self, title: str, content_lines: list, output_path: str
    ) -> bool:
        """
        导出简单的文本PDF报告

        Args:
            title: 标题
            content_lines: 内容行列表
            output_path: 输出路径

        Returns:
            是否成功
        """
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab未安装,无法导出PDF")
            return False

        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()

            # 标题
            story.append(Paragraph(title, styles["Title"]))
            story.append(Spacer(1, 20))

            # 内容
            for line in content_lines:
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 10))

            doc.build(story)

            logger.info(f"简单PDF报告已生成: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出简单PDF失败: {e}")
            return False

    def _register_chinese_fonts(self):
        """注册中文字体"""
        if not REPORTLAB_AVAILABLE:
            return

        import platform
        from pathlib import Path

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        try:
            # 字体搜索路径（按优先级）
            font_paths = []
            system = platform.system()

            if system == "Windows":
                # Windows字体路径
                windows_fonts = Path("C:/Windows/Fonts")
                font_paths = [
                    windows_fonts / "simsun.ttc",  # 宋体
                    windows_fonts / "simhei.tt",  # 黑体
                    windows_fonts / "msyh.ttc",  # 微软雅黑
                    windows_fonts / "simkai.tt",  # 楷体
                ]
            elif system == "Darwin":  # macOS
                # macOS字体路径
                font_paths = [
                    Path("/System/Library/Fonts/PingFang.ttc"),  # 苹方
                    Path("/System/Library/Fonts/STHeiti Medium.ttc"),  # 黑体
                    Path("/Library/Fonts/Songti.ttc"),  # 宋体
                ]
            elif system == "Linux":
                # Linux字体路径
                linux_fonts = [
                    Path(
                        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
                    ),  # 文泉驿微米黑
                    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),  # 文泉驿正黑
                    Path(
                        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.tt"
                    ),  # Droid
                    Path(
                        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
                    ),  # Noto Sans
                ]
                font_paths = linux_fonts

            # 尝试注册找到的第一个可用字体
            for font_path in font_paths:
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont("ChineseFont", str(font_path)))
                        logger.info(f"已注册中文字体: {font_path.name}")

                        # 设置为默认中文字体
                        from reportlab.lib.styles import getSampleStyleSheet

                        styles = getSampleStyleSheet()
                        for style in styles.byName.values():
                            style.fontName = "ChineseFont"

                        return
                    except Exception as e:
                        logger.warning(f"注册字体失败 {font_path}: {e}")
                        continue

            # 如果没有找到系统字体，尝试使用项目内置字体（如果有）
            project_fonts = Path(__file__).parent.parent.parent / "assets" / "fonts"
            if project_fonts.exists():
                for font_file in project_fonts.glob("*.tt"):
                    try:
                        pdfmetrics.registerFont(TTFont("ChineseFont", str(font_file)))
                        logger.info(f"已注册项目字体: {font_file.name}")
                        return
                    except Exception as e:
                        logger.warning(f"注册项目字体失败: {e}")

            logger.warning("未找到可用的中文字体，PDF可能无法正确显示中文")
            logger.info("建议安装思源黑体或其他开源中文字体")

        except Exception as e:
            logger.error(f"注册中文字体失败: {e}", exc_info=True)
