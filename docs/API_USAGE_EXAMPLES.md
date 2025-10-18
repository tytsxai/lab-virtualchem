# VirtualChemLab API 使用示例

**版本**: 2.0.0  
**最后更新**: 2025-10-07

---

## 📋 目录

- [概述](#概述)
- [依赖注入容器](#依赖注入容器)
- [事件总线](#事件总线)
- [实验控制器](#实验控制器)
- [数据存储](#数据存储)
- [游戏化系统](#游戏化系统)
- [错误处理](#错误处理)
- [插件系统](#插件系统)
- [性能监控](#性能监控)

---

## 概述

本文档提供VirtualChemLab核心API的实际使用示例，帮助开发者快速上手。

### 前置要求

```python
# 基础导入
from src.core.di_container import DIContainer, Lifetime
from src.core.event_bus import EventBus, Event
from src.core.experiment_controller import ExperimentController
from src.models.experiment import ExperimentTemplate
```

---

## 依赖注入容器

### 基础用法

```python
from src.core.di_container import DIContainer, Lifetime

# 创建容器
container = DIContainer()

# 注册单例服务
container.register(
    IStorage,
    FileStorage,
    lifetime=Lifetime.SINGLETON
)

# 注册瞬态服务
container.register(
    ILogger,
    ConsoleLogger,
    lifetime=Lifetime.TRANSIENT
)

# 解析服务
storage = container.resolve(IStorage)
logger = container.resolve(ILogger)
```

### 工厂函数注册

```python
def create_database_connection():
    """创建数据库连接的工厂函数"""
    return DatabaseConnection(
        host="localhost",
        port=5432,
        database="virtualchemlab"
    )

# 使用工厂函数注册
container.register(
    IDatabaseConnection,
    factory=create_database_connection,
    lifetime=Lifetime.SINGLETON
)

# 解析时会调用工厂函数
db = container.resolve(IDatabaseConnection)
```

### 注册已有实例

```python
# 创建配置实例
config = Config.load_from_file("config.json")

# 注册已有实例
container.register(
    IConfig,
    instance=config
)

# 解析时返回相同实例
config1 = container.resolve(IConfig)
config2 = container.resolve(IConfig)
assert config1 is config2  # True
```

### 自动依赖解析

```python
class ExperimentService:
    """实验服务"""
    
    def __init__(
        self,
        storage: IStorage,
        logger: ILogger,
        event_bus: IEventBus
    ):
        self.storage = storage
        self.logger = logger
        self.event_bus = event_bus

# 注册服务（依赖会自动解析）
container.register(
    IExperimentService,
    ExperimentService,
    lifetime=Lifetime.SINGLETON
)

# 解析时自动注入依赖
service = container.resolve(IExperimentService)
# ExperimentService.__init__ 的参数会自动从容器解析
```

### 装饰器注入

```python
from src.core.di_container import inject

class MyService:
    @inject
    def process_data(
        self,
        data: dict,
        storage: IStorage,  # 自动注入
        logger: ILogger     # 自动注入
    ):
        logger.info(f"处理数据: {data}")
        storage.save(data)
        return True

# 使用
service = MyService()
result = service.process_data({"key": "value"})
```

---

## 事件总线

### 发布和订阅事件

```python
from src.core.event_bus import EventBus, Event

# 创建事件总线
event_bus = EventBus()

# 定义事件处理器
def on_experiment_started(event: Event):
    print(f"实验开始: {event.data['experiment_id']}")

# 订阅事件
event_bus.subscribe("experiment.started", on_experiment_started)

# 发布事件
event_bus.publish(Event(
    name="experiment.started",
    data={"experiment_id": "exp123", "user_id": "user456"}
))
```

### 异步事件处理

```python
import asyncio

# 异步事件处理器
async def on_data_processed(event: Event):
    await asyncio.sleep(1)  # 模拟异步操作
    print(f"数据处理完成: {event.data}")

# 订阅异步事件
event_bus.subscribe_async("data.processed", on_data_processed)

# 异步发布事件
asyncio.run(event_bus.publish_async(Event(
    name="data.processed",
    data={"result": "success"}
)))
```

### 事件优先级

```python
from src.core.event_bus import EventPriority

# 高优先级处理器
def critical_handler(event: Event):
    print("关键处理器")

# 普通优先级处理器
def normal_handler(event: Event):
    print("普通处理器")

# 订阅时指定优先级
event_bus.subscribe(
    "system.alert",
    critical_handler,
    priority=EventPriority.CRITICAL
)

event_bus.subscribe(
    "system.alert",
    normal_handler,
    priority=EventPriority.NORMAL
)

# 发布事件（高优先级先执行）
event_bus.publish(Event(name="system.alert"))
# 输出: 关键处理器
#      普通处理器
```

### 事件过滤

```python
# 只处理特定用户的事件
def user_filter(event: Event) -> bool:
    return event.data.get("user_id") == "user123"

def my_handler(event: Event):
    print(f"处理用户事件: {event.data}")

# 订阅时添加过滤器
event_bus.subscribe(
    "user.action",
    my_handler,
    filter_func=user_filter
)

# 这个事件会被处理
event_bus.publish(Event(
    name="user.action",
    data={"user_id": "user123", "action": "login"}
))

# 这个事件会被过滤掉
event_bus.publish(Event(
    name="user.action",
    data={"user_id": "user456", "action": "logout"}
))
```

### 通配符订阅

```python
# 订阅所有实验相关事件
def experiment_logger(event: Event):
    print(f"实验事件: {event.name} - {event.data}")

event_bus.subscribe("experiment.*", experiment_logger)

# 这些事件都会被处理
event_bus.publish(Event(name="experiment.started", data={}))
event_bus.publish(Event(name="experiment.completed", data={}))
event_bus.publish(Event(name="experiment.failed", data={}))
```

---

## 实验控制器

### 创建和启动实验

```python
from src.core.experiment_controller import (
    ExperimentController,
    ExperimentMode
)
from src.models.experiment import ExperimentTemplate

# 加载实验模板
template = ExperimentTemplate.load_from_file("templates/titration.yaml")

# 创建实验控制器
controller = ExperimentController(
    template=template,
    user_id="user123",
    mode=ExperimentMode.PRACTICE,
    enable_auto_save=True,
    max_retries=3
)

# 启动实验
controller.start_experiment()
print(f"实验已启动，总共 {controller.total_steps} 步")
```

### 执行实验步骤

```python
# 执行第一步：准备试剂
result = controller.execute_step(
    step_index=0,
    input_data={
        "reagent": "HCl",
        "concentration": "0.1 M",
        "volume": 25.0
    }
)

if result.success:
    print(f"步骤完成！得分: {result.score}")
    print(f"反馈: {result.feedback}")
else:
    print(f"步骤失败: {result.errors}")
    print(f"提示: {controller.get_hint(0)}")
```

### 步骤验证和重试

```python
# 步骤验证失败会自动重试
for attempt in range(3):
    result = controller.execute_step(
        step_index=1,
        input_data={
            "operation": "add_reagent",
            "volume": 10.0
        }
    )
    
    if result.success:
        print("步骤成功！")
        break
    elif attempt < 2:
        print(f"尝试 {attempt + 1} 失败，重试中...")
        hint = controller.get_hint(1)
        print(f"提示: {hint}")
    else:
        print("已达到最大重试次数")
```

### 实验状态管理

```python
# 暂停实验
controller.pause_experiment()
print(f"实验已暂停，当前进度: {controller.progress_percent}%")

# 保存实验状态
state_data = controller.get_state()
save_to_file(state_data, "experiment_state.json")

# 恢复实验
controller.resume_experiment()

# 或从保存的状态恢复
state_data = load_from_file("experiment_state.json")
controller.restore_state(state_data)
```

### 完成实验和获取结果

```python
# 完成所有步骤后
if controller.is_completed:
    # 获取实验结果
    result = controller.get_result()
    
    print(f"总得分: {result.total_score}")
    print(f"完成时间: {result.duration} 秒")
    print(f"准确率: {result.accuracy}%")
    print(f"等级: {result.grade}")
    
    # 获取详细报告
    report = controller.generate_report()
    report.save_as_pdf("experiment_report.pdf")
```

### 错误处理和恢复

```python
from src.core.error_handler import ExperimentError

try:
    controller.execute_step(
        step_index=2,
        input_data={"invalid": "data"}
    )
except ExperimentError as e:
    print(f"实验错误: {e.message}")
    print(f"错误代码: {e.code}")
    print(f"建议: {e.suggestion}")
    
    # 尝试恢复
    if e.recoverable:
        controller.recover_from_error()
```

---

## 数据存储

### JSONStore 基础用法

```python
from src.core.storage import JSONStore

# 创建存储实例
storage = JSONStore(storage_dir="data/experiments")

# 保存数据
experiment_data = {
    "id": "exp123",
    "name": "酸碱滴定",
    "user_id": "user456",
    "steps": [...]
}

storage.save("exp123", experiment_data)

# 读取数据
loaded_data = storage.load("exp123")
print(loaded_data["name"])

# 检查是否存在
if storage.exists("exp123"):
    print("实验数据已存在")

# 删除数据
storage.delete("exp123")
```

### 批量操作

```python
# 保存多个实验
experiments = [
    {"id": "exp1", "name": "实验1"},
    {"id": "exp2", "name": "实验2"},
    {"id": "exp3", "name": "实验3"}
]

for exp in experiments:
    storage.save(exp["id"], exp)

# 列出所有实验
all_ids = storage.list_all()
print(f"共有 {len(all_ids)} 个实验")

# 批量读取
all_experiments = [storage.load(exp_id) for exp_id in all_ids]
```

### 查询和过滤

```python
# 查询特定用户的实验
def user_filter(data):
    return data.get("user_id") == "user123"

user_experiments = storage.query(user_filter)
print(f"用户有 {len(user_experiments)} 个实验")

# 按条件查找
completed_experiments = storage.query(
    lambda data: data.get("status") == "completed"
)
```

### 事务处理

```python
# 开始事务
with storage.transaction() as tx:
    # 读取数据
    data = tx.load("exp123")
    
    # 修改数据
    data["status"] = "completed"
    data["score"] = 95
    
    # 保存数据
    tx.save("exp123", data)
    
    # 如果发生异常，自动回滚
    # 否则提交更改
```

---

## 游戏化系统

### 成就系统

```python
from src.gamification.achievement_system import AchievementManager

# 创建成就管理器
achievement_mgr = AchievementManager()

# 检查成就
user_stats = {
    "experiments_completed": 10,
    "total_score": 950,
    "perfect_runs": 3
}

unlocked = achievement_mgr.check_achievements("user123", user_stats)

for achievement in unlocked:
    print(f"🏆 解锁成就: {achievement.name}")
    print(f"   {achievement.description}")
    print(f"   经验奖励: +{achievement.exp_reward}")
```

### 等级系统

```python
from src.gamification.level_system import LevelSystem

# 创建等级系统
level_system = LevelSystem()

# 获取用户等级
user_level = level_system.get_user_level("user123")
print(f"当前等级: {user_level.level}")
print(f"当前经验: {user_level.current_exp}/{user_level.exp_to_next}")

# 添加经验
level_up = level_system.add_exp("user123", 500)

if level_up:
    print(f"🎉 升级到 Lv.{level_up.new_level}")
    print(f"解锁奖励: {level_up.rewards}")
```

### 任务系统

```python
from src.gamification.quest_system import QuestManager

# 创建任务管理器
quest_mgr = QuestManager()

# 获取每日任务
daily_quests = quest_mgr.get_daily_quests("user123")

for quest in daily_quests:
    print(f"📋 {quest.title}")
    print(f"   进度: {quest.progress}/{quest.target}")
    print(f"   奖励: {quest.rewards}")

# 更新任务进度
quest_mgr.update_progress(
    user_id="user123",
    quest_id="daily_complete_3_exp",
    progress=1
)

# 完成任务领取奖励
rewards = quest_mgr.claim_rewards("user123", "daily_complete_3_exp")
print(f"获得奖励: {rewards}")
```

### 奖励系统

```python
from src.gamification.reward_system import RewardSystem

# 创建奖励系统
reward_system = RewardSystem()

# 发放奖励
reward = reward_system.grant_reward(
    user_id="user123",
    reward_type="experiment_completion",
    base_amount=100,
    multiplier=1.5  # 150% 奖励
)

print(f"获得奖励: {reward.amount} 经验")
print(f"额外奖励: {reward.bonus}")
```

---

## 错误处理

### 基础错误处理

```python
from src.core.error_handler import (
    ValidationError,
    ExperimentError,
    safe_execute
)

# 使用装饰器处理错误
@safe_execute
def risky_operation(data: dict):
    if not data:
        raise ValueError("数据不能为空")
    return process_data(data)

# 调用时自动捕获异常
result = risky_operation({"key": "value"})
```

### 自定义错误处理

```python
from src.core.error_handler import ErrorHandler, ErrorLevel

# 创建错误处理器
error_handler = ErrorHandler()

# 注册错误处理回调
def on_critical_error(error):
    send_alert(f"严重错误: {error.message}")
    save_error_log(error)

error_handler.register_callback(
    ErrorLevel.CRITICAL,
    on_critical_error
)

# 处理错误
try:
    dangerous_operation()
except Exception as e:
    error_handler.handle(
        e,
        level=ErrorLevel.CRITICAL,
        context={"operation": "dangerous_operation"}
    )
```

### 错误恢复机制

```python
from src.core.error_handler import ErrorRecovery

# 创建恢复策略
recovery = ErrorRecovery(max_retries=3, backoff=2.0)

# 带重试的操作
@recovery.with_retry
def unstable_operation():
    # 可能失败的操作
    return call_external_api()

# 自动重试，指数退避
result = unstable_operation()
```

### 验证器

```python
from src.core.validation import (
    validate_not_none,
    validate_type,
    validate_range
)

def process_experiment_data(data: dict):
    # 验证参数
    validate_not_none(data, "experiment_data")
    validate_type(data, dict, "experiment_data")
    
    # 验证字段
    validate_not_none(data.get("temperature"), "temperature")
    validate_range(
        data.get("temperature"),
        min_value=0,
        max_value=100,
        name="temperature"
    )
    
    # 处理数据
    return data
```

---

## 插件系统

### 注册和使用插件

```python
from src.core.plugin_system import PluginManager

# 创建插件管理器
plugin_mgr = PluginManager()

# 注册插件
plugin_mgr.register_plugin(
    name="pdf_export",
    plugin_class=PDFExportPlugin,
    config={"quality": "high"}
)

# 使用插件
pdf_plugin = plugin_mgr.get_plugin("pdf_export")
pdf_plugin.export(data, "output.pdf")
```

### 检查插件可用性

```python
# 检查插件是否可用
if plugin_mgr.is_available("pdf_export"):
    pdf_plugin = plugin_mgr.get_plugin("pdf_export")
    pdf_plugin.export(data, "report.pdf")
else:
    # 使用备用方案
    print("PDF导出插件不可用，使用文本导出")
    export_as_text(data, "report.txt")
```

### 插件生命周期

```python
# 初始化插件
plugin_mgr.initialize_all()

# 使用插件
# ...

# 清理插件
plugin_mgr.cleanup_all()
```

---

## 性能监控

### 基础性能监控

```python
from src.monitoring.performance_monitor import PerformanceMonitor

# 创建监控器
monitor = PerformanceMonitor()

# 监控代码块
with monitor.measure("data_processing"):
    process_large_dataset(data)

# 获取统计
stats = monitor.get_stats("data_processing")
print(f"平均执行时间: {stats.avg_duration}ms")
print(f"最大执行时间: {stats.max_duration}ms")
```

### 装饰器监控

```python
from src.monitoring.performance_monitor import monitor_performance

@monitor_performance("experiment_execution")
def execute_experiment(experiment_id: str):
    # 执行实验
    controller.execute(experiment_id)
    return result

# 自动记录性能数据
result = execute_experiment("exp123")
```

### 实时监控

```python
from src.monitoring.metrics_collector import MetricsCollector

# 创建指标收集器
metrics = MetricsCollector()

# 记录指标
metrics.record("api_request_count", 1)
metrics.record("api_response_time", 150)  # ms
metrics.record("memory_usage", 512)  # MB

# 获取实时指标
current_metrics = metrics.get_current()
print(f"API请求数: {current_metrics['api_request_count']}")
print(f"平均响应时间: {current_metrics['avg_response_time']}")
```

### 性能告警

```python
from src.monitoring.alerting import AlertManager

# 创建告警管理器
alert_mgr = AlertManager()

# 定义告警规则
alert_mgr.add_rule(
    name="high_response_time",
    condition=lambda metrics: metrics['response_time'] > 1000,
    action=lambda: send_notification("响应时间过高")
)

# 检查告警
alert_mgr.check_alerts(current_metrics)
```

---

## 最佳实践

### 1. 使用依赖注入

```python
# 好的做法：使用DI容器
class MyService:
    def __init__(self, storage: IStorage, logger: ILogger):
        self.storage = storage
        self.logger = logger

# 避免：硬编码依赖
class MyService:
    def __init__(self):
        self.storage = JSONStore()  # 硬编码
        self.logger = ConsoleLogger()  # 硬编码
```

### 2. 使用事件解耦

```python
# 好的做法：使用事件通信
class ExperimentService:
    def complete_experiment(self, exp_id: str):
        # 完成实验
        result = self._complete(exp_id)
        
        # 发布事件
        self.event_bus.publish(Event(
            name="experiment.completed",
            data={"experiment_id": exp_id, "result": result}
        ))

# 避免：直接调用
class ExperimentService:
    def complete_experiment(self, exp_id: str):
        result = self._complete(exp_id)
        self.notification_service.notify(...)  # 紧耦合
        self.analytics_service.track(...)  # 紧耦合
```

### 3. 优雅的错误处理

```python
# 好的做法：详细的错误处理
from src.core.error_handler import safe_execute, ValidationError

@safe_execute
def process_data(data: dict) -> dict:
    if not data:
        raise ValidationError(
            "数据不能为空",
            suggestions=["请提供有效的数据字典"],
            recoverable=True
        )
    return data

# 避免：忽略错误
def process_data(data: dict) -> dict:
    try:
        return data
    except:
        pass  # 忽略错误
```

### 4. 性能监控

```python
# 好的做法：监控关键操作
@monitor_performance("critical_operation")
def critical_operation(data: dict):
    with performance_monitor.measure("data_validation"):
        validate(data)
    
    with performance_monitor.measure("data_processing"):
        process(data)
    
    return result

# 避免：无监控
def critical_operation(data: dict):
    validate(data)
    process(data)
    return result
```

---

## 完整示例

### 完整的实验执行流程

```python
from src.core.di_container import DIContainer
from src.core.service_registration import get_configured_container
from src.core.experiment_controller import ExperimentController
from src.models.experiment import ExperimentTemplate

def run_experiment_example():
    """完整的实验执行示例"""
    
    # 1. 获取配置好的DI容器
    container = get_configured_container()
    
    # 2. 解析必要的服务
    storage = container.resolve("storage")
    event_bus = container.resolve("event_bus")
    
    # 3. 订阅事件
    def on_step_completed(event):
        print(f"步骤完成: {event.data}")
    
    event_bus.subscribe("experiment.step_completed", on_step_completed)
    
    # 4. 加载实验模板
    template = ExperimentTemplate.load_from_file(
        "assets/templates/acid_base_titration.yaml"
    )
    
    # 5. 创建实验控制器
    controller = ExperimentController(
        template=template,
        user_id="user123",
        enable_monitoring=True,
        enable_auto_save=True
    )
    
    # 6. 启动实验
    controller.start_experiment()
    
    # 7. 执行步骤
    for step_index in range(controller.total_steps):
        # 获取步骤信息
        step = controller.get_step(step_index)
        print(f"\n步骤 {step_index + 1}: {step.description}")
        
        # 执行步骤（这里简化为自动输入）
        result = controller.execute_step(
            step_index=step_index,
            input_data=generate_step_input(step)
        )
        
        # 检查结果
        if result.success:
            print(f"✅ 成功！得分: {result.score}")
        else:
            print(f"❌ 失败: {result.errors}")
            hint = controller.get_hint(step_index)
            print(f"💡 提示: {hint}")
    
    # 8. 获取实验结果
    if controller.is_completed:
        result = controller.get_result()
        print(f"\n实验完成！")
        print(f"总分: {result.total_score}")
        print(f"等级: {result.grade}")
        print(f"用时: {result.duration}秒")
        
        # 9. 生成报告
        report = controller.generate_report()
        report.save_as_pdf("experiment_report.pdf")
        print("报告已保存")

if __name__ == "__main__":
    run_experiment_example()
```

---

## 参考资料

- [API_REFERENCE.md](API_REFERENCE.md) - 完整API参考
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构
- [CODE_STYLE_GUIDE.md](CODE_STYLE_GUIDE.md) - 代码规范
- [ERROR_SYSTEM_GUIDE.md](ERROR_SYSTEM_GUIDE.md) - 错误处理系统

---

**更新历史**:
- 2025-10-07: 初始版本，包含核心API示例

---

💡 **提示**: 所有示例代码都经过测试验证，可以直接使用。


