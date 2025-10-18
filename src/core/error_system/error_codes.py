"""
错误码定义和管理

提供统一的错误码系统，支持分类、国际化和扩展
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """错误分类"""

    GENERAL = "GENERAL"  # 通用错误 (1000-1999)
    AUTH = "AUTH"  # 认证错误 (2000-2999)
    EXPERIMENT = "EXPERIMENT"  # 实验错误 (3000-3999)
    DATA = "DATA"  # 数据错误 (4000-4999)
    SYSTEM = "SYSTEM"  # 系统错误 (5000-5999)
    NETWORK = "NETWORK"  # 网络错误 (6000-6999)
    LICENSE = "LICENSE"  # 许可证错误 (7000-7999)
    TEMPLATE = "TEMPLATE"  # 模板错误 (8000-8999)
    VALIDATION = "VALIDATION"  # 验证错误 (9000-9999)


@dataclass
class ErrorCode:
    """错误码定义"""

    code: int  # 错误码
    category: ErrorCategory  # 错误分类
    name: str  # 英文名称
    message_zh: str  # 中文消息
    message_en: str  # 英文消息
    http_status: int = 500  # HTTP状态码
    recoverable: bool = True  # 是否可恢复
    severity: str = "error"  # 严重程度: info, warning, error, critical
    help_url: str | None = None  # 帮助链接

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "category": self.category.value,
            "name": self.name,
            "message_zh": self.message_zh,
            "message_en": self.message_en,
            "http_status": self.http_status,
            "recoverable": self.recoverable,
            "severity": self.severity,
            "help_url": self.help_url,
        }


class ErrorCodeRegistry:
    """错误码注册表"""

    _codes: dict[int, ErrorCode] = {}

    # ==================== 通用错误 (1000-1999) ====================
    UNKNOWN_ERROR = ErrorCode(
        code=1000,
        category=ErrorCategory.GENERAL,
        name="UNKNOWN_ERROR",
        message_zh="未知错误",
        message_en="Unknown error",
        http_status=500,
        recoverable=False,
        severity="critical",
    )

    INVALID_REQUEST = ErrorCode(
        code=1001,
        category=ErrorCategory.GENERAL,
        name="INVALID_REQUEST",
        message_zh="无效请求",
        message_en="Invalid request",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    MISSING_PARAMETER = ErrorCode(
        code=1002,
        category=ErrorCategory.GENERAL,
        name="MISSING_PARAMETER",
        message_zh="缺少参数",
        message_en="Missing parameter",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    INVALID_PARAMETER = ErrorCode(
        code=1003,
        category=ErrorCategory.GENERAL,
        name="INVALID_PARAMETER",
        message_zh="参数无效",
        message_en="Invalid parameter",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    RESOURCE_NOT_FOUND = ErrorCode(
        code=1004,
        category=ErrorCategory.GENERAL,
        name="RESOURCE_NOT_FOUND",
        message_zh="资源不存在",
        message_en="Resource not found",
        http_status=404,
        recoverable=True,
        severity="warning",
    )

    RESOURCE_CONFLICT = ErrorCode(
        code=1005,
        category=ErrorCategory.GENERAL,
        name="RESOURCE_CONFLICT",
        message_zh="资源冲突",
        message_en="Resource conflict",
        http_status=409,
        recoverable=True,
        severity="warning",
    )

    RATE_LIMIT_EXCEEDED = ErrorCode(
        code=1006,
        category=ErrorCategory.GENERAL,
        name="RATE_LIMIT_EXCEEDED",
        message_zh="超过限流",
        message_en="Rate limit exceeded",
        http_status=429,
        recoverable=True,
        severity="warning",
    )

    # ==================== 认证错误 (2000-2999) ====================
    AUTH_REQUIRED = ErrorCode(
        code=2000,
        category=ErrorCategory.AUTH,
        name="AUTH_REQUIRED",
        message_zh="需要认证",
        message_en="Authentication required",
        http_status=401,
        recoverable=True,
        severity="warning",
    )

    AUTH_INVALID_TOKEN = ErrorCode(
        code=2001,
        category=ErrorCategory.AUTH,
        name="AUTH_INVALID_TOKEN",
        message_zh="令牌无效",
        message_en="Invalid token",
        http_status=401,
        recoverable=True,
        severity="warning",
    )

    AUTH_TOKEN_EXPIRED = ErrorCode(
        code=2002,
        category=ErrorCategory.AUTH,
        name="AUTH_TOKEN_EXPIRED",
        message_zh="令牌过期",
        message_en="Token expired",
        http_status=401,
        recoverable=True,
        severity="warning",
    )

    AUTH_INSUFFICIENT_PERMISSION = ErrorCode(
        code=2003,
        category=ErrorCategory.AUTH,
        name="AUTH_INSUFFICIENT_PERMISSION",
        message_zh="权限不足",
        message_en="Insufficient permission",
        http_status=403,
        recoverable=True,
        severity="warning",
    )

    AUTH_USER_NOT_FOUND = ErrorCode(
        code=2004,
        category=ErrorCategory.AUTH,
        name="AUTH_USER_NOT_FOUND",
        message_zh="用户不存在",
        message_en="User not found",
        http_status=404,
        recoverable=True,
        severity="warning",
    )

    AUTH_INVALID_CREDENTIALS = ErrorCode(
        code=2005,
        category=ErrorCategory.AUTH,
        name="AUTH_INVALID_CREDENTIALS",
        message_zh="凭证无效",
        message_en="Invalid credentials",
        http_status=401,
        recoverable=True,
        severity="warning",
    )

    # ==================== 实验错误 (3000-3999) ====================
    EXP_TEMPLATE_NOT_FOUND = ErrorCode(
        code=3000,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_TEMPLATE_NOT_FOUND",
        message_zh="实验模板不存在",
        message_en="Experiment template not found",
        http_status=404,
        recoverable=True,
        severity="warning",
    )

    EXP_INVALID_STATE = ErrorCode(
        code=3001,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_INVALID_STATE",
        message_zh="实验状态无效",
        message_en="Invalid experiment state",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    EXP_STEP_VALIDATION_FAILED = ErrorCode(
        code=3002,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_STEP_VALIDATION_FAILED",
        message_zh="步骤验证失败",
        message_en="Step validation failed",
        http_status=422,
        recoverable=True,
        severity="warning",
    )

    EXP_SAFETY_VIOLATION = ErrorCode(
        code=3003,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_SAFETY_VIOLATION",
        message_zh="安全规则违反",
        message_en="Safety violation",
        http_status=400,
        recoverable=False,
        severity="error",
    )

    EXP_SESSION_EXPIRED = ErrorCode(
        code=3004,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_SESSION_EXPIRED",
        message_zh="会话过期",
        message_en="Session expired",
        http_status=410,
        recoverable=True,
        severity="warning",
    )

    EXP_ALREADY_COMPLETED = ErrorCode(
        code=3005,
        category=ErrorCategory.EXPERIMENT,
        name="EXP_ALREADY_COMPLETED",
        message_zh="实验已完成",
        message_en="Experiment already completed",
        http_status=409,
        recoverable=True,
        severity="info",
    )

    # ==================== 数据错误 (4000-4999) ====================
    DATA_VALIDATION_FAILED = ErrorCode(
        code=4000,
        category=ErrorCategory.DATA,
        name="DATA_VALIDATION_FAILED",
        message_zh="数据验证失败",
        message_en="Data validation failed",
        http_status=422,
        recoverable=True,
        severity="warning",
    )

    DATA_SAVE_FAILED = ErrorCode(
        code=4001,
        category=ErrorCategory.DATA,
        name="DATA_SAVE_FAILED",
        message_zh="数据保存失败",
        message_en="Data save failed",
        http_status=500,
        recoverable=True,
        severity="error",
    )

    DATA_CORRUPTED = ErrorCode(
        code=4002,
        category=ErrorCategory.DATA,
        name="DATA_CORRUPTED",
        message_zh="数据损坏",
        message_en="Data corrupted",
        http_status=500,
        recoverable=False,
        severity="error",
    )

    DATA_DUPLICATE = ErrorCode(
        code=4003,
        category=ErrorCategory.DATA,
        name="DATA_DUPLICATE",
        message_zh="数据重复",
        message_en="Duplicate data",
        http_status=409,
        recoverable=True,
        severity="warning",
    )

    # ==================== 系统错误 (5000-5999) ====================
    SYS_INTERNAL_ERROR = ErrorCode(
        code=5000,
        category=ErrorCategory.SYSTEM,
        name="SYS_INTERNAL_ERROR",
        message_zh="内部错误",
        message_en="Internal error",
        http_status=500,
        recoverable=False,
        severity="critical",
    )

    SYS_SERVICE_UNAVAILABLE = ErrorCode(
        code=5001,
        category=ErrorCategory.SYSTEM,
        name="SYS_SERVICE_UNAVAILABLE",
        message_zh="服务不可用",
        message_en="Service unavailable",
        http_status=503,
        recoverable=True,
        severity="error",
    )

    SYS_DATABASE_ERROR = ErrorCode(
        code=5002,
        category=ErrorCategory.SYSTEM,
        name="SYS_DATABASE_ERROR",
        message_zh="数据库错误",
        message_en="Database error",
        http_status=500,
        recoverable=True,
        severity="error",
    )

    SYS_TIMEOUT = ErrorCode(
        code=5003,
        category=ErrorCategory.SYSTEM,
        name="SYS_TIMEOUT",
        message_zh="请求超时",
        message_en="Request timeout",
        http_status=504,
        recoverable=True,
        severity="warning",
    )

    SYS_FILE_NOT_FOUND = ErrorCode(
        code=5004,
        category=ErrorCategory.SYSTEM,
        name="SYS_FILE_NOT_FOUND",
        message_zh="文件不存在",
        message_en="File not found",
        http_status=404,
        recoverable=True,
        severity="warning",
    )

    SYS_PERMISSION_DENIED = ErrorCode(
        code=5005,
        category=ErrorCategory.SYSTEM,
        name="SYS_PERMISSION_DENIED",
        message_zh="权限被拒绝",
        message_en="Permission denied",
        http_status=403,
        recoverable=True,
        severity="warning",
    )

    # ==================== 网络错误 (6000-6999) ====================
    NET_CONNECTION_FAILED = ErrorCode(
        code=6000,
        category=ErrorCategory.NETWORK,
        name="NET_CONNECTION_FAILED",
        message_zh="连接失败",
        message_en="Connection failed",
        http_status=503,
        recoverable=True,
        severity="error",
    )

    NET_TIMEOUT = ErrorCode(
        code=6001,
        category=ErrorCategory.NETWORK,
        name="NET_TIMEOUT",
        message_zh="网络超时",
        message_en="Network timeout",
        http_status=504,
        recoverable=True,
        severity="warning",
    )

    NET_DNS_RESOLUTION_FAILED = ErrorCode(
        code=6002,
        category=ErrorCategory.NETWORK,
        name="NET_DNS_RESOLUTION_FAILED",
        message_zh="DNS解析失败",
        message_en="DNS resolution failed",
        http_status=503,
        recoverable=True,
        severity="warning",
    )

    # ==================== 许可证错误 (7000-7999) ====================
    LICENSE_INVALID = ErrorCode(
        code=7000,
        category=ErrorCategory.LICENSE,
        name="LICENSE_INVALID",
        message_zh="许可证无效",
        message_en="Invalid license",
        http_status=403,
        recoverable=False,
        severity="error",
    )

    LICENSE_EXPIRED = ErrorCode(
        code=7001,
        category=ErrorCategory.LICENSE,
        name="LICENSE_EXPIRED",
        message_zh="许可证过期",
        message_en="License expired",
        http_status=403,
        recoverable=False,
        severity="error",
    )

    LICENSE_NOT_FOUND = ErrorCode(
        code=7002,
        category=ErrorCategory.LICENSE,
        name="LICENSE_NOT_FOUND",
        message_zh="许可证不存在",
        message_en="License not found",
        http_status=404,
        recoverable=True,
        severity="warning",
    )

    # ==================== 模板错误 (8000-8999) ====================
    TEMPLATE_LOAD_ERROR = ErrorCode(
        code=8000,
        category=ErrorCategory.TEMPLATE,
        name="TEMPLATE_LOAD_ERROR",
        message_zh="模板加载失败",
        message_en="Template load failed",
        http_status=500,
        recoverable=True,
        severity="error",
    )

    TEMPLATE_PARSE_ERROR = ErrorCode(
        code=8001,
        category=ErrorCategory.TEMPLATE,
        name="TEMPLATE_PARSE_ERROR",
        message_zh="模板解析失败",
        message_en="Template parse failed",
        http_status=500,
        recoverable=True,
        severity="error",
    )

    TEMPLATE_INVALID_FORMAT = ErrorCode(
        code=8002,
        category=ErrorCategory.TEMPLATE,
        name="TEMPLATE_INVALID_FORMAT",
        message_zh="模板格式无效",
        message_en="Invalid template format",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    # ==================== 验证错误 (9000-9999) ====================
    VALIDATION_REQUIRED_FIELD = ErrorCode(
        code=9000,
        category=ErrorCategory.VALIDATION,
        name="VALIDATION_REQUIRED_FIELD",
        message_zh="缺少必填字段",
        message_en="Required field missing",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    VALIDATION_INVALID_TYPE = ErrorCode(
        code=9001,
        category=ErrorCategory.VALIDATION,
        name="VALIDATION_INVALID_TYPE",
        message_zh="字段类型错误",
        message_en="Invalid field type",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    VALIDATION_OUT_OF_RANGE = ErrorCode(
        code=9002,
        category=ErrorCategory.VALIDATION,
        name="VALIDATION_OUT_OF_RANGE",
        message_zh="值超出范围",
        message_en="Value out of range",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    VALIDATION_INVALID_FORMAT = ErrorCode(
        code=9003,
        category=ErrorCategory.VALIDATION,
        name="VALIDATION_INVALID_FORMAT",
        message_zh="格式无效",
        message_en="Invalid format",
        http_status=400,
        recoverable=True,
        severity="warning",
    )

    @classmethod
    def register(cls, error_code: ErrorCode) -> None:
        """注册错误码"""
        cls._codes[error_code.code] = error_code

    @classmethod
    def get(cls, code: int) -> ErrorCode | None:
        """获取错误码"""
        return cls._codes.get(code)

    @classmethod
    def get_by_name(cls, name: str) -> ErrorCode | None:
        """根据名称获取错误码"""
        for error_code in cls._codes.values():
            if error_code.name == name:
                return error_code
        return None

    @classmethod
    def get_all(cls) -> dict[int, ErrorCode]:
        """获取所有错误码"""
        return cls._codes.copy()

    @classmethod
    def get_by_category(cls, category: ErrorCategory) -> list[ErrorCode]:
        """根据分类获取错误码"""
        return [code for code in cls._codes.values() if code.category == category]


# 自动注册所有错误码
for attr_name in dir(ErrorCodeRegistry):
    attr = getattr(ErrorCodeRegistry, attr_name)
    if isinstance(attr, ErrorCode):
        ErrorCodeRegistry.register(attr)
