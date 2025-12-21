"""
Score Calculator

提供独立的评分计算逻辑，支持多种评分规则与边界/错误处理。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Iterable

from src.core.rule_validator import EvaluationError, RuleValidator

logger = logging.getLogger(__name__)


class ScoreCalculationError(Exception):
    """评分计算失败（输入或规则非法）。"""


@dataclass(frozen=True)
class ScoreResult:
    total: int
    details: dict[str, Any]


class ScoreCalculator:
    """
    评分计算器

    支持规则类型：
    - conditional（默认）：{"when": <expr>, "then": <int>}
    - range：{"type": "range", "field": <name>, "ranges": [{"min":..,"max":..,"score":..}], "default": <int>}
    - clamp_total：{"type": "clamp_total", "min": <int|None>, "max": <int|None>}

    strict=False 时，单条规则出错将被记录在 details 中并跳过（总分不变）。
    strict=True 时，遇到非法规则/计算错误会抛出 ScoreCalculationError。
    """

    def __init__(self, validator: RuleValidator | None = None):
        self._validator = validator or RuleValidator()

    def calculate(
        self,
        rules: Iterable[dict[str, Any]] | None,
        context: dict[str, Any] | None = None,
        *,
        strict: bool = False,
    ) -> ScoreResult:
        if rules is None:
            return ScoreResult(total=0, details={})
        if context is None:
            context = {}

        total = 0
        details: dict[str, Any] = {}

        for i, rule in enumerate(list(rules)):
            rule_id = f"rule_{i}"
            try:
                if not isinstance(rule, dict):
                    raise ScoreCalculationError("rule 必须是 dict")

                rule_type = rule.get("type", "conditional")
                if rule_type == "conditional":
                    delta, item = self._apply_conditional_rule(rule, context)
                    total += delta
                    details[rule_id] = item
                elif rule_type == "range":
                    delta, item = self._apply_range_rule(rule, context)
                    total += delta
                    details[rule_id] = item
                elif rule_type == "clamp_total":
                    total, item = self._apply_clamp_total_rule(rule, total)
                    details[rule_id] = item
                else:
                    raise ScoreCalculationError(f"未知规则类型: {rule_type}")
            except (
                ScoreCalculationError,
                EvaluationError,
                TypeError,
                ValueError,
                KeyError,
            ) as e:
                logger.error(f"评分规则 {rule_id} 计算失败 - {type(e).__name__}: {e}")
                if strict:
                    raise ScoreCalculationError(str(e)) from e
                details[rule_id] = {"error": str(e), "score": 0}
            except Exception as e:
                logger.error(
                    f"评分规则 {rule_id} 出现未预期错误 ({type(e).__name__}): {e}",
                    exc_info=True,
                )
                if strict:
                    raise ScoreCalculationError(str(e)) from e
                details[rule_id] = {"error": str(e), "score": 0}

        return ScoreResult(total=int(total), details=details)

    def _apply_conditional_rule(
        self, rule: dict[str, Any], context: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        condition = rule.get("when", "")
        score = int(rule.get("then", 0))

        passed = self._validator.evaluate_expression(condition, context)
        if passed:
            return score, {
                "type": "conditional",
                "condition": condition,
                "score": score,
                "passed": True,
            }
        return 0, {
            "type": "conditional",
            "condition": condition,
            "score": 0,
            "passed": False,
        }

    def _apply_range_rule(
        self, rule: dict[str, Any], context: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        field = rule.get("field")
        if not field or not isinstance(field, str):
            raise ScoreCalculationError("range 规则缺少 field")
        if field not in context:
            raise ScoreCalculationError(f"上下文缺少字段: {field}")

        value = float(context[field])
        ranges = rule.get("ranges", [])
        if not isinstance(ranges, list):
            raise ScoreCalculationError("ranges 必须是 list")

        matched_score: int | None = None
        matched_range: dict[str, Any] | None = None
        for item in ranges:
            if not isinstance(item, dict):
                continue
            min_val = item.get("min")
            max_val = item.get("max")
            score = int(item.get("score", 0))
            if min_val is not None and value < float(min_val):
                continue
            if max_val is not None and value > float(max_val):
                continue
            matched_score = score
            matched_range = {"min": min_val, "max": max_val}
            break

        if matched_score is None:
            matched_score = int(rule.get("default", 0))
            return matched_score, {
                "type": "range",
                "field": field,
                "value": value,
                "matched": False,
                "score": matched_score,
            }

        return matched_score, {
            "type": "range",
            "field": field,
            "value": value,
            "matched": True,
            "range": matched_range,
            "score": matched_score,
        }

    def _apply_clamp_total_rule(
        self, rule: dict[str, Any], total: int
    ) -> tuple[int, dict[str, Any]]:
        min_total = rule.get("min")
        max_total = rule.get("max")

        new_total = total
        if min_total is not None:
            new_total = max(int(min_total), new_total)
        if max_total is not None:
            new_total = min(int(max_total), new_total)

        return new_total, {
            "type": "clamp_total",
            "before": int(total),
            "after": int(new_total),
            "min": min_total,
            "max": max_total,
        }


def calculate_score(
    rules: Iterable[dict[str, Any]] | None,
    context: dict[str, Any] | None = None,
    *,
    strict: bool = False,
    validator: RuleValidator | None = None,
) -> ScoreResult:
    """函数式接口：计算总分与详情。"""
    return ScoreCalculator(validator=validator).calculate(rules, context, strict=strict)

