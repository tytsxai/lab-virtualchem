"""
报告服务实现
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

try:
    import yaml as _yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - optional dependency
    _yaml = None

yaml = cast("Any | None", _yaml)

from src.contracts.report_service import (
    ExportFormat,
    ReportRequest,
    ReportResponse,
    ReportService,
    ReportServiceConfig,
    ReportType,
)
from src.core.repository import IRepository
from src.interfaces.report import IReportExporter, IReportGenerator, ReportFormat
from src.models.user_record import UserRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

_SUPPORTED_TEMPLATE_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".markdown", ".html", ".htm", ".jinja", ".j2", ".tpl"}
_REPORT_TYPE_ALIASES: dict[ReportType, list[str]] = {
    ReportType.EXPERIMENT: ["experiment", "exp", "lab", "实验"],
    ReportType.SUMMARY: ["summary", "sum", "overview", "汇总"],
    ReportType.ANALYSIS: ["analysis", "ana", "detail", "分析"],
    ReportType.COMPARISON: ["comparison", "compare", "cmp", "对比"],
    ReportType.PROGRESS: ["progress", "prog", "timeline", "进度"],
}


@dataclass
class TemplateInfo:
    """描述报告模板的元数据"""

    name: str
    path: Path | None = None
    report_types: set[ReportType] = field(default_factory=set)


if TYPE_CHECKING:
    from typing import Protocol

    class _ReportServiceBase(Protocol):
        def generate_report(self, request: ReportRequest) -> ReportResponse: ...

        def generate_experiment_report(
            self,
            record: UserRecord,
            format: ExportFormat = ...,
            options: dict[str, Any] | None = ...,
            template_name: str | None = ...,
        ) -> ReportResponse: ...

        def generate_summary_report(
            self,
            user_id: str,
            start_date: str | None = ...,
            end_date: str | None = ...,
            format: ExportFormat = ...,
        ) -> ReportResponse: ...

        def generate_comparison_report(self, record_ids: list[str], format: ExportFormat = ...) -> ReportResponse: ...

        def export_report(self, report_id: str, output_path: Path, format: ExportFormat) -> bool: ...

        def get_available_templates(self, report_type: ReportType | None = None) -> list[str]: ...

        def preview_report(self, request: ReportRequest) -> str: ...

else:  # pragma: no cover - runtime inherits真实基类
    _ReportServiceBase = ReportService


class ReportServiceImpl(_ReportServiceBase):
    """报告服务具体实现"""

    def __init__(
        self,
        generator: IReportGenerator,
        exporter: IReportExporter,
        record_repository: IRepository[UserRecord] | None = None,
        config: ReportServiceConfig | None = None,
    ):
        self.generator = generator
        self.exporter = exporter
        self.record_repository = record_repository
        self.config = config or ReportServiceConfig()
        self._report_cache: dict[str, str] = {}  # 报告缓存
        self._template_cache: dict[str, TemplateInfo] = {}

    def _convert_format(self, export_format: ExportFormat) -> ReportFormat:
        """将ExportFormat转换为ReportFormat"""
        format_map = {
            ExportFormat.PDF: ReportFormat.PDF,
            ExportFormat.HTML: ReportFormat.HTML,
            ExportFormat.MARKDOWN: ReportFormat.MARKDOWN,
            ExportFormat.JSON: ReportFormat.JSON,
        }
        return format_map.get(export_format, ReportFormat.PDF)

    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """生成报告"""
        try:
            if request.report_type == ReportType.EXPERIMENT and request.record_id:
                # 加载记录并生成实验报告
                record = self._load_record(request.record_id)
                if not record:
                    logger.warning(f"记录不存在: {request.record_id}")
                    return ReportResponse(success=False, message="记录不存在")
                return self.generate_experiment_report(record, request.format, request.options, request.template_name)

            elif request.report_type == ReportType.COMPARISON and request.record_ids:
                # 生成对比报告
                return self.generate_comparison_report(request.record_ids, request.format)

            else:
                logger.warning(f"不支持的报告类型或缺少参数: {request.report_type}")
                return ReportResponse(success=False, message="不支持的报告类型或缺少必要参数")

        except OSError as e:
            logger.error(f"文件操作失败: {e}", exc_info=True)
            return ReportResponse(success=False, message="文件操作失败，请检查权限和磁盘空间")
        except ValueError as e:
            logger.error(f"参数错误: {e}", exc_info=True)
            return ReportResponse(success=False, message=f"参数错误: {str(e)}")
        except Exception as e:
            logger.error(f"生成报告失败: {e}", exc_info=True)
            return ReportResponse(success=False, message="生成报告失败，请查看日志获取详细信息")

    def generate_experiment_report(
        self,
        record: UserRecord,
        format: ExportFormat = ExportFormat.PDF,
        options: dict[str, Any] | None = None,
        template_name: str | None = None,
    ) -> ReportResponse:
        """生成实验报告"""
        try:
            logger.info(f"生成实验报告: record_id={record.record_id}, format={format.value}")

            # 生成报告内容
            content = self.generator.generate(record, template=template_name, options=options)

            # 缓存报告内容
            self._cache_report(record.record_id, content)

            # 导出报告
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"report_{record.record_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
            output_path = output_dir / filename

            success = self.exporter.export(
                content,
                output_path,
                self._convert_format(format),
                metadata={"record_id": record.record_id, "user_id": record.user_id},
            )

            if success:
                logger.info(f"报告生成成功: {output_path}")
                return ReportResponse(
                    success=True,
                    report_id=record.record_id,
                    file_path=output_path,
                    message="报告生成成功",
                )
            else:
                logger.error(f"报告导出失败: record_id={record.record_id}")
                return ReportResponse(success=False, message="报告导出失败")

        except Exception as e:
            logger.exception(f"生成实验报告失败: record_id={record.record_id}")
            return ReportResponse(success=False, message=f"生成实验报告失败: {str(e)}")

    def generate_summary_report(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        format: ExportFormat = ExportFormat.PDF,
    ) -> ReportResponse:
        """生成汇总报告"""
        try:
            # 1. 加载指定时间范围内的所有记录
            records = self._load_user_records(user_id, start_date, end_date)

            if not records:
                return ReportResponse(success=False, message="指定时间范围内没有记录")

            # 2. 计算统计信息
            summary_data = {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "total_experiments": len(records),
                "completed_experiments": sum(1 for r in records if r.status == "completed"),
                "average_score": sum(r.score.total for r in records) / len(records) if records else 0,
                "total_time": sum(
                    (r.completed_at - r.started_at).total_seconds() / 60 for r in records if r.completed_at
                ),
                "experiments_by_type": self._count_by_type(records),
                "score_trend": self._calculate_score_trend(records),
                "common_mistakes": self._analyze_common_mistakes(records),
            }

            # 3. 生成报告
            content = self._generate_summary_content(summary_data)

            # 4. 导出
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
            output_path = output_dir / filename

            success = self.exporter.export(
                content,
                output_path,
                self._convert_format(format),
                metadata={"user_id": user_id, "report_type": "summary"},
            )

            if success:
                return ReportResponse(
                    success=True,
                    report_id=f"summary_{user_id}_{datetime.now().timestamp()}",
                    file_path=output_path,
                    message="汇总报告生成成功",
                )
            else:
                return ReportResponse(success=False, message="报告导出失败")

        except Exception as e:
            return ReportResponse(success=False, message=f"生成汇总报告失败: {str(e)}")

    def generate_comparison_report(
        self, record_ids: list[str], format: ExportFormat = ExportFormat.PDF
    ) -> ReportResponse:
        """生成对比报告"""
        try:
            # 1. 加载所有记录
            records = []
            for record_id in record_ids:
                record = self._load_record(record_id)
                if record:
                    records.append(record)

            if len(records) < 2:
                return ReportResponse(success=False, message="对比报告至少需要2个有效记录")

            # 2. 生成对比数据
            comparison_data = {
                "records": records,
                "comparison_metrics": {
                    "scores": [r.score.total for r in records],
                    "times": [(r.completed_at - r.started_at).total_seconds() / 60 for r in records if r.completed_at],
                    "procedural_scores": [r.score.procedural for r in records],
                    "safety_scores": [r.score.safety for r in records],
                    "scientific_scores": [r.score.scientific for r in records],
                    "mistake_counts": [len(r.mistakes_summary) for r in records],
                },
                "differences": self._calculate_differences(records),
                "recommendations": self._generate_recommendations(records),
            }

            # 3. 生成报告内容
            content = self._generate_comparison_content(comparison_data)

            # 4. 导出
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
            output_path = output_dir / filename

            success = self.exporter.export(
                content,
                output_path,
                self._convert_format(format),
                metadata={"record_ids": record_ids, "report_type": "comparison"},
            )

            if success:
                return ReportResponse(
                    success=True,
                    report_id=f"comparison_{datetime.now().timestamp()}",
                    file_path=output_path,
                    message="对比报告生成成功",
                )
            else:
                return ReportResponse(success=False, message="报告导出失败")

        except Exception as e:
            return ReportResponse(success=False, message=f"生成对比报告失败: {str(e)}")

    def export_report(self, report_id: str, output_path: Path, format: ExportFormat) -> bool:
        """导出报告"""
        try:
            # 1. 从缓存或存储加载报告
            report_content = self._load_report_from_storage(report_id)

            if not report_content:
                return False

            # 2. 导出到指定路径
            report_format = self._convert_format(format)
            success = bool(
                self.exporter.export(
                report_content, output_path, report_format, metadata={"report_id": report_id}
                )
            )

            return success

        except Exception:
            return False

    def get_available_templates(self, report_type: ReportType | None = None) -> list[str]:
        """获取可用模板（结合生成器与文件系统）"""
        builtin_templates = self.generator.list_templates()
        builtin_infos = [
            TemplateInfo(name=name, report_types=self._infer_report_types_from_name(name))
            for name in builtin_templates
        ]
        fs_infos = self._load_templates_from_directory()
        combined = builtin_infos + fs_infos

        def _matches(info: TemplateInfo) -> bool:
            if report_type is None:
                return True
            if info.report_types:
                return report_type in info.report_types
            return self._name_matches_report_type(info.name, report_type)

        filtered: list[str] = []
        seen: set[str] = set()
        for info in combined:
            if info.name in seen:
                continue
            if _matches(info):
                filtered.append(info.name)
                seen.add(info.name)

        if filtered:
            return filtered

        # 没有匹配项时回退至全部模板
        for info in combined:
            if info.name not in seen:
                filtered.append(info.name)
                seen.add(info.name)
        return filtered

    def _load_templates_from_directory(self) -> list[TemplateInfo]:
        """从文件系统加载模板元数据"""
        template_dir = Path(self.config.template_dir)
        if not template_dir.exists() or not template_dir.is_dir():
            return []

        infos: list[TemplateInfo] = []
        for entry in template_dir.rglob("*"):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in _SUPPORTED_TEMPLATE_SUFFIXES:
                continue
            content: str | None = None
            try:
                content = entry.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                logger.warning("无法读取报告模板文件: %s", entry)
                continue

            info = TemplateInfo(name=entry.stem, path=entry)
            info.report_types = self._infer_report_types_from_file(entry, content)
            infos.append(info)
            self._template_cache[info.name] = info

            # 将模板内容注册到生成器，便于后续直接引用
            try:
                self.generator.set_template(info.name, content)
            except Exception:  # pragma: no cover - 生成器可能不支持注册功能
                logger.debug("模板 %s 注册到生成器失败，忽略", info.name, exc_info=True)

        return infos

    def _infer_report_types_from_file(self, path: Path, content: str) -> set[ReportType]:
        """结合文件内容/名称推断适用的报告类型"""
        inferred = self._infer_report_types_from_name(path.stem)
        suffix = path.suffix.lower()
        data: Any | None = None

        if suffix == ".json":
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = None
        elif suffix in {".yaml", ".yml"} and yaml is not None:
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError:
                data = None

        if isinstance(data, dict):
            inferred.update(self._collect_report_type_values(data))
        else:
            inferred.update(self._extract_inline_report_types(content))

        return inferred

    def _collect_report_type_values(self, payload: dict[str, Any]) -> set[ReportType]:
        """从结构化数据里解析 report_type 字段"""
        report_types: set[ReportType] = set()
        keys = ("report_type", "type", "category")
        for key in keys:
            if key in payload:
                report_types.update(self._convert_to_report_types(payload[key]))

        if "report_types" in payload:
            report_types.update(self._convert_to_report_types(payload["report_types"]))

        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            report_types.update(self._collect_report_type_values(metadata))

        return report_types

    def _convert_to_report_types(self, value: Any) -> set[ReportType]:
        """将多种输入形式转换为 ReportType 集合"""
        result: set[ReportType] = set()
        if value is None:
            return result
        if isinstance(value, ReportType):
            result.add(value)
            return result
        if isinstance(value, str):
            candidate = self._coerce_report_type(value)
            if candidate:
                result.add(candidate)
            return result
        if isinstance(value, (list, tuple, set)):
            for item in value:
                result.update(self._convert_to_report_types(item))
        elif isinstance(value, dict):
            result.update(self._collect_report_type_values(value))
        return result

    def _coerce_report_type(self, raw: Any) -> ReportType | None:
        """尝试将字符串/枚举值转为 ReportType"""
        if raw is None:
            return None
        if isinstance(raw, ReportType):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            for report_type in ReportType:
                if normalized in {report_type.value.lower(), report_type.name.lower()}:
                    return report_type
        return None

    def _extract_inline_report_types(self, content: str) -> set[ReportType]:
        """从文本中提取 report_type 标记"""
        result: set[ReportType] = set()
        pattern = re.compile(r"report_types?\s*[:=]\s*([A-Za-z_,\s-]+)", re.IGNORECASE)
        for match in pattern.finditer(content[:512]):  # 仅扫描文件前部
            raw_value = match.group(1)
            candidates = re.split(r"[\s,]+", raw_value.strip())
            for candidate in candidates:
                report_type = self._coerce_report_type(candidate)
                if report_type:
                    result.add(report_type)
        return result

    def _name_matches_report_type(self, name: str, report_type: ReportType) -> bool:
        """根据名称推断模板是否匹配指定类型"""
        lowered = name.lower()
        if report_type.value.lower() in lowered:
            return True
        for alias in _REPORT_TYPE_ALIASES.get(report_type, []):
            if alias in lowered:
                return True
        return False

    def _infer_report_types_from_name(self, name: str) -> set[ReportType]:
        """基于模板名称的启发式推断"""
        inferred: set[ReportType] = set()
        lowered = name.lower()
        for report_type, aliases in _REPORT_TYPE_ALIASES.items():
            if report_type.value.lower() in lowered:
                inferred.add(report_type)
                continue
            if any(alias in lowered for alias in aliases):
                inferred.add(report_type)
        return inferred

    def preview_report(self, request: ReportRequest) -> str:
        """预览报告(HTML)"""
        try:
            if request.record_id:
                record = self._load_record(request.record_id)
                if record:
                    content = self.generator.generate(record, options={"format": "html"})
                    return str(content)

            return "<html><body><p>无法预览报告</p></body></html>"

        except Exception as e:
            return f"<html><body><p>预览失败: {str(e)}</p></body></html>"

    def _load_record(self, record_id: str) -> UserRecord | None:
        """加载记录"""
        if not self.record_repository:
            return None
        try:
            return self.record_repository.get(record_id)
        except Exception:
            return None

    def _load_user_records(
        self, user_id: str, start_date: str | None = None, end_date: str | None = None
    ) -> list[UserRecord]:
        """加载用户的记录"""
        if not self.record_repository:
            return []

        try:
            if hasattr(self.record_repository, "find"):
                raw_records = self.record_repository.find(user_id)
                all_records = cast(list[UserRecord], raw_records or [])
            elif hasattr(self.record_repository, "find_by"):
                all_records = cast(
                    list[UserRecord], self.record_repository.find_by(lambda r: r.user_id == user_id)
                )
            elif hasattr(self.record_repository, "find_all"):
                all_records = [
                    r
                    for r in self.record_repository.find_all()
                    if getattr(r, "user_id", None) == user_id
                ]
            else:
                return []

            if start_date or end_date:
                filtered_records: list[UserRecord] = []
                for record in all_records:
                    record_date = record.started_at.strftime("%Y-%m-%d")
                    if start_date and record_date < start_date:
                        continue
                    if end_date and record_date > end_date:
                        continue
                    filtered_records.append(record)
                return filtered_records

            return all_records
        except Exception:
            return []

    def _load_report_from_storage(self, report_id: str) -> str | None:
        """从存储加载报告内容"""
        # 从内存缓存加载
        if report_id in self._report_cache:
            return self._report_cache[report_id]

        # 从文件系统加载（如果启用了持久化）
        try:
            output_dir = Path(self.config.output_dir)
        except Exception:
            return None

        if not output_dir.exists() or not output_dir.is_dir():
            return None

        candidates: list[Path] = []

        # 1. 尝试精确匹配文件名（不含扩展名）
        for path in output_dir.iterdir():
            if path.is_file() and path.stem == report_id:
                candidates.append(path)

        # 2. 如果没有精确匹配，尝试文件名中包含 report_id 的情况
        if not candidates:
            for path in output_dir.iterdir():
                if path.is_file() and report_id in path.stem:
                    candidates.append(path)

        # 3. 针对 summary_xxx / comparison_xxx 等前缀的回退策略
        if not candidates and "_" in report_id:
            prefix = "_".join(report_id.split("_")[:2])
            for path in output_dir.glob(f"{prefix}_*"):
                if path.is_file():
                    candidates.append(path)

        if not candidates:
            return None

        # 选择最近修改的文件作为最终候选
        candidate = max(candidates, key=lambda p: p.stat().st_mtime)

        try:
            content = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # 将加载的内容写入缓存，便于后续快速访问
        self._report_cache[report_id] = content
        return content

    def _cache_report(self, report_id: str, content: str) -> None:
        """缓存报告内容"""
        self._report_cache[report_id] = content

    def _count_by_type(self, records: list[UserRecord]) -> dict[str, int]:
        """按实验类型统计"""
        result: dict[str, int] = {}
        for record in records:
            exp_id = record.experiment_id
            result[exp_id] = result.get(exp_id, 0) + 1
        return result

    def _calculate_score_trend(self, records: list[UserRecord]) -> list[float]:
        """计算分数趋势"""
        # 按时间排序后返回分数列表
        sorted_records = sorted(records, key=lambda r: r.started_at)
        return [float(r.score.total) for r in sorted_records]

    def _analyze_common_mistakes(self, records: list[UserRecord]) -> list[dict[str, Any]]:
        """分析常见错误"""
        mistake_counts: dict[str, dict[str, Any]] = {}
        for record in records:
            for mistake in record.mistakes_summary:
                key = mistake.description  # 使用description而不是message
                if key not in mistake_counts:
                    mistake_counts[key] = {"message": key, "count": 0, "severity": mistake.severity}
                mistake_counts[key]["count"] += 1

        # 按次数排序
        common_mistakes = sorted(mistake_counts.values(), key=lambda x: x["count"], reverse=True)
        return common_mistakes[:10]  # 返回前10个

    def _generate_summary_content(self, summary_data: dict[str, Any]) -> str:
        """生成汇总报告内容"""
        # 生成HTML/Markdown/纯文本内容
        content = """
