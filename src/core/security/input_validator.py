import html
import logging
import re
from pathlib import Path
from typing import Any

try:
    import bleach
except ImportError:
    bleach = None

"""输入验证和清理模块"""

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器"""

    def __init__(self) -> None:
        # 危险字符列表
        self.dangerous_chars = ["<", ">", '"', "'", "&", "\x00", "\r", "\n"]

        # 危险关键字列表
        self.dangerous_keywords = [
            "import",
            "exec",
            "eval",
            "compile",
            "open",
            "file",
            "__",
            "system",
            "subprocess",
            "os.",
            "sys.",
            "globals",
            "locals",
            "vars",
            "dir",
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
        ]

        # 允许的文件扩展名
        self.allowed_extensions = [".json", ".yaml", ".yml", ".txt", ".csv"]

        # 最大文件大小 (10MB)
        self.max_file_size = 10 * 1024 * 1024

        # 最大字符串长度
        self.max_string_length = 1000

    def sanitize_string(self, data: str) -> str:
        """清理字符串输入

        Args:
            data: 原始字符串

        Returns:
            清理后的字符串
        """
        if not isinstance(data, str):
            return str(data)

        # 限制长度
        if len(data) > self.max_string_length:
            data = data[: self.max_string_length]
            logger.warning(f"字符串被截断到 {self.max_string_length} 字符")

        # 移除危险字符
        for char in self.dangerous_chars:
            data = data.replace(char, "")

        # HTML转义
        data = html.escape(data)

        # 使用bleach清理HTML标签
        if bleach:
            data = bleach.clean(data, tags=[], strip=True)

        return data.strip()

    def validate_experiment_name(self, name: str) -> tuple[bool, str]:
        """验证实验名称

        Args:
            name: 实验名称

        Returns:
            (是否有效, 错误信息)
        """
        if not name or not name.strip():
            return False, "实验名称不能为空"

        if len(name) < 3:
            return False, "实验名称至少需要3个字符"

        if len(name) > 100:
            return False, "实验名称不能超过100个字符"

        # 检查是否包含危险字符
        sanitized = self.sanitize_string(name)
        if sanitized != name:
            return False, "实验名称包含不允许的字符"

        # 检查是否只包含字母、数字、中文、空格和基本标点
        if not re.match(r"^[\w\s\u4e00-\u9fff.,;:!?()-]+$", name):
            return False, "实验名称只能包含字母、数字、中文、空格和基本标点符号"

        return True, ""

    def validate_experiment_description(self, description: str) -> tuple[bool, str]:
        """验证实验描述

        Args:
            description: 实验描述

        Returns:
            (是否有效, 错误信息)
        """
        if not description:
            return True, ""  # 描述可以为空

        if len(description) > 1000:
            return False, "实验描述不能超过1000个字符"

        # 检查是否包含危险关键字
        description_lower = description.lower()
        for keyword in self.dangerous_keywords:
            if keyword in description_lower:
                return False, f"描述包含不允许的关键字: {keyword}"

        return True, ""

    def validate_numeric_input(
        self, value: Any, min_val: float | None = None, max_val: float | None = None
    ) -> tuple[bool, str]:
        """验证数值输入

        Args:
            value: 输入值
            min_val: 最小值
            max_val: 最大值

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 尝试转换为浮点数
            num_value = float(value)

            # 检查是否为有限数
            if not isinstance(num_value, (int, float)) or num_value != num_value:
                return False, "输入值必须是有效数字"

            # 检查范围
            if min_val is not None and num_value < min_val:
                return False, f"数值不能小于 {min_val}"

            if max_val is not None and num_value > max_val:
                return False, f"数值不能大于 {max_val}"

            return True, ""

        except (ValueError, TypeError):
            return False, "输入值必须是数字"

    def validate_file_upload(self, file_path: str) -> tuple[bool, str]:
        """验证文件上传

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误信息)
        """
        try:
            path = Path(file_path)

            # 检查文件是否存在
            if not path.exists():
                return False, "文件不存在"

            # 检查文件扩展名
            if path.suffix.lower() not in self.allowed_extensions:
                return False, f"不支持的文件类型: {path.suffix}"

            # 检查文件大小
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return False, f"文件大小超过限制 ({file_size} > {self.max_file_size})"

            # 检查文件名
            if not re.match(r"^[\w\s\u4e00-\u9fff.-]+$", path.name):
                return False, "文件名包含不允许的字符"

            return True, ""

        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False, f"文件验证失败: {str(e)}"

    def validate_experiment_data(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """验证实验数据

        Args:
            data: 实验数据字典

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 验证实验名称
        if "name" in data:
            is_valid, error = self.validate_experiment_name(data["name"])
            if not is_valid:
                errors.append(f"实验名称: {error}")

        # 验证实验描述
        if "description" in data:
            is_valid, error = self.validate_experiment_description(data["description"])
            if not is_valid:
                errors.append(f"实验描述: {error}")

        # 验证步骤数据
        if "steps" in data and isinstance(data["steps"], list):
            if len(data["steps"]) > 50:
                errors.append("实验步骤不能超过50个")

            for i, step in enumerate(data["steps"]):
                if not isinstance(step, dict):
                    errors.append(f"步骤 {i + 1}: 必须是字典格式")
                    continue

                # 验证步骤ID
                if "id" in step:
                    step_id = step["id"]
                    if not isinstance(step_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", step_id):
                        errors.append(f"步骤 {i + 1}: ID格式不正确")

                # 验证步骤描述
                if "text" in step:
                    is_valid, error = self.validate_experiment_description(step["text"])
                    if not is_valid:
                        errors.append(f"步骤 {i + 1}: {error}")

        return len(errors) == 0, errors

    def sanitize_experiment_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """清理实验数据

        Args:
            data: 原始实验数据

        Returns:
            清理后的数据
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_experiment_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    (
                        self.sanitize_experiment_data(item)
                        if isinstance(item, dict)
                        else self.sanitize_string(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized


# 全局验证器实例
input_validator = InputValidator()


def validate_and_sanitize_input(data: Any, input_type: str = "general") -> tuple[bool, str, Any]:
    """验证和清理输入的便捷函数

    Args:
        data: 输入数据
        input_type: 输入类型 (general, experiment, file, numeric)

    Returns:
        (是否有效, 错误信息, 清理后的数据)
    """
    try:
        if input_type == "experiment":
            if isinstance(data, dict):
                is_valid, errors = input_validator.validate_experiment_data(data)
                if not is_valid:
                    return False, "; ".join(errors), None
                return True, "", input_validator.sanitize_experiment_data(data)
            else:
                return False, "实验数据必须是字典格式", None

        elif input_type == "file":
            if isinstance(data, str):
                is_valid, error = input_validator.validate_file_upload(data)
                if not is_valid:
                    return False, error, None
                return True, "", data
            else:
                return False, "文件路径必须是字符串", None

        elif input_type == "numeric":
            if isinstance(data, (int, float, str)):
                is_valid, error = input_validator.validate_numeric_input(data)
                if not is_valid:
                    return False, error, None
                return True, "", float(data) if isinstance(data, str) else data
            else:
                return False, "数值输入必须是数字", None

        else:  # general
            if isinstance(data, str):
                return True, "", input_validator.sanitize_string(data)
            elif isinstance(data, dict):
                return True, "", input_validator.sanitize_experiment_data(data)
            else:
                return True, "", data

    except Exception as e:
        logger.error(f"输入验证失败: {e}")
        return False, f"输入验证失败: {str(e)}", None
