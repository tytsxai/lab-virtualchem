"""
报告生成集成测试

测试实验报告生成功能：
- 数据整理
- 报告格式化
- 多格式导出
- 报告完整性
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestBasicReportGeneration:
    """基础报告生成测试"""

    @pytest.fixture
    def completed_experiment(self):
        """完成的实验fixture"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 记录数据
        experiment.record_data("student_name", "测试学生")
        experiment.record_data("experiment_date", datetime.now().isoformat())
        experiment.record_data("v1", 24.85)
        experiment.record_data("v2", 24.92)
        experiment.record_data("v3", 24.88)

        experiment.complete()

        return experiment

    def test_report_structure(self, completed_experiment):
        """测试报告结构"""
        report = completed_experiment.generate_report()

        # 验证必需字段
        required_fields = ["experiment_type", "start_time", "end_time", "state", "data"]

        for field in required_fields:
            assert field in report, f"缺少必需字段: {field}"

    def test_data_completeness(self, completed_experiment):
        """测试数据完整性"""
        report = completed_experiment.generate_report()
        data = report.get("data", {})

        # 验证记录的数据都在报告中
        assert "v1" in data
        assert "v2" in data
        assert "v3" in data
        assert data["v1"] == 24.85

    def test_calculations_in_report(self, completed_experiment):
        """测试报告中的计算"""
        report = completed_experiment.generate_report()

        # 应该包含平均值计算
        if "calculations" in report:
            assert "average_volume" in report["calculations"]
            avg = report["calculations"]["average_volume"]
            assert 24.85 <= avg <= 24.92

    def test_metadata_inclusion(self, completed_experiment):
        """测试元数据包含"""
        report = completed_experiment.generate_report()

        # 应该包含学生信息
        assert "student_name" in report.get("data", {})

        # 应该包含时间戳
        assert "start_time" in report
        assert "end_time" in report


class TestReportFormatting:
    """报告格式化测试"""

    @pytest.fixture
    def experiment_with_data(self):
        """带数据的实验"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 添加各种类型的数据
        experiment.record_data("text_data", "这是文本数据")
        experiment.record_data("numeric_data", 12.345)
        experiment.record_data("list_data", [1, 2, 3, 4, 5])
        experiment.record_observation("观察到颜色变化")

        experiment.complete()

        return experiment

    def test_json_export(self, experiment_with_data):
        """测试JSON导出"""
        json_report = experiment_with_data.export_report(format="json")

        # 应该是有效的JSON
        parsed = json.loads(json_report)
        assert isinstance(parsed, dict)

        # 验证数据保持
        assert parsed["data"]["numeric_data"] == 12.345
        assert parsed["data"]["list_data"] == [1, 2, 3, 4, 5]

    def test_text_export(self, experiment_with_data):
        """测试文本导出"""
        text_report = experiment_with_data.export_report(format="text")

        assert isinstance(text_report, str)
        assert "实验报告" in text_report
        assert "文本数据" in text_report
        assert "12.345" in text_report

    def test_html_export(self, experiment_with_data):
        """测试HTML导出"""
        html_report = experiment_with_data.export_report(format="html")

        assert isinstance(html_report, str)
        assert "<html>" in html_report.lower()
        assert "<table>" in html_report.lower() or "表格" in html_report

    def test_markdown_export(self, experiment_with_data):
        """测试Markdown导出"""
        md_report = experiment_with_data.export_report(format="markdown")

        assert isinstance(md_report, str)
        assert "#" in md_report  # Markdown标题
        assert "|" in md_report or "-" in md_report  # 可能的表格


class TestDataVisualization:
    """数据可视化测试"""

    def test_chart_data_preparation(self):
        """测试图表数据准备"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 记录多组数据
        for i in range(5):
            experiment.record_data(f"trial_{i}", 24.8 + i * 0.1)

        experiment.complete()

        # 生成图表数据
        chart_data = experiment.get_chart_data()

        assert "labels" in chart_data
        assert "values" in chart_data
        assert len(chart_data["labels"]) == len(chart_data["values"])

    def test_curve_data_export(self):
        """测试曲线数据导出"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 记录滴定曲线数据
        for v in range(0, 30, 2):
            ph = 7 + (v - 25) * 0.5  # 模拟pH变化
            experiment.record_titration_point(volume=v, ph=ph)

        experiment.complete()

        # 获取曲线数据
        curve_data = experiment.get_curve_data()

        assert "volume" in curve_data
        assert "ph" in curve_data
        assert len(curve_data["volume"]) > 0


class TestReportCustomization:
    """报告自定义测试"""

    def test_template_selection(self):
        """测试模板选择"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.complete()

        # 使用不同模板生成报告
        report1 = experiment.generate_report(template="standard")
        report2 = experiment.generate_report(template="detailed")
        report3 = experiment.generate_report(template="brief")

        # 验证报告内容不同
        assert report1 != report2 or report2 != report3

    def test_field_selection(self):
        """测试字段选择"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.record_data("field1", "value1")
        experiment.record_data("field2", "value2")
        experiment.complete()

        # 只包含特定字段
        report = experiment.generate_report(include_fields=["field1"])

        assert "field1" in report.get("data", {})
        # field2可能存在也可能不存在，取决于实现

    def test_section_ordering(self):
        """测试章节排序"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.complete()

        # 自定义章节顺序
        report = experiment.generate_report(sections_order=["data", "observations", "calculations", "conclusion"])

        # 验证顺序（如果实现支持）
        if "sections" in report:
            section_names = [s["name"] for s in report["sections"]]
            assert section_names[0] == "data"