# 学习汇总报告

## 统计信息
- 用户ID: {summary_data["user_id"]}
- 时间范围: {summary_data["start_date"]} ~ {summary_data["end_date"]}
- 总实验数: {summary_data["total_experiments"]}
- 完成实验数: {summary_data["completed_experiments"]}
- 平均分数: {summary_data["average_score"]:.2f}
- 总用时: {summary_data["total_time"]:.2f} 分钟

## 实验类型分布
"""
        for exp_type, count in summary_data["experiments_by_type"].items():
            content += f"- {exp_type}: {count}\n"

        content += "\n## 分数趋势\n"
        content += ", ".join(f"{s:.1f}" for s in summary_data["score_trend"])

        content += "\n\n## 常见错误\n"
        for i, mistake in enumerate(summary_data["common_mistakes"][:5], 1):
            content += f"{i}. {mistake['message']} (出现{mistake['count']}次)\n"

        return content

    def _generate_comparison_content(self, comparison_data: dict[str, Any]) -> str:
        """生成对比报告内容"""
        content = "# 实验对比报告\n\n"

        records = comparison_data["records"]
        metrics = comparison_data["comparison_metrics"]

        content += "## 实验列表\n"
        for i, record in enumerate(records, 1):
            content += f"{i}. 实验{record.experiment_id} - 分数: {record.score.total}\n"

        content += "\n## 对比指标\n"
        content += f"- 分数: {metrics['scores']}\n"
        content += f"- 用时(分钟): {[f'{t:.1f}' for t in metrics['times']]}\n"
        content += f"- 操作分: {metrics['procedural_scores']}\n"
        content += f"- 安全分: {metrics['safety_scores']}\n"
        content += f"- 科学分: {metrics['scientific_scores']}\n"
        content += f"- 错误数: {metrics['mistake_counts']}\n"

        return content

    def _calculate_differences(self, records: list[UserRecord]) -> dict[str, Any]:
        """计算记录之间的差异"""
        if len(records) < 2:
            return {}

        scores = [r.score.total for r in records]
        return {
            "score_range": max(scores) - min(scores),
            "best_index": scores.index(max(scores)),
            "worst_index": scores.index(min(scores)),
        }

    def _generate_recommendations(self, records: list[UserRecord]) -> list[str]:
        """生成改进建议"""
        recommendations = []

        # 分析平均分数
        avg_score = sum(r.score.total for r in records) / len(records)
        if avg_score < 60:
            recommendations.append("整体分数偏低，建议加强基础知识学习")

        # 分析错误
        total_mistakes = sum(len(r.mistakes_summary) for r in records)
        if total_mistakes > len(records) * 3:
            recommendations.append("错误较多，建议放慢操作速度，仔细阅读步骤说明")

        # 分析安全分
        avg_safety = sum(r.score.safety for r in records) / len(records)
        if avg_safety < 30:
            recommendations.append("安全意识不足，务必注意实验安全规范")

        return recommendations
