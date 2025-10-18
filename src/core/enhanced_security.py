#!/usr/bin/env python3
"""
增强的安全防护系统
提供全面的安全监控、威胁检测、访问控制、数据加密等功能
"""

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """威胁类型"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    PATH_TRAVERSAL = "path_traversal"
    BRUTE_FORCE = "brute_force"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_LEAKAGE = "data_leakage"
    MALICIOUS_INPUT = "malicious_input"


class AccessLevel(Enum):
    """访问级别"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class SecurityEvent:
    """安全事件"""
    timestamp: float
    event_type: ThreatType
    severity: SecurityLevel
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    action_taken: str = ""


@dataclass
class ThreatDetection:
    """威胁检测"""
    threat_type: ThreatType
    confidence: float
    pattern_matched: str
    input_data: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AccessControlRule:
    """访问控制规则"""
    resource: str
    access_level: AccessLevel
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[float] = None


class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.threat_patterns = {
            ThreatType.SQL_INJECTION: [
                r"('|(\\')|(;)|(\\;)|(--)|(\\--)|(/\*)|(\\/\*)|(\*/)|(\\\*/))",
                r"(union|select|insert|update|delete|drop|create|alter|exec|execute)",
                r"(or|and)\s+\d+\s*=\s*\d+",
                r"'\s*or\s*'\d+'\s*=\s*'\d+",
                r"'\s*and\s*'\d+'\s*=\s*'\d+",
            ],
            ThreatType.XSS: [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>",
                r"<link[^>]*>",
                r"<meta[^>]*>",
                r"<style[^>]*>",
                r"expression\s*\(",
                r"url\s*\(",
                r"@import",
            ],
            ThreatType.PATH_TRAVERSAL: [
                r"\.\./",
                r"\.\.\\",
                r"%2e%2e%2f",
                r"%2e%2e%5c",
                r"\.\.%2f",
                r"\.\.%5c",
            ],
            ThreatType.MALICIOUS_INPUT: [
                r"__\w+__",
                r"import\s+",
                r"eval\s*\(",
                r"exec\s*\(",
                r"compile\s*\(",
                r"open\s*\(",
                r"os\.",
                r"sys\.",
                r"subprocess",
                r"globals",
                r"locals",
                r"vars",
                r"dir",
                r"getattr",
                r"setattr",
                r"delattr",
                r"hasattr",
            ]
        }

        self.compiled_patterns = {}
        for threat_type, patterns in self.threat_patterns.items():
            self.compiled_patterns[threat_type] = [
                __import__('re').compile(pattern, __import__('re').IGNORECASE)
                for pattern in patterns
            ]

        logger.info("威胁检测器初始化完成")

    def detect_threats(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> List[ThreatDetection]:
        """检测威胁"""
        threats = []

        if not isinstance(input_data, str):
            return threats

        for threat_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(input_data):
                    confidence = self._calculate_confidence(input_data, pattern.pattern)

                    threat = ThreatDetection(
                        threat_type=threat_type,
                        confidence=confidence,
                        pattern_matched=pattern.pattern,
                        input_data=input_data,
                        context=context or {}
                    )
                    threats.append(threat)

        return threats

    def _calculate_confidence(self, input_data: str, pattern: str) -> float:
        """计算威胁置信度"""
        # 简单的置信度计算
        base_confidence = 0.5

        # 根据输入长度调整
        if len(input_data) > 100:
            base_confidence += 0.2

        # 根据模式复杂度调整
        if len(pattern) > 20:
            base_confidence += 0.1

        # 根据特殊字符数量调整
        special_chars = sum(1 for c in input_data if c in "<>\"'&;()[]{}\\")
        if special_chars > 5:
            base_confidence += 0.2

        return min(base_confidence, 1.0)


class AccessController:
    """访问控制器"""

    def __init__(self):
        self.rules: List[AccessControlRule] = []
        self.user_permissions: Dict[str, List[AccessLevel]] = {}
        self.role_permissions: Dict[str, List[AccessLevel]] = {}
        self.session_permissions: Dict[str, List[AccessLevel]] = {}
        self.lock = __import__('threading').RLock()

        logger.info("访问控制器初始化完成")

    def add_rule(self, rule: AccessControlRule) -> None:
        """添加访问控制规则"""
        with self.lock:
            self.rules.append(rule)
        logger.debug(f"添加访问控制规则: {rule.resource}")

    def remove_rule(self, resource: str) -> None:
        """移除访问控制规则"""
        with self.lock:
            self.rules = [rule for rule in self.rules if rule.resource != resource]
        logger.debug(f"移除访问控制规则: {resource}")

    def grant_permission(self, user_id: str, access_level: AccessLevel) -> None:
        """授予用户权限"""
        with self.lock:
            if user_id not in self.user_permissions:
                self.user_permissions[user_id] = []
            if access_level not in self.user_permissions[user_id]:
                self.user_permissions[user_id].append(access_level)
        logger.debug(f"授予用户权限: {user_id} -> {access_level.value}")

    def revoke_permission(self, user_id: str, access_level: AccessLevel) -> None:
        """撤销用户权限"""
        with self.lock:
            if user_id in self.user_permissions:
                if access_level in self.user_permissions[user_id]:
                    self.user_permissions[user_id].remove(access_level)
        logger.debug(f"撤销用户权限: {user_id} -> {access_level.value}")

    def check_access(self, user_id: str, resource: str, required_level: AccessLevel) -> bool:
        """检查访问权限"""
        with self.lock:
            # 检查用户权限
            user_permissions = self.user_permissions.get(user_id, [])
            if self._has_access_level(user_permissions, required_level):
                return True

            # 检查规则
            for rule in self.rules:
                if rule.resource == resource:
                    # 检查过期时间
                    if rule.expires_at and time.time() > rule.expires_at:
                        continue

                    # 检查用户是否在允许列表中
                    if user_id in rule.allowed_users:
                        if self._has_access_level([rule.access_level], required_level):
                            return True

                    # 检查角色权限
                    user_roles = self._get_user_roles(user_id)
                    for role in user_roles:
                        if role in rule.allowed_roles:
                            if self._has_access_level([rule.access_level], required_level):
                                return True

            return False

    def _has_access_level(self, permissions: List[AccessLevel], required: AccessLevel) -> bool:
        """检查是否有足够的访问级别"""
        level_hierarchy = {
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.SUPER_ADMIN: 4
        }

        required_level = level_hierarchy.get(required, 0)
        for permission in permissions:
            if level_hierarchy.get(permission, 0) >= required_level:
                return True

        return False

    def _get_user_roles(self, user_id: str) -> List[str]:
        """获取用户角色"""
        # 这里应该从用户管理系统获取角色
        # 目前返回空列表
        return []


class DataEncryptor:
    """数据加密器"""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or self._generate_secret_key()
        logger.info("数据加密器初始化完成")

    def _generate_secret_key(self) -> str:
        """生成密钥"""
        return secrets.token_hex(32)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        try:
            import base64
            try:
                from cryptography.fernet import Fernet

                # 生成密钥
                key = hashlib.sha256(self.secret_key.encode()).digest()
                fernet = Fernet(base64.urlsafe_b64encode(key))

                # 加密数据
                encrypted_data = fernet.encrypt(data.encode())
                return base64.urlsafe_b64encode(encrypted_data).decode()
            except ImportError:
                # 如果没有cryptography库，使用简单的Base64编码
                return base64.b64encode(data.encode()).decode()
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            import base64
            try:
                from cryptography.fernet import Fernet

                # 生成密钥
                key = hashlib.sha256(self.secret_key.encode()).digest()
                fernet = Fernet(base64.urlsafe_b64encode(key))

                # 解密数据
                decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
                decrypted_data = fernet.decrypt(decoded_data)
                return decrypted_data.decode()
            except ImportError:
                # 如果没有cryptography库，使用简单的Base64解码
                return base64.b64decode(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise

    def hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2进行密码哈希
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            salt, hash_hex = hashed_password.split(':')
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hashed.hex() == hash_hex
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False


class SecurityAuditor:
    """安全审计器"""

    def __init__(self):
        self.security_events: List[SecurityEvent] = []
        self.threat_detections: List[ThreatDetection] = []
        self.audit_log: List[Dict[str, Any]] = []
        self.lock = __import__('threading').RLock()

        logger.info("安全审计器初始化完成")

    def log_security_event(self, event: SecurityEvent) -> None:
        """记录安全事件"""
        with self.lock:
            self.security_events.append(event)

            # 限制事件数量
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-500:]

        logger.warning(f"安全事件: {event.event_type.value} - {event.description}")

    def log_threat_detection(self, threat: ThreatDetection) -> None:
        """记录威胁检测"""
        with self.lock:
            self.threat_detections.append(threat)

            # 限制检测数量
            if len(self.threat_detections) > 1000:
                self.threat_detections = self.threat_detections[-500:]

        logger.warning(f"威胁检测: {threat.threat_type.value} - 置信度: {threat.confidence:.2f}")

    def log_audit_event(self, event_type: str, description: str, **kwargs) -> None:
        """记录审计事件"""
        audit_event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "description": description,
            **kwargs
        }

        with self.lock:
            self.audit_log.append(audit_event)

            # 限制审计日志数量
            if len(self.audit_log) > 1000:
                self.audit_log = self.audit_log[-500:]

        logger.info(f"审计事件: {event_type} - {description}")

    def get_security_summary(self) -> Dict[str, Any]:
        """获取安全摘要"""
        with self.lock:
            return {
                "total_security_events": len(self.security_events),
                "total_threat_detections": len(self.threat_detections),
                "total_audit_events": len(self.audit_log),
                "recent_events": self.security_events[-10:] if self.security_events else [],
                "recent_threats": self.threat_detections[-10:] if self.threat_detections else [],
                "recent_audit": self.audit_log[-10:] if self.audit_log else []
            }


