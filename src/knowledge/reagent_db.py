"""试剂数据库"""

import logging
from pathlib import Path

from src.knowledge.loader import KnowledgeLoader
from src.models.knowledge import HazardLevel, KnowledgeCard, KnowledgeType

logger = logging.getLogger(__name__)


class ReagentDatabase:
    """试剂数据库"""

    def __init__(self, knowledge_dir: Path) -> None:
        """初始化试剂数据库

        Args:
            knowledge_dir: 知识库目录
        """
        self.loader = KnowledgeLoader(knowledge_dir)
        self._reagents: dict[str, KnowledgeCard] = {}
        self._load_reagents()

    def _load_reagents(self) -> None:
        """加载所有试剂数据"""
        reagents = self.loader.load_cards_by_type(KnowledgeType.REAGENT)
        for reagent in reagents:
            self._reagents[reagent.id] = reagent

        logger.info(f"已加载 {len(self._reagents)} 种试剂数据")

    def get_reagent(self, reagent_id: str) -> KnowledgeCard | None:
        """获取试剂信息

        Args:
            reagent_id: 试剂ID

        Returns:
            试剂信息或None
        """
        return self._reagents.get(reagent_id)

    def get_reagent_by_cas(self, cas_number: str) -> KnowledgeCard | None:
        """根据CAS号获取试剂

        Args:
            cas_number: CAS号

        Returns:
            试剂信息或None
        """
        for reagent in self._reagents.values():
            if reagent.cas == cas_number:
                return reagent
        return None

    def search_reagents(self, query: str) -> list[KnowledgeCard]:
        """搜索试剂

        Args:
            query: 搜索关键词

        Returns:
            匹配的试剂列表
        """
        return self.loader.search_cards(query, KnowledgeType.REAGENT)

    def get_hazardous_reagents(self, min_level: HazardLevel = HazardLevel.WARNING) -> list[KnowledgeCard]:
        """获取危险试剂列表

        Args:
            min_level: 最低危害等级

        Returns:
            危险试剂列表
        """
        level_priority = {
            HazardLevel.INFO: 1,
            HazardLevel.WARNING: 2,
            HazardLevel.SEVERE: 3,
            HazardLevel.CRITICAL: 4,
        }

        min_priority = level_priority[min_level]
        hazardous = []

        for reagent in self._reagents.values():
            highest_level = reagent.get_highest_hazard_level()
            if highest_level and level_priority[highest_level] >= min_priority:
                hazardous.append(reagent)

        return sorted(
            hazardous,
            key=lambda r: level_priority[r.get_highest_hazard_level() or HazardLevel.INFO],
            reverse=True,
        )

    def get_incompatible_pairs(self) -> list[tuple[str, str, str, str]]:
        """获取不兼容试剂对

        从安全知识库加载配伍禁忌数据

        Returns:
            不兼容试剂对列表 [(reagent1_id, reagent2_id, risk, description), ...]
        """
        try:
            # 从安全知识库加载配伍禁忌数据
            import json
            from pathlib import Path

            safety_file = Path(__file__).parent.parent.parent / "assets" / "knowledge" / "safety.json"

            if not safety_file.exists():
                logger.warning("安全知识库文件不存在，返回默认配伍禁忌")
                return self._get_default_incompatible_pairs()

            with open(safety_file, encoding="utf-8") as f:
                safety_data = json.load(f)

            # 查找配伍禁忌条目
            incompatible_pairs = []
            for item in safety_data:
                if item.get("name") == "试剂配伍禁忌":
                    pairs = item.get("incompatible_pairs", [])
                    for pair in pairs:
                        incompatible_pairs.append(
                            (
                                pair.get("reagent1", ""),
                                pair.get("reagent2", ""),
                                pair.get("risk", "未知"),
                                pair.get("description", ""),
                            )
                        )
                    break

            if incompatible_pairs:
                logger.info(f"已加载 {len(incompatible_pairs)} 组配伍禁忌数据")
                return incompatible_pairs
            else:
                logger.warning("安全知识库中未找到配伍禁忌数据，返回默认值")
                return self._get_default_incompatible_pairs()

        except Exception as e:
            logger.error(f"加载配伍禁忌数据失败: {e}")
            return self._get_default_incompatible_pairs()

    def _get_default_incompatible_pairs(self) -> list[tuple[str, str, str, str]]:
        """获取默认的不兼容试剂对（当数据文件不可用时）

        Returns:
            默认不兼容试剂对列表
        """
        return [
            ("h2so4_conc", "h2o", "极高", "浓硫酸与水混合会放出大量热"),
            ("na", "h2o", "极高", "钠与水剧烈反应生成氢气"),
            ("k", "h2o", "极高", "钾与水的反应比钠更剧烈"),
            ("hcl", "naoh", "高", "酸碱中和反应放出大量热"),
            ("hno3_conc", "ethanol", "极高", "浓硝酸与有机物可能引起燃烧"),
            ("kmno4", "glycerol", "极高", "高锰酸钾与甘油会剧烈燃烧"),
            ("nh3", "bleach", "高", "氨与氯产生有毒气体"),
            ("p_white", "air", "极高", "白磷在空气中会自燃"),
        ]

    def check_compatibility(self, reagent1_id: str, reagent2_id: str) -> tuple[bool, str]:
        """检查两种试剂是否兼容

        Args:
            reagent1_id: 试剂1的ID
            reagent2_id: 试剂2的ID

        Returns:
            (是否兼容, 风险描述)
        """
        incompatible_pairs = self.get_incompatible_pairs()

        for r1, r2, risk, desc in incompatible_pairs:
            # 检查双向匹配
            if (r1 == reagent1_id and r2 == reagent2_id) or (r1 == reagent2_id and r2 == reagent1_id):
                return False, f"风险等级: {risk} - {desc}"

        return True, "未发现配伍禁忌"

    def reload(self) -> None:
        """重新加载试剂数据"""
        self._reagents.clear()
        self.loader.clear_cache()
        self._load_reagents()
        logger.info("试剂数据库已重新加载")
