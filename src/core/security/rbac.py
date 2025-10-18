import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any

"""基于角色的访问控制 (RBAC) 系统"""

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""

    # 实验相关权限
    CREATE_EXPERIMENT = "create_experiment"
    EDIT_EXPERIMENT = "edit_experiment"
    DELETE_EXPERIMENT = "delete_experiment"
    VIEW_EXPERIMENT = "view_experiment"
    START_EXPERIMENT = "start_experiment"
    PAUSE_EXPERIMENT = "pause_experiment"
    RESUME_EXPERIMENT = "resume_experiment"
    CANCEL_EXPERIMENT = "cancel_experiment"

    # 模板相关权限
    CREATE_TEMPLATE = "create_template"
    EDIT_TEMPLATE = "edit_template"
    DELETE_TEMPLATE = "delete_template"
    VIEW_TEMPLATE = "view_template"

    # 用户记录权限
    VIEW_OWN_RECORDS = "view_own_records"
    VIEW_ALL_RECORDS = "view_all_records"
    EXPORT_RECORDS = "export_records"

    # 系统管理权限
    VIEW_SYSTEM_STATUS = "view_system_status"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_LOGS = "view_logs"

    # 高级功能权限
    USE_ADVANCED_FEATURES = "use_advanced_features"
    ACCESS_DEBUG_MODE = "access_debug_mode"
    MANAGE_PLUGINS = "manage_plugins"


class Role(Enum):
    """角色枚举"""

    STUDENT = "student"
    ADMIN = "admin"
    GUEST = "guest"


