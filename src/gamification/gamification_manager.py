"""
游戏化管理器
统一管理所有游戏化功能
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer

from ..storage.json_store import JSONStore
from ..utils.logger import get_logger
from .achievement_system import AchievementManager, UserAchievement
from .level_system import LevelSystem, UserLevel
from .quest_system import QuestManager, QuestStatus, UserQuest
from .reward_system import RewardManager, UserReward

logger = get_logger(__name__)


class UserStats(BaseModel):
    """用户统计数据"""

    user_id: str = Field(..., description="用户ID")

    # 实验统计
    experiments_completed: int = Field(default=0, ge=0, description="完成的实验总数")
    experiments_completed_today: int = Field(
        default=0, ge=0, description="今日完成的实验数"
    )
    experiments_completed_this_week: int = Field(
        default=0, ge=0, description="本周完成的实验数"
    )
    perfect_experiments: int = Field(default=0, ge=0, description="满分实验数")
    perfect_scores_today: int = Field(default=0, ge=0, description="今日满分数")
    zero_mistake_experiments: int = Field(default=0, ge=0, description="零失误实验数")
    zero_mistake_streak: int = Field(default=0, ge=0, description="连续零失误次数")

    # 分数统计
    total_score: int = Field(default=0, ge=0, description="总分数")
    total_score_this_week: int = Field(default=0, ge=0, description="本周总分")
    average_score: float = Field(default=0.0, ge=0, description="平均分数")

    # 时间统计
    total_time_spent: int = Field(default=0, ge=0, description="总学习时间（秒）")
    fast_completion: int = Field(default=0, ge=0, description="快速完成次数")

    # 连续统计
    daily_streak: int = Field(default=0, ge=0, description="连续天数")
    last_activity_date: str | None = Field(default=None, description="最后活动日期")

    # 特殊统计
    midnight_experiment: int = Field(default=0, ge=0, description="午夜实验数")
    early_morning_experiment: int = Field(default=0, ge=0, description="早晨实验数")

    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        return value.isoformat()


class GamificationData(BaseModel):
    """用户游戏化数据"""

    user_id: str = Field(..., description="用户ID")
    level: UserLevel = Field(..., description="等级数据")
    stats: UserStats = Field(..., description="统计数据")
    achievements: list[UserAchievement] = Field(
        default_factory=list, description="成就列表"
    )
    quests: list[UserQuest] = Field(default_factory=list, description="任务列表")
    rewards: list[UserReward] = Field(default_factory=list, description="奖励列表")


class GamificationManager:
    """游戏化管理器"""

    def __init__(self, storage: JSONStore | None = None):
        """初始化游戏化管理器

        Args:
            storage: 存储服务
        """
        self.storage = storage or JSONStore()
        self.level_system = LevelSystem()
        self.achievement_manager = AchievementManager()
        self.quest_manager = QuestManager()
        self.reward_manager = RewardManager()

        logger.info("游戏化管理器初始化完成")

    def get_or_create_user_data(self, user_id: str) -> GamificationData:
        """获取或创建用户游戏化数据

        Args:
            user_id: 用户ID

        Returns:
            游戏化数据
        """
        # 尝试从存储加载
        try:
            data_dict = self.storage.get(f"gamification/{user_id}")
        except Exception:
            data_dict = None

        if data_dict:
            try:
                return GamificationData(**data_dict)
            except Exception as e:
                logger.warning(f"加载游戏化数据失败: {e}，创建新数据")

        # 创建新数据
        level = self.level_system.create_user_level(user_id)
        stats = UserStats(user_id=user_id)
        data = GamificationData(user_id=user_id, level=level, stats=stats)

        # 创建每日任务
        daily_quests = self.quest_manager.create_daily_quests()
        for quest in daily_quests:
            user_quest = UserQuest(
                quest_id=quest.id,
                user_id=user_id,
                target=quest.target_value,
                status=QuestStatus.ACTIVE,
            )
            data.quests.append(user_quest)

        self.save_user_data(data)
        logger.info(f"创建新用户游戏化数据: {user_id}")
        return data

    def save_user_data(self, data: GamificationData) -> None:
        """保存用户游戏化数据

        Args:
            data: 游戏化数据
        """
        self.storage.set(f"gamification/{data.user_id}", data.dict())

    def on_experiment_completed(
        self, user_id: str, score: float, duration_seconds: int, mistake_count: int
    ) -> dict[str, Any]:
        """实验完成事件处理

        Args:
            user_id: 用户ID
            score: 分数
            duration_seconds: 耗时（秒）
            mistake_count: 错误数

        Returns:
            事件结果（包含升级、解锁成就等信息）
        """
        data = self.get_or_create_user_data(user_id)
        result = {
            "level_up": False,
            "new_achievements": [],
            "completed_quests": [],
            "exp_gained": 0,
        }

        # 更新统计数据
        self._update_stats_on_experiment(
            data.stats, score, duration_seconds, mistake_count
        )

        # 计算经验值
        base_exp = int(score)  # 基础经验 = 分数
        if mistake_count == 0:
            base_exp = int(base_exp * 1.2)  # 零失误额外20%
        if duration_seconds < 300:  # 5分钟内完成
            base_exp = int(base_exp * 1.1)  # 快速完成额外10%

        # 增加经验值
        level_result = self.level_system.add_exp(data.level, base_exp)
        result["exp_gained"] = base_exp
        result["level_up"] = level_result["level_up"]
        result["level_info"] = level_result

        # 检查成就
        unlocked_ids = {a.achievement_id for a in data.achievements if a.completed}
        newly_unlocked = self.achievement_manager.check_all_achievements(
            data.stats.dict(), unlocked_ids
        )

        for achievement in newly_unlocked:
            user_achievement = UserAchievement(
                achievement_id=achievement.id,
                user_id=user_id,
                progress=100.0,
                completed=True,
            )
            data.achievements.append(user_achievement)
            result["new_achievements"].append(achievement)

            # 成就奖励经验
            if achievement.exp_reward > 0:
                self.level_system.add_exp(data.level, achievement.exp_reward)
                result["exp_gained"] += achievement.exp_reward

        # 更新任务进度
        self._update_quest_progress(data, result)

        # 保存数据
        self.save_user_data(data)

        logger.info(
            f"实验完成事件: 用户={user_id}, 经验+{result['exp_gained']}, "
            f"升级={result['level_up']}, 新成就={len(result['new_achievements'])}"
        )

        return result

    def _update_stats_on_experiment(
        self, stats: UserStats, score: float, duration_seconds: int, mistake_count: int
    ) -> None:
        """更新实验统计数据"""
        stats.experiments_completed += 1
        stats.experiments_completed_today += 1
        stats.experiments_completed_this_week += 1

        stats.total_score += int(score)
        stats.total_score_this_week += int(score)
        stats.average_score = stats.total_score / stats.experiments_completed

        if score >= 100:
            stats.perfect_experiments += 1
            stats.perfect_scores_today += 1

        if mistake_count == 0:
            stats.zero_mistake_experiments += 1
            stats.zero_mistake_streak += 1
        else:
            stats.zero_mistake_streak = 0

        if duration_seconds < 300:
            stats.fast_completion += 1

        stats.total_time_spent += duration_seconds

        # 检查连续天数
        today = datetime.now().strftime("%Y-%m-%d")
        if stats.last_activity_date != today:
            if stats.last_activity_date:
                last_date = datetime.strptime(stats.last_activity_date, "%Y-%m-%d")
                today_date = datetime.strptime(today, "%Y-%m-%d")
                days_diff = (today_date - last_date).days

                if days_diff == 1:
                    stats.daily_streak += 1
                else:
                    stats.daily_streak = 1
            else:
                stats.daily_streak = 1

            stats.last_activity_date = today

        # 特殊时间统计
        hour = datetime.now().hour
        if hour == 0:
            stats.midnight_experiment += 1
        elif hour < 6:
            stats.early_morning_experiment += 1

        stats.updated_at = datetime.now()

    def _update_quest_progress(
        self, data: GamificationData, result: dict[str, Any]
    ) -> None:
        """更新任务进度"""
        for user_quest in data.quests:
            if user_quest.status != QuestStatus.ACTIVE:
                continue

            quest = self.quest_manager.get_quest(user_quest.quest_id)
            if not quest:
                continue

            # 根据任务的目标键更新进度
            target_key = quest.target_key
            current_value = getattr(data.stats, target_key, 0)
            user_quest.progress = current_value

            # 检查是否完成
            if self.quest_manager.update_quest_progress(
                user_quest, 0
            ):  # 使用0增量，只检查状态
                result["completed_quests"].append(quest)

    def claim_quest_reward(self, user_id: str, quest_id: str) -> dict[str, Any]:
        """领取任务奖励

        Args:
            user_id: 用户ID
            quest_id: 任务ID

        Returns:
            领取结果
        """
        data = self.get_or_create_user_data(user_id)
        result = {"success": False, "exp_gained": 0}

        # 查找任务
        user_quest = next((q for q in data.quests if q.quest_id == quest_id), None)
        if not user_quest:
            return result

        # 领取奖励
        if self.quest_manager.claim_reward(user_quest):
            quest = self.quest_manager.get_quest(quest_id)
            if quest:
                # 给予经验奖励
                self.level_system.add_exp(data.level, quest.exp_reward)
                result["exp_gained"] = quest.exp_reward
                result["success"] = True

                self.save_user_data(data)
                logger.info(
                    f"领取任务奖励: 用户={user_id}, 任务={quest_id}, 经验+{quest.exp_reward}"
                )

        return result

    def get_user_progress(self, user_id: str) -> dict[str, Any]:
        """获取用户进度信息

        Args:
            user_id: 用户ID

        Returns:
            进度信息
        """
        data = self.get_or_create_user_data(user_id)
        progress_info = self.level_system.get_progress_to_next_level(data.level)

        return {
            "level": data.level.level,
            "title": data.level.title,
            "exp": data.level.exp,
            "total_exp": data.level.total_exp,
            "next_level_exp": progress_info["required_exp"],
            "progress_percent": progress_info["progress_percent"],
            "stats": data.stats.dict(),
            "achievement_count": len([a for a in data.achievements if a.completed]),
            "total_achievements": len(self.achievement_manager.get_all_achievements()),
        }
