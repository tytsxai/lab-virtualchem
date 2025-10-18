"""化学知识解析器

从 chemlab 分子数据库中提取化学知识。
"""

import ast
import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class KnowledgeParser:
    """化学知识解析器

    从 chemlab 的分子数据、数据库文件中提取化学知识。
    """

    def __init__(self):
        """初始化解析器"""
        self.molecules: list[dict[str, Any]] = []
        self.reagents: list[dict[str, Any]] = []

    def parse_file(self, file_path: Path) -> list[dict[str, Any]]:
        """解析数据文件

        Args:
            file_path: 文件路径

        Returns:
            知识条目列表
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".json":
                return self._parse_json(file_path)
            elif suffix in [".yaml", ".yml"]:
                return self._parse_yaml(file_path)
            elif suffix == ".py":
                return self._parse_python_data(file_path)
            else:
                logger.warning(f"不支持的文件格式: {suffix}")
                return []
        except Exception as e:
            logger.error(f"❌ 解析失败 {file_path}: {e}")
            return []

    def _parse_json(self, file_path: Path) -> list[dict[str, Any]]:
        """解析 JSON 文件"""
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # 如果是列表,直接返回
        if isinstance(data, list):
            return data

        # 如果是字典,转为列表
        if isinstance(data, dict):
            return [{"id": k, **v} for k, v in data.items()]

        return []

    def _parse_yaml(self, file_path: Path) -> list[dict[str, Any]]:
        """解析 YAML 文件"""
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return [{"id": k, **v} for k, v in data.items()]

        return []

    def _parse_python_data(self, file_path: Path) -> list[dict[str, Any]]:
        """解析 Python 数据文件

        提取 Python 文件中的字典、列表等数据结构。
        """
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        items = []

        try:
            # 尝试执行并提取全局变量
            local_vars: dict[str, Any] = {}
            exec(content, {}, local_vars)

            # 提取字典和列表
            for name, value in local_vars.items():
                if isinstance(value, (dict, list)) and not name.startswith("_"):
                    if isinstance(value, dict):
                        items.append({"id": name, **value})
                    else:
                        items.extend(value if isinstance(value, list) else [value])

        except Exception as e:
            logger.warning(f"执行 Python 文件失败: {e}")

            # 尝试静态分析
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                        # 提取字典赋值
                        items.append(self._extract_dict_from_ast(node.value))
            except Exception:  # noqa: BLE001
                pass

        return items

    def _extract_dict_from_ast(self, node: ast.Dict) -> dict[str, Any]:
        """从 AST 节点提取字典数据"""
        result = {}

        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant):
                key_str = str(key.value)
                if isinstance(value, ast.Constant):
                    result[key_str] = value.value
                elif isinstance(value, ast.List):
                    result[key_str] = [elem.value for elem in value.elts if isinstance(elem, ast.Constant)]

        return result

    def extract_molecule_info(self, data: dict[str, Any]) -> dict[str, Any]:
        """提取分子信息

        Args:
            data: 原始数据

        Returns:
            规范化的分子信息
        """
        # 映射常见字段
        field_mapping = {
            "name": ["name", "molecule_name", "title"],
            "formula": ["formula", "molecular_formula", "chem_formula"],
            "cas": ["cas", "cas_number", "cas_no"],
            "molecular_weight": ["mw", "molecular_weight", "mol_weight", "weight"],
            "density": ["density", "rho"],
            "boiling_point": ["bp", "boiling_point", "boiling_temp"],
            "melting_point": ["mp", "melting_point", "melting_temp"],
        }

        molecule = {}

        for target_key, possible_keys in field_mapping.items():
            for key in possible_keys:
                if key in data:
                    molecule[target_key] = data[key]
                    break

        # 保留其他字段
        for key, value in data.items():
            if key not in molecule:
                molecule[key] = value

        return molecule

    def categorize_knowledge(self, items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """分类知识条目

        Args:
            items: 知识条目列表

        Returns:
            分类后的字典 {类型: [条目列表]}
        """
        categories: dict[str, list[dict[str, Any]]] = {
            "reagent": [],
            "apparatus": [],
            "procedure": [],
            "general": [],
        }

        for item in items:
            # 根据字段判断类型
            if "formula" in item or "cas" in item or "molecular_weight" in item:
                categories["reagent"].append(self.extract_molecule_info(item))
            elif "apparatus" in str(item).lower() or "equipment" in str(item).lower():
                categories["apparatus"].append(item)
            elif "procedure" in str(item).lower() or "protocol" in str(item).lower():
                categories["procedure"].append(item)
            else:
                categories["general"].append(item)

        return categories

    def parse_batch(self, file_paths: list[Path]) -> dict[str, list[dict[str, Any]]]:
        """批量解析文件

        Args:
            file_paths: 文件路径列表

        Returns:
            分类后的知识库数据
        """
        all_items = []

        for file_path in file_paths:
            items = self.parse_file(file_path)
            all_items.extend(items)
            logger.info(f"✅ {file_path.name}: {len(items)} 条数据")

        # 分类
        categorized = self.categorize_knowledge(all_items)

        logger.info("\n📊 数据统计:")
        for category, items in categorized.items():
            logger.info(f"  {category}: {len(items)} 条")

        return categorized


# 测试代码
if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from src import CONFIG_PATH
    from src.fetcher import ChemLabFetcher

    logging.basicConfig(level=logging.INFO)

    # 获取数据
    fetcher = ChemLabFetcher(CONFIG_PATH)
    fetcher.clone_or_update()
    data_files = fetcher.list_molecule_data()[:10]  # 测试前10个

    # 解析
    parser = KnowledgeParser()
    knowledge = parser.parse_batch(data_files)

    # 输出示例
    for category, items in knowledge.items():
        if items:
            print(f"\n{category} 示例:")
            print(json.dumps(items[0], indent=2, ensure_ascii=False))