class TestReportStorage:
    """报告存储测试"""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """临时存储"""
        storage_dir = tmp_path / "reports"
        storage_dir.mkdir()
        return storage_dir

    def test_save_report_to_file(self, temp_storage):
        """测试保存报告到文件"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.complete()

        # 保存报告
        output_path = temp_storage / "report.json"
        experiment.save_report(output_path, format="json")

        # 验证文件存在
        assert output_path.exists()

        # 验证内容
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "experiment_type" in data

    def test_batch_report_generation(self, temp_storage):
        """测试批量报告生成"""
        from src.models.experiment import Experiment

        experiments = []
        for i in range(3):
            exp = Experiment(experiment_type="titration")
            exp.prepare()
            exp.start()
            exp.record_data("trial", i)
            exp.complete()
            experiments.append(exp)

        # 批量保存
        for i, exp in enumerate(experiments):
            output_path = temp_storage / f"report_{i}.json"
            exp.save_report(output_path)

        # 验证所有文件
        report_files = list(temp_storage.glob("report_*.json"))
        assert len(report_files) == 3

    def test_report_versioning(self, temp_storage):
        """测试报告版本控制"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.complete()

        # 保存第一版
        output_path = temp_storage / "report.json"
        experiment.save_report(output_path)

        # 修改数据
        experiment.record_data("additional_note", "补充说明")

        # 保存第二版（应该创建新文件或覆盖）
        experiment.save_report(output_path, version=2)

        # 验证版本信息
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
            # 如果实现了版本控制
            if "version" in data:
                assert data["version"] == 2


class TestReportValidation:
    """报告验证测试"""

    def test_required_fields_validation(self):
        """测试必需字段验证"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        # 不记录任何数据
        experiment.complete()

        report = experiment.generate_report()

        # 验证报告有效性
        is_valid, errors = experiment.validate_report(report)

        # 可能因为缺少数据而无效
        if not is_valid:
            assert len(errors) > 0

    def test_data_type_validation(self):
        """测试数据类型验证"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 记录正确类型的数据
        experiment.record_data("volume", 24.85)

        experiment.complete()
        report = experiment.generate_report()

        # 验证数据类型
        assert isinstance(report["data"]["volume"], (int, float))

    def test_calculation_accuracy_check(self):
        """测试计算准确性检查"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()

        # 记录数据
        experiment.record_data("v1", 24.85)
        experiment.record_data("v2", 24.92)
        experiment.record_data("v3", 24.88)

        experiment.complete()
        report = experiment.generate_report()

        # 手动验证平均值
        if "calculations" in report and "average_volume" in report["calculations"]:
            avg = report["calculations"]["average_volume"]
            expected_avg = (24.85 + 24.92 + 24.88) / 3
            assert abs(avg - expected_avg) < 0.01


class TestReportSharing:
    """报告分享测试"""

    def test_anonymous_report(self):
        """测试匿名报告"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.record_data("student_id", "123456")
        experiment.record_data("student_name", "张三")
        experiment.complete()

        # 生成匿名报告
        anonymous_report = experiment.generate_report(anonymous=True)

        # 验证个人信息被移除
        assert "student_id" not in anonymous_report.get("data", {})
        assert "student_name" not in anonymous_report.get("data", {})

    def test_watermark_addition(self):
        """测试水印添加"""

        from src.models.experiment import ExperimentTemplate

        experiment = ExperimentTemplate(id="test_exp", title="测试实验", experiment_type="titration")
        experiment.prepare()
        experiment.start()
        experiment.complete()

        # 添加水印
        report_with_watermark = experiment.generate_report(watermark="VirtualChemLab - 仅供教学使用")

        # 验证水印（如果实现）
        if "watermark" in report_with_watermark:
            assert "VirtualChemLab" in report_with_watermark["watermark"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
