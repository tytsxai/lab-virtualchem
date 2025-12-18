# 版本与配置基线（B0-T1）

## 版本来源与散落点
| 位置 | 当前值 | 消费点 | 风险与备注 |
| --- | --- | --- | --- |
| `pyproject.toml` → `[project].version` | 2.0.0 | pip 包版本、发布元数据 | 应作为首选写入源；需与代码/打包脚本联动校验。 |
| `src/__init__.py#__version__` | 2.0.0 | 运行时展示、`config_loader` 对齐 `config.app.version`、UI显示 | 与 `pyproject` 需保持同步；若未同步会被 `config_loader` 强制写入运行时版本。 |
| `main.py`/`main_optimized.py` DISPLAY_VERSION | 2.0.0 | 启动日志、Windows AppID | 依赖 `__version__`，随之漂移。 |
| `version_info.txt` | 文件/产品版本 2.0.0.0 | PyInstaller Windows 资源元数据 | 需手动更新；格式为四段版本。 |
| `build_macos.sh`/`build_windows.bat`/脚本 banner | 2.0.0 | DMG/EXE 命名与日志 | 手工维护，容易滞后；未与 `pyproject` 绑定。 |
| `installer_windows.iss` (`MyAppVersion`) | 2.0.0 | Inno Setup 安装器版本与文件名 | 手动同步，未与代码自动联动。 |
| `config/base.json`、`config.json`、`config/production.yaml` | 2.0.0 | 仅作为配置文件内容；`config_loader` 会覆盖为 `__version__` | 配置文件写入版本不再生效，但仍需同步以免误导。 |
| Git 标签（`.github/workflows/release.yml` 触发） | `v*` | Release 产物名 `VirtualChemLab-${APP_VERSION}-{os}.zip/tar.gz` | CI 会校验 tag（`vX.Y.Z`）与 `src.__version__` 一致，否则发布失败；仍需确保 `pyproject` 与代码版本同步。 |

**建议的唯一写入者**：以 `pyproject.toml` 为权威版本号，B1 可补一个校验/同步脚本，将版本写回 `src/__init__.py`、`version_info.txt`、`build_macos.sh`、`build_windows.bat`、`installer_windows.iss`，并在 CI 校验 Git 标签前后一致。

## 配置加载链路（主入口 `src/core/config_loader.py`）
1. 加载 `.env`（若存在，且不覆盖已存在的环境变量）。因此 `.env` 中的 `ENVIRONMENT` **可以**影响后续环境选择。
2. 环境判定：参数 `env` 优先，其次环境变量 `ENVIRONMENT`，否则默认 `development`；在桌面打包环境（`sys.frozen`）默认进入 `production`（并将生成的密钥持久化到用户目录）。
3. 加载配置文件并深度合并：`config/base.json` → 根目录 `config.json`（本地覆盖）→ `config/{env}.json`（环境覆盖）。
4. 环境变量覆盖（优先级最高）：`DEBUG`、`LOG_LEVEL`、`JWT_SECRET_ENV`/`JWT_SECRET_KEY`、`SESSION_SECRET_ENV`/`SESSION_SECRET_KEY`、`DEVELOPER_KEY_HASH`、`DEVELOPER_MODE_ENABLED`、`DATABASE_URL`、`REDIS_ENABLED`/`REDIS_HOST`、`CACHE_ENABLED`、`MONITORING_ENABLED`、路径类 `*_DIR` 等。
5. 版本对齐：`app.version` 被写为 `src.__version__`，避免配置文件中版本漂移误导排障。
6. 运行准备：必要目录创建；在不可写目录/打包环境下将日志/报告/数据重定向到用户目录（例如 `~/.virtualchemlab/`，可通过 `VCL_DATA_DIR` 指定）。
7. 调用方：仓库根入口 `main.py` 转发到 `src.main`，并在启动前执行 `startup_preflight` 的安全校验（生产环境 fail-fast）。

### 其他配置体系（遗留/并行）
- `src/core/config_manager.py`：用户偏好存储在 `~/.virtualchemlab/config.json`，默认版本 `2.0.0`，被 `src/ui/config_dialog.py`、`performance_dialog.py`、`refactored_main_window.py` 使用，未与 `config_loader` 同步。
- `src/core/unified_config_manager.py` + `config/schemas/app_config.py`：统一/迁移尝试，默认读取 `config/config.json`（不存在时用内置默认），主要在示例/测试中使用。
- `config/production.yaml`：仅 `scripts/security_audit.py` 引用，主加载链不读取，易与实际配置漂移。

