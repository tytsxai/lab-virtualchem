"""实验模板转换器

将 chemlab 实验数据转换为 VirtualChemLab YAML 模板格式。
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class TemplateConverter:
    """实验模板转换器"""

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化转换器

        Args:
            config: 转换配置
        """
        self.config = config or {}
        self.conversion_opts = self.config.get("conversion", {}).get("experiments", {})

    def convert(self, experiment_data: dict[str, Any], repo_info: dict[str, str] | None = None) -> dict[str, Any]:
        """转换实验数据为 YAML 模板格式

        Args:
            experiment_data: 解析后的实验数据
            repo_info: 仓库信息(用于元数据)

        Returns:
            VirtualChemLab 模板数据
        """
        # 生成实验 ID
        exp_id = self._generate_id(experiment_data)

        # 构建模板
        template = {
            "id": exp_id,
            "title": experiment_data.get("title", "未命名实验"),
            "title_en": self._extract_english_title(experiment_data),
            "level": self._determine_level(experiment_data),
            "duration_min": self.conversion_opts.get("default_duration", 45),
            "goals": self._extract_goals(experiment_data),
            "prerequisites": [],
            "reagents": self._extract_reagents(experiment_data),
            "steps": self._convert_steps(experiment_data),
            "curves": self._extract_curves(experiment_data),
            "score_rules": self._generate_score_rules(experiment_data),
            "version": "1.0.0",
        }

        # 添加元数据
        if self.conversion_opts.get("add_metadata", True):
            template["metadata"] = self._create_metadata(experiment_data, repo_info)

        return template

    def _generate_id(self, data: dict[str, Any]) -> str:
        """生成实验 ID"""
        source_file = data.get("source_file", "unknown")
        base_name = Path(source_file).stem

        # 清理文件名作为 ID
        exp_id = re.sub(r"[^a-zA-Z0-9_]", "_", base_name).lower()

        # 添加前缀
        prefix = self.config.get("output", {}).get("naming", {}).get("experiment_prefix", "chemlab_exp_")
        return f"{prefix}{exp_id}"

    def _extract_english_title(self, data: dict[str, Any]) -> str | None:
        """提取英文标题"""
        title = data.get("title", "")

        # 如果标题包含中文,返回 None
        if re.search(r"[\u4e00-\u9fff]", title):
            return None

        return title

    def _determine_level(self, data: dict[str, Any]) -> str:
        """判断难度级别"""
        # 根据步骤数、代码复杂度等判断
        steps = data.get("steps", [])
        code_info = data.get("code_info", {})

        if len(steps) <= 3 and len(code_info.get("imports", [])) <= 3:
            return "basic"
        elif len(steps) <= 6:
            return "intermediate"
        else:
            return "advanced"

    def _extract_goals(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """提取实验目标"""
        # chemlab 通常没有明确的目标定义,这里根据实验类型推断
        code_info = data.get("code_info", {})
        goals = []

        if "render" in code_info.get("operations", []):
            goals.append({"name": "成功渲染分子结构", "metric": "render_success", "eq": 1})

        if "calculate" in code_info.get("operations", []):
            goals.append({"name": "完成计算分析", "metric": "calc_complete", "eq": 1})

        # 默认目标
        if not goals:
            goals.append({"name": "完成所有实验步骤", "metric": "steps_completed", "eq": 1})

        return goals

    def _extract_reagents(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """提取试剂列表"""
        reagents = []
        molecules = data.get("code_info", {}).get("molecules", [])

        for idx, mol in enumerate(set(molecules), 1):
            reagents.append(
                {
                    "id": f"reagent_{idx}",
                    "name": mol.capitalize(),
                    "amount": "适量",
                    "hazard_level": "info",
                }
            )

        return reagents

    def _convert_steps(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """转换步骤"""
        source_steps = data.get("steps", [])
        converted = []

        for idx, step_text in enumerate(source_steps, 1):
            step = {
                "id": f"step_{idx}",
                "text": step_text,
                "media": None,
                "check": self._create_checkpoint(idx, step_text),
                "hints": [],
                "safety_level": "info",
            }

            # 检测危险操作
            if any(keyword in step_text.lower() for keyword in ["heat", "acid", "flame"]):
                step["safety_level"] = "warning"

                # 添加安全提示
                if self.conversion_opts.get("add_safety_hints", True):
                    step["hints"].append({"text": "请注意实验安全,佩戴防护装备", "trigger": None})

            converted.append(step)

        return converted

    def _create_checkpoint(self, step_num: int, step_text: str) -> dict[str, Any]:
        """创建检查点"""
        # 简单的确认型检查点
        checkpoint = {"type": "confirm", "fail_hint": f"请确认已完成步骤 {step_num}", "input": None, "require": None, "correct_value": None}

        # 如果步骤包含数值,创建输入型检查点
        if re.search(r"\d+", step_text):
            checkpoint["type"] = "input"
            checkpoint["input"] = {
                "key": f"value_{step_num}",
                "label": "请输入观察到的数值",
                "input_type": "float",
                "range": None,
                "unit": None,
                "options": None,
            }

        return checkpoint

    def _extract_curves(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """提取曲线配置"""
        curves = []

        # 如果使用了 matplotlib,可能有曲线
        code_info = data.get("code_info", {})
        if "matplotlib" in code_info.get("visualizations", []):
            curves.append(
                {
                    "id": "curve_1",
                    "type": "temp_time",  # 默认类型
                    "params": {"initial_temp": 25, "rate": 0.5},
                    "x_label": "时间",
                    "y_label": "观测值",
                    "x_unit": "s",
                    "y_unit": None,
                }
            )

        return curves

    def _generate_score_rules(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """生成评分规则"""
        if not self.conversion_opts.get("auto_generate_scoring", True):
            return []

        steps = data.get("steps", [])
        num_steps = len(steps)

        if num_steps == 0:
            return []

        # 简单的步骤完成度评分
        score_per_step = 100 // num_steps

        rules = []
        for i in range(1, num_steps + 1):
            rules.append({"when": f"steps_completed >= {i}", "then": score_per_step * i})

        return rules

    def _create_metadata(self, data: dict[str, Any], repo_info: dict[str, str] | None) -> dict[str, str]:
        """创建元数据"""
        metadata = {
            "source": "chemlab",
            "source_file": data.get("source_file", "unknown"),
            "import_date": datetime.now().isoformat(),
            "license": "BSD-3-Clause (from chemlab)",
        }

        if repo_info:
            metadata.update(
                {
                    "source_commit": repo_info.get("commit", "unknown"),
                    "source_url": repo_info.get("url", ""),
                }
            )

        return metadata

    def save_template(self, template: dict[str, Any], output_dir: Path) -> Path:
        """保存模板为 YAML 文件

        Args:
            template: 模板数据
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{template['id']}.yaml"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        logger.info(f"✅ 保存模板: {filepath}")
        return filepath

    def convert_batch(
        self, experiments: list[dict[str, Any]], output_dir: Path, repo_info: dict[str, str] | None = None
    ) -> list[Path]:
        """批量转换并保存

        Args:
            experiments: 实验数据列表
            output_dir: 输出目录
            repo_info: 仓库信息

        Returns:
            保存的文件路径列表
        """
        saved_files = []

        for exp in experiments:
            try:
                template = self.convert(exp, repo_info)
                filepath = self.save_template(template, output_dir)
                saved_files.append(filepath)
            except Exception as e:
                logger.error(f"❌ 转换失败 {exp.get('title', 'unknown')}: {e}")

        logger.info(f"\n✅ 成功转换 {len(saved_files)}/{len(experiments)} 个实验")
        return saved_files


# 测试代码
if __name__ == "__main__":
    # 模拟数据
    test_data = {
        "source_file": "water_molecule.py",
        "title": "Water Molecule Visualization",
        "description": "Visualize a water molecule using chemlab",
        "steps": ["Create water molecule", "Render the structure", "Display in 3D viewer"],
        "code_info": {"imports": ["chemlab", "numpy"], "molecules": ["water"], "operations": ["render"], "visualizations": ["mayavi"]},
    }

    converter = TemplateConverter({"conversion": {"experiments": {"add_metadata": True, "auto_generate_scoring": True}}})

    template = converter.convert(test_data, {"commit": "abc123", "url": "https://github.com/chemlab/chemlab"})

    print("\n生成的模板:")
    print(yaml.dump(template, allow_unicode=True, sort_keys=False))
