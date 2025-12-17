"""
经验值系统和等级提升模块

提供用户经验值管理、等级计算和奖励系统
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


@dataclass
class LevelReward:
    """等级奖励"""

    level: int
    title: str
    description: str
    unlocks: list[str]  # 解锁的功能或权限
    bonus_exp: int = 0  # 额外经验奖励


@dataclass
class UserProgress:
    """用户进度"""

    user_id: str
    current_level: int = 1
    current_exp: int = 0
    total_exp: int = 0
    achievements: list[str] | None = None
    last_level_up: str | None = None

    def __post_init__(self) -> None:
        if self.achievements is None:
            self.achievements = []


class ExperienceSystem(QObject):
    """经验值系统"""

    # 信号
    level_up = Signal(int, str)  # level, title
    exp_gained = Signal(int, int)  # gained_exp, total_exp
    achievement_unlocked = Signal(str)

    def __init__(self, data_dir: Path | None = None):
        super().__init__()
        self.data_dir = data_dir or Path("data/users")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 等级配置
        self.level_config = self._load_level_config()
        self.rewards = self._load_rewards()

        # 用户进度缓存
        self._user_progress: dict[str, UserProgress] = {}

        logger.info("经验值系统初始化完成")

    def _load_level_config(self) -> dict[int, int]:
        """加载等级配置"""
        # 等级经验需求表 (等级: 所需经验)
        config = {
            1: 0,  # 新手
            2: 100,  # 初学者
            3: 250,  # 学习者
            4: 450,  # 熟练者
            5: 700,  # 专家
            6: 1000,  # 大师
            7: 1350,  # 宗师
            8: 1750,  # 传奇
            9: 2200,  # 神话
            10: 2700,  # 传说
        }

        # 10级以后每级增加500经验
        for level in range(11, 51):
            config[level] = config[level - 1] + 500

        return config

    def _load_rewards(self) -> dict[int, LevelReward]:
        """加载等级奖励"""
        rewards = {
            1: LevelReward(1, "新手", "欢迎来到虚拟化学实验室！", []),
            2: LevelReward(2, "初学者", "开始你的化学学习之旅", ["基础实验"]),
            3: LevelReward(3, "学习者", "掌握基础操作", ["中级实验", "数据导出"]),
            4: LevelReward(4, "熟练者", "熟练运用实验技能", ["高级实验", "自定义模板"]),
            5: LevelReward(5, "专家", "成为实验专家", ["专家实验", "批量操作"]),
            6: LevelReward(6, "大师", "实验技能炉火纯青", ["大师实验", "实验对比"]),
            7: LevelReward(7, "宗师", "化学实验的宗师", ["宗师实验", "趋势分析"]),
            8: LevelReward(8, "传奇", "创造实验传奇", ["传奇实验", "高级分析"]),
            9: LevelReward(9, "神话", "实验神话的缔造者", ["神话实验", "AI助手"]),
            10: LevelReward(10, "传说", "传说中的实验大师", ["传说实验", "所有功能"]),
        }

        # 10级以后每5级一个特殊奖励
        for level in range(15, 51, 5):
            rewards[level] = LevelReward(
                level,
                f"等级{level}大师",
                f"达到等级{level}的成就",
                [f"等级{level}专属功能"],
                bonus_exp=level * 10,
            )

        return rewards

    def get_user_progress(self, user_id: str) -> UserProgress:
        """获取用户进度"""
        if user_id not in self._user_progress:
            self._user_progress[user_id] = self._load_user_progress(user_id)
        return self._user_progress[user_id]

    def _load_user_progress(self, user_id: str) -> UserProgress:
        """从文件加载用户进度"""
        file_path = self.data_dir / f"{user_id}_progress.json"

        if file_path.exists():
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    progress = UserProgress(**data)
                    logger.info(
                        f"加载用户 {user_id} 进度: 等级{progress.current_level}, 经验{progress.current_exp}"
                    )
                    return progress
            except Exception as e:
                logger.error(f"加载用户进度失败: {e}")

        # 创建新用户进度
        progress = UserProgress(user_id=user_id)
        self._save_user_progress(progress)
        return progress

    def _save_user_progress(self, progress: UserProgress) -> None:
        """保存用户进度"""
        try:
            file_path = self.data_dir / f"{progress.user_id}_progress.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(asdict(progress), f, ensure_ascii=False, indent=2)
            logger.debug(f"保存用户 {progress.user_id} 进度")
        except Exception as e:
            logger.error(f"保存用户进度失败: {e}")

    def add_experience(
        self, user_id: str, exp_points: int, source: str = "实验"
    ) -> tuple[bool, str | None]:
        """添加经验值

        Args:
            user_id: 用户ID
            exp_points: 经验值
            source: 经验来源

        Returns:
            (是否升级, 升级信息)
        """
        try:
            progress = self.get_user_progress(user_id)
            old_level = progress.current_level

            # 添加经验值
            progress.current_exp += exp_points
            progress.total_exp += exp_points

            # 检查是否升级
            new_level = self._calculate_level(progress.current_exp)
            leveled_up = new_level > old_level

            if leveled_up:
                progress.current_level = new_level
                reward = self.rewards.get(new_level)
                level_info = (
                    f"升级到等级{new_level} - {reward.title if reward else '未知'}"
                )

                # 发送信号
                self.level_up.emit(
                    new_level, reward.title if reward else f"等级{new_level}"
                )
                logger.info(f"用户 {user_id} 升级到等级{new_level}")
            else:
                level_info = None

            # 发送经验获得信号
            self.exp_gained.emit(exp_points, progress.current_exp)

            # 保存进度
            self._save_user_progress(progress)

            logger.info(f"用户 {user_id} 获得 {exp_points} 经验值 (来源: {source})")
            return leveled_up, level_info

        except Exception as e:
            logger.error(f"添加经验值失败: {e}")
            return False, None

    def _calculate_level(self, total_exp: int) -> int:
        """根据总经验值计算等级"""
        level = 1
        for lvl, required_exp in self.level_config.items():
            if total_exp >= required_exp:
                level = lvl
            else:
                break
        return level

    def get_level_info(self, level: int) -> LevelReward | None:
        """获取等级信息"""
        return self.rewards.get(level)

    def get_next_level_exp(self, current_exp: int) -> tuple[int, int]:
        """获取下一等级所需经验

        Returns:
            (下一等级, 所需经验)
        """
        current_level = self._calculate_level(current_exp)
        next_level = current_level + 1

        if next_level in self.level_config:
            required_exp = self.level_config[next_level]
            needed_exp = required_exp - current_exp
            return next_level, needed_exp
        else:
            return current_level, 0

    def get_level_progress(self, current_exp: int) -> tuple[int, int, int]:
        """获取等级进度

        Returns:
            (当前等级, 当前等级经验, 下一等级所需经验)
        """
        current_level = self._calculate_level(current_exp)

        if current_level in self.level_config:
            current_level_exp = current_exp - self.level_config[current_level]
        else:
            current_level_exp = 0

        next_level, needed_exp = self.get_next_level_exp(current_exp)

        return current_level, current_level_exp, needed_exp

    def unlock_achievement(self, user_id: str, achievement_id: str) -> bool:
        """解锁成就"""
        try:
            progress = self.get_user_progress(user_id)

            if (
                progress.achievements is not None
                and achievement_id not in progress.achievements
            ):
                progress.achievements.append(achievement_id)
                self._save_user_progress(progress)

                # 发送信号
                self.achievement_unlocked.emit(achievement_id)
                logger.info(f"用户 {user_id} 解锁成就: {achievement_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"解锁成就失败: {e}")
            return False

    def get_achievements(self, user_id: str) -> list[str]:
        """获取用户成就列表"""
        progress = self.get_user_progress(user_id)
        return progress.achievements.copy() if progress.achievements is not None else []

    def get_leaderboard(self, limit: int = 10) -> list[tuple[str, int, int]]:
        """获取排行榜

        Returns:
            List of (user_id, level, total_exp)
        """
        try:
            leaderboard = []

            # 扫描所有用户进度文件
            for file_path in self.data_dir.glob("*_progress.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                        user_id = data.get("user_id", "")
                        total_exp = data.get("total_exp", 0)
                        level = self._calculate_level(total_exp)

                        leaderboard.append((user_id, level, total_exp))
                except Exception as e:
                    logger.error(f"读取用户进度文件失败: {e}")
                    continue

            # 按总经验值排序
            leaderboard.sort(key=lambda x: x[2], reverse=True)
            return leaderboard[:limit]

        except Exception as e:
            logger.error(f"获取排行榜失败: {e}")
            return []

    def reset_user_progress(self, user_id: str) -> bool:
        """重置用户进度"""
        try:
            progress = UserProgress(user_id=user_id)
            self._user_progress[user_id] = progress
            self._save_user_progress(progress)

            logger.info(f"重置用户 {user_id} 进度")
            return True

        except Exception as e:
            logger.error(f"重置用户进度失败: {e}")
            return False


# 全局经验值系统实例
_experience_system: ExperienceSystem | None = None


def get_experience_system() -> ExperienceSystem:
    """获取全局经验值系统实例"""
    global _experience_system
    if _experience_system is None:
        _experience_system = ExperienceSystem()
    return _experience_system


def init_experience_system(data_dir: Path | None = None) -> ExperienceSystem:
    """初始化经验值系统"""
    global _experience_system
    _experience_system = ExperienceSystem(data_dir)
    return _experience_system
