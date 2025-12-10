"""
开发者模式认证管理
提供开发者模式的安全认证和权限管理
"""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..utils.logger import get_logger

logger = get_logger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    """读取布尔环境变量，支持常见真值字符串"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class DevSession:
    """开发者会话"""

    session_id: str
    activated_at: datetime
    expires_at: datetime
    features_enabled: dict[str, bool]

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.now() > self.expires_at

    def has_feature(self, feature: str) -> bool:
        """检查是否启用某个功能"""
        return self.features_enabled.get(feature, False)


class DeveloperAuth:
    """开发者模式认证管理器"""

    def __init__(self, config_path: str = "config.json"):
        """初始化开发者认证管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._current_session: DevSession | None = None
        self._failed_attempts = 0
        self._max_attempts = 5
        self._lockout_duration = timedelta(minutes=15)
        self._lockout_until: datetime | None = None
        self._app_environment = os.getenv("ENVIRONMENT", "development")
        self.dev_mode_enabled = False
        self._secret_sequences: list[str] = []
        self._allow_secret_sequences = False

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置"""
        self.dev_config: dict[str, object] = {}
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)

            self.dev_config = config.get("developer", {})
            app_config = config.get("app", {})
            self._app_environment = app_config.get("environment", self._app_environment)

            # 获取开发者密钥哈希（优先环境变量）
            self.dev_key_hash = self._resolve_dev_key_hash()

            # 会话超时时间(小时)
            self.session_timeout = self.dev_config.get("session_timeout_hours", 24)

            # 启用的功能列表
            self.enabled_features = self.dev_config.get(
                "enabled_features",
                [
                    "debug_console",
                    "log_viewer",
                    "performance_monitor",
                    "config_editor",
                    "database_viewer",
                    "api_tester",
                ],
            )

            if self.dev_config.get("enabled", False) and not self.dev_key_hash:
                logger.error(
                    "开发者模式已启用但未配置开发者密钥，已自动禁用。"
                    "请通过环境变量 DEVELOPER_KEY_HASH 配置密钥哈希值。"
                )
                self.dev_config["enabled"] = False

        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {self.config_path}, 使用默认配置")
            self.session_timeout = 24
            self.enabled_features = ["debug_console", "log_viewer"]
            self.dev_key_hash = ""
            self._app_environment = os.getenv("ENVIRONMENT", "development")

        self._update_dev_mode_flags()

    def _update_dev_mode_flags(self) -> None:
        """应用环境与配置开关，统一控制开发者模式可用性"""
        env = (self._app_environment or "development").lower()
        base_enabled = bool(self.dev_config.get("enabled", False))
        # 生产环境必须显式通过环境变量开启
        if env == "production":
            self.dev_mode_enabled = _env_flag("DEVELOPER_MODE_ENABLED", False)
        else:
            self.dev_mode_enabled = _env_flag("DEVELOPER_MODE_ENABLED", base_enabled)

        self._secret_sequences = [s.strip().upper() for s in self.dev_config.get("secret_sequences", []) if s]
        self._allow_secret_sequences = (
            self.dev_mode_enabled and env != "production" and bool(self._secret_sequences)
        )

    def _resolve_dev_key_hash(self) -> str:
        """解析开发者密钥哈希（优先使用环境变量）"""
        env_key_hash = (os.getenv("DEVELOPER_KEY_HASH") or "").strip()
        if env_key_hash:
            return env_key_hash

        file_key_hash = self.dev_config.get("key_hash", "") if hasattr(self, "dev_config") else ""
        if file_key_hash:
            logger.warning(
                "检测到开发者密钥哈希存储在 config.json 中。"
                "建议将其移动到环境变量 DEVELOPER_KEY_HASH，以避免敏感信息进入版本库。"
            )
            return file_key_hash

        return ""

    @staticmethod
    def _hash_key(key: str, salt: str = "") -> str:
        """生成密钥哈希

        Args:
            key: 密钥
            salt: 盐值

        Returns:
            哈希值
        """
        if not salt:
            salt = secrets.token_hex(16)

        hash_obj = hashlib.pbkdf2_hmac("sha256", key.encode(), salt.encode(), 100000)
        return f"{hash_obj.hex()}${salt}"

    def _verify_key(self, key: str, stored_hash: str) -> bool:
        """验证密钥

        Args:
            key: 输入的密钥
            stored_hash: 存储的哈希值

        Returns:
            是否验证通过
        """
        if "$" not in stored_hash:
            # 如果没有盐值，直接比较（兼容旧配置）
            return key == stored_hash or self._hash_key(key).split("$")[0] == stored_hash

        hash_part, salt = stored_hash.split("$", 1)
        computed_hash = self._hash_key(key, salt).split("$")[0]

        return hmac.compare_digest(computed_hash, hash_part)

    def is_locked_out(self) -> bool:
        """检查是否被锁定"""
        if self._lockout_until and datetime.now() < self._lockout_until:
            return True

        # 锁定期已过，重置
        if self._lockout_until:
            self._lockout_until = None
            self._failed_attempts = 0

        return False

    def authenticate(self, dev_key: str) -> bool:
        """认证开发者密钥

        Args:
            dev_key: 开发者密钥

        Returns:
            是否认证成功
        """
        if not self._is_dev_mode_allowed():
            logger.warning("当前环境未启用开发者模式，拒绝认证请求")
            return False

        # 检查锁定状态
        if self.is_locked_out():
            remaining = int((self._lockout_until - datetime.now()).total_seconds() / 60)
            logger.warning(f"开发者模式已锁定，剩余 {remaining} 分钟")
            return False

        if not self.dev_key_hash:
            logger.error(
                "开发者密钥未配置，拒绝激活开发者模式。"
                "请设置环境变量 DEVELOPER_KEY_HASH 或运行 tools/setup_dev_key.py 生成密钥。"
            )
            return False

        # 验证密钥
        is_valid = self._verify_key(dev_key, self.dev_key_hash)

        if is_valid:
            # 认证成功，创建会话
            self._failed_attempts = 0
            self._create_session()
            logger.info("开发者模式已激活")
            return True
        else:
            # 认证失败
            self._failed_attempts += 1
            logger.warning(f"开发者密钥验证失败 (尝试 {self._failed_attempts}/{self._max_attempts})")

            # 达到最大尝试次数，锁定
            if self._failed_attempts >= self._max_attempts:
                self._lockout_until = datetime.now() + self._lockout_duration
                logger.error(f"开发者模式已锁定 {self._lockout_duration.total_seconds() / 60} 分钟")

            return False

    def authenticate_by_secret_sequence(self, sequence: str) -> bool:
        """通过秘密序列认证（快捷键方式）

        Args:
            sequence: 按键序列（如 "DEVMODE" 或特殊组合）

        Returns:
            是否认证成功
        """
        if not self._is_dev_mode_allowed():
            logger.warning("未启用开发者模式，忽略秘密序列")
            return False

        if not self._allow_secret_sequences:
            logger.warning("秘密序列在当前环境被禁用或未配置，拒绝激活")
            return False

        if not self.dev_key_hash:
            logger.error("开发者密钥未配置，禁止通过秘密序列激活开发者模式")
            return False

        if sequence.upper() in self._secret_sequences:
            logger.info("检测到秘密序列，需通过开发者密钥完成认证")
            return True

        return False

    def _create_session(self):
        """创建开发者会话"""
        session_id = secrets.token_urlsafe(32)
        activated_at = datetime.now()
        expires_at = activated_at + timedelta(hours=self.session_timeout)

        # 构建功能权限
        features_enabled = dict.fromkeys(self.enabled_features, True)

        self._current_session = DevSession(
            session_id=session_id,
            activated_at=activated_at,
            expires_at=expires_at,
            features_enabled=features_enabled,
        )

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        if not self._current_session:
            return False

        if self._current_session.is_expired():
            logger.info("开发者会话已过期")
            self._current_session = None
            return False

        return True

    def get_session(self) -> DevSession | None:
        """获取当前会话"""
        if self.is_authenticated():
            return self._current_session
        return None

    def deactivate(self):
        """停用开发者模式"""
        self._current_session = None
        logger.info("开发者模式已停用")

    def extend_session(self, hours: int = None):
        """延长会话时间

        Args:
            hours: 延长的小时数，默认使用配置的超时时间
        """
        if self._current_session:
            hours = hours or self.session_timeout
            self._current_session.expires_at = datetime.now() + timedelta(hours=hours)
            logger.info(f"开发者会话已延长 {hours} 小时")

    def has_feature(self, feature: str) -> bool:
        """检查是否有权限使用某个功能

        Args:
            feature: 功能名称

        Returns:
            是否有权限
        """
        if not self.is_authenticated():
            return False

        return self._current_session.has_feature(feature)

    def _is_dev_mode_allowed(self) -> bool:
        """检查当前环境是否允许启用开发者模式"""
        if not self.dev_mode_enabled:
            return False
        if self._app_environment.lower() == "production" and not _env_flag("DEVELOPER_MODE_ENABLED", False):
            return False
        return True

    @staticmethod
    def generate_dev_key() -> str:
        """生成新的开发者密钥"""
        return secrets.token_urlsafe(32)

    @classmethod
    def setup_dev_key(cls, config_path: str = "config.json", new_key: str = None) -> str:
        """设置开发者密钥

        Args:
            config_path: 配置文件路径
            new_key: 新密钥，如果为None则自动生成

        Returns:
            设置的密钥（明文，仅显示一次）
        """
        if not new_key:
            new_key = cls.generate_dev_key()

        # 生成哈希
        auth = cls(config_path)
        key_hash = auth._hash_key(new_key)

        # 更新配置
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

            if "developer" not in config:
                config["developer"] = {}

            config["developer"]["key_hash"] = key_hash

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            logger.info("开发者密钥已更新")
            return new_key

        except Exception as e:
            logger.error(f"更新开发者密钥失败: {e}")
            raise
