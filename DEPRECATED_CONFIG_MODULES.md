# 已弃用的配置模块

以下配置模块已被弃用，请使用 `src/core/config_loader.py` 中的新配置系统：

## 已弃用的模块

1. `src/core/config.py` - 旧配置系统
2. `src/core/config_manager.py` - 另一个配置管理器
3. `src/config/config_manager.py` - 第三个配置管理器

## 迁移指南

### 旧代码

```python
from src.core.config import JsonConfig
from src.core.config_manager import ConfigManager

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
