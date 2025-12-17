# VirtualChemLab

一个具有游戏化交互体验的虚拟化学实验室应用程序。

> 📘 想要最短路径？使用 `QUICK_START.md`（English）或 `README_快速开始.md`（中文），并在完成后按照 `QUICK_START_COMPLETION.md` 检查剩余事项。需要更完整的引导可参考 `QUICK_START_GUIDE.md`。

## 快速导航

- [功能特性](#功能特性)
- [最新功能](#最新功能)
- [安装说明](#安装说明)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [开发文档](#开发文档)
- [版本号同步](#版本号同步)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系方式](#联系方式)
- [更新日志](#更新日志)

## 功能特性

### 🧪 实验功能

- **多种实验类型**: 滴定、合成、晶体生长、电化学等
- **实时物理模拟**: 重力、摩擦力、碰撞检测
- **交互式操作**: 拖拽、点击、滑动手势
- **步骤引导**: 详细的实验步骤和验证

### 🎮 游戏化体验

- **物理引擎**: 60 FPS 物理更新
- **粒子效果**: 8种不同类型的粒子效果
- **稀有度系统**: 普通、罕见、稀有、史诗、传说
- **分数系统**: 实时分数和连击计数
- **成就系统**: 实验完成度和经验值

### 🎨 用户界面

- **现代化设计**: 暗色主题和发光效果
- **响应式布局**: 适配不同屏幕尺寸
- **主题切换**: 支持多种主题模式
- **动画效果**: 流畅的过渡和反馈

### ⚙️ 配置管理

- **灵活配置**: 支持多种配置选项
- **导入导出**: 配置文件的备份和恢复
- **实时更新**: 配置更改即时生效
- **错误处理**: 完善的异常管理

## 最新功能

### 🚀 开发者启动面板 (v2.0.0 新增)

统一的图形化开发工具管理界面，整合所有启动脚本：

- ✅ **一键启动** - 运行 `python tools/developer_panel.py`
- ✅ **标签页分类** - 主应用、管理工具、许可证、开发工具、系统工具
- ✅ **实时日志** - 所有输出实时显示，带时间戳
- ✅ **进程管理** - 支持并行运行多个工具，一键停止
- ✅ **功能整合** - 12+ 个启动脚本统一管理
- ✅ **友好界面** - 现代化 GUI，操作简单直观

📖 [查看完整文档](docs/DEVELOPER_PANEL.md)

### 🔧 系统稳定性与性能优化 (v2.0.0 新增)

全面的系统完善和优化，提升项目质量和性能：

- ✅ **内存泄漏修复** - 优化内存管理，防止内存泄漏
- ✅ **线程安全增强** - 统一锁机制，确保线程安全
- ✅ **异常处理完善** - 智能错误恢复和降级处理
- ✅ **缓存性能优化** - O(1) LRU/LFU算法，提升缓存效率
- ✅ **事件总线优化** - 缓存正则表达式，优化事件处理
- ✅ **懒加载改进** - 并行预加载，重试机制
- ✅ **代码质量提升** - 减少重复，统一接口
- ✅ **测试覆盖增强** - 新增150+测试用例

📖 [查看完善报告](完善功能完成报告.md)

### 🎯 用户操作流程优化 (v2.0.0 新增)

- ✅ **统一流程管理器** - 清晰的用户操作流程
- ✅ **智能启动向导** - 首次使用引导体验
- ✅ **统一启动器** - 图形化菜单选择模式
- ✅ **流程检查工具** - 自动化质量保证
- ✅ **完整流程文档** - 详细的操作指南
- ✅ **会话管理** - 自动保存和恢复进度

### 实验模板创建向导

- ✅ 图形化模板编辑器
- ✅ 拖拽式步骤管理
- ✅ 实时预览和验证
- ✅ 一键生成YAML模板

### 实验数据分析器

- ✅ 详细的统计分析
- ✅ 趋势图表可视化
- ✅ 成绩分布分析
- ✅ 错误模式识别

### 智能缓存系统

- ✅ LRU淘汰策略
- ✅ 自动过期管理
- ✅ 性能监控工具
- ✅ 缓存调试器

## 安装说明

### 系统要求

- Python 3.10+（推荐 3.11）
- Windows 10/11, macOS 10.15+, 或 Linux
- 4GB RAM (推荐 8GB)
- 1GB 可用磁盘空间

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/tytsxai/VirtualChemLab.git
   cd VirtualChemLab
   ```

2. **创建并激活 Python 3.11 虚拟环境**

   ```bash
   python3.11 -m venv venv311
   source venv311/bin/activate          # Linux/macOS
   # 或
   venv311\\Scripts\\activate           # Windows
   ```

3. **安装依赖（锁定文件优先）**

   ```bash
   pip install -r requirements.lock
   # 如需刷新依赖，请更新 pyproject.toml 并重新生成锁定文件:
   # pip-compile --extra=dev --extra=docs --extra=redis --extra=performance --extra=admin --extra=ops --extra=plugins --generate-hashes --output-file=requirements.lock pyproject.toml
   ```
   CI/发布流程同样使用 `requirements.lock` 安装，确保依赖可重复。

4. **初始化环境变量和配置**

   ```bash
   cp env.example .env
   python config/schemas/app_config.py
   ```

   上述脚本会验证路径并在缺失时自动创建必要目录。

5. **运行应用与测试**

   ```bash
   python main.py --env development
   pytest -q
   ```

   > 💡 在无显示环境（CI/纯终端）运行测试如遇 Qt 崩溃，可使用：`QT_QPA_PLATFORM=offscreen pytest -q` 或直接执行 `make test-fast`。

6. **可选：开发者启动面板**

   ```bash
   python tools/developer_panel.py
   ```

   用于集中启动核心工具、测试和诊断程序。

> 💡 更多细节和扩展安装指引，请查看 `README_快速开始.md`、`QUICK_START_GUIDE.md`、`INSTALL.md`。

### 开发环境设置

1. **安装开发依赖**

```bash
pip install -r requirements.lock
pip install --no-deps -e .
# requirements-dev.txt 仅作为兼容入口，内部同样引用锁定文件
```

2. **安装预提交钩子**

```bash
pre-commit install
```

3. **运行测试**

```bash
pytest
```

> Note: CI 与默认测试命令会生成覆盖率报告并执行 18% 覆盖率门禁（后续目标逐步提升到 30%，产出 `coverage.xml` 与 `htmlcov/`）。如需快速运行跳过覆盖率，可执行 `pytest --no-cov` 或 `make test-fast`。
> 💡 提示：`tests/ui/test_refactored_main_window.py` 依赖真实的 Qt 图形界面环境。在无显示服务器（例如 CI 或纯终端）中，它会自动跳过。若要完整验证 UI 行为，请在本地具备 GUI 的环境执行 `pytest tests/ui/test_refactored_main_window.py`。

4. **代码格式化**

```bash
ruff format src tests
ruff check src tests --fix
```

### 系统就绪检查与运维准备

- 运行 `python scripts/readiness_check.py`，快速验证依赖、配置、安全与监控是否达标。
- 更多上线、监控、回滚与性能调优细节见 `docs/OPERATIONS_READINESS.md`。

### 环境变量与安全配置

- `VCL_JWT_SECRET`：JWT 密钥，至少 32 个字符，生产环境必须外部提供。
- `VCL_ADMIN_SECRET_KEY`：管理后台/Flask 的 SECRET_KEY，建议与 JWT 密钥不同。
- `ENVIRONMENT`：`development` / `staging` / `production`，控制默认安全策略。

写入 `.env` 或系统环境，例如：

```bash
export VCL_JWT_SECRET="please_change_me_to_a_secure_value"
export VCL_ADMIN_SECRET_KEY="admin_panel_secret"
export ENVIRONMENT="production"
```

生产环境缺少上述密钥会导致程序拒绝启动。

## 使用指南

### 快速开始

**方式1：开发者面板（推荐）✨**

```bash
python tools/developer_panel.py
```

**统一的图形化管理界面**，整合所有启动脚本和工具：

- 🚀 主应用启动（标准、快速、热加载、许可证模式）
- 👨‍💼 管理工具（教师控制台、管理后台、实验管理）
- 🔐 许可证管理（检查、备份、工具箱）
- 🛠️ 开发工具（构建、部署、测试、工具箱）
- 🔧 系统工具（维护、诊断、流程检查）

📖 [查看完整文档](docs/DEVELOPER_PANEL.md)

**方式2：命令行启动**

```bash
# 标准模式（含欢迎向导）
python main.py

# 快速模式（跳过向导）
python main.py --skip-welcome

# 热加载模式（开发调试，代码修改自动重启）
python tools/hot_reload_launcher.py
```

**方式3：许可证验证启动**

```bash
python -m src.main_with_license
```

### 基本操作

1. **启动应用**: 使用上述任一方式启动
2. **首次使用**: 按照欢迎向导完成5步设置
3. **选择实验**: 从实验模板库中选择
4. **进行实验**: 按照步骤指导完成操作
5. **查看结果**: 生成报告并查看得分
6. **游戏模式**: 按 `Ctrl+G` 切换游戏模式
7. **物理控制**:
   - 空格键：震动所有物品
   - G键：切换重力
   - R键：重置所有物品

### 配置设置

1. **打开配置**: 菜单 → 设置 → 配置
2. **调整参数**: 修改物理、UI、游戏等设置
3. **保存配置**: 点击确定保存更改

### 实验操作

1. **拖拽器材**: 鼠标左键拖拽实验器材
2. **点击交互**: 点击试剂瓶等物品
3. **观察效果**: 查看粒子效果和物理模拟
4. **完成步骤**: 按照提示完成实验步骤

## 项目结构

```
VirtualChemLab/
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   │   ├── config_manager.py    # 配置管理
│   │   ├── error_handler.py     # 错误处理
│   │   └── experiment_controller.py  # 实验控制
│   ├── models/            # 数据模型
│   ├── ui/                # 用户界面
│   │   ├── game_interaction.py  # 游戏交互
│   │   ├── particle_system.py   # 粒子系统
│   │   ├── config_dialog.py     # 配置对话框
│   │   └── main_window.py       # 主窗口
│   └── utils/             # 工具函数
├── tests/                 # 测试代码
├── docs/                  # 文档
├── requirements.txt       # 依赖列表
├── requirements-dev.txt   # 开发依赖
├── pyproject.toml        # 项目配置
└── README.md            # 说明文档
```

## 技术栈

- **GUI框架**: PySide6 (Qt6)
- **物理引擎**: 自定义物理模拟
- **粒子系统**: 自定义粒子效果
- **配置管理**: JSON配置文件
- **错误处理**: 统一异常管理
- **测试框架**: pytest（pytest-qt 可选；CI 默认禁用以降低 GUI/平台差异导致的波动）
- **代码质量**: ruff（lint + format）+ mypy（可选门禁）

## 开发文档

### 核心文档

- 📖 [开发者文档索引](docs/DEVELOPER_DOCS_INDEX.md) - 所有文档的导航中心
- 📝 [代码风格规范](docs/CODE_STYLE_GUIDE.md) - 统一的代码和注释规范
- 💻 [API使用示例](docs/API_USAGE_EXAMPLES.md) - 实际代码示例和最佳实践
- 🔧 [故障排除指南](docs/TROUBLESHOOTING.md) - 常见问题和解决方案
- 🎨 [UI组件指南](docs/UI_COMPONENTS_GUIDE.md) - UI组件使用说明

### 快速链接

- [架构设计](docs/ARCHITECTURE.md) - 系统架构说明
- [API参考](docs/API_REFERENCE.md) - 完整API文档
- [性能优化](docs/PERFORMANCE_OPTIMIZATION.md) - 性能优化指南
- [部署指南](DEPLOY.md) - 生产环境部署

## 版本号同步

- 单一来源：`src/__init__.py` 中的 `__version__`
- 同步脚本：`python tools/bump_version.py 2.0.0`，省略版本号则按当前值同步 `pyproject.toml`、`config.json`、`version_info.txt`、`installer_windows.iss`
- 便捷命令：`make bump-version VERSION=2.0.1`
- 打包脚本：`build.sh` / `build_macos.sh` / `build_windows.bat` 读取同一版本号

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 代码规范

- 遵循 [代码风格规范](docs/CODE_STYLE_GUIDE.md)
- 使用 `ruff format` 格式化代码
- 使用 `ruff check` 检查代码质量（必要时 `--fix`）
- 使用 `mypy` 进行类型检查（当前默认非阻塞，可按需启用严格门禁）
- 编写单元测试
- 更新文档

详细信息请参考 [CONTRIBUTING.md](CONTRIBUTING.md)

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: [https://github.com/tytsxai/VirtualChemLab](https://github.com/tytsxai/VirtualChemLab)
- 问题反馈: [Issues](https://github.com/tytsxai/VirtualChemLab/issues)
- 邮箱: <team@virtualchemlab.com>

## 更新日志

### v2.0.0 (2025-10-07) 🎉

- 🎯 **用户操作流程全面优化**
- 🚀 **新增开发者启动面板** - 统一的图形化工具管理界面
  - 整合所有启动脚本和开发工具
  - 实时日志输出和进程管理
  - 标签页式界面，功能分类清晰
  - 支持并行运行多个工具
- ✨ 新增统一流程管理器
- ✨ 新增智能启动向导
- ✨ 新增统一启动器
- ✨ 新增流程检查工具
- ✨ 完善会话管理和状态恢复
- 📚 新增完整的流程文档
- 🐛 修复多项用户体验问题

### v1.0.0 (2024-01-01)

- 🎉 首次发布
- ✨ 游戏化交互系统
- ✨ 物理模拟引擎
- ✨ 粒子效果系统
- ✨ 配置管理系统
- ✨ 错误处理系统
- ✨ 单元测试框架

## 致谢

感谢所有贡献者和开源社区的支持！

---

**VirtualChemLab** - 让化学实验变得更有趣！ 🧪✨
