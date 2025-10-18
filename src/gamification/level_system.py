"""
等级系统
管理用户经验值和等级
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LevelConfig:
    """等级配置"""

    base_exp: int = 100  # 基础经验值
    exp_multiplier: float = 1.5  # 经验倍率
    max_level: int = 100  # 最大等级


class UserLevel(BaseModel):
    """用户等级数据"""

    user_id: str = Field(..., description="用户ID")
    level: int = Field(default=1, ge=1, description="当前等级")
    exp: int = Field(default=0, ge=0, description="当前经验值")
    total_exp: int = Field(default=0, ge=0, description="总经验值")
    title: str = Field(default="化学新手", description="称号")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LevelSystem:
    """等级系统"""

    # 称号列表（对应等级段）
    TITLES = [
        (1, "化学新手"),
        (5, "实验学徒"),
        (10, "初级化学师"),
        (15, "化学爱好者"),
        (20, "中级化学师"),
        (25, "实验专家"),
        (30, "高级化学师"),
        (40, "化学大师"),
        (50, "实验宗师"),
        (60, "化学导师"),
        (70, "元素掌控者"),
        (80, "反应预言家"),
        (90, "化学泰斗"),
        (100, "诺贝尔候选人"),
    ]

    def __init__(self, config: LevelConfig | None = None):
        """初始化等级系统"""
        self.config = config or LevelConfig()

    def calculate_level_exp(self, level: int) -> int:
        """计算升到某级所需经验值

        Args:
            level: 目标等级

        Returns:
            所需经验值
        """
        if level <= 1:
            return 0
        return int(self.config.base_exp * math.pow(self.config.exp_multiplier, level - 1))

    def calculate_total_exp_for_level(self, level: int) -> int:
        """计算达到某等级需要的总经验值

        Args:
            level: 目标等级

        Returns:
            总经验值
        """
        total = 0
        for lv in range(1, level):
            total += self.calculate_level_exp(lv)
        return total

    def add_exp(self, user_level: UserLevel, exp_gained: int) -> dict[str, Any]:
        """增加经验值

        Args:
            user_level: 用户等级数据
            exp_gained: 获得的经验值

        Returns:
            包含升级信息的字典
        """
        result = {
            "exp_gained": exp_gained,
            "level_up": False,
            "new_level": user_level.level,
            "old_level": user_level.level,
            "new_title": user_level.title,
            "old_title": user_level.title,
        }

        # 增加经验值
        user_level.exp += exp_gained
        user_level.total_exp += exp_gained
        user_level.updated_at = datetime.now()

        # 检查是否升级
        while user_level.level < self.config.max_level:
            required_exp = self.calculate_level_exp(user_level.level + 1)

            if user_level.exp >= required_exp:
                # 升级
                user_level.exp -= required_exp
                user_level.level += 1
                result["level_up"] = True
                result["new_level"] = user_level.level

                logger.info(f"用户 {user_level.user_id} 升级到 {user_level.level}")
            else:
                break

        # 更新称号
        if result["level_up"]:
            old_title = user_level.title
            new_title = self.get_title(user_level.level)
            if new_title != old_title:
                result["old_title"] = old_title
                result["new_title"] = new_title
                user_level.title = new_title

        return result

    def get_title(self, level: int) -> str:
        """根据等级获取称号

        Args:
            level: 等级

        Returns:
            称号
        """
        title = "化学新手"
        for required_level, level_title in self.TITLES:
            if level >= required_level:
                title = level_title
            else:
                break
        return title

    def get_progress_to_next_level(self, user_level: UserLevel) -> dict[str, Any]:
        """获取到下一级的进度

        Args:
            user_level: 用户等级数据

        Returns:
            进度信息
        """
        if user_level.level >= self.config.max_level:
            return {
                "current_exp": user_level.exp,
                "required_exp": 0,
                "progress_percent": 100.0,
                "is_max_level": True,
            }

        required_exp = self.calculate_level_exp(user_level.level + 1)
        progress_percent = (user_level.exp / required_exp * 100) if required_exp > 0 else 0

        return {
            "current_exp": user_level.exp,
            "required_exp": required_exp,
            "progress_percent": progress_percent,
            "is_max_level": False,
        }

    def create_user_level(self, user_id: str) -> UserLevel:
        """创建新用户等级数据

        Args:
            user_id: 用户ID

        Returns:
            用户等级数据
        """
        return UserLevel(
            user_id=user_id,
            level=1,
            exp=0,
            total_exp=0,
            title=self.get_title(1),
        )
