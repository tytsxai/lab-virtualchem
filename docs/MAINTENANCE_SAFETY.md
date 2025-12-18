# 维护安全清单（Maintenance Safety Checklist）

本清单用于 code review 与上线前自检，目标是降低“因理解偏差导致的误改风险”。

## 1. 入口与启动链

- 新增任何入口（GUI/CLI/API/脚本）时，确认不会绕过安全闸：
  - `src/core/startup_preflight.py::ensure_secure_startup`
  - `src/core/config_loader.py` 的配置合并与运行时目录策略
- GUI 入口应保持为“薄转发”：
  - 仓库根 `main.py` → `src.main`

## 2. 配置系统边界（最常见的误用点）

- **启动配置（source of truth）**：`src/core/config_loader.py`
  - `.env`/配置文件/环境变量优先级
  - 生产 fail-fast 条件（密钥长度/存在性）
  - 打包环境 (`sys.frozen`) 的运行时目录与密钥持久化
- **用户运行时设置（UI/偏好）**：`src/core/config_manager.py`
  - 仅用于可变设置（窗口/主题/开关等），不承载生产密钥策略
- 任何涉及环境变量/配置项变更，必须同步更新：
  - `docs/CONFIGURATION_REFERENCE.md`
  - `env.example` / `.env.example`（若该项需要部署者填写；两份文件需保持一致，避免维护者复制错入口导致缺项）

## 3. 安全默认值（不要无意中“放开”）

- REST API 默认只绑定回环：`VCL_API_HOST=127.0.0.1`（见 `src/api/server.py`）
- CORS 默认仅允许本机回环来源；对外跨域必须显式 allowlist：
  - REST：`VCL_API_CORS_ORIGINS`
  - Admin：`VCL_ADMIN_CORS_ORIGINS`
- 禁止引入硬编码默认密钥：
  - API Key 仅来自 `VCL_API_KEYS` 或开发环境自动生成并落盘到运行时目录
  - 生产环境不得自动生成密钥（避免多副本漂移）
- 密钥长度基线保持一致（当前统一为 `>=32`）：
  - `src/core/startup_preflight.py`
  - `src/core/config_loader.py`

## 4. 探针与运维

- `/healthz` 与 `/readyz` 应保持轻量，避免强依赖外部系统导致误报：
  - DB/Redis 探测应为 opt-in（例如 `VCL_READY_CHECK_DB`、`REDIS_ENABLED`）
- 对外发布前至少检查：
  - `make docs-check`
  - `pytest --no-cov tests/unit/test_api_probes.py tests/unit/test_startup_preflight.py`（仓库默认启用覆盖率门禁；仅跑子集时建议加 `--no-cov`）

## 5. 数据目录与备份

- 不要假设安装目录可写；运行时数据目录是第一公民：
  - 默认 `~/.virtualchemlab`，可通过 `VCL_DATA_DIR` / `VCL_CONFIG_PATH` 覆盖
- 修改运行时目录策略或数据落盘路径时，同步检查备份脚本：
  - `scripts/backup_runtime_data.py`
  - `scripts/backup_data.py`
