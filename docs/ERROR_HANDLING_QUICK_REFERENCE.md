# 错误处理快速参考

## 🚀 快速开始

### 导入必要的模块

```python
from src.utils.enhanced_error_handler import (
    handle_errors,
    ErrorSeverity,
    show_error,
    show_warning,
    show_info,
)
from src.utils.safe_io import SafeFileIO, safe_read_json, safe_write_json
from src.utils.safe_network import SafeNetworkClient, check_network
from src.ui.error_boundary import ErrorBoundary
from src.ui.error_recovery_wizard import show_error_recovery_wizard
```

---

## 📝 常用代码片段

### 1. 装饰器错误处理

```python
@handle_errors(
    context="操作描述",
    user_message="用户友好的错误消息",
    hint="解决建议",
    severity=ErrorSeverity.ERROR,
    show_dialog=True,
)
def your_function():
    # 您的代码
    pass
```

### 2. 安全文件读取

```python
# 读取JSON（带默认值）
data = safe_read_json("config.json", default={})

# 读取文本文件
content = SafeFileIO.read_file("data.txt", default="")
```

### 3. 安全文件写入

```python
# 写入JSON（带备份）
SafeFileIO.write_json("output.json", data, backup=True)

# 写入文本
SafeFileIO.write_file("output.txt", content, create_dirs=True)
```

### 4. 网络请求（自动重试）

```python
client = SafeNetworkClient(
    base_url="http://api.example.com",
    timeout=30,
)

# GET请求
response = client.get("/endpoint")

# POST请求
response = client.post("/endpoint", json={"key": "value"})
```

### 5. UI错误边界

```python
# 包装可能出错的组件
boundary = ErrorBoundary(
    child_widget=my_widget,
    on_error=lambda e, info: logger.error(f"错误: {e}")
)
```

### 6. 错误恢复向导

```python
success = show_error_recovery_wizard(
    error_type="FileNotFoundError",
    error_message="找不到配置文件",
    error_details=traceback.format_exc(),
)
```

---

## 🔧 错误严重程度

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `INFO` | 提示信息 | 配置已加载 |
| `WARNING` | 警告但可继续 | 使用了默认值 |
| `ERROR` | 错误需要处理 | 文件读取失败 |
| `CRITICAL` | 严重错误 | 系统崩溃 |

---

## 📋 错误处理检查清单

### 文件操作

- [ ] 检查文件是否存在
- [ ] 检查磁盘空间
- [ ] 处理权限错误
- [ ] 备份重要文件
- [ ] 使用临时文件写入

### 网络操作

- [ ] 设置合理的超时
- [ ] 实现重试机制
- [ ] 检查网络连接
- [ ] 处理HTTP错误码
- [ ] 提供离线降级

### UI组件

- [ ] 使用错误边界
- [ ] 显示友好错误消息
- [ ] 提供重试选项
- [ ] 记录错误日志
- [ ] 不阻塞用户操作

---

## 🎯 最佳实践

### ✅ 推荐做法

```python
# 1. 使用装饰器处理错误
@handle_errors(context="加载数据")
def load_data():
    pass

# 2. 提供默认值
data = safe_read_json("file.json", default={})

# 3. 带备份的写入
SafeFileIO.write_json("file.json", data, backup=True)

# 4. 检查前置条件
if not SafeFileIO.check_disk_space(".", 100):
    raise OSError("磁盘空间不足")
```

### ❌ 避免的做法

```python
# 1. 不要忽略错误
try:
    risky_operation()
except Exception:
    pass  # ❌ 错误

# 2. 不要使用通用异常
try:
    pass
except Exception as e:  # ❌ 太宽泛
    pass

# 3. 不要丢失上下文
raise Exception("错误")  # ❌ 缺少上下文
```

---

## 🔍 常见错误处理

### FileNotFoundError

```python
try:
    data = SafeFileIO.read_json(path)
except FileNotFoundError:
    show_error(
        message=f"找不到文件: {path}",
        hint="请检查文件路径或重新创建文件",
    )
```

### PermissionError

```python
try:
    SafeFileIO.write_file(path, content)
except PermissionError:
    show_error(
        message="没有权限写入文件",
        hint="请以管理员身份运行或更换保存位置",
    )
```

### ConnectionError

```python
try:
    response = client.get("/api/data")
except ConnectionError:
    show_error(
        message="网络连接失败",
        hint="请检查网络连接后重试",
    )
```

### ValueError

```python
try:
    value = int(user_input)
except ValueError:
    show_warning(
        message="输入格式不正确",
        hint="请输入有效的数字",
    )
```

---

## 🧪 测试错误处理

```python
import pytest
from unittest.mock import patch

def test_file_not_found():
    """测试文件不存在的处理"""
    with patch('builtins.open', side_effect=FileNotFoundError()):
        result = load_config("missing.json")
        assert result == {}  # 应返回默认值

def test_network_timeout():
    """测试网络超时处理"""
    with patch('requests.get', side_effect=TimeoutError()):
        result = fetch_data()
        assert result is None
```

---

## 📊 错误监控

```python
# 查看错误历史
from src.utils.enhanced_error_handler import error_handler

print(f"总错误数: {len(error_handler.error_history)}")

# 最近的错误
for err in error_handler.error_history[-5:]:
    print(f"{err.severity.value}: {err.message}")
```

---

## 🎨 自定义错误消息

```python
# 使用i18n
from src.utils.i18n import I18n

i18n = I18n()

show_error(
    message=i18n.t("error.file_not_found", file=path),
    hint=i18n.t("error.file_not_found_hint"),
)
```

---

## 📞 获取帮助

- 详细文档: [ERROR_HANDLING_BEST_PRACTICES.md](ERROR_HANDLING_BEST_PRACTICES.md)
- 错误系统: [ERROR_SYSTEM_GUIDE.md](ERROR_SYSTEM_GUIDE.md)
- 示例代码: [examples/error_handling_examples.py](../examples/error_handling_examples.py)

---

**最后更新**: 2025-10-07

