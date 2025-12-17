# 文档维护状态（Source of Truth）

本仓库包含大量 Markdown 文档，其中一部分是“当前事实来源”（会随代码更新），另一部分属于“历史材料/设计文档/计划稿”（可能不再与当前实现一致）。

本页用于明确边界，减少新同学被过期信息误导的概率。

## ✅ 当前维护（推荐优先阅读）

### 根目录（入口）

- `README.md`：项目概览与主要入口
- `QUICK_START.md` / `README_快速开始.md`：最短可重复启动路径
- `QUICK_START_GUIDE.md`：更详细的上手说明
- `QUICK_START_COMPLETION.md`：上手后复查清单（偏“上线/交付”）
- `INSTALL.md`：安装与可选依赖说明
- `DEPLOY.md`：部署/打包/发布说明
- `CONTRIBUTING.md`：贡献指南
- `项目文档索引.md`：根目录索引

### docs/（开发者入口）

- `docs/README.md`：docs 目录总览
- `docs/DEVELOPER_DOCS_INDEX.md`：开发者文档索引（仅链接已存在文件）
- `docs/ARCHITECTURE.md`：架构概览
- `docs/CODE_STYLE_GUIDE.md`：代码风格与注释规范
- `docs/TROUBLESHOOTING.md`、`docs/FAQ.md`：排障与常见问题

## 🧪 文档健康检查

入口文档的本地链接检查：

```bash
make docs-check
```

全量扫描（会暴露更多“历史/计划”文档的缺失引用，通常需要逐步清理）：

```bash
python3 tools/check_docs_links.py --all
```

## 🗃️ 历史材料

- `archive/`：旧版指南与历史报告，不保证与当前实现一致（详见 `archive/README.md`）。

## 📌 维护约定（建议）

- 如果你改了安装/运行/测试/构建入口，请同步更新 `README.md`/`QUICK_START.md`/`INSTALL.md`/`DEPLOY.md` 中至少一处“可执行命令”。
- 如果你新增/移动文档，请同步更新 `项目文档索引.md` 与 `docs/DEVELOPER_DOCS_INDEX.md`，并跑 `make docs-check`。

