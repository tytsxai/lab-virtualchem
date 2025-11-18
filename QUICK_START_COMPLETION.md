# VirtualChemLab 项目补全快速开始指南

> **快速上手**: 从当前状态到生产就绪的最短路径

---

## 🚀 立即开始 (第一周)

### Day 1-2: 环境准备与代码质量

```bash
# 1. 安装开发依赖
pip install -r requirements-dev.txt

# 2. 运行代码质量检查
ruff check src/ tests/
mypy src/

# 3. 查看待修复问题
grep -r "TODO\|FIXME" src/ --include="*.py"

# 4. 开始修复 refactored_main_window.py
# 文件位置: src/ui/refactored_main_window.py
# 需要实现的方法:
# - new_experiment()
# - open_experiment()
# - save_experiment()
# - run_experiment()
# - stop_experiment()
# - show_settings()
# - show_help()
# - show_about()
```

### Day 3-4: 添加类型注解

```bash
# 1. 找出缺少类型注解的函数
python tools/code_quality_enhancer.py

# 2. 批量添加类型注解
# 优先处理核心模块:
# - src/core/config_manager.py
# - src/core/error_handler.py
# - src/core/experiment_controller.py

# 3. 验证类型注解
mypy src/core/
```

### Day 5-7: 编写核心测试

```bash
# 1. 创建测试文件
mkdir -p tests/unit/core
touch tests/unit/core/test_config_manager.py
touch tests/unit/core/test_error_handler.py
touch tests/unit/core/test_experiment_controller.py

# 2. 运行测试
pytest tests/unit/core/ -v

# 3. 查看覆盖率
pytest --cov=src/core --cov-report=html
open htmlcov/index.html
```

---

## 📝 关键文件清单

### 需要立即修复的文件

1. **src/ui/refactored_main_window.py** (8 个 TODO)
   ```python
   # TODO: 实现新建实验逻辑
   # TODO: 实现打开实验逻辑
   # TODO: 实现保存实验逻辑
   # TODO: 实现运行实验逻辑
   # TODO: 实现停止实验逻辑
   # TODO: 实现设置对话框
   # TODO: 实现帮助系统
   # TODO: 实现关于对话框
   ```

2. **src/services/report_service_impl.py** (2 个 TODO)
   ```python
   # TODO: 根据report_type筛选模板
   # TODO: 从文件系统加载（如果启用了持久化）
   ```

### 需要添加测试的核心模块

```
tests/unit/core/
├── test_config_manager.py          ⚠️ 需要创建
├── test_error_handler.py           ✅ 已存在
├── test_experiment_controller.py   ⚠️ 需要创建
├── test_event_bus.py               ⚠️ 需要创建
├── test_cache_manager.py           ✅ 已存在
└── test_database_manager.py        ⚠️ 需要创建

tests/ui/
├── test_main_window.py             ✅ 已存在
├── test_experiment_view.py         ⚠️ 需要创建
├── test_config_dialog.py           ⚠️ 需要创建
├── test_particle_system.py         ⚠️ 需要创建
└── test_game_interaction.py        ✅ 已存在

tests/integration/
├── test_experiment_flow.py         ✅ 已存在
├── test_report_generation.py       ✅ 已存在
└── test_safety_checks.py           ✅ 已存在
```

---

## 🎯 优先级任务速查

### P0 - 本周必须完成

- [ ] 修复 `refactored_main_window.py` 的 8 个 TODO
- [ ] 修复 `report_service_impl.py` 的 2 个 TODO
- [ ] 为核心模块添加类型注解
- [ ] 运行 ruff/black/isort 修复代码风格
- [ ] 编写核心模块单元测试

### P1 - 下周应该完成

- [ ] UI 组件测试
- [ ] 集成测试补充
- [ ] 性能基准测试
- [ ] 测试覆盖率达到 60%+

### P2 - 两周内完成

- [ ] Numba 加速集成
- [ ] 对象池实现
- [ ] 懒加载优化
- [ ] 测试覆盖率达到 80%+

---

## 🛠️ 常用命令

### 代码质量检查

