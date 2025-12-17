# 🔐 VirtualChemLab 设备管理与防作弊系统指南

## 📋 概述

VirtualChemLab 实现了完整的设备指纹识别、授权管理、异常检测和管理后台系统，用于防止许可证滥用、作弊行为，并提供全面的监控和管理能力。

## 🎯 核心功能

### 1. 设备指纹识别

**功能特性：**

- ✅ 多维度硬件信息采集（CPU ID、MAC地址、系统UUID、磁盘序列号）
- ✅ 跨平台支持（Windows、Linux、macOS）
- ✅ 稳定的设备唯一标识生成
- ✅ 智能缓存机制
- ✅ 硬件变更检测

**采集的信息：**

```python
{
    "device_id": "A1B2C3D4E5F6G7H8...",  # 设备唯一ID
    "hostname": "USER-PC",                # 主机名
    "mac_address": "00:1A:2B:3C:4D:5E",  # MAC地址
    "cpu_info": "Intel Core i7-9700K",   # CPU信息
    "system_uuid": "550e8400-e29b-41d4...", # 系统UUID
    "platform_info": {                    # 平台信息
        "system": "Windows",
        "release": "10",
        "version": "10.0.19044"
    },
    "network_info": {                     # 网络信息
        "local_ip": "192.168.1.100",
        "mac_address": "00:1A:2B:3C:4D:5E"
    }
}
```

### 2. IP地址追踪

**功能特性：**

- ✅ 公网IP和本地IP采集
- ✅ 地理位置查询（国家、地区、城市）
- ✅ ISP识别
- ✅ 代理/VPN检测
- ✅ 可疑IP标记和追踪
- ✅ IP使用统计分析

**IP信息示例：**

```json
{
    "ip_address": "203.0.113.42",
    "country": "China",
    "region": "Beijing",
    "city": "Beijing",
    "isp": "China Telecom",
    "is_proxy": false,
    "is_vpn": false,
    "timestamp": "2025-10-06T10:30:00"
}
```

### 3. 设备授权管理

**授权流程：**

1. **首次使用**
   - 采集设备指纹
   - 检查授权码是否可用
   - 验证设备数量限制
   - 绑定设备到许可证

2. **后续使用**
   - 验证设备指纹
   - 检查是否被封控
   - 记录使用历史
   - 追踪IP地址

3. **设备限制**
   - 每个授权码限制设备数量
   - 不同许可证类型有不同限制：
     - 试用版：1台设备
     - 个人版：2台设备
     - 教育版：5台设备
     - 商业版：10台设备
     - 企业版：无限设备

### 4. 异常检测系统

**检测类型：**

#### 4.1 设备异常

- 短时间内多设备尝试使用同一许可证
- 频繁的验证失败
- 被封控设备仍在尝试访问

#### 4.2 IP异常

- 短时间内使用多个不同IP
- 来自多个国家/地区的连接
- 使用可疑IP或代理/VPN

#### 4.3 行为异常

- 异常的使用时间模式
- 不合理的操作序列
- 疑似自动化脚本

**异常报告格式：**

```json
{
    "type": "multiple_devices",
    "severity": "high",
    "message": "检测到5个不同设备尝试使用同一许可证",
    "data": {
        "device_count": 5,
        "devices": ["device_id_1", "device_id_2", ...]
    }
}
```

### 5. 设备封控机制

**封控触发条件：**

- 管理员手动封控
- 自动检测到严重异常
- 许可证被撤销
- 违反使用协议

**封控效果：**

- 立即阻止该设备访问
- 记录封控原因和时间
- 所有验证请求被拒绝
- 审计日志完整记录

**解除封控：**

- 管理员手动解除
- 提供申诉渠道
- 记录解封操作

### 6. 审计日志系统

**记录的事件：**

| 事件类型 | 说明 | 级别 |
|---------|------|------|
| LICENSE_GENERATED | 许可证生成 | INFO |
| LICENSE_ACTIVATED | 许可证激活 | INFO |
| LICENSE_VALIDATED | 许可证验证 | INFO/WARNING |
| LICENSE_REVOKED | 许可证撤销 | WARNING |
| DEVICE_BLOCKED | 设备封控 | WARNING |
| DEVICE_UNBLOCKED | 设备解封 | INFO |
| ANOMALY_DETECTED | 异常检测 | WARNING/ERROR/CRITICAL |
| ADMIN_ACTION | 管理员操作 | INFO |

**日志格式：**

```json
{
    "event_type": "license_validated",
    "timestamp": "2025-10-06T10:30:00",
    "level": "info",
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "device_id": "A1B2C3D4E5F6G7H8",
    "ip_address": "203.0.113.42",
    "action": "验证许可证",
    "result": "成功",
    "details": {...}
}
```

