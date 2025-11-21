# VirtualChemLab 部署指南

## 📦 项目状态

✅ **可以运行了!** 项目已经过测试,核心功能正常。

---

## 🚀 快速运行(开发模式)

### 前置要求
- Python 3.10+（推荐 3.11，已在 3.10–3.13 测试）
- Windows 10+ / macOS 10.15+ / Linux

### 步骤

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

   **国内用户推荐使用镜像**:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **启动GUI应用**
   ```bash
   python main.py
   ```

3. **或仅测试核心功能**
   ```bash
   python main.py --test-core
   ```

---

## 📦 打包为可执行文件

### 方案1: PyInstaller (推荐)

#### 1.1 安装打包工具
```bash
pip install pyinstaller
```

#### 1.2 打包为单文件
```bash
pyinstaller --onefile --windowed \
  --name VirtualChemLab \
  --add-data "assets;assets" \
  --add-data "config.json;." \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets \
  main.py
```

**Windows命令**(注意分号):
```cmd
pyinstaller --onefile --windowed ^
  --name VirtualChemLab ^
  --add-data "assets;assets" ^
  --add-data "config.json;." ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  main.py
```

#### 1.3 打包为文件夹(启动更快)
```bash
pyinstaller --windowed \
  --name VirtualChemLab \
  --add-data "assets;assets" \
  --add-data "config.json;." \
  main.py
```

#### 1.4 输出位置
- **单文件**: `dist/VirtualChemLab.exe`
- **文件夹**: `dist/VirtualChemLab/VirtualChemLab.exe`

#### 1.5 分发
- **单文件**: 直接发送 `.exe` 文件
- **文件夹**: 压缩整个 `dist/VirtualChemLab/` 目录

---

### 方案2: cx_Freeze

#### 2.1 安装
```bash
pip install cx_Freeze
```

#### 2.2 创建 `setup.py`
```python
from cx_Freeze import setup, Executable
import sys

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="VirtualChemLab",
    version="1.0.0",
    description="Virtual Chemistry Laboratory",
    executables=[Executable("main.py", base=base, target_name="VirtualChemLab")],
    options={
        "build_exe": {
            "packages": ["PySide6", "numpy", "yaml", "pydantic"],
            "include_files": ["assets/", "config.json"],
        }
    }
)
```

#### 2.3 打包
```bash
python setup.py build
```

#### 2.4 输出
- 位置: `build/exe.win-amd64-3.13/`

---

### 方案3: Nuitka (性能最佳)

#### 3.1 安装
```bash
pip install nuitka
```

Windows还需安装MinGW64或MSVC编译器

#### 3.2 打包
```bash
python -m nuitka --standalone --windows-disable-console \
  --enable-plugin=pyside6 \
  --include-data-dir=assets=assets \
  --include-data-file=config.json=config.json \
  --output-dir=dist \
  main.py
```

#### 3.3 输出
- 位置: `dist/run_gui.dist/`

---

## 🐳 Docker 部署(可选)