```bash
# 运行所有检查
make lint

# 自动修复
make lint-fix

# 格式化代码
make format

# 类型检查
make type-check
```

### 测试

```bash
# 运行所有测试
make test

# 快速测试（无覆盖率）
make test-fast

# 运行特定测试
pytest tests/unit/core/test_config_manager.py -v

# 查看覆盖率
pytest --cov=src --cov-report=term-missing
```

### 性能分析

```bash
# 运行性能基准测试
python tools/performance_benchmark.py

# 性能分析
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats

# 内存分析
python -m memory_profiler main.py
```

---

## 📊 进度跟踪

### 每日检查清单

**每天结束前运行:**

```bash
# 1. 代码质量检查
ruff check src/ tests/

# 2. 类型检查
mypy src/

# 3. 运行测试
pytest

# 4. 查看覆盖率
pytest --cov=src --cov-report=term

# 5. 提交代码
git add .
git commit -m "feat: 完成XXX功能"
git push
```

### 每周检查清单

**每周五运行:**

```bash
# 1. 完整测试套件
pytest --cov=src --cov-report=html

# 2. 性能基准测试
python tools/performance_benchmark.py

# 3. 安全扫描
bandit -r src/
safety check

# 4. 生成报告
python tools/system_health_check.py

# 5. 更新文档
# 更新 CHANGELOG.md
# 更新进度报告
```

---

## 🎓 学习资源

### 项目文档

- **代码规范**: `docs/CODE_STYLE_GUIDE.md`
- **架构设计**: `docs/ARCHITECTURE.md`
- **API 文档**: `docs/API_REFERENCE.md`
- **开发者指南**: `docs/DEVELOPER.md`

### 工具文档

- **开发者面板**: `docs/DEVELOPER_PANEL.md`
- **性能优化**: `src/performance/optimization_guide.md`
- **插件系统**: `src/plugins/README.md`

### 示例代码

```bash
# 查看示例
ls examples/

# 运行示例
python examples/plugin_demo.py
python examples/performance_demo.py
python examples/error_handling_examples.py
```

---

## 🐛 常见问题

### Q1: 如何运行开发者面板?

```bash
python tools/developer_panel.py
```

### Q2: 如何快速启动应用?

```bash
# 标准模式
python main.py

# 跳过欢迎向导
python main.py --skip-welcome

# 热加载模式（开发）
python tools/hot_reload_launcher.py
```

### Q3: 如何运行特定测试?

```bash
# 运行单个测试文件
pytest tests/unit/test_config_manager.py

# 运行特定测试函数
pytest tests/unit/test_config_manager.py::test_load_config

# 运行带标记的测试
pytest -m unit
pytest -m integration
```

### Q4: 如何查看测试覆盖率?

```bash
# 生成 HTML 报告
pytest --cov=src --cov-report=html

# 在浏览器中打开
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Q5: 如何修复代码风格问题?

```bash
# 自动修复
ruff check src/ --fix
black src/ tests/
isort src/ tests/

# 或使用 make
make format
```

---

## 📞 获取帮助

### 项目资源

- **GitHub Issues**: https://github.com/virtualchemlab/virtualchemlab/issues
- **文档**: `docs/` 目录
- **示例**: `examples/` 目录

### 开发工具

- **开发者面板**: `python tools/developer_panel.py`
- **系统健康检查**: `python tools/system_health_check.py`
- **性能基准测试**: `python tools/performance_benchmark.py`

### 联系方式

- **邮箱**: team@virtualchemlab.com
- **项目主页**: https://github.com/virtualchemlab/virtualchemlab

---

## 🎉 下一步

1. ✅ 阅读本文档
2. ⏭️ 运行 `python tools/developer_panel.py` 熟悉工具
3. ⏭️ 开始修复 `refactored_main_window.py` 的 TODO
4. ⏭️ 编写第一个单元测试
5. ⏭️ 查看 `PROJECT_COMPLETION_ROADMAP.md` 了解完整计划

**祝开发顺利！** 🚀

---

**最后更新**: 2025-11-10  
**文档版本**: v1.0  
**负责人**: VirtualChemLab Team

