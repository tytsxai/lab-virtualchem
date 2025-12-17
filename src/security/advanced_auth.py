"""
高级认证系统
提供多因素认证、会话管理、安全审计等功能
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AuthMethod(Enum):
    """认证方法"""

    PASSWORD = "password"
    TOTP = "totp"  # 时间基础一次性密码
    SMS = "sms"
    EMAIL = "email"
    BIOMETRIC = "biometric"
    HARDWARE_KEY = "hardware_key"


class SessionStatus(Enum):
    """会话状态"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class SecurityLevel(Enum):
    """安全级别"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LoginAttempt:
    """登录尝试"""

    user_id: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: str | None = None
    auth_method: AuthMethod = AuthMethod.PASSWORD


@dataclass
class SecurityEvent:
    """安全事件"""

    event_id: str
    user_id: str | None
    event_type: str
    severity: SecurityLevel
    description: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    metadata: dict[str, Any]


class UserSession(BaseModel):
    """用户会话"""

    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(
        default_factory=datetime.now, description="最后活动时间"
    )
    expires_at: datetime = Field(..., description="过期时间")
    ip_address: str = Field(..., description="IP地址")
    user_agent: str = Field(..., description="用户代理")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="会话状态")
    auth_methods: list[AuthMethod] = Field(default_factory=list, description="认证方法")
    security_level: SecurityLevel = Field(
        default=SecurityLevel.MEDIUM, description="安全级别"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class MultiFactorAuth:
    """多因素认证"""

    def __init__(self, secret_key: str):
        """初始化多因素认证

        Args:
            secret_key: 密钥
        """
        self.secret_key = secret_key
        self.totp_window = 1  # TOTP时间窗口
        self.max_attempts = 3  # 最大尝试次数

        logger.info("多因素认证已初始化")

    def generate_totp_secret(self, user_id: str) -> str:
        """生成TOTP密钥

        Args:
            user_id: 用户ID

        Returns:
            TOTP密钥
        """
        # 使用用户ID和系统密钥生成唯一密钥
        key_material = f"{user_id}:{self.secret_key}:{time.time()}"
        secret = hashlib.sha256(key_material.encode()).hexdigest()[:32]
        return secret

    def generate_totp_code(self, secret: str, timestamp: int | None = None) -> str:
        """生成TOTP代码

        Args:
            secret: TOTP密钥
            timestamp: 时间戳

        Returns:
            TOTP代码
        """
        if timestamp is None:
            timestamp = int(time.time())

        # 计算时间步长
        time_step = timestamp // 30

        # 生成HMAC
        key_bytes = secret.encode()
        message = time_step.to_bytes(8, byteorder="big")
        hmac_digest = hmac.new(key_bytes, message, hashlib.sha1).digest()

        # 提取动态代码
        offset = hmac_digest[-1] & 0x0F
        code = int.from_bytes(hmac_digest[offset : offset + 4], byteorder="big")
        code = code & 0x7FFFFFFF

        # 生成6位代码
        return f"{code % 1000000:06d}"

    def verify_totp_code(
        self, secret: str, code: str, timestamp: int | None = None
    ) -> bool:
        """验证TOTP代码

        Args:
            secret: TOTP密钥
            code: 验证代码
            timestamp: 时间戳

        Returns:
            是否验证成功
        """
        if timestamp is None:
            timestamp = int(time.time())

        # 检查时间窗口内的代码
        for i in range(-self.totp_window, self.totp_window + 1):
            expected_code = self.generate_totp_code(secret, timestamp + i * 30)
            if hmac.compare_digest(code, expected_code):
                return True

        return False

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """生成备份代码

        Args:
            count: 代码数量

        Returns:
            备份代码列表
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(code)
        return codes

    def verify_backup_code(self, code: str, backup_codes: list[str]) -> bool:
        """验证备份代码

        Args:
            code: 验证代码
            backup_codes: 备份代码列表

        Returns:
            是否验证成功
        """
        return code.upper() in backup_codes