## 🖥️ 管理后台

### 启动管理后台

**Windows:**

```batch
启动管理后台.bat
```

**命令行:**

```bash
python tools/admin_server_start.py --host 127.0.0.1 --port 5000
```

**访问地址:**

```
管理面板: http://127.0.0.1:5000/dashboard
API文档: http://127.0.0.1:5000/api
```

> 注意：
> - 管理后台 API 需要在请求头携带 `X-Admin-Secret`（其值来自环境变量 `VCL_ADMIN_SECRET_KEY`）。
> - 通过 `/dashboard` 打开的页面可在右上角输入密钥后使用；如用自定义前端/脚本访问，请自行添加该 Header。
> - CORS 默认关闭；如需跨域访问请显式设置 `VCL_ADMIN_CORS_ORIGINS`。

### 管理后台功能

#### 1. 仪表板

- 总许可证数量
- 活跃设备数量
- 封控设备数量
- 24小时活动统计
- 实时刷新

#### 2. 设备管理

- 查看所有设备列表
- 搜索设备（ID、主机名、MAC地址）
- 查看设备详情
- 设备封控/解封
- 设备使用历史

#### 3. 许可证管理

- 查看许可证列表
- 许可证详情
- 验证许可证
- 撤销许可证
- 使用统计

#### 4. 活动记录

- 实时活动监控
- 过滤和搜索
- 成功/失败统计
- 导出记录

#### 5. 异常检测

- 实时异常检测
- 异常分类和等级
- 自动告警
- 处理建议

## 🔌 API接口

### 仪表板统计

```http
GET /api/dashboard/stats
```

**响应：**

```json
{
    "stats": {
        "total_licenses": 100,
        "total_devices": 250,
        "blocked_devices": 5,
        "recent_activities": 1234
    }
}
```

### 设备列表

```http
GET /api/devices
```

**响应：**

```json
{
    "devices": [
        {
            "device_id": "A1B2C3D4...",
            "hostname": "USER-PC",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "first_seen": "2025-01-01T00:00:00",
            "last_seen": "2025-10-06T10:30:00",
            "total_attempts": 50,
            "is_blocked": false
        }
    ],
    "total": 250
}
```

### 设备详情

```http
GET /api/devices/{device_id}
```

### 封控设备

```http
POST /api/devices/{device_id}/block
Content-Type: application/json

{
    "reason": "检测到异常行为"
}
```

### 解除封控

```http
POST /api/devices/{device_id}/unblock
```

### 许可证验证

```http
POST /api/licenses/{license_key}/validate
```

### 使用统计

```http
GET /api/licenses/{license_key}/usage
```

### 异常检测

```http
GET /api/licenses/{license_key}/anomalies
```

### 活动记录

```http
GET /api/activities?limit=100&license_key=XXXX&device_id=YYYY
```

## 💻 编程接口

### 设备指纹采集

```python
from src.core.device_fingerprint import DeviceFingerprintCollector

# 创建采集器
collector = DeviceFingerprintCollector()

# 采集设备指纹
fingerprint = collector.collect()

print(f"设备ID: {fingerprint.device_id}")
print(f"主机名: {fingerprint.hostname}")
print(f"MAC地址: {fingerprint.mac_address}")
```

### 设备授权检查

```python
from src.core.device_fingerprint import DeviceAuthManager

# 创建授权管理器
auth_manager = DeviceAuthManager()

# 检查设备授权
authorized, message, fingerprint = auth_manager.check_device_authorization(
    license_key="XXXX-XXXX-XXXX-XXXX",
    max_devices=2
)

if authorized:
    print("设备授权通过")
else:
    print(f"授权失败: {message}")
```

### IP追踪

```python
from src.core.ip_tracker import IPTracker

# 创建IP追踪器
tracker = IPTracker()

# 追踪IP
ip_info = tracker.track_ip(
    license_key="XXXX-XXXX-XXXX-XXXX",
    device_id="A1B2C3D4E5F6G7H8"
)

print(f"IP地址: {ip_info.ip_address}")
print(f"国家: {ip_info.country}")
print(f"城市: {ip_info.city}")

# 获取IP统计
stats = tracker.get_ip_stats(license_key="XXXX-XXXX-XXXX-XXXX")
print(f"唯一IP数: {stats['unique_ips']}")
```

### 审计日志

