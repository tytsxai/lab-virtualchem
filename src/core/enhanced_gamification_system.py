#!/usr/bin/env python3
"""
增强的游戏化系统
提供成就系统、积分系统、排行榜、个性化奖励等功能
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .robustness_integration import enhance_robustness, validate_input, log_operation

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """成就类型"""
    EXPERIMENT_COMPLETION = "experiment_completion"
    ACCURACY_MASTERY = "accuracy_mastery"
    SPEED_DEMON = "speed_demon"
    SAFETY_CHAMPION = "safety_champion"
    LEARNING_STREAK = "learning_streak"
    COLLECTION = "collection"
    SOCIAL = "social"
    SPECIAL = "special"


class RewardType(Enum):
    """奖励类型"""
    POINTS = "points"
    BADGE = "badge"
    TITLE = "title"
    AVATAR = "avatar"
    THEME = "theme"
    FEATURE = "feature"
    CURRENCY = "currency"


class DifficultyLevel(Enum):
    """难度等级"""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class Achievement:
    """成就定义"""
    id: str
    name: str
    description: str
    type: AchievementType
    difficulty: DifficultyLevel
    requirements: Dict[str, Any]
    rewards: List[Dict[str, Any]]
    icon: str
    rarity: str = "common"  # common, rare, epic, legendary
    hidden: bool = False
    category: str = "general"


@dataclass
class UserAchievement:
    """用户成就"""
    achievement_id: str
    user_id: str
    unlocked_at: datetime
    progress: Dict[str, Any] = field(default_factory=dict)
    is_unlocked: bool = False


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    username: str
    level: int = 1
    experience_points: int = 0
    total_points: int = 0
    badges: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    avatar: str = "default"
    theme: str = "default"
    unlocked_features: Set[str] = field(default_factory=set)
    currency: Dict[str, int] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    user_id: str
    username: str
    score: float
    rank: int
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reward:
    """奖励"""
    type: RewardType
    value: Any
    name: str
    description: str
    icon: str
    rarity: str = "common"


class EnhancedGamificationSystem:
    """增强的游戏化系统"""

    def __init__(self):
        self.achievements: Dict[str, Achievement] = {}
        self.user_achievements: Dict[str, List[UserAchievement]] = {}
        self.user_profiles: Dict[str, UserProfile] = {}
        self.leaderboards: Dict[str, List[LeaderboardEntry]] = {}
        self.rewards: Dict[str, Reward] = {}

        # 初始化系统
        self._initialize_achievements()
        self._initialize_rewards()
        self._initialize_leaderboards()

    def _initialize_achievements(self) -> None:
        """初始化成就系统"""
        achievements_data = [
            {
                "id": "first_experiment",
                "name": "初次实验",
                "description": "完成第一次实验",
                "type": AchievementType.EXPERIMENT_COMPLETION,
                "difficulty": DifficultyLevel.EASY,
                "requirements": {"experiments_completed": 1},
                "rewards": [{"type": "points", "value": 100}],
                "icon": "🎯",
                "rarity": "common"
            },
            {
                "id": "accuracy_master",
                "name": "精准大师",
                "description": "连续5次实验准确率达到90%以上",
                "type": AchievementType.ACCURACY_MASTERY,
                "difficulty": DifficultyLevel.HARD,
                "requirements": {"consecutive_high_accuracy": 5, "accuracy_threshold": 0.9},
                "rewards": [{"type": "badge", "value": "accuracy_master"}, {"type": "points", "value": 500}],
                "icon": "🎯",
                "rarity": "rare"
            },
            {
                "id": "speed_demon",
                "name": "速度恶魔",
                "description": "在30秒内完成基础实验",
                "type": AchievementType.SPEED_DEMON,
                "difficulty": DifficultyLevel.HARD,
                "requirements": {"max_time": 30, "experiment_type": "basic"},
                "rewards": [{"type": "title", "value": "速度恶魔"}, {"type": "points", "value": 300}],
                "icon": "⚡",
                "rarity": "epic"
            },
            {
                "id": "safety_champion",
                "name": "安全冠军",
                "description": "连续10次实验无安全事故",
                "type": AchievementType.SAFETY_CHAMPION,
                "difficulty": DifficultyLevel.EXPERT,
                "requirements": {"consecutive_safe_experiments": 10},
                "rewards": [{"type": "badge", "value": "safety_champion"}, {"type": "theme", "value": "safety"}],
                "icon": "🛡️",
                "rarity": "legendary"
            },
            {
                "id": "learning_streak",
                "name": "学习连胜",
                "description": "连续7天完成实验",
                "type": AchievementType.LEARNING_STREAK,
                "difficulty": DifficultyLevel.NORMAL,
                "requirements": {"consecutive_days": 7},
                "rewards": [{"type": "points", "value": 200}, {"type": "currency", "value": 50}],
                "icon": "🔥",
                "rarity": "rare"
            }
        ]

        for data in achievements_data:
            achievement = Achievement(**data)
            self.achievements[achievement.id] = achievement

    def _initialize_rewards(self) -> None:
        """初始化奖励系统"""
        rewards_data = [
            {
                "id": "points_100",
                "type": RewardType.POINTS,
                "value": 100,
                "name": "100积分",
                "description": "获得100个积分",
                "icon": "💰",
                "rarity": "common"
            },
            {
                "id": "badge_accuracy_master",
                "type": RewardType.BADGE,
                "value": "accuracy_master",
                "name": "精准大师徽章",
                "description": "精准大师专属徽章",
                "icon": "🏆",
                "rarity": "rare"
            },
            {
                "id": "title_speed_demon",
                "type": RewardType.TITLE,
                "value": "速度恶魔",
                "name": "速度恶魔称号",
                "description": "速度恶魔专属称号",
                "icon": "👑",
                "rarity": "epic"
            },
            {
                "id": "theme_safety",
                "type": RewardType.THEME,
                "value": "safety",
                "name": "安全主题",
                "description": "安全主题界面",
                "icon": "🎨",
                "rarity": "legendary"
            }
        ]

        for data in rewards_data:
            reward = Reward(**data)
            self.rewards[reward.id] = reward

    def _initialize_leaderboards(self) -> None:
        """初始化排行榜"""
        self.leaderboards = {
            "total_points": [],
            "accuracy": [],
            "speed": [],
            "safety": [],
            "weekly": [],
            "monthly": []
        }

    @enhance_robustness(
        operation_name="create_user_profile",
        security_level="medium",
        enable_caching=True
    )
    @validate_input(validation_rules={
        "user_id": {"type": str, "required": True},
        "username": {"type": str, "required": True}
    })
    @log_operation(operation_name="create_profile")
    def create_user_profile(self, user_id: str, username: str) -> UserProfile:
        """创建用户档案"""
        logger.info(f"创建用户档案: {user_id} - {username}")

        profile = UserProfile(
            user_id=user_id,
            username=username,
            currency={"coins": 0, "gems": 0},
            statistics={
                "experiments_completed": 0,
                "total_time": 0,
                "average_accuracy": 0.0,
                "best_accuracy": 0.0,
                "streak_days": 0,
                "last_experiment_date": None
            }
        )

        self.user_profiles[user_id] = profile
        self.user_achievements[user_id] = []

        # 记录用户创建事件
        self._log_gamification_event(user_id, "profile_created", {
            "username": username,
            "created_at": profile.created_at.isoformat()
        })

        return profile

    @enhance_robustness(
        operation_name="update_user_progress",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="update_progress")
    def update_user_progress(
        self,
        user_id: str,
        experiment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新用户进度"""
        if user_id not in self.user_profiles:
            logger.warning(f"用户 {user_id} 档案不存在")
            return {}

        profile = self.user_profiles[user_id]
        profile.last_active = datetime.now()

        # 更新统计数据
        self._update_statistics(profile, experiment_data)

        # 计算经验值和等级
        old_level = profile.level
        self._calculate_experience_and_level(profile, experiment_data)

        # 检查成就
        unlocked_achievements = self._check_achievements(user_id, experiment_data)

        # 更新排行榜
        self._update_leaderboards(user_id, profile)

        # 记录进度更新事件
        self._log_gamification_event(user_id, "progress_updated", {
            "old_level": old_level,
            "new_level": profile.level,
            "experience_gained": experiment_data.get("experience_gained", 0),
            "unlocked_achievements": [a.achievement_id for a in unlocked_achievements]
        })

        return {
            "level_up": profile.level > old_level,
            "new_level": profile.level,
            "experience_points": profile.experience_points,
            "unlocked_achievements": unlocked_achievements,
            "total_points": profile.total_points
        }

    def _update_statistics(self, profile: UserProfile, experiment_data: Dict[str, Any]) -> None:
        """更新统计数据"""
        stats = profile.statistics

        # 更新实验完成数
        stats["experiments_completed"] += 1

        # 更新总时间
        duration = experiment_data.get("duration", 0)
        stats["total_time"] += duration

        # 更新准确率
        accuracy = experiment_data.get("accuracy", 0.0)
        if accuracy > stats["best_accuracy"]:
            stats["best_accuracy"] = accuracy

        # 计算平均准确率
        total_experiments = stats["experiments_completed"]
        current_avg = stats["average_accuracy"]
        stats["average_accuracy"] = (current_avg * (total_experiments - 1) + accuracy) / total_experiments

        # 更新连续天数
        today = datetime.now().date()
        last_date = stats.get("last_experiment_date")
        if last_date:
            last_date = datetime.fromisoformat(last_date).date()
            if today == last_date:
                # 同一天，不增加连续天数
                pass
            elif (today - last_date).days == 1:
                # 连续一天
                stats["streak_days"] += 1
            else:
                # 中断了连续
                stats["streak_days"] = 1
        else:
            stats["streak_days"] = 1

        stats["last_experiment_date"] = today.isoformat()

    def _calculate_experience_and_level(self, profile: UserProfile, experiment_data: Dict[str, Any]) -> None:
        """计算经验值和等级"""
        # 基础经验值
        base_exp = experiment_data.get("base_experience", 50)

        # 准确率奖励
        accuracy = experiment_data.get("accuracy", 0.0)
        accuracy_bonus = int(accuracy * 100)

        # 速度奖励
        duration = experiment_data.get("duration", 0)
        speed_bonus = max(0, 50 - int(duration / 10))

        # 安全性奖励
        safety_score = experiment_data.get("safety_score", 0.0)
        safety_bonus = int(safety_score * 50)

        # 总经验值
        total_exp = base_exp + accuracy_bonus + speed_bonus + safety_bonus

        # 更新经验值
        profile.experience_points += total_exp
        profile.total_points += total_exp

        # 计算等级
        new_level = self._calculate_level(profile.experience_points)
        profile.level = new_level

        # 记录经验值获得
        experiment_data["experience_gained"] = total_exp

    def _calculate_level(self, experience_points: int) -> int:
        """计算等级"""
        # 等级计算公式: level = sqrt(experience / 100) + 1
        import math
        return int(math.sqrt(experience_points / 100)) + 1

    def _check_achievements(self, user_id: str, experiment_data: Dict[str, Any]) -> List[UserAchievement]:
        """检查成就解锁"""
        if user_id not in self.user_achievements:
            return []

        profile = self.user_profiles[user_id]
        user_achievements = self.user_achievements[user_id]
        unlocked_achievements = []

        for achievement_id, achievement in self.achievements.items():
            # 检查是否已经解锁
            if any(ua.achievement_id == achievement_id and ua.is_unlocked for ua in user_achievements):
                continue

            # 检查成就条件
            if self._check_achievement_requirements(achievement, profile, experiment_data):
                # 解锁成就
                user_achievement = UserAchievement(
                    achievement_id=achievement_id,
                    user_id=user_id,
                    unlocked_at=datetime.now(),
                    is_unlocked=True
                )
                user_achievements.append(user_achievement)
                unlocked_achievements.append(user_achievement)

                # 发放奖励
                self._grant_rewards(user_id, achievement.rewards)

                # 记录成就解锁事件
                self._log_gamification_event(user_id, "achievement_unlocked", {
                    "achievement_id": achievement_id,
                    "achievement_name": achievement.name,
                    "rewards": achievement.rewards
                })

        return unlocked_achievements

    def _check_achievement_requirements(
        self,
        achievement: Achievement,
        profile: UserProfile,
        experiment_data: Dict[str, Any]
    ) -> bool:
        """检查成就要求"""
        requirements = achievement.requirements

        if achievement.type == AchievementType.EXPERIMENT_COMPLETION:
            required_count = requirements.get("experiments_completed", 1)
            return profile.statistics["experiments_completed"] >= required_count

        elif achievement.type == AchievementType.ACCURACY_MASTERY:
            consecutive_count = requirements.get("consecutive_high_accuracy", 5)
            threshold = requirements.get("accuracy_threshold", 0.9)
            # 这里需要检查连续高准确率，简化实现
            return experiment_data.get("accuracy", 0.0) >= threshold

        elif achievement.type == AchievementType.SPEED_DEMON:
            max_time = requirements.get("max_time", 30)
            return experiment_data.get("duration", 0) <= max_time

        elif achievement.type == AchievementType.SAFETY_CHAMPION:
            consecutive_count = requirements.get("consecutive_safe_experiments", 10)
            return profile.statistics["streak_days"] >= consecutive_count

        elif achievement.type == AchievementType.LEARNING_STREAK:
            consecutive_days = requirements.get("consecutive_days", 7)
            return profile.statistics["streak_days"] >= consecutive_days

        return False

    def _grant_rewards(self, user_id: str, rewards: List[Dict[str, Any]]) -> None:
        """发放奖励"""
        if user_id not in self.user_profiles:
            return

        profile = self.user_profiles[user_id]

        for reward_data in rewards:
            reward_type = reward_data.get("type")
            reward_value = reward_data.get("value")

            if reward_type == "points":
                profile.total_points += reward_value
            elif reward_type == "badge":
                if reward_value not in profile.badges:
                    profile.badges.append(reward_value)
            elif reward_type == "title":
                if reward_value not in profile.titles:
                    profile.titles.append(reward_value)
            elif reward_type == "theme":
                profile.theme = reward_value
            elif reward_type == "currency":
                # 假设是金币
                profile.currency["coins"] = profile.currency.get("coins", 0) + reward_value

    def _update_leaderboards(self, user_id: str, profile: UserProfile) -> None:
        """更新排行榜"""
        # 更新总积分排行榜
        self._update_leaderboard("total_points", user_id, profile.total_points, {
            "level": profile.level,
            "experiments_completed": profile.statistics["experiments_completed"]
        })

        # 更新准确率排行榜
        accuracy = profile.statistics["average_accuracy"]
        self._update_leaderboard("accuracy", user_id, accuracy, {
            "best_accuracy": profile.statistics["best_accuracy"],
            "experiments_completed": profile.statistics["experiments_completed"]
        })

        # 更新安全性排行榜
        safety_score = profile.statistics.get("safety_score", 0.0)
        self._update_leaderboard("safety", user_id, safety_score, {
            "streak_days": profile.statistics["streak_days"]
        })

    def _update_leaderboard(
        self,
        leaderboard_name: str,
        user_id: str,
        score: float,
        additional_data: Dict[str, Any]
    ) -> None:
        """更新单个排行榜"""
        if leaderboard_name not in self.leaderboards:
            self.leaderboards[leaderboard_name] = []

        leaderboard = self.leaderboards[leaderboard_name]
        profile = self.user_profiles[user_id]

        # 查找现有条目
        existing_entry = None
        for entry in leaderboard:
            if entry.user_id == user_id:
                existing_entry = entry
                break

        if existing_entry:
            # 更新现有条目
            existing_entry.score = score
            existing_entry.additional_data.update(additional_data)
        else:
            # 创建新条目
            entry = LeaderboardEntry(
                user_id=user_id,
                username=profile.username,
                score=score,
                rank=0,  # 稍后计算
                additional_data=additional_data
            )
            leaderboard.append(entry)

        # 重新排序
        leaderboard.sort(key=lambda x: x.score, reverse=True)

        # 更新排名
        for i, entry in enumerate(leaderboard):
            entry.rank = i + 1

    @enhance_robustness(
        operation_name="get_user_profile",
        security_level="low",
        enable_caching=True
    )
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户档案"""
        return self.user_profiles.get(user_id)

    @enhance_robustness(
        operation_name="get_user_achievements",
        security_level="low",
        enable_caching=True
    )
    def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """获取用户成就"""
        return self.user_achievements.get(user_id, [])

    @enhance_robustness(
        operation_name="get_leaderboard",
        security_level="low",
        enable_caching=True
    )
    def get_leaderboard(self, leaderboard_name: str, limit: int = 10) -> List[LeaderboardEntry]:
        """获取排行榜"""
        if leaderboard_name not in self.leaderboards:
            return []

        return self.leaderboards[leaderboard_name][:limit]

    @enhance_robustness(
        operation_name="get_available_achievements",
        security_level="low",
        enable_caching=True
    )
    def get_available_achievements(self, user_id: str) -> List[Achievement]:
        """获取可用成就"""
        if user_id not in self.user_achievements:
            return list(self.achievements.values())

        user_achievement_ids = {ua.achievement_id for ua in self.user_achievements[user_id] if ua.is_unlocked}
        available_achievements = []

        for achievement in self.achievements.values():
            if achievement.id not in user_achievement_ids:
                available_achievements.append(achievement)

        return available_achievements

    @enhance_robustness(
        operation_name="get_user_statistics",
        security_level="low",
        enable_caching=True
    )
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        if user_id not in self.user_profiles:
            return {}

        profile = self.user_profiles[user_id]
        achievements = self.user_achievements.get(user_id, [])

        return {
            "profile": {
                "user_id": profile.user_id,
                "username": profile.username,
                "level": profile.level,
                "experience_points": profile.experience_points,
                "total_points": profile.total_points,
                "badges": profile.badges,
                "titles": profile.titles,
                "avatar": profile.avatar,
                "theme": profile.theme,
                "currency": profile.currency,
                "created_at": profile.created_at.isoformat(),
                "last_active": profile.last_active.isoformat()
            },
            "statistics": profile.statistics,
            "achievements": {
                "total_unlocked": len([a for a in achievements if a.is_unlocked]),
                "total_available": len(self.achievements),
                "recent_unlocked": [
                    {
                        "id": a.achievement_id,
                        "unlocked_at": a.unlocked_at.isoformat()
                    }
                    for a in achievements if a.is_unlocked
                ][-5:]  # 最近5个
            }
        }

    def _log_gamification_event(self, user_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """记录游戏化事件"""
        logger.info(f"游戏化事件: {user_id} - {event_type}: {data}")


# 全局实例
enhanced_gamification_system = EnhancedGamificationSystem()
