"""
成就系统
管理用户成就和勋章
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AchievementType(str, Enum):
    """成就类型"""

    EXPERIMENT = "experiment"  # 实验相关
    SCORE = "score"  # 分数相关
    SPEED = "speed"  # 速度相关
    ACCURACY = "accuracy"  # 准确度相关
    STREAK = "streak"  # 连续完成
    SPECIAL = "special"  # 特殊成就


class Achievement(BaseModel):
    """成就定义"""

    id: str = Field(..., description="成就ID")
    name: str = Field(..., description="成就名称")
    description: str = Field(..., description="成就描述")
    type: AchievementType = Field(..., description="成就类型")
    icon: str = Field(default="🏆", description="图标")
    exp_reward: int = Field(default=0, ge=0, description="经验奖励")
    rarity: str = Field(default="common", description="稀有度: common/rare/epic/legendary")
    hidden: bool = Field(default=False, description="是否隐藏成就")

    # 完成条件
    condition_key: str = Field(..., description="条件键名")
    condition_value: Any = Field(..., description="条件目标值")

    class Config:
        use_enum_values = True


class UserAchievement(BaseModel):
    """用户成就记录"""

    achievement_id: str = Field(..., description="成就ID")
    user_id: str = Field(..., description="用户ID")
    unlocked_at: datetime = Field(default_factory=datetime.now, description="解锁时间")
    progress: float = Field(default=0.0, ge=0, le=100, description="完成进度")
    completed: bool = Field(default=False, description="是否完成")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AchievementManager:
    """成就管理器"""

    def __init__(self):
        """初始化成就管理器"""
        self.achievements: dict[str, Achievement] = {}
        self._initialize_achievements()

    def _initialize_achievements(self) -> None:
        """初始化预定义成就"""
        default_achievements = [
            # 实验相关
            Achievement(
                id="first_experiment",
                name="初次尝试",
                description="完成第一个实验",
                type=AchievementType.EXPERIMENT,
                icon="🧪",
                exp_reward=50,
                rarity="common",
                condition_key="experiments_completed",
                condition_value=1,
            ),
            Achievement(
                id="experiment_veteran",
                name="实验老手",
                description="完成10个实验",
                type=AchievementType.EXPERIMENT,
                icon="🔬",
                exp_reward=200,
                rarity="rare",
                condition_key="experiments_completed",
                condition_value=10,
            ),
            Achievement(
                id="experiment_master",
                name="实验大师",
                description="完成50个实验",
                type=AchievementType.EXPERIMENT,
                icon="⚗️",
                exp_reward=500,
                rarity="epic",
                condition_key="experiments_completed",
                condition_value=50,
            ),
            # 分数相关
            Achievement(
                id="perfect_score",
                name="完美实验",
                description="获得100分的完美实验",
                type=AchievementType.SCORE,
                icon="⭐",
                exp_reward=100,
                rarity="rare",
                condition_key="perfect_experiments",
                condition_value=1,
            ),
            Achievement(
                id="high_achiever",
                name="高分选手",
                description="累计获得1000分",
                type=AchievementType.SCORE,
                icon="🌟",
                exp_reward=300,
                rarity="epic",
                condition_key="total_score",
                condition_value=1000,
            ),
            # 速度相关
            Achievement(
                id="speed_runner",
                name="速通大师",
                description="在5分钟内完成一个实验",
                type=AchievementType.SPEED,
                icon="⚡",
                exp_reward=150,
                rarity="rare",
                condition_key="fast_completion",
                condition_value=300,  # 秒
            ),
            # 准确度相关
            Achievement(
                id="no_mistakes",
                name="零失误",
                description="完成一个实验且零错误",
                type=AchievementType.ACCURACY,
                icon="💯",
                exp_reward=120,
                rarity="rare",
                condition_key="zero_mistake_experiments",
                condition_value=1,
            ),
            Achievement(
                id="accuracy_king",
                name="精准之王",
                description="连续5个实验零错误",
                type=AchievementType.ACCURACY,
                icon="👑",
                exp_reward=400,
                rarity="epic",
                condition_key="zero_mistake_streak",
                condition_value=5,
            ),
            # 连续完成
            Achievement(
                id="daily_practice",
                name="每日练习",
                description="连续3天完成实验",
                type=AchievementType.STREAK,
                icon="📅",
                exp_reward=100,
                rarity="common",
                condition_key="daily_streak",
                condition_value=3,
            ),
            Achievement(
                id="dedication",
                name="坚持不懈",
                description="连续7天完成实验",
                type=AchievementType.STREAK,
                icon="🔥",
                exp_reward=300,
                rarity="rare",
                condition_key="daily_streak",
                condition_value=7,
            ),
            # 特殊成就
            Achievement(
                id="night_owl",
                name="夜猫子",
                description="在午夜完成实验",
                type=AchievementType.SPECIAL,
                icon="🦉",
                exp_reward=80,
                rarity="rare",
                hidden=True,
                condition_key="midnight_experiment",
                condition_value=1,
            ),
            Achievement(
                id="early_bird",
                name="早起鸟",
                description="在早上6点前完成实验",
                type=AchievementType.SPECIAL,
                icon="🐦",
                exp_reward=80,
                rarity="rare",
                hidden=True,
                condition_key="early_morning_experiment",
                condition_value=1,
            ),
        ]

        for achievement in default_achievements:
            self.achievements[achievement.id] = achievement

    def add_achievement(self, achievement: Achievement) -> None:
        """添加成就

        Args:
            achievement: 成就对象
        """
        self.achievements[achievement.id] = achievement
        logger.info(f"添加成就: {achievement.name} ({achievement.id})")

    def get_achievement(self, achievement_id: str) -> Achievement | None:
        """获取成就

        Args:
            achievement_id: 成就ID

        Returns:
            成就对象
        """
        return self.achievements.get(achievement_id)

    def get_all_achievements(self, include_hidden: bool = False) -> list[Achievement]:
        """获取所有成就

        Args:
            include_hidden: 是否包含隐藏成就

        Returns:
            成就列表
        """
        achievements = list(self.achievements.values())
        if not include_hidden:
            achievements = [a for a in achievements if not a.hidden]
        return achievements

    def check_achievement_unlock(self, achievement_id: str, user_stats: dict[str, Any]) -> tuple[bool, float]:
        """检查成就是否解锁

        Args:
            achievement_id: 成就ID
            user_stats: 用户统计数据

        Returns:
            (是否解锁, 完成进度百分比)
        """
        achievement = self.get_achievement(achievement_id)
        if not achievement:
            return False, 0.0

        condition_key = achievement.condition_key
        condition_value = achievement.condition_value
        current_value = user_stats.get(condition_key, 0)

        # 计算进度
        if isinstance(condition_value, (int, float)):
            progress = min(100.0, (current_value / condition_value) * 100)
            unlocked = current_value >= condition_value
        else:
            # 布尔类型条件
            unlocked = bool(current_value)
            progress = 100.0 if unlocked else 0.0

        return unlocked, progress

    def check_all_achievements(self, user_stats: dict[str, Any], unlocked_ids: set[str]) -> list[Achievement]:
        """检查所有成就，返回新解锁的成就

        Args:
            user_stats: 用户统计数据
            unlocked_ids: 已解锁的成就ID集合

        Returns:
            新解锁的成就列表
        """
        newly_unlocked = []

        for achievement_id, achievement in self.achievements.items():
            # 跳过已解锁的
            if achievement_id in unlocked_ids:
                continue

            # 检查是否解锁
            unlocked, _ = self.check_achievement_unlock(achievement_id, user_stats)
            if unlocked:
                newly_unlocked.append(achievement)
                logger.info(f"解锁成就: {achievement.name} ({achievement_id})")

        return newly_unlocked

    def get_rarity_color(self, rarity: str) -> str:
        """获取稀有度颜色

        Args:
            rarity: 稀有度

        Returns:
            颜色代码
        """
        colors = {
            "common": "#9E9E9E",
            "rare": "#2196F3",
            "epic": "#9C27B0",
            "legendary": "#FF9800",
        }
        return colors.get(rarity, "#9E9E9E")
