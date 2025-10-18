# 国际化快速参考

## 🚀 快速开始

### 基本使用

```python
from src.utils.i18n import I18n

# 创建实例
i18n = I18n()

# 获取翻译
text = i18n.t("ui.confirm")  # "确认" (中文) 或 "Confirm" (英文)

# 切换语言
i18n.set_language("en_US")  # 切换到英文
```

## 📝 常用翻译键

### 按钮文本

| 键 | 中文 | 英文 |
|---|------|------|
| `ui.confirm` | 确认 | Confirm |
| `ui.cancel` | 取消 | Cancel |
| `ui.close` | 关闭 | Close |
| `ui.save` | 保存 | Save |
| `ui.delete` | 删除 | Delete |
| `ui.submit` | 提交 | Submit |
| `ui.next` | 下一步 | Next |
| `ui.previous` | 上一步 | Previous |
| `ui.retry` | 重试 | Retry |

### 消息提示

| 键 | 中文 | 英文 |
|---|------|------|
| `message.loading` | 加载中... | Loading... |
| `message.saving` | 保存中... | Saving... |
| `message.success` | 成功 | Success |
| `message.error` | 错误 | Error |
| `ui.info` | 提示 | Info |
| `ui.warning` | 警告 | Warning |

### 错误消息

| 键 | 使用示例 |
|---|----------|
| `error.file_not_found` | `i18n.t("error.file_not_found", file="config.json")` |
| `error.permission_denied` | `i18n.t("error.permission_denied")` |
| `error.network_error` | `i18n.t("error.network_error")` |
| `error.save_failed` | `i18n.t("error.save_failed", error=str(e))` |

## 🎨 在UI中使用

### PyQt/PySide6 组件

```python
from PySide6.QtWidgets import QPushButton, QMessageBox

# 按钮
btn = QPushButton(self.i18n.t("ui.confirm"))

# 消息框
QMessageBox.information(
    self,
    self.i18n.t("ui.info"),
    self.i18n.t("settings.save_success")
)

# 窗口标题
self.setWindowTitle(self.i18n.t("settings.title"))
```

### 参数化翻译

```python
# 带参数的翻译
score_msg = self.i18n.t("ui.final_score_message", score=95)
# 结果: "恭喜!您的最终得分是: 95"

progress = self.i18n.t("ui.progress_format", percent=75, current=3, total=4)
# 结果: "进度: 75% (3/4)"
```

## 🌍 支持的语言

| 代码 | 语言 | 完成度 |
|------|------|--------|
| `zh_CN` | 简体中文 | 100% ✅ |
| `en_US` | English | 100% ✅ |
| `ja_JP` | 日本語 | 100% ✅ |
| `ko_KR` | 한국어 | 100% ✅ |
| `fr_FR` | Français | 100% ✅ |
| `de_DE` | Deutsch | 100% ✅ |
| `es_ES` | Español | 100% ✅ |

## 🔧 实用函数

### 获取可用语言

```python
languages = i18n.get_available_languages()
# ['de_DE', 'en_US', 'es_ES', 'fr_FR', 'ja_JP', 'ko_KR', 'zh_CN']
```

### 获取语言名称

```python
name = i18n.get_language_name("zh_CN")  # "简体中文"
native = i18n.get_language_name("ja_JP", native=True)  # "日本語"
```

### 检查翻译是否存在

```python
if i18n.has_translation("ui.confirm"):
    text = i18n.t("ui.confirm")
```

## 📂 文件位置

```
assets/i18n/
├── zh_CN.json      # 简体中文
├── en_US.json      # 英文
├── ja_JP.json      # 日文
├── ko_KR.json      # 韩文
├── fr_FR.json      # 法文
├── de_DE.json      # 德文
├── es_ES.json      # 西班牙文
└── languages.json  # 语言元数据
```

## ✅ 验证工具

### 验证翻译完整性

```bash
python tools/i18n_validator.py
```

### 运行测试

```bash
python -m pytest tests/test_i18n_integration.py -v
```

## 💡 技巧

### 1. 使用UI文案管理器

```python
from src.ui.ui_text_manager import UITextManager

ui_mgr = UITextManager(i18n)
welcome_texts = ui_mgr.get_welcome_texts()
```

### 2. 语言切换后更新UI

```python
def on_language_changed(self, lang_code):
    self.i18n.set_language(lang_code)
    self.update_ui_texts()  # 刷新所有文本

def update_ui_texts(self):
    self.btn_confirm.setText(self.i18n.t("ui.confirm"))
    self.btn_cancel.setText(self.i18n.t("ui.cancel"))
    # ... 更新其他文本
```

### 3. 在设置对话框中显示语言列表

```python
for lang_code in i18n.get_available_languages():
    lang_name = i18n.get_language_name(lang_code, native=True)
    self.language_combo.addItem(lang_name, lang_code)
```

## ⚠️ 注意事项

1. **不要硬编码文本** - 始终使用翻译键
2. **测试所有语言** - 确保UI在不同语言下正常显示
3. **提供足够的上下文** - 使用嵌套键组织翻译
4. **处理参数** - 使用 `{param}` 占位符进行参数化翻译

## 🔗 相关文档

- [完整使用指南](./I18N_GUIDE.md)
- [验证报告](./I18N_VERIFICATION_REPORT.md)
- [实现总结](./I18N_IMPLEMENTATION_SUMMARY.md)

