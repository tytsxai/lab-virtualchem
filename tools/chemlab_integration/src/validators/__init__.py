"""验证器模块

验证生成的数据符合 VirtualChemLab 标准。
"""

from .schema_validator import validate_card, validate_template

__all__ = ["validate_template", "validate_card"]
