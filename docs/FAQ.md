# FAQ

本页收录一些高频问题与快速解法，避免信息分散在 Issue/聊天记录里。

## 运行与环境

### Q1: 运行 `pytest` 时 Qt 崩溃/找不到显示设备？

在无显示环境（CI/纯终端）下，尝试：

```bash
QT_QPA_PLATFORM=offscreen pytest -q
```

或直接使用：

```bash
make test-fast
```

### Q2: 我应该用 `python` 还是 `python3`？

以你的环境为准。多数系统上推荐明确使用 `python3`。仓库文档中会同时给出示例，例如：

- `python3 main.py --env development`
- `venv311/bin/python main.py --env development`

## 插件与可选依赖

### Q3: RDKit / WeasyPrint / OpenMM 安装失败怎么办？

这些依赖在不同平台上的安装策略差异很大。建议优先参考 `INSTALL.md` 的“按需安装插件”与对应平台建议。

## 其它

更多问题与排障路径：`docs/TROUBLESHOOTING.md`。

