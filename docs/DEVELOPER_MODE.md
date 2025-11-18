# 🛠️ VirtualChemLab 开发者模式指南

## 概述

开发者模式是 VirtualChemLab 为开发者提供的高级调试和配置工具集，允许开发者深入了解系统运行状态、查看日志、编辑配置、监控性能等。

**重要说明**:
- ⚠️ 开发者模式仅供开发和调试使用
- 🔒 普通用户无法访问开发者功能
- 🔐 需要通过认证才能激活

---

## 激活方式

### 方式1: 开发者密钥认证

1. 启动 VirtualChemLab 应用
2. 在主窗口中输入秘密序列（如连续输入 "DEVMODE"）
3. 或通过菜单：帮助 -> 开发者认证（菜单默认隐藏）
4. 输入开发者密钥

> ⚠️ 在使用此方式之前，请先在环境变量中配置 `DEVELOPER_KEY_HASH`。
> 建议使用 `tools/setup_dev_key.py` 来生成随机密钥并自动写入 `.env` 文件，避免将敏感信息保存在配置文件中。

### 方式2: 秘密按键序列

在主窗口中快速连续输入以下任一序列（不区分大小写）：

- `DEVMODE`
- `DEVELOPER`
- `DEBUG`
- `CONSOLE`

输入正确后将自动激活开发者模式。

### 方式3: 快捷键

激活开发者模式后，可使用快捷键：

- **Ctrl+Shift+D**: 打开开发者控制台

---

## 功能模块

### 1. 📋 日志查看器

**功能**:
- 实时查看应用日志
- 按日志级别过滤（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 关键词搜索
- 自动刷新
- 查看最近1000条日志

**使用方法**:
1. 打开开发者控制台
2. 切换到"日志查看"标签页
3. 使用过滤器和搜索功能定位问题
4. 启用"自动刷新"实时监控

**适用场景**:
- 调试应用错误
- 追踪程序执行流程
- 监控异常信息

---

### 2. 📊 性能监控器

**功能**:
- CPU使用率监控
- 内存使用监控
- 线程数统计
- 实时更新（每秒）

**依赖**: 需要安装 `psutil` 包

```bash
pip install psutil
```

**使用方法**:
1. 打开开发者控制台
2. 切换到"性能监控"标签页
3. 查看实时性能指标

**适用场景**:
- 性能优化
- 资源泄漏检测
- 性能瓶颈分析

---

### 3. ⚙️ 配置编辑器

**功能**:
- 可视化查看配置树
- JSON编辑器直接编辑配置
- 配置验证
- 热重载（部分配置）

**使用方法**:
1. 打开开发者控制台
2. 切换到"配置编辑"标签页
3. 在树视图或JSON编辑器中修改配置
4. 点击"保存配置"

**注意事项**:
- ⚠️ 某些配置需要重启应用才能生效
- 🔒 请谨慎修改配置，错误的配置可能导致应用无法启动
- 💾 修改前建议备份 `config.json`

**适用场景**:
- 快速调整参数
- 测试不同配置
- 开发环境配置

---

### 4. 🐛 调试控制台

**功能**:
- 执行Python代码
- 访问应用内部变量
- 实时测试代码片段

**使用方法**:
1. 打开开发者控制台
2. 切换到"调试控制台"标签页
3. 在命令输入框中输入Python代码
4. 按Enter或点击"执行"

**示例**:

```python
# 查看配置
config.get("app.name")

# 查看日志
logger.info("测试日志")

# 查看实验模板
template_engine.list_available_experiments()

# 查看系统信息
import sys
sys.version
```

**⚠️ 安全警告**:
- 此功能可以执行任意Python代码
- 请勿在生产环境启用
- 仅用于开发和调试

---

### 5. 💾 数据库查看器

**功能**:
- 查看数据库表结构
- 浏览数据记录
- 执行SQL查询

**状态**: 🚧 开发中

---

### 6. 🌐 API测试器

**功能**:
- 测试API接口
- 查看请求/响应
- 性能测试

**状态**: 🚧 开发中

---

## 配置说明

开发者模式配置位于 `config.json` 的 `developer` 节点：

```json
{
  "developer": {
    "enabled": true,                    // 是否启用开发者模式
    "session_timeout_hours": 24,        // 会话超时时间（小时）
    "enabled_features": [               // 启用的功能列表
      "debug_console",
      "log_viewer",
      "performance_monitor",
      "config_editor",
      "database_viewer",
      "api_tester"
    ],
    "secret_sequences": [               // 秘密按键序列
      "DEVMODE",
      "DEVELOPER"
    ],
    "max_login_attempts": 5,            // 最大登录尝试次数
    "lockout_duration_minutes": 15      // 锁定时长（分钟）
  }
}
```

> ✅ 开发者密钥哈希通过环境变量 `DEVELOPER_KEY_HASH` 提供。请勿在 `config.json` 中保存真实密钥或哈希值。

---

## 安全管理

