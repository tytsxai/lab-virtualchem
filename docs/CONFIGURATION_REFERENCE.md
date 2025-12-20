# Configuration Reference (Source of Truth)

本页是“维护安全”视角下的配置事实来源：它只描述当前实现确实读取/生效的配置项与环境变量，并明确优先级与风险点。

如果你在文档里看到与本页冲突的描述，应以代码实现为准，并优先更新文档（参考 `docs/DOCS_STATUS.md`）。

默认使用场景：**本地桌面单机**（macOS/Windows/Linux）。REST API 与 Admin API 为可选组件，通常只在内网或本机开启。

## 1. 配置优先级与加载顺序

当前主配置加载入口为 `src/core/config_loader.py`，其核心顺序为：

1. 读取 `.env`（若存在；不会覆盖已存在的环境变量）
2. 判定环境 `ENVIRONMENT`（优先级：显式传参 > `ENVIRONMENT` env > 打包默认 production > 默认 development）
3. 深度合并配置文件（存在则参与合并）：
   - `config/base.json`（基线）
   - `config.json`（仓库根目录，本地覆盖/兼容旧入口）
   - `config/<environment>.json`（环境覆盖）
4. 环境变量覆盖（最高优先级）
5. 运行准备（目录创建/重定向、版本对齐等）

验证工具（推荐）：
- `python tools/validate_config.py`：按当前实现加载并输出关键路径/安全闸结论
- `python tools/reset_config.py`：备份后重置损坏的 `config.json`

## 2. 配置文件职责边界

- `config/base.json`：可运行的默认基线（应保持最小但完整）
- `config/<env>.json`：按环境覆盖（例如 `production.json`）
- `config.json`：本地覆盖（开发机/部署机差异化；建议不要在仓库中提交真实密钥）
- `~/.virtualchemlab/config.json`：用户运行时目录配置（主要用于桌面打包环境持久化生成的密钥；可通过 `VCL_DATA_DIR`/`VCL_CONFIG_PATH` 改写位置）

## 3. 关键环境变量（按模块）

### 3.1 启动/环境

- `ENVIRONMENT`：`development`/`staging`/`production`
- `DEBUG`：覆盖 `app.debug`
- `LOG_LEVEL`：覆盖日志级别
- `APP_ENV`：环境别名（主要影响日志级别下限判定；生产环境日志不会低于 INFO）

### 3.2 运行时目录与可写路径

- `VCL_DATA_DIR`：指定用户运行时目录根（默认 `~/.virtualchemlab/`）
- `VCL_FORCE_USER_DATA_DIR`：强制将日志/报告/数据重定向到用户目录（即使项目目录可写）
- `VCL_CONFIG_PATH`：指定用户级 `config.json` 的绝对路径
- `TEMPLATES_DIR` / `KNOWLEDGE_DIR` / `USER_DATA_DIR` / `REPORTS_DIR` / `I18N_DIR`：覆盖对应资源目录（用于快速重定向路径）

风险提示：
- 桌面打包（`sys.frozen`）或项目目录不可写时，系统会自动重定向可写目录；维护者改动路径策略时应同时更新 `DEPLOY.md` 与本页。
- Windows 默认运行时目录会优先读取 `APPDATA`/`LOCALAPPDATA`（用于定位用户可写目录）。

### 3.3 安全与密钥（启动前安全闸）

由 `src/core/startup_preflight.py` 统一校验（生产环境为 fail-fast）：

- `JWT_SECRET_KEY`：>=32
- `SESSION_SECRET_KEY`：>=32
- `DEVELOPER_MODE_ENABLED=true` 时还需要开发者密钥（由 `DEVELOPER_SECRET_ENV`/配置决定）

与“密钥变量名可配置”相关：
- `JWT_SECRET_ENV`：允许指定 JWT 密钥所在 env 变量名（默认 `JWT_SECRET_KEY`）
- `SESSION_SECRET_ENV`：允许指定会话密钥所在 env 变量名（默认 `SESSION_SECRET_KEY`）
- `DEVELOPER_SECRET_ENV`：允许指定开发者密钥所在 env 变量名（默认 `DEVELOPER_SECRET_KEY`）
- `DEVELOPER_KEY_HASH`：开发者认证的哈希值（避免明文密钥进入 repo/磁盘）

