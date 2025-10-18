# VirtualChemLab 代码风格与注释规范

**版本**: 1.0.0  
**最后更新**: 2025-10-07

---

## 📋 目录

- [概述](#概述)
- [Python代码风格](#python代码风格)
- [文档字符串规范](#文档字符串规范)
- [注释规范](#注释规范)
- [类型注解规范](#类型注解规范)
- [命名规范](#命名规范)
- [文件组织规范](#文件组织规范)
- [示例](#示例)

---

## 概述

本文档定义了VirtualChemLab项目的代码风格和注释规范，确保代码库的一致性和可维护性。

### 核心原则

1. **清晰优于简洁** - 代码应该易于理解
2. **一致性至上** - 遵循统一的风格
3. **文档完备** - 关键代码必须有文档
4. **类型安全** - 使用类型注解
5. **可测试性** - 编写易于测试的代码

---

## Python代码风格

### 基础规范

我们遵循以下Python编码规范：

- **PEP 8** - Python代码风格指南
- **PEP 257** - 文档字符串规范
- **PEP 484** - 类型注解
- **Google Python Style Guide** - Google Python风格指南（部分）

### 代码格式化工具

项目使用以下工具确保代码风格一致：

```bash
# 代码格式化
black src tests --line-length 100

# 导入排序
isort src tests --profile black

# 代码检查
ruff check src tests --fix

# 类型检查
mypy src --strict
```

### 行长度

- 最大行长度：**100字符**
- 文档字符串：**88字符**
- 注释：**72字符**

### 缩进

- 使用 **4个空格** 缩进
- 不使用制表符

### 导入顺序

```python
"""模块文档字符串"""

# 1. 标准库导入
import os
import sys
from typing import Any, Dict, List

# 2. 第三方库导入
from PySide6.QtCore import Qt, Signal
from pydantic import BaseModel

# 3. 本地应用导入
from src.core.di_container import DIContainer
from src.models.experiment import ExperimentTemplate
```

---

## 文档字符串规范

### 模块级文档字符串

每个Python模块文件必须以文档字符串开头：

```python
"""
模块名称 - 简短描述

详细说明模块的功能、用途和设计思路。

功能特性:
- 特性1: 描述
- 特性2: 描述
- 特性3: 描述

示例:
    基本用法示例
    
    >>> from module import Class
    >>> obj = Class()
    >>> obj.method()

注意:
    重要的使用注意事项

参考:
    - 相关文档链接
    - 设计文档链接
"""
```

### 类文档字符串

```python
class ExperimentController:
    """实验流程控制器
    
    管理实验的生命周期、状态转换和数据流转。
    
    该控制器负责：
    1. 实验的创建和初始化
    2. 实验步骤的执行和验证
    3. 实验数据的收集和分析
    4. 错误处理和恢复机制
    
    属性:
        template (ExperimentTemplate): 实验模板
        user_id (str): 用户ID
        state (ExperimentState): 当前实验状态
        session_id (str): 会话ID
        
    示例:
        创建并执行实验
        
        >>> controller = ExperimentController(template, user_id="user123")
        >>> controller.start_experiment()
        >>> result = controller.execute_step(step_data)
        
    注意:
        - 实验执行过程中会自动保存状态
        - 支持从中断点恢复实验
        - 线程安全的操作
        
    参考:
        - docs/EXPERIMENT_GUIDE.md
        - ExperimentState枚举定义
    """
```

### 方法/函数文档字符串

使用Google风格的文档字符串：

```python
def execute_step(
    self,
    step_index: int,
    input_data: dict[str, Any],
    auto_save: bool = True
) -> StepResult:
    """执行实验步骤
    
    验证并执行指定的实验步骤，记录执行结果。
    
    该方法会：
    1. 验证步骤索引的有效性
    2. 验证输入数据的格式和内容
    3. 执行步骤逻辑
    4. 记录执行结果和错误
    5. 触发相关事件
    6. 自动保存状态（可选）
    
    Args:
        step_index (int): 步骤索引，从0开始
        input_data (dict[str, Any]): 步骤输入数据，键值对格式
        auto_save (bool, optional): 是否自动保存状态. 默认为True
        
    Returns:
        StepResult: 步骤执行结果，包含：
            - success (bool): 是否成功
            - score (int): 得分
            - errors (list[str]): 错误列表
            - warnings (list[str]): 警告列表
            - data (dict): 步骤数据
            
    Raises:
        ValueError: 当步骤索引无效时
        ValidationError: 当输入数据验证失败时
        ExperimentStateError: 当实验状态不允许执行步骤时
        
    示例:
        执行第一步
        
        >>> result = controller.execute_step(
        ...     step_index=0,
        ...     input_data={"reagent": "HCl", "volume": 10.0}
        ... )
        >>> if result.success:
        ...     print(f"得分: {result.score}")
        
    注意:
        - 必须按顺序执行步骤
        - 输入数据必须符合步骤定义的格式
        - 执行失败不会影响已完成的步骤
        
    参考:
        - StepResult类定义
        - ValidationError异常
    """
```

### 属性文档字符串

```python
@property
def current_step(self) -> int:
    """当前步骤索引
    
    返回当前正在执行或即将执行的步骤索引。
    如果实验未开始，返回0；如果已完成，返回总步骤数。
    
    Returns:
        int: 当前步骤索引（从0开始）
        
    示例:
        >>> controller.current_step
        2
    """
    return self._current_step
```

---

## 注释规范

### 单行注释

```python
# 好的注释：解释为什么这样做
# 使用缓存避免重复计算，提升性能
result = self._cache.get(key)

# 不好的注释：重复代码的意思
# 从缓存获取结果
result = self._cache.get(key)
```

### 多行注释

```python
# 复杂算法或业务逻辑需要详细注释
#
# 实验评分算法：
# 1. 基础分：完成步骤的基本分数
# 2. 时间加成：快速完成可获得额外分数
# 3. 准确度加成：操作准确度高可获得额外分数
# 4. 连击加成：连续成功操作可获得连击加成
# 5. 惩罚机制：错误操作会扣分
#
# 最终得分 = 基础分 × (1 + 时间加成 + 准确度加成 + 连击加成) - 惩罚
```

### TODO注释

```python
# TODO(username): 描述需要做的事情和原因
# TODO(ww): 添加错误重试机制，提高系统健壮性 - Issue #123

# FIXME(username): 描述需要修复的问题
# FIXME(ww): 内存泄漏问题，需要释放大对象 - Bug #456

# NOTE(username): 重要说明
# NOTE(ww): 此处的顺序很重要，不要随意调整

# HACK(username): 临时解决方案
# HACK(ww): 临时绕过Qt的布局问题，等待Qt 6.8修复
```

### 复杂逻辑注释

```python
def calculate_score(self, step_result: StepResult) -> int:
    """计算步骤得分"""
    
    # 步骤1: 计算基础分数
    # 基础分由步骤的难度系数决定
    base_score = step_result.base_score * self.difficulty_factor
    
    # 步骤2: 应用时间加成
    # 如果完成时间低于标准时间的80%，获得20%加成
    # 如果完成时间低于标准时间的50%，获得50%加成
    time_bonus = 0
    if step_result.duration < self.standard_time * 0.5:
        time_bonus = base_score * 0.5
    elif step_result.duration < self.standard_time * 0.8:
        time_bonus = base_score * 0.2
    
    # 步骤3: 应用准确度加成
    # 准确度100%: 30%加成
    # 准确度95-99%: 20%加成  
    # 准确度90-94%: 10%加成
    accuracy_bonus = 0
    if step_result.accuracy >= 1.0:
        accuracy_bonus = base_score * 0.3
    elif step_result.accuracy >= 0.95:
        accuracy_bonus = base_score * 0.2
    elif step_result.accuracy >= 0.9:
        accuracy_bonus = base_score * 0.1
    
    # 步骤4: 应用连击加成
    # 每连续成功一次，加成增加5%，最高50%
    combo_bonus = min(self.combo_count * 0.05, 0.5) * base_score
    
    # 步骤5: 计算最终得分
    final_score = int(base_score + time_bonus + accuracy_bonus + combo_bonus)
    
    return final_score
```

---

## 类型注解规范

### 基本类型注解

```python
from typing import Any, Dict, List, Optional, Union, Callable

def process_data(
    data: dict[str, Any],
    options: list[str] | None = None,
    callback: Callable[[str], None] | None = None
) -> tuple[bool, str]:
    """处理数据"""
    pass
```

### 泛型类型

```python
from typing import TypeVar, Generic

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

class Cache(Generic[K, V]):
    """通用缓存类"""
    
    def get(self, key: K) -> V | None:
        """获取缓存值"""
        pass
    
    def set(self, key: K, value: V) -> None:
        """设置缓存值"""
        pass
```

### Protocol类型

```python
from typing import Protocol

class Drawable(Protocol):
    """可绘制对象协议"""
    
    def draw(self, canvas: Any) -> None:
        """绘制到画布"""
        ...

def render(obj: Drawable) -> None:
    """渲染对象"""
    obj.draw(canvas)
```

### 类型别名

```python
# 复杂类型使用别名简化
StepData = dict[str, Any]
ValidationResult = tuple[bool, list[str]]
EventHandler = Callable[[Event], None]

def validate_step(step: StepData) -> ValidationResult:
    """验证步骤数据"""
    pass
```

---

## 命名规范

### 模块和包

- 小写字母
- 单词之间用下划线分隔
- 简短且描述性强

```python
# 好的命名
experiment_controller.py
user_management.py
data_validator.py

# 避免的命名
ExperimentController.py  # 不要用大驼峰
exp_ctrl.py  # 不要缩写
```

### 类名

- 大驼峰命名法（PascalCase）
- 名词或名词短语
- 清晰描述类的职责

```python
# 好的命名
class ExperimentController:
class UserRecord:
class DataValidator:

# 避免的命名
class experiment_controller:  # 不要用下划线
class EC:  # 不要缩写
class DoStuff:  # 不要用动词
```

### 函数和方法

- 小写字母加下划线
- 动词或动词短语
- 清晰描述功能

```python
# 好的命名
def validate_input(data: dict) -> bool:
def calculate_score(result: StepResult) -> int:
def get_user_by_id(user_id: str) -> User | None:

# 避免的命名
def ValidateInput(data: dict) -> bool:  # 不要用大驼峰
def calc_scr(r: StepResult) -> int:  # 不要缩写
def data(d: dict) -> bool:  # 不要用名词
```

### 变量

- 小写字母加下划线
- 名词或名词短语
- 描述性强

```python
# 好的命名
user_id = "user123"
experiment_template = load_template()
total_score = calculate_total()

# 避免的命名
userId = "user123"  # 不要用驼峰
t = load_template()  # 不要单字母（循环除外）
x = calculate_total()  # 不要无意义命名
```

### 常量

- 全大写字母
- 单词之间用下划线分隔

```python
# 好的命名
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# 避免的命名
max_retry_count = 3  # 不要小写
MaxRetryCount = 3  # 不要驼峰
```

### 私有成员

- 单下划线前缀表示内部使用
- 双下划线前缀表示名称改写（少用）

```python
class MyClass:
    def __init__(self):
        self._internal_value = 0  # 内部使用
        self.__private_value = 0  # 名称改写（少用）
    
    def _internal_method(self):  # 内部方法
        pass
    
    def public_method(self):  # 公共方法
        pass
```

---

## 文件组织规范

### 标准文件结构

```python
"""
模块文档字符串
"""

# 1. Future导入
from __future__ import annotations

# 2. 标准库导入
import os
import sys
from typing import Any

# 3. 第三方库导入
from PySide6.QtCore import Qt
from pydantic import BaseModel

# 4. 本地导入
from src.core.di_container import DIContainer
from src.models.experiment import ExperimentTemplate

# 5. 模块级常量
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 6. 类型别名和类型变量
T = TypeVar("T")
StepData = dict[str, Any]

# 7. 异常类定义
class CustomError(Exception):
    """自定义异常"""
    pass

# 8. 主要类定义
class MainClass:
    """主要类"""
    pass

# 9. 辅助函数
def helper_function() -> None:
    """辅助函数"""
    pass

# 10. 模块级别的初始化代码（如果需要）
logger = logging.getLogger(__name__)
```

### 文件命名

```
模块文件: lowercase_with_underscores.py
测试文件: test_module_name.py
配置文件: config.py, settings.py
工具文件: utils.py, helpers.py
```

---

## 示例

### 完整的模块示例

```python
"""
实验数据分析器

提供实验数据的统计分析、趋势分析和可视化功能。

功能特性:
- 基础统计：平均分、中位数、标准差等
- 趋势分析：学习曲线、进步趋势
- 异常检测：识别异常数据点
- 可视化：生成图表和报告

示例:
    基本用法
    
    >>> analyzer = ExperimentAnalyzer(user_id="user123")
    >>> stats = analyzer.get_statistics()
    >>> print(f"平均分: {stats.average_score}")
    
参考:
    - docs/DATA_ANALYSIS_GUIDE.md
    - ExperimentMetrics类
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from src.core.di_container import DIContainer
from src.models.user_record import UserRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 常量定义
MIN_DATA_POINTS = 3  # 最小数据点数量
OUTLIER_THRESHOLD = 3.0  # 异常值阈值（标准差倍数）


@dataclass
class Statistics:
    """统计数据
    
    属性:
        count: 数据点数量
        average: 平均值
        median: 中位数
        std_dev: 标准差
        min_value: 最小值
        max_value: 最大值
    """
    
    count: int
    average: float
    median: float
    std_dev: float
    min_value: float
    max_value: float


class ExperimentAnalyzer:
    """实验数据分析器
    
    分析用户的实验数据，提供统计信息和趋势分析。
    
    属性:
        user_id (str): 用户ID
        records (list[UserRecord]): 用户实验记录
        
    示例:
        >>> analyzer = ExperimentAnalyzer(user_id="user123")
        >>> stats = analyzer.get_statistics()
        >>> trend = analyzer.analyze_trend(days=30)
        
    注意:
        - 需要至少3个数据点才能进行有效分析
        - 分析结果会缓存，避免重复计算
    """
    
    def __init__(self, user_id: str, container: DIContainer | None = None):
        """初始化分析器
        
        Args:
            user_id: 用户ID
            container: 依赖注入容器（可选）
        """
        self.user_id = user_id
        self.container = container or DIContainer()
        self.records: list[UserRecord] = []
        self._cache: dict[str, Any] = {}
        
        # 加载用户记录
        self._load_records()
    
    def _load_records(self) -> None:
        """加载用户实验记录
        
        从存储中加载用户的所有实验记录。
        
        Raises:
            RuntimeError: 加载记录失败时
        """
        try:
            storage = self.container.resolve("storage")
            self.records = storage.get_user_records(self.user_id)
            logger.info(f"加载了 {len(self.records)} 条记录")
        except Exception as e:
            logger.error(f"加载记录失败: {e}")
            raise RuntimeError(f"无法加载用户记录: {e}") from e
    
    def get_statistics(self, days: int | None = None) -> Statistics:
        """获取统计信息
        
        计算指定时间范围内的基础统计信息。
        
        Args:
            days: 分析的天数，None表示所有数据
            
        Returns:
            Statistics: 统计结果
            
        Raises:
            ValueError: 当数据点不足时
            
        示例:
            >>> stats = analyzer.get_statistics(days=30)
            >>> print(f"最近30天平均分: {stats.average}")
        """
        # 过滤数据
        records = self._filter_by_date(self.records, days)
        
        if len(records) < MIN_DATA_POINTS:
            raise ValueError(
                f"数据点不足，需要至少 {MIN_DATA_POINTS} 个数据点"
            )
        
        # 提取分数
        scores = [record.score for record in records]
        
        # 计算统计量
        return Statistics(
            count=len(scores),
            average=float(np.mean(scores)),
            median=float(np.median(scores)),
            std_dev=float(np.std(scores)),
            min_value=float(np.min(scores)),
            max_value=float(np.max(scores))
        )
    
    def _filter_by_date(
        self,
        records: list[UserRecord],
        days: int | None
    ) -> list[UserRecord]:
        """按日期过滤记录
        
        Args:
            records: 原始记录列表
            days: 保留最近N天的记录，None表示全部
            
        Returns:
            list[UserRecord]: 过滤后的记录
        """
        if days is None:
            return records
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return [
            record for record in records
            if record.timestamp >= cutoff_date
        ]
```

---

## 工具配置

### pyproject.toml

```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py38"

[tool.mypy]
python_version = "3.8"
strict = true
warn_return_any = true
warn_unused_configs = true
```

---

## 总结

遵循本规范可以：

✅ 提高代码可读性  
✅ 便于团队协作  
✅ 减少维护成本  
✅ 提升代码质量  
✅ 加速新人上手  

**记住**：好的代码应该像好的文章一样，让人一读就懂。

---

**更新历史**:
- 2025-10-07: 初始版本


