# VirtualChemLab Architecture (Source of Truth)

本页描述 **当前实现** 的系统架构与关键设计决策，目标是让不熟悉背景的维护者也能安全修改代码：

- 你应该从哪里入手理解系统
- 哪些模块是“关键链路/易误改点”
- 配置、密钥、可写目录与权限相关逻辑的边界与风险

如果本页与其他文档冲突，请以本页 + 代码实现为准，并优先修正文档漂移（参见 `docs/DOCS_STATUS.md`）。

## 1. 系统边界与运行形态

VirtualChemLab 主要以 **桌面 GUI（Qt/PySide6）** 形态运行，同时提供可选的 **REST API 服务** 与 **管理后台** 工具。

核心组成：

- GUI 应用：`python main.py`（推荐入口）
- REST API：`python -m src.api.server`（默认仅回环）
- 管理后台：`python tools/admin_server_start.py`（单独启动，独立密钥要求）

## 2. 入口与启动链路（关键业务流程）

### 2.1 GUI 启动链路（推荐入口）

```
main.py (repo root)
  └─ bootstrap sys.path / parse --env
  └─ src.main.main()
       ├─ get_config()  -> Config.load()
       ├─ ensure_secure_startup(config)   # 生产环境 fail-fast
       ├─ configure_container(config)     # DI 容器注册
       ├─ DPI / Qt attributes
       └─ MainWindow(container).show()
```

关键点（易误改）：

- `main.py` 必须保持“薄转发”，避免出现多个入口绕过安全闸/配置加载而产生行为漂移。
- `--env` 仅用于兼容命令行；真实环境选择以 `ENVIRONMENT` 为准（入口会做映射并移除参数，避免 Qt 误解析）。
- 启动前安全闸：`src/core/startup_preflight.py`。生产环境弱密钥会直接退出（fail-fast）。

### 2.2 REST API 启动链路

入口：`src/api/server.py`（`__main__`）

默认行为：
- 仅监听 `127.0.0.1`（通过 `VCL_API_HOST` 修改）
- 默认端口 `8080`（通过 `VCL_API_PORT` 修改）
- 默认启用认证与限流；认证使用 `VCL_API_KEYS`

风险提示：
- 将 `VCL_API_HOST=0.0.0.0` 等价于对外暴露服务，必须同时配置 `VCL_API_KEYS` 并做好网络隔离/反向代理/防火墙。

### 2.3 管理后台启动链路

入口：`tools/admin_server_start.py`

关键点：
- 管理后台密钥 `VCL_ADMIN_SECRET_KEY` 在 Admin API 层强校验（不是在全局配置加载阶段强制），避免阻断主 GUI 启动。

## 3. 配置系统（配置项/环境变量/风险）

主配置加载实现：`src/core/config_loader.py`

配置优先级（从低到高）：
1. `config/base.json`
2. `config.json`（仓库根目录，本地覆盖/兼容）
3. `config/<environment>.json`
4. 环境变量（最高优先级；`.env` 只是“批量注入 env”的载体）

桌面打包/不可写目录：
- 当检测到打包环境（`sys.frozen`）或项目目录不可写时，会将日志/报告/用户数据等重定向到用户运行时目录（默认 `~/.virtualchemlab/`），避免因为不可写导致运行不稳定。

建议阅读：
- `docs/CONFIGURATION_REFERENCE.md`：配置与环境变量的“事实来源”
- `python tools/validate_config.py`：按当前实现校验并输出关键结论

## 4. 分层与模块地图

建议以“入口 -> 配置 -> DI -> UI/业务 -> 存储/外部接口”的路径理解代码。

### 4.1 `src/core/`（核心与基础设施）

职责：
- 配置加载与运行准备：`config_loader.py`
- 启动前安全闸：`startup_preflight.py`
- 依赖注入容器：`di_container.py` + `service_registration.py`
- 实验核心逻辑：`experiment_controller.py`、`template_engine.py`、`curve_generator.py`
- 安全与开发者认证：`dev_auth.py` 等

维护安全关注：
- 密钥与严格模式：production 的 fail-fast 条件不要被“开发便利”稀释。
- 运行时目录重定向：任何改动都要考虑打包环境与不可写目录。

### 4.2 `src/ui/`（Qt GUI）

职责：
- 主窗口与交互入口：`main_window.py`
- 交互式实验/集成：`interactive_experiment_controller.py`、`integration_manager.py`
- 设置/配置 UI：`config_dialog.py`、`settings_dialog.py`
- 错误展示与恢复：`error_dialog.py`、`error_recovery_wizard.py`

维护安全关注：
- Qt 会解析 `sys.argv`；启动参数需要在入口处剥离（例如 `--env`）。
- 无显示环境（CI/纯终端）下 UI 测试可能需要跳过或使用 `QT_QPA_PLATFORM=offscreen`。

### 4.3 `src/api/`（REST/Admin API）

职责：
- API server：`server.py`
- 认证/中间件：`middleware.py`
- Admin API：`admin_api.py`
- 客户端：`client.py`

维护安全关注：
- 默认“仅本机回环”是安全基线；任何默认值改变都应被视为安全变更并同步更新文档。

### 4.4 资产与数据目录

- `assets/`：模板、知识库、i18n 等静态资产
- `data/`、`user_data/`、`reports/`、`logs/`：运行时数据（可能被重定向到用户目录）

### 4.5 其它 `src/*` 包（功能模块 / 可选依赖）

仓库中还包含较多“功能模块/集成模块/实验性目录”（例如 `src/ai/`、`src/voice/`、`src/monitoring/`、`src/plugins/`、`src/integration/` 等）。

维护安全提示：
- 这些目录中不少能力依赖**可选第三方库**（缺失时会降级或禁用），因此不要在核心启动链路中无条件引入。
- 判断某个模块是否属于“启动关键路径”，优先以入口链路与 `src/core/` 的 service 注册为准，而不是以目录名称推断。

## 5. 关键业务对象与数据流（简化）

### 5.1 实验模板 -> 运行时实验

```
assets/templates/*   -> TemplateEngine -> ExperimentController -> UI 展示/交互 -> 记录/报告
```

维护安全关注：
- 模板格式/字段更改属于“高耦合变更”，需要同步更新模板校验、UI 显示与文档。

### 5.2 配置与密钥

```
.env/env vars -> Config.load() -> startup_preflight -> DI services -> UI/API
```

维护安全关注：
- 生产环境密钥缺失必须 fail-fast；开发环境允许降级但要显式日志提醒，避免“以为安全实际不安全”。

## 6. 维护安全约定（防误改清单）

当你修改以下文件/逻辑时，建议视为“需要同步更新文档 + 增加验证”的变更：

- 入口：`main.py`、`src/main.py`
- 配置加载：`src/core/config_loader.py`
- 生产安全闸：`src/core/startup_preflight.py`
- API 默认监听/认证：`src/api/server.py`、`src/api/middleware.py`

最小验证：
- `python tools/validate_config.py`
- `python -m pytest -q`（无 GUI 环境可用 `QT_QPA_PLATFORM=offscreen`）
