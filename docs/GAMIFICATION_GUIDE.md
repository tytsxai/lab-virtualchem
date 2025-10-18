# 🎮 游戏化系统使用指南

## 概述

VirtualChemLab 游戏化系统为虚拟化学实验室添加了丰富的游戏化元素，通过等级、成就、任务等机制，提升用户学习积极性和参与度。

## 核心特性

### 📊 等级系统

- **经验值获取**：完成实验获得经验值
  - 基础经验 = 实验分数
  - 零失误额外 +20% 经验
  - 快速完成（<5分钟）额外 +10% 经验

- **等级与称号**：
  - 等级 1-100，每升级所需经验递增
  - 不同等级解锁不同称号：
    - Lv1: 化学新手
    - Lv5: 实验学徒
    - Lv10: 初级化学师
    - Lv20: 中级化学师
    - Lv30: 高级化学师
    - Lv50: 实验宗师
    - Lv100: 诺贝尔候选人

### 🏆 成就系统

成就分为多种类型：

#### 实验相关

- **初次尝试**：完成第一个实验（50 EXP）
- **实验老手**：完成10个实验（200 EXP）
- **实验大师**：完成50个实验（500 EXP）

#### 分数相关

- **完美实验**：获得100分（100 EXP）
- **高分选手**：累计1000分（300 EXP）

#### 速度相关

- **速通大师**：5分钟内完成实验（150 EXP）

#### 准确度相关

- **零失误**：零错误完成实验（120 EXP）
- **精准之王**：连续5次零错误（400 EXP）

#### 连续完成

- **每日练习**：连续3天完成实验（100 EXP）
- **坚持不懈**：连续7天完成实验（300 EXP）

#### 特殊成就（隐藏）

- **夜猫子**：午夜完成实验（80 EXP）
- **早起鸟**：早上6点前完成实验（80 EXP）

### 📋 任务系统

#### 每日任务（每天刷新）

- **每日一练**：完成1个实验（50 EXP）
- **勤奋学习**：完成3个实验（150 EXP）
- **今日完美**：获得一次满分（100 EXP）

#### 每周任务（每周一刷新）

- **周常任务**：本周完成10个实验（500 EXP）
- **周积分挑战**：本周累计500分（400 EXP）

### 🎁 奖励系统

- **徽章**：解锁特殊徽章装饰个人资料
- **头像框**：不同等级解锁不同边框
  - 青铜框（Lv10）
  - 白银框（Lv20）
  - 黄金框（Lv30）
- **主题**：解锁特殊界面主题

## 用户界面

### 游戏化面板

位于主窗口右侧的游戏化面板包含：

1. **用户等级卡片**
   - 等级徽章（颜色随等级变化）
   - 当前称号
   - 经验进度条

2. **每日任务列表**
   - 任务进度显示
   - 一键领取奖励按钮

3. **最近成就**
   - 最近解锁的6个成就
   - 按稀有度分类（普通/稀有/史诗/传奇）

### 动画效果

- **经验获得动画**：实验完成后飞向等级卡片
- **升级动画**：金色渐变对话框，自动关闭
- **成就解锁动画**：紫色渐变对话框，展示新成就

## 开发者API

### 基础使用

```python
from src.gamification.gamification_manager import GamificationManager

# 初始化管理器
manager = GamificationManager()

# 获取或创建用户数据
user_data = manager.get_or_create_user_data("user_001")

# 实验完成事件
result = manager.on_experiment_completed(
    user_id="user_001",
    score=95.5,
    duration_seconds=180,
    mistake_count=1
)

# 结果包含：
# - exp_gained: 获得的经验值
# - level_up: 是否升级
# - new_achievements: 新解锁的成就列表
# - completed_quests: 完成的任务列表
```

### 自定义成就

```python
from src.gamification.achievement_system import Achievement, AchievementType

custom_achievement = Achievement(
    id="custom_master",
    name="自定义大师",
    description="完成所有自定义实验",
    type=AchievementType.SPECIAL,
    icon="🌟",
    exp_reward=1000,
    rarity="legendary",
    condition_key="custom_experiments_completed",
    condition_value=10,
)

manager.achievement_manager.add_achievement(custom_achievement)
```

### 自定义任务

```python
from src.gamification.quest_system import Quest, QuestType
from datetime import datetime, timedelta

custom_quest = Quest(
    id="weekend_challenge",
    name="周末挑战",
    description="周末完成5个实验",
    type=QuestType.SPECIAL,
    icon="🎯",
    target_key="weekend_experiments",
    target_value=5,
    exp_reward=300,
    expires_at=datetime.now() + timedelta(days=2),
)
```

### UI组件集成

```python
from src.ui.gamification_widgets import (
    LevelBadge,
    UserLevelCard,
    AchievementCard,
    QuestCard,
    GamificationPanel
)

# 创建等级徽章
badge = LevelBadge(level=25)

# 创建用户等级卡片
level_card = UserLevelCard(user_level=user_data.level)
level_card.set_exp_progress(current=450, required=1000)

# 创建成就卡片
achievement_card = AchievementCard(achievement=achievement, unlocked=True)
achievement_card.clicked.connect(on_achievement_clicked)

# 创建任务卡片
quest_card = QuestCard(quest=quest, user_quest=user_quest)
quest_card.claim_clicked.connect(on_claim_reward)
```

## 数据存储

游戏化数据存储在 `data/gamification/{user_id}.json` 中，包含：

```json
{
  "user_id": "student_001",
  "level": {
    "level": 15,
    "exp": 450,
    "total_exp": 5230,
    "title": "化学爱好者"
  },
  "stats": {
    "experiments_completed": 23,
    "perfect_experiments": 5,
    "total_score": 2150,
    "daily_streak": 5
  },
  "achievements": [...],
  "quests": [...],
  "rewards": [...]
}
```

## 设计原则

1. **不破坏原有流程**：游戏化元素是额外奖励，不影响核心实验功能
2. **平面化设计**：使用现代平面设计风格，美观简洁
3. **渐进式解锁**：随等级提升逐步解锁新功能
4. **正向激励**：只有奖励没有惩罚，鼓励持续学习
5. **数据驱动**：所有游戏化元素基于实际实验数据

## 配置选项

可以通过配置调整游戏化系统：

```json
{
  "gamification": {
    "enabled": true,
    "show_panel": true,
    "exp_multiplier": 1.0,
    "achievement_notifications": true,
    "level_up_animations": true
  }
}
```

## 最佳实践

1. **定期完成任务**：每日任务提供稳定经验来源
2. **追求完美**：零失误和满分提供大量经验加成
3. **持续学习**：连续登录天数提升学习效率
4. **探索隐藏成就**：尝试不同时间段和实验方式
5. **收集全成就**：完成度提升成就感

## 常见问题

**Q: 游戏化会影响实验评分吗？**
A: 不会。游戏化系统完全独立，实验评分依然基于实验操作的准确性。

**Q: 如何查看所有成就？**
A: 在游戏化面板成就区域点击"查看全部"按钮。

**Q: 任务过期了怎么办？**
A: 每日任务每天刷新，每周任务每周一刷新，不用担心错过。

**Q: 经验值有上限吗？**
A: 经验值无上限，但等级上限为100级。

**Q: 可以关闭游戏化功能吗？**
A: 可以在设置中关闭游戏化面板显示，但数据仍会记录。

## 未来计划

- [ ] 排行榜系统
- [ ] 好友系统和PK功能
- [ ] 每月赛季奖励
- [ ] 更多自定义头像和主题
- [ ] 实验挑战模式
- [ ] 团队协作任务

---

更新日期：2025-10-06
版本：v1.0.0
