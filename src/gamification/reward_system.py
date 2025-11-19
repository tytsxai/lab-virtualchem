"""
奖励系统
管理用户奖励和虚拟物品
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RewardType(str, Enum):
    """奖励类型"""

    EXP = "exp"  # 经验值
    BADGE = "badge"  # 徽章
    AVATAR = "avatar"  # 头像框
    TITLE = "title"  # 称号
    THEME = "theme"  # 主题


class Reward(BaseModel):
    """奖励定义"""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="奖励ID")
    name: str = Field(..., description="奖励名称")
    description: str = Field(..., description="奖励描述")
    type: RewardType = Field(..., description="奖励类型")
    icon: str = Field(default="🎁", description="图标")
    rarity: str = Field(default="common", description="稀有度")

class UserReward(BaseModel):
    """用户奖励记录"""

    reward_id: str = Field(..., description="奖励ID")
    user_id: str = Field(..., description="用户ID")
    obtained_at: datetime = Field(default_factory=datetime.now, description="获得时间")
    equipped: bool = Field(default=False, description="是否装备")

    @field_serializer("obtained_at")
    def serialize_obtained_at(self, value: datetime) -> str:
        return value.isoformat()

class RewardManager:
    """奖励管理器"""

    def __init__(self):
        """初始化奖励管理器"""
        self.rewards: dict[str, Reward] = {}
        self._initialize_rewards()

    def _initialize_rewards(self) -> None:
        """初始化预定义奖励"""
        default_rewards = [
            # 徽章
            Reward(
                id="badge_first_exp",
                name="初心徽章",
                description="完成第一个实验",
                type=RewardType.BADGE,
                icon="🎖️",
                rarity="common",
            ),
            Reward(
                id="badge_perfect",
                name="完美徽章",
                description="获得满分",
                type=RewardType.BADGE,
                icon="💎",
                rarity="rare",
            ),
            # 头像框
            Reward(
                id="avatar_bronze",
                name="青铜框",
                description="达到10级解锁",
                type=RewardType.AVATAR,
                icon="🔶",
                rarity="common",
            ),
            Reward(
                id="avatar_silver",
                name="白银框",
                description="达到20级解锁",
                type=RewardType.AVATAR,
                icon="⬜",
                rarity="rare",
            ),
            Reward(
                id="avatar_gold",
                name="黄金框",
                description="达到30级解锁",
                type=RewardType.AVATAR,
                icon="🔸",
                rarity="epic",
            ),
            # 主题
            Reward(
                id="theme_dark",
                name="暗夜主题",
                description="暗色系主题",
                type=RewardType.THEME,
                icon="🌙",
                rarity="common",
            ),
            Reward(
                id="theme_rainbow",
                name="彩虹主题",
                description="多彩主题",
                type=RewardType.THEME,
                icon="🌈",
                rarity="rare",
            ),
        ]

        for reward in default_rewards:
            self.rewards[reward.id] = reward

    def add_reward(self, reward: Reward) -> None:
        """添加奖励

        Args:
            reward: 奖励对象
        """
        self.rewards[reward.id] = reward
        logger.info(f"添加奖励: {reward.name} ({reward.id})")

    def get_reward(self, reward_id: str) -> Reward | None:
        """获取奖励

        Args:
            reward_id: 奖励ID

        Returns:
            奖励对象
        """
        return self.rewards.get(reward_id)

    def get_all_rewards(self) -> list[Reward]:
        """获取所有奖励

        Returns:
            奖励列表
        """
        return list(self.rewards.values())

    def get_rewards_by_type(self, reward_type: RewardType) -> list[Reward]:
        """根据类型获取奖励

        Args:
            reward_type: 奖励类型

        Returns:
            奖励列表
        """
        return [r for r in self.rewards.values() if r.type == reward_type]
