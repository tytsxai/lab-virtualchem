"""
化学渲染模块 - RDKit 适配层
用于分子结构可视化和化学属性计算
"""

import logging
from io import BytesIO
from typing import Any

from . import registry, require_plugin

logger = logging.getLogger(__name__)


class ChemRenderer:
    """化学结构渲染器"""

    def __init__(self):
        self.rdkit = registry.get_module("rdkit")

    @require_plugin("rdkit")
    def smiles_to_image(self, smiles: str, width: int = 300, height: int = 300, format: str = "PNG") -> bytes | None:
        """将SMILES转换为图片

        Args:
            smiles: SMILES字符串
            width: 图片宽度
            height: 图片高度
            format: 图片格式 (PNG/SVG)

        Returns:
            图片二进制数据，失败返回None
        """
        from rdkit import Chem
        from rdkit.Chem import Draw

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.error(f"无效的SMILES: {smiles}")
                return None

            if format.upper() == "SVG":
                drawer = Draw.rdMolDraw2D.MolDraw2DSVG(width, height)
                drawer.DrawMolecule(mol)
                drawer.FinishDrawing()
                return drawer.GetDrawingText().encode("utf-8")
            else:
                img = Draw.MolToImage(mol, size=(width, height))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()

        except Exception as e:
            logger.error(f"渲染SMILES失败: {e}")
            return None

    def get_mol_properties(self, smiles: str) -> dict[str, Any] | None:
        """获取分子基本属性

        Args:
            smiles: SMILES字符串

        Returns:
            分子属性字典
        """
        if not registry.is_available("rdkit"):
            logger.warning("RDKit未安装，无法计算分子属性")
            return {"formula": "未知", "molecular_weight": 0.0, "error": "RDKit未安装"}

        from rdkit import Chem
        from rdkit.Chem import Crippen, Descriptors

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return None

            return {
                "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
                "molecular_weight": Descriptors.MolWt(mol),
                "num_atoms": mol.GetNumAtoms(),
                "num_bonds": mol.GetNumBonds(),
                "num_rings": Descriptors.RingCount(mol),
                "logp": Crippen.MolLogP(mol),  # 脂水分配系数
                "tpsa": Descriptors.TPSA(mol),  # 极性表面积
                "num_hdonors": Descriptors.NumHDonors(mol),
                "num_hacceptors": Descriptors.NumHAcceptors(mol),
            }

        except Exception as e:
            logger.error(f"计算分子属性失败: {e}")
            return None

    def validate_smiles(self, smiles: str) -> tuple[bool, str]:
        """验证SMILES有效性

        Args:
            smiles: SMILES字符串

        Returns:
            (是否有效, 错误信息)
        """
        if not registry.is_available("rdkit"):
            logger.warning("RDKit未安装，使用基本验证")
            # 简单检查：非空且包含化学符号
            if not smiles or not isinstance(smiles, str):
                return False, "SMILES不能为空"
            # 基本格式检查
            if any(c in smiles for c in ["C", "N", "O", "S", "P", "c", "n", "o", "s", "p"]):
                return True, "警告: RDKit未安装，仅进行了基本格式检查"
            return False, "SMILES格式可能无效"

        from rdkit import Chem

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return False, "无效的SMILES格式"
            return True, ""
        except Exception as e:
            return False, str(e)

    def smiles_to_inchi(self, smiles: str) -> str | None:
        """SMILES转InChI"""
        if not registry.is_available("rdkit"):
            logger.warning("RDKit未安装，无法转换InChI")
            return None

        from rdkit import Chem

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return Chem.MolToInchi(mol)
        except Exception:
            pass
        return None

    def inchi_to_smiles(self, inchi: str) -> str | None:
        """InChI转SMILES"""
        if not registry.is_available("rdkit"):
            logger.warning("RDKit未安装，无法转换SMILES")
            return None

        from rdkit import Chem

        try:
            mol = Chem.MolFromInchi(inchi)
            if mol:
                return Chem.MolToSmiles(mol)
        except Exception:
            pass
        return None


# 回退实现：无RDKit时的简单渲染
def _fallback_smiles_to_image(*_args, **kwargs) -> bytes:
    """回退：返回占位图片"""
    # 创建简单的占位PNG
    from PIL import Image, ImageDraw

    width = kwargs.get("width", 300)
    height = kwargs.get("height", 300)

    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    text = "RDKit 未安装\n无法渲染分子结构"
    bbox = draw.textbbox((0, 0), text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, text, fill="gray")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# 注册插件和回退
registry.register(
    name="rdkit",
    description="分子结构渲染和化学属性计算",
    module_name="rdkit",
    license="BSD-3-Clause",
    fallback=_fallback_smiles_to_image,
)


# 便捷函数
def get_renderer() -> ChemRenderer:
    """获取渲染器实例"""
    return ChemRenderer()


def is_available() -> bool:
    """检查RDKit是否可用"""
    return registry.is_available("rdkit")
