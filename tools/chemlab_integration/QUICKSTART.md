# 🚀 ChemLab 集成快速开始

## 5 分钟上手指南

### Windows 用户

#### 方式 1: 双击运行 (推荐)

1. 双击 `导入ChemLab数据.bat`
2. 按提示选择操作
3. 等待完成

#### 方式 2: 命令行

```powershell
cd tools\chemlab_integration

# 安装依赖
pip install -r requirements.txt

# 导入所有数据
python scripts\import_all.py

# 验证数据
python scripts\validate_output.py ..\..\data\templates
```

### Linux/macOS 用户

```bash
cd tools/chemlab_integration

# 安装依赖
pip install -r requirements.txt

# 导入所有数据
python scripts/import_all.py

# 验证数据
python scripts/validate_output.py ../../data/templates
```

---

## 常用命令

### 导入数据

```bash
# 导入所有数据
python scripts/import_all.py

# 仅导入实验
python scripts/import_experiments.py

# 仅导入知识库
python scripts/import_knowledge.py

# 更新到最新版本
python scripts/import_all.py --update

# 强制覆盖已存在文件
python scripts/import_all.py --force

# 详细输出
python scripts/import_all.py --verbose
```

### 验证数据

```bash
# 验证实验模板
python scripts/validate_output.py ../../data/templates

# 验证知识库
python scripts/validate_output.py ../../data/knowledge

# 保存验证报告
python scripts/validate_output.py ../../data/templates --output report.json
```

---

## 配置调整

编辑 `config.yaml` 自定义设置:

```yaml
# 修改输出目录
output:
  experiments_dir: "../../data/templates"
  knowledge_dir: "../../data/knowledge"

# 调整过滤规则
filters:
  experiments:
    include_levels: ["basic", "intermediate"]  # 仅导入基础和中级
    min_steps: 3
    max_steps: 20

# 转换选项
conversion:
  experiments:
    default_duration: 60  # 改为 60 分钟
```

---

## 验证导入结果

### 1. 检查文件

```bash
# 查看导入的实验
ls ../../data/templates/chemlab_exp_*.yaml

# 查看导入的知识卡片
ls ../../data/knowledge/reagent/chemlab_*.yaml
```

### 2. 在 VirtualChemLab 中测试

```bash
cd ../..
python main.py
```

在 VirtualChemLab 中:
1. 打开实验列表
2. 查找 "chemlab_exp_" 开头的实验
3. 尝试运行新导入的实验

---

## 故障排查

### 问题 1: Git 克隆失败

**原因**: 网络问题或 Git 未安装

**解决**:
```bash
# 检查 Git
git --version

# 如未安装,请安装 Git
# Windows: https://git-scm.com/download/win
# Linux: sudo apt install git
# macOS: brew install git
```

### 问题 2: 依赖安装失败

**解决**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --upgrade
```

### 问题 3: 验证失败

**解决**:
```bash
# 查看详细错误
python scripts/import_all.py --verbose

# 检查模型是否正确导入
python -c "from src.models.experiment import ExperimentTemplate; print('OK')"
```

---

## 下一步

✅ 导入成功后:

1. 📚 阅读完整文档: [docs/CHEMLAB_INTEGRATION.md](../../docs/CHEMLAB_INTEGRATION.md)
2. 🧪 在 VirtualChemLab 中试用新实验
3. ⚙️ 根据需要调整配置和重新导入
4. 🔄 定期更新 ChemLab 数据

---

## 获取帮助

- 📖 完整文档: [docs/CHEMLAB_INTEGRATION.md](../../docs/CHEMLAB_INTEGRATION.md)
- 🐛 报告问题: GitHub Issues
- 💬 讨论交流: GitHub Discussions

---

**祝使用愉快! 🎉**