**配置写入者建议**：将运行时主配置限定为 `config/base.json` + 环境 JSON，并在加载时支持与 `base.json` 合并；逐步收敛 UI 偏好与主配置的版本号来源（至少共享同一版本常量）。

## 敏感配置清单与默认值
- JWT 密钥：`JWT_SECRET_KEY`（或通过 `JWT_SECRET_ENV` / 配置的 `jwt_secret_env` 指向的变量）。无值时开发环境自动生成；生产缺失会报错，但 DI 回退逻辑会写入弱口令（需警惕）。
- 管理后台密钥：`VCL_ADMIN_SECRET_KEY`（可由 `ADMIN_SECRET_ENV`/`developer.admin_secret_env` 指定）；`src/api/admin_api.py` 与生产配置校验依赖此值。
- 默认管理员：`VCL_ADMIN_USERNAME`/`VCL_ADMIN_PASSWORD`/`VCL_ADMIN_EMAIL` 用于种子用户创建（未设密码则跳过）。
- 开发者模式：`DEVELOPER_KEY_HASH`（`tools/setup_dev_key.py` 生成）；`config.json` 里仍包含 `developer.enabled` 和按键序列，默认禁用。
- 会话/教学密钥示例：`SESSION_SECRET_KEY`、`TEACHER_PASSWORD_HASH` 等在 `env.example` 中给出，应在本地 `.env` 或 `secrets.txt` 提供真实值。
- 许可证/支付/通知：`LICENSE_SECRET_KEY`、`WEBHOOK_SECRET`、`SMTP_*`、`TELEGRAM_BOT_TOKEN` 等在 `config/crypto_payment_config.json` 以 `${VAR}` 形式引用，当前值为占位符。
- 其他：`JWT_SECRET_KEY`（默认，可通过 `JWT_SECRET_ENV` / `security.jwt_secret_env` 指向其他变量）、`DATABASE_URL`、`REDIS_HOST/PORT` 等基础设施变量。

## 依赖文件分布与 CI 安装顺序
- 依赖分布：`requirements.txt` / `requirements-dev.txt` / 多个 `requirements-*.txt` 均首行 `-r requirements.lock`，锁文件为唯一完整清单；部分文件再追加可选包（如 `requirements-production.txt` 的 PyInstaller、Redis、RDKit 注释项）。
- CI 流程：
  - `.github/workflows/ci.yml`（Ubuntu）：升级 pip → `pip install -r requirements.txt` → `pip install -r requirements-dev.txt` → pytest（忽略 UI 测试）。
  - `.github/workflows/test.yml`：三平台矩阵，安装同上；Ruff → MyPy（容错）→ 单元/集成/性能测试 → Codecov。
  - `.github/workflows/release.yml`（Ubuntu/Windows/macOS）：安装 `requirements.lock` → `pyinstaller` → 打包（Windows zip / Linux/macOS tar.gz）→ 上传 artifacts → Ubuntu job 发布 Release；并校验 tag 与 `src.__version__` 一致。
  - `.github/workflows/test.yml` `build` 作业：Windows 安装 `requirements.txt` + `pyinstaller`，验证 PyInstaller 产物。
- 本地打包脚本：`build.sh` 自动安装 PyInstaller；`build_macos.sh`/`build_windows.bat` 手动安装特定版本的 PySide6/pymunk/numba/sqlalchemy/PyInstaller，不读取锁文件，存在漂移风险。

## 冲突与风险提示
- 版本号需人工多点更新（脚本、资源、安装器、Git 标签），缺少自动校验，发布易错版。
- 多配置体系（`config_loader` vs `config_manager`/`unified_config_manager`）同时存在，版本号/密钥来源可能不一致，UI 与核心逻辑有机会读取不同值。
- 打包脚本与锁文件脱钩，依赖版本可能与 CI/运行时不一致。

**后续动作建议**（供 B1 参考）：以 `pyproject.toml` 为唯一版本源构建同步脚本；调整 `config_loader` 先加载 `.env` 再决定环境并支持 `base.json` 合并；为生产环境移除弱口令回退；统一 UI 偏好配置的版本来源；让打包脚本使用锁文件或专用冻结清单。
