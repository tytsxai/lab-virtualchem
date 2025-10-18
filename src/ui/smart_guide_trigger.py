"""
智能引导触发器
根据用户行为和上下文自动触发合适的引导

功能:
1. 行为检测 - 检测用户操作模式
2. 上下文分析 - 分析当前应用状态
3. 智能触发 - 在合适时机显示引导
4. 学习适应 - 根据用户熟练度调整
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TriggerCondition(Enum):
    """触发条件类型"""

    FIRST_TIME = "first_time"  # 首次操作
    IDLE_TIME = "idle_time"  # 空闲时间
    ERROR_COUNT = "error_count"  # 错误次数
    RETRY_COUNT = "retry_count"  # 重试次数
    TIME_SPENT = "time_spent"  # 花费时间
    STUCK_DETECTION = "stuck_detection"  # 卡住检测
    ACHIEVEMENT = "achievement"  # 成就解锁
    FEATURE_UNUSED = "feature_unused"  # 未使用功能


@dataclass
class GuideTrigger:
    """引导触发器配置"""

    id: str
    guide_id: str  # 要触发的引导ID
    condition: TriggerCondition
    threshold: Any  # 触发阈值
    context: str | None = None  # 上下文条件
    priority: int = 0  # 优先级
    cooldown: int = 0  # 冷却时间（秒）
    max_triggers: int = -1  # 最大触发次数（-1表示无限制）
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserBehavior:
    """用户行为记录"""

    action: str
    timestamp: datetime
    context: str | None = None
    success: bool = True
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SmartGuideTrigger(QObject):
    """智能引导触发器"""

    guide_triggered = Signal(str)  # 引导ID
    context_changed = Signal(str)  # 上下文变更

    def __init__(self):
        super().__init__()

        # 触发器配置
        self.triggers: dict[str, GuideTrigger] = {}

        # 用户行为历史
        self.behavior_history: list[UserBehavior] = []

        # 触发历史
        self.trigger_history: dict[str, list[datetime]] = {}

        # 当前上下文
        self.current_context = ""

        # 状态追踪
        self.idle_timer: QTimer | None = None
        self.last_action_time = datetime.now()
        self.error_count = 0
        self.retry_count = 0

        # 用户熟练度
        self.user_skill_level = "beginner"  # beginner, intermediate, advanced

        # 加载配置
        self.load_triggers()
        self.load_behavior_history()

        # 启动空闲检测
        self.start_idle_detection()

        logger.info("智能引导触发器初始化完成")

    def add_trigger(self, trigger: GuideTrigger):
        """添加触发器"""
        self.triggers[trigger.id] = trigger
        logger.debug(f"添加触发器: {trigger.id}")

    def record_behavior(self, behavior: UserBehavior):
        """记录用户行为"""
        self.behavior_history.append(behavior)
        self.last_action_time = datetime.now()

        # 重置空闲计时器
        if self.idle_timer:
            self.idle_timer.stop()
            self.idle_timer.start(5000)  # 5秒无操作视为空闲

        # 检查触发条件
        self.check_triggers(behavior)

        logger.debug(f"记录用户行为: {behavior.action}")

    def record_action(self, action: str, context: str | None = None, success: bool = True):
        """记录用户操作"""
        behavior = UserBehavior(action=action, timestamp=datetime.now(), context=context, success=success)

        self.record_behavior(behavior)

        # 更新统计
        if not success:
            self.error_count += 1

    def set_context(self, context: str):
        """设置当前上下文"""
        if self.current_context != context:
            self.current_context = context
            self.context_changed.emit(context)
            logger.info(f"上下文变更: {context}")

            # 检查上下文相关的触发器
            self.check_context_triggers(context)

    def check_triggers(self, behavior: UserBehavior):
        """检查所有触发器"""
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            # 检查冷却时间
            if not self._is_trigger_available(trigger):
                continue

            # 检查上下文
            if trigger.context and trigger.context != self.current_context:
                continue

            # 检查条件
            if self._check_trigger_condition(trigger, behavior):
                self._fire_trigger(trigger)

    def check_context_triggers(self, context: str):
        """检查上下文触发器"""
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            if trigger.context == context:
                if trigger.condition == TriggerCondition.FIRST_TIME:
                    # 检查是否首次进入此上下文
                    if not self._has_triggered(trigger.id):
                        self._fire_trigger(trigger)

    def _check_trigger_condition(self, trigger: GuideTrigger, behavior: UserBehavior) -> bool:
        """检查触发条件"""

        if trigger.condition == TriggerCondition.FIRST_TIME:
            # 首次操作
            return behavior.action == trigger.metadata.get("action") and not self._has_triggered(trigger.id)

        elif trigger.condition == TriggerCondition.ERROR_COUNT:
            # 错误次数达到阈值
            return self.error_count >= trigger.threshold

        elif trigger.condition == TriggerCondition.RETRY_COUNT:
            # 重试次数达到阈值
            return self.retry_count >= trigger.threshold

        elif trigger.condition == TriggerCondition.STUCK_DETECTION:
            # 检测用户卡住
            return self._detect_stuck(trigger)

        elif trigger.condition == TriggerCondition.ACHIEVEMENT:
            # 成就解锁
            return behavior.action == "achievement_unlocked" and behavior.metadata.get(
                "achievement_id"
            ) == trigger.metadata.get("achievement_id")

        elif trigger.condition == TriggerCondition.FEATURE_UNUSED:
            # 功能未使用
            feature_name = trigger.metadata.get("feature")
            return not self._has_used_feature(feature_name)

        return False

    def _detect_stuck(self, trigger: GuideTrigger) -> bool:
        """检测用户是否卡住"""
        # 检查最近N次操作
        recent_count = 10
        if len(self.behavior_history) < recent_count:
            return False

        recent_behaviors = self.behavior_history[-recent_count:]

        # 检查失败率
        failure_count = sum(1 for b in recent_behaviors if not b.success)
        failure_rate = failure_count / len(recent_behaviors)

        # 检查重复操作
        actions = [b.action for b in recent_behaviors]
        unique_actions = len(set(actions))

        # 如果失败率高且操作单一，可能卡住了
        return failure_rate > 0.5 and unique_actions <= 3

    def _has_used_feature(self, feature_name: str) -> bool:
        """检查是否使用过某功能"""
        return any(b.action == feature_name for b in self.behavior_history)

    def _is_trigger_available(self, trigger: GuideTrigger) -> bool:
        """检查触发器是否可用（冷却时间检查）"""
        if trigger.id not in self.trigger_history:
            return True

        trigger_times = self.trigger_history[trigger.id]

        # 检查最大触发次数
        if trigger.max_triggers > 0 and len(trigger_times) >= trigger.max_triggers:
            return False

        # 检查冷却时间
        if trigger.cooldown > 0 and trigger_times:
            last_trigger = trigger_times[-1]
            cooldown_end = last_trigger + timedelta(seconds=trigger.cooldown)
            if datetime.now() < cooldown_end:
                return False

        return True

    def _has_triggered(self, trigger_id: str) -> bool:
        """检查触发器是否已触发过"""
        return trigger_id in self.trigger_history and len(self.trigger_history[trigger_id]) > 0

    def _fire_trigger(self, trigger: GuideTrigger):
        """触发引导"""
        # 记录触发
        if trigger.id not in self.trigger_history:
            self.trigger_history[trigger.id] = []

        self.trigger_history[trigger.id].append(datetime.now())

        # 发送信号
        self.guide_triggered.emit(trigger.guide_id)

        logger.info(f"触发引导: {trigger.guide_id} (触发器: {trigger.id})")

    def start_idle_detection(self):
        """启动空闲检测"""
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.on_idle)
        self.idle_timer.start(5000)  # 5秒检测一次

    def on_idle(self):
        """空闲处理"""
        idle_duration = (datetime.now() - self.last_action_time).total_seconds()

        # 检查空闲触发器
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            if trigger.condition == TriggerCondition.IDLE_TIME:
                if idle_duration >= trigger.threshold and self._is_trigger_available(trigger):
                    self._fire_trigger(trigger)

    def load_triggers(self):
        """加载触发器配置"""
        # 默认触发器
        default_triggers = [
            # 首次进入实验选择
            GuideTrigger(
                id="first_experiment_selection",
                guide_id="experiment_guide",
                condition=TriggerCondition.FIRST_TIME,
                threshold=0,
                context="experiment_selection",
                metadata={"action": "enter_experiment_selection"},
            ),
            # 错误3次后提供帮助
            GuideTrigger(
                id="error_help",
                guide_id="error_recovery_guide",
                condition=TriggerCondition.ERROR_COUNT,
                threshold=3,
                cooldown=300,  # 5分钟冷却
            ),
            # 卡住检测
            GuideTrigger(
                id="stuck_help",
                guide_id="step_help_guide",
                condition=TriggerCondition.STUCK_DETECTION,
                threshold=0,
                cooldown=600,  # 10分钟冷却
            ),
            # 空闲30秒提示
            GuideTrigger(
                id="idle_hint",
                guide_id="idle_tips",
                condition=TriggerCondition.IDLE_TIME,
                threshold=30,
                priority=1,
            ),
        ]

        for trigger in default_triggers:
            self.add_trigger(trigger)

        # 从文件加载
        config_file = Path("user_data/guide_triggers.json")
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = json.load(f)

                for trigger_data in data.get("triggers", []):
                    trigger = GuideTrigger(
                        id=trigger_data["id"],
                        guide_id=trigger_data["guide_id"],
                        condition=TriggerCondition(trigger_data["condition"]),
                        threshold=trigger_data["threshold"],
                        context=trigger_data.get("context"),
                        priority=trigger_data.get("priority", 0),
                        cooldown=trigger_data.get("cooldown", 0),
                        max_triggers=trigger_data.get("max_triggers", -1),
                        enabled=trigger_data.get("enabled", True),
                        metadata=trigger_data.get("metadata", {}),
                    )
                    self.add_trigger(trigger)

                logger.info(f"加载了 {len(data.get('triggers', []))} 个自定义触发器")

            except Exception as e:
                logger.warning(f"加载触发器配置失败: {e}")

    def load_behavior_history(self):
        """加载行为历史"""
        history_file = Path("user_data/behavior_history.json")
        if history_file.exists():
            try:
                with open(history_file, encoding="utf-8") as f:
                    data = json.load(f)

                for behavior_data in data.get("behaviors", []):
                    behavior = UserBehavior(
                        action=behavior_data["action"],
                        timestamp=datetime.fromisoformat(behavior_data["timestamp"]),
                        context=behavior_data.get("context"),
                        success=behavior_data.get("success", True),
                        duration=behavior_data.get("duration", 0.0),
                        metadata=behavior_data.get("metadata", {}),
                    )
                    self.behavior_history.append(behavior)

                logger.info(f"加载了 {len(data.get('behaviors', []))} 条行为历史")

            except Exception as e:
                logger.warning(f"加载行为历史失败: {e}")

    def save_behavior_history(self):
        """保存行为历史"""
        history_file = Path("user_data/behavior_history.json")
        history_file.parent.mkdir(exist_ok=True)

        try:
            # 只保存最近1000条
            recent_behaviors = self.behavior_history[-1000:]

            data = {
                "behaviors": [
                    {
                        "action": b.action,
                        "timestamp": b.timestamp.isoformat(),
                        "context": b.context,
                        "success": b.success,
                        "duration": b.duration,
                        "metadata": b.metadata,
                    }
                    for b in recent_behaviors
                ]
            }

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("行为历史已保存")

        except Exception as e:
            logger.error(f"保存行为历史失败: {e}")


# 全局实例
_smart_trigger: SmartGuideTrigger | None = None


def get_smart_trigger() -> SmartGuideTrigger:
    """获取全局智能触发器"""
    global _smart_trigger
    if _smart_trigger is None:
        _smart_trigger = SmartGuideTrigger()
    return _smart_trigger
