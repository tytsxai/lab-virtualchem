# 🤝 贡献指南

感谢您对 VirtualChemLab 项目的关注！我们欢迎各种形式的贡献。

---

## 📋 目录

- [行为准则](#-行为准则)
- [如何贡献](#-如何贡献)
- [开发流程](#-开发流程)
- [代码规范](#-代码规范)
- [提交规范](#-提交规范)
- [问题反馈](#-问题反馈)

---

## 📜 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：

- ✅ 使用友好和包容的语言
- ✅ 尊重不同的观点和经历
- ✅ 优雅地接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表示同理心

### 不可接受的行为

- ❌ 使用性别化的语言或图像
- ❌ 挑衅、侮辱或贬损性的评论
- ❌ 公开或私下骚扰
- ❌ 未经许可发布他人的私人信息
- ❌ 其他不道德或不专业的行为

---

## 💡 如何贡献

### 贡献类型

我们欢迎以下类型的贡献：

#### 1. 代码贡献
- 🐛 修复Bug
- ✨ 添加新功能
- ⚡ 性能优化
- 🎨 UI/UX改进

#### 2. 文档贡献
- 📝 改进文档
- 🌍 翻译文档
- 📖 编写教程

#### 3. 测试贡献
- ✅ 编写测试用例
- 🔍 发现并报告Bug
- 📊 性能测试

#### 4. 其他贡献
- 💬 回答问题
- 🎨 设计资源
- 📢 推广项目

---

## 🔄 开发流程

### 1. Fork项目

```bash
# Fork项目到您的GitHub账号
# 然后克隆您的Fork
git clone https://github.com/YOUR_USERNAME/VirtualChemLab.git
cd VirtualChemLab
```

### 2. 设置开发环境

```bash
# 添加upstream远程仓库
git remote add upstream https://github.com/ORIGINAL_OWNER/VirtualChemLab.git

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
make dev-install
```

### 3. 创建分支

```bash
# 从main分支创建新分支
git checkout -b feature/amazing-feature

# 分支命名规范:
# - feature/xxx  新功能
# - bugfix/xxx   Bug修复
# - docs/xxx     文档更新
# - refactor/xxx 代码重构
```

### 4. 开发

```bash
# 编写代码
# ...

# 运行代码检查
make lint

# 运行测试
make test

# 运行所有检查
make all-checks
```

### 5. 提交代码

```bash
# 添加更改
git add .

# 提交（遵循提交规范）
git commit -m "feat: add amazing feature"

# 推送到您的Fork
git push origin feature/amazing-feature
```

### 6. 创建Pull Request

1. 访问您的Fork页面
2. 点击"New Pull Request"
3. 填写PR模板
4. 等待审查

---

## 📝 代码规范

### Python代码规范

我们使用 **Ruff** 进行代码检查和格式化。

```bash
# 检查代码
make lint

# 自动修复
make lint-fix

# 格式化代码
make format
```

### 代码风格

#### 1. 类型注解

```python
# ✅ 推荐：使用现代类型注解
from __future__ import annotations

def function(param: str | None = None) -> dict[str, Any]:
    """函数说明"""
    ...

# ❌ 避免：旧式类型注解
from typing import Optional, Dict, Any

def function(param: Optional[str] = None) -> Dict[str, Any]:
    ...
```

#### 2. 文档字符串

```python
def calculate_score(answers: list[str], correct: list[str]) -> float:
    """
    计算实验得分

    Args:
        answers: 用户答案列表
        correct: 正确答案列表

    Returns:
        得分（0-100）

    Raises:
        ValueError: 答案列表长度不匹配

    Example:
        >>> calculate_score(["A", "B"], ["A", "B"])
        100.0
    """
    ...
```

#### 3. Import排序

```python
# 标准库
import os
import sys
from pathlib import Path

# 第三方库
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

# 本地模块
from ..core.experiment import Experiment
from ..utils.logger import get_logger
```

#### 4. 命名规范

```python
# 类名：PascalCase
class ExperimentController:
    pass

# 函数/变量名：snake_case
def calculate_result():
    experiment_id = "exp_001"

# 常量：UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有成员：_前缀
class MyClass:
    def __init__(self):
        self._private_var = 0
```

### 测试规范

#### 测试文件命名

```
tests/
├── ui/
│   ├── test_main_window.py
│   └── test_error_boundary.py
└── core/
    └── test_experiment.py
```

#### 测试用例编写

```python
import pytest

def test_function_success():
    """测试成功情况"""
    result = function(valid_input)
    assert result == expected_output

def test_function_failure():
    """测试失败情况"""
    with pytest.raises(ValueError):
        function(invalid_input)

@pytest.mark.parametrize("input,expected", [
    ("a", "A"),
    ("b", "B"),
])
def test_function_parametrized(input, expected):
    """参数化测试"""
    assert function(input) == expected
```

---

## 📋 提交规范

我们使用 **Conventional Commits** 规范。

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | feat: add experiment export |
| `fix` | Bug修复 | fix: resolve chart rendering issue |
| `docs` | 文档更新 | docs: update README |
| `style` | 代码格式 | style: format with ruff |
| `refactor` | 代码重构 | refactor: simplify error handling |
| `perf` | 性能优化 | perf: optimize list scrolling |
| `test` | 测试相关 | test: add error boundary tests |
| `chore` | 构建/工具 | chore: update dependencies |

### 提交示例

```bash
# 简单提交
git commit -m "feat: add dark mode support"

# 详细提交
git commit -m "feat(ui): add responsive layout

- Add breakpoints for mobile/tablet/desktop
- Implement adaptive sizing
- Support touch gestures

Closes #123"

# Breaking change
git commit -m "feat!: redesign API

BREAKING CHANGE: API endpoint changed from /v1 to /v2"
```

---

## 🐛 问题反馈

### 报告Bug

使用以下模板提交Bug：

```markdown
**Bug描述**
简要描述Bug

**复现步骤**
1. 打开应用
2. 点击'...'
3. 出现错误

**预期行为**
应该怎样工作

**实际行为**
实际发生了什么

**截图**
如果可能，添加截图

**环境信息**
- OS: [e.g. Windows 10]
- Python: [e.g. 3.11]
- 版本: [e.g. 1.0.0]

**附加信息**
其他相关信息
```

### 功能请求

使用以下模板请求新功能：

```markdown
**功能描述**
简要描述您想要的功能

**使用场景**
这个功能解决什么问题？

**建议的实现**
您认为应该如何实现？

**替代方案**
考虑过其他方案吗？

**附加信息**
其他相关信息
```

---

## 🔍 代码审查

### 审查清单

提交PR前，请确保：

- [ ] 代码通过所有测试
- [ ] 代码通过Linter检查
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 遵循代码规范
- [ ] 提交信息符合规范
- [ ] 没有合并冲突

### 审查流程

1. **自动检查** - CI/CD自动运行测试
2. **代码审查** - 维护者审查代码
3. **讨论修改** - 根据反馈修改
4. **合并** - 审查通过后合并

---

## 🎯 优先级

我们优先处理以下类型的贡献：

### 高优先级 🔴
- 安全问题修复
- 严重Bug修复
- 性能问题修复

### 中优先级 🟡
- 功能增强
- 文档改进
- 测试增加

### 低优先级 🟢
- 代码重构
- 依赖更新
- 小的UI调整

---

## 📚 学习资源

### 项目文档
- [README](README.md)
- [快速上手](QUICKSTART.md)
- [架构设计](docs/architecture.md)

### 外部资源
- [Python官方文档](https://docs.python.org/)
- [PySide6文档](https://doc.qt.io/qtforpython/)
- [Git教程](https://git-scm.com/book/zh/v2)

---

## 💬 获取帮助

需要帮助？

- 💡 [GitHub Discussions](https://github.com/yourusername/VirtualChemLab/discussions)
- 💬 [Issue Tracker](https://github.com/yourusername/VirtualChemLab/issues)
- 📧 Email: dev@virtualchemlab.com

---

## 🙏 致谢

感谢所有贡献者！

您的贡献将被记录在：
- [贡献者列表](https://github.com/yourusername/VirtualChemLab/graphs/contributors)
- [变更日志](CHANGELOG.md)

---

## 📄 许可证

贡献即表示您同意在 MIT 许可证下分享您的代码。

---

<div align="center">

**感谢您的贡献！** ❤️

Made with ❤️ by VirtualChemLab Team

</div>
