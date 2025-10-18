"""
操作历史和撤销/重做系统
提供完整的操作历史记录和撤销重做功能
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ActionCategory(Enum):
    """操作类别"""

    EXPERIMENT = "experiment"  # 实验操作
    DATA_ENTRY = "data_entry"  # 数据输入
    SETTING = "setting"  # 设置更改
    FILE = "file"  # 文件操作
    VIEW = "view"  # 视图操作


@dataclass
class Action:
    """操作记录"""

    id: str
    category: ActionCategory
    name: str
    description: str
    timestamp: datetime
    undo_callback: Callable | None = None
    redo_callback: Callable | None = None
    data: dict[str, Any] | None = None

    def can_undo(self) -> bool:
        """是否可以撤销"""
        return self.undo_callback is not None

    def can_redo(self) -> bool:
        """是否可以重做"""
        return self.redo_callback is not None


class ActionHistory(QObject):
    """操作历史管理器"""

    # 信号
    action_added = Signal(Action)
    action_undone = Signal(Action)
    action_redone = Signal(Action)
    history_cleared = Signal()
    history_changed = Signal()

    def __init__(self, max_history: int = 100):
        super().__init__()
        self.max_history = max_history
        self.undo_stack: list[Action] = []
        self.redo_stack: list[Action] = []
        self.action_counter = 0

        logger.info(f"操作历史管理器初始化完成 (最多{max_history}条记录)")

    def add_action(
        self,
        category: ActionCategory,
        name: str,
        description: str,
        undo_callback: Callable | None = None,
        redo_callback: Callable | None = None,
        data: dict[str, Any] | None = None,
    ) -> str:
        """添加操作

        Args:
            category: 操作类别
            name: 操作名称
            description: 操作描述
            undo_callback: 撤销回调
            redo_callback: 重做回调
            data: 附加数据

        Returns:
            操作ID
        """
        self.action_counter += 1
        action_id = f"action_{self.action_counter}"

        action = Action(
            id=action_id,
            category=category,
            name=name,
            description=description,
            timestamp=datetime.now(),
            undo_callback=undo_callback,
            redo_callback=redo_callback,
            data=data or {},
        )

        # 添加到撤销栈
        self.undo_stack.append(action)

        # 清空重做栈
        self.redo_stack.clear()

        # 限制历史记录数量
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

        # 发送信号
        self.action_added.emit(action)
        self.history_changed.emit()

        logger.debug(f"添加操作: {name}")

        return action_id

    def can_undo(self) -> bool:
        """是否可以撤销"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """是否可以重做"""
        return len(self.redo_stack) > 0

    def undo(self) -> bool:
        """撤销操作

        Returns:
            是否成功
        """
        if not self.can_undo():
            logger.warning("无法撤销：撤销栈为空")
            return False

        action = self.undo_stack.pop()

        if not action.can_undo():
            logger.warning(f"操作不支持撤销: {action.name}")
            return False

        try:
            # 执行撤销
            if action.undo_callback:
                action.undo_callback()

            # 移到重做栈
            self.redo_stack.append(action)

            # 发送信号
            self.action_undone.emit(action)
            self.history_changed.emit()

            logger.info(f"撤销操作: {action.name}")
            return True

        except Exception as e:
            logger.error(f"撤销操作失败 {action.name}: {e}")
            # 恢复到撤销栈
            self.undo_stack.append(action)
            return False

    def redo(self) -> bool:
        """重做操作

        Returns:
            是否成功
        """
        if not self.can_redo():
            logger.warning("无法重做：重做栈为空")
            return False

        action = self.redo_stack.pop()

        if not action.can_redo():
            logger.warning(f"操作不支持重做: {action.name}")
            return False

        try:
            # 执行重做
            if action.redo_callback:
                action.redo_callback()

            # 移到撤销栈
            self.undo_stack.append(action)

            # 发送信号
            self.action_redone.emit(action)
            self.history_changed.emit()

            logger.info(f"重做操作: {action.name}")
            return True

        except Exception as e:
            logger.error(f"重做操作失败 {action.name}: {e}")
            # 恢复到重做栈
            self.redo_stack.append(action)
            return False

    def get_undo_description(self) -> str:
        """获取撤销操作描述"""
        if self.can_undo():
            return self.undo_stack[-1].description
        return ""

    def get_redo_description(self) -> str:
        """获取重做操作描述"""
        if self.can_redo():
            return self.redo_stack[-1].description
        return ""

    def get_history(self, limit: int = 50) -> list[Action]:
        """获取历史记录

        Args:
            limit: 最多返回的记录数

        Returns:
            操作列表（从新到旧）
        """
        return self.undo_stack[-limit:][::-1]

    def clear_history(self):
        """清除历史记录"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.history_cleared.emit()
        self.history_changed.emit()
        logger.info("操作历史已清除")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "total_actions": len(self.undo_stack),
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "undo_count": len(self.undo_stack),
            "redo_count": len(self.redo_stack),
        }


