"""
认证授权模块

支持JWT认证、RBAC权限控制、密码加密等
"""

import hashlib
import hmac
import logging
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any

import jwt

logger = logging.getLogger(__name__)


class Role(Enum):
    """角色枚举"""

    ADMIN = "admin"
    STUDENT = "student"
    GUEST = "guest"


class Permission(Enum):
    """权限枚举"""

    # 实验相关
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_UPDATE = "experiment:update"
    EXPERIMENT_DELETE = "experiment:delete"
    EXPERIMENT_RUN = "experiment:run"

    # 报告相关
    REPORT_CREATE = "report:create"
    REPORT_READ = "report:read"
    REPORT_UPDATE = "report:update"
    REPORT_DELETE = "report:delete"
    REPORT_EXPORT = "report:export"

    # 用户相关
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # 系统管理
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"


@dataclass
class User:
    """用户"""

    id: str
    username: str
    email: str
    password_hash: str
    roles: list[Role] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Token:
    """令牌"""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int = 3600  # 秒
    expires_at: datetime | None = None


@dataclass
class AuthContext:
    """认证上下文"""

    user: User
    token: Token
    permissions: set[Permission]

    def has_permission(self, permission: Permission) -> bool:
        """检查权限"""
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        """检查角色"""
        return role in self.user.roles

    def has_any_role(self, *roles: Role) -> bool:
        """检查是否拥有任一角色"""
        return any(role in self.user.roles for role in roles)

    def has_all_roles(self, *roles: Role) -> bool:
        """检查是否拥有所有角色"""
        return all(role in self.user.roles for role in roles)


class PasswordHasher:
    """密码哈希工具"""

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # iterations
        )

        return password_hash.hex(), salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = PasswordHasher.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)


class JWTManager:
    """JWT管理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire: int = 3600,
        refresh_token_expire: int = 86400 * 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire

    def create_access_token(self, user_id: str, extra_claims: dict[str, Any] | None = None) -> str:
        """创建访问令牌"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.access_token_expire)

        payload = {"sub": user_id, "iat": now, "exp": expires, "type": "access"}

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.refresh_token_expire)

        payload = {"sub": user_id, "iat": now, "exp": expires, "type": "refresh"}

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """解码令牌"""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError as e:
            raise ValueError("令牌已过期") from e
        except jwt.InvalidTokenError as e:
            raise ValueError("无效的令牌") from e

    def verify_token(self, token: str, token_type: str = "access") -> str | None:
        """验证令牌"""
        try:
            payload = self.decode_token(token)
            if payload.get("type") != token_type:
                raise ValueError(f"期望的令牌类型: {token_type}")
            return payload.get("sub")
        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            return None


class RBACManager:
    """基于角色的访问控制管理器"""

    def __init__(self):
        self._role_permissions: dict[Role, set[Permission]] = {
            Role.ADMIN: set(Permission),  # 管理员拥有所有权限
            Role.STUDENT: {
                Permission.EXPERIMENT_READ,
                Permission.EXPERIMENT_RUN,
                Permission.REPORT_CREATE,
                Permission.REPORT_READ,
            },
            Role.GUEST: {
                Permission.EXPERIMENT_READ,
                Permission.REPORT_READ,
            },
        }

    def get_permissions(self, roles: list[Role]) -> set[Permission]:
        """获取角色的权限"""
        permissions = set()
        for role in roles:
            permissions.update(self._role_permissions.get(role, set()))
        return permissions

    def add_permission_to_role(self, role: Role, permission: Permission) -> None:
        """为角色添加权限"""
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].add(permission)

    def remove_permission_from_role(self, role: Role, permission: Permission) -> None:
        """从角色移除权限"""
        if role in self._role_permissions:
            self._role_permissions[role].discard(permission)

    def has_permission(self, roles: list[Role], permission: Permission) -> bool:
        """检查角色是否拥有权限"""
        return permission in self.get_permissions(roles)


class IAuthService(ABC):
    """认证服务接口"""

    @abstractmethod
    def authenticate(self, username: str, password: str) -> AuthContext | None:
        """认证用户"""
        pass

    @abstractmethod
    def authorize(self, token: str) -> AuthContext | None:
        """授权（验证令牌）"""
        pass

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Token | None:
        """刷新令牌"""
        pass

    @abstractmethod
    def logout(self, token: str) -> bool:
        """登出"""
        pass


