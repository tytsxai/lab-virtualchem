"""实验相关接口定义"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from ..models.experiment import ExperimentTemplate, Step
from ..models.user_record import Mistake, UserRecord


class IExperimentEngine(ABC):
    """实验引擎接口"""

    @abstractmethod
    def initialize(self, template: ExperimentTemplate, user_id: str) -> None:
        """初始化实验

        Args:
            template: 实验模板
            user_id: 用户ID
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """开始实验"""
        pass

    @abstractmethod
    def get_current_step(self) -> Step | None:
        """获取当前步骤

        Returns:
            当前步骤对象,无则返回None
        """
        pass

    @abstractmethod
    def submit_step(self, user_input: dict[str, Any]) -> tuple[bool, str, Mistake | None]:
        """提交步骤

        Args:
            user_input: 用户输入

        Returns:
            (是否通过, 提示信息, 错误对象)
        """
        pass

    @abstractmethod
    def next_step(self) -> bool:
        """进入下一步

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def previous_step(self) -> bool:
        """返回上一步

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def complete(self) -> UserRecord:
        """完成实验

        Returns:
            用户记录
        """
        pass

    @abstractmethod
    def get_progress(self) -> dict[str, Any]:
        """获取实验进度

        Returns:
            进度信息字典
        """
        pass

    @abstractmethod
    def get_record(self) -> UserRecord:
        """获取实验记录

        Returns:
            用户记录对象
        """
        pass


class IExperimentValidator(ABC):
    """实验验证器接口"""

    @abstractmethod
    def check_step(self, step: Step, user_input: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
        """验证步骤

        Args:
            step: 步骤对象
            user_input: 用户输入
            context: 上下文数据

        Returns:
            (是否通过, 提示信息)
        """
        pass

    @abstractmethod
    def evaluate_score(self, score_rules: list[dict[str, Any]], context: dict[str, Any]) -> tuple[int, dict[str, int]]:
        """评估分数

        Args:
            score_rules: 评分规则列表
            context: 评分上下文

        Returns:
            (总分, 分项详情)
        """
        pass

    @abstractmethod
    def validate_dependencies(self, step: Step, context: dict[str, Any]) -> bool:
        """验证依赖关系

        Args:
            step: 步骤对象
            context: 上下文数据

        Returns:
            是否满足依赖
        """
        pass


class ICurveGenerator(ABC):
    """曲线生成器接口"""

    @abstractmethod
    def generate(self, curve_type: str, params: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
        """生成曲线数据

        Args:
            curve_type: 曲线类型
            params: 参数字典

        Returns:
            (x轴数据, y轴数据)
        """
        pass

    @abstractmethod
    def register_curve_type(self, curve_type: str, generator_func: Any) -> None:
        """注册曲线类型

        Args:
            curve_type: 曲线类型标识
            generator_func: 生成函数
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """获取支持的曲线类型

        Returns:
            曲线类型列表
        """
        pass


class ISafetyChecker(ABC):
    """安全检查器接口"""

    @abstractmethod
    def check_temperature(self, temperature: float, reagents: list[str]) -> tuple[bool, str]:
        """检查温度安全

        Args:
            temperature: 温度值
            reagents: 试剂列表

        Returns:
            (是否安全, 警告信息)
        """
        pass

    @abstractmethod
    def check_mixing(self, reagent1: str, reagent2: str) -> tuple[bool, str]:
        """检查混合安全

        Args:
            reagent1: 试剂1
            reagent2: 试剂2

        Returns:
            (是否安全, 警告信息)
        """
        pass

    @abstractmethod
    def check_protection(self, operation: str, protection: list[str]) -> tuple[bool, str]:
        """检查防护措施

        Args:
            operation: 操作类型
            protection: 防护用品列表

        Returns:
            (是否充分, 建议信息)
        """
        pass
