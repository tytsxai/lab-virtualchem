"""
插件系统单元测试
"""

import tempfile
from pathlib import Path

import pytest

from src.plugins import PluginStatus, registry


class TestPluginRegistry:
    """测试插件注册表"""

    def test_plugin_registration(self):
        """测试插件注册"""
        plugins = registry.list_plugins()
        assert len(plugins) > 0, "应该有注册的插件"

        # 验证必需字段
        for name, info in plugins.items():
            assert info.name == name
            assert info.description
            assert info.module_name
            assert info.license
            assert isinstance(info.status, PluginStatus)

    def test_plugin_status(self):
        """测试插件状态"""
        # 至少应该尝试加载了所有插件
        plugins = registry.list_plugins()

        for _name, info in plugins.items():
            # 状态应该是已知的
            assert info.status in [
                PluginStatus.AVAILABLE,
                PluginStatus.NOT_INSTALLED,
                PluginStatus.ERROR,
                PluginStatus.DISABLED,
            ]

    def test_is_available(self):
        """测试可用性检查"""
        plugins = registry.list_plugins()

        for name in plugins:
            available = registry.is_available(name)
            assert isinstance(available, bool)

    def test_get_module(self):
        """测试获取模块"""
        # 获取一个可用的插件
        available_plugins = [
            name
            for name, info in registry.list_plugins().items()
            if info.status == PluginStatus.AVAILABLE
        ]

        if available_plugins:
            name = available_plugins[0]
            module = registry.get_module(name)
            assert module is not None

    def test_get_info(self):
        """测试获取插件信息"""
        plugins = registry.list_plugins()

        if plugins:
            name = list(plugins.keys())[0]
            info = registry.get_info(name)
            assert info is not None
            assert info.name == name


class TestChemRenderer:
    """测试化学渲染插件"""

    def test_import(self):
        """测试导入"""
        from src.plugins.chem_render import get_renderer

        renderer = get_renderer()
        assert renderer is not None

    def test_validate_smiles(self):
        """测试SMILES验证"""
        from src.plugins.chem_render import get_renderer

        renderer = get_renderer()

        # 测试有效SMILES
        valid, error = renderer.validate_smiles("CCO")

        if registry.is_available("rdkit"):
            assert valid is True
            assert error == ""
        else:
            # 回退行为
            pass

    def test_smiles_to_image(self):
        """测试SMILES转图片"""
        from src.plugins.chem_render import get_renderer

        renderer = get_renderer()

        img_data = renderer.smiles_to_image("CCO")
        assert img_data is not None
        assert isinstance(img_data, bytes)
        assert len(img_data) > 0

    def test_get_mol_properties(self):
        """测试获取分子属性"""
        from src.plugins.chem_render import get_renderer

        renderer = get_renderer()

        props = renderer.get_mol_properties("CCO")
        assert props is not None
        assert isinstance(props, dict)
        assert "molecular_weight" in props


class TestAdvancedPlotter:
    """测试高级图表插件"""

    def test_import(self):
        """测试导入"""
        from src.plugins.advanced_plots import get_plotter, is_available

        plotter = get_plotter()
        assert plotter is not None

        available = is_available()
        assert isinstance(available, bool)


class TestPDFExporter:
    """测试PDF导出插件"""

    def test_import(self):
        """测试导入"""
        from src.plugins.pdf_export import get_exporter, is_available

        exporter = get_exporter()
        assert exporter is not None

        available = is_available()
        assert isinstance(available, bool)

    def test_export(self):
        """测试导出功能"""
        from src.plugins.pdf_export import get_exporter

        exporter = get_exporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"

            content = [
                {"type": "heading", "data": "测试报告"},
                {"type": "text", "data": "这是测试内容"},
            ]

            success = exporter.export(output_path, content, method="auto", title="测试")

            # 应该成功（要么生成PDF，要么生成TXT）
            assert success is True or output_path.with_suffix(".txt").exists()


class TestThermoKinetics:
    """测试热力学计算插件"""

    def test_import(self):
        """测试导入"""
        from src.plugins.thermo_kinetics import get_calculator, is_available

        calc = get_calculator()
        assert calc is not None

        available = is_available()
        assert isinstance(available, bool)

    def test_calculate_equilibrium(self):
        """测试平衡计算"""
        from src.plugins.thermo_kinetics import get_calculator

        calc = get_calculator()

        result = calc.calculate_equilibrium(
            temperature=1000,
            pressure=101325,
            composition={"H2": 0.5, "O2": 0.25, "N2": 0.25},
        )

        # 应该返回结果（真实或回退）
        assert result is not None
        assert "temperature" in result


class TestMoleculeAnimator:
    """测试分子动画插件"""

    def test_import(self):
        """测试导入"""
        from src.plugins.molecule_animator import get_animator, is_available

        animator = get_animator()
        assert animator is not None

        available = is_available()
        assert isinstance(available, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