@dataclass
class User:
    """用户信息"""

    user_id: str
    username: str
    role: Role
    permissions: set[Permission]
    created_at: datetime
    last_login: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class RBACManager:
    """基于角色的访问控制管理器"""

    def __init__(self) -> None:
        # 角色权限映射
        self.role_permissions = {
            Role.GUEST: {
                Permission.VIEW_EXPERIMENT,
                Permission.VIEW_TEMPLATE,
            },
            Role.STUDENT: {
                Permission.CREATE_EXPERIMENT,
                Permission.EDIT_EXPERIMENT,
                Permission.VIEW_EXPERIMENT,
                Permission.START_EXPERIMENT,
                Permission.PAUSE_EXPERIMENT,
                Permission.RESUME_EXPERIMENT,
                Permission.CANCEL_EXPERIMENT,
                Permission.VIEW_TEMPLATE,
                Permission.VIEW_OWN_RECORDS,
                Permission.USE_ADVANCED_FEATURES,
            },
            Role.ADMIN: set(Permission),  # 管理员拥有所有权限
        }

        # 用户会话管理
        self.active_sessions: dict[str, User] = {}
        self.session_timeout = timedelta(hours=8)

        logger.info("RBAC管理器已初始化")

    def create_user(self, user_id: str, username: str, role: Role, metadata: dict | None = None) -> User:
        """创建用户

        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            metadata: 用户元数据

        Returns:
            用户对象
        """
        permissions = self.role_permissions.get(role, set())
        user = User(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions,
            created_at=datetime.now(),
            metadata=metadata or {},
        )

        logger.info(f"创建用户: {username} (角色: {role.value})")
        return user

    def has_permission(self, user: User, permission: Permission) -> bool:
        """检查用户是否有指定权限

        Args:
            user: 用户对象
            permission: 权限

        Returns:
            是否有权限
        """
        if not user.is_active:
            return False

        return permission in user.permissions

    def has_any_permission(self, user: User, permissions: list[Permission]) -> bool:
        """检查用户是否有任意一个权限

        Args:
            user: 用户对象
            permissions: 权限列表

        Returns:
            是否有任意权限
        """
        return any(self.has_permission(user, perm) for perm in permissions)

    def has_all_permissions(self, user: User, permissions: list[Permission]) -> bool:
        """检查用户是否有所有权限

        Args:
            user: 用户对象
            permissions: 权限列表

        Returns:
            是否有所有权限
        """
        return all(self.has_permission(user, perm) for perm in permissions)

    def add_permission(self, user: User, permission: Permission) -> bool:
        """为用户添加权限

        Args:
            user: 用户对象
            permission: 权限

        Returns:
            是否成功添加
        """
        if permission not in user.permissions:
            user.permissions.add(permission)
            logger.info(f"为用户 {user.username} 添加权限: {permission.value}")
            return True
        return False

    def remove_permission(self, user: User, permission: Permission) -> bool:
        """移除用户权限

        Args:
            user: 用户对象
            permission: 权限

        Returns:
            是否成功移除
        """
        if permission in user.permissions:
            user.permissions.remove(permission)
            logger.info(f"移除用户 {user.username} 权限: {permission.value}")
            return True
        return False

    def change_user_role(self, user: User, new_role: Role) -> bool:
        """更改用户角色

        Args:
            user: 用户对象
            new_role: 新角色

        Returns:
            是否成功更改
        """
        old_role = user.role
        user.role = new_role
        user.permissions = self.role_permissions.get(new_role, set())

        logger.info(f"用户 {user.username} 角色从 {old_role.value} 更改为 {new_role.value}")
        return True

    def create_session(self, user: User, session_id: str) -> bool:
        """创建用户会话

        Args:
            user: 用户对象
            session_id: 会话ID

        Returns:
            是否成功创建
        """
        if not user.is_active:
            return False

        user.last_login = datetime.now()
        self.active_sessions[session_id] = user

        logger.info(f"创建用户会话: {user.username} ({session_id})")
        return True

    def get_user_from_session(self, session_id: str) -> User | None:
        """从会话获取用户

        Args:
            session_id: 会话ID

        Returns:
            用户对象或None
        """
        user = self.active_sessions.get(session_id)
        if user and user.is_active:
            # 检查会话是否过期
            if user.last_login and datetime.now() - user.last_login > self.session_timeout:
                self.remove_session(session_id)
                return None
            return user
        return None

    def remove_session(self, session_id: str) -> bool:
        """移除用户会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功移除
        """
        if session_id in self.active_sessions:
            user = self.active_sessions.pop(session_id)
            logger.info(f"移除用户会话: {user.username} ({session_id})")
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话

        Returns:
            清理的会话数量
        """
        expired_sessions = []
        now = datetime.now()

        for session_id, user in self.active_sessions.items():
            if user.last_login and now - user.last_login > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.remove_session(session_id)

        if expired_sessions:
            logger.info(f"清理了 {len(expired_sessions)} 个过期会话")

        return len(expired_sessions)

    def get_user_permissions(self, user: User) -> list[Permission]:
        """获取用户权限列表

        Args:
            user: 用户对象

        Returns:
            权限列表
        """
        return list(user.permissions)

    def check_resource_access(self, user: User, resource_type: str, _resource_id: str, action: str) -> bool:
        """检查资源访问权限

        Args:
            user: 用户对象
            resource_type: 资源类型 (experiment, template, record)
            resource_id: 资源ID
            action: 操作 (view, edit, delete)

        Returns:
            是否有访问权限
        """
        # 管理员拥有所有权限
        if user.role == Role.ADMIN:
            return True

        # 根据资源类型和操作检查权限
        if resource_type == "experiment":
            if action == "view":
                return self.has_permission(user, Permission.VIEW_EXPERIMENT)
            elif action == "edit":
                return self.has_permission(user, Permission.EDIT_EXPERIMENT)
            elif action == "delete":
                return self.has_permission(user, Permission.DELETE_EXPERIMENT)

        elif resource_type == "template":
            if action == "view":
                return self.has_permission(user, Permission.VIEW_TEMPLATE)
            elif action == "edit":
                return self.has_permission(user, Permission.EDIT_TEMPLATE)
            elif action == "delete":
                return self.has_permission(user, Permission.DELETE_TEMPLATE)

        elif resource_type == "record" and action == "view":
            # 学生只能查看自己的记录，管理员可以查看所有记录
            if user.role == Role.STUDENT:
                return self.has_permission(user, Permission.VIEW_OWN_RECORDS)
            elif user.role == Role.ADMIN:
                return self.has_permission(user, Permission.VIEW_ALL_RECORDS)

        return False


# 全局RBAC管理器实例
rbac_manager = RBACManager()


def require_permission(permission: Permission):
    """权限装饰器

    Args:
        permission: 需要的权限
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从参数中获取用户信息
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break

            if not user:
                logger.error("权限检查失败: 未找到用户信息")
                raise PermissionError("权限检查失败: 未找到用户信息")

            if not rbac_manager.has_permission(user, permission):
                logger.warning(f"用户 {user.username} 缺少权限: {permission.value}")
                raise PermissionError(f"缺少权限: {permission.value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: list[Permission]):
    """需要任意权限的装饰器

    Args:
        permissions: 权限列表
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break

            if not user:
                logger.error("权限检查失败: 未找到用户信息")
                raise PermissionError("权限检查失败: 未找到用户信息")

            if not rbac_manager.has_any_permission(user, permissions):
                logger.warning(f"用户 {user.username} 缺少权限: {[p.value for p in permissions]}")
                raise PermissionError(f"缺少权限: {[p.value for p in permissions]}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: Role):
    """角色装饰器

    Args:
        role: 需要的角色
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break

            if not user:
                logger.error("角色检查失败: 未找到用户信息")
                raise PermissionError("角色检查失败: 未找到用户信息")

            if user.role != role and user.role != Role.ADMIN:
                logger.warning(f"用户 {user.username} 角色不匹配: 需要 {role.value}, 实际 {user.role.value}")
                raise PermissionError(f"需要角色: {role.value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionError(Exception):
    """权限错误"""

    pass
