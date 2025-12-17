"""
数据验证框架

支持Pydantic集成、自定义验证器、验证规则链等
"""

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from enum import Enum
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    PydanticValidationError = Exception

T = TypeVar("T")


class ValidationSeverity(Enum):
    """验证严重性"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError(Exception):
    """验证错误"""

    message: str = ""
    field: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: str | None = None
    value: Any | None = None
    metadata: dict[str, Any] = dc_field(default_factory=dict)

    def __post_init__(self) -> None:
        # Exception.__init__ 不会被 dataclass 自动调用
        super().__init__(self.message)
        if self.value is not None and "value" not in self.metadata:
            self.metadata["value"] = self.value


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: list[ValidationError] = dc_field(default_factory=list)
    warnings: list[ValidationError] = dc_field(default_factory=list)

    def add_error(self, field: str, message: str, code: str | None = None) -> None:
        """添加错误"""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                severity=ValidationSeverity.ERROR,
                code=code,
            )
        )
        self.is_valid = False

    def add_warning(self, field: str, message: str, code: str | None = None) -> None:
        """添加警告"""
        self.warnings.append(
            ValidationError(
                field=field,
                message=message,
                severity=ValidationSeverity.WARNING,
                code=code,
            )
        )

    def merge(self, other: "ValidationResult") -> None:
        """合并验证结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class IValidator(ABC, Generic[T]):
    """验证器接口"""

    @abstractmethod
    def validate(self, value: T) -> ValidationResult:
        """验证值"""
        pass


class BaseValidator(IValidator[T]):
    """基础验证器"""

    def __init__(self, field_name: str = "value"):
        self.field_name = field_name

    def validate(self, value: T) -> ValidationResult:
        """验证值"""
        result = ValidationResult(is_valid=True)
        self._do_validate(value, result)
        return result

    @abstractmethod
    def _do_validate(self, value: T, result: ValidationResult) -> None:
        """执行验证"""
        pass


class RequiredValidator(BaseValidator[Any]):
    """必填验证器"""

    def _do_validate(self, value: Any, result: ValidationResult) -> None:
        if value is None or (isinstance(value, str) and not value.strip()):
            result.add_error(self.field_name, f"{self.field_name} 是必填项")


class TypeValidator(BaseValidator[Any]):
    """类型验证器"""

    def __init__(self, expected_type: type, field_name: str = "value"):
        super().__init__(field_name)
        self.expected_type = expected_type

    def _do_validate(self, value: Any, result: ValidationResult) -> None:
        if not isinstance(value, self.expected_type):
            result.add_error(
                self.field_name,
                f"{self.field_name} 必须是 {self.expected_type.__name__} 类型",
            )


class RangeValidator(BaseValidator[float]):
    """范围验证器"""

    def __init__(
        self,
        min_value: float | None = None,
        max_value: float | None = None,
        field_name: str = "value",
    ):
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value

    def _do_validate(self, value: float, result: ValidationResult) -> None:
        if self.min_value is not None and value < self.min_value:
            result.add_error(
                self.field_name, f"{self.field_name} 不能小于 {self.min_value}"
            )

        if self.max_value is not None and value > self.max_value:
            result.add_error(
                self.field_name, f"{self.field_name} 不能大于 {self.max_value}"
            )


class LengthValidator(BaseValidator[str]):
    """长度验证器"""

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        field_name: str = "value",
    ):
        super().__init__(field_name)
        self.min_length = min_length
        self.max_length = max_length

    def _do_validate(self, value: str, result: ValidationResult) -> None:
        length = len(value)

        if self.min_length is not None and length < self.min_length:
            result.add_error(
                self.field_name, f"{self.field_name} 长度不能小于 {self.min_length}"
            )

        if self.max_length is not None and length > self.max_length:
            result.add_error(
                self.field_name, f"{self.field_name} 长度不能大于 {self.max_length}"
            )


