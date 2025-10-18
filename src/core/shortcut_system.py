"""
快捷键系统

提供键盘快捷键管理和处理功能
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class KeyModifier(Enum):
    """按键修饰符"""

    NONE = 0
    CTRL = 1
    ALT = 2
    SHIFT = 4
    META = 8  # Windows键或Cmd键


class KeyCode(Enum):
    """按键代码"""

    # 字母键
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"  # noqa: E741
    J = "J"
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    O = "O"  # noqa: E741
    P = "P"
    Q = "Q"
    R = "R"
    S = "S"
    T = "T"
    U = "U"
    V = "V"
    W = "W"
    X = "X"
    Y = "Y"
    Z = "Z"

    # 数字键
    DIGIT_0 = "0"
    DIGIT_1 = "1"
    DIGIT_2 = "2"
    DIGIT_3 = "3"
    DIGIT_4 = "4"
    DIGIT_5 = "5"
    DIGIT_6 = "6"
    DIGIT_7 = "7"
    DIGIT_8 = "8"
    DIGIT_9 = "9"

    # 功能键
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"

    # 特殊键
    ESCAPE = "Escape"
    TAB = "Tab"
    CAPS_LOCK = "CapsLock"
    SHIFT = "Shift"
    CTRL = "Control"
    ALT = "Alt"
    META = "Meta"
    SPACE = "Space"
    ENTER = "Enter"
    BACKSPACE = "Backspace"
    DELETE = "Delete"
    INSERT = "Insert"
    HOME = "Home"
    END = "End"
    PAGE_UP = "PageUp"
    PAGE_DOWN = "PageDown"

    # 方向键
    ARROW_UP = "ArrowUp"
    ARROW_DOWN = "ArrowDown"
    ARROW_LEFT = "ArrowLeft"
    ARROW_RIGHT = "ArrowRight"

    # 符号键
    SEMICOLON = ";"
    EQUAL = "="
    COMMA = ","
    MINUS = "-"
    PERIOD = "."
    SLASH = "/"
    BACKTICK = "`"
    BRACKET_LEFT = "["
    BACKSLASH = "\\"
    BRACKET_RIGHT = "]"
    QUOTE = "'"


@dataclass
class KeyCombination:
    """按键组合"""

    key: KeyCode
    modifiers: KeyModifier = KeyModifier.NONE
    description: str | None = None

    def __str__(self) -> str:
        """字符串表示"""
        parts = []

        if self.modifiers & KeyModifier.CTRL:
            parts.append("Ctrl")
        if self.modifiers & KeyModifier.ALT:
            parts.append("Alt")
        if self.modifiers & KeyModifier.SHIFT:
            parts.append("Shift")
        if self.modifiers & KeyModifier.META:
            parts.append("Meta")

        parts.append(self.key.value)
        return "+".join(parts)

    def __hash__(self) -> int:
        """哈希值"""
        return hash((self.key, self.modifiers))

    def __eq__(self, other: Any) -> bool:
        """相等比较"""
        if not isinstance(other, KeyCombination):
            return False
        return self.key == other.key and self.modifiers == other.modifiers


@dataclass
class Shortcut:
    """快捷键定义"""

    id: str
    combination: KeyCombination
    action: Callable[[], None]
    description: str
    category: str = "general"
    enabled: bool = True
    context: str | None = None  # 上下文（如特定窗口）

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.id}: {self.combination} - {self.description}"


class IShortcutManager(ABC):
    """快捷键管理器接口"""

    @abstractmethod
    def register(self, shortcut: Shortcut) -> bool:
        """注册快捷键"""
        pass

    @abstractmethod
    def unregister(self, shortcut_id: str) -> bool:
        """注销快捷键"""
        pass

    @abstractmethod
    def handle_key_event(self, key: str, modifiers: int) -> bool:
        """处理按键事件"""
        pass

    @abstractmethod
    def get_shortcuts(self, category: str | None = None) -> list[Shortcut]:
        """获取快捷键列表"""
        pass

    @abstractmethod
    def enable_shortcut(self, shortcut_id: str) -> bool:
        """启用快捷键"""
        pass

    @abstractmethod
    def disable_shortcut(self, shortcut_id: str) -> bool:
        """禁用快捷键"""
        pass


class ShortcutManager(IShortcutManager):
    """快捷键管理器实现"""

    def __init__(self):
        self.shortcuts: dict[KeyCombination, Shortcut] = {}
        self.shortcuts_by_id: dict[str, Shortcut] = {}
        self.contexts: set[str] = set()
        self.current_context: str | None = None

    def register(self, shortcut: Shortcut) -> bool:
        """注册快捷键"""
        if shortcut.id in self.shortcuts_by_id:
            logger.warning(f"快捷键ID已存在: {shortcut.id}")
            return False

        if shortcut.combination in self.shortcuts:
            logger.warning(f"快捷键组合已存在: {shortcut.combination}")
            return False

        self.shortcuts[shortcut.combination] = shortcut
        self.shortcuts_by_id[shortcut.id] = shortcut

        if shortcut.context:
            self.contexts.add(shortcut.context)

        logger.info(f"注册快捷键: {shortcut}")
        return True

    def unregister(self, shortcut_id: str) -> bool:
        """注销快捷键"""
        if shortcut_id not in self.shortcuts_by_id:
            return False

        shortcut = self.shortcuts_by_id[shortcut_id]
        del self.shortcuts[shortcut.combination]
        del self.shortcuts_by_id[shortcut_id]

        logger.info(f"注销快捷键: {shortcut_id}")
        return True

    def handle_key_event(self, key: str, modifiers: int) -> bool:
        """处理按键事件"""
        try:
            # 解析按键
            key_code = self._parse_key(key)
            modifier_flags = self._parse_modifiers(modifiers)

            combination = KeyCombination(key_code, modifier_flags)

            # 查找匹配的快捷键
            shortcut = self.shortcuts.get(combination)
            if not shortcut or not shortcut.enabled:
                return False

            # 检查上下文
            if shortcut.context and shortcut.context != self.current_context:
                return False

            # 执行动作
            try:
                shortcut.action()
                logger.debug(f"执行快捷键: {shortcut}")
                return True
            except Exception as e:
                logger.error(f"快捷键执行错误: {shortcut.id}: {e}")
                return False

        except Exception as e:
            logger.error(f"按键事件处理错误: {e}")
            return False

    def get_shortcuts(self, category: str | None = None) -> list[Shortcut]:
        """获取快捷键列表"""
        shortcuts = list(self.shortcuts_by_id.values())

        if category:
            shortcuts = [s for s in shortcuts if s.category == category]

        return shortcuts

    def enable_shortcut(self, shortcut_id: str) -> bool:
        """启用快捷键"""
        if shortcut_id not in self.shortcuts_by_id:
            return False

        self.shortcuts_by_id[shortcut_id].enabled = True
        return True

    def disable_shortcut(self, shortcut_id: str) -> bool:
        """禁用快捷键"""
        if shortcut_id not in self.shortcuts_by_id:
            return False

        self.shortcuts_by_id[shortcut_id].enabled = False
        return True

    def set_context(self, context: str | None) -> None:
        """设置当前上下文"""
        self.current_context = context
        logger.debug(f"设置快捷键上下文: {context}")

    def _parse_key(self, key: str) -> KeyCode:
        """解析按键"""
        # 尝试直接匹配
        for key_code in KeyCode:
            if key_code.value == key:
                return key_code

        # 特殊映射
        key_mapping = {
            "Escape": KeyCode.ESCAPE,
            "Tab": KeyCode.TAB,
            "CapsLock": KeyCode.CAPS_LOCK,
            "Shift": KeyCode.SHIFT,
            "Control": KeyCode.CTRL,
            "Alt": KeyCode.ALT,
            "Meta": KeyCode.META,
            "Space": KeyCode.SPACE,
            "Enter": KeyCode.ENTER,
            "Backspace": KeyCode.BACKSPACE,
            "Delete": KeyCode.DELETE,
            "Insert": KeyCode.INSERT,
            "Home": KeyCode.HOME,
            "End": KeyCode.END,
            "PageUp": KeyCode.PAGE_UP,
            "PageDown": KeyCode.PAGE_DOWN,
            "ArrowUp": KeyCode.ARROW_UP,
            "ArrowDown": KeyCode.ARROW_DOWN,
            "ArrowLeft": KeyCode.ARROW_LEFT,
            "ArrowRight": KeyCode.ARROW_RIGHT,
        }

        if key in key_mapping:
            return key_mapping[key]

        # 默认返回字母A
        logger.warning(f"未知按键: {key}")
        return KeyCode.A

    def _parse_modifiers(self, modifiers: int) -> KeyModifier:
        """解析修饰符"""
        result = KeyModifier.NONE

        if modifiers & 0x1:  # Ctrl
            result = KeyModifier(result.value | KeyModifier.CTRL.value)
        if modifiers & 0x2:  # Alt
            result = KeyModifier(result.value | KeyModifier.ALT.value)
        if modifiers & 0x4:  # Shift
            result = KeyModifier(result.value | KeyModifier.SHIFT.value)
        if modifiers & 0x8:  # Meta
            result = KeyModifier(result.value | KeyModifier.META.value)

        return result


class ShortcutParser:
    """快捷键解析器"""

    @staticmethod
    def parse(shortcut_string: str) -> KeyCombination | None:
        """解析快捷键字符串"""
        try:
            parts = shortcut_string.split("+")
            if not parts:
                return None

            modifiers = KeyModifier.NONE
            key_str = parts[-1].strip()

            # 解析修饰符
            for part in parts[:-1]:
                part = part.strip().lower()
                if part in ["ctrl", "control"]:
                    modifiers = KeyModifier(modifiers.value | KeyModifier.CTRL.value)
                elif part in ["alt"]:
                    modifiers = KeyModifier(modifiers.value | KeyModifier.ALT.value)
                elif part in ["shift"]:
                    modifiers = KeyModifier(modifiers.value | KeyModifier.SHIFT.value)
                elif part in ["meta", "cmd", "win"]:
                    modifiers = KeyModifier(modifiers.value | KeyModifier.META.value)

            # 解析按键
            key_code = ShortcutParser._parse_key_string(key_str)
            if key_code is None:
                return None

            return KeyCombination(key_code, modifiers)

        except Exception as e:
            logger.error(f"快捷键解析错误: {shortcut_string}: {e}")
            return None

    @staticmethod
    def _parse_key_string(key_str: str) -> KeyCode | None:
        """解析按键字符串"""
        key_str = key_str.strip()

        # 直接匹配
        for key_code in KeyCode:
            if key_code.value == key_str:
                return key_code

        # 特殊映射
        key_mapping = {
            "esc": KeyCode.ESCAPE,
            "tab": KeyCode.TAB,
            "caps": KeyCode.CAPS_LOCK,
            "space": KeyCode.SPACE,
            "enter": KeyCode.ENTER,
            "return": KeyCode.ENTER,
            "backspace": KeyCode.BACKSPACE,
            "del": KeyCode.DELETE,
            "delete": KeyCode.DELETE,
            "ins": KeyCode.INSERT,
            "insert": KeyCode.INSERT,
            "home": KeyCode.HOME,
            "end": KeyCode.END,
            "pgup": KeyCode.PAGE_UP,
            "pageup": KeyCode.PAGE_UP,
            "pgdown": KeyCode.PAGE_DOWN,
            "pagedown": KeyCode.PAGE_DOWN,
            "up": KeyCode.ARROW_UP,
            "down": KeyCode.ARROW_DOWN,
            "left": KeyCode.ARROW_LEFT,
            "right": KeyCode.ARROW_RIGHT,
            ";": KeyCode.SEMICOLON,
            "=": KeyCode.EQUAL,
            ",": KeyCode.COMMA,
            "-": KeyCode.MINUS,
            ".": KeyCode.PERIOD,
            "/": KeyCode.SLASH,
            "`": KeyCode.BACKTICK,
            "[": KeyCode.BRACKET_LEFT,
            "\\": KeyCode.BACKSLASH,
            "]": KeyCode.BRACKET_RIGHT,
            "'": KeyCode.QUOTE,
        }

        if key_str.lower() in key_mapping:
            return key_mapping[key_str.lower()]

        return None


class ShortcutConfig:
    """快捷键配置"""

    def __init__(self, manager: ShortcutManager):
        self.manager = manager
        self.config_file: str | None = None

    def load_from_file(self, config_file: str) -> bool:
        """从文件加载配置"""
        try:
            import json

            with open(config_file, encoding="utf-8") as f:
                config_data = json.load(f)

            self.config_file = config_file
            return self._load_config(config_data)

        except Exception as e:
            logger.error(f"加载快捷键配置失败: {e}")
            return False

    def save_to_file(self, config_file: str) -> bool:
        """保存配置到文件"""
        try:
            import json

            config_data = self._save_config()

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.config_file = config_file
            return True

        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")
            return False

    def _load_config(self, config_data: dict[str, Any]) -> bool:
        """加载配置数据"""
        try:
            shortcuts_data = config_data.get("shortcuts", [])

            for shortcut_data in shortcuts_data:
                shortcut_id = shortcut_data.get("id")
                combination_str = shortcut_data.get("combination")
                description = shortcut_data.get("description", "")
                category = shortcut_data.get("category", "general")
                enabled = shortcut_data.get("enabled", True)
                context = shortcut_data.get("context")

                if not shortcut_id or not combination_str:
                    continue

                combination = ShortcutParser.parse(combination_str)
                if not combination:
                    continue

                # 创建虚拟动作（实际应用中需要根据ID查找真实动作）
                def create_action(action_id: str):
                    def action():
                        logger.info(f"执行快捷键动作: {action_id}")

                    return action

                shortcut = Shortcut(
                    id=shortcut_id,
                    combination=combination,
                    action=create_action(shortcut_id),
                    description=description,
                    category=category,
                    enabled=enabled,
                    context=context,
                )

                self.manager.register(shortcut)

            return True

        except Exception as e:
            logger.error(f"加载快捷键配置数据失败: {e}")
            return False

    def _save_config(self) -> dict[str, Any]:
        """保存配置数据"""
        shortcuts_data = []

        for shortcut in self.manager.get_shortcuts():
            shortcut_data = {
                "id": shortcut.id,
                "combination": str(shortcut.combination),
                "description": shortcut.description,
                "category": shortcut.category,
                "enabled": shortcut.enabled,
            }

            if shortcut.context:
                shortcut_data["context"] = shortcut.context

            shortcuts_data.append(shortcut_data)

        return {"shortcuts": shortcuts_data, "version": "1.0"}


class ShortcutHelp:
    """快捷键帮助"""

    def __init__(self, manager: ShortcutManager):
        self.manager = manager

    def generate_help_text(self, category: str | None = None) -> str:
        """生成帮助文本"""
        shortcuts = self.manager.get_shortcuts(category)

        if not shortcuts:
            return "没有可用的快捷键"

        # 按类别分组
        categories = {}
        for shortcut in shortcuts:
            if shortcut.category not in categories:
                categories[shortcut.category] = []
            categories[shortcut.category].append(shortcut)

        lines = []
        lines.append("快捷键帮助:")
        lines.append("=" * 50)

        for cat, cat_shortcuts in categories.items():
            lines.append(f"\n{cat.upper()}:")
            lines.append("-" * 20)

            for shortcut in sorted(cat_shortcuts, key=lambda x: str(x.combination)):
                status = "✓" if shortcut.enabled else "✗"
                lines.append(f"{status} {shortcut.combination:<20} - {shortcut.description}")

        return "\n".join(lines)

    def generate_html_help(self, category: str | None = None) -> str:
        """生成HTML帮助"""
        shortcuts = self.manager.get_shortcuts(category)

        if not shortcuts:
            return "<p>没有可用的快捷键</p>"

        # 按类别分组
        categories = {}
        for shortcut in shortcuts:
            if shortcut.category not in categories:
                categories[shortcut.category] = []
            categories[shortcut.category].append(shortcut)

        html_parts = []
        html_parts.append("<h2>快捷键帮助</h2>")

        for cat, cat_shortcuts in categories.items():
            html_parts.append(f"<h3>{cat}</h3>")
            html_parts.append("<table border='1' cellpadding='5' cellspacing='0'>")
            html_parts.append("<tr><th>快捷键</th><th>描述</th><th>状态</th></tr>")

            for shortcut in sorted(cat_shortcuts, key=lambda x: str(x.combination)):
                status = "启用" if shortcut.enabled else "禁用"
                html_parts.append(
                    f"<tr><td>{shortcut.combination}</td><td>{shortcut.description}</td><td>{status}</td></tr>"
                )

            html_parts.append("</table>")

        return "\n".join(html_parts)


# 全局快捷键管理器
_global_shortcut_manager = ShortcutManager()


def get_global_shortcut_manager() -> ShortcutManager:
    """获取全局快捷键管理器"""
    return _global_shortcut_manager


# 便捷函数
def register_shortcut(
    shortcut_id: str,
    combination: str | KeyCombination,
    action: Callable[[], None],
    description: str,
    category: str = "general",
    context: str | None = None,
) -> bool:
    """注册快捷键"""
    if isinstance(combination, str):
        key_combination = ShortcutParser.parse(combination)
        if not key_combination:
            return False
    else:
        key_combination = combination

    shortcut = Shortcut(
        id=shortcut_id,
        combination=key_combination,
        action=action,
        description=description,
        category=category,
        context=context,
    )

    return _global_shortcut_manager.register(shortcut)


def unregister_shortcut(shortcut_id: str) -> bool:
    """注销快捷键"""
    return _global_shortcut_manager.unregister(shortcut_id)


def handle_key_event(key: str, modifiers: int) -> bool:
    """处理按键事件"""
    return _global_shortcut_manager.handle_key_event(key, modifiers)


# 预定义快捷键
class DefaultShortcuts:
    """默认快捷键"""

    # 文件操作
    NEW = "Ctrl+N"
    OPEN = "Ctrl+O"
    SAVE = "Ctrl+S"
    SAVE_AS = "Ctrl+Shift+S"
    CLOSE = "Ctrl+W"
    EXIT = "Ctrl+Q"

    # 编辑操作
    UNDO = "Ctrl+Z"
    REDO = "Ctrl+Y"
    CUT = "Ctrl+X"
    COPY = "Ctrl+C"
    PASTE = "Ctrl+V"
    SELECT_ALL = "Ctrl+A"
    FIND = "Ctrl+F"
    REPLACE = "Ctrl+H"

    # 视图操作
    ZOOM_IN = "Ctrl+Plus"
    ZOOM_OUT = "Ctrl+Minus"
    ZOOM_RESET = "Ctrl+0"
    FULLSCREEN = "F11"

    # 实验操作
    START_EXPERIMENT = "F5"
    PAUSE_EXPERIMENT = "F6"
    STOP_EXPERIMENT = "F7"
    RESET_EXPERIMENT = "F8"

    # 帮助
    HELP = "F1"
    ABOUT = "Ctrl+Shift+A"


# 快捷键装饰器
def shortcut(combination: str, description: str, category: str = "general", context: str | None = None):
    """快捷键装饰器"""

    def decorator(func: Callable[[], None]) -> Callable[[], None]:
        shortcut_id = f"{func.__module__}.{func.__name__}"
        register_shortcut(shortcut_id, combination, func, description, category, context)
        return func

    return decorator


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 快捷键系统演示 ===\n")

    # 1. 基础快捷键注册
    logger.info("1. 基础快捷键注册:")

    def new_file():
        logger.info("新建文件")

    def open_file():
        logger.info("打开文件")

    def save_file():
        logger.info("保存文件")

    register_shortcut("file.new", "Ctrl+N", new_file, "新建文件", "file")
    register_shortcut("file.open", "Ctrl+O", open_file, "打开文件", "file")
    register_shortcut("file.save", "Ctrl+S", save_file, "保存文件", "file")

    logger.info("")

    # 2. 快捷键装饰器
    logger.info("2. 快捷键装饰器:")

    @shortcut("F5", "开始实验", "experiment")
    def start_experiment():
        logger.info("开始实验")

    @shortcut("F6", "暂停实验", "experiment")
    def pause_experiment():
        logger.info("暂停实验")

    logger.info("")

    # 3. 快捷键解析
    logger.info("3. 快捷键解析:")

    test_combinations = ["Ctrl+N", "Ctrl+Shift+S", "Alt+F4", "F1", "Ctrl+Plus", "Ctrl+Minus"]

    for combo_str in test_combinations:
        combination = ShortcutParser.parse(combo_str)
        if combination:
            logger.info(f"解析成功: {combo_str} -> {combination}")
        else:
            logger.info(f"解析失败: {combo_str}")

    logger.info("")

    # 4. 帮助生成
    logger.info("4. 帮助生成:")

    help_generator = ShortcutHelp(_global_shortcut_manager)
    help_text = help_generator.generate_help_text()
    logger.info(f"帮助文本:\n{help_text}")

    logger.info("")

    # 5. 配置保存和加载
    logger.info("5. 配置保存和加载:")

    config = ShortcutConfig(_global_shortcut_manager)

    # 保存配置
    if config.save_to_file("shortcuts.json"):
        logger.info("快捷键配置保存成功")

    # 加载配置
    if config.load_from_file("shortcuts.json"):
        logger.info("快捷键配置加载成功")

    logger.info("快捷键系统演示完成！")
