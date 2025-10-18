"""实验数据解析器

从 chemlab 示例代码中提取实验信息。
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentParser:
    """实验数据解析器

    解析 chemlab 的 Python 示例文件,提取实验相关信息。
    """

    def __init__(self):
        """初始化解析器"""
        self.experiments: list[dict[str, Any]] = []

    def parse_file(self, file_path: Path) -> dict[str, Any] | None:
        """解析单个示例文件

        Args:
            file_path: 文件路径

        Returns:
            实验数据字典,失败返回 None
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 提取文档字符串
            docstring = self._extract_docstring(content)

            # 提取代码结构
            code_info = self._analyze_code(content)

            # 构建实验数据
            experiment = {
                "source_file": str(file_path.name),
                "title": self._extract_title(docstring, file_path),
                "description": docstring or "",
                "code_info": code_info,
                "raw_content": content,
            }

            logger.info(f"✅ 解析成功: {experiment['title']}")
            return experiment

        except Exception as e:
            logger.error(f"❌ 解析失败 {file_path}: {e}")
            return None

    def _extract_docstring(self, content: str) -> str | None:
        """提取模块文档字符串"""
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            return docstring
        except Exception:  # noqa: BLE001
            # 尝试正则提取
            match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            match = re.search(r"'''(.*?)'''", content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return None

    def _extract_title(self, docstring: str | None, file_path: Path) -> str:
        """提取标题"""
        if docstring:
            # 取文档字符串第一行
            first_line = docstring.split("\n")[0].strip()
            if first_line:
                return first_line

        # 使用文件名作为标题
        title = file_path.stem.replace("_", " ").title()
        return title

    def _analyze_code(self, content: str) -> dict[str, Any]:
        """分析代码结构

        提取实验步骤、使用的分子、操作等信息。
        """
        info = {
            "imports": [],
            "molecules": [],
            "operations": [],
            "visualizations": [],
        }

        try:
            tree = ast.parse(content)

            # 提取导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    info["imports"].append(node.module)

            # 提取分子相关代码 (简化版)
            # 寻找 Molecule, System 等关键字
            molecule_patterns = [
                r"Molecule\s*\(\s*['\"](\w+)['\"]",  # Molecule('water')
                r"system\s*=.*?Molecule.*?['\"](\w+)['\"]",
            ]

            for pattern in molecule_patterns:
                matches = re.findall(pattern, content)
                info["molecules"].extend(matches)

            # 提取操作 (函数调用)
            operation_keywords = [
                "render",
                "animate",
                "run",
                "simulate",
                "calculate",
                "optimize",
            ]
            for keyword in operation_keywords:
                if keyword in content:
                    info["operations"].append(keyword)

            # 提取可视化相关
            if "matplotlib" in str(info["imports"]) or "plt." in content:
                info["visualizations"].append("matplotlib")
            if "mayavi" in str(info["imports"]):
                info["visualizations"].append("mayavi")

        except Exception as e:
            logger.warning(f"代码分析失败: {e}")

        return info

    def extract_steps_from_code(self, code_info: dict[str, Any]) -> list[str]:
        """从代码信息提取实验步骤

        Args:
            code_info: 代码分析结果

        Returns:
            步骤描述列表
        """
        steps = []

        # 根据导入推断步骤
        if code_info["molecules"]:
            steps.append(f"创建分子体系: {', '.join(set(code_info['molecules']))}")

        if "render" in code_info["operations"]:
            steps.append("渲染分子结构")

        if "animate" in code_info["operations"]:
            steps.append("播放分子动画")

        if "calculate" in code_info["operations"]:
            steps.append("进行计算分析")

        if code_info["visualizations"]:
            steps.append(f"可视化结果 (使用 {', '.join(code_info['visualizations'])})")

        # 如果没有提取到步骤,返回默认步骤
        if not steps:
            steps = ["加载数据", "执行实验", "观察结果"]

        return steps

    def parse_batch(self, file_paths: list[Path]) -> list[dict[str, Any]]:
        """批量解析文件

        Args:
            file_paths: 文件路径列表

        Returns:
            实验数据列表
        """
        experiments = []

        for file_path in file_paths:
            exp = self.parse_file(file_path)
            if exp:
                # 提取步骤
                exp["steps"] = self.extract_steps_from_code(exp["code_info"])
                experiments.append(exp)

        logger.info(f"✅ 成功解析 {len(experiments)}/{len(file_paths)} 个实验")
        return experiments


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
    example_files = fetcher.list_examples()[:5]  # 测试前5个

    # 解析
    parser = ExperimentParser()
    experiments = parser.parse_batch(example_files)

    # 输出
    for exp in experiments:
        print(f"\n实验: {exp['title']}")
        print(f"  描述: {exp['description'][:100]}...")
        print(f"  步骤数: {len(exp['steps'])}")
        print(f"  步骤: {exp['steps']}")
