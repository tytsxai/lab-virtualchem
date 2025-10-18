"""
离线许可证管理系统

支持基于加密货币购买的离线许可证验证
"""

import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """许可证类型"""

    TRIAL = "trial"  # 试用版
    PERSONAL = "personal"  # 个人版
    EDUCATION = "education"  # 教育版
    COMMERCIAL = "commercial"  # 商业版
    ENTERPRISE = "enterprise"  # 企业版


class LicenseStatus(Enum):
    """许可证状态"""

    VALID = "valid"  # 有效
    EXPIRED = "expired"  # 已过期
    INVALID = "invalid"  # 无效
    REVOKED = "revoked"  # 已撤销
    NOT_ACTIVATED = "not_activated"  # 未激活


@dataclass
class CryptoPayment:
    """加密货币支付信息"""

    currency: str  # 币种 (BTC, ETH, USDT等)
    tx_hash: str  # 交易哈希
    amount: float  # 支付金额
    recipient_address: str  # 收款地址
    timestamp: datetime  # 支付时间
    block_number: int | None = None  # 区块高度
    confirmations: int = 0  # 确认数


@dataclass
class License:
    """许可证"""

    license_key: str  # 许可证密钥
    license_type: LicenseType  # 许可证类型
    user_id: str  # 用户ID
    email: str  # 用户邮箱
    machine_id: str  # 机器ID (用于设备绑定)
    issue_date: datetime  # 签发日期
    expiry_date: datetime  # 过期日期
    payment: CryptoPayment  # 支付信息
    features: list[str]  # 可用功能列表
    max_devices: int = 1  # 最大设备数
    is_activated: bool = False  # 是否已激活
    activated_at: datetime | None = None  # 激活时间
    signature: str = ""  # 数字签名

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["license_type"] = self.license_type.value
        data["issue_date"] = self.issue_date.isoformat()
        data["expiry_date"] = self.expiry_date.isoformat()
        data["payment"]["timestamp"] = self.payment.timestamp.isoformat()
        if self.activated_at:
            data["activated_at"] = self.activated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "License":
        """从字典创建"""
        # 转换日期
        data["issue_date"] = datetime.fromisoformat(data["issue_date"])
        data["expiry_date"] = datetime.fromisoformat(data["expiry_date"])
        if data.get("activated_at"):
            data["activated_at"] = datetime.fromisoformat(data["activated_at"])

        # 转换枚举
        data["license_type"] = LicenseType(data["license_type"])

        # 转换支付信息
        payment_data = data["payment"]
        payment_data["timestamp"] = datetime.fromisoformat(payment_data["timestamp"])
        data["payment"] = CryptoPayment(**payment_data)

        return cls(**data)


