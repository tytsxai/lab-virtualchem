# VirtualChemLab 安装指南

## 系统要求

- **Python**: 3.10 或更高（推荐 3.11）
- **操作系统**: Windows / macOS / Linux
- **内存**: 建议 4GB 以上
- **磁盘空间**: 500MB（基础版），2GB（完整版）

## 安装方式

### 方式一：最小安装（推荐入门）

仅安装核心功能，适合快速体验：

```bash
# 克隆仓库
git clone https://github.com/tytsxai/VirtualChemLab.git
cd VirtualChemLab

# 安装核心依赖（推荐使用锁定文件）
pip install -r requirements.lock
# 如需自定义版本，请更新 pyproject.toml 并重新生成锁定文件
# pip-compile --extra=dev --extra=docs --extra=redis --extra=performance --extra=admin --extra=ops --extra=plugins --generate-hashes --output-file=requirements.lock pyproject.toml

# 运行程序
python main.py
```

**功能**：
- ✅ 基础化学实验模拟
- ✅ 数据记录和分析
- ✅ matplotlib 图表
- ❌ 分子结构可视化（需要 RDKit）
- ❌ PDF 报告导出（需要 ReportLab）
- ❌ 交互式图表（需要 PyQtGraph）

---

### 方式二：推荐安装（常用功能）

安装核心功能 + 常用插件：

```bash
# 安装核心依赖（或使用 requirements.lock 保持一致）
pip install -r requirements.lock

# 安装推荐插件
pip install rdkit reportlab

# 或使用插件管理工具
python -m src.plugins.manager install --recommended
```

**功能**：
- ✅ 所有基础功能
- ✅ 分子结构渲染和属性计算
- ✅ PDF 报告生成
- ❌ 交互式图表
- ❌ 高级热力学计算

---

### 方式三：完整安装（所有功能）

安装所有可选功能：

```bash
# 安装核心依赖（或使用 requirements.lock 保持一致）
pip install -r requirements.lock

# 安装所有 pip 可装的插件
pip install -r requirements-optional.txt

# OpenMM 需要用 conda 安装（可选）
conda install -c conda-forge openmm
```

**功能**：
- ✅ 所有功能

---

## 按需安装插件

### 化学结构渲染 (RDKit)

用于分子可视化和属性计算：

```bash
pip install rdkit
```

### 交互式图表 (PyQtGraph)

用于高性能实时图表：

```bash
pip install pyqtgraph
```

### PDF 报告生成

**方案1：ReportLab**（推荐）
```bash
pip install reportlab
```

**方案2：WeasyPrint**（更强大，依赖更多）
```bash
pip install weasyprint
```

### 高级热力学计算 (Cantera)

用于精确的化学反应计算：

```bash
pip install cantera
```

### 分子动力学 (OpenMM)

用于分子模拟和动画：

```bash
# 推荐用 conda 安装
conda install -c conda-forge openmm
```

---

## 验证安装

### 1. 检查插件状态

```bash
python -m src.plugins.manager status
```

### 2. 运行测试

```bash
pytest tests/test_plugins.py -v
```

### 3. 运行演示

```bash
python examples/plugin_demo.py
```

### 4. 启动程序

```bash
python main.py
```

---

## 常见问题

### Q: 安装 RDKit 失败

**Windows**:
```bash
# 使用 conda
conda install -c conda-forge rdkit
```

**macOS**:
```bash
# 使用 Homebrew
brew install rdkit
pip install rdkit
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-rdkit
pip install rdkit
```

### Q: WeasyPrint 安装失败

WeasyPrint 依赖系统库，需要先安装：

**Windows**:
下载 GTK3 Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

**macOS**:
```bash
brew install cairo pango gdk-pixbuf libffi
pip install weasyprint
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
pip install weasyprint
```

### Q: OpenMM 安装失败

OpenMM 需要用 conda 安装：

```bash
# 创建 conda 环境（可选）
conda create -n chemlab python=3.10
conda activate chemlab

# 安装 OpenMM
conda install -c conda-forge openmm

# 安装其他依赖
pip install -r requirements.lock
```

### Q: 导入错误

确保在项目根目录运行程序：

```bash
cd VirtualChemLab
python main.py
```

或设置 PYTHONPATH：

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python main.py
```

### Q: 没有 main.py

如果还没有创建主程序，可以先运行演示：

```bash
python examples/plugin_demo.py
```

---

## 环境变量配置

- `JWT_SECRET_KEY`：JWT 密钥，至少 32 个字符。生产环境必须外部提供。
- `SESSION_SECRET_KEY`：会话密钥，至少 32 个字符。生产环境必须外部提供。
- `VCL_ADMIN_SECRET_KEY`：管理后台/Flask SECRET_KEY，建议独立于 JWT 密钥。
- `ENVIRONMENT`：`development` / `staging` / `production`，用于切换默认安全策略。

可通过 `.env` 或系统环境变量设置，例如：

```bash
export JWT_SECRET_KEY="please_change_me_to_a_secure_value"
export SESSION_SECRET_KEY="please_change_me_to_a_secure_value"
export VCL_ADMIN_SECRET_KEY="admin_panel_secret"
export ENVIRONMENT="production"
```

生产环境缺少必需密钥将导致程序拒绝启动。

---

## 开发环境设置

如果要参与开发：

```bash
# 安装开发/测试所需的全部依赖（包含 dev/docs/admin/performance 等 extras）
pip install -r requirements.lock
pip install --no-deps -e .

# 安装所有可选插件（用于实验性或可选功能）
pip install -r requirements-optional.txt

# 运行测试
pytest

# 代码格式化
black src/

# 类型检查
mypy src/
```

---

## 卸载

```bash
# 卸载核心依赖
pip uninstall -r requirements.lock -y

# 卸载可选插件
pip uninstall -r requirements-optional.txt -y

# 删除项目文件
rm -rf VirtualChemLab
```

---

## 更新

```bash
# 更新代码
git pull

# 更新依赖
pip install --upgrade -r requirements.lock

# 更新插件
pip install --upgrade -r requirements-optional.txt
```

---

## 技术支持

- **文档**: [docs/PLUGINS.md](docs/PLUGINS.md)
- **问题反馈**: GitHub Issues
- **讨论**: GitHub Discussions

---

## 许可证

本项目采用 MIT 许可证。所有可选插件均为宽松许可证，可安全用于商业项目。详见各插件的许可证声明。
