"""
工具提示增强器
自动为控件添加丰富的工具提示和帮助文本
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolTip,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TooltipEnhancer:
    """工具提示增强器"""

    # 预定义的工具提示模板
    TOOLTIP_TEMPLATES = {
        # 按钮类
        "start_experiment": "开始新的实验\n点击后将打开实验选择界面",
        "pause_experiment": "暂停当前实验\n可以随时恢复继续",
        "stop_experiment": "停止实验\n将结束当前实验并保存数据",
        "save": "保存当前进度\n实验数据将被保存到本地",
        "load": "加载已保存的实验\n从本地恢复之前的实验进度",
        "export": "导出实验数据\n支持多种格式：PDF、CSV、JSON",
        "import": "导入实验数据\n从文件导入实验配置或数据",
        "settings": "打开设置\n配置应用程序的各项参数",
        "help": "获取帮助\n查看用户手册和常见问题",
        "about": "关于\n查看应用程序信息和版本",
        # 实验操作类
        "add_reagent": "添加试剂\n将试剂加入容器中",
        "heat": "加热\n对容器进行加热操作",
        "cool": "冷却\n降低容器温度",
        "mix": "搅拌\n混合容器中的物质",
        "measure": "测量\n记录实验数据",
        "observe": "观察\n记录实验现象",
        # 设置类
        "language": "语言设置\n选择界面显示语言",
        "theme": "主题设置\n选择浅色或深色主题",
        "auto_save": "自动保存\n定时自动保存实验进度",
        "notifications": "通知设置\n配置系统通知选项",
        # 输入类
        "experiment_name": "实验名称\n为您的实验输入一个描述性名称",
        "student_name": "学生姓名\n输入您的真实姓名",
        "student_id": "学号\n输入您的学号",
        "temperature": "温度\n输入目标温度值（单位：℃）",
        "volume": "体积\n输入液体体积（单位：mL）",
        "concentration": "浓度\n输入溶液浓度（单位：mol/L）",
    }

    # 快捷键提示
    SHORTCUT_HINTS = {
        "save": "Ctrl+S",
        "open": "Ctrl+O",
        "new": "Ctrl+N",
        "quit": "Ctrl+Q",
        "help": "F1",
        "fullscreen": "F11",
        "settings": "Ctrl+,",
        "zoom_in": "Ctrl++",
        "zoom_out": "Ctrl+-",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "copy": "Ctrl+C",
        "paste": "Ctrl+V",
        "cut": "Ctrl+X",
    }

    @staticmethod
    def enhance_widget(
        widget: QWidget,
        tooltip_key: str | None = None,
        custom_tooltip: str | None = None,
        shortcut: str | None = None,
    ):
        """增强控件的工具提示

        Args:
            widget: 要增强的控件
            tooltip_key: 预定义工具提示的键
            custom_tooltip: 自定义工具提示文本
            shortcut: 快捷键提示
        """
        try:
            tooltip_text = ""

            # 获取基础提示文本
            if custom_tooltip:
                tooltip_text = custom_tooltip
            elif tooltip_key and tooltip_key in TooltipEnhancer.TOOLTIP_TEMPLATES:
                tooltip_text = TooltipEnhancer.TOOLTIP_TEMPLATES[tooltip_key]
            else:
                # 使用控件的现有提示文本
                tooltip_text = widget.toolTip() or ""

            # 添加快捷键提示
            if shortcut:
                if tooltip_text:
                    tooltip_text += f"\n\n<b>快捷键:</b> {shortcut}"
                else:
                    tooltip_text = f"<b>快捷键:</b> {shortcut}"
            elif tooltip_key and tooltip_key in TooltipEnhancer.SHORTCUT_HINTS:
                shortcut_hint = TooltipEnhancer.SHORTCUT_HINTS[tooltip_key]
                if tooltip_text:
                    tooltip_text += f"\n\n<b>快捷键:</b> {shortcut_hint}"

            # 添加类型特定的提示
            if isinstance(widget, QPushButton):
                tooltip_text = TooltipEnhancer._enhance_button_tooltip(
                    widget, tooltip_text
                )
            elif isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox)):
                tooltip_text = TooltipEnhancer._enhance_input_tooltip(
                    widget, tooltip_text
                )
            elif isinstance(widget, QComboBox):
                tooltip_text = TooltipEnhancer._enhance_combobox_tooltip(
                    widget, tooltip_text
                )
            elif isinstance(widget, QCheckBox):
                tooltip_text = TooltipEnhancer._enhance_checkbox_tooltip(
                    widget, tooltip_text
                )

            # 设置富文本格式的工具提示
            if tooltip_text:
                # 将纯文本转换为HTML格式
                html_tooltip = TooltipEnhancer._format_as_html(tooltip_text)
                widget.setToolTip(html_tooltip)

                # 设置工具提示的显示时间
                widget.setToolTipDuration(5000)  # 5秒

            logger.debug(
                f"增强控件工具提示: {widget.objectName() or type(widget).__name__}"
            )

        except Exception as e:
            logger.warning(f"增强工具提示失败: {e}")

    @staticmethod
    def _enhance_button_tooltip(button: QPushButton, base_tooltip: str) -> str:
        """增强按钮工具提示"""
        # 如果按钮被禁用，添加说明
        if not button.isEnabled():
            base_tooltip += "\n\n<i>（当前不可用）</i>"
        return base_tooltip

    @staticmethod
    def _enhance_input_tooltip(widget: QWidget, base_tooltip: str) -> str:
        """增强输入框工具提示"""
        if isinstance(widget, QLineEdit):
            # 添加占位符提示
            if widget.placeholderText():
                base_tooltip += f"\n<i>示例: {widget.placeholderText()}</i>"

        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            # 添加范围提示
            min_val = widget.minimum()
            max_val = widget.maximum()
            base_tooltip += f"\n\n<b>有效范围:</b> {min_val} ~ {max_val}"

        return base_tooltip

    @staticmethod
    def _enhance_combobox_tooltip(combobox: QComboBox, base_tooltip: str) -> str:
        """增强下拉框工具提示"""
        count = combobox.count()
        if count > 0:
            base_tooltip += f"\n\n<i>共有 {count} 个选项</i>"
        return base_tooltip

    @staticmethod
    def _enhance_checkbox_tooltip(checkbox: QCheckBox, base_tooltip: str) -> str:
        """增强复选框工具提示"""
        state = "已启用" if checkbox.isChecked() else "已禁用"
        base_tooltip += f"\n\n<i>当前状态: {state}</i>"
        return base_tooltip

    @staticmethod
    def _format_as_html(text: str) -> str:
        """将文本格式化为HTML"""
        # 如果已经是HTML，直接返回
        if text.startswith("<") or "<b>" in text or "<i>" in text:
            return f'<div style="font-size: 11pt; line-height: 1.5;">{text}</div>'

        # 转换纯文本为HTML
        lines = text.split("\n")
        html_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>")

        return f'<div style="font-size: 11pt; line-height: 1.5;">{"".join(html_lines)}</div>'

    @staticmethod
    def enhance_container(container: QWidget, recursive: bool = True):
        """批量增强容器中的所有控件

        Args:
            container: 容器控件
            recursive: 是否递归处理子控件
        """
        try:
            if recursive:
                children = container.findChildren(QWidget)
            else:
                children = [c for c in container.children() if isinstance(c, QWidget)]

            for child in children:
                # 根据对象名或类型自动匹配工具提示
                object_name = child.objectName()

                # 尝试从对象名推断工具提示键
                if object_name:
                    # 移除常见的前缀/后缀
                    tooltip_key = object_name.lower()
                    tooltip_key = tooltip_key.replace("_btn", "").replace("_button", "")
                    tooltip_key = tooltip_key.replace("_edit", "").replace("_input", "")
                    tooltip_key = tooltip_key.replace("_combo", "").replace("_box", "")

                    # 如果已经有工具提示，不覆盖
                    if not child.toolTip():
                        TooltipEnhancer.enhance_widget(child, tooltip_key=tooltip_key)

            logger.info(f"批量增强容器工具提示完成，处理了 {len(children)} 个控件")

        except Exception as e:
            logger.error(f"批量增强工具提示失败: {e}")

    @staticmethod
    def set_global_tooltip_style():
        """设置全局工具提示样式"""
        # 设置工具提示字体
        font = QFont()
        font.setPointSize(11)
        font.setFamily("Microsoft YaHei UI, Segoe UI, Arial")
        QToolTip.setFont(font)

        logger.info("已设置全局工具提示样式")


class RichTooltip:
    """富文本工具提示生成器"""

    @staticmethod
    def create(
        title: str,
        description: str,
        shortcuts: list[tuple[str, str]] | None = None,
        tips: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> str:
        """创建富文本工具提示

        Args:
            title: 标题
            description: 描述
            shortcuts: 快捷键列表 [(动作, 快捷键)]
            tips: 提示列表
            warnings: 警告列表

        Returns:
            str: HTML格式的工具提示
        """
        html_parts = [
            "<div style=\"font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 11pt; line-height: 1.6;\">"
        ]

        # 标题
        html_parts.append(
            f'<p style="font-size: 12pt; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">{title}</p>'
        )

        # 描述
        html_parts.append(
            f'<p style="color: #34495e; margin-bottom: 8px;">{description}</p>'
        )

        # 快捷键
        if shortcuts:
            html_parts.append(
                '<p style="font-weight: bold; color: #3498db; margin-top: 8px; margin-bottom: 4px;">快捷键:</p>'
            )
            html_parts.append('<table style="margin-left: 10px;">')
            for action, shortcut in shortcuts:
                html_parts.append(
                    f'<tr><td style="color: #7f8c8d; padding-right: 10px;">{action}:</td><td style="color: #2c3e50; font-weight: 500;">{shortcut}</td></tr>'
                )
            html_parts.append("</table>")

        # 提示
        if tips:
            html_parts.append(
                '<p style="font-weight: bold; color: #27ae60; margin-top: 8px; margin-bottom: 4px;">💡 提示:</p>'
            )
            html_parts.append(
                '<ul style="margin-left: 20px; margin-top: 0; color: #7f8c8d;">'
            )
            for tip in tips:
                html_parts.append(f'<li style="margin-bottom: 4px;">{tip}</li>')
            html_parts.append("</ul>")

        # 警告
        if warnings:
            html_parts.append(
                '<p style="font-weight: bold; color: #e74c3c; margin-top: 8px; margin-bottom: 4px;">⚠️ 警告:</p>'
            )
            html_parts.append(
                '<ul style="margin-left: 20px; margin-top: 0; color: #c0392b;">'
            )
            for warning in warnings:
                html_parts.append(f'<li style="margin-bottom: 4px;">{warning}</li>')
            html_parts.append("</ul>")

        html_parts.append("</div>")

        return "".join(html_parts)
