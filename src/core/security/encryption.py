import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None
    hashes = None
    PBKDF2HMAC = None

"""数据加密和安全模块"""

logger = logging.getLogger(__name__)


class DataEncryption:
    """数据加密类"""

    def __init__(self, key: bytes | None = None):
        """初始化加密器

        Args:
            key: 加密密钥，如果为None则生成新密钥
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography库未安装，加密功能将被禁用")
            self.enabled = False
            return

        self.enabled = True
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = key

        self.cipher = Fernet(self.key)
        logger.info("数据加密器已初始化")

    def encrypt_string(self, data: str) -> str:
        """加密字符串

        Args:
            data: 要加密的字符串

        Returns:
            加密后的base64编码字符串
        """
        if not self.enabled:
            logger.warning("加密功能未启用")
            return data

        try:
            encrypted_data = self.cipher.encrypt(data.encode("utf-8"))
            return base64.b64encode(encrypted_data).decode("utf-8")
        except Exception as e:
            logger.error(f"字符串加密失败: {e}")
            raise ValueError(f"加密失败: {str(e)}") from e

    def decrypt_string(self, encrypted_data: str) -> str:
        """解密字符串

        Args:
            encrypted_data: base64编码的加密字符串

        Returns:
            解密后的字符串
        """
        if not self.enabled:
            logger.warning("加密功能未启用")
            return encrypted_data

        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode("utf-8")
        except Exception as e:
            logger.error(f"字符串解密失败: {e}")
            raise ValueError(f"解密失败: {str(e)}") from e

    def encrypt_dict(self, data: dict[str, Any]) -> str:
        """加密字典数据

        Args:
            data: 要加密的字典

        Returns:
            加密后的base64编码字符串
        """
        if not self.enabled:
            logger.warning("加密功能未启用")
            return json.dumps(data, ensure_ascii=False)

        try:
            json_data = json.dumps(data, ensure_ascii=False)
            encrypted_data = self.cipher.encrypt(json_data.encode("utf-8"))
            return base64.b64encode(encrypted_data).decode("utf-8")
        except Exception as e:
            logger.error(f"字典加密失败: {e}")
            raise ValueError(f"加密失败: {str(e)}") from e

    def decrypt_dict(self, encrypted_data: str) -> dict[str, Any]:
        """解密字典数据

        Args:
            encrypted_data: base64编码的加密字符串

        Returns:
            解密后的字典
        """
        if not self.enabled:
            logger.warning("加密功能未启用")
            return json.loads(encrypted_data)

        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            json_data = decrypted_data.decode("utf-8")
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"字典解密失败: {e}")
            raise ValueError(f"解密失败: {str(e)}") from e

    def get_key(self) -> str:
        """获取加密密钥

        Returns:
            base64编码的密钥
        """
        if not self.enabled:
            return ""
        return base64.b64encode(self.key).decode("utf-8")


class PasswordManager:
    """密码管理器"""

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        """哈希密码

        Args:
            password: 原始密码
            salt: 盐值，如果为None则生成新盐值

        Returns:
            (哈希后的密码, 盐值)
        """
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2进行密码哈希
        if CRYPTOGRAPHY_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode("utf-8"),
                iterations=100000,
            )
            password_hash = base64.b64encode(kdf.derive(password.encode("utf-8"))).decode("utf-8")
        else:
            # 回退到标准库实现
            password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
            password_hash = base64.b64encode(password_hash).decode("utf-8")

        return password_hash, salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """验证密码

        Args:
            password: 原始密码
            hashed_password: 哈希后的密码
            salt: 盐值

        Returns:
            密码是否正确
        """
        try:
            computed_hash, _ = PasswordManager.hash_password(password, salt)
            return secrets.compare_digest(computed_hash, hashed_password)
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False

    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """生成安全密码

        Args:
            length: 密码长度

        Returns:
            生成的密码
        """
        minimum_length = max(8, 4)  # 至少覆盖四类字符并符合基本安全要求
        if length < minimum_length:
            raise ValueError(f"密码长度至少为{minimum_length}位")

        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        digits = "0123456789"
        specials = "!@#$%^&*"
        all_characters = uppercase + lowercase + digits + specials
        rng = secrets.SystemRandom()

        # 先保留每种字符类型至少一个
        password_chars = [
            rng.choice(uppercase),
            rng.choice(lowercase),
            rng.choice(digits),
            rng.choice(specials),
        ]

        # 填充剩余字符
        remaining = length - len(password_chars)
        password_chars.extend(rng.choice(all_characters) for _ in range(remaining))

        # 打乱顺序，避免模式
        rng.shuffle(password_chars)
        return "".join(password_chars)


class SecureToken:
    """安全令牌管理器"""

    def __init__(self, secret_key: str | None = None):
        """初始化令牌管理器

        Args:
            secret_key: 密钥，如果为None则生成新密钥
        """
        if secret_key is None:
            self.secret_key = secrets.token_urlsafe(32)
        else:
            self.secret_key = secret_key

        self.tokens: dict[str, dict[str, Any]] = {}
        self.default_expiry = timedelta(hours=24)

        logger.info("安全令牌管理器已初始化")

    def generate_token(self, user_id: str, expires_in: timedelta | None = None) -> str:
        """生成安全令牌

        Args:
            user_id: 用户ID
            expires_in: 过期时间，如果为None则使用默认值

        Returns:
            生成的令牌
        """
        if expires_in is None:
            expires_in = self.default_expiry

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + expires_in

        self.tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "is_active": True,
        }

        logger.info(f"为用户 {user_id} 生成令牌")
        return token

    def validate_token(self, token: str) -> tuple[bool, str | None]:
        """验证令牌

        Args:
            token: 要验证的令牌

        Returns:
            (是否有效, 用户ID)
        """
        if token not in self.tokens:
            return False, None

        token_data = self.tokens[token]

        # 检查令牌是否过期
        if datetime.now() > token_data["expires_at"]:
            del self.tokens[token]
            return False, None

        # 检查令牌是否激活
        if not token_data["is_active"]:
            return False, None

        return True, token_data["user_id"]

    def revoke_token(self, token: str) -> bool:
        """撤销令牌

        Args:
            token: 要撤销的令牌

        Returns:
            是否成功撤销
        """
        if token in self.tokens:
            self.tokens[token]["is_active"] = False
            logger.info(f"令牌已撤销: {token}")
            return True
        return False

    def cleanup_expired_tokens(self) -> int:
        """清理过期令牌

        Returns:
            清理的令牌数量
        """
        expired_tokens = []
        now = datetime.now()

        for token, data in self.tokens.items():
            if now > data["expires_at"]:
                expired_tokens.append(token)

        for token in expired_tokens:
            del self.tokens[token]

        if expired_tokens:
            logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")

        return len(expired_tokens)

    def get_token_info(self, token: str) -> dict[str, Any] | None:
        """获取令牌信息

        Args:
            token: 令牌

        Returns:
            令牌信息或None
        """
        return self.tokens.get(token)


class DataSanitizer:
    """数据清理器"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除危险字符
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\\", "/"]
        for char in dangerous_chars:
            filename = filename.replace(char, "_")

        # 限制长度
        if len(filename) > 255:
            filename = filename[:255]

        # 移除前后空格
        filename = filename.strip()

        # 确保文件名不为空
        if not filename:
            filename = "unnamed_file"

        return filename

    @staticmethod
    def sanitize_path(path: str) -> str:
        """清理路径

        Args:
            path: 原始路径

        Returns:
            清理后的路径
        """
        # 移除危险路径组件
        dangerous_components = ["..", ".", "~"]
        path_components = path.split("/")

        sanitized_components = []
        for component in path_components:
            if component not in dangerous_components:
                sanitized_components.append(DataSanitizer.sanitize_filename(component))

        return "/".join(sanitized_components)

    @staticmethod
    def sanitize_json(data: Any) -> Any:
        """清理JSON数据

        Args:
            data: 原始数据

        Returns:
            清理后的数据
        """
        if isinstance(data, dict):
            return {key: DataSanitizer.sanitize_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [DataSanitizer.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            # 移除控制字符
            return "".join(char for char in data if ord(char) >= 32 or char in "\n\r\t")
        else:
            return data


# 全局实例
data_encryption = DataEncryption()
password_manager = PasswordManager()
secure_token = SecureToken()
data_sanitizer = DataSanitizer()
