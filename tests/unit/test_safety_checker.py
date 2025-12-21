from __future__ import annotations

import math

import pytest

safety_checker = pytest.importorskip("src.core.safety_checker")

SafetyChecker = safety_checker.SafetyChecker
SafetyWarning = safety_checker.SafetyWarning


@pytest.fixture()
def checker() -> SafetyChecker:
    return SafetyChecker()


class TestTemperatureSafety:
    def test_temperature_ok_under_default_limit(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_temperature(temperature=80, reagents=[])
        assert ok is True
        assert msg == ""

    def test_temperature_warn_between_default_and_absolute(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_temperature(temperature=220, reagents=[])
        assert ok is True
        assert "较高" in msg

    def test_temperature_danger_at_absolute_limit(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_temperature(temperature=250, reagents=[])
        assert ok is False
        assert "超出安全上限" in msg

    def test_temperature_danger_with_volatile_reagent_stricter_limit(
        self, checker: SafetyChecker
    ) -> None:
        warnings = checker.check_temperature_warnings(
            121, reagents=["volatile_solvent", "water"]
        )
        assert any(w.code == "volatile_reagent_temperature" for w in warnings)
        assert any(w.severity == "danger" for w in warnings)

    @pytest.mark.parametrize("bad", [None, "100", object()])
    def test_temperature_invalid_types_are_danger(self, checker: SafetyChecker, bad) -> None:
        warnings = checker.check_temperature_warnings(bad, reagents=[])
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_temperature"
        assert warnings[0].severity == "danger"

    def test_temperature_nan_is_danger(self, checker: SafetyChecker) -> None:
        warnings = checker.check_temperature_warnings(float("nan"), reagents=[])
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_temperature"
        assert warnings[0].severity == "danger"

    def test_temperature_nan_matches_math_nan(self, checker: SafetyChecker) -> None:
        value = float("nan")
        assert math.isnan(value)
        ok, msg = checker.check_temperature(value, reagents=[])
        assert ok is False
        assert "NaN" in msg


class TestMixingSafety:
    def test_mixing_dangerous_pair_blocks(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_mixing("H2SO4", "KMnO4")
        assert ok is False
        assert "禁止" in msg or "高风险" in msg

    def test_mixing_h2so4_conc_and_water_special_message(self, checker: SafetyChecker) -> None:
        warnings = checker.check_mixing_warnings("h2so4_conc", "h2o")
        assert len(warnings) == 1
        assert warnings[0].code == "h2so4_water_mix"
        assert warnings[0].severity == "danger"
        assert "浓硫酸" in warnings[0].message

    def test_mixing_warning_pair_is_allowed_but_warns(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_mixing("HCl", "NaOH")
        assert ok is True
        assert "放热" in msg or "飞溅" in msg

    def test_mixing_same_reagent_is_info(self, checker: SafetyChecker) -> None:
        warnings = checker.check_mixing_warnings("HCl", "HCl")
        assert len(warnings) == 1
        assert warnings[0].severity == "info"
        ok, msg = checker.check_mixing("HCl", "HCl")
        assert ok is True
        assert msg != ""

    @pytest.mark.parametrize(
        "r1,r2",
        [
            ("", "HCl"),
            ("HCl", ""),
            (None, "HCl"),
            ("HCl", None),
        ],
    )
    def test_mixing_missing_reagent_is_danger(self, checker: SafetyChecker, r1, r2) -> None:
        warnings = checker.check_mixing_warnings(r1, r2)
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_reagents"
        assert warnings[0].severity == "danger"


class TestProtectionSafety:
    def test_protection_unknown_operation_is_ok(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_protection("unknown_operation", ["goggles"])
        assert ok is True
        assert msg == ""

    def test_protection_missing_items_warns(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_protection("handle_corrosive", ["goggles"])
        assert ok is True  # warning but not danger
        assert "缺少" in msg
        assert "防护手套" in msg or "实验服" in msg

    def test_protection_sufficient_is_ok(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_protection(
            "handle_corrosive", ["goggles", "gloves", "lab_coat"]
        )
        assert ok is True
        assert msg == ""

    def test_protection_ignores_empty_strings(self, checker: SafetyChecker) -> None:
        warnings = checker.check_protection_warnings("mixing", ["", "goggles", " "])
        assert len(warnings) == 1
        assert warnings[0].code == "missing_protection"


class TestDangerousOperationDetection:
    def test_detect_dangerous_operation_destructive(self, checker: SafetyChecker) -> None:
        warnings = checker.detect_dangerous_operations("clear_all_records")
        assert any(w.code == "dangerous_destructive_operation" for w in warnings)
        assert any(w.severity == "danger" for w in warnings)

    def test_detect_heating_combines_temperature_and_protection(
        self, checker: SafetyChecker
    ) -> None:
        warnings = checker.detect_dangerous_operations(
            "heating",
            context={"temperature": 260, "reagents": [], "protection": ["goggles"]},
        )
        codes = {w.code for w in warnings}
        assert "temperature_too_high" in codes
        assert "missing_protection" in codes  # should require lab_coat too

    def test_detect_mixing_dedupes_warnings(self, checker: SafetyChecker) -> None:
        warnings = checker.detect_dangerous_operations(
            "mixing",
            context={
                "mixing": ("HCl", "NaOH"),
                "protection": ["goggles"],  # missing gloves
            },
        )
        assert len(warnings) == len({(w.code, w.message, w.severity) for w in warnings})


class TestWarningRankingAndTypes:
    def test_more_severe_message_selected(self, checker: SafetyChecker) -> None:
        ok, msg = checker.check_temperature(temperature=251, reagents=["volatile_solvent"])
        assert ok is False
        assert msg  # returns the most severe message

    def test_warning_is_dataclass(self) -> None:
        w = SafetyWarning(code="x", message="m", severity="info")
        assert w.code == "x"
        assert w.message == "m"
        assert w.severity == "info"
