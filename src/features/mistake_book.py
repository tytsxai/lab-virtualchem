"""
错题本系统

提供错题收集、整理和复习功能：
- 自动收集错误
- 按类型分类
- 错题统计分析
- 复习提醒
"""

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Mistake:
    """错误记录"""

    mistake_id: str
    student_id: str
    experiment_id: str
    experiment_name: str
    mistake_type: str  # 'operation', 'calculation', 'concept', 'safety', 'other'
    mistake_description: str
    correct_answer: str = ""
    student_answer: str = ""
    occurred_at: str = ""
    reviewed: bool = False
    reviewed_at: str = ""
    mastered: bool = False
    review_count: int = 0
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        if not self.occurred_at:
            self.occurred_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Mistake":
        return cls(**data)


@dataclass
class ReviewRecord:
    """复习记录"""

    record_id: str
    student_id: str
    mistake_ids: list[str]
    review_date: str
    duration: int = 0  # 秒
    correct_count: int = 0
    total_count: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewRecord":
        return cls(**data)


class MistakeBook:
    """错题本"""

    def __init__(self, data_dir: Path = None):
        """
        初始化错题本

        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir or Path("data/mistakes")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.mistakes_dir = self.data_dir / "mistakes"
        self.reviews_dir = self.data_dir / "reviews"
        self.mistakes_dir.mkdir(exist_ok=True)
        self.reviews_dir.mkdir(exist_ok=True)

        logger.info("错题本初始化完成")

    def add_mistake(
        self,
        student_id: str,
        experiment_id: str,
        experiment_name: str,
        mistake_type: str,
        mistake_description: str,
        **kwargs,
    ) -> Mistake:
        """
        添加错误

        Args:
            student_id: 学生ID
            experiment_id: 实验ID
            experiment_name: 实验名称
            mistake_type: 错误类型
            mistake_description: 错误描述
            **kwargs: 其他参数

        Returns:
            错误对象
        """
        mistake_id = f"{student_id}_{experiment_id}_{datetime.now().timestamp()}"

        mistake = Mistake(
            mistake_id=mistake_id,
            student_id=student_id,
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            mistake_type=mistake_type,
            mistake_description=mistake_description,
            **kwargs,
        )

        self._save_mistake(mistake)
        logger.info(f"添加错误: {mistake_id}")

        return mistake

    def _save_mistake(self, mistake: Mistake):
        """保存错误"""
        student_mistakes_file = self.mistakes_dir / f"{mistake.student_id}.json"

        # 加载现有错误
        mistakes = self.get_student_mistakes(mistake.student_id)

        # 更新或添加
        updated = False
        for i, m in enumerate(mistakes):
            if m.mistake_id == mistake.mistake_id:
                mistakes[i] = mistake
                updated = True
                break

        if not updated:
            mistakes.append(mistake)

        # 保存
        try:
            with open(student_mistakes_file, "w", encoding="utf-8") as f:
                json.dump(
                    [m.to_dict() for m in mistakes], f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"保存错误失败: {e}")

    def get_student_mistakes(
        self, student_id: str, reviewed: bool = None, mistake_type: str = None
    ) -> list[Mistake]:
        """
        获取学生的错误

        Args:
            student_id: 学生ID
            reviewed: 是否已复习（可选）
            mistake_type: 错误类型（可选）

        Returns:
            错误列表
        """
        student_mistakes_file = self.mistakes_dir / f"{student_id}.json"

        if not student_mistakes_file.exists():
            return []

        try:
            with open(student_mistakes_file, encoding="utf-8") as f:
                data = json.load(f)
                mistakes = [Mistake.from_dict(m) for m in data]

            # 过滤
            if reviewed is not None:
                mistakes = [m for m in mistakes if m.reviewed == reviewed]

            if mistake_type:
                mistakes = [m for m in mistakes if m.mistake_type == mistake_type]

            return mistakes
        except Exception as e:
            logger.error(f"加载学生错误失败: {e}")
            return []

    def mark_as_reviewed(
        self, mistake_id: str, student_id: str, mastered: bool = False
    ) -> bool:
        """
        标记为已复习

        Args:
            mistake_id: 错误ID
            student_id: 学生ID
            mastered: 是否掌握

        Returns:
            是否成功
        """
        mistakes = self.get_student_mistakes(student_id)

        for mistake in mistakes:
            if mistake.mistake_id == mistake_id:
                mistake.reviewed = True
                mistake.reviewed_at = datetime.now().isoformat()
                mistake.review_count += 1
                mistake.mastered = mastered

                self._save_mistake(mistake)
                logger.info(f"标记错误已复习: {mistake_id}")
                return True

        return False

    def get_mistakes_by_type(self, student_id: str) -> dict[str, list[Mistake]]:
        """
        按类型分组错误

        Args:
            student_id: 学生ID

        Returns:
            分组的错误
        """
        mistakes = self.get_student_mistakes(student_id)

        grouped = {}
        for mistake in mistakes:
            if mistake.mistake_type not in grouped:
                grouped[mistake.mistake_type] = []
            grouped[mistake.mistake_type].append(mistake)

        return grouped

    def get_mistakes_by_experiment(self, student_id: str) -> dict[str, list[Mistake]]:
        """
        按实验分组错误

        Args:
            student_id: 学生ID

        Returns:
            分组的错误
        """
        mistakes = self.get_student_mistakes(student_id)

        grouped = {}
        for mistake in mistakes:
            if mistake.experiment_id not in grouped:
                grouped[mistake.experiment_id] = []
            grouped[mistake.experiment_id].append(mistake)

        return grouped

    def get_statistics(self, student_id: str) -> dict:
        """
        获取错题统计

        Args:
            student_id: 学生ID

        Returns:
            统计信息
        """
        mistakes = self.get_student_mistakes(student_id)

        if not mistakes:
            return {
                "total": 0,
                "reviewed": 0,
                "mastered": 0,
                "by_type": {},
                "by_experiment": {},
            }

        total = len(mistakes)
        reviewed = len([m for m in mistakes if m.reviewed])
        mastered = len([m for m in mistakes if m.mastered])

        # 按类型统计
        type_counter = Counter(m.mistake_type for m in mistakes)

        # 按实验统计
        exp_counter = Counter(m.experiment_id for m in mistakes)

        return {
            "total": total,
            "reviewed": reviewed,
            "mastered": mastered,
            "review_rate": round(reviewed / total * 100, 2) if total > 0 else 0,
            "mastery_rate": round(mastered / total * 100, 2) if total > 0 else 0,
            "by_type": dict(type_counter),
            "by_experiment": dict(exp_counter),
        }

    def get_review_suggestions(self, student_id: str, limit: int = 10) -> list[Mistake]:
        """
        获取复习建议

        Args:
            student_id: 学生ID
            limit: 返回数量

        Returns:
            建议复习的错误列表
        """
        mistakes = self.get_student_mistakes(student_id, reviewed=False)

        if not mistakes:
            # 如果没有未复习的，返回已复习但未掌握的
            mistakes = [
                m
                for m in self.get_student_mistakes(student_id)
                if m.reviewed and not m.mastered
            ]

        # 按时间排序，优先复习旧的错误
        mistakes.sort(key=lambda m: m.occurred_at)

        return mistakes[:limit]

    def create_review_session(
        self, student_id: str, mistake_ids: list[str]
    ) -> ReviewRecord:
        """
        创建复习会话

        Args:
            student_id: 学生ID
            mistake_ids: 错误ID列表

        Returns:
            复习记录
        """
        record_id = f"review_{student_id}_{datetime.now().timestamp()}"

        record = ReviewRecord(
            record_id=record_id,
            student_id=student_id,
            mistake_ids=mistake_ids,
            review_date=datetime.now().isoformat(),
            total_count=len(mistake_ids),
        )

        self._save_review_record(record)
        logger.info(f"创建复习会话: {record_id}")

        return record

    def update_review_session(self, record_id: str, student_id: str, **kwargs) -> bool:
        """
        更新复习会话

        Args:
            record_id: 记录ID
            student_id: 学生ID
            **kwargs: 更新字段

        Returns:
            是否成功
        """
        records = self.get_review_records(student_id)

        for record in records:
            if record.record_id == record_id:
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)

                self._save_review_record(record)
                logger.info(f"更新复习会话: {record_id}")
                return True

        return False

    def _save_review_record(self, record: ReviewRecord):
        """保存复习记录"""
        student_reviews_file = self.reviews_dir / f"{record.student_id}.json"

        # 加载现有记录
        records = self.get_review_records(record.student_id)

        # 更新或添加
        updated = False
        for i, r in enumerate(records):
            if r.record_id == record.record_id:
                records[i] = record
                updated = True
                break

        if not updated:
            records.append(record)

        # 保存
        try:
            with open(student_reviews_file, "w", encoding="utf-8") as f:
                json.dump(
                    [r.to_dict() for r in records], f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"保存复习记录失败: {e}")

    def get_review_records(self, student_id: str) -> list[ReviewRecord]:
        """获取复习记录"""
        student_reviews_file = self.reviews_dir / f"{student_id}.json"

        if not student_reviews_file.exists():
            return []

        try:
            with open(student_reviews_file, encoding="utf-8") as f:
                data = json.load(f)
                return [ReviewRecord.from_dict(r) for r in data]
        except Exception as e:
            logger.error(f"加载复习记录失败: {e}")
            return []

    def export_mistakes(
        self, student_id: str, output_path: Path, format: str = "json"
    ) -> bool:
        """
        导出错题

        Args:
            student_id: 学生ID
            output_path: 输出路径
            format: 格式（json/csv）

        Returns:
            是否成功
        """
        mistakes = self.get_student_mistakes(student_id)

        try:
            if format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(
                        [m.to_dict() for m in mistakes], f, indent=2, ensure_ascii=False
                    )
            elif format == "csv":
                import csv

                with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "错误ID",
                            "实验",
                            "类型",
                            "描述",
                            "正确答案",
                            "学生答案",
                            "发生时间",
                            "已复习",
                            "已掌握",
                        ]
                    )
                    for m in mistakes:
                        writer.writerow(
                            [
                                m.mistake_id,
                                m.experiment_name,
                                m.mistake_type,
                                m.mistake_description,
                                m.correct_answer,
                                m.student_answer,
                                m.occurred_at,
                                "是" if m.reviewed else "否",
                                "是" if m.mastered else "否",
                            ]
                        )

            logger.info(f"错题已导出: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出错题失败: {e}")
            return False


# 全局错题本实例
mistake_book = MistakeBook()
