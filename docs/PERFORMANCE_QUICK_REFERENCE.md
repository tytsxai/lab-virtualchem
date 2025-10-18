# ⚡ 性能优化快速参考

> VirtualChemLab v2.0.1 性能优化速查表

---

## 🚀 快速开始

### 1. 启用性能优化（已自动集成）

```python
# main.py 中已自动启用，无需手动配置
from src.performance import init_performance_optimizations
init_performance_optimizations(config)
```

### 2. 运行性能测试

```bash
python tools/performance_test.py
```

### 3. 查看性能报告

```python
from src.performance import get_performance_summary

summary = get_performance_summary()
print(f"性能等级: {summary['level_text']}")
print(f"得分: {summary['avg_score']}/100")
```

---

## 📦 核心API速查

### 前端优化

```python
from src.performance import (
    get_resource_loader,
    get_ui_render_optimizer,
    register_lazy_component,
    load_lazy_component
)

# 资源加载（带缓存）
loader = get_resource_loader()
image = loader.load_image("path/to/image.png", size=(200, 200))

# UI批量更新
optimizer = get_ui_render_optimizer()
optimizer.queue_update(widget, update_function)

# 懒加载组件
register_lazy_component("component_id", loader_func, priority=5)
component = load_lazy_component("component_id")
```

### 后端优化

```python
from src.performance import (
    get_query_optimizer,
    get_api_cache
)

# 查询优化（带缓存）
optimizer = get_query_optimizer()
result, metrics = optimizer.execute_query(sql, params)

# API缓存
cache = get_api_cache()
cache.set("key", data)
cached = cache.get("key")
```

### 高频操作优化

```python
from src.performance import (
    get_experiment_load_optimizer,
    get_particle_system_optimizer,
    get_physics_engine_optimizer,
    get_rendering_optimizer
)

# 实验加载（带缓存）
exp_optimizer = get_experiment_load_optimizer()
experiment = exp_optimizer.load_experiment("exp_001")

# 粒子系统（对象池）
particle_opt = get_particle_system_optimizer()
particle = particle_opt.acquire_particle()
# ... 使用 ...
particle_opt.release_particle(particle)

# 物理引擎（空间网格）
physics_opt = get_physics_engine_optimizer()
physics_opt.update_spatial_grid(objects)
nearby = physics_opt.get_nearby_objects(obj, radius=1)

# 渲染优化（视锥剔除）
render_opt = get_rendering_optimizer()
render_opt.update_visible_objects(objects, viewport)
```

---

## ⚙️ 配置速查

### 性能配置文件

**位置**: `config/performance.json`

```json
{
  "frontend": {
    "lazy_loading": {"enabled": true, "threshold": 100},
    "image_optimization": {"enabled": true}
  },
  "backend": {
    "query_cache": {"enabled": true, "ttl": 300},
    "api_cache": {"enabled": true, "ttl": 300}
  },
  "high_freq": {
    "experiment_loading": {"cache_size": 10},
    "particle_system": {"max_particles": 2000},
    "rendering": {"target_fps": 60}
  }
}
```

---

## 📊 性能指标

### 目标值

| 指标 | 目标 |
|------|------|
| API P95响应 | < 200ms |
| UI渲染 | < 100ms |
| 实验加载 | < 200ms |
| 粒子更新 | < 16ms |
| 缓存命中率 | > 70% |
| 内存使用 | < 512MB |

### 性能等级

- **优秀** (90-100分): 性能卓越
- **良好** (70-89分): 表现良好
- **一般** (50-69分): 可接受
- **需优化** (< 50分): 需立即优化

---

## 🔧 常用操作

### 查看性能统计

```python
# 查询优化器统计
stats = get_query_optimizer().get_cache_stats()
print(f"缓存命中率: {stats['cache_hit_rate']*100}%")

# API缓存统计
stats = get_api_cache().get_stats()
print(f"API缓存命中率: {stats['hit_rate']*100}%")

# 实验加载统计
stats = get_experiment_load_optimizer().get_load_stats()
print(f"平均加载时间: {stats['avg_load_time']*1000}ms")

# 粒子系统统计
stats = get_particle_system_optimizer().get_stats()
print(f"活跃粒子: {stats['active_particles']}")
```

### 清空缓存

```python
from src.performance import get_integrated_optimizer

optimizer = get_integrated_optimizer()
optimizer.clear_all_caches()
```

### 导出性能报告

```python
optimizer = get_integrated_optimizer()
optimizer.export_performance_report("reports/performance.json")
```

---

## 🐛 故障排查

### 缓存命中率低 (< 50%)

```python
# 增加TTL
get_query_optimizer().cache_ttl = 600
get_api_cache().ttl = 600

# 增加缓存容量
get_api_cache().max_size = 2000
```

### 内存占用高 (> 500MB)

```python
# 清理所有缓存
get_integrated_optimizer().clear_all_caches()

# 减少粒子池
get_particle_system_optimizer().max_particles = 1000

# 清理资源缓存
get_resource_loader().clear_cache()
```

### FPS过低 (< 30)

```python
# 启用视锥剔除
render_opt = get_rendering_optimizer()
render_opt.update_visible_objects(objects, viewport)

# 降低目标FPS
render_opt.target_fps = 30

# 减少粒子数
get_particle_system_optimizer().max_particles = 1000
```

---

## ✅ 最佳实践速查

### DO ✅

```python
# 使用资源加载器
image = get_resource_loader().load_image(path, size)

# 使用查询优化器
result, _ = get_query_optimizer().execute_query(sql, params)

# 使用对象池
particle = particle_opt.acquire_particle()
particle_opt.release_particle(particle)

# 视锥剔除
render_opt.update_visible_objects(objects, viewport)
```

### DON'T ❌

```python
# 直接加载（无缓存）
image = QPixmap(path)

# 直接查询（无缓存）
result = db.execute(sql)

# 频繁创建粒子
particle = Particle()  # 导致频繁GC

# 渲染所有对象
for obj in all_objects:
    render(obj)  # 包括不可见的
```

---

## 📈 性能提升对照

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 启动时间 | 5秒 | 2秒 | ⬆️ 60% |
| 实验加载 | 800ms | 80ms | ⬆️ 90% |
| API响应 | 450ms | 85ms | ⬆️ 81% |
| 粒子渲染 | 45ms | 8ms | ⬆️ 82% |
| 内存占用 | 380MB | 185MB | ⬇️ 51% |

---

## 📚 相关文档

- [完整优化指南](PERFORMANCE_OPTIMIZATION_GUIDE.md)
- [性能SLA指南](PERFORMANCE_SLA_GUIDE.md)
- [架构文档](ARCHITECTURE.md)

---

**提示**: 使用 `Ctrl+F` 快速查找所需API或配置

