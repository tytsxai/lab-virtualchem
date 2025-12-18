# VirtualChemLab 生产运行手册（最小版）

本手册用于“马上上线 + 长期稳定运行”的最低操作闭环：安全基线、配置、探针、备份与回滚。

## 1. 生产启动前必备环境变量

**桌面打包应用（单机）推荐做法**
- 不要求用户手工设置 `JWT_SECRET_KEY` / `SESSION_SECRET_KEY`：打包环境下程序会在首次启动时为本机自动生成并持久化到用户数据目录（默认 `~/.virtualchemlab/config.json`，或 `VCL_DATA_DIR` / `VCL_CONFIG_PATH` 指定的路径）。
- 如需企业环境统一管控密钥，仍可通过环境变量显式覆盖。
- 注意：`config.json` 会包含密钥类配置（用于本机运行），请将其视为敏感文件，建议依赖操作系统的用户目录权限保护，并将 `VCL_DATA_DIR` 纳入 Time Machine / 文件历史记录等系统备份策略。

**严格生产（源码运行/容器/多副本）提醒**
- 当 `ENVIRONMENT=production` 且非打包环境时，启动会对 `JWT_SECRET_KEY` / `SESSION_SECRET_KEY` 做 fail-fast 校验（缺失或长度不足会直接退出），避免密钥漂移。
- 如需对外暴露 REST/Admin API，请同时配置鉴权密钥与网络访问控制（防火墙/反向代理/TLS）。

**按需设置**
- `VCL_DATA_DIR`：运行时可写数据目录（默认 `~/.virtualchemlab`）
- `LOG_LEVEL`：日志级别（生产环境最低会被强制为 `INFO`）
- `VCL_API_KEYS`：API 访问密钥（逗号分隔多把；启动 REST API 时必需）
- `VCL_API_CORS_ORIGINS`：允许的 CORS Origin（逗号分隔；默认只允许本地回环）
- `VCL_ADMIN_SECRET_KEY`：管理后台密钥（>=32，仅启动 AdminAPI 时必需）
- `DEVELOPER_MODE_ENABLED=true`：启用开发者模式（生产不建议）
- `DEVELOPER_SECRET_KEY`（>=32）：生产启用开发者模式时必需

## 2. 运行时数据目录（强烈建议）

生产环境建议显式设置：

```bash
export VCL_DATA_DIR="$HOME/.virtualchemlab"
```

理由：打包后的应用安装目录通常不可写（Windows Program Files / macOS .app）。

## 3. 健康检查与就绪检查（探针）

API Server：
- 兼容接口：`GET /api/health`、`GET /api/ready`（面向集成/调用方）
- 部署探针：`GET /healthz`、`GET /readyz`（面向运维探针，含构建信息与可选依赖检查）

建议：
- `health` 用于“进程还活着”
- `ready` 用于“可以接收请求”

## 4. 备份与恢复

### 4.1 备份（推荐每天一次）

```bash
python scripts/backup_runtime_data.py
```

常用参数：
- `--runtime-root <dir>`：指定运行时目录
- `--output-dir <dir>`：备份输出目录
- `--keep N`：保留最近 N 份（默认 7；`-1` 不清理）
- `--dry-run`：查看会打包哪些路径

### 4.2 恢复（回滚数据）

1) 停止应用/服务  
2) 将备份解压到运行时目录（默认 `~/.virtualchemlab`）：

```bash
mkdir -p "$VCL_DATA_DIR"
tar -xzf virtualchemlab_backup_*.tar.gz -C "$VCL_DATA_DIR"
```

3) 启动应用并检查 `GET /api/ready`

## 5. 回滚流程（应用版本）

1) 保留上一版本发布包（Release artifact）  
2) 回滚仅需替换可执行文件/应用目录；运行时数据目录不动（`VCL_DATA_DIR`）  
3) 回滚后检查 `GET /api/health` 和 `GET /api/ready`
