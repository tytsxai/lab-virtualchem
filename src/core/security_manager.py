"""
安全管理器
提供身份验证、授权、加密、安全审计和威胁检测功能
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .common_exceptions import SecurityError
from .enhanced_event_bus import Event, EventPriority, publish_event, subscribe_event
from .enhanced_observability import LogLevel, get_observability
from .error_handler import get_error_handler

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(Enum):
    """权限"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ThreatType(Enum):
    """威胁类型"""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"
    MALWARE = "malware"
    PHISHING = "phishing"


@dataclass
class User:
    """用户"""

    id: str
    username: str
    email: str
    password_hash: str
    salt: str
    roles: list[str] = field(default_factory=list)
    permissions: list[Permission] = field(default_factory=list)
    is_active: bool = True
    is_locked: bool = False
    failed_login_attempts: int = 0
    last_login: float | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": [p.value for p in self.permissions],
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "failed_login_attempts": self.failed_login_attempts,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SecurityEvent:
    """安全事件"""

    id: str
    event_type: str
    severity: SecurityLevel
    user_id: str | None
    ip_address: str | None
    user_agent: str | None
    description: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "description": self.description,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ThreatDetection:
    """威胁检测"""

    threat_type: ThreatType
    severity: SecurityLevel
    confidence: float
    description: str
    mitigation: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "threat_type": self.threat_type.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "description": self.description,
            "mitigation": self.mitigation,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class EncryptionProvider(ABC):
    """加密提供者接口"""

    @abstractmethod
    def encrypt(self, data: str, key: str) -> str:
        """加密数据"""
        pass

    @abstractmethod
    def decrypt(self, encrypted_data: str, key: str) -> str:
        """解密数据"""
        pass

    @abstractmethod
    def hash(self, data: str, salt: str) -> str:
        """哈希数据"""
        pass


class SimpleEncryptionProvider(EncryptionProvider):
    """简单加密提供者"""

    def encrypt(self, data: str, key: str) -> str:
        """加密数据"""
        # 简单的XOR加密（生产环境应使用更强的加密算法）
        encrypted = ""
        for i, char in enumerate(data):
            encrypted += chr(ord(char) ^ ord(key[i % len(key)]))
        return encrypted.encode().hex()

    def decrypt(self, encrypted_data: str, key: str) -> str:
        """解密数据"""
        try:
            data = bytes.fromhex(encrypted_data).decode()
            decrypted = ""
            for i, char in enumerate(data):
                decrypted += chr(ord(char) ^ ord(key[i % len(key)]))
            return decrypted
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise SecurityError("Decryption failed") from e

    def hash(self, data: str, salt: str) -> str:
        """哈希数据"""
        return hashlib.pbkdf2_hmac("sha256", data.encode(), salt.encode(), 100000).hex()


