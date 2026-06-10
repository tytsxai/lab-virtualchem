# VirtualChemLab 文档入口

本目录收录 VirtualChemLab 的开发、配置、API、部署、排障和维护文档。VirtualChemLab 是一个本地桌面优先的游戏化虚拟化学实验室（gamified virtual chemistry lab），主要用于化学教学、实验流程训练和 PySide6 桌面教学工具二次开发。

> 当前事实来源：根目录 [README.md](../README.md)、[QUICK_START.md](../QUICK_START.md)、[README_快速开始.md](../README_快速开始.md)、[INSTALL.md](../INSTALL.md)、本文件和 [DOCS_STATUS.md](DOCS_STATUS.md)。历史总结类文档可能不完全代表当前实现。

## 新用户先读

| 文档 | 用途 |
| --- | --- |
| [README.md](../README.md) | 项目定位、核心功能、技术栈、限制、快速开始 |
| [QUICK_START.md](../QUICK_START.md) | 英文最短启动路径 |
| [README_快速开始.md](../README_快速开始.md) | 中文最短启动路径 |
| [QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md) | 更完整的上手说明 |
| [INSTALL.md](../INSTALL.md) | 安装方式、可选依赖和平台差异 |
| [FAQ.md](FAQ.md) | 常见问题 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 排障路径 |

## 开发者入口

| 文档 | 用途 |
| --- | --- |
| [DEVELOPER_DOCS_INDEX.md](DEVELOPER_DOCS_INDEX.md) | 开发者文档总索引 |
| [DEVELOPER_QUICKSTART.md](DEVELOPER_QUICKSTART.md) | 开发环境快速入口 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构概览 |
| [CODE_STYLE_GUIDE.md](CODE_STYLE_GUIDE.md) | 代码风格和注释规范 |
| [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) | 配置文件与环境变量 |
| [API_REFERENCE.md](API_REFERENCE.md) | 可选 API 参考 |
| [API_USAGE_EXAMPLES.md](API_USAGE_EXAMPLES.md) | API 使用示例 |
| [PLUGINS.md](PLUGINS.md) | 插件系统说明 |
| [EXPERIMENT_COMPILER_GUIDE.md](EXPERIMENT_COMPILER_GUIDE.md) | 实验编译器与模板相关说明 |

## 运维与发布

| 文档 | 用途 |
| --- | --- |
| [OPERATIONS_READINESS.md](OPERATIONS_READINESS.md) | 运维准备与上线检查 |
| [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md) | 生产运行手册 |
| [MONITORING_GUIDE.md](MONITORING_GUIDE.md) | 监控说明 |
| [SECURITY_GUIDE.md](SECURITY_GUIDE.md) | 安全配置与实践 |
| [MAINTENANCE_SAFETY.md](MAINTENANCE_SAFETY.md) | 维护安全检查清单 |
| [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) | 性能优化说明 |
| [../DEPLOY.md](../DEPLOY.md) | 桌面打包、部署和发布说明 |

## 当前真实入口

```bash
git clone https://github.com/tytsxai/lab-virtualchem.git
cd lab-virtualchem

python3.11 -m venv venv311
venv311/bin/python -m pip install -r requirements.lock

cp env.example .env
venv311/bin/python tools/validate_config.py
venv311/bin/python main.py --env development
```

测试与文档检查：

```bash
venv311/bin/python -m pytest -q
make test-fast
make docs-check
```

## 模块定位

- `src/main/`：应用启动，负责配置加载、启动前安全校验、DI 容器和 Qt 应用初始化。
- `src/ui/`：PySide6/Qt6 桌面界面、实验视图、交互控件、欢迎向导和 UI 安全工具。
- `src/core/`：模板引擎、曲线生成、配置、事件、缓存、启动、安全和基础服务。
- `src/models/`：实验、用户记录、知识库和验证模型。
- `src/knowledge/`：试剂、器材、安全知识、危险检查和 PubChem 集成。
- `src/plugins/`：化学结构渲染、图表、PDF 导出和高级计算等可选插件。
- `src/api/`：可选 REST/Admin API，默认不作为公网服务暴露。
- `assets/templates/`：实验模板 YAML。
- `assets/knowledge/`：实验知识 JSON。
- `tools/`：开发者面板、配置校验、文档链接检查、健康检查和维护工具。

## 文档维护约定

- 修改安装、运行、测试或配置入口时，同步更新根目录 README、快速开始或安装文档中的命令。
- 修改 API、配置、插件、模板格式或部署行为时，同步更新对应文档。
- 新增或移动文档后运行：

```bash
make docs-check
```

- 全量 Markdown 链接扫描可使用：

```bash
python tools/check_docs_links.py --all
```
