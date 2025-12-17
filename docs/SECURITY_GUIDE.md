# Security Guide（安全指南）

本指南用于汇总 VirtualChemLab 的安全相关约定与建议配置。

> 安全与认证的协议层说明参见：`docs/API_EVENT_PROTOCOL.md` 的“安全与认证”章节。

## 基础建议

- 生产环境通过环境变量注入密钥/令牌，不在仓库提交真实密钥
- 使用最小权限原则配置管理员/服务账号
- 启用日志与审计（如适用）

## 相关入口

- 环境变量样例：`.env.example`、`env.example`
- 安全扫描工具（如有）：`tools/security_scan.py`

