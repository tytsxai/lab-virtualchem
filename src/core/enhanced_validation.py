#!/usr/bin/env python3
"""
增强的数据验证系统
提供全面的数据验证、类型检查、业务规则验证等功能
"""

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

try:
    from pydantic import BaseModel, ValidationError as PydanticValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    PydanticValidationError = Exception

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


class ValidationSeverity(Enum):
    """验证严重性"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    validator: Callable[[Any], bool]
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    validated_data: Optional[Any] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseValidator(ABC):
    """基础验证器"""

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """验证数据"""
        pass


class TypeValidator(BaseValidator):
    """类型验证器"""

    def __init__(self, expected_type: type):
        self.expected_type = expected_type

    def validate(self, data: Any) -> ValidationResult:
        """验证类型"""
        result = ValidationResult(is_valid=True)

        if not isinstance(data, self.expected_type):
            result.is_valid = False
            result.errors.append(
                f"期望类型 {self.expected_type.__name__}，实际类型 {type(data).__name__}"
            )

        return result


class RangeValidator(BaseValidator):
    """范围验证器"""

    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, data: Any) -> ValidationResult:
        """验证范围"""
        result = ValidationResult(is_valid=True)

        try:
            value = float(data)

            if self.min_value is not None and value < self.min_value:
                result.is_valid = False
                result.errors.append(f"值 {value} 小于最小值 {self.min_value}")

            if self.max_value is not None and value > self.max_value:
                result.is_valid = False
                result.errors.append(f"值 {value} 大于最大值 {self.max_value}")

        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"无法转换为数值: {data}")

        return result


class LengthValidator(BaseValidator):
    """长度验证器"""

    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, data: Any) -> ValidationResult:
        """验证长度"""
        result = ValidationResult(is_valid=True)

        if not hasattr(data, '__len__'):
            result.is_valid = False
            result.errors.append(f"数据没有长度属性: {type(data).__name__}")
            return result

        length = len(data)

        if self.min_length is not None and length < self.min_length:
            result.is_valid = False
            result.errors.append(f"长度 {length} 小于最小长度 {self.min_length}")

        if self.max_length is not None and length > self.max_length:
            result.is_valid = False
            result.errors.append(f"长度 {length} 大于最大长度 {self.max_length}")

        return result


class PatternValidator(BaseValidator):
    """模式验证器"""

    def __init__(self, pattern: str, flags: int = 0):
        self.pattern = pattern
        self.regex = re.compile(pattern, flags)

    def validate(self, data: Any) -> ValidationResult:
        """验证模式"""
        result = ValidationResult(is_valid=True)

        if not isinstance(data, str):
            result.is_valid = False
            result.errors.append(f"模式验证需要字符串类型，实际类型: {type(data).__name__}")
            return result

        if not self.regex.match(data):
            result.is_valid = False
            result.errors.append(f"字符串 '{data}' 不匹配模式 '{self.pattern}'")

        return result


class CustomValidator(BaseValidator):
    """自定义验证器"""

    def __init__(self, validator_func: Callable[[Any], bool], error_message: str):
        self.validator_func = validator_func
        self.error_message = error_message

    def validate(self, data: Any) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(is_valid=True)

        try:
            if not self.validator_func(data):
                result.is_valid = False
                result.errors.append(self.error_message)
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"验证器执行失败: {e}")

        return result


class SchemaValidator(BaseValidator):
    """模式验证器"""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.field_validators: Dict[str, List[BaseValidator]] = {}
        self._parse_schema()

    def _parse_schema(self) -> None:
        """解析模式"""
        for field_name, field_config in self.schema.items():
            validators = []

            # 类型验证
            if 'type' in field_config:
                validators.append(TypeValidator(field_config['type']))

            # 范围验证
            if 'min' in field_config or 'max' in field_config:
                validators.append(RangeValidator(
                    field_config.get('min'),
                    field_config.get('max')
                ))

            # 长度验证
            if 'min_length' in field_config or 'max_length' in field_config:
                validators.append(LengthValidator(
                    field_config.get('min_length'),
                    field_config.get('max_length')
                ))

            # 模式验证
            if 'pattern' in field_config:
                validators.append(PatternValidator(field_config['pattern']))

            # 自定义验证
            if 'validator' in field_config:
                validators.append(CustomValidator(
                    field_config['validator'],
                    field_config.get('error_message', '自定义验证失败')
                ))

            self.field_validators[field_name] = validators

    def validate(self, data: Any) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(is_valid=True)

        if not isinstance(data, dict):
            result.is_valid = False
            result.errors.append("模式验证需要字典类型")
            return result

        # 验证必需字段
        required_fields = [name for name, config in self.schema.items()
                          if config.get('required', True)]

        for field_name in required_fields:
            if field_name not in data:
                result.is_valid = False
                result.errors.append(f"缺少必需字段: {field_name}")

        # 验证字段值
        for field_name, value in data.items():
            if field_name in self.field_validators:
                for validator in self.field_validators[field_name]:
                    field_result = validator.validate(value)
                    if not field_result.is_valid:
                        result.is_valid = False
                        result.errors.extend([f"{field_name}: {error}" for error in field_result.errors])
                    result.warnings.extend([f"{field_name}: {warning}" for warning in field_result.warnings])
                    result.info.extend([f"{field_name}: {info}" for info in field_result.info])

        return result


class PydanticValidator(BaseValidator):
    """Pydantic验证器"""

    def __init__(self, model_class: Type[Any]):
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic不可用，请安装: pip install pydantic")
        self.model_class = model_class

    def validate(self, data: Any) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(is_valid=True)

        try:
            validated_data = self.model_class(**data)
            result.validated_data = validated_data
        except PydanticValidationError as e:
            result.is_valid = False
            result.errors.append(f"Pydantic验证失败: {e}")
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"验证器执行失败: {e}")

        return result


class ValidationChain(BaseValidator):
    """验证链"""

    def __init__(self):
        self.validators: List[BaseValidator] = []

    def add_validator(self, validator: BaseValidator) -> 'ValidationChain':
        """添加验证器"""
        self.validators.append(validator)
        return self

    def validate(self, data: Any) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            validator_result = validator.validate(data)

            # 合并结果
            if not validator_result.is_valid:
                result.is_valid = False

            result.errors.extend(validator_result.errors)
            result.warnings.extend(validator_result.warnings)
            result.info.extend(validator_result.info)

            # 如果验证失败且是严格模式，停止验证
            if not validator_result.is_valid and result.metadata.get('strict_mode', False):
                break

        return result


class EnhancedValidator:
    """增强验证器"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level
        self.validators: Dict[str, BaseValidator] = {}
        self.validation_cache: Dict[str, ValidationResult] = {}
        self.validation_stats: Dict[str, Dict[str, int]] = {}

        logger.info(f"增强验证器初始化完成，级别: {validation_level.value}")

    def register_validator(self, name: str, validator: BaseValidator) -> None:
        """注册验证器"""
        self.validators[name] = validator
        logger.debug(f"注册验证器: {name}")

    def validate(self, data: Any, validator_name: Optional[str] = None) -> ValidationResult:
        """验证数据"""
        start_time = time.time()

        # 生成缓存键
        cache_key = self._generate_cache_key(data, validator_name)

        # 检查缓存
        if cache_key in self.validation_cache:
            logger.debug("验证缓存命中")
            return self.validation_cache[cache_key]

        # 执行验证
        if validator_name and validator_name in self.validators:
            validator = self.validators[validator_name]
        else:
            # 使用默认验证链
            validator = self._create_default_validator(data)

        result = validator.validate(data)
        result.execution_time = time.time() - start_time

        # 缓存结果
        self.validation_cache[cache_key] = result

        # 更新统计
        self._update_stats(validator_name or "default", result)

        return result

    def _create_default_validator(self, data: Any) -> BaseValidator:
        """创建默认验证器"""
        chain = ValidationChain()

        # 根据数据类型添加验证器
        if isinstance(data, dict):
            # 字典验证
            chain.add_validator(TypeValidator(dict))

            # 检查是否有模式
            if 'type' in data or 'schema' in data:
                # 尝试解析为模式
                try:
                    schema = self._extract_schema(data)
                    if schema:
                        chain.add_validator(SchemaValidator(schema))
                except Exception as e:
                    logger.warning(f"模式解析失败: {e}")

        elif isinstance(data, (int, float)):
            # 数值验证
            chain.add_validator(TypeValidator(type(data)))
            chain.add_validator(RangeValidator())

        elif isinstance(data, str):
            # 字符串验证
            chain.add_validator(TypeValidator(str))
            chain.add_validator(LengthValidator())

        elif isinstance(data, list):
            # 列表验证
            chain.add_validator(TypeValidator(list))
            chain.add_validator(LengthValidator())

        return chain

    def _extract_schema(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从数据中提取模式"""
        # 这里可以实现智能模式提取逻辑
        # 目前返回None，表示无法提取
        return None

    def _generate_cache_key(self, data: Any, validator_name: Optional[str]) -> str:
        """生成缓存键"""
        import hashlib

        # 序列化数据
        try:
            data_str = json.dumps(data, sort_keys=True, default=str)
        except (TypeError, ValueError):
            data_str = str(data)

        # 生成哈希
        content = f"{validator_name}:{data_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _update_stats(self, validator_name: str, result: ValidationResult) -> None:
        """更新统计信息"""
        if validator_name not in self.validation_stats:
            self.validation_stats[validator_name] = {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'errors': 0,
                'warnings': 0
            }

        stats = self.validation_stats[validator_name]
        stats['total'] += 1

        if result.is_valid:
            stats['valid'] += 1
        else:
            stats['invalid'] += 1

        stats['errors'] += len(result.errors)
        stats['warnings'] += len(result.warnings)

    def get_validation_stats(self) -> Dict[str, Dict[str, int]]:
        """获取验证统计"""
        return self.validation_stats.copy()

    def clear_cache(self) -> None:
        """清除缓存"""
        self.validation_cache.clear()
        logger.info("验证缓存已清除")

    def generate_validation_report(self) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 数据验证报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"验证级别: {self.validation_level.value}")
        report.append("")

        # 统计信息
        total_validations = sum(stats['total'] for stats in self.validation_stats.values())
        total_valid = sum(stats['valid'] for stats in self.validation_stats.values())
        total_invalid = sum(stats['invalid'] for stats in self.validation_stats.values())
        total_errors = sum(stats['errors'] for stats in self.validation_stats.values())
        total_warnings = sum(stats['warnings'] for stats in self.validation_stats.values())

        report.append("## 总体统计")
        report.append(f"总验证次数: {total_validations}")
        report.append(f"有效验证: {total_valid}")
        report.append(f"无效验证: {total_invalid}")
        report.append(f"总错误数: {total_errors}")
        report.append(f"总警告数: {total_warnings}")
        report.append(f"成功率: {(total_valid/total_validations*100):.1f}%" if total_validations > 0 else "N/A")
        report.append("")

        # 详细统计
        report.append("## 详细统计")
        for validator_name, stats in self.validation_stats.items():
            report.append(f"### {validator_name}")
            report.append(f"总次数: {stats['total']}")
            report.append(f"有效: {stats['valid']}")
            report.append(f"无效: {stats['invalid']}")
            report.append(f"错误: {stats['errors']}")
            report.append(f"警告: {stats['warnings']}")
            report.append("")

        return "\n".join(report)


# 全局实例
enhanced_validator = EnhancedValidator()


def validate_data(
    data: Any,
    validator_name: Optional[str] = None,
    validation_level: Optional[ValidationLevel] = None
) -> ValidationResult:
    """验证数据的便捷函数"""
    if validation_level:
        enhanced_validator.validation_level = validation_level

    return enhanced_validator.validate(data, validator_name)


def register_validator(name: str, validator: BaseValidator) -> None:
    """注册验证器的便捷函数"""
    enhanced_validator.register_validator(name, validator)


def get_enhanced_validator() -> EnhancedValidator:
    """获取增强验证器实例"""
    return enhanced_validator