### 生成新的开发者密钥

使用工具脚本生成随机密钥并写入 `.env` 文件：

```bash
python tools/setup_dev_key.py
```

> 运行后按照提示选择随机密钥或自定义密钥，并确认要写入的环境变量文件（默认 `.env`）。脚本会自动：
> - 生成强随机密钥（或使用自定义密钥）
> - 计算哈希并写入 `DEVELOPER_KEY_HASH`
> - 在终端显示一次明文密钥，供您安全保存

也可以手动生成：

```python
from src.core.dev_auth import DeveloperAuth

raw_key = DeveloperAuth.generate_dev_key()
hashed = DeveloperAuth._hash_key(raw_key)
print(raw_key)
# 将 hashed 写入 DEVELOPER_KEY_HASH 环境变量
```

### 密钥安全建议

1. ✅ 生产环境必须设置独立密钥（不要使用示例或测试密钥）
2. ✅ 使用强密钥（32字符以上）
3. ✅ 定期更换密钥
4. ✅ 不要将密钥提交到版本控制
5. ✅ 使用环境变量或密钥管理系统

### 访问控制

**失败锁定机制**:
- 连续失败5次后锁定15分钟
- 锁定期间无法认证
- 防止暴力破解

**会话管理**:
- 会话默认24小时过期
- 可手动延长会话
- 关闭控制台不会清除会话

---

## 使用场景示例

### 场景1: 调试实验模板加载错误

1. 激活开发者模式
2. 打开日志查看器
3. 设置日志级别为 "ERROR"
4. 搜索 "template" 或 "load"
5. 查看错误堆栈信息
6. 定位问题

### 场景2: 优化性能

1. 打开性能监控器
2. 运行实验
3. 观察CPU和内存使用
4. 识别性能瓶颈
5. 使用调试控制台测试优化方案

### 场景3: 修改配置参数

1. 打开配置编辑器
2. 在JSON编辑器中修改参数
3. 保存配置
4. 重启应用（如需要）
5. 验证效果

---

## 常见问题

### Q: 忘记开发者密钥怎么办？

A: 重新生成即可。运行 `python tools/setup_dev_key.py` 生成新的随机密钥并写入 `DEVELOPER_KEY_HASH`，随后使用新的明文密钥登录。旧密钥将自动失效。

### Q: 开发者菜单不显示？

A: 开发者菜单默认隐藏，需要先通过秘密序列或密钥认证激活开发者模式。

### Q: 秘密序列不工作？

A:
- 确保在主窗口中输入
- 快速连续输入，不要停顿超过2秒
- 输入完整的序列（如 DEVMODE）
- 检查 `config.json` 中的 `secret_sequences` 配置

### Q: 日志查看器显示"文件不存在"？

A:
- 确保应用已运行一段时间生成日志
- 检查 `logs/app.log` 文件是否存在
- 检查日志配置是否正确

### Q: 性能监控器不工作？

A: 需要安装 `psutil` 包：

```bash
pip install psutil
```

### Q: 如何禁用开发者模式？

A: 在 `config.json` 中设置：

```json
{
  "developer": {
    "enabled": false
  }
}
```

---

## 最佳实践

1. **开发环境**:
   - 启用所有开发者功能
   - 使用 `tools/setup_dev_key.py` 生成的测试密钥，并保存在本地 `.env`
   - 启用自动刷新和详细日志

2. **测试环境**:
   - 启用开发者模式
   - 使用专用测试密钥（与生产环境区分）
   - 启用性能监控

3. **生产环境**:
   - 建议禁用开发者模式
   - 如需启用，必须使用强密钥
   - 只启用必要的功能
   - 严格控制访问权限

---

## 扩展开发

### 添加新的开发者功能

1. 在 `src/ui/developer_console.py` 中创建新的Widget
2. 在 `DeveloperConsole.init_ui()` 中添加标签页
3. 在 `config.json` 的 `enabled_features` 中添加功能名
4. 实现功能逻辑

### 示例：添加自定义工具

```python
# 在 DeveloperConsole 类中添加
def _create_custom_tool(self) -> QWidget:
    """创建自定义工具"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 你的工具UI
    layout.addWidget(QLabel("自定义工具"))

    return widget

# 在 init_ui 中添加
if self.dev_auth.has_feature('custom_tool'):
    self.custom_tool = self._create_custom_tool()
    self.tab_widget.addTab(self.custom_tool, "🔧 自定义工具")
```

---

## 相关文档

- [开发者快速入门](DEVELOPER_QUICKSTART.md)
- [API开发指南](API_DEV_GUIDE.md)
- [架构文档](ARCHITECTURE.md)
- [性能优化](PERFORMANCE_OPTIMIZATION.md)

---

## 技术支持

如有问题或建议，请：
- 查看日志文件：`logs/app.log`
- 提交Issue
- 联系开发团队

---

**版本**: 1.0.0
**更新日期**: 2025-10-06
**维护者**: VirtualChemLab 开发团队

