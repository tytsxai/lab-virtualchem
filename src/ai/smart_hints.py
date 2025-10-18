"""
智能提示模块
提供上下文相关的智能提示和帮助信息
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HintType(Enum):
    """提示类型"""

    PROCEDURAL = "procedural"  # 操作步骤提示
    CONCEPTUAL = "conceptual"  # 概念解释提示
    SAFETY = "safety"  # 安全注意事项
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    OPTIMIZATION = "optimization"  # 优化建议
    GENERAL = "general"  # 通用提示


class HintLevel(Enum):
    """提示级别"""

    SUBTLE = "subtle"  # 微妙提示
    DIRECT = "direct"  # 直接提示
    DETAILED = "detailed"  # 详细说明


@dataclass
class Hint:
    """提示"""

    hint_id: str
    hint_type: HintType
    level: HintLevel
    content: str
    context: dict[str, Any] | None = None
    priority: int = 0  # 优先级，数字越大越重要

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "hint_id": self.hint_id,
            "hint_type": self.hint_type.value,
            "level": self.level.value,
            "content": self.content,
            "context": self.context or {},
            "priority": self.priority,
        }


class SmartHints:
    """智能提示系统"""

    def __init__(self):
        """初始化智能提示系统"""
        self.hints_database: dict[str, list[Hint]] = {}
        self._load_default_hints()

    def _load_default_hints(self):
        """加载默认提示"""
        # 实验步骤提示
        self.add_hint(
            Hint(
                hint_id="exp_start_01",
                hint_type=HintType.PROCEDURAL,
                level=HintLevel.DIRECT,
                content="开始实验前，请确保已阅读实验目标和安全须知",
                context={"stage": "start"},
                priority=10,
            )
        )

        self.add_hint(
            Hint(
                hint_id="reagent_select_01",
                hint_type=HintType.PROCEDURAL,
                level=HintLevel.SUBTLE,
                content="选择试剂时，请注意试剂的浓度和用量",
                context={"stage": "reagent_selection"},
                priority=5,
            )
        )

        # 安全提示
        self.add_hint(
            Hint(
                hint_id="safety_01",
                hint_type=HintType.SAFETY,
                level=HintLevel.DIRECT,
                content="处理强酸强碱时，务必佩戴防护眼镜和手套",
                context={"hazard": "corrosive"},
                priority=15,
            )
        )

        self.add_hint(
            Hint(
                hint_id="safety_02",
                hint_type=HintType.SAFETY,
                level=HintLevel.DIRECT,
                content="加热操作时，请使用石棉网，避免直接加热",
                context={"operation": "heating"},
                priority=12,
            )
        )

        # 概念提示
        self.add_hint(
            Hint(
                hint_id="concept_ph_01",
                hint_type=HintType.CONCEPTUAL,
                level=HintLevel.DETAILED,
                content="pH值表示溶液的酸碱性，pH < 7 为酸性，pH > 7 为碱性，pH = 7 为中性",
                context={"topic": "acid_base"},
                priority=7,
            )
        )

        # 故障排除提示
        self.add_hint(
            Hint(
                hint_id="trouble_01",
                hint_type=HintType.TROUBLESHOOTING,
                level=HintLevel.DETAILED,
                content="如果滴定终点不明显，可以尝试使用更合适的指示剂",
                context={"problem": "endpoint_unclear"},
                priority=8,
            )
        )

        # 优化建议
        self.add_hint(
            Hint(
                hint_id="optimize_01",
                hint_type=HintType.OPTIMIZATION,
                level=HintLevel.SUBTLE,
                content="建议多次测量取平均值，以提高实验结果的准确性",
                context={"stage": "measurement"},
                priority=6,
            )
        )

    def add_hint(self, hint: Hint):
        """添加提示"""
        key = self._get_context_key(hint.context or {})
        if key not in self.hints_database:
            self.hints_database[key] = []
        self.hints_database[key].append(hint)
        logger.debug(f"添加提示: {hint.hint_id} (key: {key})")

    def get_hints(
        self,
        context: dict[str, Any],
        hint_type: HintType | None = None,
        level: HintLevel | None = None,
        max_count: int = 3,
    ) -> list[Hint]:
        """获取相关提示

        Args:
            context: 上下文信息
            hint_type: 提示类型过滤
            level: 提示级别过滤
            max_count: 最大返回数量

        Returns:
            提示列表，按优先级排序
        """
        # 查找匹配的提示
        matching_hints = []

        # 精确匹配
        exact_key = self._get_context_key(context)
        if exact_key in self.hints_database:
            matching_hints.extend(self.hints_database[exact_key])

        # 部分匹配
        for key, hints in self.hints_database.items():
            if key != exact_key and self._context_matches(context, key):
                matching_hints.extend(hints)

        # 应用过滤器
        if hint_type:
            matching_hints = [h for h in matching_hints if h.hint_type == hint_type]

        if level:
            matching_hints = [h for h in matching_hints if h.level == level]

        # 按优先级排序
        matching_hints.sort(key=lambda h: h.priority, reverse=True)

        # 限制数量
        return matching_hints[:max_count]

    def get_hint_by_id(self, hint_id: str) -> Hint | None:
        """根据ID获取提示"""
        for hints in self.hints_database.values():
            for hint in hints:
                if hint.hint_id == hint_id:
                    return hint
        return None

    def _get_context_key(self, context: dict[str, Any]) -> str:
        """生成上下文键"""
        if not context:
            return "general"

        # 使用主要上下文字段作为键
        key_parts = []
        for key in ["stage", "topic", "operation", "hazard", "problem"]:
            if key in context:
                key_parts.append(f"{key}:{context[key]}")

        return "|".join(key_parts) if key_parts else "general"

    def _context_matches(self, context: dict[str, Any], key: str) -> bool:
        """检查上下文是否匹配"""
        if key == "general":
            return True

        key_parts = key.split("|")
        for part in key_parts:
            if ":" in part:
                k, v = part.split(":", 1)
                if context.get(k) == v:
                    return True

        return False

    def clear_hints(self):
        """清除所有自定义提示（保留默认提示）"""
        self.hints_database.clear()
        self._load_default_hints()


if __name__ == "__main__":
    # 示例使用
    smart_hints = SmartHints()

    # 获取实验开始时的提示
    print("=== 实验开始阶段 ===")
    hints = smart_hints.get_hints(context={"stage": "start"})
    for hint in hints:
        print(f"[{hint.hint_type.value}] {hint.content}")

    print("\n=== 试剂选择阶段 ===")
    hints = smart_hints.get_hints(context={"stage": "reagent_selection"})
    for hint in hints:
        print(f"[{hint.hint_type.value}] {hint.content}")

    print("\n=== 处理腐蚀性试剂 ===")
    hints = smart_hints.get_hints(context={"hazard": "corrosive"}, hint_type=HintType.SAFETY)
    for hint in hints:
        print(f"[{hint.hint_type.value}] {hint.content}")

    print("\n=== 滴定终点不明显 ===")
    hints = smart_hints.get_hints(context={"problem": "endpoint_unclear"})
    for hint in hints:
        print(f"[{hint.hint_type.value}] {hint.content}")