class LicenseManager:
    """许可证管理器"""

    def __init__(self, secret_key: str, license_file: Path):
        """初始化

        Args:
            secret_key: 用于签名的密钥
            license_file: 许可证存储文件路径
        """
        self.secret_key = secret_key
        self.license_file = license_file
        self._revoked_keys: set[str] = set()  # 已撤销的许可证

        # 加载已撤销列表
        self._load_revoked_keys()

    def generate_license(
        self,
        user_id: str,
        email: str,
        machine_id: str,
        license_type: LicenseType,
        payment: CryptoPayment,
        validity_days: int = 365,
        features: list[str] | None = None,
    ) -> License:
        """生成许可证

        Args:
            user_id: 用户ID
            email: 用户邮箱
            machine_id: 机器ID
            license_type: 许可证类型
            payment: 支付信息
            validity_days: 有效期天数
            features: 功能列表

        Returns:
            生成的许可证
        """
        # 生成许可证密钥
        license_key = self._generate_license_key(user_id, email, payment.tx_hash)

        # 默认功能
        if features is None:
            features = self._get_default_features(license_type)

        # 创建许可证
        now = datetime.now()
        license_obj = License(
            license_key=license_key,
            license_type=license_type,
            user_id=user_id,
            email=email,
            machine_id=machine_id,
            issue_date=now,
            expiry_date=now + timedelta(days=validity_days),
            payment=payment,
            features=features,
            max_devices=self._get_max_devices(license_type),
        )

        # 生成签名
        license_obj.signature = self._sign_license(license_obj)

        logger.info(f"生成许可证: {license_key} for {email}")
        return license_obj

    def validate_license(self, license_obj: License, machine_id: str) -> tuple[LicenseStatus, str | None]:
        """验证许可证

        Args:
            license_obj: 许可证对象
            machine_id: 当前机器ID

        Returns:
            (状态, 错误消息)
        """
        # 检查是否已撤销
        if license_obj.license_key in self._revoked_keys:
            return LicenseStatus.REVOKED, "许可证已被撤销"

        # 验证签名
        if not self._verify_signature(license_obj):
            return LicenseStatus.INVALID, "许可证签名无效"

        # 检查是否已激活
        if not license_obj.is_activated:
            return LicenseStatus.NOT_ACTIVATED, "许可证未激活"

        # 检查设备绑定
        if license_obj.machine_id != machine_id:
            return LicenseStatus.INVALID, "许可证与当前设备不匹配"

        # 检查过期时间
        if datetime.now() > license_obj.expiry_date:
            return LicenseStatus.EXPIRED, "许可证已过期"

        return LicenseStatus.VALID, None

    def activate_license(self, license_obj: License, machine_id: str) -> tuple[bool, str | None]:
        """激活许可证

        Args:
            license_obj: 许可证对象
            machine_id: 机器ID

        Returns:
            (是否成功, 错误消息)
        """
        # 检查是否已激活
        if license_obj.is_activated:
            return False, "许可证已激活"

        # 检查设备绑定
        if license_obj.machine_id != machine_id:
            return False, "许可证与当前设备不匹配"

        # 激活
        license_obj.is_activated = True
        license_obj.activated_at = datetime.now()

        # 重新签名
        license_obj.signature = self._sign_license(license_obj)

        logger.info(f"激活许可证: {license_obj.license_key}")
        return True, None

    def save_license(self, license_obj: License) -> bool:
        """保存许可证到文件

        Args:
            license_obj: 许可证对象

        Returns:
            是否成功
        """
        try:
            # 确保目录存在
            self.license_file.parent.mkdir(parents=True, exist_ok=True)

            # 加密保存
            encrypted_data = self._encrypt_license(license_obj)

            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f, indent=2)

            logger.info(f"许可证已保存: {self.license_file}")
            return True

        except Exception as e:
            logger.error(f"保存许可证失败: {e}")
            return False

    def load_license(self) -> License | None:
        """从文件加载许可证

        Returns:
            许可证对象,如果不存在或无效则返回None
        """
        try:
            if not self.license_file.exists():
                logger.warning("许可证文件不存在")
                return None

            with open(self.license_file, encoding="utf-8") as f:
                encrypted_data = json.load(f)

            # 解密
            license_obj = self._decrypt_license(encrypted_data)

            logger.info(f"许可证已加载: {license_obj.license_key}")
            return license_obj

        except Exception as e:
            logger.error(f"加载许可证失败: {e}")
            return None

    def revoke_license(self, license_key: str) -> bool:
        """撤销许可证

        Args:
            license_key: 许可证密钥

        Returns:
            是否成功
        """
        self._revoked_keys.add(license_key)
        self._save_revoked_keys()
        logger.info(f"许可证已撤销: {license_key}")
        return True

    def get_license_info(self, license_obj: License) -> dict[str, Any]:
        """获取许可证信息

        Args:
            license_obj: 许可证对象

        Returns:
            许可证信息字典
        """
        days_remaining = (license_obj.expiry_date - datetime.now()).days

        return {
            "license_key": license_obj.license_key,
            "license_type": license_obj.license_type.value,
            "email": license_obj.email,
            "issue_date": license_obj.issue_date.strftime("%Y-%m-%d"),
            "expiry_date": license_obj.expiry_date.strftime("%Y-%m-%d"),
            "days_remaining": max(0, days_remaining),
            "is_activated": license_obj.is_activated,
            "features": license_obj.features,
            "payment": {
                "currency": license_obj.payment.currency,
                "tx_hash": license_obj.payment.tx_hash,
                "amount": license_obj.payment.amount,
            },
        }

    # ========== 私有方法 ==========

    def _generate_license_key(self, user_id: str, email: str, tx_hash: str) -> str:
        """生成许可证密钥"""
        data = f"{user_id}:{email}:{tx_hash}:{secrets.token_hex(16)}"
        hash_obj = hashlib.sha256(data.encode())
        key = hash_obj.hexdigest()[:32].upper()

        # 格式化为 XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
        return "-".join([key[i : i + 4] for i in range(0, len(key), 4)])

    def _sign_license(self, license_obj: License) -> str:
        """对许可证进行数字签名"""
        # 生成签名数据
        data = {
            "license_key": license_obj.license_key,
            "user_id": license_obj.user_id,
            "email": license_obj.email,
            "machine_id": license_obj.machine_id,
            "license_type": license_obj.license_type.value,
            "issue_date": license_obj.issue_date.isoformat(),
            "expiry_date": license_obj.expiry_date.isoformat(),
            "tx_hash": license_obj.payment.tx_hash,
            "is_activated": license_obj.is_activated,
        }

        # 生成签名
        data_str = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256(f"{data_str}:{self.secret_key}".encode()).hexdigest()

        return signature

    def _verify_signature(self, license_obj: License) -> bool:
        """验证许可证签名"""
        expected_signature = self._sign_license(license_obj)
        return license_obj.signature == expected_signature

    def _encrypt_license(self, license_obj: License) -> dict[str, Any]:
        """加密许可证数据 (简单实现)"""
        data = license_obj.to_dict()
        # 这里使用简单的编码,生产环境应使用真正的加密
        data["_encrypted"] = True
        return data

    def _decrypt_license(self, encrypted_data: dict[str, Any]) -> License:
        """解密许可证数据"""
        if not encrypted_data.get("_encrypted"):
            raise ValueError("无效的许可证格式")

        encrypted_data.pop("_encrypted")
        return License.from_dict(encrypted_data)

    def _get_default_features(self, license_type: LicenseType) -> list[str]:
        """获取默认功能列表"""
        features_map = {
            LicenseType.TRIAL: ["basic_experiments", "limited_reports"],
            LicenseType.PERSONAL: ["all_experiments", "full_reports", "data_export"],
            LicenseType.EDUCATION: [
                "all_experiments",
                "full_reports",
                "data_export",
            ],
            LicenseType.COMMERCIAL: [
                "all_experiments",
                "full_reports",
                "data_export",
                "api_access",
                "priority_support",
            ],
            LicenseType.ENTERPRISE: [
                "all_experiments",
                "full_reports",
                "data_export",
                "api_access",
                "priority_support",
                "custom_integration",
                "on_premise_deployment",
            ],
        }
        return features_map.get(license_type, [])

    def _get_max_devices(self, license_type: LicenseType) -> int:
        """获取最大设备数"""
        devices_map = {
            LicenseType.TRIAL: 1,
            LicenseType.PERSONAL: 2,
            LicenseType.EDUCATION: 5,
            LicenseType.COMMERCIAL: 10,
            LicenseType.ENTERPRISE: 999,
        }
        return devices_map.get(license_type, 1)

    def _load_revoked_keys(self) -> None:
        """加载已撤销的许可证列表"""
        revoked_file = self.license_file.parent / "revoked_licenses.json"
        try:
            if revoked_file.exists():
                with open(revoked_file, encoding="utf-8") as f:
                    self._revoked_keys = set(json.load(f))
        except Exception as e:
            logger.error(f"加载撤销列表失败: {e}")

    def _save_revoked_keys(self) -> None:
        """保存已撤销的许可证列表"""
        revoked_file = self.license_file.parent / "revoked_licenses.json"
        try:
            with open(revoked_file, "w", encoding="utf-8") as f:
                json.dump(list(self._revoked_keys), f, indent=2)
        except Exception as e:
            logger.error(f"保存撤销列表失败: {e}")


def get_machine_id() -> str:
    """获取机器唯一ID

    使用增强的设备指纹系统获取更可靠的机器ID
    """
    try:
        from .device_fingerprint import DeviceFingerprintCollector

        collector = DeviceFingerprintCollector()
        fingerprint = collector.collect()
        return fingerprint.device_id
    except Exception as e:
        logger.warning(f"使用设备指纹系统失败，回退到简单模式: {e}")
        # 回退到简单模式
        import platform
        import uuid

        machine_info = f"{platform.node()}:{platform.machine()}:{uuid.getnode()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:32]
