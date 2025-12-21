"""
Safety checker utilities.

This module provides a lightweight, dependency-free implementation of the
`ISafetyChecker` interface used across the project. It focuses on:
- Basic temperature safety checks
- Reagent mixing compatibility checks
- Protection equipment requirements
- Dangerous operation detection and warning generation
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any

from src.interfaces.experiment import ISafetyChecker


@dataclass(frozen=True)
class SafetyWarning:
    """Structured warning used by SafetyChecker APIs."""

    code: str
    message: str
    severity: str = "warning"  # info|warning|danger


class SafetyChecker(ISafetyChecker):
    """
    Minimal safety checker implementation.

    The checker returns `(ok, message)` for the interface methods and provides
    helper APIs returning structured warnings for richer callers.
    """

    DEFAULT_MAX_TEMPERATURE_C = 200.0
    ABSOLUTE_MAX_TEMPERATURE_C = 250.0

    _DANGEROUS_MIXES: set[frozenset[str]] = {
        frozenset({"H2SO4", "KMnO4"}),
        frozenset({"h2so4_conc", "h2o"}),
    }

    _WARNING_MIXES: set[frozenset[str]] = {
        frozenset({"concentrated_HCl", "concentrated_NaOH"}),
        frozenset({"HCl", "NaOH"}),
    }

    _REQUIRED_PROTECTION_BY_OPERATION: dict[str, set[str]] = {
        "heating": {"goggles", "lab_coat"},
        "handle_corrosive": {"goggles", "gloves", "lab_coat"},
        "handle_toxic": {"mask", "gloves", "goggles"},
        "mixing": {"goggles", "gloves"},
    }

    _EQUIPMENT_DISPLAY_NAMES: dict[str, str] = {
        "goggles": "护目镜",
        "gloves": "防护手套",
        "lab_coat": "实验服",
        "mask": "口罩/面罩",
    }

    def check_temperature(self, temperature: float, reagents: list[str]) -> tuple[bool, str]:
        warnings = self.check_temperature_warnings(temperature, reagents=reagents)
        if not warnings:
            return True, ""
        most_severe = max(warnings, key=self._severity_rank)
        return most_severe.severity != "danger", most_severe.message

    def check_mixing(self, reagent1: str, reagent2: str) -> tuple[bool, str]:
        warnings = self.check_mixing_warnings(reagent1, reagent2)
        if not warnings:
            return True, ""
        most_severe = max(warnings, key=self._severity_rank)
        return most_severe.severity != "danger", most_severe.message

    def check_protection(self, operation: str, protection: list[str]) -> tuple[bool, str]:
        warnings = self.check_protection_warnings(operation, protection)
        if not warnings:
            return True, ""
        most_severe = max(warnings, key=self._severity_rank)
        return most_severe.severity != "danger", most_severe.message

    def detect_dangerous_operations(
        self, operation: str, *, context: dict[str, Any] | None = None
    ) -> list[SafetyWarning]:
        normalized = (operation or "").strip().lower()
        context = context or {}
        warnings: list[SafetyWarning] = []

        if normalized in {"heat", "heating"}:
            warnings.extend(
                self.check_temperature_warnings(
                    context.get("temperature"), reagents=context.get("reagents") or []
                )
            )
            warnings.extend(
                self.check_protection_warnings("heating", context.get("protection") or [])
            )

        if normalized in {"mix", "mixing"}:
            mixing = context.get("mixing")
            if isinstance(mixing, tuple) and len(mixing) == 2:
                warnings.extend(self.check_mixing_warnings(mixing[0], mixing[1]))
            warnings.extend(
                self.check_protection_warnings("mixing", context.get("protection") or [])
            )

        if normalized in {"handle_corrosive", "handle_toxic"}:
            warnings.extend(
                self.check_protection_warnings(normalized, context.get("protection") or [])
            )

        if normalized in {"clear_all_records", "wipe_database"}:
            warnings.append(
                SafetyWarning(
                    code="dangerous_destructive_operation",
                    message="该操作具有破坏性，执行前请确认已备份并具备必要权限。",
                    severity="danger",
                )
            )

        return self._dedupe_warnings(warnings)

    def check_temperature_warnings(
        self, temperature: Any, *, reagents: list[str] | None = None
    ) -> list[SafetyWarning]:
        reagents = reagents or []
        if temperature is None:
            return [
                SafetyWarning(
                    code="invalid_temperature",
                    message="温度值缺失，无法进行安全检查。",
                    severity="danger",
                )
            ]
        if not isinstance(temperature, (int, float)):
            return [
                SafetyWarning(
                    code="invalid_temperature",
                    message="温度值类型无效，无法进行安全检查。",
                    severity="danger",
                )
            ]
        if isinstance(temperature, float) and isnan(temperature):
            return [
                SafetyWarning(
                    code="invalid_temperature",
                    message="温度值为 NaN，无法进行安全检查。",
                    severity="danger",
                )
            ]

        warnings: list[SafetyWarning] = []
        if temperature >= self.ABSOLUTE_MAX_TEMPERATURE_C:
            warnings.append(
                SafetyWarning(
                    code="temperature_too_high",
                    message=f"温度 {temperature}°C 超出安全上限（{self.ABSOLUTE_MAX_TEMPERATURE_C}°C）。",
                    severity="danger",
                )
            )
        elif temperature > self.DEFAULT_MAX_TEMPERATURE_C:
            warnings.append(
                SafetyWarning(
                    code="high_temperature",
                    message=f"温度 {temperature}°C 较高，请注意防护与控温。",
                    severity="warning",
                )
            )

        lower_limit_reagents = {"volatile_solvent", "flammable_solvent"}
        if set(reagents) & lower_limit_reagents and temperature > 120:
            warnings.append(
                SafetyWarning(
                    code="volatile_reagent_temperature",
                    message="涉及挥发/易燃试剂时温度过高，请加强通风并降低温度。",
                    severity="danger",
                )
            )

        return self._dedupe_warnings(warnings)

    def check_mixing_warnings(self, reagent1: str, reagent2: str) -> list[SafetyWarning]:
        r1 = (reagent1 or "").strip()
        r2 = (reagent2 or "").strip()
        if not r1 or not r2:
            return [
                SafetyWarning(
                    code="invalid_reagents",
                    message="试剂信息不完整，无法进行混合安全检查。",
                    severity="danger",
                )
            ]
        if r1 == r2:
            return [
                SafetyWarning(
                    code="same_reagent",
                    message="两种试剂相同，混合检查无意义。",
                    severity="info",
                )
            ]

        key = frozenset({r1, r2})
        if key in self._DANGEROUS_MIXES:
            if key == frozenset({"h2so4_conc", "h2o"}):
                return [
                    SafetyWarning(
                        code="h2so4_water_mix",
                        message="禁止将水加入浓硫酸，应将浓硫酸缓慢加入水中。",
                        severity="danger",
                    )
                ]
            return [
                SafetyWarning(
                    code="dangerous_mix",
                    message="该试剂组合具有高风险，禁止直接混合。",
                    severity="danger",
                )
            ]
        if key in self._WARNING_MIXES:
            return [
                SafetyWarning(
                    code="exothermic_mix",
                    message="该混合可能放热/产生飞溅，请缓慢加入并做好防护。",
                    severity="warning",
                )
            ]
        return []

    def check_protection_warnings(
        self, operation: str, protection: list[str] | None
    ) -> list[SafetyWarning]:
        normalized = (operation or "").strip().lower()
        required = self._REQUIRED_PROTECTION_BY_OPERATION.get(normalized)
        if not required:
            return []

        protection_set = {p for p in (protection or []) if isinstance(p, str) and p.strip()}
        missing = sorted(required - protection_set)
        if not missing:
            return []

        missing_names = [self._EQUIPMENT_DISPLAY_NAMES.get(x, x) for x in missing]
        return [
            SafetyWarning(
                code="missing_protection",
                message=f"缺少必要防护用品：{', '.join(missing_names)}。",
                severity="warning",
            )
        ]

    @staticmethod
    def _severity_rank(w: SafetyWarning) -> int:
        return {"info": 0, "warning": 1, "danger": 2}.get(w.severity, 1)

    @staticmethod
    def _dedupe_warnings(warnings: list[SafetyWarning]) -> list[SafetyWarning]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[SafetyWarning] = []
        for w in warnings:
            key = (w.code, w.message, w.severity)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(w)
        return deduped

