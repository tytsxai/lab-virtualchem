# VirtualChemLab 部署指南

## 📦 项目状态

✅ **可以运行了!** 项目已经过测试,核心功能正常。

## 🎯 推荐部署方式

- **本地桌面单机**（教学/实验室/内网环境）：主应用 + 可选管理工具。
- **macOS 兼容**：通过 `build_macos.sh` 打包为 `.app`，适合分发给单机用户。
- REST API/管理后台为**可选组件**，默认仅绑定本机回环地址；不建议直接公网暴露。

---

## 🚀 快速运行(开发模式)

### 前置要求
- Python 3.10+（推荐 3.11，已在 3.10–3.13 测试）
- Windows 10+ / macOS 10.15+ / Linux

### 步骤

1. **安装依赖**
   ```bash
   pip install --require-hashes -r requirements.lock
   ```

   **国内用户推荐使用镜像**:
   ```bash
   pip install --require-hashes -r requirements.lock -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```
   > 若暂时无法使用哈希锁文件，可退回 `pip install -r requirements.txt`，但发布/打包请使用锁文件。

2. **启动GUI应用**
   ```bash
   python main.py
   ```

3. **或仅测试核心功能**
   ```bash
   python main.py --test-core
   ```

---

## 🧰 生产运行手册（最小集）

### 1) 启动前安全闸（fail-fast）

启动入口会在 `startup_preflight` 记录 `version/env/build_time`，并在 **production** 环境对必需密钥做强校验（缺失/长度不足会直接退出进程）。

**必需环境变量（production）**
- `ENVIRONMENT=production`
- `JWT_SECRET_KEY`：长度 `>=32`（主应用/REST API）
- `SESSION_SECRET_KEY`：长度 `>=32`（主应用/REST API）

**仅在启用对应组件时需要**
- `VCL_ADMIN_SECRET_KEY`：长度 `>=32`（Admin API）
- `VCL_API_KEYS`：API 访问密钥（逗号分隔多把，用于 REST API）

**可选/高级**
- `DEVELOPER_MODE_ENABLED=true`：显式开启开发者模式（生产默认关闭）
  - 同时需要 `DEVELOPER_SECRET_KEY`（长度 `>=32`，或通过 `DEVELOPER_SECRET_ENV` 指定变量名）
- `LOG_LEVEL=INFO|WARNING|ERROR`：生产环境最低为 `INFO`（即使配置为 `DEBUG` 也会被抬升）
- `VCL_BUILD_TIME`/`VCL_BUILD_SHA`/`VCL_BUILD_ID`：构建系统写入，用于日志与探针输出

上线前建议在目标环境执行一次配置事实校验（避免“文档写了/但实际没配”）：
```bash
python tools/validate_config.py --env production
```

### 2) 启动命令

**GUI**
```bash
ENVIRONMENT=production python main.py
```

**REST API（默认仅绑定回环）**
```bash
VCL_API_HOST=127.0.0.1 VCL_API_KEYS=change-me ENVIRONMENT=production python -m src.api.server
```
如需对外提供服务请显式设置 `VCL_API_HOST=0.0.0.0`，并结合防火墙/反向代理做访问控制；不建议直接对公网暴露。

可选：慢连接保护（防止连接长时间占用导致服务卡死）
- `VCL_API_CONN_TIMEOUT=10`：单连接 socket 超时时间（秒，默认 10）

### 3) 健康检查/就绪探针

- `GET /healthz`：轻量（配置/密钥/依赖/磁盘可写），返回 `version/build`
- `GET /readyz`：就绪（可选检查 DB/缓存；默认跳过外部依赖），返回 `version/build`
- `GET /api/health`：兼容旧接口，同样返回 `version/build`
- `GET /api/ready`：兼容就绪接口（模板/存储可用性；失败返回 503）
- `GET /metrics`：Prometheus 文本指标（默认 **需要认证**，通过 `X-API-Key`）

### 4) 每日/每周备份与恢复

**备份（ZIP + 轮转）**
```bash
# 每日：默认保留 14 份
python scripts/backup_data.py --mode daily

# 每周：默认保留 8 份
python scripts/backup_data.py --mode weekly
```
产物位于 `backups/daily/` 与 `backups/weekly/`，内部包含 `manifest.json`（版本/构建信息/文件清单）。
运行时数据目录会自动识别（`VCL_DATA_DIR` / `VCL_CONFIG_PATH` / 不可写目录重定向），
避免“备份了仓库目录，但实际数据写在用户目录”的偏差。

**恢复（默认仅解压到 restores/，不覆盖）**
```bash
python scripts/restore_backup.py backups/daily/<file>.zip

# 验证无误后可选择覆盖应用到项目目录（会覆盖同名文件）
python scripts/restore_backup.py backups/daily/<file>.zip --apply
```

安全说明：
- `restore_backup.py` 会对 zip 成员路径做校验，阻止 `../` 等路径穿越（zip-slip）。
- `--apply` **仅允许**覆盖运行时可变数据：`data/`、`user_data/`、`config.json`；其余文件会被跳过并提示，避免误覆盖源码/可执行文件。

