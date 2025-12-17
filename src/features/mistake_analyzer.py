"""
错题分析器

提供错题的深度分析功能：
- 错误模式识别
- 薄弱知识点分析
- 学习建议生成
- 错题趋势分析
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MistakeAnalyzer:
    """错题分析器"""

    def __init__(self, mistake_book=None):
        """
        初始化错题分析器

        Args:
            mistake_book: 错题本实例
        """
        from .mistake_book import mistake_book as default_book

        self.mistake_book = mistake_book or default_book

        # 知识点关键词映射
        self.knowledge_keywords = {
            "酸碱中和": ["酸", "碱", "中和", "pH", "指示剂", "滴定"],
            "氧化还原": ["氧化", "还原", "电子转移", "化合价", "氧化剂", "还原剂"],
            "溶液配制": ["溶液", "浓度", "溶质", "溶剂", "稀释", "配制"],
            "仪器使用": ["仪器", "滴定管", "移液管", "容量瓶", "烧杯", "锥形瓶"],
            "实验操作": ["操作", "步骤", "顺序", "方法", "技巧"],
            "安全规范": ["安全", "防护", "危险", "有毒", "腐蚀", "易燃"],
            "数据处理": ["计算", "数据", "公式", "误差", "精确度", "有效数字"],
            "现象观察": ["现象", "颜色", "沉淀", "气体", "变化", "观察"],
        }

        logger.info("错题分析器初始化完成")

    def analyze_student_weaknesses(self, student_id: str) -> dict:
        """
        分析学生薄弱点

        Args:
            student_id: 学生ID

        Returns:
            薄弱点分析结果
        """
        mistakes = self.mistake_book.get_student_mistakes(student_id)

        if not mistakes:
            return {
                "student_id": student_id,
                "total_mistakes": 0,
                "message": "暂无错误数据",
            }

        # 按类型统计
        type_counter = Counter(m.mistake_type for m in mistakes)

        # 识别知识点薄弱环节
        knowledge_weaknesses = self._identify_knowledge_gaps(mistakes)

        # 找出高频错误
        frequent_mistakes = self._find_frequent_mistakes(mistakes)

        # 分析错误趋势
        trend = self._analyze_mistake_trend(mistakes)

        # 生成薄弱点列表（按错误数量排序）
        weakness_list = []
        for mistake_type, count in type_counter.most_common():
            weakness_list.append(
                {
                    "type": mistake_type,
                    "count": count,
                    "percentage": round(count / len(mistakes) * 100, 2),
                    "severity": self._get_severity(count, len(mistakes)),
                }
            )

        return {
            "student_id": student_id,
            "total_mistakes": len(mistakes),
            "weaknesses_by_type": weakness_list,
            "knowledge_gaps": knowledge_weaknesses,
            "frequent_mistakes": frequent_mistakes,
            "trend": trend,
            "recommendations": self._generate_recommendations(
                weakness_list, knowledge_weaknesses
            ),
        }

    def _identify_knowledge_gaps(self, mistakes: list) -> list[dict]:
        """识别知识点薄弱环节"""
        knowledge_scores = defaultdict(int)

        for mistake in mistakes:
            description = mistake.mistake_description.lower()

            # 匹配知识点关键词
            for knowledge, keywords in self.knowledge_keywords.items():
                for keyword in keywords:
                    if keyword in description:
                        knowledge_scores[knowledge] += 1
                        break

        # 转换为列表并排序
        gaps = [
            {
                "knowledge_point": knowledge,
                "mistake_count": count,
                "priority": "高" if count >= 5 else "中" if count >= 3 else "低",
            }
            for knowledge, count in knowledge_scores.items()
        ]

        gaps.sort(key=lambda x: x["mistake_count"], reverse=True)

        return gaps

    def _find_frequent_mistakes(self, mistakes: list, threshold: int = 2) -> list[dict]:
        """找出高频错误"""
        description_counter = Counter(m.mistake_description for m in mistakes)

        frequent = []
        for description, count in description_counter.items():
            if count >= threshold:
                # 获取该错误的示例
                examples = [m for m in mistakes if m.mistake_description == description]

                frequent.append(
                    {
                        "description": description,
                        "occurrence_count": count,
                        "experiments": list({m.experiment_name for m in examples}),
                        "first_occurred": min(m.occurred_at for m in examples),
                        "last_occurred": max(m.occurred_at for m in examples),
                    }
                )

        frequent.sort(key=lambda x: x["occurrence_count"], reverse=True)

        return frequent

    def _analyze_mistake_trend(self, mistakes: list) -> dict:
        """分析错误趋势"""
        if not mistakes:
            return {"trend": "无数据"}

        # 按时间排序
        sorted_mistakes = sorted(mistakes, key=lambda m: m.occurred_at)

        # 分成两半比较
        mid = len(sorted_mistakes) // 2
        if mid == 0:
            return {"trend": "数据不足", "message": "需要更多数据来分析趋势"}

        first_half = sorted_mistakes[:mid]
        second_half = sorted_mistakes[mid:]

        first_count = len(first_half)
        second_count = len(second_half)

        # 计算变化率（使用三元运算符）
        change_rate = (
            (second_count - first_count) / first_count * 100 if first_count > 0 else 0
        )

        # 判断趋势
        if change_rate < -20:
            trend = "显著改善"
            emoji = "📈"
        elif change_rate < -5:
            trend = "有所改善"
            emoji = "📊"
        elif change_rate > 20:
            trend = "需要关注"
            emoji = "⚠️"
        elif change_rate > 5:
            trend = "略有增加"
            emoji = "📉"
        else:
            trend = "基本稳定"
            emoji = "➡️"

        return {
            "trend": trend,
            "emoji": emoji,
            "change_rate": round(change_rate, 2),
            "first_period_count": first_count,
            "second_period_count": second_count,
            "message": f"错误数量{trend}（变化率：{change_rate:+.1f}%）",
        }

    def _get_severity(self, count: int, total: int) -> str:
        """获取严重程度"""
        percentage = count / total * 100

        if percentage >= 40:
            return "严重"
        elif percentage >= 25:
            return "较重"
        elif percentage >= 15:
            return "中等"
        else:
            return "较轻"

    def _generate_recommendations(
        self, weaknesses: list[dict], knowledge_gaps: list[dict]
    ) -> list[str]:
        """生成学习建议"""
        recommendations = []

        # 基于薄弱类型的建议
        for weakness in weaknesses[:3]:  # 只针对前3个薄弱点
            wtype = weakness["type"]

            if wtype == "operation":
                recommendations.append(
                    "🔧 操作错误较多，建议：\n"
                    "  - 复习实验操作视频\n"
                    "  - 多次练习标准操作流程\n"
                    "  - 注意操作细节和规范"
                )
            elif wtype == "calculation":
                recommendations.append(
                    "🧮 计算错误较多，建议：\n"
                    "  - 复习相关化学计算公式\n"
                    "  - 加强数学计算能力\n"
                    "  - 注意单位换算和有效数字"
                )
            elif wtype == "concept":
                recommendations.append(
                    "📚 概念理解不够，建议：\n"
                    "  - 系统复习相关理论知识\n"
                    "  - 理解概念的本质和应用\n"
                    "  - 做好概念辨析和总结"
                )
            elif wtype == "safety":
                recommendations.append(
                    "⚠️ 安全意识需加强，建议：\n"
                    "  - 学习化学实验安全规范\n"
                    "  - 了解化学品的危险性\n"
                    "  - 掌握应急处理方法"
                )

        # 基于知识点薄弱的建议
        for gap in knowledge_gaps[:2]:  # 只针对前2个知识点
            knowledge = gap["knowledge_point"]
            priority = gap["priority"]

            recommendations.append(
                f"📌 {knowledge}知识点薄弱（优先级：{priority}）\n"
                "  建议重点复习相关内容，多做针对性练习"
            )

        # 通用建议
        if len(weaknesses) > 5:
            recommendations.append(
                "💡 错误类型较多，建议：\n"
                "  - 制定系统的复习计划\n"
                "  - 每天复习1-2个错题\n"
                "  - 定期进行错题回顾"
            )

        return recommendations

    def compare_with_class(self, student_id: str, class_students: list[str]) -> dict:
        """
        与班级平均水平比较

        Args:
            student_id: 学生ID
            class_students: 班级学生ID列表

        Returns:
            比较结果
        """
        student_mistakes = self.mistake_book.get_student_mistakes(student_id)
        student_count = len(student_mistakes)

        # 计算班级平均
        class_mistake_counts = []
        for sid in class_students:
            if sid != student_id:
                mistakes = self.mistake_book.get_student_mistakes(sid)
                class_mistake_counts.append(len(mistakes))

        if not class_mistake_counts:
            return {"student_id": student_id, "message": "无班级数据可比较"}

        class_avg = sum(class_mistake_counts) / len(class_mistake_counts)

        # 计算差异
        difference = student_count - class_avg
        percentage_diff = (difference / class_avg * 100) if class_avg > 0 else 0

        # 判断水平
        if percentage_diff < -30:
            level = "优秀"
            emoji = "🌟"
        elif percentage_diff < -10:
            level = "良好"
            emoji = "👍"
        elif percentage_diff < 10:
            level = "中等"
            emoji = "📊"
        elif percentage_diff < 30:
            level = "待提高"
            emoji = "📈"
        else:
            level = "需加强"
            emoji = "⚠️"

        return {
            "student_id": student_id,
            "student_mistake_count": student_count,
            "class_average": round(class_avg, 2),
            "difference": round(difference, 2),
            "percentage_difference": round(percentage_diff, 2),
            "level": level,
            "emoji": emoji,
            "ranking": sorted(class_mistake_counts + [student_count]).index(
                student_count
            )
            + 1,
            "total_students": len(class_students),
        }

    def predict_next_mistakes(self, student_id: str, experiment_id: str) -> list[str]:
        """
        预测可能的错误

        Args:
            student_id: 学生ID
            experiment_id: 实验ID

        Returns:
            可能的错误列表
        """
        # 获取该学生的历史错误
        all_mistakes = self.mistake_book.get_student_mistakes(student_id)

        # 获取该实验的错误
        exp_mistakes = [m for m in all_mistakes if m.experiment_id == experiment_id]

        if not exp_mistakes:
            # 如果没有该实验的错误，返回该学生的常见错误类型
            type_counter = Counter(m.mistake_type for m in all_mistakes)
            common_types = [t for t, _ in type_counter.most_common(3)]

            return [f"注意避免{mistake_type}类错误" for mistake_type in common_types]

        # 如果有该实验的错误，返回具体建议
        predictions = []

        # 找出该实验的高频错误
        desc_counter = Counter(m.mistake_description for m in exp_mistakes)

        for desc, count in desc_counter.most_common(3):
            if count >= 2:
                predictions.append(f"⚠️ 容易出错：{desc}")

        return predictions

    def generate_review_plan(self, student_id: str, days: int = 7) -> dict:
        """
        生成复习计划

        Args:
            student_id: 学生ID
            days: 计划天数

        Returns:
            复习计划
        """
        mistakes = self.mistake_book.get_student_mistakes(student_id, reviewed=False)

        if not mistakes:
            return {"student_id": student_id, "message": "无需复习的错题", "plan": []}

        # 按优先级排序（旧的错误优先）
        mistakes.sort(key=lambda m: m.occurred_at)

        # 分配到每天
        mistakes_per_day = len(mistakes) // days + (
            1 if len(mistakes) % days > 0 else 0
        )

        plan = []
        for day in range(days):
            start_idx = day * mistakes_per_day
            end_idx = min(start_idx + mistakes_per_day, len(mistakes))

            day_mistakes = mistakes[start_idx:end_idx]

            if day_mistakes:
                plan.append(
                    {
                        "day": day + 1,
                        "date": (datetime.now() + timedelta(days=day)).strftime(
                            "%Y-%m-%d"
                        ),
                        "mistake_count": len(day_mistakes),
                        "mistake_ids": [m.mistake_id for m in day_mistakes],
                        "experiments": list({m.experiment_name for m in day_mistakes}),
                        "estimated_time": len(day_mistakes) * 5,  # 每个错题估计5分钟
                    }
                )

        return {
            "student_id": student_id,
            "total_mistakes": len(mistakes),
            "plan_days": days,
            "daily_average": mistakes_per_day,
            "plan": plan,
        }


# 全局错题分析器实例
mistake_analyzer = MistakeAnalyzer()