class EnhancedSecurityManager:
    """增强安全管理器"""

    def __init__(self):
        self.threat_detector = ThreatDetector()
        self.access_controller = AccessController()
        self.data_encryptor = DataEncryptor()
        self.security_auditor = SecurityAuditor()

        # 安全配置
        self.security_config = {
            "max_failed_attempts": 5,
            "lockout_duration": 300,  # 5分钟
            "session_timeout": 3600,  # 1小时
            "password_min_length": 8,
            "enable_threat_detection": True,
            "enable_access_control": True,
            "enable_data_encryption": True,
            "enable_audit_logging": True
        }

        # 失败尝试记录
        self.failed_attempts: Dict[str, List[float]] = {}
        self.locked_accounts: Dict[str, float] = {}

        logger.info("增强安全管理器初始化完成")

    def validate_input(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """验证输入"""
        if not self.security_config["enable_threat_detection"]:
            return True

        # 检测威胁
        threats = self.threat_detector.detect_threats(input_data, context)

        if threats:
            # 记录威胁检测
            for threat in threats:
                self.security_auditor.log_threat_detection(threat)

            # 记录安全事件
            event = SecurityEvent(
                timestamp=time.time(),
                event_type=threats[0].threat_type,
                severity=SecurityLevel.HIGH,
                description=f"检测到威胁: {threats[0].threat_type.value}",
                details={"threats": [threat.__dict__ for threat in threats]},
                blocked=True,
                action_taken="输入被阻止"
            )
            self.security_auditor.log_security_event(event)

            return False

        return True

    def check_access(self, user_id: str, resource: str, required_level: AccessLevel) -> bool:
        """检查访问权限"""
        if not self.security_config["enable_access_control"]:
            return True

        # 检查账户是否被锁定
        if user_id in self.locked_accounts:
            if time.time() < self.locked_accounts[user_id]:
                logger.warning(f"账户被锁定: {user_id}")
                return False
            else:
                # 解锁账户
                del self.locked_accounts[user_id]

        # 检查访问权限
        has_access = self.access_controller.check_access(user_id, resource, required_level)

        if not has_access:
            # 记录未授权访问
            event = SecurityEvent(
                timestamp=time.time(),
                event_type=ThreatType.UNAUTHORIZED_ACCESS,
                severity=SecurityLevel.HIGH,
                user_id=user_id,
                description=f"未授权访问尝试: {resource}",
                details={"resource": resource, "required_level": required_level.value},
                blocked=True,
                action_taken="访问被拒绝"
            )
            self.security_auditor.log_security_event(event)

        return has_access

    def authenticate_user(self, user_id: str, password: str) -> bool:
        """用户认证"""
        # 检查账户是否被锁定
        if user_id in self.locked_accounts:
            if time.time() < self.locked_accounts[user_id]:
                logger.warning(f"账户被锁定: {user_id}")
                return False
            else:
                # 解锁账户
                del self.locked_accounts[user_id]

        # 这里应该从用户数据库验证密码
        # 目前使用简单的模拟验证
        is_valid = self._verify_user_credentials(user_id, password)

        if is_valid:
            # 清除失败记录
            if user_id in self.failed_attempts:
                del self.failed_attempts[user_id]

            # 记录成功登录
            self.security_auditor.log_audit_event(
                "user_login",
                f"用户登录成功: {user_id}",
                user_id=user_id
            )
        else:
            # 记录失败尝试
            self._record_failed_attempt(user_id)

            # 记录失败登录
            self.security_auditor.log_audit_event(
                "user_login_failed",
                f"用户登录失败: {user_id}",
                user_id=user_id
            )

        return is_valid

    def _verify_user_credentials(self, user_id: str, password: str) -> bool:
        """验证用户凭据"""
        # 这里应该从用户数据库验证
        # 目前使用简单的模拟
        return password == "password123"  # 仅用于演示

    def _record_failed_attempt(self, user_id: str) -> None:
        """记录失败尝试"""
        current_time = time.time()

        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = []

        self.failed_attempts[user_id].append(current_time)

        # 清理过期的失败记录
        cutoff_time = current_time - self.security_config["lockout_duration"]
        self.failed_attempts[user_id] = [
            attempt for attempt in self.failed_attempts[user_id]
            if attempt > cutoff_time
        ]

        # 检查是否需要锁定账户
        if len(self.failed_attempts[user_id]) >= self.security_config["max_failed_attempts"]:
            lockout_time = current_time + self.security_config["lockout_duration"]
            self.locked_accounts[user_id] = lockout_time

            # 记录账户锁定
            event = SecurityEvent(
                timestamp=current_time,
                event_type=ThreatType.BRUTE_FORCE,
                severity=SecurityLevel.CRITICAL,
                user_id=user_id,
                description=f"账户因多次失败尝试被锁定: {user_id}",
                details={"failed_attempts": len(self.failed_attempts[user_id])},
                blocked=True,
                action_taken="账户被锁定"
            )
            self.security_auditor.log_security_event(event)

    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        if not self.security_config["enable_data_encryption"]:
            return data

        return self.data_encryptor.encrypt(data)

    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        if not self.security_config["enable_data_encryption"]:
            return encrypted_data

        return self.data_encryptor.decrypt(encrypted_data)

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.data_encryptor.hash_password(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.data_encryptor.verify_password(password, hashed_password)

    def get_security_report(self) -> str:
        """获取安全报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 安全报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 安全摘要
        summary = self.security_auditor.get_security_summary()
        report.append("## 安全摘要")
        report.append(f"安全事件总数: {summary['total_security_events']}")
        report.append(f"威胁检测总数: {summary['total_threat_detections']}")
        report.append(f"审计事件总数: {summary['total_audit_events']}")
        report.append("")

        # 最近安全事件
        if summary['recent_events']:
            report.append("## 最近安全事件")
            for event in summary['recent_events']:
                report.append(f"- {time.strftime('%H:%M:%S', time.localtime(event.timestamp))}: {event.description}")
            report.append("")

        # 最近威胁检测
        if summary['recent_threats']:
            report.append("## 最近威胁检测")
            for threat in summary['recent_threats']:
                report.append(f"- {time.strftime('%H:%M:%S', time.localtime(threat.timestamp))}: {threat.threat_type.value} (置信度: {threat.confidence:.2f})")
            report.append("")

        # 锁定账户
        if self.locked_accounts:
            report.append("## 锁定账户")
            for user_id, lockout_time in self.locked_accounts.items():
                remaining_time = lockout_time - time.time()
                if remaining_time > 0:
                    report.append(f"- {user_id}: 剩余锁定时间 {remaining_time:.0f}秒")
            report.append("")

        return "\n".join(report)


# 全局实例
security_manager = EnhancedSecurityManager()


def secure_input(func):
    """安全输入装饰器"""
    def wrapper(*args, **kwargs):
        # 检查所有字符串参数
        for arg in args:
            if isinstance(arg, str):
                if not security_manager.validate_input(arg):
                    raise ValueError(f"输入包含威胁: {arg[:50]}...")

        for key, value in kwargs.items():
            if isinstance(value, str):
                if not security_manager.validate_input(value):
                    raise ValueError(f"输入包含威胁: {value[:50]}...")

        return func(*args, **kwargs)
    return wrapper


def require_access(required_level: AccessLevel):
    """访问控制装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 这里需要从上下文中获取用户ID
            # 目前使用简单的模拟
            user_id = "current_user"  # 应该从请求上下文获取

            if not security_manager.check_access(user_id, func.__name__, required_level):
                raise PermissionError(f"访问被拒绝: {func.__name__}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_security_manager() -> EnhancedSecurityManager:
    """获取安全管理器实例"""
    return security_manager
