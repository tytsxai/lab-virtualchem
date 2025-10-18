"""
安全检查集成测试

测试实验安全功能：
- 温度监控
- 试剂兼容性
- 操作规范检查
- 应急处理
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestTemperatureSafety:
    """温度安全测试"""

    @pytest.fixture
    def setup_heating_experiment(self):
        """设置加热实验"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()

        yield experiment

        # 清理
        if experiment.state == "running":
            experiment.abort()

    def test_temperature_limit_enforcement(self, setup_heating_experiment):
        """测试温度限制执行"""
        experiment = setup_heating_experiment

        # 正常温度应该可以
        result = experiment.heat(temperature=80, duration=30)
        assert result is True

        # 超出安全温度应该失败
        with pytest.raises(ValueError, match="温度.*安全"):
            experiment.heat(temperature=250, duration=30)

    def test_temperature_monitoring(self, setup_heating_experiment):
        """测试温度监控"""
        experiment = setup_heating_experiment

        # 开始加热
        experiment.heat(temperature=100, duration=60)

        # 检查温度是否被记录
        current_temp = experiment.get_current_temperature()
        assert current_temp is not None
        assert 0 <= current_temp <= 150

    def test_overheat_alert(self, setup_heating_experiment):
        """测试过热警报"""
        experiment = setup_heating_experiment

        # 模拟温度异常升高
        experiment.set_temperature(95)

        # 检查是否触发警报
        alerts = experiment.get_safety_alerts()
        assert any("温度" in alert for alert in alerts)

    def test_cooling_requirement(self, setup_heating_experiment):
        """测试冷却要求"""
        experiment = setup_heating_experiment

        # 加热
        experiment.heat(temperature=100, duration=30)

        # 尝试在未冷却时进行下一步应该警告
        with pytest.warns(UserWarning, match="冷却"):
            experiment.add_reagent("water")

        # 冷却后应该可以
        experiment.cool_down()
        result = experiment.add_reagent("water")
        assert result is True


class TestReagentSafety:
    """试剂安全测试"""

    @pytest.fixture
    def setup_reagent_experiment(self):
        """设置试剂实验"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="general")
        experiment.prepare()
        experiment.start()

        return experiment

    def test_incompatible_reagents(self, setup_reagent_experiment):
        """测试不兼容试剂检查"""
        experiment = setup_reagent_experiment

        # 添加酸
        experiment.add_reagent("concentrated_HCl")

        # 尝试添加不兼容的碱应该警告
        with pytest.warns(UserWarning, match="兼容"):
            experiment.add_reagent("concentrated_NaOH")

    def test_dangerous_combinations(self, setup_reagent_experiment):
        """测试危险组合"""
        experiment = setup_reagent_experiment

        # 强酸 + 强氧化剂 = 危险
        experiment.add_reagent("H2SO4")

        with pytest.raises(ValueError, match="危险"):
            experiment.add_reagent("KMnO4")

    def test_reagent_amount_limits(self, setup_reagent_experiment):
        """测试试剂用量限制"""
        experiment = setup_reagent_experiment

        # 超量应该失败
        with pytest.raises(ValueError, match="用量"):
            experiment.add_reagent("HCl", amount=500)  # mL

        # 正常用量应该可以
        result = experiment.add_reagent("HCl", amount=50)
        assert result is True

    def test_toxic_reagent_warning(self, setup_reagent_experiment):
        """测试有毒试剂警告"""
        experiment = setup_reagent_experiment

        # 使用有毒试剂应该产生警告
        with pytest.warns(UserWarning, match="有毒|毒性"):
            experiment.add_reagent("mercury_compound")

        # 检查安全提示
        safety_tips = experiment.get_safety_tips()
        assert any("通风" in tip or "防护" in tip for tip in safety_tips)


class TestOperationSafety:
    """操作安全测试"""

    def test_required_protection_equipment(self):
        """测试必需的防护装备"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()

        # 检查是否提示防护装备
        protection = experiment.get_required_protection()

        assert "goggles" in protection  # 护目镜
        assert "gloves" in protection  # 手套
        assert "lab_coat" in protection  # 实验服

    def test_ventilation_requirement(self):
        """测试通风要求"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()

        # 使用挥发性试剂
        with pytest.warns(UserWarning, match="通风"):
            experiment.add_reagent("volatile_solvent")

        # 检查通风状态
        if hasattr(experiment, "ventilation_status"):
            assert experiment.ventilation_status == "required"

    def test_emergency_stop(self):
        """测试紧急停止"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()

        # 加热中
        experiment.heat(temperature=100, duration=60)

        # 紧急停止
        experiment.emergency_stop()

        # 检查状态
        assert experiment.state == "emergency_stopped"

        # 检查加热是否停止
        if hasattr(experiment, "heating"):
            assert experiment.heating is False

    def test_spill_response(self):
        """测试溢出响应"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="general")
        experiment.prepare()
        experiment.start()

        # 模拟溢出
        experiment.report_incident("spill", details="酸溅出")

        # 检查应急指导
        response = experiment.get_emergency_response("spill")

        assert response is not None
        assert any(keyword in response.lower() for keyword in ["中和", "稀释", "清理"])


class TestComplianceChecks:
    """合规性检查测试"""

    def test_procedure_order_validation(self):
        """测试操作顺序验证"""
        from src.models.experiment import Experiment

        experiment = Experiment(experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 错误的操作顺序应该警告
        with pytest.warns(UserWarning, match="顺序|步骤"):
            # 未润洗就使用滴定管
            experiment.use_burette(rinse=False)

    def test_waste_disposal_reminder(self):
        """测试废液处理提醒"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="general")
        experiment.prepare()
        experiment.start()

        # 产生废液
        experiment.add_reagent("HCl")
        experiment.add_reagent("NaOH")
        experiment.neutralize()

        # 完成时应该提醒废液处理
        experiment.complete()

        reminders = experiment.get_completion_reminders()
        assert any("废液" in r or "处理" in r for r in reminders)

    def test_equipment_check_before_start(self):
        """测试实验前设备检查"""
        from src.models.experiment import Experiment

        experiment = Experiment(experiment_type="titration")

        # 准备时应该检查设备
        checklist = experiment.get_equipment_checklist()

        assert "burette" in checklist
        assert "flask" in checklist

        # 未通过检查不应该开始
        experiment.equipment_checked = False

        with pytest.raises(RuntimeError, match="设备检查"):
            experiment.start()