class SessionManager:
    """会话管理器"""

    def __init__(self, secret_key: str, session_timeout: int = 3600):
        """初始化会话管理器

        Args:
            secret_key: 密钥
            session_timeout: 会话超时时间（秒）
        """
        self.secret_key = secret_key
        self.session_timeout = session_timeout
        self.active_sessions: dict[str, UserSession] = {}
        self.session_tokens: dict[str, str] = {}  # token -> session_id
        import threading

        self._lock = threading.RLock()

        logger.info(f"会话管理器已初始化: timeout={session_timeout}s")

    def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        auth_methods: list[AuthMethod],
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, UserSession]:
        """创建会话

        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            auth_methods: 认证方法
            security_level: 安全级别
            metadata: 元数据

        Returns:
            (会话令牌, 会话对象)
        """
        with self._lock:
            # 生成会话ID和令牌
            session_id = secrets.token_urlsafe(32)
            token = self._generate_session_token(session_id, user_id)

            # 计算过期时间
            expires_at = datetime.now() + timedelta(seconds=self.session_timeout)

            # 创建会话
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                auth_methods=auth_methods,
                security_level=security_level,
                metadata=metadata or {},
            )

            # 存储会话
            self.active_sessions[session_id] = session
            self.session_tokens[token] = session_id

            logger.info(f"会话已创建: {session_id} for {user_id}")
            return token, session

    def validate_session(self, token: str) -> UserSession | None:
        """验证会话

        Args:
            token: 会话令牌

        Returns:
            会话对象
        """
        with self._lock:
            if token not in self.session_tokens:
                return None

            session_id = self.session_tokens[token]
            if session_id not in self.active_sessions:
                return None

            session = self.active_sessions[session_id]

            # 检查会话状态
            if session.status != SessionStatus.ACTIVE:
                return None

            # 检查是否过期
            if datetime.now() > session.expires_at:
                session.status = SessionStatus.EXPIRED
                return None

            # 更新最后活动时间
            session.last_activity = datetime.now()

            return session

    def refresh_session(self, token: str) -> str | None:
        """刷新会话

        Args:
            token: 会话令牌

        Returns:
            新令牌
        """
        with self._lock:
            session = self.validate_session(token)
            if not session:
                return None

            # 生成新令牌
            new_token = self._generate_session_token(
                session.session_id, session.user_id
            )

            # 更新令牌映射
            del self.session_tokens[token]
            self.session_tokens[new_token] = session.session_id

            # 延长过期时间
            session.expires_at = datetime.now() + timedelta(
                seconds=self.session_timeout
            )

            logger.info(f"会话已刷新: {session.session_id}")
            return new_token

    def revoke_session(self, token: str) -> bool:
        """撤销会话

        Args:
            token: 会话令牌

        Returns:
            是否成功撤销
        """
        with self._lock:
            if token not in self.session_tokens:
                return False

            session_id = self.session_tokens[token]
            if session_id in self.active_sessions:
                self.active_sessions[session_id].status = SessionStatus.REVOKED

            del self.session_tokens[token]

            logger.info(f"会话已撤销: {session_id}")
            return True

    def revoke_user_sessions(self, user_id: str) -> int:
        """撤销用户所有会话

        Args:
            user_id: 用户ID

        Returns:
            撤销的会话数量
        """
        with self._lock:
            revoked_count = 0

            for session in self.active_sessions.values():
                if (
                    session.user_id == user_id
                    and session.status == SessionStatus.ACTIVE
                ):
                    session.status = SessionStatus.REVOKED
                    revoked_count += 1

            # 清理令牌映射
            tokens_to_remove = []
            for token, session_id in self.session_tokens.items():
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    if session.user_id == user_id:
                        tokens_to_remove.append(token)

            for token in tokens_to_remove:
                del self.session_tokens[token]

            logger.info(f"用户会话已撤销: {user_id} - {revoked_count} 个会话")
            return revoked_count

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话

        Returns:
            清理的会话数量
        """
        with self._lock:
            current_time = datetime.now()
            expired_sessions = []

            for session_id, session in self.active_sessions.items():
                if current_time > session.expires_at:
                    expired_sessions.append(session_id)

            # 清理过期会话
            for session_id in expired_sessions:
                session = self.active_sessions[session_id]
                session.status = SessionStatus.EXPIRED

                # 清理令牌映射
                tokens_to_remove = [
                    token
                    for token, sid in self.session_tokens.items()
                    if sid == session_id
                ]
                for token in tokens_to_remove:
                    del self.session_tokens[token]

            logger.info(f"过期会话已清理: {len(expired_sessions)} 个会话")
            return len(expired_sessions)

    def _generate_session_token(self, session_id: str, user_id: str) -> str:
        """生成会话令牌

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            会话令牌
        """
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.session_timeout,
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def get_user_sessions(self, user_id: str) -> list[UserSession]:
        """获取用户会话列表

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        with self._lock:
            return [
                session
                for session in self.active_sessions.values()
                if session.user_id == user_id
            ]

    def get_session_stats(self) -> dict[str, Any]:
        """获取会话统计

        Returns:
            统计信息
        """
        with self._lock:
            total_sessions = len(self.active_sessions)
            active_sessions = sum(
                1
                for session in self.active_sessions.values()
                if session.status == SessionStatus.ACTIVE
            )

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": total_sessions - active_sessions,
                "tokens_count": len(self.session_tokens),
            }


