"""转换器单元测试"""

import unittest

from src.converters.card_converter import CardConverter
from src.converters.template_converter import TemplateConverter


class TestTemplateConverter(unittest.TestCase):
    """实验模板转换器测试"""

    def setUp(self):
        """初始化"""
        self.converter = TemplateConverter()

    def test_convert_basic_experiment(self):
        """测试基本实验转换"""
        data = {
            "source_file": "test_exp.py",
            "title": "Test Experiment",
            "description": "A test experiment",
            "steps": ["Step 1", "Step 2", "Step 3"],
            "code_info": {"imports": ["chemlab"], "molecules": ["water"], "operations": ["render"], "visualizations": []},
        }

        template = self.converter.convert(data)

        self.assertIn("id", template)
        self.assertIn("title", template)
        self.assertIn("steps", template)
        self.assertEqual(len(template["steps"]), 3)
        self.assertEqual(template["level"], "basic")

    def test_generate_id(self):
        """测试 ID 生成"""
        data = {"source_file": "my_experiment.py"}
        exp_id = self.converter._generate_id(data)

        self.assertIn("my_experiment", exp_id)
        self.assertTrue(exp_id.replace("_", "").isalnum())


class TestCardConverter(unittest.TestCase):
    """知识卡片转换器测试"""

    def setUp(self):
        """初始化"""
        self.converter = CardConverter()

    def test_convert_reagent(self):
        """测试试剂转换"""
        data = {
            "name": "Water",
            "formula": "H2O",
            "cas": "7732-18-5",
            "molecular_weight": 18.015,
            "density": 1.0,
            "boiling_point": 100,
        }

        card = self.converter.convert_reagent(data)

        self.assertEqual(card["type"], "reagent")
        self.assertEqual(card["title"], "Water")
        self.assertEqual(card["formula"], "H2O")
        self.assertEqual(card["cas"], "7732-18-5")
        self.assertIsNotNone(card["properties"])

    def test_extract_properties(self):
        """测试物理性质提取"""
        data = {"density": 1.5, "boiling_point": 150, "mp": 50, "mw": 100}

        props = self.converter._extract_properties(data)

        self.assertEqual(props["density"], 1.5)
        self.assertEqual(props["boiling_point"], 150)
        self.assertEqual(props["melting_point"], 50)
        self.assertEqual(props["molecular_weight"], 100)

    def test_extract_hazards(self):
        """测试危害信息提取"""
        data = {"hazard": "Toxic substance", "content": "This is a corrosive material"}

        hazards = self.converter._extract_hazards(data)

        self.assertGreater(len(hazards), 0)
        # 应该检测到 toxic 和 corrosive
        types = [h["type"] for h in hazards]
        self.assertIn("toxic", types)
        self.assertIn("corrosive", types)


if __name__ == "__main__":
    unittest.main()
