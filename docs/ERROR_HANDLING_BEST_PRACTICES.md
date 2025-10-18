# 错误处理最佳实践指南

## 📋 目录

1. [概述](#概述)
2. [错误处理原则](#错误处理原则)
3. [使用工具](#使用工具)
4. [常见场景](#常见场景)
5. [用户体验](#用户体验)
6. [测试与调试](#测试与调试)
7. [最佳实践清单](#最佳实践清单)

---

## 概述

良好的错误处理是提升应用稳定性和用户体验的关键。本指南提供了VirtualChemLab项目中错误处理的最佳实践。

### 核心目标

- **容错性**: 应用能够优雅地处理错误，不会崩溃
- **可恢复性**: 提供自动或手动恢复机制
- **用户友好**: 向用户提供清晰、可操作的错误信息
- **可调试性**: 记录足够的信息便于开发者诊断问题

---

## 错误处理原则

### 1. 永远不要忽略错误

❌ **错误示例**:
```python
try:
    risky_operation()
except Exception:
    pass  # 忽略错误
```

✅ **正确示例**:
```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
    # 采取适当的错误处理措施
```

### 2. 在正确的层级处理错误

- **底层**: 转换技术性错误为业务错误
- **中层**: 添加上下文信息
- **顶层**: 向用户展示友好消息

### 3. 提供恢复选项

每个错误都应该考虑:
- 用户能做什么?
- 系统能自动恢复吗?
- 需要重启吗?

### 4. 记录完整的上下文

错误日志应包含:
- 错误类型和消息
- 发生时间
- 用户操作
- 系统状态
- 堆栈跟踪

---

## 使用工具

### 1. 增强错误处理器

```python
from src.utils.enhanced_error_handler import (
    handle_errors,
    ErrorSeverity,
    show_error,
    show_warning,
)

@handle_errors(
    context="加载实验数据",
    user_message="无法加载实验",
    hint="请检查文件是否存在",
    severity=ErrorSeverity.ERROR,
)
def load_experiment(file_path: str):
    # 实现代码
    pass
```

### 2. 安全文件操作

```python
from src.utils.safe_io import SafeFileIO, safe_read_json

# 安全读取JSON
data = safe_read_json("config.json", default={})

# 安全写入文件
SafeFileIO.write_json("output.json", data, backup=True)
```

### 3. 安全网络操作

```python
from src.utils.safe_network import SafeNetworkClient

client = SafeNetworkClient(base_url="http://api.example.com")

# 自动重试的GET请求
response = client.get("/data")
```

### 4. 错误边界组件

```python
from src.ui.error_boundary import ErrorBoundary

# 包装可能出错的组件
boundary = ErrorBoundary(
    child_widget=my_widget,
    on_error=lambda e, info: logger.error(f"组件错误: {e}")
)
```

### 5. 错误恢复向导

```python
from src.ui.error_recovery_wizard import show_error_recovery_wizard

# 显示交互式恢复向导
success = show_error_recovery_wizard(
    error_type="FileNotFoundError",
    error_message="找不到配置文件",
    error_details=traceback.format_exc(),
)
```

---

## 常见场景

### 场景1: 文件操作

#### 读取文件

```python
from src.utils.safe_io import SafeFileIO
from src.utils.enhanced_error_handler import handle_errors

@handle_errors(
    context="读取配置文件",
    user_message="无法读取配置",
    hint="请检查文件路径和权限",
)
def load_config(path: str) -> dict:
    return SafeFileIO.read_json(path, default={})
```

#### 写入文件

```python
@handle_errors(
    context="保存实验记录",
    user_message="保存失败",
    hint="请检查磁盘空间和权限",
)
def save_record(path: str, data: dict) -> bool:
    # 先检查磁盘空间
    if not SafeFileIO.check_disk_space(path, required_mb=10):
        raise OSError("磁盘空间不足")
    
    # 带备份的写入
    return SafeFileIO.write_json(path, data, backup=True)
```

### 场景2: 网络请求

```python
from src.utils.safe_network import SafeNetworkClient, RetryStrategy

# 配置重试策略
retry_strategy = RetryStrategy(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
)

client = SafeNetworkClient(
    base_url="http://api.example.com",
    timeout=30,
    retry_strategy=retry_strategy,
)

# 发送请求（自动重试）
try:
    response = client.get("/experiments")
except ConnectionError as e:
    # 网络错误处理
    show_error(
        message="网络连接失败",
        hint="请检查网络连接后重试",
        parent=self,
    )
```

### 场景3: UI组件加载

```python
from src.ui.error_boundary import ErrorBoundary

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 使用错误边界保护实验视图
        try:
            experiment_view = ExperimentView()
            self.experiment_boundary = ErrorBoundary(
                child_widget=experiment_view,
                on_error=self.on_component_error,
            )
            self.setCentralWidget(self.experiment_boundary)
        except Exception as e:
            logger.error(f"创建实验视图失败: {e}", exc_info=True)
            self.show_error_fallback()
    
    def on_component_error(self, error: Exception, info: str):
        """组件错误回调"""
        logger.error(f"组件错误: {error}\n{info}")
        # 可以发送错误报告、显示通知等
```

### 场景4: 数据验证

```python
from src.utils.enhanced_error_handler import handle_errors, ErrorSeverity

@handle_errors(
    context="验证用户输入",
    severity=ErrorSeverity.WARNING,
    show_dialog=False,  # 不显示对话框，在UI中显示
)
def validate_input(value: str, field_name: str) -> bool:
    if not value:
        raise ValueError(f"{field_name}不能为空")
    
    if len(value) > 100:
        raise ValueError(f"{field_name}长度不能超过100个字符")
    
    return True

# 使用
try:
    validate_input(user_input, "实验名称")
except ValueError as e:
    # 在UI中显示验证错误
    self.show_validation_error(str(e))
```

### 场景5: 异步操作

```python
from PySide6.QtCore import QThread, Signal

class WorkerThread(QThread):
    error_occurred = Signal(Exception, str)
    
    def run(self):
        try:
            # 执行耗时操作
            self.perform_task()
        except Exception as e:
            # 发射错误信号
            self.error_occurred.emit(e, traceback.format_exc())
    
    @handle_errors(
        context="执行后台任务",
        reraise=True,  # 重新抛出以便信号捕获
    )
    def perform_task(self):
        # 任务逻辑
        pass

# 使用
worker = WorkerThread()
worker.error_occurred.connect(
    lambda e, trace: show_error(
        message=f"后台任务失败: {str(e)}",
        details=trace,
        parent=self,
    )
)
worker.start()
```

---

## 用户体验

### 1. 错误消息设计

#### 错误消息的三个层次

1. **标题**: 简短描述问题
2. **消息**: 用户友好的说明
3. **提示**: 具体的解决建议

示例:
```python
show_error(
    message="无法加载实验文件",  # 简短清晰
    hint="请检查文件路径是否正确，或尝试重新下载文件",  # 可操作的建议
    details=f"文件路径: {path}\n错误: {str(e)}",  # 技术细节
)
```

### 2. 提供恢复选项

```python
from PySide6.QtWidgets import QMessageBox

def show_file_error(file_path: str):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setText(f"无法访问文件: {file_path}")
    msg.setInformativeText("您想如何处理？")
    
    msg.addButton("重试", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton("选择其他文件", QMessageBox.ButtonRole.ActionRole)
    msg.addButton("使用默认配置", QMessageBox.ButtonRole.ActionRole)
    msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
    
    result = msg.exec()
    # 根据选择执行相应操作
```

### 3. 进度反馈

对于可能花费时间的恢复操作:

```python
from PySide6.QtWidgets import QProgressDialog

progress = QProgressDialog("正在恢复文件...", "取消", 0, 0, self)
progress.setWindowModality(Qt.WindowModal)
progress.show()

try:
    # 执行恢复操作
    recover_file()
    progress.close()
except Exception as e:
    progress.close()
    show_error(f"恢复失败: {e}")
```

---

## 测试与调试

### 1. 错误模拟

创建测试用例来模拟各种错误:

```python
import pytest
from unittest.mock import patch

def test_file_not_found_error():
    """测试文件不存在的错误处理"""
    with patch('builtins.open', side_effect=FileNotFoundError()):
        result = load_config("nonexistent.json")
        assert result == {}  # 应该返回默认值

def test_network_timeout():
    """测试网络超时的错误处理"""
    with patch('requests.get', side_effect=TimeoutError()):
        client = SafeNetworkClient()
        result = client.get("/api/test")
        assert result is None
```

### 2. 错误日志分析

查看错误日志:

```python
from pathlib import Path

def analyze_error_logs():
    """分析错误日志，找出常见问题"""
    log_dir = Path("logs/errors")
    
    error_counts = {}
    for log_file in log_dir.glob("*.log"):
        with open(log_file) as f:
            for line in f:
                if "ERROR" in line:
                    # 统计错误类型
                    error_type = extract_error_type(line)
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
    
    return error_counts
```

### 3. 调试模式

在开发环境中启用详细的错误信息:

```python
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    # 显示详细的堆栈跟踪
    error_handler.show_dialogs = True
    logging.getLogger().setLevel(logging.DEBUG)
else:
    # 生产环境：简化的错误消息
    error_handler.show_dialogs = False
    logging.getLogger().setLevel(logging.INFO)
```

---

## 最佳实践清单

### ✅ 文件操作

- [ ] 使用`SafeFileIO`类进行所有文件操作
- [ ] 在写入前检查磁盘空间
- [ ] 对重要文件进行备份
- [ ] 使用临时文件和原子性替换
- [ ] 正确处理编码错误

### ✅ 网络操作

- [ ] 使用`SafeNetworkClient`进行网络请求
- [ ] 配置合理的超时时间
- [ ] 实现重试机制（指数退避）
- [ ] 检查网络连接状态
- [ ] 提供离线模式降级

### ✅ UI组件

- [ ] 使用`ErrorBoundary`包装关键组件
- [ ] 提供降级UI或占位符
- [ ] 显示用户友好的错误消息
- [ ] 提供重试和恢复选项
- [ ] 记录UI错误到日志

### ✅ 数据验证

- [ ] 在输入点进行验证
- [ ] 提供即时反馈
- [ ] 显示具体的验证错误
- [ ] 高亮错误字段
- [ ] 提供正确的输入示例

### ✅ 日志记录

- [ ] 记录错误上下文
- [ ] 包含堆栈跟踪
- [ ] 记录用户操作序列
- [ ] 区分错误严重程度
- [ ] 定期清理旧日志

### ✅ 用户体验

- [ ] 错误消息清晰易懂
- [ ] 提供解决建议
- [ ] 支持一键复制错误信息
- [ ] 显示恢复进度
- [ ] 避免技术术语

### ✅ 测试

- [ ] 测试所有错误路径
- [ ] 模拟各种异常情况
- [ ] 验证错误恢复机制
- [ ] 测试用户交互流程
- [ ] 检查日志记录

---

## 示例：完整的错误处理流程

```python
from src.utils.enhanced_error_handler import handle_errors, ErrorSeverity
from src.utils.safe_io import SafeFileIO
from src.ui.error_recovery_wizard import show_error_recovery_wizard

class ExperimentLoader:
    """实验加载器 - 展示完整的错误处理"""
    
    @handle_errors(
        context="加载实验",
        user_message="加载实验失败",
        severity=ErrorSeverity.ERROR,
    )
    def load_experiment(self, experiment_id: str):
        """加载实验（带完整错误处理）"""
        
        # 步骤1: 检查磁盘空间
        if not SafeFileIO.check_disk_space(self.data_dir, required_mb=50):
            raise OSError("磁盘空间不足，请清理后重试")
        
        # 步骤2: 读取实验数据
        file_path = self.data_dir / f"{experiment_id}.json"
        data = SafeFileIO.read_json(file_path)
        
        if not data:
            # 文件为空或损坏，尝试恢复
            success = show_error_recovery_wizard(
                error_type="DataCorruption",
                error_message="实验数据文件损坏",
                error_details=f"文件: {file_path}",
            )
            
            if not success:
                raise ValueError("无法恢复实验数据")
        
        # 步骤3: 验证数据
        try:
            self.validate_experiment_data(data)
        except ValueError as e:
            logger.warning(f"数据验证失败: {e}")
            # 尝试使用默认值修复
            data = self.fix_experiment_data(data)
        
        # 步骤4: 加载成功
        logger.info(f"实验加载成功: {experiment_id}")
        return data
    
    def validate_experiment_data(self, data: dict):
        """验证实验数据"""
        required_fields = ["id", "name", "steps"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必需字段: {field}")
    
    def fix_experiment_data(self, data: dict) -> dict:
        """修复损坏的实验数据"""
        # 添加默认值
        data.setdefault("id", "unknown")
        data.setdefault("name", "未命名实验")
        data.setdefault("steps", [])
        return data
```

---

## 总结

良好的错误处理需要:

1. **预防**: 在可能出错的地方添加防护
2. **检测**: 及时发现和记录错误
3. **响应**: 提供友好的错误消息和恢复选项
4. **改进**: 分析错误模式，持续优化

记住: **错误是不可避免的，但糟糕的错误处理是可以避免的！**

---

## 相关文档

- [错误系统指南](ERROR_SYSTEM_GUIDE.md)
- [错误系统快速参考](ERROR_SYSTEM_QUICK_REFERENCE.md)
- [API文档](API_REFERENCE.md)

---

**最后更新**: 2025-10-07