class SecurityAuditor:
    """安全审计器"""

    def __init__(self):
        """初始化安全审计器"""
        self.login_attempts: list[LoginAttempt] = []
        self.security_events: list[SecurityEvent] = []
        self.failed_attempts: dict[str, list[LoginAttempt]] = {}  # user_id -> attempts
        self.ip_blacklist: set[str] = set()
        self.user_blacklist: set[str] = set()

        # 安全策略
        self.max_failed_attempts = 5
        self.lockout_duration = 900  # 15分钟
        self.ip_block_duration = 3600  # 1小时

        logger.info("安全审计器已初始化")

    def record_login_attempt(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        auth_method: AuthMethod = AuthMethod.PASSWORD,
        failure_reason: str | None = None,
    ) -> None:
        """记录登录尝试

        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            success: 是否成功
            auth_method: 认证方法
            failure_reason: 失败原因
        """
        attempt = LoginAttempt(
            user_id=user_id,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            auth_method=auth_method,
        )

        self.login_attempts.append(attempt)

        # 记录失败尝试
        if not success:
            if user_id not in self.failed_attempts:
                self.failed_attempts[user_id] = []
            self.failed_attempts[user_id].append(attempt)

            # 检查是否需要锁定
            self._check_user_lockout(user_id)
            self._check_ip_block(ip_address)

        logger.info(f"登录尝试已记录: {user_id} - {'成功' if success else '失败'}")

    def record_security_event(
        self,
        user_id: str | None,
        event_type: str,
        severity: SecurityLevel,
        description: str,
        ip_address: str,
        user_agent: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """记录安全事件

        Args:
            user_id: 用户ID
            event_type: 事件类型
            severity: 严重程度
            description: 描述
            ip_address: IP地址
            user_agent: 用户代理
            metadata: 元数据
        """
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self.security_events.append(event)

        # 根据严重程度采取行动
        if severity == SecurityLevel.CRITICAL:
            self._handle_critical_event(event)
        elif severity == SecurityLevel.HIGH:
            self._handle_high_severity_event(event)

        logger.warning(f"安全事件已记录: {event_type} - {severity.value}")

    def _check_user_lockout(self, user_id: str) -> None:
        """检查用户锁定

        Args:
            user_id: 用户ID
        """
        if user_id not in self.failed_attempts:
            return

        # 获取最近的失败尝试
        recent_attempts = [
            attempt
            for attempt in self.failed_attempts[user_id]
            if datetime.now() - attempt.timestamp
            < timedelta(seconds=self.lockout_duration)
        ]

        if len(recent_attempts) >= self.max_failed_attempts:
            self.user_blacklist.add(user_id)
            self.record_security_event(
                user_id=user_id,
                event_type="user_lockout",
                severity=SecurityLevel.HIGH,
                description=f"用户 {user_id} 因多次失败登录被锁定",
                ip_address="",
                user_agent="",
            )

    def _check_ip_block(self, ip_address: str) -> None:
        """检查IP封锁

        Args:
            ip_address: IP地址
        """
        # 统计该IP的失败尝试
        failed_count = sum(
            1
            for attempt in self.login_attempts
            if attempt.ip_address == ip_address
            and not attempt.success
            and datetime.now() - attempt.timestamp
            < timedelta(seconds=self.ip_block_duration)
        )

        if failed_count >= self.max_failed_attempts * 2:
            self.ip_blacklist.add(ip_address)
            self.record_security_event(
                user_id=None,
                event_type="ip_block",
                severity=SecurityLevel.HIGH,
                description=f"IP {ip_address} 因多次失败登录被封锁",
                ip_address=ip_address,
                user_agent="",
            )

    def _handle_critical_event(self, event: SecurityEvent) -> None:
        """处理严重事件

        Args:
            event: 安全事件
        """
        # 立即锁定相关用户
        if event.user_id:
            self.user_blacklist.add(event.user_id)

        # 封锁IP
        self.ip_blacklist.add(event.ip_address)

        logger.critical(f"严重安全事件: {event.event_type} - {event.description}")

    def _handle_high_severity_event(self, event: SecurityEvent) -> None:
        """处理高严重程度事件

        Args:
            event: 安全事件
        """
        # 记录并监控
        logger.warning(f"高严重程度安全事件: {event.event_type} - {event.description}")

    def is_user_blocked(self, user_id: str) -> bool:
        """检查用户是否被封锁

        Args:
            user_id: 用户ID

        Returns:
            是否被封锁
        """
        return user_id in self.user_blacklist

    def is_ip_blocked(self, ip_address: str) -> bool:
        """检查IP是否被封锁

        Args:
            ip_address: IP地址

        Returns:
            是否被封锁
        """
        return ip_address in self.ip_blacklist

    def get_security_report(self) -> dict[str, Any]:
        """获取安全报告

        Returns:
            安全报告
        """
        # 统计登录尝试
        total_attempts = len(self.login_attempts)
        successful_attempts = sum(
            1 for attempt in self.login_attempts if attempt.success
        )
        failed_attempts = total_attempts - successful_attempts

        # 统计安全事件
        events_by_severity = {}
        for event in self.security_events:
            severity = event.severity.value
            events_by_severity[severity] = events_by_severity.get(severity, 0) + 1

        return {
            "login_attempts": {
                "total": total_attempts,
                "successful": successful_attempts,
                "failed": failed_attempts,
                "success_rate": successful_attempts / total_attempts
                if total_attempts > 0
                else 0.0,
            },
            "security_events": {
                "total": len(self.security_events),
                "by_severity": events_by_severity,
            },
            "blocked_users": len(self.user_blacklist),
            "blocked_ips": len(self.ip_blacklist),
            "failed_attempts_by_user": {
                user_id: len(attempts)
                for user_id, attempts in self.failed_attempts.items()
            },
        }


class AdvancedAuth:
    """高级认证系统"""

    def __init__(self, secret_key: str, session_timeout: int = 3600):
        """初始化高级认证系统

        Args:
            secret_key: 密钥
            session_timeout: 会话超时时间（秒）
        """
        self.secret_key = secret_key
        self.mfa = MultiFactorAuth(secret_key)
        self.session_manager = SessionManager(secret_key, session_timeout)
        self.security_auditor = SecurityAuditor()

        # 用户认证配置
        self.user_auth_configs: dict[str, dict[str, Any]] = {}

        logger.info("高级认证系统已初始化")

    def register_user_auth_config(
        self,
        user_id: str,
        totp_secret: str | None = None,
        backup_codes: list[str] | None = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> None:
        """注册用户认证配置

        Args:
            user_id: 用户ID
            totp_secret: TOTP密钥
            backup_codes: 备份代码
            security_level: 安全级别
        """
        self.user_auth_configs[user_id] = {
            "totp_secret": totp_secret or self.mfa.generate_totp_secret(user_id),
            "backup_codes": backup_codes or self.mfa.generate_backup_codes(),
            "security_level": security_level,
            "created_at": datetime.now(),
        }

        logger.info(f"用户认证配置已注册: {user_id}")

    def authenticate_user(
        self,
        user_id: str,
        password: str,
        ip_address: str,
        user_agent: str,
        totp_code: str | None = None,
        backup_code: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """认证用户

        Args:
            user_id: 用户ID
            password: 密码
            ip_address: IP地址
            user_agent: 用户代理
            totp_code: TOTP代码
            backup_code: 备份代码

        Returns:
            (是否成功, 会话令牌, 错误信息)
        """
        # 检查用户是否被封锁
        if self.security_auditor.is_user_blocked(user_id):
            self.security_auditor.record_login_attempt(
                user_id,
                ip_address,
                user_agent,
                False,
                AuthMethod.PASSWORD,
                "用户被封锁",
            )
            return False, None, "用户被封锁"

        # 检查IP是否被封锁
        if self.security_auditor.is_ip_blocked(ip_address):
            self.security_auditor.record_login_attempt(
                user_id, ip_address, user_agent, False, AuthMethod.PASSWORD, "IP被封锁"
            )
            return False, None, "IP被封锁"

        # 验证密码（这里应该与实际的密码验证逻辑集成）
        password_valid = self._verify_password(user_id, password)

        if not password_valid:
            self.security_auditor.record_login_attempt(
                user_id, ip_address, user_agent, False, AuthMethod.PASSWORD, "密码错误"
            )
            return False, None, "密码错误"

        # 检查是否需要多因素认证
        auth_config = self.user_auth_configs.get(user_id)
        if auth_config and auth_config["security_level"] in [
            SecurityLevel.HIGH,
            SecurityLevel.CRITICAL,
        ]:
            if not totp_code and not backup_code:
                return False, None, "需要多因素认证"

            # 验证TOTP代码
            if totp_code and not self.mfa.verify_totp_code(
                auth_config["totp_secret"], totp_code
            ):
                self.security_auditor.record_login_attempt(
                    user_id,
                    ip_address,
                    user_agent,
                    False,
                    AuthMethod.TOTP,
                    "TOTP代码错误",
                )
                return False, None, "TOTP代码错误"

            # 验证备份代码
            if backup_code and not self.mfa.verify_backup_code(
                backup_code, auth_config["backup_codes"]
            ):
                self.security_auditor.record_login_attempt(
                    user_id,
                    ip_address,
                    user_agent,
                    False,
                    AuthMethod.PASSWORD,
                    "备份代码错误",
                )
                return False, None, "备份代码错误"

        # 创建会话
        auth_methods = [AuthMethod.PASSWORD]
        if totp_code:
            auth_methods.append(AuthMethod.TOTP)
        if backup_code:
            auth_methods.append(AuthMethod.PASSWORD)  # 备份代码也算密码认证

        security_level = (
            auth_config["security_level"] if auth_config else SecurityLevel.MEDIUM
        )

        token, session = self.session_manager.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            auth_methods=auth_methods,
            security_level=security_level,
        )

        # 记录成功登录
        self.security_auditor.record_login_attempt(
            user_id, ip_address, user_agent, True, AuthMethod.PASSWORD
        )

        logger.info(f"用户认证成功: {user_id}")
        return True, token, None

    def _verify_password(self, _user_id: str, _password: str) -> bool:
        """验证密码

        Args:
            user_id: 用户ID
            password: 密码

        Returns:
            是否有效
        """
        # 这里应该与实际的密码验证逻辑集成
        # 暂时返回True用于测试
        return True

    def validate_session(self, token: str) -> UserSession | None:
        """验证会话

        Args:
            token: 会话令牌

        Returns:
            会话对象
        """
        return self.session_manager.validate_session(token)

    def logout(self, token: str) -> bool:
        """登出

        Args:
            token: 会话令牌

        Returns:
            是否成功
        """
        return self.session_manager.revoke_session(token)

    def get_security_report(self) -> dict[str, Any]:
        """获取安全报告

        Returns:
            安全报告
        """
        return self.security_auditor.get_security_report()

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话

        Returns:
            清理的会话数量
        """
        return self.session_manager.cleanup_expired_sessions()
