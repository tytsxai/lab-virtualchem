# 开发者快速入门（维护安全版）

> 目标：让新维护者在 10 分钟内完成“可运行、可调试、可验证”的最短路径。
> 本文档只覆盖“当前实现已存在且可复现”的步骤；扩展功能与规划性材料请参考 `docs/DOCS_STATUS.md`。

## 1. 最短启动路径（GUI）

1. 创建并激活虚拟环境（示例：Python 3.11）：

```bash
python3.11 -m venv venv311
source venv311/bin/activate
```

2. 安装依赖（以锁定文件为准）：

```bash
pip install -r requirements.lock
```

3. 初始化环境变量与配置（生成 `.env`）：

```bash
cp env.example .env
python3 tools/validate_config.py
```

4. 启动应用：

```bash
python3 main.py --env development
```

如需更详细的上手说明，请直接阅读根目录入口文档：
- `README.md`
- `README_快速开始.md`
- `QUICK_START_GUIDE.md`

## 2. 开发者面板（推荐）

开发者面板用于集中启动核心工具、测试和诊断程序：

```bash
python3 tools/developer_panel.py
```

文档：`docs/DEVELOPER_PANEL.md`

## 3. REST / Admin API（集成调试用）

权威接口说明：`docs/API.md`（与 `src/api/server.py` / `src/api/admin_api.py` 对齐）。

启动 REST API：

```bash
python3 -m src.api.server
```

> 注意：大多数端点需要 API Key；本机开发首次启动可能会自动生成并写入 `~/.virtualchemlab/`（详见 `docs/API.md`）。

## 4. 最小验证（测试）

```bash
pytest -q
```

无显示环境（CI/纯终端）如遇 Qt 相关问题，可参考 `README.md` 的 `QT_QPA_PLATFORM=offscreen` 提示。