class SecurityManager:
    """安全管理器"""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._error_handler = get_error_handler()
        self._observability = get_observability()

        # 用户管理
        self._users: dict[str, User] = {}
        self._sessions: dict[str, dict[str, Any]] = {}

        # 安全事件
        self._security_events: list[SecurityEvent] = []
        self._threat_detections: list[ThreatDetection] = []

        # 加密提供者
        self._encryption_provider = SimpleEncryptionProvider()

        # 安全策略
        self._max_failed_attempts = self._config.get("max_failed_attempts", 5)
        self._session_timeout = self._config.get("session_timeout", 3600)  # 1小时
        self._password_min_length = self._config.get("password_min_length", 8)

        # 统计信息
        self._stats = {
            "total_users": 0,
            "active_sessions": 0,
            "security_events": 0,
            "threat_detections": 0,
            "failed_logins": 0,
            "successful_logins": 0,
        }

        # 线程安全
        self._lock = threading.RLock()

        # 事件订阅
        self._setup_event_subscriptions()

        # 初始化
        self._initialize_default_users()

    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        subscribe_event("user_login_request", self._handle_login_request)
        subscribe_event("user_logout_request", self._handle_logout_request)
        subscribe_event("permission_check_request", self._handle_permission_check)
        subscribe_event("security_audit_request", self._handle_security_audit)

    def _initialize_default_users(self) -> None:
        """初始化默认用户"""
        # 创建默认管理员用户
        self.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            roles=["admin"],
            permissions=[Permission.ADMIN],
        )

        # 创建默认普通用户
        self.create_user(
            username="user",
            email="user@example.com",
            password="user123",
            roles=["user"],
            permissions=[Permission.READ, Permission.WRITE],
        )

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: list[str] | None = None,
        permissions: list[Permission] | None = None,
    ) -> User:
        """创建用户"""
        if len(password) < self._password_min_length:
            raise SecurityError(
                f"Password must be at least {self._password_min_length} characters"
            )

        # 生成盐
        salt = secrets.token_hex(16)

        # 哈希密码
        password_hash = self._encryption_provider.hash(password, salt)

        # 创建用户
        user = User(
            id=secrets.token_hex(8),
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            roles=roles or [],
            permissions=permissions or [],
        )

        with self._lock:
            self._users[user.id] = user
            self._stats["total_users"] += 1

        # 记录安全事件
        self._log_security_event(
            "user_created", SecurityLevel.MEDIUM, user.id, f"User created: {username}"
        )

        return user

    def authenticate_user(
        self, username: str, password: str, ip_address: str | None = None
    ) -> str | None:
        """用户认证"""
        # 查找用户
        user = None
        for u in self._users.values():
            if u.username == username:
                user = u
                break

        if not user:
            self._stats["failed_logins"] += 1
            self._log_security_event(
                "authentication_failed",
                SecurityLevel.MEDIUM,
                None,
                f"Authentication failed for username: {username}",
                ip_address=ip_address,
            )
            return None

        # 检查用户状态
        if not user.is_active:
            self._log_security_event(
                "inactive_user_login_attempt",
                SecurityLevel.HIGH,
                user.id,
                f"Inactive user login attempt: {username}",
                ip_address=ip_address,
            )
            return None

        if user.is_locked:
            self._log_security_event(
                "locked_user_login_attempt",
                SecurityLevel.HIGH,
                user.id,
                f"Locked user login attempt: {username}",
                ip_address=ip_address,
            )
            return None

        # 验证密码
        if not self._verify_password(password, user.password_hash, user.salt):
            user.failed_login_attempts += 1
            user.updated_at = time.time()

            # 检查是否达到最大失败次数
            if user.failed_login_attempts >= self._max_failed_attempts:
                user.is_locked = True
                self._log_security_event(
                    "user_locked",
                    SecurityLevel.HIGH,
                    user.id,
                    f"User locked due to too many failed attempts: {username}",
                    ip_address=ip_address,
                )

            self._stats["failed_logins"] += 1
            self._log_security_event(
                "authentication_failed",
                SecurityLevel.MEDIUM,
                user.id,
                f"Authentication failed for user: {username}",
                ip_address=ip_address,
            )
            return None

        # 认证成功
        user.failed_login_attempts = 0
        user.last_login = time.time()
        user.updated_at = time.time()

        # 创建会话
        session_id = self._create_session(user.id, ip_address)

        self._stats["successful_logins"] += 1
        self._log_security_event(
            "authentication_success",
            SecurityLevel.LOW,
            user.id,
            f"Authentication successful: {username}",
            ip_address=ip_address,
        )

        return session_id

    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        try:
            computed_hash = self._encryption_provider.hash(password, salt)
            return hmac.compare_digest(computed_hash, password_hash)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def _create_session(self, user_id: str, ip_address: str | None = None) -> str:
        """创建会话"""
        session_id = secrets.token_hex(16)

        session = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "ip_address": ip_address,
            "is_active": True,
        }

        with self._lock:
            self._sessions[session_id] = session
            self._stats["active_sessions"] += 1

        return session_id

    def validate_session(self, session_id: str) -> str | None:
        """验证会话"""
        with self._lock:
            session = self._sessions.get(session_id)

            if not session or not session["is_active"]:
                return None

            # 检查会话超时
            if time.time() - session["last_activity"] > self._session_timeout:
                session["is_active"] = False
                self._stats["active_sessions"] -= 1
                return None

            # 更新最后活动时间
            session["last_activity"] = time.time()

            return session["user_id"]

    def logout_user(self, session_id: str) -> bool:
        """用户登出"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["is_active"] = False
                self._stats["active_sessions"] -= 1

                # 记录安全事件
                user_id = self._sessions[session_id]["user_id"]
                self._log_security_event(
                    "user_logout", SecurityLevel.LOW, user_id, "User logged out"
                )

                return True

        return False

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查权限"""
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return False

        return permission in user.permissions

    def has_role(self, user_id: str, role: str) -> bool:
        """检查角色"""
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return False

        return role in user.roles

    def encrypt_data(self, data: str, key: str) -> str:
        """加密数据"""
        try:
            return self._encryption_provider.encrypt(data, key)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise SecurityError("Encryption failed") from e

    def decrypt_data(self, encrypted_data: str, key: str) -> str:
        """解密数据"""
        try:
            return self._encryption_provider.decrypt(encrypted_data, key)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise SecurityError("Decryption failed") from e

    def detect_threat(
        self, threat_type: ThreatType, description: str, **metadata
    ) -> None:
        """检测威胁"""
        detection = ThreatDetection(
            threat_type=threat_type,
            severity=SecurityLevel.HIGH,
            confidence=0.8,
            description=description,
            mitigation="Investigate and take appropriate action",
            timestamp=time.time(),
            metadata=metadata,
        )

        with self._lock:
            self._threat_detections.append(detection)
            self._stats["threat_detections"] += 1

        # 发布威胁检测事件
        publish_event(
            "threat_detected", detection.to_dict(), priority=EventPriority.HIGH
        )

        # 记录安全事件
        self._log_security_event(
            "threat_detected",
            SecurityLevel.CRITICAL,
            None,
            f"Threat detected: {threat_type.value} - {description}",
            metadata=metadata,
        )

    def _log_security_event(
        self,
        event_type: str,
        severity: SecurityLevel,
        user_id: str | None,
        description: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        **metadata,
    ) -> None:
        """记录安全事件"""
        event = SecurityEvent(
            id=secrets.token_hex(8),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            timestamp=time.time(),
            metadata=metadata,
        )

        with self._lock:
            self._security_events.append(event)
            self._stats["security_events"] += 1

        # 发布安全事件
        publish_event("security_event", event.to_dict(), priority=EventPriority.HIGH)

        # 记录日志
        self._observability.log(
            LogLevel.WARNING
            if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]
            else LogLevel.INFO,
            f"Security event: {event_type}",
            module="SecurityManager",
            function="_log_security_event",
            extra_data=event.to_dict(),
        )

    def get_user(self, user_id: str) -> User | None:
        """获取用户"""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def get_security_events(
        self, severity: SecurityLevel | None = None, limit: int | None = None
    ) -> list[SecurityEvent]:
        """获取安全事件"""
        events = self._security_events.copy()

        # 过滤严重程度
        if severity:
            events = [event for event in events if event.severity == severity]

        # 限制数量
        if limit:
            events = events[-limit:]

        return events

    def get_threat_detections(
        self, threat_type: ThreatType | None = None, limit: int | None = None
    ) -> list[ThreatDetection]:
        """获取威胁检测"""
        detections = self._threat_detections.copy()

        # 过滤威胁类型
        if threat_type:
            detections = [
                detection
                for detection in detections
                if detection.threat_type == threat_type
            ]

        # 限制数量
        if limit:
            detections = detections[-limit:]

        return detections

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def _handle_login_request(self, event: Event) -> None:
        """处理登录请求"""
        username = event.data.get("username")
        password = event.data.get("password")
        ip_address = event.data.get("ip_address")

        if username and password:
            session_id = self.authenticate_user(username, password, ip_address)

            # 发布登录结果
            publish_event(
                "login_result",
                {"success": session_id is not None, "session_id": session_id},
                priority=EventPriority.NORMAL,
            )

    def _handle_logout_request(self, event: Event) -> None:
        """处理登出请求"""
        session_id = event.data.get("session_id")

        if session_id:
            success = self.logout_user(session_id)

            # 发布登出结果
            publish_event(
                "logout_result", {"success": success}, priority=EventPriority.NORMAL
            )

    def _handle_permission_check(self, event: Event) -> None:
        """处理权限检查请求"""
        user_id = event.data.get("user_id")
        permission = event.data.get("permission")

        if user_id and permission:
            try:
                perm = Permission(permission)
                has_permission = self.check_permission(user_id, perm)

                # 发布权限检查结果
                publish_event(
                    "permission_check_result",
                    {"has_permission": has_permission},
                    priority=EventPriority.NORMAL,
                )
            except ValueError:
                logger.error(f"Invalid permission: {permission}")

    def _handle_security_audit(self, event: Event) -> None:
        """处理安全审计请求"""
        audit_type = event.data.get("type", "full")

        if audit_type == "full":
            # 执行完整安全审计
            self._perform_security_audit()
        elif audit_type == "user":
            user_id = event.data.get("user_id")
            if user_id:
                self._audit_user(user_id)

    def _perform_security_audit(self) -> None:
        """执行安全审计"""
        # 检查过期会话
        current_time = time.time()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if current_time - session["last_activity"] > self._session_timeout:
                expired_sessions.append(session_id)

        # 清理过期会话
        for session_id in expired_sessions:
            self.logout_user(session_id)

        # 记录审计事件
        self._log_security_event(
            "security_audit",
            SecurityLevel.MEDIUM,
            None,
            f"Security audit completed, cleaned {len(expired_sessions)} expired sessions",
        )

    def _audit_user(self, user_id: str) -> None:
        """审计用户"""
        user = self._users.get(user_id)
        if not user:
            return

        # 检查用户状态
        if user.failed_login_attempts > 0:
            self._log_security_event(
                "user_audit",
                SecurityLevel.MEDIUM,
                user_id,
                f"User has {user.failed_login_attempts} failed login attempts",
            )

        # 检查会话
        user_sessions = [
            session
            for session in self._sessions.values()
            if session["user_id"] == user_id and session["is_active"]
        ]

        if len(user_sessions) > 1:
            self._log_security_event(
                "multiple_sessions",
                SecurityLevel.MEDIUM,
                user_id,
                f"User has {len(user_sessions)} active sessions",
            )

    def export_security_data(self, output_dir: Path) -> None:
        """导出安全数据"""
        output_dir.mkdir(exist_ok=True)

        # 导出用户信息（不包含密码）
        users_file = output_dir / "users.json"
        users_data = {
            "users": [user.to_dict() for user in self._users.values()],
            "total_users": len(self._users),
        }

        with open(users_file, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

        # 导出安全事件
        events_file = output_dir / "security_events.json"
        events_data = {
            "events": [event.to_dict() for event in self._security_events],
            "total_events": len(self._security_events),
        }

        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)

        # 导出威胁检测
        threats_file = output_dir / "threat_detections.json"
        threats_data = {
            "detections": [
                detection.to_dict() for detection in self._threat_detections
            ],
            "total_detections": len(self._threat_detections),
        }

        with open(threats_file, "w", encoding="utf-8") as f:
            json.dump(threats_data, f, indent=2, ensure_ascii=False)

        # 导出统计信息
        stats_file = output_dir / "security_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)


# 全局安全管理器实例
_global_security_manager = SecurityManager()


def get_security_manager() -> SecurityManager:
    """获取全局安全管理器"""
    return _global_security_manager


def authenticate_user(
    username: str, password: str, ip_address: str | None = None
) -> str | None:
    """用户认证"""
    return _global_security_manager.authenticate_user(username, password, ip_address)


def validate_session(session_id: str) -> str | None:
    """验证会话"""
    return _global_security_manager.validate_session(session_id)


def check_permission(user_id: str, permission: Permission) -> bool:
    """检查权限"""
    return _global_security_manager.check_permission(user_id, permission)


def encrypt_data(data: str, key: str) -> str:
    """加密数据"""
    return _global_security_manager.encrypt_data(data, key)


def decrypt_data(encrypted_data: str, key: str) -> str:
    """解密数据"""
    return _global_security_manager.decrypt_data(encrypted_data, key)
