"""
任务系统
管理每日任务、挑战等
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuestType(str, Enum):
    """任务类型"""

    DAILY = "daily"  # 每日任务
    WEEKLY = "weekly"  # 每周任务
    ACHIEVEMENT = "achievement"  # 成就任务
    SPECIAL = "special"  # 特殊任务


class QuestStatus(str, Enum):
    """任务状态"""

    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    CLAIMED = "claimed"  # 已领取奖励
    EXPIRED = "expired"  # 已过期


class Quest(BaseModel):
    """任务定义"""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    type: QuestType = Field(..., description="任务类型")
    icon: str = Field(default="📋", description="图标")

    # 目标
    target_key: str = Field(..., description="目标键名")
    target_value: int = Field(..., description="目标值")

    # 奖励
    exp_reward: int = Field(default=0, ge=0, description="经验奖励")

    # 时间限制
    expires_at: datetime | None = Field(default=None, description="过期时间")

    @field_serializer("expires_at")
    def serialize_expires_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class UserQuest(BaseModel):
    """用户任务记录"""

    model_config = ConfigDict(use_enum_values=True)

    quest_id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    status: QuestStatus = Field(default=QuestStatus.ACTIVE, description="状态")
    progress: int = Field(default=0, ge=0, description="当前进度")
    target: int = Field(..., description="目标值")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    claimed_at: datetime | None = Field(default=None, description="领取时间")

    @field_serializer("started_at", "completed_at", "claimed_at")
    def serialize_datetimes(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.progress >= self.target

    @property
    def progress_percent(self) -> float:
        """完成百分比"""
        if self.target == 0:
            return 100.0
        return min(100.0, (self.progress / self.target) * 100)


class QuestManager:
    """任务管理器"""

    def __init__(self):
        """初始化任务管理器"""
        self.quests: dict[str, Quest] = {}
        self._initialize_quests()

    def _initialize_quests(self) -> None:
        """初始化预定义任务模板"""
        # 每日任务模板
        self.daily_quest_templates = [
            {
                "id": "daily_complete_1",
                "name": "每日一练",
                "description": "完成1个实验",
                "icon": "📚",
                "target_key": "experiments_completed_today",
                "target_value": 1,
                "exp_reward": 50,
            },
            {
                "id": "daily_complete_3",
                "name": "勤奋学习",
                "description": "完成3个实验",
                "icon": "📖",
                "target_key": "experiments_completed_today",
                "target_value": 3,
                "exp_reward": 150,
            },
            {
                "id": "daily_perfect",
                "name": "今日完美",
                "description": "获得一次满分",
                "icon": "⭐",
                "target_key": "perfect_scores_today",
                "target_value": 1,
                "exp_reward": 100,
            },
        ]

        # 每周任务模板
        self.weekly_quest_templates = [
            {
                "id": "weekly_complete_10",
                "name": "周常任务",
                "description": "本周完成10个实验",
                "icon": "🎯",
                "target_key": "experiments_completed_this_week",
                "target_value": 10,
                "exp_reward": 500,
            },
            {
                "id": "weekly_score_500",
                "name": "周积分挑战",
                "description": "本周累计获得500分",
                "icon": "🏆",
                "target_key": "total_score_this_week",
                "target_value": 500,
                "exp_reward": 400,
            },
        ]

    def create_daily_quests(self) -> list[Quest]:
        """创建每日任务

        Returns:
            每日任务列表
        """
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_start = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)

        quests = []
        for template in self.daily_quest_templates:
            quest_data = template.copy()
            quest_data["type"] = QuestType.DAILY
            quest_data["expires_at"] = tomorrow_start
            quest = Quest(**quest_data)
            quests.append(quest)
            self.quests[quest.id] = quest

        logger.info(f"创建 {len(quests)} 个每日任务")
        return quests

    def create_weekly_quests(self) -> list[Quest]:
        """创建每周任务

        Returns:
            每周任务列表
        """
        # 计算下周一的开始时间
        now = datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = now + timedelta(days=days_until_monday)
        next_monday_start = datetime(
            next_monday.year, next_monday.month, next_monday.day, 0, 0, 0
        )

        quests = []
        for template in self.weekly_quest_templates:
            quest_data = template.copy()
            quest_data["type"] = QuestType.WEEKLY
            quest_data["expires_at"] = next_monday_start
            quest = Quest(**quest_data)
            quests.append(quest)
            self.quests[quest.id] = quest

        logger.info(f"创建 {len(quests)} 个每周任务")
        return quests

    def update_quest_progress(self, user_quest: UserQuest, increment: int = 1) -> bool:
        """更新任务进度

        Args:
            user_quest: 用户任务
            increment: 增加的进度值

        Returns:
            是否完成任务
        """
        if user_quest.status != QuestStatus.ACTIVE:
            return False

        user_quest.progress += increment

        # 检查是否完成
        if user_quest.is_completed and user_quest.status == QuestStatus.ACTIVE:
            user_quest.status = QuestStatus.COMPLETED
            user_quest.completed_at = datetime.now()
            logger.info(f"任务完成: {user_quest.quest_id}")
            return True

        return False

    def claim_reward(self, user_quest: UserQuest) -> bool:
        """领取任务奖励

        Args:
            user_quest: 用户任务

        Returns:
            是否成功领取
        """
        if user_quest.status != QuestStatus.COMPLETED:
            return False

        user_quest.status = QuestStatus.CLAIMED
        user_quest.claimed_at = datetime.now()
        logger.info(f"领取任务奖励: {user_quest.quest_id}")
        return True

    def check_expired_quests(self, user_quests: list[UserQuest]) -> list[UserQuest]:
        """检查过期任务

        Args:
            user_quests: 用户任务列表

        Returns:
            过期的任务列表
        """
        now = datetime.now()
        expired = []

        for user_quest in user_quests:
            if user_quest.status in [QuestStatus.COMPLETED, QuestStatus.CLAIMED]:
                continue

            quest = self.quests.get(user_quest.quest_id)
            if quest and quest.expires_at and now >= quest.expires_at:
                user_quest.status = QuestStatus.EXPIRED
                expired.append(user_quest)
                logger.info(f"任务过期: {user_quest.quest_id}")

        return expired

    def get_quest(self, quest_id: str) -> Quest | None:
        """获取任务

        Args:
            quest_id: 任务ID

        Returns:
            任务对象
        """
        return self.quests.get(quest_id)
