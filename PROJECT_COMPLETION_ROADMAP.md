# VirtualChemLab 项目补全路线图

> **版本**: v2.0.0 → v2.1.0  
> **创建日期**: 2025-11-10  
> **项目状态**: Beta → Production Ready

---

## 📊 项目现状分析

### 当前状态
- **版本**: v2.0.0 (Beta)
- **代码行数**: ~150,000 行 Python 代码
- **测试覆盖率**: 20%
- **文档完整度**: 60%
- **核心功能**: 70% 完成
- **技术债务**: 中等

### 主要问题
1. ❌ **代码质量**: 存在 TODO/FIXME 标记，缺少类型注解
2. ❌ **测试不足**: 测试覆盖率仅 20%，需提升至 80%+
3. ❌ **文档缺失**: API 文档、用户手册不完整
4. ❌ **性能问题**: 启动时间长，内存占用高
5. ❌ **功能缺失**: 部分实验类型、协作功能未实现
6. ❌ **安全隐患**: 输入验证不足，权限控制不完善

---

## 🎯 总体目标

将 VirtualChemLab 从 Beta 版本提升到生产就绪状态，实现：

- ✅ **代码质量**: 90+ 分
- ✅ **测试覆盖率**: 80%+
- ✅ **文档完整度**: 95%+
- ✅ **性能提升**: 启动时间 < 3 秒，内存占用 < 200MB
- ✅ **功能完整**: 100% 核心功能实现
- ✅ **安全加固**: 通过安全审计

---

## 📋 任务清单概览

### 总计: 10 大类任务，73 个子任务

| 类别 | 子任务数 | 优先级 | 预计工时 |
|------|---------|--------|---------|
| 1️⃣ 代码质量与完整性 | 6 | 🔴 高 | 40h |
| 2️⃣ 测试覆盖率提升 | 6 | 🔴 高 | 60h |
| 3️⃣ 文档完善 | 7 | 🟡 中 | 50h |
| 4️⃣ 性能优化 | 8 | 🔴 高 | 45h |
| 5️⃣ 功能完善 | 8 | 🟡 中 | 80h |
| 6️⃣ 用户体验优化 | 7 | 🟡 中 | 35h |
| 7️⃣ 安全性加固 | 7 | 🔴 高 | 40h |
| 8️⃣ 部署与运维 | 7 | 🟡 中 | 45h |
| 9️⃣ 国际化与本地化 | 5 | 🟢 低 | 30h |
| 🔟 发布准备 | 7 | 🔴 高 | 25h |

**总预计工时**: ~450 小时 (约 11-12 周，2 人团队)

---

## 🆕 最新进展 (2025-11-20)

- ✅ 本地以真实显示环境运行 `venv311/bin/python -m pytest`，覆盖 GUI/非 GUI 测试（含 `tests/ui/test_refactored_main_window.py`）；完整输出归档于 `logs/pytest-full.log`，可供 CI 对齐。
- ✅ `tests/unit/test_service_registration.py` 扩展 DI & 事件总线用例，验证服务注册单例/瞬态行为与管理员播种流程，覆盖 roadmap 中“核心模块单元测试”项的 ServiceRegistry 缺口。
- ✅ 修复 Bandit 高危 `hashlib.md5` 诊断，统一改用 `hashlib.sha256`，并记录最新的 `logs/bandit-report.txt` 与 `logs/pip-audit-report.txt` 以支持安全审计。
- ✅ 运行 `venv311/bin/python -m pytest / ruff check / mypy src` 并将完整输出归档到 `logs/pytest-*.log`、`logs/ruff-*.log`、`logs/mypy-*.log`，为后续回归提供统一失败基线。
- ✅ `report_service_impl.py` 补全集成：支持 `ReportType` 过滤、自定义模板加载和模板名透传，并新增 `tests/unit/services/test_report_service_impl.py` 覆盖文件系统模板与过滤逻辑。
- ✅ 核心/服务/UI 第一批关键模块（`core/config_manager.py`、`services/report_service_impl.py`、`ui/ui_config.py`）补充严格类型注解并通过独立 `mypy --follow-imports=skip` 校验，消除返回值 `Any`。
- ✅ 核心模块单测补齐：新增 `tests/unit/core/test_config_manager.py`、`test_error_handler.py`、`test_event_bus.py`，覆盖配置管理、错误处理、事件总线三大低依赖模块。
- ✅ 新建 `reports/perf_baseline.md`，记录当前硬件的 CPU / 内存 / 引导耗时，并同步 `tools/performance_benchmark.py` 在沙箱下的 `sysctl` 权限报错供排障参考。

