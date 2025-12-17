"""
用户友好的错误处理
将技术错误转换为用户能理解的提示
"""

import traceback
from typing import Any


class FriendlyErrorHandler:
    """友好的错误处理器"""

    # 常见错误的用户友好提示
    ERROR_MESSAGES: dict[str, dict[str, Any]] = {
        # 依赖相关
        "ModuleNotFoundError": {
            "title": "缺少必要的程序组件",
            "message": "程序运行需要的某些组件未安装",
            "solutions": [
                "运行命令: pip install -r requirements.txt",
                "确保使用 Python 3.10 或更高版本",
                "检查网络连接后重试安装",
            ],
        },
        "ImportError": {
            "title": "程序组件加载失败",
            "message": "无法加载必要的程序组件",
            "solutions": [
                "运行命令: pip install -r requirements.txt",
                "重新安装 Python",
                "检查 Python 环境变量设置",
            ],
        },
        # 文件相关
        "FileNotFoundError": {
            "title": "找不到文件",
            "message": "程序需要的文件不存在",
            "solutions": [
                "检查文件路径是否正确",
                "确保没有移动或删除重要文件",
                "尝试重新安装程序",
            ],
        },
        "PermissionError": {
            "title": "没有访问权限",
            "message": "程序没有权限访问某些文件或文件夹",
            "solutions": [
                "以管理员身份运行程序",
                "检查文件和文件夹的访问权限",
                "关闭可能占用文件的其他程序",
            ],
        },
        # 模板相关
        "TemplateLoadError": {
            "title": "实验模板加载失败",
            "message": "无法加载实验模板文件",
            "solutions": [
                "检查 assets/templates 目录是否存在",
                "确保模板文件格式正确 (.yaml 或 .yml)",
                "查看示例模板: assets/templates/titration_naoh_hcl.yaml",
            ],
        },
        "ValidationError": {
            "title": "数据格式错误",
            "message": "实验模板或数据格式不正确",
            "solutions": [
                "检查模板文件的语法是否正确",
                "参考示例模板格式",
                "查看详细错误信息找出具体问题",
            ],
        },
        # 配置相关
        "KeyError": {
            "title": "配置项缺失",
            "message": "配置文件中缺少必要的设置项",
            "solutions": [
                "检查 config.json 文件是否完整",
                "对比默认配置文件补充缺失项",
                "删除 config.json 让程序自动生成",
            ],
        },
        # 数据库相关
        "sqlite3.OperationalError": {
            "title": "数据库访问失败",
            "message": "无法访问或操作数据库",
            "solutions": [
                "检查 data 目录的访问权限",
                "关闭其他可能使用数据库的程序",
                "备份后删除数据库文件让程序重建",
            ],
        },
        # 网络相关
        "ConnectionError": {
            "title": "网络连接失败",
            "message": "无法连接到网络服务",
            "solutions": ["检查网络连接是否正常", "检查防火墙设置", "稍后重试"],
        },
    }

    @classmethod
    def get_friendly_message(
        cls, error: Exception, context: str | None = None
    ) -> dict[str, str | list[str]]:
        """将异常转换为友好的错误信息

        Args:
            error: 异常对象
            context: 错误发生的上下文

        Returns:
            包含友好错误信息的字典
        """
        error_type = type(error).__name__
        error_str = str(error)

        # 获取预定义的友好提示
        friendly_info: dict[str, Any] = dict(
            cls.ERROR_MESSAGES.get(
                error_type,
                {
                    "title": "程序运行出错",
                    "message": "程序遇到了一个意外的问题",
                    "solutions": [
                        "尝试重新启动程序",
                        "检查日志文件获取详细信息",
                        "如果问题持续，请联系技术支持",
                    ],
                },
            )
        )

        # 特殊处理某些错误
        solutions: list[str] = list(friendly_info["solutions"])  # 转换为可变列表

        if error_type == "ModuleNotFoundError":
            # 提取缺失的模块名
            import re

            match = re.search(r"No module named '(\w+)'", error_str)
            if match:
                module_name = match.group(1)
                friendly_info["message"] = f"缺少必要组件: {module_name}"
                solutions.insert(0, f"安装缺失组件: pip install {module_name}")

        elif error_type == "FileNotFoundError":
            # 提取文件路径
            if error_str:
                friendly_info["message"] = f"找不到文件: {error_str}"

        elif error_type == "TemplateLoadError":
            # 提取具体错误信息
            if "找不到实验模板" in error_str:
                friendly_info["message"] = error_str
                solutions.insert(0, "检查实验ID是否正确")
            elif "experiment" in error_str:
                friendly_info["message"] = "模板文件格式错误: 缺少 'experiment' 根节点"
                solutions.insert(0, "确保模板文件以 'experiment:' 开头")

        # 更新解决方案列表
        friendly_info["solutions"] = solutions

        # 添加上下文信息
        if context:
            friendly_info["context"] = context

        # 添加技术详情(供高级用户查看)
        friendly_info["technical_details"] = str(
            {
                "error_type": error_type,
                "error_message": error_str,
                "traceback": traceback.format_exc(),
            }
        )

        return friendly_info

    @classmethod
    def format_error_dialog(
        cls, error: Exception, context: str | None = None
    ) -> tuple[str, str]:
        """格式化错误信息用于对话框显示

        Args:
            error: 异常对象
            context: 错误发生的上下文

        Returns:
            (标题, 详细信息) 元组
        """
        friendly_info = cls.get_friendly_message(error, context)

        title: str = str(friendly_info["title"])

        # 构建详细信息
        details: list[str] = []

        if context:
            details.append(f"📍 位置: {context}")
            details.append("")

        details.append(f"❌ 问题: {friendly_info['message']}")
        details.append("")
        details.append("💡 解决方案:")

        solutions = friendly_info.get("solutions", [])
        if isinstance(solutions, list):
            for i, solution in enumerate(solutions, 1):
                details.append(f"  {i}. {solution}")

        # 添加技术详情(折叠)
        tech_details = friendly_info.get("technical_details", "")
        details.append("")
        details.append("━" * 50)
        details.append("🔧 技术详情 (供调试使用):")
        details.append(f"  {tech_details}")

        message: str = "\n".join(details)

        return (title, message)

    @classmethod
    def format_console_error(cls, error: Exception, context: str | None = None) -> str:
        """格式化错误信息用于控制台显示

        Args:
            error: 异常对象
            context: 错误发生的上下文

        Returns:
            格式化的错误文本
        """
        friendly_info = cls.get_friendly_message(error, context)

        lines = []
        lines.append("=" * 60)
        lines.append(f"❌ {friendly_info['title']}")
        lines.append("=" * 60)
        lines.append("")

        if context:
            lines.append(f"📍 位置: {context}")
            lines.append("")

        lines.append(f"问题: {friendly_info['message']}")
        lines.append("")
        lines.append("💡 解决方案:")

        solutions = friendly_info.get("solutions", [])
        if isinstance(solutions, list):
            for i, solution in enumerate(solutions, 1):
                lines.append(f"  {i}. {solution}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# 便捷函数
def friendly_error_message(error: Exception, context: str | None = None) -> str:
    """获取友好的错误信息(单行)"""
    info = FriendlyErrorHandler.get_friendly_message(error, context)
    return f"{info['title']}: {info['message']}"


def print_friendly_error(error: Exception, context: str | None = None) -> None:
    """在控制台打印友好的错误信息"""
    print(FriendlyErrorHandler.format_console_error(error, context))
