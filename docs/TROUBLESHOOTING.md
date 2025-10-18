# VirtualChemLab 故障排除指南

**版本**: 2.0.0  
**最后更新**: 2025-10-07

---

## 📋 目录

- [常见问题](#常见问题)
- [安装问题](#安装问题)
- [启动问题](#启动问题)
- [实验执行问题](#实验执行问题)
- [UI/界面问题](#ui界面问题)
- [性能问题](#性能问题)
- [数据存储问题](#数据存储问题)
- [插件问题](#插件问题)
- [许可证问题](#许可证问题)
- [调试技巧](#调试技巧)

---

## 常见问题

### Q: 如何查看系统日志？

**解答**:

日志文件位于 `logs/` 目录：

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看性能日志
tail -f logs/performance.log
```

日志级别配置：

```python
# config.json
{
    "logging": {
        "level": "DEBUG",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "file": "logs/app.log",
        "console": true
    }
}
```

### Q: 如何重置应用配置？

**解答**:

```bash
# 备份当前配置
cp config.json config.json.backup

# 恢复默认配置
cp config/base.json config.json

# 或使用工具重置
python tools/reset_config.py
```

### Q: 如何清理缓存？

**解答**:

```bash
# 清理所有缓存
python tools/clear_cache.py --all

# 只清理实验缓存
python tools/clear_cache.py --experiments

# 只清理UI缓存
python tools/clear_cache.py --ui
```

---

## 安装问题

### 问题：pip install 失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement...
```

**原因**:
- Python版本不兼容
- pip版本过旧
- 网络连接问题

**解决方案**:

```bash
# 1. 检查Python版本（需要3.8+）
python --version

# 2. 升级pip
python -m pip install --upgrade pip

# 3. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 分步安装
pip install PySide6
pip install pydantic
pip install -r requirements.txt
```

### 问题：PySide6 安装失败

**症状**:
```
ERROR: Failed building wheel for PySide6
```

**解决方案**:

**Windows**:
```bash
# 安装Visual C++ Build Tools
# 下载: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 或使用预编译包
pip install PySide6-Essentials
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip
sudo apt-get install qt6-base-dev

# Fedora
sudo dnf install python3-devel
sudo dnf install qt6-qtbase-devel
```

**macOS**:
```bash
# 安装Xcode命令行工具
xcode-select --install

# 或使用Homebrew
brew install python@3.11
```

### 问题：依赖冲突

**症状**:
```
ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案**:

```bash
# 1. 创建新的虚拟环境
python -m venv venv_new
source venv_new/bin/activate  # Linux/macOS
venv_new\Scripts\activate  # Windows

# 2. 升级pip和setuptools
pip install --upgrade pip setuptools wheel

# 3. 安装依赖
pip install -r requirements.txt

# 4. 如果仍有问题，使用conda
conda create -n virtualchemlab python=3.11
conda activate virtualchemlab
pip install -r requirements.txt
```

---

## 启动问题

### 问题：应用无法启动

**症状**:
```
ModuleNotFoundError: No module named 'src'
```

**解决方案**:

```bash
# 1. 确保在项目根目录
cd /path/to/VirtualChemLab

# 2. 检查PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%cd%  # Windows

# 3. 使用-m参数运行
python -m src.main

# 4. 或直接运行main.py
python main.py
```

### 问题：配置文件错误

**症状**:
```
ConfigError: Invalid configuration file
```

**解决方案**:

```bash
# 1. 验证配置文件
python -c "import json; json.load(open('config.json'))"

# 2. 查看具体错误
python tools/validate_config.py

# 3. 恢复默认配置
python tools/reset_config.py --backup
```

### 问题：端口被占用

**症状**:
```
OSError: [Errno 48] Address already in use
```

**解决方案**:

```bash
# 1. 查找占用端口的进程
# Linux/macOS
lsof -i :8000
# Windows
netstat -ano | findstr :8000

# 2. 终止进程
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows

# 3. 或更改端口
python main.py --port 8001
```

### 问题：GUI无法显示

**症状**:
- 窗口不显示
- 黑屏
- 崩溃

**解决方案**:

```bash
# 1. 检查显示服务器（Linux）
echo $DISPLAY
export DISPLAY=:0

# 2. 检查Qt平台插件
export QT_DEBUG_PLUGINS=1
python main.py

# 3. 尝试不同的Qt平台
export QT_QPA_PLATFORM=xcb  # Linux
python main.py

# 4. 检查OpenGL支持
export QT_XCB_GL_INTEGRATION=xcb_egl
```

---

## 实验执行问题

### 问题：实验无法加载

**症状**:
```
ExperimentError: Failed to load experiment template
```

**解决方案**:

```bash
# 1. 验证模板文件
python tools/validate_template.py assets/templates/titration.yaml

# 2. 检查文件权限
ls -l assets/templates/

# 3. 检查YAML语法
python -c "import yaml; yaml.safe_load(open('assets/templates/titration.yaml'))"

# 4. 使用示例模板
cp assets/templates/example.yaml assets/templates/my_template.yaml
```

### 问题：步骤验证失败

**症状**:
```
ValidationError: Step validation failed
```

**解决方案**:

```python
# 1. 启用调试模式
controller = ExperimentController(
    template=template,
    user_id="user123",
    debug=True  # 显示详细错误
)

# 2. 查看验证规则
step = template.steps[0]
print(f"验证规则: {step.checkpoints}")

# 3. 检查输入数据格式
from src.core.rule_validator import RuleValidator

validator = RuleValidator()
result = validator.validate(step, input_data)
print(f"验证结果: {result}")
```

### 问题：实验状态丢失

**症状**:
- 实验进度不保存
- 重启后数据丢失

**解决方案**:

```python
# 1. 检查自动保存配置
controller = ExperimentController(
    template=template,
    user_id="user123",
    enable_auto_save=True,  # 确保启用
    auto_save_interval=30  # 30秒自动保存
)

# 2. 手动保存状态
state = controller.get_state()
with open('experiment_state.json', 'w') as f:
    json.dump(state, f)

# 3. 恢复状态
with open('experiment_state.json', 'r') as f:
    state = json.load(f)
controller.restore_state(state)

# 4. 检查存储权限
import os
print(os.access('data/experiment_states/', os.W_OK))
```

### 问题：曲线生成错误

**症状**:
```
CurveGenerationError: Failed to generate curve
```

**解决方案**:

```python
# 1. 检查曲线参数
from src.core.curve_generator import CurveGenerator

generator = CurveGenerator()

# 查看支持的曲线类型
print(generator.supported_types)

# 2. 验证参数
params = {
    "curve_type": "titration",
    "initial_ph": 3.0,
    "final_ph": 11.0,
    "equivalence_point": 25.0
}

curve_data = generator.generate(params)

# 3. 使用默认参数
curve_data = generator.generate_default("titration")
```

---

## UI/界面问题

### 问题：界面显示异常

**症状**:
- 控件重叠
- 布局错乱
- 字体过小/过大

**解决方案**:

```python
# 1. 重置UI配置
from src.ui.settings_dialog import SettingsDialog

settings = SettingsDialog()
settings.reset_to_defaults()

# 2. 调整DPI缩放
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1.0"

# 3. 强制重绘
main_window.update()
main_window.repaint()

# 4. 检查样式表
print(main_window.styleSheet())
```

### 问题：主题切换失败

**症状**:
- 主题不生效
- 颜色显示错误

**解决方案**:

```python
# 1. 检查主题文件
from src.ui.customization.theme_manager import ThemeManager

theme_mgr = ThemeManager()
print(theme_mgr.available_themes())

# 2. 应用主题
theme_mgr.apply_theme("dark")

# 3. 重新加载样式
qss_file = "assets/themes/dark.qss"
with open(qss_file, 'r') as f:
    app.setStyleSheet(f.read())

# 4. 清除缓存的样式
QApplication.instance().setStyleSheet("")
```

### 问题：动画卡顿

**症状**:
- 动画不流畅
- 粒子效果延迟

**解决方案**:

```python
# 1. 降低粒子数量
from src.ui.particle_system import ParticleSystem

particle_system = ParticleSystem(
    max_particles=50,  # 减少数量
    update_interval=33  # 30 FPS
)

# 2. 禁用复杂效果
settings = {
    "enable_particles": False,
    "enable_shadows": False,
    "enable_blur": False
}

# 3. 使用硬件加速
import os
os.environ["QT_OPENGL"] = "desktop"

# 4. 优化刷新率
timer = QTimer()
timer.setInterval(16)  # 60 FPS
```

---

## 性能问题

### 问题：启动速度慢

**症状**:
- 启动需要10秒以上
- 初始化时间长

**解决方案**:

```bash
# 1. 使用快速启动模式
python main.py --fast-start

# 2. 启用启动优化
python main.py --optimize-startup

# 3. 分析启动性能
python tools/profile_startup.py

# 4. 禁用不必要的插件
# config.json
{
    "plugins": {
        "auto_load": false,
        "enabled": ["essential_only"]
    }
}
```

### 问题：内存占用高

**症状**:
- 内存使用超过500MB
- 内存持续增长

**解决方案**:

```python
# 1. 启用内存监控
from src.core.memory_manager import MemoryManager

memory_mgr = MemoryManager(
    max_memory_mb=500,
    auto_cleanup=True
)

# 2. 手动清理
memory_mgr.cleanup()

# 3. 分析内存使用
import tracemalloc
tracemalloc.start()

# ... 运行代码 ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)

# 4. 使用对象池
from src.utils.object_pool import ObjectPool

pool = ObjectPool(max_size=100)
```

### 问题：CPU占用高

**症状**:
- CPU使用率超过50%
- 风扇高速运转

**解决方案**:

```python
# 1. 降低刷新频率
QTimer.setInterval(50)  # 从16ms提高到50ms (20 FPS)

# 2. 异步处理
import asyncio

async def heavy_task():
    await asyncio.sleep(0.1)
    # 处理任务
    
asyncio.run(heavy_task())

# 3. 使用线程池
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=2) as executor:
    future = executor.submit(heavy_computation)
    result = future.result()

# 4. 启用缓存
from src.core.smart_cache import SmartCache

cache = SmartCache(max_size=1000)
result = cache.get_or_compute(key, expensive_function)
```

---

## 数据存储问题

### 问题：数据保存失败

**症状**:
```
StorageError: Failed to save data
```

**解决方案**:

```python
# 1. 检查磁盘空间
import shutil
stat = shutil.disk_usage('/')
print(f"可用空间: {stat.free / (1024**3):.2f} GB")

# 2. 检查文件权限
import os
data_dir = 'data/experiments'
print(f"可写: {os.access(data_dir, os.W_OK)}")

# 3. 创建目录
os.makedirs(data_dir, exist_ok=True)

# 4. 使用事务
from src.core.storage import JSONStore

storage = JSONStore('data/experiments')
with storage.transaction() as tx:
    tx.save('exp123', data)
```

### 问题：数据损坏

**症状**:
```
JSONDecodeError: Expecting value
```

**解决方案**:

```bash
# 1. 恢复备份
python tools/restore_backup.py --latest

# 2. 验证数据文件
python tools/validate_data.py data/experiments/

# 3. 修复损坏的文件
python tools/repair_data.py data/experiments/exp123.json

# 4. 启用自动备份
# config.json
{
    "storage": {
        "auto_backup": true,
        "backup_interval": 3600,  # 1小时
        "keep_backups": 10
    }
}
```

### 问题：数据迁移失败

**症状**:
- 版本升级后数据不兼容
- 导入旧数据失败

**解决方案**:

```bash
# 1. 使用迁移工具
python tools/migrate_data.py --from v1.0 --to v2.0

# 2. 查看迁移日志
cat logs/migration.log

# 3. 回滚迁移
python tools/migrate_data.py --rollback

# 4. 手动迁移
python tools/convert_data_format.py old_format.json new_format.json
```

---

## 插件问题

### 问题：插件加载失败

**症状**:
```
PluginError: Failed to load plugin 'pdf_export'
```

**解决方案**:

```python
# 1. 检查插件依赖
from src.core.plugin_system import PluginManager

plugin_mgr = PluginManager()
print(plugin_mgr.check_dependencies('pdf_export'))

# 2. 安装缺失的依赖
pip install reportlab

# 3. 使用Fallback
if not plugin_mgr.is_available('pdf_export'):
    # 使用备用方案
    export_as_html(data)

# 4. 查看详细错误
plugin_mgr.load_plugin('pdf_export', debug=True)
```

### 问题：插件冲突

**症状**:
- 两个插件无法同时使用
- 功能异常

**解决方案**:

```python
# 1. 检查插件兼容性
conflicts = plugin_mgr.check_conflicts(['plugin_a', 'plugin_b'])
print(f"冲突: {conflicts}")

# 2. 禁用冲突插件
plugin_mgr.disable_plugin('plugin_a')

# 3. 使用插件优先级
plugin_mgr.set_priority('plugin_b', priority=10)

# 4. 隔离插件环境
plugin_mgr.isolate_plugin('plugin_a')
```

---

## 许可证问题

### 问题：许可证验证失败

**症状**:
```
LicenseError: Invalid license key
```

**解决方案**:

```bash
# 1. 检查许可证文件
cat data/licenses/license.key

# 2. 验证许可证
python tools/verify_license.py

# 3. 重新激活
python tools/activate_license.py --key YOUR_LICENSE_KEY

# 4. 查看许可证信息
python tools/license_info.py
```

### 问题：设备限制

**症状**:
```
LicenseError: Maximum device limit reached
```

**解决方案**:

```bash
# 1. 查看已绑定设备
python tools/list_devices.py

# 2. 解绑旧设备
python tools/unbind_device.py --device-id DEVICE_ID

# 3. 重新绑定当前设备
python tools/bind_device.py

# 4. 购买更多设备授权
# 访问: https://virtualchemlab.com/upgrade
```

---

## 调试技巧

### 启用调试模式

```bash
# 方式1: 命令行参数
python main.py --debug

# 方式2: 环境变量
export DEBUG=1
python main.py

# 方式3: 配置文件
# config.json
{
    "debug": true,
    "verbose": true
}
```

### 使用开发者控制台

```python
# 1. 启动应用
python main.py

# 2. 按Ctrl+Shift+D打开开发者控制台

# 3. 在控制台执行Python代码
>>> print(main_window.experiment_controller.state)
>>> main_window.experiment_controller.reset()

# 4. 查看变量
>>> locals()
>>> globals()
```

### 性能分析

```bash
# 1. CPU性能分析
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats

# 2. 内存分析
python -m memory_profiler main.py

# 3. 可视化分析
pip install snakeviz
snakeviz profile.stats
```

### 日志分析

```python
# 1. 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. 添加自定义日志
logger = logging.getLogger(__name__)
logger.debug(f"变量值: {variable}")

# 3. 日志过滤
import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 4. 日志格式化
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

### 网络调试

```bash
# 1. 查看API请求
export DEBUG_API=1
python main.py

# 2. 使用代理
export HTTP_PROXY=http://127.0.0.1:8888
export HTTPS_PROXY=http://127.0.0.1:8888

# 3. 抓包分析
# 使用Wireshark或Charles
```

---

## 获取帮助

### 在线资源

1. **官方文档**: https://docs.virtualchemlab.com
2. **GitHub Issues**: https://github.com/virtualchemlab/issues
3. **社区论坛**: https://forum.virtualchemlab.com
4. **Stack Overflow**: 标签 `virtualchemlab`

### 提交Bug报告

请包含以下信息：

```markdown
**环境信息**:
- OS: Windows 10 / macOS 12 / Ubuntu 22.04
- Python版本: 3.11.0
- VirtualChemLab版本: 2.0.0

**问题描述**:
简要描述问题

**复现步骤**:
1. 启动应用
2. 点击...
3. 看到错误...

**期望行为**:
应该...

**实际行为**:
但实际...

**日志**:
```
粘贴相关日志
```

**截图**:
如果适用，添加截图
```

### 联系支持

- **邮箱**: support@virtualchemlab.com
- **企业支持**: enterprise@virtualchemlab.com
- **紧急热线**: +86-xxx-xxxx-xxxx

---

## 附录

### 常用命令

```bash
# 启动相关
python main.py                    # 标准启动
python main.py --debug           # 调试模式
python main.py --fast-start      # 快速启动
python main.py --safe-mode       # 安全模式

# 工具命令
python tools/validate_config.py  # 验证配置
python tools/clear_cache.py      # 清理缓存
python tools/reset_config.py     # 重置配置
python tools/migrate_data.py     # 数据迁移

# 开发命令
pytest                           # 运行测试
black src tests                  # 格式化代码
ruff check src tests            # 代码检查
mypy src                        # 类型检查
```

### 配置文件位置

```
config.json                      # 主配置文件
config/development.json          # 开发环境配置
config/production.json           # 生产环境配置
config/test.json                # 测试环境配置
.env                            # 环境变量
```

### 重要文件位置

```
logs/                           # 日志目录
data/                          # 数据目录
backups/                       # 备份目录
data/licenses/                 # 许可证目录
data/experiments/              # 实验数据
data/users/                    # 用户数据
```

---

**更新历史**:
- 2025-10-07: 初始版本，包含常见问题和解决方案

---

💡 **提示**: 遇到问题先查看日志，90%的问题都能从日志中找到线索。


