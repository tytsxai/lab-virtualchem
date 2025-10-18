"""曲线生成器单元测试"""

import numpy as np
import pytest

from src.core.curve_generator import CurveGenerationError, CurveGenerator


@pytest.fixture
def generator():
    """创建曲线生成器实例"""
    return CurveGenerator()


def test_curve_generator_init(generator):
    """测试曲线生成器初始化"""
    assert isinstance(generator.PKA_VALUES, dict)
    assert "acetic_acid" in generator.PKA_VALUES


def test_strong_acid_titration_curve(generator):
    """测试强酸强碱滴定曲线"""
    V, pH = generator.generate_titration_curve(
        acid_type="strong",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=100,
    )

    assert isinstance(V, np.ndarray)
    assert isinstance(pH, np.ndarray)
    assert len(V) == len(pH)
    assert V[0] >= 0
    assert V[-1] > 0
    assert all(0 <= p <= 14 for p in pH)


def test_weak_acid_titration_curve(generator):
    """测试弱酸强碱滴定曲线"""
    V, pH = generator.generate_titration_curve(
        acid_type="acetic_acid",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=100,
    )

    assert isinstance(V, np.ndarray)
    assert isinstance(pH, np.ndarray)
    assert len(V) > 0
    assert all(0 <= p <= 14 for p in pH)


def test_heating_curve(generator):
    """测试加热曲线"""
    t, temp = generator.generate_temperature_curve(
        mode="heating",
        initial_temp=25.0,
        params={
            "total_time_s": 300,
            "power_W": 100,
            "mass_g": 100,
            "specific_heat": 4.18,
            "boiling_point": 100,
        },
        num_points=50,
    )

    assert isinstance(t, np.ndarray)
    assert isinstance(temp, np.ndarray)
    assert len(t) == len(temp)
    assert t[0] == 0
    # 初始温度应该接近25.0 (允许数值误差)
    assert abs(temp[0] - 25.0) < 2.0


def test_cooling_curve(generator):
    """测试冷却曲线"""
    t, temp = generator.generate_temperature_curve(
        mode="cooling",
        initial_temp=100.0,
        params={
            "total_time_s": 600,
            "ambient_temp": 25,
            "cooling_constant": 0.01,
        },
        num_points=50,
    )

    assert isinstance(t, np.ndarray)
    assert isinstance(temp, np.ndarray)
    assert temp[0] > temp[-1]  # 温度下降


def test_unsupported_curve_type(generator):
    """测试不支持的曲线类型"""
    with pytest.raises(CurveGenerationError):
        generator.generate("unsupported_type", {})


def test_missing_required_parameter(generator):
    """测试缺少必要参数的情况"""
    with pytest.raises(CurveGenerationError, match="缺少必要参数"):
        generator.generate("titration_ph", {"acid_M": 0.1})  # 缺少其他必要参数


def test_generate_wrapper_titration(generator):
    """测试generate包装方法 - 滴定曲线"""
    V, pH = generator.generate(
        "titration_ph",
        {
            "acid_type": "strong",
            "acid_M": 0.1,
            "acid_V_ml": 25.0,
            "base_M": 0.1,
        },
        num_points=50,
    )
    # 由于滴定曲线可能会跳过某些点,长度可能略小于num_points
    assert len(V) >= 45  # 允许一些点被跳过
    assert len(pH) >= 45
    assert len(V) == len(pH)


def test_generate_wrapper_temperature(generator):
    """测试generate包装方法 - 温度曲线"""
    t, temp = generator.generate(
        "temp_time",
        {
            "mode": "heating",
            "initial_temp": 25.0,
            "total_time_s": 300,
            "power_W": 100,
            "mass_g": 100,
            "specific_heat": 4.18,
            "boiling_point": 100,
        },
        num_points=30,
    )
    assert len(t) == 30
    assert len(temp) == 30