---

## 🔥 优先级任务 (P0 - 必须完成)

### 1️⃣ 代码质量与完整性 (40h)

**目标**: 修复所有 TODO，提升代码质量到 90+ 分

- [x] **完成 refactored_main_window.py 中的 TODO** (8h ✅ 2025-02-XX)
  - 实现新建、打开、保存实验功能（`RefactoredMainWindow._new/open/save_experiment`）
  - 实现运行、停止实验逻辑（发出 `experiment_started/stopped` 信号并更新状态栏）
  - 实现设置对话框和帮助系统（复用现有 Settings/Help/About 对话框，动态版本号）
  - ➕ 新增 `ExperimentView` 接入与状态持久化挂钩；添加 PySide6 UI 测试确保基础流程稳定
  
- [x] **完成 report_service_impl.py 中的 TODO** (4h)
  - [x] 实现根据 report_type 筛选模板
  - [x] 实现从文件系统加载功能，并在 `tests/unit/services/test_report_service_impl.py` 中覆盖文件系统模板注册/过滤

- [ ] **添加类型注解** (12h)
  - 为所有公共函数添加类型提示
  - 为所有参数添加类型注解
  - 运行 mypy 验证类型正确性
  - ✅ 2025-11-20: `src/core/config_manager.py`、`src/services/report_service_impl.py`、`src/ui/ui_config.py` 已通过独立 mypy 校验

- [ ] **代码风格检查与修复** (8h)
  - 运行 ruff 检查并修复所有问题
  - 运行 black 格式化代码
  - 运行 isort 整理导入
  
- [ ] **清理未使用的代码** (4h)
  - 删除未使用的导入
  - 删除未使用的函数和类
  - 清理注释掉的代码
  
- [ ] **添加缺失的 docstring** (4h)
  - 为所有公共类添加文档字符串
  - 为所有公共函数添加文档字符串
  - 遵循 Google 风格文档规范

---

### 2️⃣ 测试覆盖率提升 (60h)

**目标**: 从 20% 提升到 80%+ 测试覆盖率

- [ ] **核心模块单元测试** (20h)
  - ✅ `src/core/config_manager.py` 测试（`tests/unit/core/test_config_manager.py`）
  - ✅ `src/core/error_handler.py` 测试（`tests/unit/core/test_error_handler.py`）
  - `src/core/experiment_controller.py` 测试
  - ✅ `src/core/event_bus.py` 测试（`tests/unit/core/test_event_bus.py`）
  - ✅ 2025-11-19: `src/core/service_registration.py` (DI/事件总线/管理员播种) 已由 `tests/unit/test_service_registration.py` 覆盖
  - 其他核心模块测试
  - 🔄 服务层延伸：`tests/unit/services/test_report_service_impl.py` 覆盖报告服务模板注册/过滤

- [ ] **UI 组件测试** (15h)
  - `src/ui/main_window.py` 测试
  - `src/ui/experiment_view.py` 测试
  - `src/ui/config_dialog.py` 测试
  - 粒子系统和游戏交互测试
  
- [ ] **集成测试** (10h)
  - 完整实验流程测试
  - 报告生成流程测试
  - 安全检查流程测试
  
- [ ] **性能测试** (8h)
  - 启动时间基准测试
  - 内存占用基准测试
  - 响应速度基准测试
  - ✅ 2025-11-20: 记录 `reports/perf_baseline.md` 手工基线（含 `tools/performance_benchmark.py` 权限失败日志、CPU/内存/引导耗时）
  
- [ ] **端到端测试** (5h)
  - 用户完整操作流程测试
  - 多场景端到端测试
  
- [ ] **测试覆盖率报告** (2h)
  - 生成 HTML 覆盖率报告
  - 识别未覆盖区域
  - 制定补充测试计划

---

### 4️⃣ 性能优化 (45h)

**目标**: 启动时间 < 3 秒，内存占用 < 200MB