### Dockerfile示例
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# 复制文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露端口(如果是Web版)
# EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
```

**注意**: GUI应用在Docker中运行需要X11转发,不建议用于桌面应用。

---

## 📱 便携版制作

### Windows便携版

1. **安装到虚拟环境**
   ```cmd
   python -m venv venv_portable
   venv_portable\Scripts\activate
   pip install -r requirements.txt
   ```

2. **创建启动脚本** `VirtualChemLab.bat`
   ```batch
   @echo off
   cd /d "%~dp0"
   venv_portable\Scripts\python.exe main.py
   pause
   ```

3. **打包文件夹**
   ```
   VirtualChemLab_Portable/
   ├── venv_portable/      (虚拟环境)
   ├── src/
   ├── assets/
   ├── main.py
   ├── VirtualChemLab.bat  (启动器)
   └── README.txt
   ```

4. **压缩分发**
   ```cmd
   7z a VirtualChemLab_v1.0_Portable.7z VirtualChemLab_Portable\
   ```

---

## 🌐 Web版部署(未来计划)

### 技术栈建议
- **前端**: React / Vue.js
- **后端**: FastAPI
- **部署**: Vercel / Heroku / AWS

### 当前状态
❌ 未实现 - 需要重写UI层

---

## 📊 部署方案对比

| 方案 | 文件大小 | 启动速度 | 打包难度 | 推荐度 |
|------|---------|---------|---------|-------|
| **直接运行** | N/A | 快 | 无 | ⭐⭐⭐⭐⭐ (开发) |
| **PyInstaller(单文件)** | ~150MB | 慢(3-5s) | 简单 | ⭐⭐⭐⭐ |
| **PyInstaller(文件夹)** | ~200MB | 快(1s) | 简单 | ⭐⭐⭐⭐⭐ (推荐) |
| **cx_Freeze** | ~180MB | 中 | 中等 | ⭐⭐⭐ |
| **Nuitka** | ~100MB | 最快 | 困难 | ⭐⭐⭐⭐ (进阶) |
| **便携版** | ~300MB | 快 | 简单 | ⭐⭐⭐⭐ (教学场景) |

---

## ✅ 验证部署

### 测试清单

1. **核心功能测试**
   ```bash
   python main.py --test-core
   ```
   - [ ] 模板加载成功
   - [ ] 曲线生成正常
   - [ ] 无错误输出

2. **GUI测试**
   ```bash
   python main.py
   ```
   - [ ] 窗口正常打开
   - [ ] 实验列表显示
   - [ ] 可以选择并开始实验
   - [ ] 提交答案有反馈
   - [ ] 可以生成报告

3. **打包测试**
   - [ ] 可执行文件能启动
   - [ ] 功能完整
   - [ ] 无崩溃

---

## 🐛 常见问题

### Q1: PyInstaller打包后运行报错 "Failed to execute script"?

**A**: 可能缺少数据文件,检查 `--add-data` 是否正确:
```bash
# 查看打包日志
pyinstaller --onefile --windowed --log-level=DEBUG main.py
```

### Q2: 打包后文件过大?

**A**: 可以:
1. 使用UPX压缩: `pip install pyinstaller[upx]`
2. 排除不需要的库:
   ```bash
   --exclude-module matplotlib
   --exclude-module pandas
   ```

### Q3: 打包后启动慢?

**A**:
- 使用文件夹模式而非单文件
- 或使用Nuitka编译

### Q4: Mac打包后无法运行?

**A**: 需要签名:
```bash
codesign --force --deep --sign - dist/VirtualChemLab.app
```

### Q5: Linux缺少Qt库?

**A**: 安装系统依赖:
```bash
# Ubuntu/Debian
sudo apt-get install libxcb-xinerama0 libxkbcommon-x11-0

# CentOS/RHEL
sudo yum install xcb-util-wm xcb-util-renderutil
```

---

## 📝 版本发布流程

### 1. 准备发布

```bash
# 更新版本号
vim src/__init__.py  # VERSION = "1.0.0"
vim pyproject.toml   # version = "1.0.0"

# 更新CHANGELOG
vim CHANGELOG.md

# 提交
git add .
git commit -m "Release v1.0.0"
git tag v1.0.0
```

### 2. 打包

```bash
# Windows
pyinstaller VirtualChemLab.spec

# 测试
dist\VirtualChemLab\VirtualChemLab.exe

# 压缩
7z a VirtualChemLab_v1.0.0_Windows_x64.7z dist\VirtualChemLab\
```

### 3. 发布

```bash
# 推送标签
git push origin v1.0.0

# 创建GitHub Release
# 上传压缩包
```

---

## 🎯 当前状态

### ✅ 已完成
- [x] 核心引擎运行正常
- [x] GUI可以启动
- [x] 依赖完整安装
- [x] 滴定实验模板可用
- [x] 曲线生成功能正常

### ⏳ 待优化
- [ ] 添加更多实验模板
- [ ] 优化启动速度
- [ ] 添加图标资源
- [ ] 完善错误处理
- [ ] 创建安装程序

### 🎯 推荐部署方式

**开发/测试**: 直接运行 `python main.py`

**分发给用户**: PyInstaller打包(文件夹模式)

**教学环境**: 便携版(含虚拟环境)

---

## 📞 技术支持

如遇部署问题,请:
1. 查看 `logs/app.log` 日志
2. 搜索GitHub Issues
3. 提交新Issue并附带日志

---

**部署状态**: ✅ **可以运行和部署!**

**最后测试**: 2025-10-06
**Python版本**: 3.13.7
**操作系统**: Windows 10

---

*Happy Deploying!* 🚀




