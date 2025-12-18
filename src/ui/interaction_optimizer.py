"""
交互优化器
优化用户交互流程，提供智能默认值和上下文感知
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class InteractionType(str, Enum):
    """交互类型"""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    DRAG = "drag"
    KEYBOARD = "keyboard"
    MENU = "menu"
    DIALOG = "dialog"
    FORM = "form"
    NAVIGATION = "navigation"


class UserSkillLevel(str, Enum):
    """用户技能水平"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class UserBehavior:
    """用户行为记录"""

    timestamp: datetime
    interaction_type: InteractionType
    component: str
    action: str
    duration_ms: float
    success: bool
    context: dict[str, Any]
    user_id: str


@dataclass
class UserPreference:
    """用户偏好"""

    user_id: str
    component: str
    setting: str
    value: Any
    frequency: int
    last_used: datetime
    confidence: float


@dataclass
class InteractionPattern:
    """交互模式"""

    pattern_id: str
    sequence: list[InteractionType]
    frequency: int
    success_rate: float
    avg_duration_ms: float
    common_contexts: list[str]
    user_skill_level: UserSkillLevel


class InteractionOptimizer(QObject):
    """交互优化器"""

    # 信号
    pattern_detected = Signal(str, dict)  # 模式ID, 模式数据
    optimization_suggested = Signal(str, str)  # 组件, 建议
    user_skill_updated = Signal(str, UserSkillLevel)  # 用户ID, 技能水平

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 用户行为数据
        self.user_behaviors: dict[str, deque[Any]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.user_preferences: dict[str, dict[str, UserPreference]] = defaultdict(dict)
        self.interaction_patterns: dict[str, InteractionPattern] = {}

        # 用户画像
        self.user_skill_levels: dict[str, UserSkillLevel] = {}
        self.user_contexts: dict[str, dict[str, Any]] = defaultdict(dict)

        # 优化设置
        self.learning_enabled = True
        self.pattern_detection_enabled = True
        self.auto_optimization_enabled = True

        # 分析参数
        self.pattern_window_minutes = 30
        self.min_pattern_frequency = 3
        self.skill_assessment_threshold = 10

        # 定时器
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.analyze_patterns)
        self.analysis_timer.start(60000)  # 每分钟分析一次

        # 数据持久化
        self.data_file = Path("data/interaction_optimizer.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        self.load_data()

        logger.info("交互优化器初始化完成")

    def record_interaction(
        self,
        user_id: str,
        interaction_type: InteractionType,
        component: str,
        action: str,
        duration_ms: float,
        success: bool,
        context: dict[str, Any] | None = None,
    ) -> None:
        """记录用户交互"""
        try:
            behavior = UserBehavior(
                timestamp=datetime.now(),
                interaction_type=interaction_type,
                component=component,
                action=action,
                duration_ms=duration_ms,
                success=success,
                context=context or {},
                user_id=user_id,
            )

            self.user_behaviors[user_id].append(behavior)

            # 实时分析
            if self.learning_enabled:
                self._analyze_user_skill(user_id)
                self._update_user_preferences(user_id, behavior)

            logger.debug(
                f"记录用户交互: {user_id} - {interaction_type.value} - {component}"
            )

        except Exception as e:
            logger.error(f"记录用户交互失败: {e}")

    def _analyze_user_skill(self, user_id: str) -> None:
        """分析用户技能水平"""
        try:
            behaviors = self.user_behaviors[user_id]
            if len(behaviors) < self.skill_assessment_threshold:
                return

            # 分析交互效率
            recent_behaviors = list(behaviors)[-50:]  # 最近50次交互

            # 计算平均交互时间
            avg_duration = sum(b.duration_ms for b in recent_behaviors) / len(
                recent_behaviors
            )

            # 计算成功率
            success_rate = sum(1 for b in recent_behaviors if b.success) / len(
                recent_behaviors
            )

            # 分析交互复杂度
            complex_interactions = sum(
                1
                for b in recent_behaviors
                if b.interaction_type
                in [InteractionType.DRAG, InteractionType.KEYBOARD]
            )
            complexity_ratio = complex_interactions / len(recent_behaviors)

            # 分析错误恢复能力
            error_recoveries = 0
            for i in range(1, len(recent_behaviors)):
                if not recent_behaviors[i - 1].success and recent_behaviors[i].success:
                    error_recoveries += 1

            recovery_rate = error_recoveries / max(
                1, sum(1 for b in recent_behaviors if not b.success)
            )

            # 技能水平评估
            old_skill = self.user_skill_levels.get(user_id, UserSkillLevel.BEGINNER)
            new_skill = self._calculate_skill_level(
                avg_duration, success_rate, complexity_ratio, recovery_rate
            )

            if new_skill != old_skill:
                self.user_skill_levels[user_id] = new_skill
                self.user_skill_updated.emit(user_id, new_skill)
                logger.info(f"用户技能水平更新: {user_id} - {new_skill.value}")

        except Exception as e:
            logger.error(f"分析用户技能失败: {e}")

    def _calculate_skill_level(
        self,
        avg_duration: float,
        success_rate: float,
        complexity_ratio: float,
        recovery_rate: float,
    ) -> UserSkillLevel:
        """计算技能水平"""
        # 技能评分算法
        score = 0

        # 交互效率 (权重: 30%)
        if avg_duration < 500:  # 快速交互
            score += 30
        elif avg_duration < 1000:
            score += 20
        elif avg_duration < 2000:
            score += 10

        # 成功率 (权重: 40%)
        if success_rate > 0.9:
            score += 40
        elif success_rate > 0.8:
            score += 30
        elif success_rate > 0.7:
            score += 20
        elif success_rate > 0.6:
            score += 10

        # 复杂度 (权重: 20%)
        if complexity_ratio > 0.3:
            score += 20
        elif complexity_ratio > 0.2:
            score += 15
        elif complexity_ratio > 0.1:
            score += 10

        # 恢复能力 (权重: 10%)
        if recovery_rate > 0.8:
            score += 10
        elif recovery_rate > 0.6:
            score += 8
        elif recovery_rate > 0.4:
            score += 5

        # 转换为技能水平
        if score >= 90:
            return UserSkillLevel.EXPERT
        elif score >= 70:
            return UserSkillLevel.ADVANCED
        elif score >= 50:
            return UserSkillLevel.INTERMEDIATE
        else:
            return UserSkillLevel.BEGINNER

    def _update_user_preferences(self, user_id: str, behavior: UserBehavior) -> None:
        """更新用户偏好"""
        try:
            # 更新组件偏好
            component_key = f"{behavior.component}.{behavior.action}"
            if component_key in self.user_preferences[user_id]:
                preference = self.user_preferences[user_id][component_key]
                preference.frequency += 1
                preference.last_used = behavior.timestamp
                preference.confidence = min(1.0, preference.confidence + 0.1)
            else:
                preference = UserPreference(
                    user_id=user_id,
                    component=behavior.component,
                    setting=behavior.action,
                    value=behavior.context.get("value", ""),
                    frequency=1,
                    last_used=behavior.timestamp,
                    confidence=0.1,
                )
                self.user_preferences[user_id][component_key] = preference

            # 更新上下文偏好
            for key, value in behavior.context.items():
                context_key = f"context.{key}"
                if context_key in self.user_preferences[user_id]:
                    self.user_preferences[user_id][context_key].frequency += 1
                else:
                    self.user_preferences[user_id][context_key] = UserPreference(
                        user_id=user_id,
                        component="context",
                        setting=key,
                        value=value,
                        frequency=1,
                        last_used=behavior.timestamp,
                        confidence=0.1,
                    )

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")

    def analyze_patterns(self) -> None:
        """分析交互模式"""
        if not self.pattern_detection_enabled:
            return

        try:
            logger.debug("开始分析交互模式")

            # 分析每个用户的交互模式
            for user_id, behaviors in self.user_behaviors.items():
                if len(behaviors) < self.min_pattern_frequency:
                    continue

                # 检测交互序列模式
                patterns = self._detect_sequence_patterns(user_id, behaviors)

                # 检测时间模式
                time_patterns = self._detect_time_patterns(user_id, behaviors)

                # 检测上下文模式
                context_patterns = self._detect_context_patterns(user_id, behaviors)

                # 合并模式
                all_patterns = patterns + time_patterns + context_patterns

                for pattern in all_patterns:
                    self._register_pattern(pattern)

            logger.debug(
                f"模式分析完成，检测到 {len(self.interaction_patterns)} 个模式"
            )

        except Exception as e:
            logger.error(f"分析交互模式失败: {e}")

    def _detect_sequence_patterns(
        self, user_id: str, behaviors: deque[Any]
    ) -> list[InteractionPattern]:
        """检测序列模式"""
        patterns = []

        try:
            # 滑动窗口检测
            window_size = 3
            sequences = defaultdict(list)

            for i in range(len(behaviors) - window_size + 1):
                sequence = tuple(
                    b.interaction_type for b in list(behaviors)[i : i + window_size]
                )
                sequences[sequence].append(i)

            # 识别频繁序列
            for sequence, positions in sequences.items():
                if len(positions) >= self.min_pattern_frequency:
                    # 计算模式统计
                    pattern_behaviors = [
                        list(behaviors)[i : i + window_size] for i in positions
                    ]
                    success_rate = sum(
                        1 for seq in pattern_behaviors if all(b.success for b in seq)
                    ) / len(pattern_behaviors)

                    avg_duration = sum(
                        sum(b.duration_ms for b in seq) for seq in pattern_behaviors
                    ) / len(pattern_behaviors)

                    # 提取上下文
                    contexts = []
                    for seq in pattern_behaviors:
                        for b in seq:
                            contexts.extend(b.context.keys())

                    common_contexts = list(set(contexts))

                    pattern = InteractionPattern(
                        pattern_id=f"sequence_{user_id}_{hash(sequence)}",
                        sequence=list(sequence),
                        frequency=len(positions),
                        success_rate=success_rate,
                        avg_duration_ms=avg_duration,
                        common_contexts=common_contexts,
                        user_skill_level=self.user_skill_levels.get(
                            user_id, UserSkillLevel.BEGINNER
                        ),
                    )

                    patterns.append(pattern)

        except Exception as e:
            logger.error(f"检测序列模式失败: {e}")

        return patterns

    def _detect_time_patterns(
        self, user_id: str, behaviors: deque[Any]
    ) -> list[InteractionPattern]:
        """检测时间模式"""
        patterns = []

        try:
            # 按小时分组
            hourly_groups = defaultdict(list)
            for behavior in behaviors:
                hour = behavior.timestamp.hour
                hourly_groups[hour].append(behavior)

            # 识别活跃时间段
            for hour, hour_behaviors in hourly_groups.items():
                if len(hour_behaviors) >= self.min_pattern_frequency:
                    success_rate = sum(1 for b in hour_behaviors if b.success) / len(
                        hour_behaviors
                    )
                    avg_duration = sum(b.duration_ms for b in hour_behaviors) / len(
                        hour_behaviors
                    )

                    pattern = InteractionPattern(
                        pattern_id=f"time_{user_id}_{hour}",
                        sequence=[InteractionType.CLICK],  # 占位符
                        frequency=len(hour_behaviors),
                        success_rate=success_rate,
                        avg_duration_ms=avg_duration,
                        common_contexts=[f"hour_{hour}"],
                        user_skill_level=self.user_skill_levels.get(
                            user_id, UserSkillLevel.BEGINNER
                        ),
                    )

                    patterns.append(pattern)

        except Exception as e:
            logger.error(f"检测时间模式失败: {e}")

        return patterns

    def _detect_context_patterns(
        self, user_id: str, behaviors: deque[Any]
    ) -> list[InteractionPattern]:
        """检测上下文模式"""
        patterns = []

        try:
            # 按组件分组
            component_groups = defaultdict(list)
            for behavior in behaviors:
                component_groups[behavior.component].append(behavior)

            # 识别组件使用模式
            for component, component_behaviors in component_groups.items():
                if len(component_behaviors) >= self.min_pattern_frequency:
                    success_rate = sum(
                        1 for b in component_behaviors if b.success
                    ) / len(component_behaviors)
                    avg_duration = sum(
                        b.duration_ms for b in component_behaviors
                    ) / len(component_behaviors)

                    # 提取常见上下文
                    contexts = []
                    for b in component_behaviors:
                        contexts.extend(b.context.keys())

                    common_contexts = list(set(contexts))

                    pattern = InteractionPattern(
                        pattern_id=f"context_{user_id}_{component}",
                        sequence=[InteractionType.CLICK],  # 占位符
                        frequency=len(component_behaviors),
                        success_rate=success_rate,
                        avg_duration_ms=avg_duration,
                        common_contexts=common_contexts,
                        user_skill_level=self.user_skill_levels.get(
                            user_id, UserSkillLevel.BEGINNER
                        ),
                    )

                    patterns.append(pattern)

        except Exception as e:
            logger.error(f"检测上下文模式失败: {e}")

        return patterns

    def _register_pattern(self, pattern: InteractionPattern) -> None:
        """注册交互模式"""
        try:
            if pattern.pattern_id in self.interaction_patterns:
                # 更新现有模式
                existing = self.interaction_patterns[pattern.pattern_id]
                existing.frequency += pattern.frequency
                existing.success_rate = (
                    existing.success_rate + pattern.success_rate
                ) / 2
                existing.avg_duration_ms = (
                    existing.avg_duration_ms + pattern.avg_duration_ms
                ) / 2
            else:
                # 注册新模式
                self.interaction_patterns[pattern.pattern_id] = pattern
                self.pattern_detected.emit(
                    pattern.pattern_id,
                    {
                        "sequence": [t.value for t in pattern.sequence],
                        "frequency": pattern.frequency,
                        "success_rate": pattern.success_rate,
                        "avg_duration_ms": pattern.avg_duration_ms,
                        "common_contexts": pattern.common_contexts,
                        "user_skill_level": pattern.user_skill_level.value,
                    },
                )

        except Exception as e:
            logger.error(f"注册交互模式失败: {e}")

    def get_user_preferences(
        self, user_id: str, component: str | None = None
    ) -> dict[str, Any]:
        """获取用户偏好"""
        try:
            preferences = self.user_preferences.get(user_id, {})

            if component:
                # 过滤特定组件的偏好
                filtered = {
                    key: pref
                    for key, pref in preferences.items()
                    if pref.component == component
                }
                return filtered

            return preferences

        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return {}

    def get_smart_defaults(self, user_id: str, component: str, setting: str) -> Any:
        """获取智能默认值"""
        try:
            # 查找用户偏好
            preference_key = f"{component}.{setting}"
            preference = self.user_preferences.get(user_id, {}).get(preference_key)

            if preference and preference.confidence > 0.5:
                return preference.value

            # 查找相似用户的偏好
            similar_preferences = []
            for other_user_id, other_preferences in self.user_preferences.items():
                if other_user_id != user_id:
                    other_pref = other_preferences.get(preference_key)
                    if other_pref and other_pref.confidence > 0.7:
                        similar_preferences.append(other_pref)

            if similar_preferences:
                # 返回最频繁的值
                value_counts: dict[str, int] = defaultdict(int)
                for pref in similar_preferences:
                    value_counts[pref.value] += pref.frequency

                most_common_value = max(value_counts.items(), key=lambda x: x[1])[0]
                return most_common_value

            # 返回系统默认值
            return self._get_system_default(component, setting)

        except Exception as e:
            logger.error(f"获取智能默认值失败: {e}")
            return self._get_system_default(component, setting)

    def _get_system_default(self, component: str, setting: str) -> Any:
        """获取系统默认值"""
        defaults = {
            "theme": {"name": "light", "color": "#ffffff"},
            "font": {"size": 12, "family": "Arial"},
            "window": {"width": 1200, "height": 800},
            "experiment": {"auto_save": True, "show_hints": True},
            "game": {"sound_enabled": True, "particle_effects": True},
        }

        return defaults.get(component, {}).get(setting, None)

    def optimize_user_flow(self, user_id: str, _current_component: str) -> list[str]:
        """优化用户流程"""
        try:
            suggestions = []

            # 基于用户技能水平提供建议
            skill_level = self.user_skill_levels.get(user_id, UserSkillLevel.BEGINNER)

            if skill_level == UserSkillLevel.BEGINNER:
                suggestions.extend(["显示操作提示", "启用引导模式", "简化界面选项"])
            elif skill_level == UserSkillLevel.INTERMEDIATE:
                suggestions.extend(["显示快捷键提示", "提供高级选项", "启用自动完成"])
            elif skill_level == UserSkillLevel.ADVANCED:
                suggestions.extend(["启用批量操作", "提供自定义选项", "显示性能统计"])
            else:  # EXPERT
                suggestions.extend(["启用专家模式", "提供API接口", "显示调试信息"])

            # 基于交互模式提供建议
            user_patterns = [
                pattern
                for pattern in self.interaction_patterns.values()
                if pattern.pattern_id.startswith(f"sequence_{user_id}_")
                or pattern.pattern_id.startswith(f"context_{user_id}_")
            ]

            for pattern in user_patterns:
                if pattern.success_rate < 0.7:
                    suggestions.append(f"优化 {pattern.common_contexts[0]} 操作流程")

                if pattern.avg_duration_ms > 2000:
                    suggestions.append(f"简化 {pattern.common_contexts[0]} 操作步骤")

            # 去重并返回
            return list(set(suggestions))

        except Exception as e:
            logger.error(f"优化用户流程失败: {e}")
            return []

    def personalize_interface(self, user_id: str, component: QWidget) -> None:
        """个性化界面"""
        try:
            # 获取用户偏好
            preferences = self.get_user_preferences(user_id, component.objectName())

            # 应用偏好设置
            for _key, preference in preferences.items():
                if preference.confidence > 0.6:
                    self._apply_preference(component, preference)

            # 基于技能水平调整界面
            skill_level = self.user_skill_levels.get(user_id, UserSkillLevel.BEGINNER)
            self._adjust_interface_for_skill(component, skill_level)

        except Exception as e:
            logger.error(f"个性化界面失败: {e}")

    def _apply_preference(
        self, _component: QWidget, preference: UserPreference
    ) -> None:
        """应用偏好设置"""
        try:
            # 这里应该实现具体的偏好应用逻辑
            # 比如设置字体大小、颜色、布局等
            logger.debug(
                f"应用偏好: {preference.component}.{preference.setting} = {preference.value}"
            )

        except Exception as e:
            logger.error(f"应用偏好失败: {e}")

    def _adjust_interface_for_skill(
        self, _component: QWidget, skill_level: UserSkillLevel
    ) -> None:
        """根据技能水平调整界面"""
        try:
            # 这里应该实现基于技能水平的界面调整
            # 比如显示/隐藏高级选项、调整提示级别等
            logger.debug(f"根据技能水平调整界面: {skill_level.value}")

        except Exception as e:
            logger.error(f"调整界面失败: {e}")

    def save_data(self) -> None:
        """保存数据"""
        try:
            data = {
                "user_preferences": {
                    user_id: {
                        key: {
                            "component": pref.component,
                            "setting": pref.setting,
                            "value": pref.value,
                            "frequency": pref.frequency,
                            "last_used": pref.last_used.isoformat(),
                            "confidence": pref.confidence,
                        }
                        for key, pref in prefs.items()
                    }
                    for user_id, prefs in self.user_preferences.items()
                },
                "user_skill_levels": {
                    user_id: skill.value
                    for user_id, skill in self.user_skill_levels.items()
                },
                "interaction_patterns": {
                    pattern_id: {
                        "sequence": [t.value for t in pattern.sequence],
                        "frequency": pattern.frequency,
                        "success_rate": pattern.success_rate,
                        "avg_duration_ms": pattern.avg_duration_ms,
                        "common_contexts": pattern.common_contexts,
                        "user_skill_level": pattern.user_skill_level.value,
                    }
                    for pattern_id, pattern in self.interaction_patterns.items()
                },
            }

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info("交互优化器数据已保存")

        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    def load_data(self) -> None:
        """加载数据"""
        try:
            if not self.data_file.exists():
                return

            with open(self.data_file, encoding="utf-8") as f:
                data = json.load(f)

            # 加载用户偏好
            for user_id, prefs in data.get("user_preferences", {}).items():
                for key, pref_data in prefs.items():
                    preference = UserPreference(
                        user_id=user_id,
                        component=pref_data["component"],
                        setting=pref_data["setting"],
                        value=pref_data["value"],
                        frequency=pref_data["frequency"],
                        last_used=datetime.fromisoformat(pref_data["last_used"]),
                        confidence=pref_data["confidence"],
                    )
                    self.user_preferences[user_id][key] = preference

            # 加载用户技能水平
            for user_id, skill_value in data.get("user_skill_levels", {}).items():
                self.user_skill_levels[user_id] = UserSkillLevel(skill_value)

            # 加载交互模式
            for pattern_id, pattern_data in data.get(
                "interaction_patterns", {}
            ).items():
                pattern = InteractionPattern(
                    pattern_id=pattern_id,
                    sequence=[InteractionType(t) for t in pattern_data["sequence"]],
                    frequency=pattern_data["frequency"],
                    success_rate=pattern_data["success_rate"],
                    avg_duration_ms=pattern_data["avg_duration_ms"],
                    common_contexts=pattern_data["common_contexts"],
                    user_skill_level=UserSkillLevel(pattern_data["user_skill_level"]),
                )
                self.interaction_patterns[pattern_id] = pattern

            logger.info("交互优化器数据已加载")

        except Exception as e:
            logger.error(f"加载数据失败: {e}")

    def get_optimization_report(self) -> str:
        """获取优化报告"""
        try:
            total_users = len(self.user_behaviors)
            total_patterns = len(self.interaction_patterns)
            total_preferences = sum(
                len(prefs) for prefs in self.user_preferences.values()
            )

            report = f"""
# 交互优化报告

## 总体统计
- 活跃用户数: {total_users}
- 检测到的模式: {total_patterns}
- 用户偏好数: {total_preferences}

## 用户技能分布
"""

            skill_counts = defaultdict(int)
            for skill in self.user_skill_levels.values():
                skill_counts[skill] += 1

            for skill, count in skill_counts.items():
                report += f"- {skill.value}: {count} 用户\n"

            report += """
## 交互模式统计
"""

            for pattern_id, pattern in self.interaction_patterns.items():
                report += f"- {pattern_id}: 频率 {pattern.frequency}, 成功率 {pattern.success_rate:.2%}\n"

            report += """
## 优化建议
"""

            if total_patterns == 0:
                report += "- 未检测到交互模式，建议增加用户交互数据\n"

            if total_preferences == 0:
                report += "- 未检测到用户偏好，建议启用偏好学习功能\n"

            low_success_patterns = [
                pattern
                for pattern in self.interaction_patterns.values()
                if pattern.success_rate < 0.7
            ]

            if low_success_patterns:
                report += (
                    f"- 发现 {len(low_success_patterns)} 个低成功率模式，需要优化\n"
                )

            return report

        except Exception as e:
            logger.error(f"生成优化报告失败: {e}")
            return f"报告生成失败: {e}"


# 全局交互优化器实例
interaction_optimizer = InteractionOptimizer()