**建议的回滚流程（最小）**
- 先停止服务/应用进程
- 使用 `restore_backup.py` 解压并核对 `manifest.json`（版本/构建号）
- 使用 `--apply` 覆盖恢复 `data/`、`user_data/`、`config.json`
- 重新启动后用 `/healthz` + `/readyz` 验证，再逐步放量

### 5) 生产日志级别（配置一致性）

项目的实际日志级别读取 `log.level` 或环境变量 `LOG_LEVEL`。
请确保生产配置中设置的是 `log.level`（而非 `monitoring.log_level`），否则不会生效。

---

## 📦 打包为可执行文件

### 打包环境要求
- Python 3.10–3.12（锁文件由 3.12 生成，推荐 3.12）
- pip 23+（支持 `--require-hashes`）
- Windows：可选 Inno Setup 6 用于生成安装包
- macOS：Xcode Command Line Tools，若需签名/公证需设置 `APPLE_DEVELOPER_ID`/`APPLE_ID` 等环境变量
- Linux：Qt 运行时依赖（如 `libxcb` 系列），详见常见问题

### 推荐：官方一键脚本（PyInstaller）
依赖会基于 `requirements.lock` 安装，入口统一为 `main.py`。

- **Windows**
  ```cmd
  build_windows.bat
  ```
  输出 `dist\VirtualChemLab\VirtualChemLab.exe`，若安装了 Inno Setup 会额外生成 `dist\VirtualChemLab-Setup-<version>.exe`。

- **macOS**
  ```bash
  chmod +x build_macos.sh
  ./build_macos.sh
  ```
  输出 `dist/VirtualChemLab.app` 与 `dist/VirtualChemLab-<version>.dmg`（若已安装 hdiutil）。

- **Linux**
  ```bash
  chmod +x build.sh
  ./build.sh
  ```
  输出 `dist/VirtualChemLab/VirtualChemLab` 以及压缩包 `VirtualChemLab_Release_v<version>.tar.gz`。

> 图标可选：Windows/Linux 使用 `assets/icons/app.ico`，macOS 使用 `assets/icons/app.icns`，缺失时脚本会回退为默认图标。

### 方案1: PyInstaller (推荐)

#### 1.1 安装打包工具
```bash
pip install --require-hashes -r requirements.lock
pip install "pyinstaller==6.3.0"
```

#### 1.2 打包为单文件
```bash
pyinstaller --onefile --windowed \
  --name VirtualChemLab \
  --add-data "assets;assets" \
  --add-data "config;config" \
  --add-data "config.json;." \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets \
  --hidden-import pymunk \
  --hidden-import numba \
  --hidden-import sqlalchemy \
  main.py
```

**Windows命令**(注意分号):
```cmd
pyinstaller --onefile --windowed ^
  --name VirtualChemLab ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "config.json;." ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import pymunk ^
  --hidden-import numba ^
  --hidden-import sqlalchemy ^
  main.py
```

#### 1.3 打包为文件夹(启动更快)
```bash
pyinstaller --windowed \
  --name VirtualChemLab \
  --add-data "assets;assets" \
  --add-data "config;config" \
  --add-data "config.json;." \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets \
  --hidden-import pymunk \
  --hidden-import numba \
  --hidden-import sqlalchemy \
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

### Q0: `pip install --require-hashes -r requirements.lock` 报 HashMismatch 或不支持的 wheel?

**A**:
- 确保使用 Python 3.12（锁文件生成版本）且 pip >= 23
- 清理缓存后重试: `pip cache purge`
- 若仍失败，可临时退回 `pip install -r requirements.txt`，但发布前务必恢复锁文件安装

### Q0.5: PyInstaller 提示找不到 `run_gui.py` 或 `VirtualChemLab.spec`?

**A**: 项目入口统一为 `main.py`，请使用仓库提供的构建脚本或上文的 PyInstaller 参数，无需旧的 spec。

### Q1: PyInstaller打包后运行报错 "Failed to execute script"?

**A**: 可能缺少数据文件,检查 `--add-data` 是否正确（特别是 `assets`、`config`、`config.json`）:
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
# 更新版本号（以 2.0.0 为例）
vim src/__init__.py    # __version__ = "2.0.0"
vim pyproject.toml     # version = "2.0.0"

# 更新CHANGELOG
vim CHANGELOG.md

# 提交
git add .
git commit -m "Release v2.0.0"
git tag v2.0.0
```

### 2. 打包

```bash
# Windows（含 Inno Setup 安装包）
build_windows.bat
# macOS（生成 .app 与 .dmg）
./build_macos.sh
# Linux（生成 onedir 与 tar.gz）
./build.sh

# 测试入口
dist/VirtualChemLab/VirtualChemLab.exe
dist/VirtualChemLab.app
```

### 3. 发布

```bash
# 推送标签
git push origin v2.0.0

# GitHub Actions 会自动使用 PyInstaller（入口 main.py、requirements.lock）生成:
#   VirtualChemLab-<version>-windows.zip
# 如需额外资产，手动在 Release 中上传 dist 目录产物
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
