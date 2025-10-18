# 多语言国际化（i18n）使用指南

## 目录

- [概述](#概述)
- [支持的语言](#支持的语言)
- [快速开始](#快速开始)
- [高级功能](#高级功能)
- [添加新语言](#添加新语言)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

## 概述

VirtualChemLab 提供了全面的多语言国际化支持，使得应用可以轻松适配不同语言和地区的用户。

### 特性

- ✅ **多语言支持**：支持中文、英语、日语、韩语、法语、德语、西班牙语等
- ✅ **动态切换**：运行时动态切换语言，无需重启应用
- ✅ **嵌套键**：支持点号分隔的嵌套键查找（如 `"ui.welcome"`）
- ✅ **格式化参数**：支持参数化翻译和字符串格式化
- ✅ **回退机制**：找不到翻译时自动回退到默认语言
- ✅ **复数形式**：支持基于数量的复数形式处理
- ✅ **RTL支持**：支持从右到左的语言（如阿拉伯语）
- ✅ **缺失检测**：自动检测并记录缺失的翻译键

## 支持的语言

| 语言代码 | 语言名称 | 完成度 | 状态 |
|---------|---------|--------|------|
| zh_CN   | 简体中文 | 100%   | ✅ 已启用 |
| en_US   | English | 100%   | ✅ 已启用 |
| ja_JP   | 日本語  | 80%    | ✅ 已启用 |
| ko_KR   | 한국어   | 80%    | ✅ 已启用 |
| fr_FR   | Français | 80%   | ✅ 已启用 |
| de_DE   | Deutsch | 80%    | ✅ 已启用 |
| es_ES   | Español | 80%    | ✅ 已启用 |
| zh_TW   | 繁體中文 | 0%     | 🚧 计划中 |
| ru_RU   | Русский | 0%     | 🚧 计划中 |
| ar_SA   | العربية | 0%     | 🚧 计划中 |

## 快速开始

### 1. 初始化 I18n

```python
from src.utils.i18n import I18n

# 使用默认配置
i18n = I18n()  # 默认中文，回退到英文

# 或自定义配置
i18n = I18n(
    i18n_dir="assets/i18n",
    default_language="en_US",
    fallback_language="zh_CN"
)
```

### 2. 基本翻译

```python
# 简单翻译
text = i18n.translate("app.title")
# 或使用简写
text = i18n.t("app.title")

# 嵌套键
welcome = i18n.t("ui.welcome")
```

### 3. 参数化翻译

```python
# 翻译文件中：
# "status.loaded_experiments": "已加载 {count} 个实验"

message = i18n.t("status.loaded_experiments", count=5)
# 输出: "已加载 5 个实验"
```

### 4. 切换语言

```python
# 切换到日语
success = i18n.set_language("ja_JP")

if success:
    print("语言切换成功")
else:
    print("语言切换失败，语言文件不存在")
```

## 高级功能

### 1. 复数形式处理

在翻译文件中定义复数形式：

```json
{
    "items_count": {
        "zero": "没有项目",
        "one": "1个项目",
        "two": "2个项目",
        "few": "{count}个项目（少量）",
        "many": "{count}个项目（很多）",
        "other": "{count}个项目"
    }
}
```

在代码中使用：

```python
# 根据数量自动选择合适的复数形式
text = i18n.t("items_count", count=0)   # "没有项目"
text = i18n.t("items_count", count=1)   # "1个项目"
text = i18n.t("items_count", count=5)   # "5个项目（很多）"
```

### 2. 获取语言信息

```python
# 获取可用语言列表
languages = i18n.get_available_languages()
# ['zh_CN', 'en_US', 'ja_JP', 'ko_KR', ...]

# 获取语言显示名称
name = i18n.get_language_name("ja_JP")          # "日本語"
native_name = i18n.get_language_name("ja_JP", native=True)  # "日本語"

# 获取文字方向
direction = i18n.get_language_direction("ar_SA")  # "rtl"
```

### 3. 检查翻译是否存在

```python
# 检查某个键是否有翻译
has_trans = i18n.has_translation("ui.welcome")

# 获取所有翻译键
all_keys = i18n.get_all_keys()

# 获取特定前缀的键
ui_keys = i18n.get_all_keys(prefix="ui")
```

### 4. 缺失翻译检测

```python
# 获取缺失的翻译键
missing = i18n.get_missing_keys()
print(f"缺失的翻译: {missing}")

# 清空缺失记录
i18n.clear_missing_keys()
```

### 5. 在 Qt 组件中使用

```python
from PySide6.QtWidgets import QLabel, QPushButton

class MyWidget(QWidget):
    def __init__(self, i18n: I18n):
        super().__init__()
        self.i18n = i18n

        # 创建组件时使用翻译
        self.label = QLabel(self.i18n.t("ui.welcome"))
        self.btn = QPushButton(self.i18n.t("ui.confirm"))

    def update_language(self):
        """更新所有文本为新语言"""
        self.label.setText(self.i18n.t("ui.welcome"))
        self.btn.setText(self.i18n.t("ui.confirm"))
```

## 添加新语言

### 步骤 1: 创建翻译文件

在 `assets/i18n/` 目录下创建新的 JSON 文件，如 `ru_RU.json`：

```json
{
    "app": {
        "title": "VirtualChemLab - Виртуальная химическая лаборатория",
        "version": "v1.0.0"
    },
    "menu": {
        "file": "Файл",
        "settings": "Настройки",
        ...
    }
}
```

### 步骤 2: 更新语言元数据

在 `src/utils/i18n.py` 的 `LANGUAGE_METADATA` 中添加：

```python
LANGUAGE_METADATA = {
    # ... 现有语言 ...
    "ru_RU": {
        "name": "Русский",
        "native_name": "Русский",
        "direction": "ltr"
    }
}
```

### 步骤 3: 更新语言配置

在 `assets/i18n/languages.json` 中添加语言配置：

```json
{
    "languages": {
        "ru_RU": {
            "name": "Русский",
            "native_name": "Русский",
            "direction": "ltr",
            "locale": "ru_RU",
            "region": "Russia",
            "iso_639_1": "ru",
            "iso_639_2": "rus",
            "enabled": true,
            "completion": 100
        }
    }
}
```

### 步骤 4: 测试新语言

```python
# 测试加载
i18n = I18n()
success = i18n.set_language("ru_RU")
print(i18n.t("app.title"))
```

## 最佳实践

### 1. 翻译键命名规范

- 使用**点号分隔**的层级结构：`category.subcategory.key`
- 使用**小写字母和下划线**：`user_manual`, `confirm_exit`
- 使用**语义化命名**：描述内容而非位置

✅ 好的命名：

```json
{
    "ui.welcome": "欢迎",
    "message.confirm_exit": "确定要退出吗？",
    "error.load_failed": "加载失败"
}
```

❌ 不好的命名：

```json
{
    "label1": "欢迎",
    "button_text": "确定",
    "msg": "失败"
}
```

### 2. 保持翻译文件同步

- 所有语言文件应该有**相同的键结构**
- 使用工具检查翻译完整性
- 为未翻译的内容保留占位符

### 3. 参数化字符串

使用参数化而非字符串拼接：

✅ 好的做法：

```json
{
    "status.loaded_experiments": "已加载 {count} 个实验"
}
```

```python
message = i18n.t("status.loaded_experiments", count=5)
```

❌ 不好的做法：

```python
message = "已加载 " + str(count) + " 个实验"
```

### 4. 处理复数

为不同数量提供合适的翻译：

```json
{
    "errors": {
        "zero": "没有错误",
        "one": "1个错误",
        "other": "{count}个错误"
    }
}
```

### 5. 提供上下文

在翻译键或注释中提供上下文信息：

```json
{
    "ui.save": "保存",
    "ui.save_tooltip": "保存当前实验进度",
    "_comment_save": "用于保存按钮的标签"
}
```

## 故障排除

### 问题 1: 翻译显示为键名

**症状**：界面显示 `"ui.welcome"` 而不是实际文本

**原因**：

- 翻译文件不存在
- 翻译键不存在
- 语言未正确加载

**解决方法**：

```python
# 检查语言是否加载成功
if not i18n.load_language("zh_CN"):
    print("语言文件加载失败")

# 检查翻译是否存在
if not i18n.has_translation("ui.welcome"):
    print("翻译键不存在")

# 查看缺失的键
print(i18n.get_missing_keys())
```

### 问题 2: 参数化翻译失败

**症状**：显示 `"已加载 {count} 个实验"` 而不是 `"已加载 5 个实验"`

**原因**：参数名不匹配

**解决方法**：

```python
# 确保参数名匹配
# 翻译文件: "已加载 {count} 个实验"
text = i18n.t("status.loaded_experiments", count=5)  # ✅ 正确
text = i18n.t("status.loaded_experiments", num=5)    # ❌ 错误
```

### 问题 3: 语言切换后UI未更新

**症状**：调用 `set_language()` 后界面没有变化

**原因**：需要手动更新UI组件

**解决方法**：

```python
def change_language(self, lang_code: str):
    """切换语言并更新UI"""
    if self.i18n.set_language(lang_code):
        # 更新所有UI文本
        self.update_ui_texts()

def update_ui_texts(self):
    """更新所有UI组件的文本"""
    self.label.setText(self.i18n.t("ui.welcome"))
    self.button.setText(self.i18n.t("ui.confirm"))
    # 更新其他组件...
```

### 问题 4: 中文或特殊字符乱码

**症状**：中文显示为乱码或问号

**原因**：文件编码问题

**解决方法**：

- 确保所有 JSON 文件使用 **UTF-8 编码**
- Python 代码中打开文件时指定编码：

```python
with open(lang_file, encoding="utf-8") as f:
    data = json.load(f)
```

## 相关资源

- [翻译文件目录](../assets/i18n/)
- [语言配置文件](../assets/i18n/languages.json)
- [I18n 类源码](../src/utils/i18n.py)
- [设置对话框源码](../src/ui/settings_dialog.py)

## 贡献翻译

我们欢迎社区贡献新语言翻译或改进现有翻译！

1. Fork 项目
2. 创建或修改语言文件
3. 测试翻译
4. 提交 Pull Request

详见 [贡献指南](../CONTRIBUTING.md)

---

**最后更新**: 2025-10-06
**版本**: v1.0.0