class PatternValidator(BaseValidator[str]):
    """正则模式验证器"""

    def __init__(
        self, pattern: str, field_name: str = "value", message: str | None = None
    ):
        super().__init__(field_name)
        self.pattern = re.compile(pattern)
        self.message = message or f"{field_name} 格式不正确"

    def _do_validate(self, value: str, result: ValidationResult) -> None:
        if not self.pattern.match(value):
            result.add_error(self.field_name, self.message)


class EmailValidator(PatternValidator):
    """邮箱验证器"""

    def __init__(self, field_name: str = "email"):
        super().__init__(
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            field_name=field_name,
            message=f"{field_name} 格式不正确",
        )


class URLValidator(PatternValidator):
    """URL验证器"""

    def __init__(self, field_name: str = "url"):
        super().__init__(
            pattern=r"^https?://[^\s]+$",
            field_name=field_name,
            message=f"{field_name} 格式不正确",
        )


class CustomValidator(BaseValidator[Any]):
    """自定义验证器"""

    def __init__(
        self,
        validate_func: Callable[[Any], bool],
        error_message: str,
        field_name: str = "value",
    ):
        super().__init__(field_name)
        self.validate_func = validate_func
        self.error_message = error_message

    def _do_validate(self, value: Any, result: ValidationResult) -> None:
        if not self.validate_func(value):
            result.add_error(self.field_name, self.error_message)


class ValidatorChain(IValidator[T]):
    """验证器链"""

    def __init__(self):
        self._validators: list[IValidator[T]] = []

    def add(self, validator: IValidator[T]) -> "ValidatorChain":
        """添加验证器"""
        self._validators.append(validator)
        return self

    def validate(self, value: T) -> ValidationResult:
        """执行所有验证器"""
        result = ValidationResult(is_valid=True)

        for validator in self._validators:
            validator_result = validator.validate(value)
            result.merge(validator_result)

        return result


class SchemaValidator(Generic[T]):
    """模式验证器"""

    def __init__(self):
        self._field_validators: dict[str, ValidatorChain] = {}

    def field(self, name: str) -> ValidatorChain:
        """添加字段验证"""
        if name not in self._field_validators:
            self._field_validators[name] = ValidatorChain()
        return self._field_validators[name]

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(is_valid=True)

        for field_name, validator_chain in self._field_validators.items():
            value = data.get(field_name)
            field_result = validator_chain.validate(value)
            result.merge(field_result)

        return result


class PydanticValidator(IValidator[T]):
    """Pydantic验证器适配器"""

    def __init__(self, model_class: type[BaseModel]):
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic未安装")

        self.model_class = model_class

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """使用Pydantic验证"""
        result = ValidationResult(is_valid=True)

        try:
            self.model_class(**value)
        except PydanticValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                result.add_error(field, error["msg"], error["type"])

        return result


class ValidationRule:
    """验证规则建造器"""

    @staticmethod
    def required(field_name: str = "value") -> RequiredValidator:
        """必填规则"""
        return RequiredValidator(field_name)

    @staticmethod
    def type_of(expected_type: type, field_name: str = "value") -> TypeValidator:
        """类型规则"""
        return TypeValidator(expected_type, field_name)

    @staticmethod
    def range(
        min_value: float | None = None,
        max_value: float | None = None,
        field_name: str = "value",
    ) -> RangeValidator:
        """范围规则"""
        return RangeValidator(min_value, max_value, field_name)

    @staticmethod
    def length(
        min_length: int | None = None,
        max_length: int | None = None,
        field_name: str = "value",
    ) -> LengthValidator:
        """长度规则"""
        return LengthValidator(min_length, max_length, field_name)

    @staticmethod
    def pattern(pattern: str, field_name: str = "value") -> PatternValidator:
        """模式规则"""
        return PatternValidator(pattern, field_name)

    @staticmethod
    def email(field_name: str = "email") -> EmailValidator:
        """邮箱规则"""
        return EmailValidator(field_name)

    @staticmethod
    def url(field_name: str = "url") -> URLValidator:
        """URL规则"""
        return URLValidator(field_name)

    @staticmethod
    def custom(
        validate_func: Callable[[Any], bool],
        error_message: str,
        field_name: str = "value",
    ) -> CustomValidator:
        """自定义规则"""
        return CustomValidator(validate_func, error_message, field_name)