class TestSafetyLogger:
    """安全日志测试"""

    def test_safety_event_logging(self):
        """测试安全事件记录"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()

        # 触发安全事件
        with pytest.raises(ValueError):
            experiment.heat(temperature=300, duration=30)

        # 检查安全日志
        safety_log = experiment.get_safety_log()

        assert len(safety_log) > 0
        assert any("温度" in event.get("message", "") for event in safety_log)

    def test_warning_accumulation(self):
        """测试警告累积"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="general")
        experiment.prepare()
        experiment.start()

        # 触发多个警告
        with pytest.warns():
            experiment.add_reagent("concentrated_acid", protection=False)

        with pytest.warns():
            experiment.heat(temperature=90, ventilation=False)

        # 检查累积的警告
        warnings = experiment.get_all_warnings()
        assert len(warnings) >= 2

    def test_safety_score_calculation(self):
        """测试安全评分计算"""
        from src.models.experiment import Experiment

        experiment = Experiment(experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 正确操作
        experiment.check_equipment()
        experiment.wear_protection(["goggles", "gloves", "lab_coat"])
        experiment.complete()

        # 计算安全评分
        score = experiment.calculate_safety_score()

        assert 0 <= score <= 100
        assert score >= 80  # 正确操作应该有高分


class TestEmergencyProcedures:
    """应急程序测试"""

    def test_fire_response(self):
        """测试火灾响应"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()
        experiment.heat(temperature=100, duration=60)

        # 报告火灾
        response = experiment.handle_emergency("fire")

        assert "灭火" in response or "fire" in response.lower()
        assert experiment.state == "emergency_stopped"

    def test_chemical_exposure(self):
        """测试化学品接触"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="general")
        experiment.prepare()
        experiment.start()

        # 报告皮肤接触
        response = experiment.handle_emergency("skin_contact", chemical="HCl")

        assert "冲洗" in response or "水" in response
        assert "15分钟" in response or "15" in response

    def test_equipment_malfunction(self):
        """测试设备故障"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="synthesis")
        experiment.prepare()
        experiment.start()

        # 报告设备故障
        experiment.report_malfunction("heating_mantle", issue="过热")

        # 应该自动停止
        assert experiment.state in ["paused", "emergency_stopped"]

        # 获取故障处理指导
        guidance = experiment.get_malfunction_guidance("heating_mantle")
        assert guidance is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
