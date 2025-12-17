"""自定义验证器"""

import re
from typing import Any


def validate_expression(expression: str) -> tuple[bool, str]:
    """验证表达式是否安全

    Args:
        expression: 表达式字符串

    Returns:
        (是否有效, 错误信息)
    """
    if not expression or len(expression) > 1000:
        return False, "表达式为空或过长"

    # 检查是否包含危险关键字
    dangerous_keywords = [
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
    ]

    for keyword in dangerous_keywords:
        if keyword in expression.lower():
            return False, f"表达式包含禁止的关键字: {keyword}"

    # 检查是否包含函数调用(除了白名单)
    allowed_functions = [
        "abs",
        "min",
        "max",
        "len",
        "range",
        "round",
        "int",
        "float",
        "str",
    ]
    function_pattern = r"\b([a-zA-Z_]\w*)\s*\("
    functions = re.findall(function_pattern, expression)

    for func in functions:
        if func not in allowed_functions:
            return False, f"不允许调用函数: {func}"

    return True, ""


def validate_range(value: float, range_spec: list[float]) -> tuple[bool, str]:
    """验证数值是否在范围内

    Args:
        value: 数值
        range_spec: 范围 [min, max]

    Returns:
        (是否有效, 错误信息)
    """
    if not range_spec or len(range_spec) != 2:
        return True, ""  # 无范围限制

    min_val, max_val = range_spec
    if not min_val <= value <= max_val:
        return False, f"数值 {value} 超出有效范围 [{min_val}, {max_val}]"

    return True, ""


def validate_yaml_safe(data: Any) -> tuple[bool, str]:
    """验证YAML数据是否安全(不包含Python对象)

    Args:
        data: YAML解析后的数据

    Returns:
        (是否安全, 错误信息)
    """
    # 检查是否包含Python对象标签
    if isinstance(data, str) and "!!python" in data:
        return False, "YAML包含Python对象标签"

    return True, ""
