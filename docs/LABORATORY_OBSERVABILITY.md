# 🔬 实验室观测性指南

> VirtualChemLab 实验执行全程观测性解决方案

## 📋 目录

1. [概述](#概述)
2. [实验观测性架构](#实验观测性架构)
3. [核心功能](#核心功能)
4. [快速开始](#快速开始)
5. [实验指标详解](#实验指标详解)
6. [使用示例](#使用示例)
7. [配置选项](#配置选项)
8. [最佳实践](#最佳实践)

---

## 概述

实验室观测性是 VirtualChemLab 的核心能力之一,提供实验执行全过程的可见性和可追踪性。通过集成的监控系统,可以:

- ✅ **追踪实验执行** - 从开始到完成的完整链路追踪
- ✅ **收集性能指标** - 实验时长、步骤耗时、验证性能
- ✅ **分析实验数据** - 评分分布、错误类型、完成率
- ✅ **监控系统健康** - 资源使用、错误率、活跃实验
- ✅ **用户行为分析** - 实验历史、热门实验、学习轨迹

### 架构概览

```
┌─────────────────────────────────────────────┐
│        实验室观测性系统架构                   │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────┐       │
│  │     ExperimentController         │       │
│  │  (实验控制器 - 集成监控)          │       │
│  └──────────────┬───────────────────┘       │
│                 │                           │
│        ┌────────┴───────┬──────────┐        │
│        │                │          │        │
│  ┌─────▼─────┐  ┌──────▼───┐  ┌──▼──────┐  │
│  │ APM 指标  │  │ 分布式   │  │ 实验    │  │
│  │           │  │ 追踪     │  │ 指标    │  │
│  │• 计数器   │  │• TraceID │  │• 评分   │  │
│  │• 仪表     │  │• Span    │  │• 时长   │  │
│  │• 直方图   │  │• 日志    │  │• 错误   │  │
│  │• 计时器   │  │• 标签    │  │• 步骤   │  │
│  └───────────┘  └──────────┘  └─────────┘  │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │        数据持久化                   │    │
│  │  • JSONL 日志文件                   │    │
│  │  • 时间序列数据                     │    │
│  │  • 聚合统计信息                     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 实验观测性架构

### 1. 三层监控体系

#### 第一层: APM 应用性能监控

实时记录实验执行的关键性能指标:

| 指标类型 | 指标名称 | 说明 | 标签 |
|---------|---------|------|------|
| Counter | `experiment.initialized` | 实验初始化次数 | experiment_id, user_id |
| Counter | `experiment.started` | 实验开始次数 | experiment_id, experiment_type |
| Counter | `experiment.completed` | 实验完成次数 | experiment_id, experiment_type |
| Counter | `experiment.step.passed` | 步骤通过次数 | experiment_id, step_id |
| Counter | `experiment.step.failed` | 步骤失败次数 | experiment_id, step_id, severity |
| Gauge | `experiment.active` | 当前活跃实验数 | experiment_id, user_id |
| Gauge | `experiment.steps.total` | 实验总步骤数 | experiment_id |
| Histogram | `experiment.duration_seconds` | 实验总时长(秒) | experiment_id |
| Histogram | `experiment.score` | 实验得分 | experiment_id |
| Histogram | `experiment.mistakes` | 错误次数 | experiment_id |
| Histogram | `experiment.step.duration_ms` | 步骤执行时间(毫秒) | experiment_id, step_id, passed |
| Histogram | `experiment.step.validation_duration_ms` | 步骤验证时间(毫秒) | experiment_id, step_id |

#### 第二层: 分布式追踪

为每个实验执行创建完整的追踪链路:

```
Trace: experiment.execute (实验主追踪)
├─ Span: experiment.step.prepare_reagents
│  ├─ 标签: step_id=prepare_reagents, step_index=0
│  ├─ 事件: step_passed, attempts=1
│  └─ 持续时间: 1.2s
├─ Span: experiment.step.titration
│  ├─ 标签: step_id=titration, step_index=1
│  ├─ 事件: step_failed, attempts=2, severity=moderate
│  └─ 持续时间: 3.5s
└─ 事件: experiment_completed
   └─ 属性: score=85, total_mistakes=1, completion_rate=100%
```

#### 第三层: 实验指标聚合

长期存储和分析实验数据:

- **实验维度**: 按实验ID聚合所有运行数据
- **用户维度**: 按用户ID追踪学习轨迹
- **时间维度**: 时间序列分析和趋势预测
- **步骤维度**: 细粒度的步骤统计分析

---

## 核心功能

### 1. 自动化监控集成

实验控制器(`ExperimentController`)自动集成监控,无需额外代码:

```python
from src.core.experiment_controller import ExperimentController
from src.models.experiment import ExperimentTemplate

# 加载实验模板
template = ExperimentTemplate.load("titration_experiment.yaml")

# 创建控制器(默认启用监控)
controller = ExperimentController(
    template=template,
    user_id="student_001",
    enable_monitoring=True  # 默认值,可省略
)

# 所有操作自动记录监控数据
controller.start_experiment()
controller.submit_step({"reagent": "HCl", "volume": 10.0})
controller.complete_experiment()

# 监控数据自动记录到:
# - logs/apm/metrics_YYYYMMDD.jsonl
# - logs/traces/traces_YYYYMMDD.jsonl
```

### 2. 实时指标查询

```python
from src.monitoring import get_experiment_metrics_collector

# 获取指标收集器
collector = get_experiment_metrics_collector()

# 查询实验指标
metrics = collector.get_experiment_metrics("exp_titration_001")

print(f"实验: {metrics.experiment_title}")
print(f"总运行次数: {metrics.total_runs}")
print(f"完成率: {metrics.completion_rate:.1f}%")
print(f"平均得分: {metrics.avg_score:.1f}")
print(f"平均时长: {metrics.avg_duration_seconds:.1f}秒")
print(f"平均错误: {metrics.avg_mistakes_per_run:.1f}次")
```

### 3. 聚合统计分析

```python
# 获取所有实验汇总
summary = collector.get_all_experiments_summary()

for exp in summary:
    print(f"{exp['experiment_title']}: "
          f"{exp['total_runs']}次运行, "
          f"完成率{exp['completion_rate']:.1f}%, "
          f"平均分{exp['avg_score']:.1f}")

# 获取用户实验历史
history = collector.get_user_experiment_history("student_001", limit=5)

for run in history:
    print(f"{run['timestamp']}: {run['experiment_title']} - "
          f"得分{run['score']['total']}")

# 获取热门实验
popular = collector.get_popular_experiments(limit=10)

for exp in popular:
    print(f"{exp['experiment_title']}: {exp['total_runs']}次运行")
```

### 4. 分布式追踪查询

```python
from src.monitoring import get_trace_manager

trace_mgr = get_trace_manager()

# 获取追踪树
trace_tree = trace_mgr.get_trace_tree("trace_id_123")

print(f"总持续时间: {trace_tree['total_duration_ms']}ms")
print(f"根操作: {trace_tree['root_operation']}")
print(f"子操作数: {len(trace_tree['children'])}")

# 遍历所有步骤
for span in trace_tree['children']:
    print(f"  {span['operation_name']}: {span['duration_ms']}ms")
    print(f"    状态: {span['status']}")
    print(f"    标签: {span['tags']}")

# 获取统计信息
stats = trace_mgr.get_statistics(since_minutes=60)

print(f"最近1小时:")
print(f"  总追踪数: {stats['total_traces']}")
print(f"  成功率: {stats['success_rate']:.1f}%")
print(f"  平均时长: {stats['avg_duration_ms']}ms")
```

---

## 快速开始

### 1. 基础使用

```python
from src.core.experiment_controller import ExperimentController
from src.models.experiment import ExperimentTemplate

# 1. 加载实验模板
template = ExperimentTemplate.load("assets/templates/acid_base_titration.yaml")

# 2. 创建控制器(监控自动启用)
controller = ExperimentController(
    template=template,
    user_id="student_zhang",
)

# 3. 开始实验(开始追踪)
controller.start_experiment()

# 4. 执行实验步骤(自动记录指标)
step1_input = {"reagent": "NaOH", "concentration": 0.1}
passed, message, mistake = controller.submit_step(step1_input)

if passed:
    controller.next_step()

# 5. 完成实验(结束追踪,记录聚合数据)
record = controller.complete_experiment()

print(f"实验完成!")
print(f"得分: {record.score.total}")
print(f"耗时: {record.total_duration_seconds}秒")
```

### 2. 查询实验指标

```python
from src.monitoring import get_experiment_metrics_collector

collector = get_experiment_metrics_collector()

# 获取特定实验的指标
metrics = collector.get_experiment_metrics("exp_acid_base_titration")

# 评分分布
print("评分分布:")
for range_name, count in metrics.score_distribution.items():
    print(f"  {range_name}分: {count}人")

# 步骤通过率
print("\n步骤通过率:")
for step_id, rate in metrics.step_pass_rates.items():
    print(f"  {step_id}: {rate:.1f}%")

# 错误类型分析
print("\n错误类型:")
for error_type, count in metrics.mistake_types.items():
    print(f"  {error_type}: {count}次")
```

### 3. 导出监控数据

```python
# 导出为字典
data = metrics.to_dict()

# 保存为JSON
import json
with open("experiment_metrics.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 或导出所有实验汇总
summary = collector.get_all_experiments_summary()
with open("experiments_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
```

---

## 实验指标详解

### ExperimentMetrics 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `experiment_id` | str | 实验唯一标识符 |
| `experiment_title` | str | 实验标题 |
| `experiment_type` | str | 实验类型(titration/synthesis等) |
| `total_runs` | int | 总运行次数 |
| `completed_runs` | int | 完成的运行次数 |
| `abandoned_runs` | int | 放弃的运行次数 |
| `completion_rate` | float | 完成率(%) |
| `avg_duration_seconds` | float | 平均时长(秒) |
| `min_duration_seconds` | float | 最短时长(秒) |
| `max_duration_seconds` | float | 最长时长(秒) |
| `avg_score` | float | 平均得分 |
| `min_score` | int | 最低得分 |
| `max_score` | int | 最高得分 |
| `score_distribution` | dict | 评分分布(0-59, 60-79, 80-89, 90-100) |
| `total_mistakes` | int | 总错误次数 |
| `avg_mistakes_per_run` | float | 平均每次实验的错误数 |
| `mistake_types` | dict | 错误类型统计 |
| `total_steps` | int | 实验总步骤数 |
| `step_pass_rates` | dict | 各步骤通过率(%) |
| `step_avg_attempts` | dict | 各步骤平均尝试次数 |
| `first_run_at` | datetime | 首次运行时间 |
| `last_run_at` | datetime | 最后运行时间 |

---

## 使用示例

### 示例1: 实验性能分析

```python
from src.monitoring import get_experiment_metrics_collector

collector = get_experiment_metrics_collector()

def analyze_experiment_performance(experiment_id: str):
    """分析实验性能"""
    metrics = collector.get_experiment_metrics(experiment_id)

    print(f"=== {metrics.experiment_title} 性能分析 ===\n")

    # 完成率分析
    print(f"完成率: {metrics.completion_rate:.1f}%")
    if metrics.completion_rate < 80:
        print("  ⚠️  完成率偏低,建议优化实验难度")

    # 时长分析
    print(f"\n时长统计:")
    print(f"  平均: {metrics.avg_duration_seconds:.1f}秒")
    print(f"  范围: {metrics.min_duration_seconds:.1f} - {metrics.max_duration_seconds:.1f}秒")

    # 评分分析
    print(f"\n评分统计:")
    print(f"  平均分: {metrics.avg_score:.1f}")
    print(f"  分数范围: {metrics.min_score} - {metrics.max_score}")
    print(f"\n评分分布:")
    for range_name, count in metrics.score_distribution.items():
        percentage = (count / metrics.total_runs * 100) if metrics.total_runs > 0 else 0
        print(f"  {range_name}分: {count}人 ({percentage:.1f}%)")

    # 难点步骤识别
    print(f"\n难点步骤 (通过率 < 80%):")
    difficult_steps = {
        step_id: rate
        for step_id, rate in metrics.step_pass_rates.items()
        if rate < 80
    }

    if difficult_steps:
        for step_id, rate in sorted(difficult_steps.items(), key=lambda x: x[1]):
            avg_attempts = metrics.step_avg_attempts.get(step_id, 0)
            print(f"  {step_id}: 通过率{rate:.1f}%, 平均尝试{avg_attempts:.1f}次")
    else:
        print("  ✅ 没有明显难点")

    # 常见错误
    print(f"\n常见错误:")
    sorted_mistakes = sorted(
        metrics.mistake_types.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    for error_type, count in sorted_mistakes:
        print(f"  {error_type}: {count}次")

# 使用示例
analyze_experiment_performance("exp_acid_base_titration")
```

### 示例2: 学生学习轨迹分析

```python
def analyze_student_progress(user_id: str):
    """分析学生学习进度"""
    collector = get_experiment_metrics_collector()
    history = collector.get_user_experiment_history(user_id, limit=20)

    print(f"=== 学生 {user_id} 学习轨迹 ===\n")

    if not history:
        print("暂无实验记录")
        return

    # 基本统计
    completed = [h for h in history if h.get("status") == "completed"]
    print(f"总实验次数: {len(history)}")
    print(f"完成次数: {len(completed)}")
    print(f"完成率: {len(completed)/len(history)*100:.1f}%")

    # 平均成绩
    if completed:
        avg_score = sum(h["score"]["total"] for h in completed) / len(completed)
        print(f"平均成绩: {avg_score:.1f}分")

        # 成绩趋势
        recent_5 = completed[:5]
        older_5 = completed[5:10] if len(completed) > 5 else []

        if older_5:
            recent_avg = sum(h["score"]["total"] for h in recent_5) / len(recent_5)
            older_avg = sum(h["score"]["total"] for h in older_5) / len(older_5)
            trend = recent_avg - older_avg

            print(f"\n成绩趋势:")
            print(f"  最近5次平均: {recent_avg:.1f}分")
            print(f"  之前5次平均: {older_avg:.1f}分")

            if trend > 5:
                print(f"  📈 进步明显 (+{trend:.1f}分)")
            elif trend < -5:
                print(f"  📉 需要关注 ({trend:.1f}分)")
            else:
                print(f"  ➡️  稳定 ({trend:+.1f}分)")

    # 最近实验列表
    print(f"\n最近实验:")
    for i, run in enumerate(history[:5], 1):
        status_emoji = "✅" if run.get("status") == "completed" else "❌"
        score = run.get("score", {}).get("total", 0)
        timestamp = run.get("timestamp", "").split(".")[0] if run.get("timestamp") else ""
        print(f"  {i}. {status_emoji} {run['experiment_title']} - {score}分 ({timestamp})")

# 使用示例
analyze_student_progress("student_zhang")
```

### 示例3: 热门实验仪表板

```python
def generate_dashboard():
    """生成实验仪表板"""
    collector = get_experiment_metrics_collector()

    print("=" * 60)
    print("           VirtualChemLab 实验仪表板")
    print("=" * 60)

    # 热门实验
    print("\n🔥 热门实验 TOP 5:")
    popular = collector.get_popular_experiments(limit=5)

    for i, exp in enumerate(popular, 1):
        print(f"\n{i}. {exp['experiment_title']}")
        print(f"   运行次数: {exp['total_runs']}")
        print(f"   平均分: {exp['avg_score']:.1f}")
        print(f"   完成率: {exp['completion_rate']:.1f}%")

    # 所有实验汇总
    summary = collector.get_all_experiments_summary()

    total_runs = sum(e['total_runs'] for e in summary)
    total_completed = sum(e['completed_runs'] for e in summary)

    print(f"\n📊 总体统计:")
    print(f"   实验总数: {len(summary)}")
    print(f"   总运行次数: {total_runs}")
    print(f"   总完成次数: {total_completed}")
    print(f"   整体完成率: {total_completed/total_runs*100:.1f}%" if total_runs > 0 else "   整体完成率: 0%")

    # 需要关注的实验
    print(f"\n⚠️  需要关注的实验 (完成率 < 70%):")
    low_completion = [
        e for e in summary
        if e['completion_rate'] < 70 and e['total_runs'] >= 5
    ]

    if low_completion:
        for exp in sorted(low_completion, key=lambda x: x['completion_rate']):
            print(f"   • {exp['experiment_title']}: {exp['completion_rate']:.1f}%")
    else:
        print("   ✅ 所有实验表现良好")

    print("\n" + "=" * 60)

# 使用示例
generate_dashboard()
```

---

## 配置选项

### 1. 监控配置文件

在 `config/monitoring_config.json` 中配置:

```json
{
  "monitoring": {
    "enabled": true,
    "app_name": "VirtualChemLab",

    "backend": {
      "apm": {
        "enabled": true,
        "log_dir": "logs/apm"
      }
    },

    "tracing": {
      "enabled": true,
      "service_name": "VirtualChemLab",
      "log_dir": "logs/traces",
      "sample_rate": 1.0
    },

    "experiment_metrics": {
      "enabled": true,
      "cache_ttl_minutes": 5,
      "retention_days": 30
    }
  }
}
```

### 2. 程序化配置

```python
from src.core.experiment_controller import ExperimentController

# 禁用监控
controller = ExperimentController(
    template=template,
    user_id=user_id,
    enable_monitoring=False  # 禁用
)

# 或通过环境变量
import os
os.environ['DISABLE_MONITORING'] = '1'
```

### 3. 数据保留策略

```python
from src.monitoring import get_experiment_metrics_collector

collector = get_experiment_metrics_collector()

# 清理30天前的数据
cleared_count = collector.clear_old_data(days=30)
print(f"清理了 {cleared_count} 条旧数据")
```

---

## 最佳实践

### 1. 监控数据的使用原则

✅ **推荐做法:**

- 定期分析实验指标,优化实验设计
- 识别难点步骤,提供针对性帮助
- 追踪学生进步,个性化教学
- 监控系统健康,及时发现问题

❌ **避免做法:**

- 不要过度依赖监控数据评估学生
- 不要在生产环境禁用监控
- 不要忽略低完成率的警告信号

### 2. 性能影响最小化

监控系统设计为轻量级:

- **APM 记录**: < 5ms 开销
- **追踪创建**: < 2ms 开销
- **指标聚合**: 异步后台处理
- **数据存储**: JSONL 格式,顺序写入

### 3. 数据隐私保护

- 监控数据仅包含实验执行信息
- 不记录学生个人敏感信息
- 用户ID可以是匿名标识符
- 定期清理过期数据

### 4. 故障处理

监控系统采用fail-safe设计:

```python
# 监控失败不会影响实验执行
try:
    # 记录监控数据
    self._monitor.apm.increment_counter("experiment.started")
except Exception as e:
    logger.warning(f"监控记录失败,继续执行: {e}")
    # 实验继续正常执行
```

---

## 日志文件结构

```
logs/
├── apm/
│   └── metrics_20251006.jsonl          # APM 指标日志
├── traces/
│   └── traces_20251006.jsonl           # 分布式追踪日志
├── frontend/
│   └── errors_20251006.jsonl           # 前端错误日志
└── behavior/
    └── events_20251006.jsonl           # 用户行为日志
```

每个文件都是 JSONL 格式(每行一个 JSON 对象),便于:

- 流式处理大文件
- 使用 jq 等工具查询
- 导入数据分析工具
- 按日期轮转存储

---

## 常见问题

### Q1: 监控会影响实验性能吗?

A: 监控开销极小(< 5ms/步骤),对用户体验无感知。

### Q2: 可以在运行时禁用监控吗?

A: 可以,通过 `enable_monitoring=False` 参数。但建议保持启用。

### Q3: 监控数据会占用多少磁盘空间?

A: 每个实验约 5-10KB 日志。可通过 `clear_old_data()` 定期清理。

### Q4: 如何导出监控数据到其他系统?

A: 读取 JSONL 日志文件,或调用 API 导出为 JSON/CSV 格式。

### Q5: 监控数据可以用于学生评估吗?

A: 可以作为参考,但不应作为唯一评估标准。重点关注学习进步趋势。

---

## 相关文档

- [监控与可观测性指南](./MONITORING_GUIDE.md)
- [API 协议文档](./API_EVENT_PROTOCOL.md)
- [实验系统增强说明](./实验系统增强说明.md)
- [性能优化指南](./PERFORMANCE_OPTIMIZATION.md)

---

**文档版本**: v1.0.0
**更新时间**: 2025-10-06
**维护团队**: VirtualChemLab Team
