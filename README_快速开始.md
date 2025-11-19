# 快速开始（简版）

为了方便中文用户快速上手，这份文件概述了最重要的准备步骤，详细内容请参考 `README.md` 和 `QUICK_START_GUIDE.md`。

1. **创建虚拟环境**
   ```bash
   python3.11 -m venv venv311
   venv311/bin/python -m pip install -r requirements.txt
   ```

2. **初始化配置**
   - 复制 `env.example` 为 `.env`，根据环境修改必要变量。
   - 运行 `python config/schemas/app_config.py` 验证路径和生成缺失目录。

3. **运行应用**
   ```bash
   venv311/bin/python main.py --env development
   ```

4. **执行测试**
   ```bash
   venv311/bin/python -m pytest -q
   ```

5. **更多资源**
   - `QUICK_START_COMPLETION.md`：上线前的检查清单。
   - `INSTALL.md`：安装细节与常见问题。

完成以上步骤后即可按照正式文档继续配置与部署。