- [ ] **集成 Numba 加速** (8h)
  - pH 曲线计算加速
  - 物理模拟计算加速
  - 数据处理加速
  
- [ ] **实现对象池** (6h)
  - 粒子对象池
  - 数据点对象池
  - 减少 GC 压力
  
- [ ] **优化懒加载** (6h)
  - 优化模块导入顺序
  - 实现并行预加载
  - 减少启动时间 50%+
  
- [ ] **粒子系统批量更新** (8h)
  - 实现批量渲染
  - 优化粒子更新算法
  - 提升渲染性能 5-20 倍
  
- [ ] **数据库查询优化** (6h)
  - 添加索引
  - 优化查询语句
  - 实现查询缓存
  
- [ ] **内存优化** (5h)
  - 为热点类添加 `__slots__`
  - 减少内存占用 20-40%
  
- [ ] **缓存策略优化** (4h)
  - 优化 LRU/LFU 算法
  - 提高缓存命中率
  
- [ ] **性能基准测试** (2h)
  - 运行完整性能测试
  - 验证优化效果
  - 生成性能报告

---

### 7️⃣ 安全性加固 (40h)

**目标**: 通过安全审计，修复所有安全漏洞

- [ ] **安全漏洞扫描** (4h)
  - 运行 bandit 安全扫描
  - 运行 safety 依赖检查
  - 识别潜在安全问题
  - ✅ 2025-11-19: 已运行 `venv311/bin/bandit -r src/` 与 `venv311/bin/pip-audit -r requirements.txt`，并修复全部高危 `hashlib.md5` 诊断；输出日志：`logs/bandit-report.txt`、`logs/pip-audit-report.txt`
  
- [ ] **输入验证加固** (8h)
  - 加强所有用户输入验证
  - 防止 SQL 注入
  - 防止 XSS 攻击
  
- [ ] **身份认证完善** (8h)
  - 实现多因素认证 (MFA)
  - 密码强度验证
  - 会话管理优化
  
- [ ] **权限控制系统** (10h)
  - 实现 RBAC (基于角色的访问控制)
  - 细粒度权限管理
  - 权限审计日志
  
- [ ] **数据加密** (6h)
  - 敏感数据加密存储
  - HTTPS 传输加密
  - 密钥管理
  
- [ ] **审计日志** (2h)
  - 记录所有关键操作
  - 日志完整性保护
  
- [ ] **API 安全** (2h)
  - 实现 API 限流
  - 防重放攻击
  - API 密钥管理

---

## 🟡 重要任务 (P1 - 应该完成)

### 3️⃣ 文档完善 (50h)

- [ ] API 参考文档 (10h)
- [ ] 用户手册 (12h)
- [ ] 开发者指南 (10h)
- [ ] 实验模板文档 (6h)
- [ ] 部署文档 (6h)
- [ ] 故障排除指南 (4h)
- [ ] API 示例代码 (2h)

### 5️⃣ 功能完善 (80h)

- [ ] 完善实验类型 (15h) - 气体、有机、分析化学
- [ ] 实验模板系统 (12h) - 可视化编辑器
- [ ] 智能 AI 助手 (15h) - 实验建议、错误诊断
- [ ] 数据分析功能 (10h) - 趋势图表、统计分析
- [ ] 报告生成系统 (10h) - PDF/HTML/Word
- [ ] 协作功能 (10h) - 多用户协作
- [ ] 移动端支持 (6h) - 响应式设计
- [ ] 语音控制 (2h) - 语音命令

### 6️⃣ 用户体验优化 (35h)

- [ ] 界面响应性优化 (8h)
- [ ] 错误提示优化 (6h)
- [ ] 操作流程优化 (6h)
- [ ] 新手引导优化 (6h)
- [ ] 无障碍支持 (4h)
- [ ] 主题系统完善 (3h)
- [ ] 动画效果优化 (2h)

### 8️⃣ 部署与运维 (45h)

- [ ] Docker 容器化 (8h)
- [ ] CI/CD 流程 (10h)
- [ ] 监控告警系统 (8h)
- [ ] 日志聚合分析 (8h)
- [ ] 健康检查端点 (4h)
- [ ] 备份恢复策略 (4h)
- [ ] 性能监控 (3h)

---

## 🟢 可选任务 (P2 - 可以完成)

