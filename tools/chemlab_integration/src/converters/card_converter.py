"""知识卡片转换器

将 chemlab 化学知识转换为 VirtualChemLab 知识卡片格式。
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class CardConverter:
    """知识卡片转换器"""

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化转换器

        Args:
            config: 转换配置
        """
        self.config = config or {}
        self.conversion_opts = self.config.get("conversion", {}).get("knowledge", {})

    def convert_reagent(self, data: dict[str, Any], repo_info: dict[str, str] | None = None) -> dict[str, Any]:
        """转换试剂数据为知识卡片

        Args:
            data: 试剂原始数据
            repo_info: 仓库信息

        Returns:
            知识卡片数据
        """
        # 生成 ID
        card_id = self._generate_id(data, "reagent")

        # 构建卡片
        card = {
            "id": card_id,
            "type": "reagent",
            "title": data.get("name", "未命名化合物"),
            "title_en": data.get("name") if not self._is_chinese(data.get("name", "")) else None,
            "content": self._generate_content(data),
            "cas": data.get("cas"),
            "formula": data.get("formula"),
            "properties": self._extract_properties(data),
            "hazards": self._extract_hazards(data),
            "images": [],
            "videos": [],
            "references": self._extract_references(data),
            "tags": self._generate_tags(data),
            "version": "1.0.0",
            "author": "ChemLab Import Tool",
            "metadata": {},
        }

        # 添加元数据
        if self.conversion_opts.get("add_metadata", True):
            card["metadata"] = self._create_metadata(data, repo_info)

        return card

    def convert_apparatus(self, data: dict[str, Any], repo_info: dict[str, str] | None = None) -> dict[str, Any]:
        """转换装置/器皿数据"""
        card_id = self._generate_id(data, "apparatus")

        card = {
            "id": card_id,
            "type": "apparatus",
            "title": data.get("name", "未命名装置"),
            "title_en": data.get("name_en"),
            "content": self._generate_content(data),
            "cas": None,
            "formula": None,
            "properties": None,
            "hazards": [],
            "images": [],
            "videos": [],
            "references": [],
            "tags": self._generate_tags(data),
            "version": "1.0.0",
            "author": "ChemLab Import Tool",
            "metadata": {},
        }

        if self.conversion_opts.get("add_metadata", True):
            card["metadata"] = self._create_metadata(data, repo_info)

        return card

    def convert_procedure(self, data: dict[str, Any], repo_info: dict[str, str] | None = None) -> dict[str, Any]:
        """转换操作规程数据"""
        card_id = self._generate_id(data, "procedure")

        card = {
            "id": card_id,
            "type": "procedure",
            "title": data.get("name", "未命名规程"),
            "title_en": data.get("name_en"),
            "content": self._generate_procedure_content(data),
            "cas": None,
            "formula": None,
            "properties": None,
            "hazards": self._extract_hazards(data),
            "images": [],
            "videos": [],
            "references": [],
            "tags": self._generate_tags(data),
            "version": "1.0.0",
            "author": "ChemLab Import Tool",
            "metadata": {},
        }

        if self.conversion_opts.get("add_metadata", True):
            card["metadata"] = self._create_metadata(data, repo_info)

        return card

    def _generate_id(self, data: dict[str, Any], type_prefix: str) -> str:
        """生成卡片 ID"""
        name = data.get("id") or data.get("name", "unknown")

        # 清理名称
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name)).lower()

        # 添加前缀
        prefix = self.config.get("output", {}).get("naming", {}).get("knowledge_prefix", "chemlab_")
        return f"{prefix}{type_prefix}_{clean_name}"

    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文"""
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _generate_content(self, data: dict[str, Any]) -> str:
        """生成内容(Markdown 格式)"""
        content_parts = []

        # 描述
        if "description" in data:
            content_parts.append(data["description"])

        # 基本信息
        info_items = []
        if "formula" in data:
            info_items.append(f"**化学式**: {data['formula']}")
        if "cas" in data:
            info_items.append(f"**CAS号**: {data['cas']}")
        if "molecular_weight" in data:
            info_items.append(f"**分子量**: {data['molecular_weight']} g/mol")

        if info_items:
            content_parts.append("\n## 基本信息\n\n" + "\n".join(info_items))

        # 物理性质
        props = self._extract_properties(data)
        if props and any(v is not None for v in props.values()):
            prop_items = []
            if props.get("density"):
                prop_items.append(f"- **密度**: {props['density']} g/cm³")
            if props.get("boiling_point"):
                prop_items.append(f"- **沸点**: {props['boiling_point']} °C")
            if props.get("melting_point"):
                prop_items.append(f"- **熔点**: {props['melting_point']} °C")
            if props.get("solubility"):
                prop_items.append(f"- **溶解性**: {props['solubility']}")

            if prop_items:
                content_parts.append("\n## 物理性质\n\n" + "\n".join(prop_items))

        # 其他信息
        for key, value in data.items():
            if (
                key
                not in [
                    "id",
                    "name",
                    "formula",
                    "cas",
                    "description",
                    "density",
                    "boiling_point",
                    "melting_point",
                    "molecular_weight",
                ]
                and isinstance(value, str)
                and value
            ):
                content_parts.append(f"\n## {key.title()}\n\n{value}")

        return "\n\n".join(content_parts) if content_parts else "暂无详细信息"

    def _generate_procedure_content(self, data: dict[str, Any]) -> str:
        """生成操作规程内容"""
        content_parts = []

        if "description" in data:
            content_parts.append(data["description"])

        # 步骤
        if "steps" in data and isinstance(data["steps"], list):
            steps_md = "\n## 操作步骤\n\n"
            for idx, step in enumerate(data["steps"], 1):
                steps_md += f"{idx}. {step}\n"
            content_parts.append(steps_md)

        # 注意事项
        if "safety" in data or "warnings" in data:
            warnings = data.get("safety") or data.get("warnings")
            content_parts.append(f"\n## 注意事项\n\n{warnings}")

        return "\n\n".join(content_parts) if content_parts else "暂无详细信息"

    def _extract_properties(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """提取物理性质"""
        if not self.conversion_opts.get("property_mapping", {}).get("density", True):
            return None

        properties = {
            "density": data.get("density"),
            "boiling_point": data.get("boiling_point") or data.get("bp"),
            "melting_point": data.get("melting_point") or data.get("mp"),
            "molecular_weight": data.get("molecular_weight") or data.get("mw"),
            "solubility": data.get("solubility"),
            "appearance": data.get("appearance") or data.get("color"),
        }

        # 如果所有值都为 None,返回 None
        if all(v is None for v in properties.values()):
            return None

        return properties

    def _extract_hazards(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """提取危害信息"""
        hazards = []

        # 从 hazard 字段提取
        if "hazard" in data or "hazards" in data:
            hazard_text = data.get("hazard") or data.get("hazards")

            if isinstance(hazard_text, str):
                # 简单解析危害文本
                hazards.append(
                    {
                        "type": "general",
                        "level": "warning",
                        "hint": hazard_text,
                        "emergency": "如有不适,立即就医",
                    }
                )
            elif isinstance(hazard_text, list):
                for h in hazard_text:
                    hazards.append(
                        {
                            "type": "general",
                            "level": "warning",
                            "hint": str(h),
                            "emergency": None,
                        }
                    )

        # 从关键词推断
        content = str(data).lower()
        if "toxic" in content or "poison" in content:
            hazards.append({"type": "toxic", "level": "severe", "hint": "有毒物质,避免接触", "emergency": "立即就医"})

        if "corrosive" in content or "acid" in content:
            hazards.append(
                {"type": "corrosive", "level": "warning", "hint": "腐蚀性物质,注意防护", "emergency": "用大量水冲洗"}
            )

        if "flammable" in content or "inflammable" in content:
            hazards.append(
                {"type": "flammable", "level": "warning", "hint": "易燃物质,远离火源", "emergency": "使用灭火器灭火"}
            )

        return hazards

    def _extract_references(self, data: dict[str, Any]) -> list[str]:
        """提取参考资料"""
        refs = []

        if "reference" in data or "references" in data:
            ref_data = data.get("reference") or data.get("references")
            if isinstance(ref_data, str):
                refs.append(ref_data)
            elif isinstance(ref_data, list):
                refs.extend(ref_data)

        # 添加 chemlab 来源
        refs.append("Data source: ChemLab (https://github.com/chemlab/chemlab)")

        return refs

    def _generate_tags(self, data: dict[str, Any]) -> list[str]:
        """生成标签"""
        tags = []

        # 从现有标签提取
        if "tags" in data:
            if isinstance(data["tags"], list):
                tags.extend(data["tags"])
            elif isinstance(data["tags"], str):
                tags.append(data["tags"])

        # 从类别推断
        if "formula" in data:
            tags.append("化合物")
        if "organic" in str(data).lower():
            tags.append("有机化学")
        if "inorganic" in str(data).lower():
            tags.append("无机化学")

        # 添加来源标签
        tags.append("chemlab")

        return list(set(tags))  # 去重

    def _create_metadata(self, _data: dict[str, Any], repo_info: dict[str, str] | None) -> dict[str, str]:
        """创建元数据"""
        metadata = {
            "source": "chemlab",
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

    def save_card(self, card: dict[str, Any], output_dir: Path) -> Path:
        """保存知识卡片

        Args:
            card: 卡片数据
            output_dir: 输出目录 (应该是知识库类型目录,如 knowledge/reagent/)

        Returns:
            保存的文件路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{card['id']}.yaml"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(card, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        logger.info(f"✅ 保存卡片: {filepath}")
        return filepath

    def convert_batch(
        self,
        knowledge_data: dict[str, list[dict[str, Any]]],
        output_base_dir: Path,
        repo_info: dict[str, str] | None = None,
    ) -> dict[str, list[Path]]:
        """批量转换知识数据

        Args:
            knowledge_data: 分类后的知识数据 {类型: [数据列表]}
            output_base_dir: 输出基础目录
            repo_info: 仓库信息

        Returns:
            保存的文件路径 {类型: [文件路径列表]}
        """
        saved_files: dict[str, list[Path]] = {}

        for category, items in knowledge_data.items():
            if not items:
                continue

            saved_files[category] = []
            output_dir = Path(output_base_dir) / category

            for item in items:
                try:
                    # 根据类型选择转换方法
                    if category == "reagent":
                        card = self.convert_reagent(item, repo_info)
                    elif category == "apparatus":
                        card = self.convert_apparatus(item, repo_info)
                    elif category == "procedure":
                        card = self.convert_procedure(item, repo_info)
                    else:
                        # 默认转为 FAQ 类型
                        card = self.convert_apparatus(item, repo_info)  # 复用
                        card["type"] = "faq"

                    filepath = self.save_card(card, output_dir)
                    saved_files[category].append(filepath)

                except Exception as e:
                    logger.error(f"❌ 转换失败 {item.get('name', 'unknown')}: {e}")

        # 统计
        total = sum(len(files) for files in saved_files.values())
        logger.info(f"\n✅ 成功转换 {total} 个知识卡片")
        for category, files in saved_files.items():
            logger.info(f"  {category}: {len(files)} 个")

        return saved_files


# 测试代码
if __name__ == "__main__":
    # 模拟数据
    test_reagent = {
        "name": "Water",
        "formula": "H2O",
        "cas": "7732-18-5",
        "molecular_weight": 18.015,
        "density": 1.0,
        "boiling_point": 100,
        "melting_point": 0,
        "description": "Water is a transparent, tasteless, odorless chemical compound.",
    }

    converter = CardConverter({"conversion": {"knowledge": {"add_metadata": True}}})

    card = converter.convert_reagent(test_reagent, {"commit": "abc123", "url": "https://github.com/chemlab/chemlab"})

    print("\n生成的知识卡片:")
    print(yaml.dump(card, allow_unicode=True, sort_keys=False))
