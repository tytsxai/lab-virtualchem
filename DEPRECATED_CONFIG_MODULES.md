# 已弃用/易混淆的配置模块说明

本仓库存在多套“配置”概念，为避免维护者误改/误用，先明确边界：

- **启动配置（Source of Truth）**：`src/core/config_loader.py`
  - 负责 `.env`/配置文件/环境变量合并、运行时目录策略、生产 fail-fast（密钥/安全闸）
  - GUI 启动与 DI 容器注册默认使用该配置（见 `src/core/service_registration.py`）
- **用户运行时设置（UI/偏好）**：`src/core/config_manager.py`
  - 负责在运行时目录持久化“可变设置”（窗口大小、UI 开关、游戏参数等）
  - 使用 JSON Schema 校验，不用于生产密钥策略

下文“已弃用”的模块指：不再作为上述两类配置的推荐入口。

## 已弃用的模块

1. `src/core/config.py` - 旧配置系统
2. `src/config/config_manager.py` - 旧配置系统（第三套配置管理器，建议逐步迁移/移除）

## 迁移指南

### 旧代码

```python
from src.core.config import JsonConfig

# 旧方式
config = JsonConfig("config.json")
value = config.get("app.debug", False)
```

### 新代码

```python
from src.core.config_loader import get_config

# 新方式
config = get_config()
value = config.app.debug
```

## 迁移状态

- [x] `src/core/service_registration.py` - 已迁移到新配置系统
- [ ] 其他模块仍在迁移中

## 删除计划

这些模块将在所有引用迁移完成后删除。
