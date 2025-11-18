# 运维与上线就绪指南

本指南帮助你在发布 VirtualChemLab 之前完成必要的验证、监控和运维准备，确保核心功能稳定、性能与安全达标，并具备可观测性。

---

## 1. 快速健康检查

1. 激活项目环境（如 `source venv/bin/activate`）。
2. 运行就绪度脚本：

```bash
python scripts/readiness_check.py
```

该脚本会检查：

- Python 版本与关键依赖是否齐备
- `config.json` 与环境变量中的安全配置（JWT 密钥、开发者模式）
- 必要的资源目录（assets/templates、knowledge、logs、reports、data 等）
- 监控与日志配置状态

所有检查通过后才能进入下一阶段。

---

## 2. 测试与验证

| 类型 | 命令 | 说明 |
| --- | --- | --- |
| 单元测试 | `python -m pytest tests/unit` | 覆盖配置加载、缓存、错误处理等核心模块。 |
| 集成测试 | `python -m pytest tests --maxfail=1` | 全量运行，确保模块间交互稳定。 |
| 性能回归 | `python tests/comprehensive_performance_test.py` | 验证缓存、事件总线、数据库等性能指标是否达标。 |
| 关键场景手动验证 | 参照 `docs/USER_WORKFLOW_GUIDE.md` | 覆盖实验创建、模板管理、数据分析等用户关键流程。 |

> 如果测试环境缺少 `pytest` 等依赖，请先运行 `pip install -r requirements-dev.txt`。

---

## 3. 性能与安全

1. **性能配置**
   - 根据部署目标调优 `config/performance.json`（线程数、缓存、并行预加载等）。
   - 运行 `tests/comprehensive_performance_test.py` 验证指标。

2. **安全配置**
   - 每个环境必须通过环境变量或密钥管理系统设置唯一的 `JWT_SECRET_KEY`。
   - 生产环境必须保持 `config.json` 中 `developer.enabled = false`。
   - 更新 `env`/密钥时同步刷新 `tools/generate_secrets.py` 输出。

---

## 4. 日志、监控与告警

- **日志**：`config.json` 中 `log.file` 默认指向 `logs/app.log`。确保部署目标具备日志轮转与外部收集方案（如 ELK、Loki）。
- **监控**：默认启用性能与错误跟踪（`config.monitoring`）。结合已有的监控代理或 APM，将 `metrics_enabled` 与 `health_check_interval` 调整为实际需求。
- **健康探针**：若通过 Web 包装或 API 暴露，请在探针脚本中调用 `scripts/readiness_check.py` 或实现轻量级 `/healthz` 接口。
- **告警**：将 `logs/`、`reports/` 或指标采集系统接入现有告警平台（邮件、Slack、飞书等）。

---

## 5. 发布与回滚步骤

1. `git status` 确认工作区干净，记录版本号（`src/__init__.py`）。
2. 使用 `build_macos.sh` / `build_windows.bat` 或 PyInstaller spec 生成发行包。
3. 在预生产环境再次运行 `scripts/readiness_check.py` + 全量测试。
4. 发布成功后，执行：
   - 监控看板巡检（CPU/RAM、GPU、事件总线延迟等）
   - 日志采样校验（敏感信息脱敏、异常堆栈）
5. 如需回滚，保留上一版本安装包，在目标环境执行原脚本即可；配置文件建议通过版本控制或备份恢复。

---

## 6. 常见问题

| 问题 | 处理方式 |
| --- | --- |
| `JWT` 检查失败 | 确认部署环境导出 `JWT_SECRET_KEY`，并重新启动服务。 |
| 资产目录缺失 | 运行 `python main.py` 首次启动时会自动创建数据目录；模板等请从 `assets/` 同步。 |
| 性能退化 | 检查 `config/performance.json` 与 `config/monitoring_config.json`，必要时启用性能优化入口 `main_optimized.py`。 |
| 监控未上报 | 确认 `monitoring.enabled`、代理配置和网络出口策略。 |

---

通过以上流程，可以确保 VirtualChemLab 在核心功能、性能、安全、测试与运维等方面达到上线标准。欢迎根据实际环境扩展自动化脚本和 CI/CD 流程。***
