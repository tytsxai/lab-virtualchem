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

        静态提取 Python 文件中的字典、列表等字面量数据结构。

        ChemLab 数据源来自外部仓库，不能在导入工具里执行其 Python 文件。
        这里仅解析模块顶层赋值，并使用 ast.literal_eval 接受纯字面量。
        """
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            logger.warning(f"Python 数据文件语法无效: {file_path}: {exc}")
            return []

        items: list[dict[str, Any]] = []
        for node in tree.body:
            assignment_name: str | None = None
            value_node: ast.AST | None = None

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assignment_name = target.id
                        value_node = node.value
                        break
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                assignment_name = node.target.id
                value_node = node.value

            if (
                not assignment_name
                or assignment_name.startswith("_")
                or value_node is None
            ):
                continue

            try:
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError):
                logger.debug("跳过非字面量 Python 赋值: %s", assignment_name)
                continue

            items.extend(self._coerce_literal_items(assignment_name, value))

        return items

    def _coerce_literal_items(self, name: str, value: Any) -> list[dict[str, Any]]:
        """Normalize literal Python data into knowledge item dictionaries."""
        if isinstance(value, dict):
            return [{"id": name, **value}]
        if not isinstance(value, list):
            return []

        items: list[dict[str, Any]] = []
        for index, entry in enumerate(value):
            if isinstance(entry, dict):
                if "id" in entry:
                    items.append(entry)
                else:
                    items.append({"id": f"{name}_{index}", **entry})
        return items

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

    def categorize_knowledge(
        self, items: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
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
