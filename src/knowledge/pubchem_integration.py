"""PubChem数据库集成模块

通过PubChemPy访问PubChem化合物数据库,自动补充试剂信息和安全数据。
"""

import logging
import time
from typing import Any

try:
    import pubchempy as pcp

    PUBCHEM_AVAILABLE = True
except ImportError:
    PUBCHEM_AVAILABLE = False
    pcp = None

from ..models.knowledge import ReagentInfo

logger = logging.getLogger(__name__)

MAX_FIELD_CHARS = 512
MAX_SYNONYMS = 10
MAX_SYNONYM_CHARS = 128
MAX_BATCH_SIZE = 50
MIN_REQUEST_INTERVAL_SEC = 0.2  # 5 req/sec


class PubChemIntegration:
    """PubChem数据库集成类"""

    def __init__(self) -> None:
        """初始化PubChem集成"""
        self.available = PUBCHEM_AVAILABLE
        self._last_request_ts: float | None = None
        if not self.available:
            logger.warning(
                "PubChemPy未安装,自动补充功能不可用. 安装: pip install pubchempy"
            )

    def _clean_str(self, value: Any, *, max_len: int = MAX_FIELD_CHARS) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        value = value.replace("\x00", "").strip()
        if len(value) > max_len:
            return value[:max_len]
        return value

    def _clean_float(self, value: Any, *, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _clean_int(self, value: Any, *, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except Exception:
            return default

    def _clean_synonyms(self, synonyms: Any) -> list[str]:
        if not synonyms:
            return []
        if not isinstance(synonyms, (list, tuple)):
            synonyms = [synonyms]

        cleaned: list[str] = []
        for item in synonyms:
            s = self._clean_str(item, max_len=MAX_SYNONYM_CHARS)
            if s and s not in cleaned:
                cleaned.append(s)
            if len(cleaned) >= MAX_SYNONYMS:
                break
        return cleaned

    def _throttle(self) -> None:
        if not self.available:
            return
        now = time.monotonic()
        if self._last_request_ts is None:
            self._last_request_ts = now
            return
        elapsed = now - self._last_request_ts
        if elapsed < MIN_REQUEST_INTERVAL_SEC:
            time.sleep(MIN_REQUEST_INTERVAL_SEC - elapsed)
        self._last_request_ts = time.monotonic()

    def search_compound(
        self, identifier: str, namespace: str = "name"
    ) -> dict[str, Any] | None:
        """搜索化合物信息

        Args:
            identifier: 化合物标识符(名称、CAS号、SMILES等)
            namespace: 标识符类型 ('name', 'smiles', 'inchi', 'inchikey', 'formula')

        Returns:
            化合物信息字典,如果未找到返回None
        """
        if not self.available:
            logger.warning("PubChem不可用,无法搜索化合物")
            return None

        try:
            self._throttle()
            compounds = pcp.get_compounds(identifier, namespace)

            if not compounds:
                logger.info(f"未找到化合物: {identifier} ({namespace})")
                return None

            # 取第一个匹配结果
            compound = compounds[0]

            return self._extract_compound_data(compound)

        except Exception as e:
            logger.error(f"搜索化合物失败 {identifier}: {e}")
            return None

    def _extract_compound_data(self, compound: Any) -> dict[str, Any]:
        """提取化合物数据

        Args:
            compound: PubChem Compound对象

        Returns:
            结构化的化合物数据
        """
        synonyms_clean = self._clean_synonyms(getattr(compound, "synonyms", None))
        common_name = synonyms_clean[0] if synonyms_clean else ""

        return {
            "cid": self._clean_int(getattr(compound, "cid", None), default=0),
            "name": self._clean_str(getattr(compound, "iupac_name", "")),
            "common_name": self._clean_str(common_name, max_len=MAX_SYNONYM_CHARS),
            "molecular_formula": self._clean_str(
                getattr(compound, "molecular_formula", "")
            ),
            "molecular_weight": self._clean_float(
                getattr(compound, "molecular_weight", None)
            ),
            "canonical_smiles": self._clean_str(getattr(compound, "canonical_smiles", "")),
            "isomeric_smiles": self._clean_str(getattr(compound, "isomeric_smiles", "")),
            "inchi": self._clean_str(getattr(compound, "inchi", "")),
            "inchikey": self._clean_str(getattr(compound, "inchikey", "")),
            "synonyms": synonyms_clean,
            # 物理化学性质
            "xlogp": self._clean_float(getattr(compound, "xlogp", None), default=0.0),
            "exact_mass": self._clean_float(
                getattr(compound, "exact_mass", None), default=0.0
            ),
            "monoisotopic_mass": self._clean_float(
                getattr(compound, "monoisotopic_mass", None), default=0.0
            ),
            "tpsa": self._clean_float(getattr(compound, "tpsa", None), default=0.0),  # 拓扑极性表面积
            "complexity": self._clean_float(
                getattr(compound, "complexity", None), default=0.0
            ),
            "h_bond_donor_count": self._clean_int(
                getattr(compound, "h_bond_donor_count", None), default=0
            ),
            "h_bond_acceptor_count": self._clean_int(
                getattr(compound, "h_bond_acceptor_count", None), default=0
            ),
            "rotatable_bond_count": self._clean_int(
                getattr(compound, "rotatable_bond_count", None), default=0
            ),
            "heavy_atom_count": self._clean_int(
                getattr(compound, "heavy_atom_count", None), default=0
            ),
            "charge": self._clean_int(getattr(compound, "charge", None), default=0),
        }

    def get_safety_info(self, identifier: str) -> dict[str, Any]:
        """获取化合物安全信息

        Args:
            identifier: 化合物标识符

        Returns:
            安全信息字典
        """
        if not self.available:
            return {"available": False}

        try:
            self._throttle()
            compounds = pcp.get_compounds(identifier, "name")
            if not compounds:
                return {"available": False, "error": "Compound not found"}

            compound = compounds[0]

            # 从PubChem获取GHS分类
            safety_data = {
                "available": True,
                "cid": compound.cid,
                "hazard_classes": [],  # 需要额外API调用获取
                "precautionary_statements": [],
                "signal_word": "",
                # 基础危险判断(基于性质)
                "is_flammable": self._check_flammability(compound),
                "is_corrosive": self._check_corrosivity(compound),
                "is_toxic": self._check_toxicity(compound),
            }

            return safety_data

        except Exception as e:
            logger.error(f"获取安全信息失败 {identifier}: {e}")
            return {"available": False, "error": str(e)}

    def _check_flammability(self, compound: Any) -> bool:
        """检查易燃性(简化判断)"""
        # 基于分子式简单判断
        formula = compound.molecular_formula or ""
        # 含碳氢化合物可能易燃
        return "C" in formula and "H" in formula

    def _check_corrosivity(self, compound: Any) -> bool:
        """检查腐蚀性(简化判断)"""
        # 强酸强碱通常有腐蚀性
        synonyms = [s.lower() for s in (compound.synonyms or [])]
        corrosive_keywords = ["acid", "base", "hydroxide", "chloride"]
        return any(kw in " ".join(synonyms) for kw in corrosive_keywords)

    def _check_toxicity(self, compound: Any) -> bool:
        """检查毒性(简化判断)"""
        # 重金属、卤素化合物可能有毒
        formula = compound.molecular_formula or ""
        toxic_elements = ["Hg", "Pb", "As", "Cd", "Cr", "Cl", "Br", "I"]
        return any(elem in formula for elem in toxic_elements)

    def auto_fill_reagent(
        self, name: str, existing_data: ReagentInfo | None = None
    ) -> ReagentInfo:
        """自动填充试剂信息

        Args:
            name: 试剂名称
            existing_data: 已有的试剂数据(用于补充)

        Returns:
            补充完整的ReagentInfo对象
        """
        compound_data = self.search_compound(name)

        if not compound_data:
            # 如果没找到,返回现有数据或创建基础数据
            if existing_data:
                return existing_data
            return ReagentInfo(
                name=self._clean_str(name, max_len=MAX_SYNONYM_CHARS),
                formula="",
                cas_number="",
                description=self._clean_str(
                    f"化合物 {name} (PubChem未找到数据)", max_len=MAX_FIELD_CHARS
                ),
                hazards=[],
                safety_measures=[],
            )

        # 创建或更新ReagentInfo
        if existing_data:
            # 补充缺失字段
            if not existing_data.formula:
                existing_data.formula = compound_data["molecular_formula"]
            if not existing_data.molecular_weight:
                existing_data.molecular_weight = compound_data["molecular_weight"]
            return existing_data
        else:
            # 创建新数据
            return ReagentInfo(
                name=self._clean_str(
                    compound_data.get("common_name") or name, max_len=MAX_SYNONYM_CHARS
                ),
                formula=self._clean_str(
                    compound_data.get("molecular_formula", ""), max_len=MAX_FIELD_CHARS
                ),
                cas_number="",  # PubChem不直接提供CAS
                molecular_weight=float(compound_data.get("molecular_weight") or 0.0),
                description=self._clean_str(
                    f"{compound_data.get('name','')} (PubChem CID: {compound_data.get('cid', 0)})",
                    max_len=MAX_FIELD_CHARS,
                ),
                smiles=self._clean_str(
                    compound_data.get("canonical_smiles", ""), max_len=MAX_FIELD_CHARS
                ),
                hazards=self._generate_hazards(compound_data),
                safety_measures=self._generate_safety_measures(compound_data),
            )

    def _generate_hazards(self, compound_data: dict[str, Any]) -> list[str]:
        """根据化合物数据生成危险提示"""
        hazards = []

        # 基于性质判断
        if self._check_flammability(type("obj", (), compound_data)()):
            hazards.append("易燃")
        if self._check_corrosivity(type("obj", (), compound_data)()):
            hazards.append("腐蚀性")
        if self._check_toxicity(type("obj", (), compound_data)()):
            hazards.append("有毒")

        return hazards or ["需要进一步评估"]

    def _generate_safety_measures(self, compound_data: dict[str, Any]) -> list[str]:
        """根据化合物数据生成安全措施"""
        measures = ["佩戴实验室护目镜", "穿戴实验服"]

        # 根据危险性添加措施
        if self._check_flammability(type("obj", (), compound_data)()):
            measures.append("远离火源")
        if self._check_corrosivity(type("obj", (), compound_data)()):
            measures.append("佩戴防护手套")
        if self._check_toxicity(type("obj", (), compound_data)()):
            measures.append("在通风橱中操作")

        return measures

    def batch_update_reagents(self, reagent_names: list[str]) -> dict[str, ReagentInfo]:
        """批量更新试剂信息

        Args:
            reagent_names: 试剂名称列表

        Returns:
            试剂名称到ReagentInfo的映射
        """
        if len(reagent_names) > MAX_BATCH_SIZE:
            raise ValueError(
                f"批量更新数量超限: {len(reagent_names)} (max {MAX_BATCH_SIZE})"
            )

        results = {}

        for name in reagent_names:
            logger.info(f"正在更新试剂信息: {name}")
            results[name] = self.auto_fill_reagent(name)

        return results


# 全局实例
pubchem = PubChemIntegration()


def get_compound_info(
    identifier: str, namespace: str = "name"
) -> dict[str, Any] | None:
    """便捷函数: 获取化合物信息"""
    return pubchem.search_compound(identifier, namespace)


def auto_fill_reagent(name: str) -> ReagentInfo:
    """便捷函数: 自动填充试剂信息"""
    return pubchem.auto_fill_reagent(name)