管理后台（Admin API）：
- `VCL_ADMIN_SECRET_KEY`：启动 Admin API 时必须提供（在 `src/api/admin_api.py` 强校验）
- `ADMIN_SECRET_ENV`：允许指定管理后台密钥所在 env 变量名（默认 `VCL_ADMIN_SECRET_KEY`）

默认管理员种子用户（GUI/核心认证初始化）：
- `VCL_ADMIN_PASSWORD`：若设置则在启动时尝试创建一个默认管理员用户；未设置则跳过（见 `src/core/service_registration.py` 的 `_seed_default_users`）
- `VCL_ADMIN_USERNAME`：默认管理员用户名（默认 `admin`）
- `VCL_ADMIN_EMAIL`：默认管理员邮箱（默认 `<username>@example.com`）

风险提示：
- `VCL_ADMIN_PASSWORD` 属于敏感信息，应仅通过部署环境注入；避免写入 `config.json`/仓库文件/截图日志。
- 该“种子逻辑”只会在用户不存在时创建；不会覆盖已有用户密码（避免意外重置）。

### 3.4 REST API（`src/api/server.py`）

仅在启动 REST API 时需要以下配置（默认仅绑定回环地址，适合本机/内网使用）。

- `VCL_API_HOST`：默认 `127.0.0.1`（仅本机回环）
- `VCL_API_PORT`：默认 `8080`
- `VCL_API_KEYS`：API Key 列表（逗号分隔多把）
- `VCL_API_CORS_ORIGINS`：CORS allowlist（逗号分隔）
- `VCL_ADMIN_CORS_ORIGINS`：Admin API 的 CORS allowlist（逗号分隔；`*` 仅建议用于开发）
- `VCL_HEALTH_DIR`：`/healthz` 写入探针目录（默认 `logs`）
- `VCL_HEALTHZ_REQUIRE_ADMIN_SECRET`：是否要求 Admin 密钥也参与 `/healthz` 成功判定（默认仅报告，不作为失败条件）
- `VCL_READY_CHECK_DB`：`/readyz` 是否探测数据库（默认关闭）
- `DATABASE_URL`：当需要 DB 探测时使用；sqlite 会做文件存在性检查，其它类型默认跳过

风险提示：
- 将 `VCL_API_HOST` 设为 `0.0.0.0` 等同于对外暴露服务，必须同时配置 `VCL_API_KEYS` 并配合防火墙/反向代理/限流。

### 3.5 Redis（可选）

- `REDIS_ENABLED`：是否启用 Redis
- `REDIS_HOST` / `REDIS_PORT`：Redis 连接信息（`/readyz` 会按需探测 TCP 连通性）

### 3.6 监控（可选）

- `MONITORING_ENABLED`：是否启用监控（覆盖 `monitoring.enabled`）

### 3.7 缓存与后台线程（性能/排障开关）

- `CACHE_ENABLED`：启用/禁用缓存
- `VCL_DISABLE_BACKGROUND_THREADS=1`：禁用后台线程（排障用，可能降低功能完整性）
- `VCL_TEST_MODE=1`：测试降级开关（pytest/CI 场景）
- `VCL_EMERGENCY_STATE_DIR`：严重错误时应急状态写入目录（默认 `logs/emergency`）
- `VCL_DISABLE_STARTUP_TIPS=1`：禁用 GUI 启动提示/新手引导（排障或自动化场景；仅影响 UI 层）

### 3.8 许可证/管理后台（可选工具）

以下配置主要用于管理后台与许可证相关工具（例如 `python tools/admin_server_start.py`、`src/main_with_license.py`），不影响主 GUI 的最小启动链路：

- `LICENSE_SECRET_KEY`：许可证签名/校验密钥（建议 >=32；生产环境必须提供）
  - `config/crypto_payment_config.json` 中 `license.secret_key` 可能为 `${LICENSE_SECRET_KEY}` 形式的占位符，启动脚本会据此解析并从环境变量读取

## 4. 文档与实现一致性约定（维护安全）

当你修改以下内容时，必须同步更新文档，否则容易造成“误改”：

- 启动入口/参数：`main.py`、`src/main.py`、`src/api/server.py`
- 配置加载策略：`src/core/config_loader.py`
- 生产环境 fail-fast 条件：`src/core/startup_preflight.py`
- 对外暴露服务默认值（host/port/CORS/auth）

建议每次发布前至少运行：
- `python tools/validate_config.py --env production`（在 CI/部署环境中执行）
