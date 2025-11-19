import pytest

from src.utils import unit_converter as unit_converter_module


@pytest.fixture
def converter_without_pint(monkeypatch):
    """Create a UnitConverter instance that behaves as if Pint is missing."""
    monkeypatch.setattr(unit_converter_module, "PINT_AVAILABLE", False)
    monkeypatch.setattr(unit_converter_module, "UnitRegistry", None)
    return unit_converter_module.UnitConverter()


@pytest.fixture
def converter_with_pint():
    """Require Pint and provide a ready-to-use UnitConverter."""
    pytest.importorskip("pint")
    converter = unit_converter_module.UnitConverter()
    if not converter.available:
        pytest.skip("UnitConverter is not configured with Pint")
    return converter


def test_convert_returns_original_value_without_pint(converter_without_pint):
    result = converter_without_pint.convert(5.0, "m", "cm")
    assert result == pytest.approx(5.0)


def test_format_quantity_without_pint(converter_without_pint):
    formatted = converter_without_pint.format_quantity(12.3456, "mL", precision=1)
    assert formatted == "12.3 mL"


def test_calculation_helpers_without_pint(converter_without_pint):
    assert converter_without_pint.calculate_molarity(0.01, 10.0) == pytest.approx(1.0)
    assert converter_without_pint.calculate_mass(2.0, 58.44) == pytest.approx(116.88)
    assert converter_without_pint.calculate_volume(0.5, 0.1) == pytest.approx(5.0)


def test_dilution_without_pint_supports_optional_v2(converter_without_pint):
    auto_v2 = converter_without_pint.dilution_calculation(2.0, 10.0, 0.5)
    assert auto_v2["V2"] == pytest.approx(40.0)

    manual_v2 = converter_without_pint.dilution_calculation(2.0, 10.0, 1.0, V2=15.0)
    assert manual_v2["V2"] == pytest.approx(15.0)


@pytest.mark.skipif(
    not unit_converter_module.PINT_AVAILABLE,
    reason="Pint is required for conversion tests",
)
def test_convert_volume_with_pint(converter_with_pint):
    result = converter_with_pint.volume_to_liter(2500.0, "mL")
    assert result == pytest.approx(2.5)


@pytest.mark.skipif(
    not unit_converter_module.PINT_AVAILABLE,
    reason="Pint is required for conversion tests",
)
def test_invalid_conversion_raises_value_error(converter_with_pint):
    with pytest.raises(ValueError):
        converter_with_pint.convert(1.0, "meter", "second")


@pytest.mark.skipif(
    not unit_converter_module.PINT_AVAILABLE,
    reason="Pint is required for validation tests",
)
def test_validate_unit_with_pint(converter_with_pint):
    assert converter_with_pint.validate_unit(1.0, "mol / liter", "mol / liter")
    assert not converter_with_pint.validate_unit(1.0, "mol", "meter")


@pytest.mark.skipif(
    not unit_converter_module.PINT_AVAILABLE,
    reason="Pint is required for dilution tests",
)
def test_dilution_with_pint_calculates_target_volume(converter_with_pint):
    result = converter_with_pint.dilution_calculation(
        1.0, 10.0, 0.5, C1_unit="M", V1_unit="mL", C2_unit="M", V2_unit="mL"
    )
    assert result["V2"] == pytest.approx(20.0)


@pytest.mark.skipif(
    not unit_converter_module.PINT_AVAILABLE,
    reason="Pint is required for chemistry helpers",
)
def test_calculate_mass_and_volume_with_pint(converter_with_pint):
    mass = converter_with_pint.calculate_mass(0.5, 58.44)
    assert mass == pytest.approx(29.22)

    volume = converter_with_pint.calculate_volume(0.1, 0.5)
    assert volume == pytest.approx(0.2)
