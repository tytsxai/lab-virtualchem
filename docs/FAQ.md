# FAQ

本页收录一些高频问题与快速解法，避免信息分散在 Issue/聊天记录里。

## 项目定位

### Q1: VirtualChemLab 是什么？

VirtualChemLab 是一个开源、本地桌面优先的游戏化虚拟化学实验室（open-source gamified virtual chemistry lab）。它用 Python + PySide6/Qt6 提供实验模板、步骤引导、基础数据曲线、物理交互、知识/安全提示、学习记录和可选报告/API 能力，主要服务化学教学、实验演示和流程训练。

### Q2: 这个项目适合谁？

适合化学教师、学生、STEM 教学工具开发者，以及需要在单机或内网环境运行实验教学软件的维护者。典型场景包括课堂演示、课前预习、滴定/蒸馏/重结晶等实验流程练习、实验安全训练和 PySide6 教学软件二次开发。

### Q3: 它能替代真实实验或专业计算化学软件吗？

不能。VirtualChemLab 是教学型模拟器，不是研究级计算化学、量子化学或分析化学引擎，也不能替代真实实验室安全培训、SDS、PPE 或教师监督。

### Q4: 它是 Web/SaaS 产品吗？

不是默认的公共 SaaS。当前主路径是本地桌面应用；REST/Admin API 是可选组件，默认更适合本机或内网使用。如果要对外开放，需要额外处理认证、CORS、限流、防火墙和日志审计。

## 运行与环境

### Q5: 如何先确认核心链路能跑，不启动 GUI？

可以运行非 GUI 自检：

```bash
python main.py --test-core
```

该命令会验证配置加载、依赖注入、当前可加载实验模板列表和滴定曲线生成，适合 CI、纯终端或首次安装后的快速排查。如果输出里出现历史/实验性模板的 schema 校验错误，应以最后列出的可用实验列表为准。

### Q6: 运行 `pytest` 时 Qt 崩溃/找不到显示设备？

在无显示环境（CI/纯终端）下，尝试：

```bash
QT_QPA_PLATFORM=offscreen pytest -q
```

或直接使用：

```bash
make test-fast
```

### Q7: 我应该用 `python` 还是 `python3`？

以你的环境为准。多数系统上推荐明确使用 `python3`。仓库文档中会同时给出示例，例如：

- `python3 main.py --env development`
- `venv311/bin/python main.py --env development`

## 插件与可选依赖

### Q8: RDKit / WeasyPrint / OpenMM 安装失败怎么办？

这些依赖在不同平台上的安装策略差异很大。建议优先参考 `INSTALL.md` 的“按需安装插件”与对应平台建议。

### Q9: 实验模板在哪里？

教学实验模板位于 `assets/templates/`。当前核心自检可加载的模板包括滴定、简单蒸馏、缓冲溶液和 AgCl 沉淀等；目录中也保留了部分历史/实验性模板，例如交互式、重结晶、酯化相关模板，这些文件需要按当前 Pydantic schema 对齐后再视为正式可用。

## 其它

更多问题与排障路径：`docs/TROUBLESHOOTING.md`。
