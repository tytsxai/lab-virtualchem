"""
数据保护模块
提供数据加密、脱敏、备份恢复等功能
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..utils.logger import get_logger

logger = get_logger(__name__)
GCM_HEADER = b"VCLG"  # 标识新格式，避免与旧CBC混淆
GCM_NONCE_SIZE = 12


class EncryptionAlgorithm(Enum):
    """加密算法"""

    AES256 = "aes256"
    RSA2048 = "rsa2048"
    RSA4096 = "rsa4096"
    FERNET = "fernet"


class DataClassification(Enum):
    """数据分类"""

    PUBLIC = "public"  # 公开
    INTERNAL = "internal"  # 内部
    CONFIDENTIAL = "confidential"  # 机密
    SECRET = "secret"  # 秘密


class BackupType(Enum):
    """备份类型"""

    FULL = "full"  # 完整备份
    INCREMENTAL = "incremental"  # 增量备份
    DIFFERENTIAL = "differential"  # 差异备份


@dataclass
class EncryptionKey:
    """加密密钥"""

    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True


@dataclass
class DataMetadata:
    """数据元数据"""

    data_id: str
    classification: DataClassification
    owner: str
    created_at: datetime
    last_modified: datetime
    encryption_key_id: str | None = None
    retention_period: timedelta | None = None
    tags: list[str] = None


class DataEncryption:
    """数据加密"""

    def __init__(self, master_key: str | None = None):
        """初始化数据加密

        Args:
            master_key: 主密钥
        """
        self.master_key = master_key or self._generate_master_key()
        self.encryption_keys: dict[str, EncryptionKey] = {}
        self._lock = threading.RLock()

        # 初始化默认密钥
        self._initialize_default_keys()

        logger.info("数据加密已初始化")

    def _generate_master_key(self) -> str:
        """生成主密钥

        Returns:
            主密钥
        """
        return secrets.token_urlsafe(32)

    def _initialize_default_keys(self) -> None:
        """初始化默认密钥"""
        # 生成Fernet密钥
        fernet_key = Fernet.generate_key()
        self.encryption_keys["default_fernet"] = EncryptionKey(
            key_id="default_fernet",
            algorithm=EncryptionAlgorithm.FERNET,
            key_data=fernet_key,
            created_at=datetime.now(),
        )

        # 生成AES密钥
        aes_key = secrets.token_bytes(32)
        self.encryption_keys["default_aes"] = EncryptionKey(
            key_id="default_aes", algorithm=EncryptionAlgorithm.AES256, key_data=aes_key, created_at=datetime.now()
        )

        logger.info("默认加密密钥已初始化")

    def encrypt_data(self, data: str | bytes, key_id: str = "default_fernet") -> bytes:
        """加密数据

        Args:
            data: 要加密的数据
            key_id: 密钥ID

        Returns:
            加密后的数据
        """
        with self._lock:
            if key_id not in self.encryption_keys:
                raise ValueError(f"密钥不存在: {key_id}")

            key = self.encryption_keys[key_id]

            if key.algorithm == EncryptionAlgorithm.FERNET:
                return self._encrypt_with_fernet(data, key.key_data)
            elif key.algorithm == EncryptionAlgorithm.AES256:
                return self._encrypt_with_aes(data, key.key_data)
            else:
                raise ValueError(f"不支持的加密算法: {key.algorithm}")

    def decrypt_data(self, encrypted_data: bytes, key_id: str = "default_fernet") -> bytes:
        """解密数据

        Args:
            encrypted_data: 加密的数据
            key_id: 密钥ID

        Returns:
            解密后的数据
        """
        with self._lock:
            if key_id not in self.encryption_keys:
                raise ValueError(f"密钥不存在: {key_id}")

            key = self.encryption_keys[key_id]

            if key.algorithm == EncryptionAlgorithm.FERNET:
                return self._decrypt_with_fernet(encrypted_data, key.key_data)
            elif key.algorithm == EncryptionAlgorithm.AES256:
                return self._decrypt_with_aes(encrypted_data, key.key_data)
            else:
                raise ValueError(f"不支持的加密算法: {key.algorithm}")

    def _encrypt_with_fernet(self, data: str | bytes, key: bytes) -> bytes:
        """使用Fernet加密

        Args:
            data: 要加密的数据
            key: 密钥

        Returns:
            加密后的数据
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        fernet = Fernet(key)
        return fernet.encrypt(data)

    def _decrypt_with_fernet(self, encrypted_data: bytes, key: bytes) -> bytes:
        """使用Fernet解密

        Args:
            encrypted_data: 加密的数据
            key: 密钥

        Returns:
            解密后的数据
        """
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)

    def _encrypt_with_aes(self, data: str | bytes, key: bytes) -> bytes:
        """使用AES-GCM加密并添加数据完整性标签

        Args:
            data: 要加密的数据
            key: 密钥

        Returns:
            加密后的数据
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        if len(key) not in (16, 24, 32):
            raise ValueError("AES密钥长度必须是128/192/256位")

        nonce = secrets.token_bytes(GCM_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)

        # 标记新格式: header + nonce + ciphertext_with_tag
        return GCM_HEADER + nonce + ciphertext

    def _decrypt_with_aes(self, encrypted_data: bytes, key: bytes) -> bytes:
        """使用AES解密（优先GCM，兼容旧CBC）

        Args:
            encrypted_data: 加密的数据
            key: 密钥

        Returns:
            解密后的数据
        """
        if encrypted_data.startswith(GCM_HEADER):
            payload = encrypted_data[len(GCM_HEADER) :]
            if len(payload) < GCM_NONCE_SIZE + 16:
                raise ValueError("AES-GCM 密文长度无效")

            nonce = payload[:GCM_NONCE_SIZE]
            ciphertext = payload[GCM_NONCE_SIZE:]
            aesgcm = AESGCM(key)

            try:
                return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            except InvalidTag as exc:
                raise ValueError("AES-GCM 验证失败，数据可能被篡改") from exc

        # 兼容历史CBC密文，优先提示迁移
        logger.warning("检测到旧版AES-CBC密文，建议重新加密以启用认证保护")
        return self._decrypt_legacy_cbc(encrypted_data, key)

    def _decrypt_legacy_cbc(self, encrypted_data: bytes, key: bytes) -> bytes:
        """兼容旧版 AES-CBC 解密（不具备完整性校验）"""
        if len(encrypted_data) < 16:
            raise ValueError("AES-CBC 密文长度无效")

        iv = encrypted_data[:16]
        encrypted = encrypted_data[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        padding_length = decrypted[-1]
        if padding_length == 0 or padding_length > len(decrypted):
            raise ValueError("AES-CBC 填充无效")
        return decrypted[:-padding_length]

    def generate_key(self, algorithm: EncryptionAlgorithm, key_id: str | None = None) -> str:
        """生成新密钥

        Args:
            algorithm: 加密算法
            key_id: 密钥ID

        Returns:
            密钥ID
        """
        with self._lock:
            if not key_id:
                key_id = f"{algorithm.value}_{secrets.token_hex(8)}"

            if algorithm == EncryptionAlgorithm.FERNET:
                key_data = Fernet.generate_key()
            elif algorithm == EncryptionAlgorithm.AES256:
                key_data = secrets.token_bytes(32)
            else:
                raise ValueError(f"不支持的算法: {algorithm}")

            self.encryption_keys[key_id] = EncryptionKey(
                key_id=key_id, algorithm=algorithm, key_data=key_data, created_at=datetime.now()
            )

            logger.info(f"新密钥已生成: {key_id}")
            return key_id

    def rotate_key(self, old_key_id: str, new_key_id: str | None = None) -> str:
        """轮换密钥

        Args:
            old_key_id: 旧密钥ID
            new_key_id: 新密钥ID

        Returns:
            新密钥ID
        """
        with self._lock:
            if old_key_id not in self.encryption_keys:
                raise ValueError(f"密钥不存在: {old_key_id}")

            old_key = self.encryption_keys[old_key_id]

            if not new_key_id:
                new_key_id = f"{old_key.algorithm.value}_rotated_{secrets.token_hex(8)}"

            # 生成新密钥
            if old_key.algorithm == EncryptionAlgorithm.FERNET:
                key_data = Fernet.generate_key()
            elif old_key.algorithm == EncryptionAlgorithm.AES256:
                key_data = secrets.token_bytes(32)
            else:
                raise ValueError(f"不支持的算法: {old_key.algorithm}")

            self.encryption_keys[new_key_id] = EncryptionKey(
                key_id=new_key_id, algorithm=old_key.algorithm, key_data=key_data, created_at=datetime.now()
            )

            # 标记旧密钥为非活跃
            old_key.is_active = False

            logger.info(f"密钥已轮换: {old_key_id} -> {new_key_id}")
            return new_key_id

    def get_key_info(self, key_id: str) -> EncryptionKey | None:
        """获取密钥信息

        Args:
            key_id: 密钥ID

        Returns:
            密钥信息
        """
        return self.encryption_keys.get(key_id)

    def list_keys(self) -> list[EncryptionKey]:
        """列出所有密钥

        Returns:
            密钥列表
        """
        return list(self.encryption_keys.values())


class DataMasking:
    """数据脱敏"""

    def __init__(self):
        """初始化数据脱敏"""
        self.masking_rules: dict[str, dict[str, Any]] = {}
        self._initialize_default_rules()

        logger.info("数据脱敏已初始化")

    def _initialize_default_rules(self) -> None:
        """初始化默认脱敏规则"""
        self.masking_rules = {
            "email": {
                "pattern": r"(\w{1,3})\w*@(\w{1,3})\w*\.(\w+)",
                "replacement": r"\1***@\2***.\3",
                "description": "邮箱脱敏",
            },
            "phone": {"pattern": r"(\d{3})\d{4}(\d{4})", "replacement": r"\1****\2", "description": "手机号脱敏"},
            "id_card": {
                "pattern": r"(\d{6})\d{8}(\d{4})",
                "replacement": r"\1********\2",
                "description": "身份证号脱敏",
            },
            "credit_card": {
                "pattern": r"(\d{4})\d{8}(\d{4})",
                "replacement": r"\1********\2",
                "description": "信用卡号脱敏",
            },
            "name": {"pattern": r"(\w{1})\w*", "replacement": r"\1***", "description": "姓名脱敏"},
        }

    def mask_data(self, data: str, data_type: str) -> str:
        """脱敏数据

        Args:
            data: 要脱敏的数据
            data_type: 数据类型

        Returns:
            脱敏后的数据
        """
        if data_type not in self.masking_rules:
            return data

        import re

        rule = self.masking_rules[data_type]
        pattern = rule["pattern"]
        replacement = rule["replacement"]

        masked_data = re.sub(pattern, replacement, data)

        logger.debug(f"数据已脱敏: {data_type}")
        return masked_data

    def add_masking_rule(self, data_type: str, pattern: str, replacement: str, description: str) -> None:
        """添加脱敏规则

        Args:
            data_type: 数据类型
            pattern: 正则表达式模式
            replacement: 替换模式
            description: 描述
        """
        self.masking_rules[data_type] = {"pattern": pattern, "replacement": replacement, "description": description}

        logger.info(f"脱敏规则已添加: {data_type}")

    def mask_dict(self, data: dict[str, Any], mask_fields: list[str]) -> dict[str, Any]:
        """脱敏字典数据

        Args:
            data: 要脱敏的字典
            mask_fields: 需要脱敏的字段列表

        Returns:
            脱敏后的字典
        """
        masked_data = data.copy()

        for field in mask_fields:
            if field in masked_data and isinstance(masked_data[field], str):
                # 尝试根据字段名推断数据类型
                data_type = self._infer_data_type(field)
                masked_data[field] = self.mask_data(masked_data[field], data_type)

        return masked_data

    def _infer_data_type(self, field_name: str) -> str:
        """推断数据类型

        Args:
            field_name: 字段名

        Returns:
            数据类型
        """
        field_lower = field_name.lower()

        if "email" in field_lower:
            return "email"
        elif "phone" in field_lower or "mobile" in field_lower:
            return "phone"
        elif "id_card" in field_lower or "idcard" in field_lower:
            return "id_card"
        elif "credit_card" in field_lower or "card" in field_lower:
            return "credit_card"
        elif "name" in field_lower:
            return "name"
        else:
            return "default"


class DataBackup:
    """数据备份"""

    def __init__(self, backup_dir: str = "backups"):
        """初始化数据备份

        Args:
            backup_dir: 备份目录
        """
        self.backup_dir = backup_dir
        self.encryption = DataEncryption()

        # 创建备份目录
        os.makedirs(backup_dir, exist_ok=True)

        logger.info(f"数据备份已初始化: {backup_dir}")

    def create_backup(
        self,
        source_path: str,
        backup_name: str | None = None,
        _backup_type: BackupType = BackupType.FULL,
        encrypt: bool = True,
    ) -> str:
        """创建备份

        Args:
            source_path: 源路径
            backup_name: 备份名称
            backup_type: 备份类型
            encrypt: 是否加密

        Returns:
            备份文件路径
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        backup_path = os.path.join(self.backup_dir, f"{backup_name}.backup")

        try:
            if os.path.isfile(source_path):
                # 文件备份
                shutil.copy2(source_path, backup_path)
            elif os.path.isdir(source_path):
                # 目录备份
                shutil.make_archive(backup_path, "zip", source_path)
                backup_path += ".zip"

            # 加密备份
            if encrypt:
                encrypted_path = backup_path + ".encrypted"
                with open(backup_path, "rb") as f:
                    data = f.read()

                encrypted_data = self.encryption.encrypt_data(data)

                with open(encrypted_path, "wb") as f:
                    f.write(encrypted_data)

                # 删除未加密的备份
                os.remove(backup_path)
                backup_path = encrypted_path

            logger.info(f"备份已创建: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            raise

    def restore_backup(self, backup_path: str, target_path: str, decrypt: bool = True) -> bool:
        """恢复备份

        Args:
            backup_path: 备份文件路径
            target_path: 目标路径
            decrypt: 是否解密

        Returns:
            是否成功
        """
        try:
            if decrypt and backup_path.endswith(".encrypted"):
                # 解密备份
                with open(backup_path, "rb") as f:
                    encrypted_data = f.read()

                decrypted_data = self.encryption.decrypt_data(encrypted_data)

                # 写入临时文件
                temp_path = backup_path + ".temp"
                with open(temp_path, "wb") as f:
                    f.write(decrypted_data)

                backup_path = temp_path

            if backup_path.endswith(".zip"):
                # 解压目录备份
                shutil.unpack_archive(backup_path, target_path)
            else:
                # 恢复文件备份
                shutil.copy2(backup_path, target_path)

            # 清理临时文件
            if backup_path.endswith(".temp"):
                os.remove(backup_path)

            logger.info(f"备份已恢复: {backup_path} -> {target_path}")
            return True

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False

    def list_backups(self) -> list[dict[str, Any]]:
        """列出备份文件

        Returns:
            备份文件列表
        """
        backups = []

        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".backup") or filename.endswith(".backup.encrypted"):
                file_path = os.path.join(self.backup_dir, filename)
                stat = os.stat(file_path)

                backups.append(
                    {
                        "name": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime),
                        "encrypted": filename.endswith(".encrypted"),
                    }
                )

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def cleanup_old_backups(self, days: int = 30) -> int:
        """清理旧备份

        Args:
            days: 保留天数

        Returns:
            清理的备份数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".backup") or filename.endswith(".backup.encrypted"):
                file_path = os.path.join(self.backup_dir, filename)
                stat = os.stat(file_path)

                if datetime.fromtimestamp(stat.st_ctime) < cutoff_date:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"旧备份已删除: {filename}")
                    except Exception as e:
                        logger.error(f"删除备份失败: {e}")

        logger.info(f"清理了 {cleaned_count} 个旧备份")
        return cleaned_count


class DataProtection:
    """数据保护管理器"""

    def __init__(self, master_key: str | None = None, backup_dir: str = "backups"):
        """初始化数据保护管理器

        Args:
            master_key: 主密钥
            backup_dir: 备份目录
        """
        self.encryption = DataEncryption(master_key)
        self.masking = DataMasking()
        self.backup = DataBackup(backup_dir)

        # 数据分类配置
        self.data_classifications: dict[str, DataClassification] = {}

        logger.info("数据保护管理器已初始化")

    def classify_data(self, data_id: str, classification: DataClassification, _owner: str) -> None:
        """分类数据

        Args:
            data_id: 数据ID
            classification: 数据分类
            owner: 所有者
        """
        self.data_classifications[data_id] = classification

        logger.info(f"数据已分类: {data_id} -> {classification.value}")

    def protect_data(self, data: Any, data_id: str, encrypt: bool = True, mask: bool = False) -> Any:
        """保护数据

        Args:
            data: 要保护的数据
            data_id: 数据ID
            encrypt: 是否加密
            mask: 是否脱敏

        Returns:
            保护后的数据
        """
        protected_data = data

        # 脱敏
        if mask and isinstance(data, dict):
            classification = self.data_classifications.get(data_id, DataClassification.INTERNAL)
            if classification in [DataClassification.CONFIDENTIAL, DataClassification.SECRET]:
                protected_data = self.masking.mask_dict(data, list(data.keys()))

        # 加密
        if encrypt:
            if isinstance(protected_data, str):
                protected_data = self.encryption.encrypt_data(protected_data)
            elif isinstance(protected_data, dict):
                protected_data = json.dumps(protected_data).encode("utf-8")
                protected_data = self.encryption.encrypt_data(protected_data)

        return protected_data

    def unprotect_data(self, protected_data: Any, _data_id: str, decrypt: bool = True) -> Any:
        """解除数据保护

        Args:
            protected_data: 受保护的数据
            data_id: 数据ID
            decrypt: 是否解密

        Returns:
            原始数据
        """
        data = protected_data

        # 解密
        if decrypt and isinstance(data, bytes):
            try:
                decrypted_data = self.encryption.decrypt_data(data)
                if isinstance(decrypted_data, bytes):
                    try:
                        data = json.loads(decrypted_data.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        data = decrypted_data.decode("utf-8")
            except Exception as e:
                logger.error(f"解密失败: {e}")
                return protected_data

        return data

    def create_data_backup(self, data: Any, backup_name: str | None = None) -> str:
        """创建数据备份

        Args:
            data: 要备份的数据
            backup_name: 备份名称

        Returns:
            备份文件路径
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"data_backup_{timestamp}"

        # 序列化数据
        if isinstance(data, dict):
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            data_str = str(data)

        # 加密数据
        encrypted_data = self.encryption.encrypt_data(data_str)

        # 保存备份
        backup_path = os.path.join(self.backup.backup_dir, f"{backup_name}.backup.encrypted")
        with open(backup_path, "wb") as f:
            f.write(encrypted_data)

        logger.info(f"数据备份已创建: {backup_path}")
        return backup_path

    def restore_data_backup(self, backup_path: str) -> Any:
        """恢复数据备份

        Args:
            backup_path: 备份文件路径

        Returns:
            恢复的数据
        """
        try:
            with open(backup_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.encryption.decrypt_data(encrypted_data)

            try:
                data = json.loads(decrypted_data.decode("utf-8"))
            except json.JSONDecodeError:
                data = decrypted_data.decode("utf-8")

            logger.info(f"数据备份已恢复: {backup_path}")
            return data

        except Exception as e:
            logger.error(f"恢复数据备份失败: {e}")
            raise

    def get_protection_report(self) -> dict[str, Any]:
        """获取保护报告

        Returns:
            保护报告
        """
        return {
            "encryption_keys": len(self.encryption.encryption_keys),
            "masking_rules": len(self.masking.masking_rules),
            "data_classifications": len(self.data_classifications),
            "backups": len(self.backup.list_backups()),
            "classification_distribution": {
                classification.value: sum(1 for c in self.data_classifications.values() if c == classification)
                for classification in DataClassification
            },
        }