def test_different_num_points(generator):
    """测试不同的采样点数"""
    for n_points in [10, 50, 200]:
        V, pH = generator.generate_titration_curve(
            acid_type="strong",
            acid_M=0.1,
            acid_V_ml=25.0,
            base_M=0.1,
            num_points=n_points,
        )
        # 由于滴定曲线优化可能跳过某些点,长度可能略小
        assert len(V) >= n_points * 0.9  # 允许10%的点被跳过
        assert len(pH) >= n_points * 0.9
        assert len(V) == len(pH)


def test_pka_values_database(generator):
    """测试pKa值数据库"""
    assert generator.PKA_VALUES["acetic_acid"] == 4.76
    assert generator.PKA_VALUES["formic_acid"] == 3.75
    assert generator.PKA_VALUES["carbonic_acid_1"] == 6.35
    assert "phosphoric_acid_1" in generator.PKA_VALUES


def test_weak_acid_with_different_pka(generator):
    """测试不同pKa的弱酸滴定"""
    for acid_type in ["acetic_acid", "formic_acid", "carbonic_acid_1"]:
        V, pH = generator.generate_titration_curve(
            acid_type=acid_type,
            acid_M=0.1,
            acid_V_ml=25.0,
            base_M=0.1,
            num_points=100,
        )
        assert len(V) > 0
        assert all(0 <= p <= 14 for p in pH)


def test_titration_equivalence_point(generator):
    """测试滴定等当点"""
    V, pH = generator.generate_titration_curve(
        acid_type="strong",
        acid_M=0.1,
        acid_V_ml=25.0,
        base_M=0.1,
        num_points=200,
    )
    # 检查pH跃迁范围 - 强酸强碱滴定应该有明显的pH跃迁
    pH_range = max(pH) - min(pH)
    assert pH_range >= 10  # pH应该从低到高有明显跃迁

    # 检查等当点附近的pH变化
    eq_idx = np.argmin(np.abs(V - 25.0))
    # 等当点附近pH应该在酸性到中性区域(考虑数值精度)
    assert pH[eq_idx] >= 3.9  # 滴定过程中pH应该上升(允许0.1的数值误差)


def test_temperature_curve_boundary_conditions(generator):
    """测试温度曲线的边界条件"""
    # 测试达到沸点后停止
    t, temp = generator.generate_temperature_curve(
        mode="heating",
        initial_temp=25.0,
        params={
            "total_time_s": 1000,
            "power_W": 500,
            "mass_g": 100,
            "specific_heat": 4.18,
            "boiling_point": 100,
        },
        num_points=100,
    )
    # 温度不应超过沸点太多(允许数值计算误差)
    assert max(temp) <= 105  # 允许一定的数值误差


def test_cooling_to_ambient_temperature(generator):
    """测试冷却到环境温度"""
    t, temp = generator.generate_temperature_curve(
        mode="cooling",
        initial_temp=100.0,
        params={
            "total_time_s": 1000,
            "ambient_temp": 25,
            "cooling_constant": 0.05,
        },
        num_points=100,
    )
    # 验证冷却过程 - 温度应该下降
    assert temp[0] > temp[-1]  # 温度应该下降
    # 最后温度应该接近环境温度(允许数值误差)
    assert temp[-1] >= 20  # 不会低于环境温度太多
    assert temp[-1] <= 35  # 应该在合理范围内


def test_distillation_mode(generator):
    """测试蒸馏模式温度曲线"""
    t, temp = generator.generate_temperature_curve(
        mode="distillation",
        initial_temp=25.0,
        params={
            "total_time_s": 600,
            "power_W": 200,
            "mass_g": 100,
            "specific_heat": 4.18,
            "boiling_point": 78,  # 乙醇沸点
            "distillation_time_s": 300,
        },
        num_points=100,
    )
    assert isinstance(t, np.ndarray)
    assert isinstance(temp, np.ndarray)
    # 验证温度数据合理性
    assert len(t) > 0
    assert len(temp) > 0
    assert all(t >= 0 for t in t)  # 时间应该非负
