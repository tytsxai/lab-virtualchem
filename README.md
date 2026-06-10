# VirtualChemLab - 游戏化虚拟化学实验室

[![Release](https://img.shields.io/github/v/release/tytsxai/lab-virtualchem)](https://github.com/tytsxai/lab-virtualchem/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[llms.txt](llms.txt) · [Quick Start](QUICK_START.md) · [快速开始](README_快速开始.md) · [Docs](docs/README.md) · [Issues](https://github.com/tytsxai/lab-virtualchem/issues)

VirtualChemLab 是一个开源的本地桌面虚拟化学实验室（open-source gamified virtual chemistry lab）。它面向化学教学、实验演示和流程训练，用 Python + PySide6/Qt6 提供实验模板、步骤引导、物理交互、曲线生成、知识/安全提示、学习记录和可选的本机/内网 API 能力。

它解决的问题：让教师、学生和教学工具开发者可以在不依赖公网服务的情况下，快速搭建可重复运行的化学实验模拟环境，用于课堂演示、课前预习、实验流程练习、实验数据可视化和教学软件二次开发。

> English positioning: VirtualChemLab is a local desktop chemistry education simulator for classroom and lab training. It is not a public SaaS product and not a research-grade computational chemistry engine.

## 项目事实卡 / Project Facts

| 项目项 | 说明 |
| --- | --- |
| 项目类型 | 本地桌面应用；虚拟化学实验室；化学实验模拟器 |
| Target users | chemistry teachers, students, education developers, lab training maintainers |
| 当前代码版本 | `3.0.0`，以 [src/__init__.py](src/__init__.py) 为准 |
| 主入口 | `python main.py --env development`，内部转发到 `src.main` |
| GUI 技术栈 | Python 3.10+ / PySide6 / Qt6 |
| 科学计算 | NumPy, SciPy, matplotlib, pandas |
| 物理与交互 | Pymunk 2D physics adapter, Qt widgets, custom interaction/gamification modules |
| 数据与配置 | YAML experiment templates, JSON config, pydantic/jsonschema validation, SQLite/SQLAlchemy modules |
| 可选能力 | REST/Admin API, plugins, PDF/HTML reports, monitoring, i18n, developer panel |
| 默认部署 | 单机桌面、本机或内网；API 默认不面向公网 |
| License | MIT |

## 核心功能 / Core Features

- 实验模板系统：从 [assets/templates](assets/templates) 加载 YAML 实验模板，覆盖滴定、蒸馏、重结晶、沉淀、酯化、缓冲溶液等教学场景。
- 实验流程训练：按步骤执行、校验输入、记录实验过程、生成分数与反馈，适合训练规范操作和可复现实验流程。
- 虚拟实验交互：PySide6 桌面界面、拖拽/点击交互、粒子和动画反馈、游戏化分数/成就模块。
- 曲线与数据可视化：内置滴定曲线、温度曲线等数据生成逻辑，可配合 matplotlib / pyqtgraph 展示实验数据。
- 化学知识与安全提示：包含试剂、器材、流程和安全知识库，提供基础危险检查与实验安全提醒。
- 插件与报告：支持化学结构渲染、图表、PDF/HTML 报告等可选插件能力。
- 开发与维护工具：包含开发者面板、配置校验、文档链接检查、健康检查、性能与安全相关测试。
- AI 辅助实验编译：仓库包含受控的自然语言实验编译模块，用于把结构化实验描述转换为模板；它不是通用化学推理模型。

## 适合谁使用 / Who It Is For

- 化学教师：用于课堂演示、实验流程讲解、课前预习材料和安全操作训练。
- 学生：用于在本机重复练习实验步骤、观察曲线和理解基础实验现象。
- 教学软件开发者：用于二次开发 PySide6 桌面教学工具、实验模板系统或实验报告功能。
- 实验室/内网维护者：用于在单机或内网环境分发桌面工具，并按需启用本机 API 或管理面板。

## 使用场景 / Use Cases

- 虚拟化学实验室（virtual chemistry lab）和化学实验模拟器（chemistry experiment simulator）。
- 滴定模拟、酸碱中和、缓冲溶液、蒸馏、重结晶、沉淀反应、酯化反应的教学演示。
- 化学课堂游戏化教学、实验安全训练、实验步骤评分、学习记录和报告生成。
- Python / Qt 教育软件、STEM 教学工具、桌面实验模拟器的二次开发样例。

## 不适用场景与限制 / Limitations

- 不是研究级计算化学或量子化学模拟器，不能替代专业分析软件或真实实验数据。
- 不是安全关键系统，不能替代真实实验室安全培训、SDS、PPE 或教师监督。
- 默认是本地桌面应用；REST/Admin API 仅作为可选本机/内网组件，不建议直接暴露到公网。
- GUI 运行需要可用显示环境；CI/纯终端测试建议使用 `QT_QPA_PLATFORM=offscreen` 或 `make test-fast`。
- RDKit、OpenMM、WeasyPrint 等可选依赖在不同系统上的安装方式不同，遇到问题请先看 [INSTALL.md](INSTALL.md)。

## 快速开始 / Quick Start

```bash
git clone https://github.com/tytsxai/lab-virtualchem.git
cd lab-virtualchem

python3.11 -m venv venv311
venv311/bin/python -m pip install -r requirements.lock

cp env.example .env
venv311/bin/python tools/validate_config.py

venv311/bin/python main.py --env development
```

运行测试：

```bash
venv311/bin/python -m pytest -q

# 无显示环境或 CI 可使用：
QT_QPA_PLATFORM=offscreen venv311/bin/python -m pytest -q
# 或：
make test-fast
```

常用开发命令：

```bash
make install
make run
make test-fast
make docs-check
python tools/developer_panel.py
```

## 仓库结构 / Repository Map

```text
lab-virtualchem/
├── main.py                 # 根入口：兼容 python main.py，并统一转发到 src.main
├── src/
│   ├── main/               # 应用启动、配置加载、启动前安全校验、Qt 应用初始化
│   ├── ui/                 # PySide6/Qt6 桌面界面、实验视图、欢迎向导、交互控件
│   ├── core/               # 配置、模板引擎、曲线生成、事件、缓存、启动和安全基础能力
│   ├── models/             # 实验、用户记录、知识库等数据模型
│   ├── knowledge/          # 试剂、危险检查、PubChem 集成等知识模块
│   ├── plugins/            # 可选插件：化学渲染、图表、PDF、热力学/动力学等
│   ├── api/                # 可选 REST/Admin API
│   └── monitoring/         # 健康检查、日志安全、性能监控等
├── assets/
│   ├── templates/          # 实验模板 YAML
│   ├── knowledge/          # 试剂、器材、流程、安全知识 JSON
│   └── i18n/               # 多语言资源
├── docs/                   # 开发、配置、API、部署、排障和维护文档
├── examples/               # 示例实验、API 集成和错误处理示例
├── tests/                  # 单元测试、集成测试、UI 测试、性能/安全相关测试
└── tools/                  # 开发者面板、配置校验、文档链接检查、健康检查等工具
```

## 文档导航 / Documentation

- [QUICK_START.md](QUICK_START.md)：英文最短启动路径。
- [README_快速开始.md](README_快速开始.md)：中文最短启动路径。
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)：更完整的新手引导。
- [INSTALL.md](INSTALL.md)：安装方式、可选依赖和常见安装问题。
- [docs/README.md](docs/README.md)：开发者文档入口。
- [docs/CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md)：配置与环境变量参考。
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md)：可选 API 参考。
- [docs/PLUGINS.md](docs/PLUGINS.md)：插件说明。
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 和 [docs/FAQ.md](docs/FAQ.md)：排障与常见问题。
- [llms.txt](llms.txt)：给 AI 搜索引擎和 LLM 引用的项目摘要。