# 实验数据验证器示例
class ExperimentValidator(SchemaValidator):
    """实验数据验证器"""

    def __init__(self):
        super().__init__()

        # 实验ID验证
        self.field("experiment_id").add(ValidationRule.required("experiment_id")).add(
            ValidationRule.pattern(r"^exp_[a-z0-9]+$", "experiment_id")
        )

        # 实验名称验证
        self.field("title").add(ValidationRule.required("title")).add(
            ValidationRule.length(min_length=3, max_length=100, field_name="title")
        )

        # 温度验证
        self.field("temperature").add(ValidationRule.type_of(float, "temperature")).add(
            ValidationRule.range(
                min_value=-273.15, max_value=1000, field_name="temperature"
            )
        )


class ChemicalValidator(SchemaValidator):
    """化学品验证器"""

    def __init__(self):
        super().__init__()

        # 化学品名称
        self.field("name").add(ValidationRule.required("name")).add(
            ValidationRule.length(min_length=1, max_length=200, field_name="name")
        )

        # 浓度验证
        self.field("concentration").add(
            ValidationRule.type_of(float, "concentration")
        ).add(
            ValidationRule.range(min_value=0, max_value=100, field_name="concentration")
        )

        # pH值验证
        self.field("ph").add(
            ValidationRule.range(min_value=0, max_value=14, field_name="ph")
        )


if __name__ == "__main__":
    logger.info("=== 数据验证框架演示 ===\n")

    # 1. 基础验证器
    logger.info("1. 基础验证器:")
    email_validator = EmailValidator("email")
    result = email_validator.validate("test@example.com")
    logger.info(f"邮箱验证: {'✅ 有效' if result.is_valid else '❌ 无效'}")

    result = email_validator.validate("invalid-email")
    logger.info(f"无效邮箱: {'✅ 有效' if result.is_valid else '❌ 无效'}")
    if result.errors:
        logger.info(f"  错误: {result.errors[0].message}\n")

    # 2. 验证器链
    logger.info("2. 验证器链:")
    password_chain = ValidatorChain()
    password_chain.add(ValidationRule.required("password"))
    password_chain.add(ValidationRule.length(min_length=8, field_name="password"))

    result = password_chain.validate("12345")
    logger.info(f"密码 '12345': {'✅ 有效' if result.is_valid else '❌ 无效'}")
    if result.errors:
        for error in result.errors:
            logger.info(f"  - {error.message}")
    print()

    # 3. 模式验证器
    logger.info("3. 实验数据验证:")
    experiment_validator = ExperimentValidator()

    experiment_data = {
        "experiment_id": "exp_001",
        "title": "酸碱滴定实验",
        "temperature": 25.5,
    }

    result = experiment_validator.validate(experiment_data)
    logger.info(f"实验数据: {'✅ 有效' if result.is_valid else '❌ 无效'}\n")

    # 4. 化学品验证
    logger.info("4. 化学品数据验证:")
    chemical_validator = ChemicalValidator()

    chemical_data = {"name": "盐酸", "concentration": 0.1, "ph": 1.5}

    result = chemical_validator.validate(chemical_data)
    logger.info(f"化学品数据: {'✅ 有效' if result.is_valid else '❌ 无效'}\n")

    # 5. 自定义验证器
    logger.info("5. 自定义验证器:")

    def is_even(value):
        return value % 2 == 0

    even_validator = ValidationRule.custom(is_even, "值必须是偶数", "number")

    result = even_validator.validate(4)
    logger.info(f"数字 4: {'✅ 有效' if result.is_valid else '❌ 无效'}")

    result = even_validator.validate(5)
    logger.info(f"数字 5: {'✅ 有效' if result.is_valid else '❌ 无效'}")
    if result.errors:
        logger.info(f"  错误: {result.errors[0].message}\n")

    logger.info("✅ 演示完成")
