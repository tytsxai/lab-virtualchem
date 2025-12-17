# 快速开始（简版）

为了方便中文用户快速上手，这份文件概述了最重要的准备步骤，详细内容请参考 `README.md` 和 `QUICK_START_GUIDE.md`。

## 环境要求

- Python 3.11（推荐使用独立虚拟环境）
- `requirements.lock`（或在刷新依赖时使用 `requirements.txt`）
- Git 与终端环境（可运行 `python3.11`）

## 设置步骤

1. **创建虚拟环境并安装依赖**
   ```bash
   python3.11 -m venv venv311
   venv311/bin/python -m pip install -r requirements.lock
   # 若需更新依赖，可切换为 requirements.txt
   ```

2. **初始化配置并验证目录**
   ```bash
   cp env.example .env
   venv311/bin/python config/schemas/app_config.py
   ```
   上述脚本会检查关键路径并自动创建缺失目录。

3. **运行应用**
   ```bash
   venv311/bin/python main.py --env development
   ```

4. **执行测试**
   ```bash
   venv311/bin/python -m pytest -q
   ```
   如在无显示环境（CI/纯终端）运行测试遇到 Qt 崩溃，可改用：
   `QT_QPA_PLATFORM=offscreen venv311/bin/python -m pytest -q`（或直接执行 `make test-fast`）。

## 后续阅读

- `QUICK_START_GUIDE.md`：完整引导与配图说明。
- `QUICK_START_COMPLETION.md`：上线前检查清单。
- `INSTALL.md`：安装细节、插件选择与常见问题。

完成以上步骤后即可按照正式文档继续配置与部署。