## 配置与安全默认值 / Configuration Notes

- `ENVIRONMENT` 支持 `development`、`staging`、`production`、`test`。
- `python main.py --env development` 会把 `--env` 映射为 `ENVIRONMENT`，避免 Qt 误读命令行参数；CLI 同时支持 `dev`、`stage`、`prod` 作为常用别名。
- 生产环境必须显式提供足够强度的密钥，例如 `JWT_SECRET_KEY`、`SESSION_SECRET_KEY`。
- `VCL_API_HOST` 默认使用回环地址；如需对外绑定，必须配合认证、CORS、限流和防火墙。
- 详细说明见 [docs/CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md) 与 [DEPLOY.md](DEPLOY.md)。

## 贡献 / Contributing

1. Fork 本仓库。
2. 创建分支：`git checkout -b feature/your-change`。
3. 安装依赖并运行测试：`make install && make test-fast`。
4. 修改代码时同步更新相关文档。
5. 提交 Pull Request。

更多约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## SEO / GEO Keywords

中文关键词：虚拟化学实验室、化学实验模拟器、化学游戏化教学、化学课堂工具、滴定模拟、酸碱中和模拟、晶体生长模拟、电化学实验模拟、实验安全训练、Python 化学教学软件、PySide6 教学桌面应用。

English keywords: virtual chemistry lab, gamified chemistry simulator, chemistry experiment simulator, titration simulator, classroom chemistry app, chemistry education software, STEM teaching tool, PySide6 desktop app, Python chemistry lab simulation, open source chemistry simulator.

建议 GitHub Topics：`virtual-chemistry-lab`, `chemistry-simulator`, `chemistry-education`, `gamified-learning`, `pyside6`, `qt6`, `python`, `stem-education`, `titration-simulator`, `desktop-app`。

## License

MIT License. See [LICENSE](LICENSE).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=tytsxai/lab-virtualchem&type=Date)](https://www.star-history.com/#tytsxai/lab-virtualchem&Date)
