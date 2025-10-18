"""3D分子可视化模块

使用py3Dmol实现交互式3D分子查看器，支持:
- PubChem分子数据加载
- 多种渲染样式
- 交互式操作
- 动画演示
- 高质量图像导出
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import py3Dmol

    PY3DMOL_AVAILABLE = True
except ImportError:
    PY3DMOL_AVAILABLE = False
    logger.warning("py3Dmol未安装，3D可视化功能不可用")

try:
    import io  # noqa: F401

    from PIL import Image  # noqa: F401

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class Molecule3DViewer:
    """3D分子查看器"""

    # 预定义渲染样式
    STYLES = {
        "stick": {"stick": {"radius": 0.15}},
        "sphere": {"sphere": {"radius": 0.5}},
        "cartoon": {"cartoon": {}},
        "line": {"line": {}},
        "cross": {"cross": {"radius": 0.1}},
        "ball_stick": {"stick": {"radius": 0.15}, "sphere": {"radius": 0.3}},
    }

    # 颜色方案
    COLOR_SCHEMES = {
        "default": "default",
        "carbon": "carbonChain",
        "amino": "amino",
        "shapely": "shapely",
        "nucleic": "nucleic",
    }

    def __init__(self, width: int = 800, _height: int = 600):
        """初始化3D查看器

        Args:
            width: 查看器宽度
            height: 查看器高度
        """
        if not PY3DMOL_AVAILABLE:
            raise ImportError("py3Dmol未安装，请运行: pip install py3Dmol")

        self.width = width
        self.height = _height
        self.viewer = None
        self.current_molecule = None

    def create_viewer(self) -> "py3Dmol.view":
        """创建新的3D查看器实例"""
        self.viewer = py3Dmol.view(width=self.width, height=self.height)
        return self.viewer

    def load_from_pubchem(self, compound_name: str) -> bool:
        """从PubChem加载分子

        Args:
            compound_name: 化合物名称或CID

        Returns:
            是否成功加载
        """
        try:
            # 尝试导入PubChemPy
            import pubchempy as pcp

            # 搜索化合物
            compounds = pcp.get_compounds(compound_name, "name")
            if not compounds:
                logger.error(f"未找到化合物: {compound_name}")
                return False

            compound = compounds[0]

            # 获取3D结构 (SDF格式)
            sdf_data = pcp.get_sdf(compound.cid, record_type="3d")

            if not sdf_data:
                logger.warning(f"{compound_name} 无3D结构，尝试使用2D")
                sdf_data = pcp.get_sdf(compound.cid)

            # 加载到查看器
            if self.viewer is None:
                self.create_viewer()

            self.viewer.addModel(sdf_data, "sdf")
            self.current_molecule = {
                "name": compound.iupac_name or compound_name,
                "formula": compound.molecular_formula,
                "cid": compound.cid,
                "data": sdf_data,
            }

            logger.info(f"成功加载分子: {compound_name}")
            return True

        except ImportError:
            logger.error("PubChemPy未安装，无法从PubChem加载")
            return False
        except Exception as e:
            logger.error(f"加载分子失败: {e}")
            return False

    def load_from_file(self, file_path: Path, format: str = "auto") -> bool:
        """从文件加载分子

        Args:
            file_path: 文件路径
            format: 文件格式 (auto/sdf/pdb/mol/xyz/mol2)

        Returns:
            是否成功加载
        """
        try:
            # 自动检测格式
            if format == "auto":
                suffix = file_path.suffix.lower()
                format_map = {
                    ".sd": "sd",
                    ".pdb": "pdb",
                    ".mol": "mol",
                    ".xyz": "xyz",
                    ".mol2": "mol2",
                }
                format = format_map.get(suffix, "sd")

            # 读取文件
            with open(file_path, encoding="utf-8") as f:
                data = f.read()

            # 加载到查看器
            if self.viewer is None:
                self.create_viewer()

            self.viewer.addModel(data, format)
            self.current_molecule = {
                "name": file_path.stem,
                "source": str(file_path),
                "format": format,
                "data": data,
            }

            logger.info(f"成功加载文件: {file_path}")
            return True

        except Exception as e:
            logger.error(f"加载文件失败: {e}")
            return False

    def load_from_smiles(self, smiles: str, name: str = "molecule") -> bool:
        """从SMILES字符串加载分子

        Args:
            smiles: SMILES字符串
            name: 分子名称

        Returns:
            是否成功加载
        """
        try:
            # 需要RDKit来转换SMILES到3D
            from rdkit import Chem
            from rdkit.Chem import AllChem

            # 从SMILES创建分子
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.error(f"无效的SMILES: {smiles}")
                return False

            # 添加氢原子
            mol = Chem.AddHs(mol)

            # 生成3D坐标
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)

            # 转换为MOL格式
            mol_block = Chem.MolToMolBlock(mol)

            # 加载到查看器
            if self.viewer is None:
                self.create_viewer()

            self.viewer.addModel(mol_block, "mol")
            self.current_molecule = {"name": name, "smiles": smiles, "data": mol_block}

            logger.info(f"成功从SMILES加载: {name}")
            return True

        except ImportError:
            logger.error("RDKit未安装，无法处理SMILES")
            return False
        except Exception as e:
            logger.error(f"从SMILES加载失败: {e}")
            return False

    def set_style(self, style: str = "ball_stick", color_scheme: str = "default"):
        """设置渲染样式

        Args:
            style: 样式名称
            color_scheme: 颜色方案
        """
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        # 获取样式配置
        style_config = self.STYLES.get(style, self.STYLES["ball_stick"])

        # 应用样式
        self.viewer.setStyle(style_config)

        # 应用颜色方案
        if color_scheme in self.COLOR_SCHEMES:
            self.viewer.setStyle({"colorscheme": self.COLOR_SCHEMES[color_scheme]})

        logger.debug(f"应用样式: {style}, 颜色: {color_scheme}")

    def add_surface(self, opacity: float = 0.7, color: str = "white"):
        """添加分子表面

        Args:
            opacity: 透明度 (0-1)
            color: 表面颜色
        """
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        self.viewer.addSurface(py3Dmol.VDW, {"opacity": opacity, "color": color})
        logger.debug(f"添加表面: 透明度={opacity}, 颜色={color}")

    def add_labels(self, atom_labels: bool = True, residue_labels: bool = False):
        """添加标签

        Args:
            atom_labels: 显示原子标签
            residue_labels: 显示残基标签
        """
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        if atom_labels:
            self.viewer.addPropertyLabels("atom", "", {"fontColor": "black"})

        if residue_labels:
            self.viewer.addResLabels()

        logger.debug(f"添加标签: 原子={atom_labels}, 残基={residue_labels}")

    def spin(self, enable: bool = True, axis: str = "y", speed: float = 1.0):
        """设置自动旋转

        Args:
            enable: 是否启用
            axis: 旋转轴 (x/y/z)
            speed: 旋转速度
        """
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        if enable:
            self.viewer.spin(axis, speed)
        else:
            self.viewer.spin(False)

        logger.debug(f"自动旋转: {enable}, 轴={axis}, 速度={speed}")

    def zoom(self, factor: float = 1.0):
        """缩放视图

        Args:
            factor: 缩放因子
        """
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        self.viewer.zoom(factor)
        logger.debug(f"缩放: {factor}")

    def render(self):
        """渲染并显示"""
        if self.viewer is None:
            logger.warning("查看器未初始化")
            return

        self.viewer.zoomTo()
        self.viewer.show()
        logger.debug("渲染完成")

    def export_png(self, output_path: Path, _width: int = 1200, _height: int = 900) -> bool:
        """导出PNG图像

        Args:
            output_path: 输出路径
            width: 图像宽度
            height: 图像高度

        Returns:
            是否成功导出
        """
        if not PIL_AVAILABLE:
            logger.error("Pillow未安装，无法导出图像")
            return False

        if self.viewer is None:
            logger.warning("查看器未初始化")
            return False

        try:
            # py3Dmol的PNG导出 (需要在Jupyter环境)
            png_data = self.viewer.png()

            # 保存图像
            with open(output_path, "wb") as f:
                f.write(png_data)

            logger.info(f"成功导出图像: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出图像失败: {e}")
            return False

    def get_molecule_info(self) -> dict[str, Any]:
        """获取当前分子信息"""
        return self.current_molecule or {}


# 便捷函数
def quick_view(
    compound_name: str, style: str = "ball_stick", spin: bool = True, surface: bool = False
) -> Molecule3DViewer:
    """快速查看分子

    Args:
        compound_name: 化合物名称
        style: 渲染样式
        spin: 是否自动旋转
        surface: 是否显示表面

    Returns:
        Molecule3DViewer实例
    """
    viewer = Molecule3DViewer()

    # 加载分子
    if viewer.load_from_pubchem(compound_name):
        # 设置样式
        viewer.set_style(style)

        # 表面
        if surface:
            viewer.add_surface()

        # 旋转
        if spin:
            viewer.spin(True)

        # 渲染
        viewer.render()

    return viewer


def compare_molecules(molecules: list[str], style: str = "ball_stick") -> list[Molecule3DViewer]:
    """对比查看多个分子

    Args:
        molecules: 分子名称列表
        style: 渲染样式

    Returns:
        Molecule3DViewer实例列表
    """
    viewers = []

    for mol_name in molecules:
        viewer = Molecule3DViewer(width=400, height=400)
        if viewer.load_from_pubchem(mol_name):
            viewer.set_style(style)
            viewer.render()
            viewers.append(viewer)

    return viewers


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 快速查看阿司匹林
    logger.info("查看阿司匹林分子...")
    viewer = quick_view("aspirin", style="ball_stick", spin=True, surface=True)

    # 查看多个分子
    logger.info("\n对比查看分子...")
    molecules = ["ethanol", "methanol", "propanol"]
    viewers = compare_molecules(molecules)

    logger.info(f"\n成功加载 {len(viewers)} 个分子")