class AuthService(IAuthService):
    """认证服务实现"""

    def __init__(
        self,
        jwt_manager: JWTManager,
        rbac_manager: RBACManager,
        user_repository: Any,  # IUserRepository
    ):
        self.jwt_manager = jwt_manager
        self.rbac_manager = rbac_manager
        self.user_repository = user_repository
        self._blacklist: set[str] = set()  # 令牌黑名单

    def authenticate(self, username: str, password: str) -> AuthContext | None:
        """认证用户"""
        # 查找用户
        user = self.user_repository.find_by_username(username)

        if not user or not user.is_active:
            logger.warning(f"认证失败: 用户不存在或未激活 - {username}")
            return None

        # 验证密码（这里简化处理，实际应从数据库获取salt）
        if not self._verify_password(password, user.password_hash):
            logger.warning(f"认证失败: 密码错误 - {username}")
            return None

        # 创建令牌
        access_token = self.jwt_manager.create_access_token(user.id)
        refresh_token = self.jwt_manager.create_refresh_token(user.id)

        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.jwt_manager.access_token_expire,
        )

        # 获取权限
        permissions = self.rbac_manager.get_permissions(user.roles)

        # 更新最后登录时间
        user.last_login = datetime.now()

        logger.info(f"用户认证成功: {username}")

        return AuthContext(user=user, token=token, permissions=permissions)

    def authorize(self, token: str) -> AuthContext | None:
        """授权"""
        # 检查黑名单
        if token in self._blacklist:
            logger.warning("令牌在黑名单中")
            return None

        # 验证令牌
        user_id = self.jwt_manager.verify_token(token)

        if not user_id:
            return None

        # 获取用户
        user = self.user_repository.find_by_id(user_id)

        if not user or not user.is_active:
            return None

        # 获取权限
        permissions = self.rbac_manager.get_permissions(user.roles)

        token_obj = Token(access_token=token)

        return AuthContext(user=user, token=token_obj, permissions=permissions)

    def refresh_token(self, refresh_token: str) -> Token | None:
        """刷新令牌"""
        user_id = self.jwt_manager.verify_token(refresh_token, token_type="refresh")

        if not user_id:
            return None

        # 创建新的访问令牌
        access_token = self.jwt_manager.create_access_token(user_id)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # 刷新令牌保持不变
            expires_in=self.jwt_manager.access_token_expire,
        )

    def logout(self, token: str) -> bool:
        """登出"""
        # 添加到黑名单
        self._blacklist.add(token)
        logger.info("用户已登出")
        return True

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码

        Args:
            password: 明文密码
            stored_hash: 存储的密码哈希(格式: hash$salt 或 旧格式hash)

        Returns:
            是否验证通过
        """
        # 新格式: hash$salt
        if "$" in stored_hash:
            hash_part, salt = stored_hash.split("$", 1)
            computed_hash, _ = PasswordHasher.hash_password(password, salt)
            return hmac.compare_digest(computed_hash, hash_part)

        # 兼容旧格式(SHA256,不安全,仅用于向后兼容)
        logger.warning("使用旧密码格式,建议升级")
        return stored_hash == hashlib.sha256(password.encode()).hexdigest()


# 装饰器
def require_auth(func):
    """需要认证的装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 从上下文获取token（实际应用中从请求头获取）
        token = kwargs.get("token") or getattr(args[0], "token", None)

        if not token:
            raise PermissionError("需要认证")

        # 验证token（需要从容器获取auth_service）
        # auth_service = get_auth_service()
        # context = auth_service.authorize(token)

        # if not context:
        #     raise PermissionError("认证失败")

        return func(*args, **kwargs)

    return wrapper


def require_permission(permission: Permission):
    """需要权限的装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从上下文获取权限
            context = kwargs.get("auth_context")

            if not context or not context.has_permission(permission):
                raise PermissionError(f"需要权限: {permission.value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*roles: Role):
    """需要角色的装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = kwargs.get("auth_context")

            if not context or not context.has_any_role(*roles):
                raise PermissionError(f"需要角色: {[r.value for r in roles]}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


# 简单的用户仓储（用于演示）
class SimpleUserRepository:
    """简单用户仓储"""

    def __init__(self):
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.id] = user

    def find_by_username(self, username: str) -> User | None:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)


