# 配置一致性检查报告

## 发现的问题

### 1. 路径配置不一致

**问题**: 不同配置文件中的路径字段命名不一致

- `config.json`: 使用 `paths.templates`, `paths.knowledge`, `paths.i18n`
- `config/base.json`: 使用 `paths.templates_dir`, `paths.knowledge_dir`, `paths.i18n_dir`

**影响**: 可能导致配置加载失败或路径解析错误

### 2. 数据库配置不一致

**问题**: 数据库类型和配置方式不一致

- `config.json`: 使用 SQLite (`type: "sqlite"`)
- `config/base.json`: 使用 JSON (`type: "json"`)

**影响**: 可能导致数据存储方式混乱

### 3. 缓存配置不一致

**问题**: 缓存配置字段命名不一致

- `config.json`: 使用 `cache.enabled`
- `config/base.json`: 使用 `performance.cache_enabled`

**影响**: 可能导致缓存功能失效

## 修复建议

### 1. 统一路径配置

建议使用 `config.json` 的命名方式：

```json
{
    "paths": {
        "templates": "assets/templates",
        "knowledge": "assets/knowledge",
        "i18n": "assets/i18n",
        "user_data": "user_data",
        "reports": "reports"
    }
}
```

### 2. 统一数据库配置

建议使用 SQLite 作为默认数据库：

```json
{
    "database": {
        "type": "sqlite",
        "path": "data/virtualchemlab.db",
        "url": "sqlite:///data/virtualchemlab.db"
    }
}
```

### 3. 统一缓存配置

建议使用 `cache` 节点：

```json
{
    "cache": {
        "enabled": true,
        "type": "memory",
        "max_size": 500
    }
}
```

## 优先级

- **高优先级**: 路径配置不一致
- **中优先级**: 数据库配置不一致
- **低优先级**: 缓存配置不一致

## 下一步行动

1. 更新 `config/base.json` 使用统一的字段命名
2. 更新 `config/development.json` 和 `config/production.json` 继承基础配置
3. 测试配置加载确保一致性