### 9️⃣ 国际化与本地化 (30h)

- [ ] 中文翻译完善 (8h)
- [ ] 英文翻译完善 (8h)
- [ ] 多语言支持 (8h) - 日/韩/法语
- [ ] i18n 工具完善 (4h)
- [ ] 语言切换优化 (2h)

---

## 🚀 发布准备 (P0 - 必须完成, 25h)

### 🔟 v2.1.0 发布清单

- [ ] **版本号统一** (2h)
  - 统一 pyproject.toml、version_info.txt
  - 统一所有文档中的版本号
  
- [ ] **打包测试** (6h)
  - Windows 打包测试 (exe)
  - macOS 打包测试 (dmg)
  - Linux 打包测试 (deb/rpm)
  
- [ ] **发布说明编写** (3h)
  - 编写 CHANGELOG.md
  - 编写 Release Notes
  - 突出新功能和改进
  
- [ ] **安装程序创建** (6h)
  - 创建 Windows 安装程序
  - 创建 macOS 安装程序
  - 创建 Linux 安装包
  
- [ ] **文档最终审查** (3h)
  - 审查所有文档完整性
  - 检查链接有效性
  - 确保示例代码可运行
  
- [ ] **最终测试** (4h)
  - 全平台功能测试
  - 性能回归测试
  - 安全测试
  
- [ ] **GitHub Release** (1h)
  - 创建 GitHub Release
  - 上传安装包
  - 发布公告

---

## 📅 建议时间线

### 第 1-3 周: 代码质量与测试 (P0)
- Week 1: 代码质量修复 + 核心模块测试
- Week 2: UI 测试 + 集成测试
- Week 3: 性能测试 + 覆盖率报告

### 第 4-6 周: 性能优化与安全 (P0)
- Week 4: Numba 加速 + 对象池 + 懒加载
- Week 5: 粒子系统 + 数据库优化
- Week 6: 安全扫描 + 输入验证 + 认证系统

### 第 7-9 周: 功能与文档 (P1)
- Week 7: 实验类型 + AI 助手
- Week 8: 数据分析 + 报告生成
- Week 9: API 文档 + 用户手册

### 第 10-11 周: 部署与优化 (P1)
- Week 10: Docker + CI/CD + 监控
- Week 11: UX 优化 + 国际化

### 第 12 周: 发布准备 (P0)
- 打包测试 + 文档审查 + 最终测试 + 发布

---

## 📊 成功指标

### 代码质量
- ✅ Ruff 检查通过率: 100%
- ✅ Mypy 类型检查通过率: 95%+
- ✅ 代码重复率: < 5%
- ✅ 代码复杂度: < 10 (平均)

### 测试质量
- ✅ 单元测试覆盖率: 80%+
- ✅ 集成测试覆盖率: 70%+
- ✅ 测试通过率: 100%
- ✅ 测试执行时间: < 5 分钟

### 性能指标
- ✅ 启动时间: < 3 秒
- ✅ 内存占用 (空闲): < 200MB
- ✅ 内存占用 (运行): < 500MB
- ✅ UI 响应时间: < 100ms

### 安全指标
- ✅ 安全漏洞: 0 个高危
- ✅ 依赖漏洞: 0 个高危
- ✅ 代码扫描: 通过
- ✅ 渗透测试: 通过

---

## 🛠️ 工具与资源

### 开发工具
- **代码质量**: ruff, black, isort, mypy
- **测试**: pytest, pytest-cov, pytest-qt
- **性能**: py-spy, memory-profiler, numba
- **安全**: bandit, safety, pip-audit

### 文档工具
- **API 文档**: Sphinx, mkdocs
- **图表**: Mermaid, PlantUML
- **截图**: Snagit, Greenshot

### 部署工具
- **容器化**: Docker, docker-compose
- **CI/CD**: GitHub Actions
- **监控**: Prometheus, Grafana
- **日志**: ELK Stack

---

## 📞 联系与支持

- **项目主页**: https://github.com/tytsxai/virtualchemlab
- **问题反馈**: https://github.com/tytsxai/virtualchemlab/issues
- **邮箱**: team@virtualchemlab.com

---

**最后更新**: 2025-11-10  
**文档版本**: v1.0  
**负责人**: VirtualChemLab Team
