# 工具测试指南

## 快速测试所有工具

### 运行集成测试
```bash
# 测试所有工具是否正常工作
python tests/test_tools_integration.py
```

### 运行单元测试
```bash
# 测试配置管理
pytest tests/unit/test_config.py -v

# 测试密钥生成器
pytest tests/unit/test_generate_secrets.py -v

# 运行所有单元测试
pytest tests/unit/ -v
```

## 测试覆盖的内容

### 1. 配置文件存在性
- ✅ config/base.json
- ✅ config/development.json
- ✅ config/production.json
- ✅ config/test.json

### 2. 文档文件存在性
- ✅ 综合建议报告
- ✅ 执行清单
- ✅ 一页总结
- ✅ 文档索引
- ✅ 使用指南
- ✅ 完成报告
- ✅ 快速开始

### 3. 工具文件存在性
- ✅ tools/generate_secrets.py
- ✅ tools/test_coverage_tracker.py
- ✅ 快速改进工具箱.bat
- ✅ 快速测试.bat

### 4. 模块导入
- ✅ 配置模块可以导入
- ✅ 配置对象可以创建
- ✅ 单例模式工作正常

### 5. 工具运行
- ✅ 密钥生成器可以运行
- ✅ 覆盖率追踪器可以运行
- ✅ 配置管理可以运行

## 预期输出

```
============================================================
VirtualChemLab 工具集成测试
============================================================

============================================================
测试: 配置文件
============================================================
✅ config/base.json 存在
✅ config/development.json 存在
✅ config/production.json 存在
✅ config/test.json 存在

============================================================
测试: 文档文件
============================================================
✅ 🎯VirtualChemLab项目综合建议报告.md (8192 bytes)
✅ ✅项目改进执行清单.md (6144 bytes)
...

============================================================
测试总结
============================================================
✅ 配置文件
✅ 文档文件
✅ 工具文件
✅ 模块导入
✅ 密钥生成器
✅ 覆盖率追踪器
✅ 配置管理

通过: 7/7

🎉 所有测试通过!
```

## 故障排除

### 问题: 模块导入失败
```bash
# 解决方案: 安装依赖
pip install pydantic
```

### 问题: pytest未找到
```bash
# 解决方案: 安装pytest
pip install pytest pytest-cov
```

### 问题: 工具运行失败
```bash
# 解决方案: 检查Python路径
python --version
which python  # Linux/Mac
where python  # Windows
```

## 持续集成

### 添加到CI/CD
```yaml
# .github/workflows/test.yml
name: Test Tools

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -r requirements.txt
      - run: python tests/test_tools_integration.py
      - run: pytest tests/unit/test_config.py -v
```