class UndoRedoHelper:
    """撤销重做辅助类"""

    @staticmethod
    def create_value_change_action(
        history: ActionHistory, name: str, setter: Callable[[Any], None], old_value: Any, new_value: Any
    ) -> str:
        """创建值更改操作

        Args:
            history: 操作历史管理器
            name: 操作名称
            setter: 值设置函数
            old_value: 旧值
            new_value: 新值

        Returns:
            操作ID
        """

        def undo():
            setter(old_value)

        def redo():
            setter(new_value)

        return history.add_action(
            category=ActionCategory.DATA_ENTRY,
            name=name,
            description=f"将{name}从 {old_value} 更改为 {new_value}",
            undo_callback=undo,
            redo_callback=redo,
            data={"old_value": old_value, "new_value": new_value},
        )

    @staticmethod
    def create_list_add_action(history: ActionHistory, name: str, list_obj: list, item: Any, index: int = -1) -> str:
        """创建列表添加操作

        Args:
            history: 操作历史管理器
            name: 操作名称
            list_obj: 列表对象
            item: 添加的项
            index: 添加位置（-1表示末尾）

        Returns:
            操作ID
        """

        def undo():
            if item in list_obj:
                list_obj.remove(item)

        def redo():
            if index == -1:
                list_obj.append(item)
            else:
                list_obj.insert(index, item)

        return history.add_action(
            category=ActionCategory.DATA_ENTRY,
            name=name,
            description=f"添加项到{name}",
            undo_callback=undo,
            redo_callback=redo,
            data={"item": item, "index": index},
        )

    @staticmethod
    def create_list_remove_action(
        history: ActionHistory, name: str, list_obj: list, item: Any, index: int | None = None
    ) -> str:
        """创建列表移除操作

        Args:
            history: 操作历史管理器
            name: 操作名称
            list_obj: 列表对象
            item: 移除的项
            index: 原来的位置

        Returns:
            操作ID
        """
        if index is None:
            index = list_obj.index(item) if item in list_obj else -1

        def undo():
            if index >= 0:
                list_obj.insert(index, item)
            else:
                list_obj.append(item)

        def redo():
            if item in list_obj:
                list_obj.remove(item)

        return history.add_action(
            category=ActionCategory.DATA_ENTRY,
            name=name,
            description=f"从{name}移除项",
            undo_callback=undo,
            redo_callback=redo,
            data={"item": item, "index": index},
        )

    @staticmethod
    def create_dict_change_action(
        history: ActionHistory, name: str, dict_obj: dict, key: Any, old_value: Any, new_value: Any
    ) -> str:
        """创建字典更改操作

        Args:
            history: 操作历史管理器
            name: 操作名称
            dict_obj: 字典对象
            key: 键
            old_value: 旧值
            new_value: 新值

        Returns:
            操作ID
        """

        def undo():
            if old_value is None:
                dict_obj.pop(key, None)
            else:
                dict_obj[key] = old_value

        def redo():
            if new_value is None:
                dict_obj.pop(key, None)
            else:
                dict_obj[key] = new_value

        return history.add_action(
            category=ActionCategory.DATA_ENTRY,
            name=name,
            description=f"更改{name}[{key}]",
            undo_callback=undo,
            redo_callback=redo,
            data={"key": key, "old_value": old_value, "new_value": new_value},
        )


# 全局实例
_action_history: ActionHistory | None = None


def get_action_history() -> ActionHistory:
    """获取全局操作历史管理器"""
    global _action_history
    if _action_history is None:
        _action_history = ActionHistory()
    return _action_history
