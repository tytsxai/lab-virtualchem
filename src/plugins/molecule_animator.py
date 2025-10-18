"""
分子动画模块 - OpenMM 适配层
用于简单的分子动力学演示（可选，默认禁用）
"""

import logging
from pathlib import Path

import numpy as np

from . import registry, require_plugin

logger = logging.getLogger(__name__)


class MoleculeAnimator:
    """分子动画生成器"""

    def __init__(self):
        self.openmm = registry.get_module("openmm")
        self._system = None
        self._simulation = None

    @require_plugin("openmm")
    def setup_simple_system(self, pdb_file: Path, temperature: float = 300.0, timestep: float = 2.0) -> bool:
        """设置简单分子系统

        Args:
            pdb_file: PDB结构文件
            temperature: 温度 (K)
            timestep: 时间步长 (fs)

        Returns:
            是否成功
        """
        from openmm import LangevinIntegrator
        from openmm.app import ForceField, PDBFile, Simulation
        from openmm.unit import femtoseconds, kelvin, picoseconds

        try:
            # 加载结构
            pdb = PDBFile(str(pdb_file))

            # 创建力场
            forcefield = ForceField("amber14-all.xml", "amber14/tip3p.xml")

            # 创建系统
            self._system = forcefield.createSystem(pdb.topology, nonbondedMethod=forcefield.NoCutoff)

            # 创建积分器
            integrator = LangevinIntegrator(temperature * kelvin, 1.0 / picoseconds, timestep * femtoseconds)

            # 创建模拟
            self._simulation = Simulation(pdb.topology, self._system, integrator)
            self._simulation.context.setPositions(pdb.positions)

            # 能量最小化
            self._simulation.minimizeEnergy()

            logger.info(f"OpenMM系统初始化成功: {pdb_file}")
            return True

        except Exception as e:
            logger.error(f"OpenMM初始化失败: {e}")
            return False

    @require_plugin("openmm")
    def generate_trajectory(self, num_frames: int = 100, frame_interval: int = 100) -> list[np.ndarray] | None:
        """生成轨迹帧

        Args:
            num_frames: 总帧数
            frame_interval: 帧间隔步数

        Returns:
            位置数据列表 [(N, 3), ...]
        """
        if not self._simulation:
            logger.error("未初始化模拟系统")
            return None

        try:
            trajectory = []

            for _i in range(num_frames):
                # 运行模拟
                self._simulation.step(frame_interval)

                # 获取位置
                state = self._simulation.context.getState(getPositions=True)
                positions = state.getPositions(asNumpy=True)

                trajectory.append(positions)

            logger.info(f"轨迹生成成功: {num_frames}帧")
            return trajectory

        except Exception as e:
            logger.error(f"轨迹生成失败: {e}")
            return None

    @require_plugin("openmm")
    def get_energy_components(self) -> dict[str, float] | None:
        """获取能量组分

        Returns:
            能量字典 (单位: kJ/mol)
        """
        if not self._simulation:
            return None

        try:
            state = self._simulation.context.getState(getEnergy=True)

            return {
                "kinetic": state.getKineticEnergy()._value,
                "potential": state.getPotentialEnergy()._value,
                "total": (state.getKineticEnergy() + state.getPotentialEnergy())._value,
            }

        except Exception as e:
            logger.error(f"能量计算失败: {e}")
            return None

    @require_plugin("openmm")
    def save_trajectory(self, output_file: Path, trajectory: list[np.ndarray], format: str = "pdb") -> bool:
        """保存轨迹到文件

        Args:
            output_file: 输出文件
            trajectory: 轨迹数据
            format: 文件格式 ('pdb', 'dcd')

        Returns:
            是否成功
        """
        from openmm.app import DCDFile, PDBFile

        try:
            if format.lower() == "pdb":
                # 保存为PDB（仅最后一帧）
                with open(str(output_file), "w", encoding="utf-8") as f:
                    PDBFile.writeFile(self._simulation.topology, trajectory[-1], f)
            elif format.lower() == "dcd":
                # 保存为DCD轨迹
                with open(str(output_file), "wb") as f:
                    dcd = DCDFile(f, self._simulation.topology, self._simulation.integrator.getStepSize())
                    for positions in trajectory:
                        dcd.writeModel(positions)

            logger.info(f"轨迹保存成功: {output_file}")
            return True

        except Exception as e:
            logger.error(f"轨迹保存失败: {e}")
            return False


# 回退实现：简单的随机运动模拟
def _fallback_generate_trajectory(num_frames: int = 100, num_atoms: int = 10) -> list[np.ndarray]:
    """回退：生成随机运动轨迹"""
    logger.warning("OpenMM未安装，生成模拟轨迹")

    trajectory = []
    positions = np.random.randn(num_atoms, 3)

    for _i in range(num_frames):
        # 添加小的随机扰动
        positions += np.random.randn(num_atoms, 3) * 0.1
        trajectory.append(positions.copy())

    return trajectory


# 注册插件
registry.register(
    name="openmm",
    description="分子动力学模拟与动画",
    module_name="openmm",
    license="MIT",
    fallback=_fallback_generate_trajectory,
)


def get_animator() -> MoleculeAnimator:
    """获取动画生成器实例"""
    return MoleculeAnimator()


def is_available() -> bool:
    """检查OpenMM是否可用"""
    return registry.is_available("openmm")