# 导出 DeveloperAuth (从 dev_auth 模块)
try:
    from .dev_auth import DeveloperAuth
except ImportError:
    logger.warning("DeveloperAuth 模块未找到，开发者模式功能将不可用")
    DeveloperAuth = None  # type: ignore


if __name__ == "__main__":
    logger.info("=== 认证授权系统演示 ===\n")

    # 1. 创建用户
    logger.info("1. 创建用户:")
    password_hash = hashlib.sha256(b"password123").hexdigest()

    user = User(
        id="user_001",
        username="student1",
        email="student1@example.com",
        password_hash=password_hash,
        roles=[Role.STUDENT],
    )

    user_repo = SimpleUserRepository()
    user_repo.add(user)
    logger.info(f"用户已创建: {user.username}\n")

    # 2. 创建JWT管理器和RBAC管理器
    logger.info("2. 初始化认证系统:")
    jwt_manager = JWTManager(secret_key="your-secret-key")
    rbac_manager = RBACManager()

    # 3. 创建认证服务
    auth_service = AuthService(jwt_manager, rbac_manager, user_repo)

    # 4. 认证用户
    logger.info("3. 用户认证:")
    context = auth_service.authenticate("student1", "password123")

    if context:
        logger.info("✅ 认证成功")
        logger.info(f"用户: {context.user.username}")
        logger.info(f"角色: {[r.value for r in context.user.roles]}")
        logger.info(f"权限数: {len(context.permissions)}")
        logger.info(f"访问令牌: {context.token.access_token[:50]}...\n")

        # 5. 检查权限
        logger.info("4. 权限检查:")
        logger.info(f"可以运行实验: {context.has_permission(Permission.EXPERIMENT_RUN)}")
        logger.info(f"可以删除用户: {context.has_permission(Permission.USER_DELETE)}")
        logger.info(f"是否学生角色: {context.has_role(Role.STUDENT)}\n")

        # 6. 授权（验证令牌）
        logger.info("5. 令牌授权:")
        new_context = auth_service.authorize(context.token.access_token)
        if new_context:
            logger.info(f"✅ 授权成功: {new_context.user.username}\n")

    logger.info("✅ 演示完成")


def create_jwt_manager_from_config(config=None) -> JWTManager:
    """从配置创建JWT管理器

    Args:
        config: 配置对象 (Config或IConfig)
               如果为None，从环境变量读取

    Returns:
        JWTManager: JWT管理器实例

    Raises:
        ValueError: 如果密钥未设置

    Examples:
        # 从环境变量
        jwt_manager = create_jwt_manager_from_config()

        # 从配置对象
        from src.core.config_loader import get_config
        config = get_config()
        jwt_manager = create_jwt_manager_from_config(config)
    """
    secret_key = None
    algorithm = "HS256"
    access_expire = 3600
    refresh_expire = 86400 * 7

    # 尝试从配置对象获取
    if config:
        try:
            # 新配置系统 (Config from config_loader)
            if hasattr(config, "security"):
                secret_key = config.security.jwt_secret_key
                algorithm = config.security.jwt_algorithm
                access_expire = config.security.jwt_expiration
        except AttributeError:
            pass

        try:
            # 旧配置系统 (IConfig)
            if hasattr(config, "get"):
                secret_key = config.get("security.jwt_secret", None)
                algorithm = config.get("security.jwt_algorithm", "HS256")
                access_expire = config.get("security.jwt_expiration", 3600)
        except Exception:
            pass

    # 从环境变量获取 (优先级最高)
    secret_key = os.getenv("JWT_SECRET_KEY", secret_key)

    # 验证密钥
    if not secret_key:
        raise ValueError("JWT密钥未设置！请设置环境变量 JWT_SECRET_KEY 或在配置文件中设置")

    if secret_key == "change-this-in-production" or secret_key == "your-secret-key":
        logger.warning("⚠️ 警告：正在使用默认JWT密钥，生产环境请更换！")

    if len(secret_key) < 32:
        raise ValueError("JWT密钥长度必须至少32个字符")

    return JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire=access_expire,
        refresh_token_expire=refresh_expire,
    )