```python
from src.core.audit_logger import get_audit_logger, AuditEventType, AuditLevel

# 获取审计日志记录器
audit_logger = get_audit_logger()

# 记录事件
audit_logger.log_event(
    event_type=AuditEventType.LICENSE_VALIDATED,
    action="验证许可证",
    result="成功",
    level=AuditLevel.INFO,
    license_key="XXXX-XXXX-XXXX-XXXX",
    device_id="A1B2C3D4E5F6G7H8",
    ip_address="203.0.113.42"
)

# 查询事件
events = audit_logger.get_events(
    license_key="XXXX-XXXX-XXXX-XXXX",
    limit=100
)

# 获取统计
stats = audit_logger.get_statistics()
print(f"总事件数: {stats['total_events']}")
```

### 异常检测

```python
from src.core.license_validator import LicenseMonitor
from src.core.license_manager import LicenseManager
from pathlib import Path

# 创建监控器
license_manager = LicenseManager(
    secret_key="your_secret_key",
    license_file=Path("data/license.json")
)
monitor = LicenseMonitor(license_manager)

# 检测异常
anomalies = monitor.detect_anomalies(license_key="XXXX-XXXX-XXXX-XXXX")

for anomaly in anomalies:
    print(f"类型: {anomaly['type']}")
    print(f"严重程度: {anomaly['severity']}")
    print(f"消息: {anomaly['message']}")
```

## 📊 数据存储

### 目录结构

```
data/
├── device_fingerprint.json        # 设备指纹缓存
├── device_auth/
│   ├── auth_history.json         # 授权历史
│   └── blocked_devices.json      # 封控设备列表
├── ip_tracking/
│   ├── ip_history.json           # IP历史记录
│   └── suspicious_ips.json       # 可疑IP列表
└── license.json                   # 许可证文件

logs/
└── audit/
    ├── audit_20251006.jsonl      # 审计日志（按日期）
    ├── audit_20251005.jsonl
    └── ...
```

## 🔒 安全建议

### 1. 管理后台安全

- ⚠️ **仅在内网使用**：不要将管理后台暴露到公网
- ⚠️ **使用强密钥**：修改默认的 `secret_key`
- ⚠️ **启用身份认证**：在生产环境添加登录验证
- ⚠️ **使用HTTPS**：通过反向代理启用SSL
- ⚠️ **限制访问IP**：使用防火墙或IP白名单

### 2. 数据保护

- 定期备份审计日志和设备数据
- 加密敏感信息存储
- 限制日志文件访问权限
- 定期清理过期数据

### 3. 异常处理

- 设置告警阈值
- 及时处理高危异常
- 建立异常处理流程
- 记录处理结果

### 4. 合规性

- 遵守数据保护法规（GDPR、个人信息保护法等）
- 明确告知用户数据收集范围
- 提供数据查询和删除接口
- 定期进行安全审计

## 🚀 最佳实践

### 1. 设备管理

- 合理设置设备数量限制
- 定期审查设备列表
- 及时清理无效设备
- 建立设备申诉机制

### 2. 异常检测

- 根据业务调整检测阈值
- 避免误报和过度封控
- 人工审核高危异常
- 持续优化检测规则

### 3. 日志管理

- 定期归档审计日志
- 建立日志分析流程
- 监控关键指标
- 生成定期报告

### 4. 性能优化

- 使用缓存减少重复采集
- 异步处理日志写入
- 定期清理历史数据
- 优化数据库查询

## 🛠️ 故障排除

### 问题1: 设备指纹采集失败

**原因：** 权限不足或系统不支持
**解决：**

- 使用管理员权限运行
- 检查系统兼容性
- 查看错误日志

### 问题2: 管理后台无法访问

**原因：** 端口被占用或防火墙阻止
**解决：**

- 更换端口
- 检查防火墙设置
- 确认服务正常启动

### 问题3: IP地理位置查询失败

**原因：** 网络问题或API限制
**解决：**

- 检查网络连接
- 使用本地IP数据库
- 配置代理

### 问题4: 审计日志丢失

**原因：** 磁盘空间不足或权限问题
**解决：**

- 检查磁盘空间
- 确认写入权限
- 定期清理日志

## 📞 支持

如有问题，请：

1. 查看日志文件：`logs/audit/`
2. 检查配置文件：`config/crypto_payment_config.json`
3. 提交Issue到项目仓库
4. 联系技术支持

## 🔄 更新日志

### v1.0.0 (2025-10-06)

- ✅ 实现设备指纹识别系统
- ✅ 添加IP地址追踪功能
- ✅ 开发设备授权管理
- ✅ 实现异常检测机制
- ✅ 创建管理后台面板
- ✅ 集成审计日志系统
- ✅ 提供完整API接口

---

**注意：** 本系统旨在防止滥用和作弊，请合理使用，避免侵犯用户隐私。
