"""
许可证验证器 - 增强版

集成设备指纹识别和授权管理
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .device_fingerprint import (
    DeviceAuthManager,
    DeviceFingerprint,
    get_device_auth_manager,
)
from .license_manager import License, LicenseManager, LicenseStatus, get_machine_id

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """验证结果"""

    SUCCESS = "success"  # 验证成功
    LICENSE_INVALID = "license_invalid"  # 许可证无效
    LICENSE_EXPIRED = "license_expired"  # 许可证过期
    LICENSE_NOT_ACTIVATED = "license_not_activated"  # 未激活
    LICENSE_REVOKED = "license_revoked"  # 已撤销
    DEVICE_MISMATCH = "device_mismatch"  # 设备不匹配
    DEVICE_BLOCKED = "device_blocked"  # 设备被封控
    DEVICE_LIMIT_EXCEEDED = "device_limit_exceeded"  # 超出设备数量限制
    NETWORK_ERROR = "network_error"  # 网络错误


@dataclass
class ValidationReport:
    """验证报告"""

    result: ValidationResult  # 验证结果
    license_info: dict[str, Any] | None  # 许可证信息
    device_fingerprint: DeviceFingerprint | None  # 设备指纹
    message: str  # 消息
    timestamp: datetime  # 验证时间
    additional_info: dict[str, Any] | None = None  # 额外信息


class EnhancedLicenseValidator:
    """增强的许可证验证器"""

    def __init__(
        self,
        license_manager: LicenseManager,
        device_auth_manager: DeviceAuthManager | None = None,
    ):
        """初始化

        Args:
            license_manager: 许可证管理器
            device_auth_manager: 设备授权管理器
        """
        self.license_manager = license_manager
        self.device_auth_manager = device_auth_manager or get_device_auth_manager()

    def validate(
        self, license_obj: License | None = None, enable_device_check: bool = True
    ) -> ValidationReport:
        """验证许可证

        Args:
            license_obj: 许可证对象（如果为None，则从文件加载）
            enable_device_check: 是否启用设备检查

        Returns:
            验证报告
        """
        timestamp = datetime.now()

        # 加载许可证
        if license_obj is None:
            license_obj = self.license_manager.load_license()

        if not license_obj:
            return ValidationReport(
                result=ValidationResult.LICENSE_INVALID,
                license_info=None,
                device_fingerprint=None,
                message="未找到许可证文件",
                timestamp=timestamp,
            )

        # 获取机器ID
        machine_id = get_machine_id()

        # 基础许可证验证
        status, error_msg = self.license_manager.validate_license(
            license_obj, machine_id
        )

        # 映射许可证状态到验证结果
        result_mapping = {
            LicenseStatus.EXPIRED: ValidationResult.LICENSE_EXPIRED,
            LicenseStatus.INVALID: ValidationResult.LICENSE_INVALID,
            LicenseStatus.REVOKED: ValidationResult.LICENSE_REVOKED,
            LicenseStatus.NOT_ACTIVATED: ValidationResult.LICENSE_NOT_ACTIVATED,
        }

        if status != LicenseStatus.VALID:
            return ValidationReport(
                result=result_mapping.get(status, ValidationResult.LICENSE_INVALID),
                license_info=self.license_manager.get_license_info(license_obj),
                device_fingerprint=None,
                message=error_msg or "许可证验证失败",
                timestamp=timestamp,
            )

        # 设备授权检查
        device_fingerprint = None
        if enable_device_check:
            authorized, auth_message, device_fingerprint = (
                self.device_auth_manager.check_device_authorization(
                    license_obj.license_key, license_obj.max_devices
                )
            )

            if not authorized:
                # 判断失败原因
                if "封控" in auth_message:
                    result = ValidationResult.DEVICE_BLOCKED
                elif "超出" in auth_message:
                    result = ValidationResult.DEVICE_LIMIT_EXCEEDED
                else:
                    result = ValidationResult.DEVICE_MISMATCH

                return ValidationReport(
                    result=result,
                    license_info=self.license_manager.get_license_info(license_obj),
                    device_fingerprint=device_fingerprint,
                    message=auth_message,
                    timestamp=timestamp,
                )

        # 验证成功
        logger.info(f"许可证验证成功: {license_obj.license_key}")

        return ValidationReport(
            result=ValidationResult.SUCCESS,
            license_info=self.license_manager.get_license_info(license_obj),
            device_fingerprint=device_fingerprint,
            message="验证成功",
            timestamp=timestamp,
            additional_info=self.device_auth_manager.get_device_usage_stats(
                license_obj.license_key
            ),
        )

    def activate_license(
        self, license_obj: License, force: bool = False
    ) -> tuple[bool, str, DeviceFingerprint | None]:
        """激活许可证

        Args:
            license_obj: 许可证对象
            force: 是否强制激活（跳过设备检查）

        Returns:
            (是否成功, 消息, 设备指纹)
        """
        # 获取当前设备ID
        machine_id = get_machine_id()

        # 设备授权检查
        device_fingerprint = None
        if not force:
            authorized, auth_message, device_fingerprint = (
                self.device_auth_manager.check_device_authorization(
                    license_obj.license_key, license_obj.max_devices
                )
            )

            if not authorized:
                logger.error(f"设备授权检查失败: {auth_message}")
                return False, auth_message, device_fingerprint

        # 激活许可证
        success, message = self.license_manager.activate_license(
            license_obj, machine_id
        )

        if success:
            # 保存许可证
            self.license_manager.save_license(license_obj)
            logger.info(f"许可证激活成功: {license_obj.license_key}")

        return success, message, device_fingerprint


class LicenseMonitor:
    """许可证监控器"""

    def __init__(
        self,
        license_manager: LicenseManager,
        device_auth_manager: DeviceAuthManager | None = None,
    ):
        """初始化

        Args:
            license_manager: 许可证管理器
            device_auth_manager: 设备授权管理器
        """
        self.license_manager = license_manager
        self.device_auth_manager = device_auth_manager or get_device_auth_manager()
        self.validator = EnhancedLicenseValidator(license_manager, device_auth_manager)

    def check_license_health(self) -> dict[str, Any]:
        """检查许可证健康状态

        Returns:
            健康状态报告
        """
        report = self.validator.validate()

        health_status = {
            "status": report.result.value,
            "message": report.message,
            "timestamp": report.timestamp.isoformat(),
            "is_healthy": report.result == ValidationResult.SUCCESS,
        }

        if report.license_info:
            health_status["license"] = report.license_info

        if report.device_fingerprint:
            health_status["device"] = {
                "device_id": report.device_fingerprint.device_id,
                "hostname": report.device_fingerprint.hostname,
                "platform": report.device_fingerprint.platform_info.get("system"),
            }

        if report.additional_info:
            health_status["usage_stats"] = report.additional_info

        return health_status

    def detect_anomalies(self, license_key: str) -> list[dict[str, Any]]:
        """检测异常行为

        Args:
            license_key: 许可证密钥

        Returns:
            异常列表
        """
        anomalies = []

        # 获取使用统计
        stats = self.device_auth_manager.get_device_usage_stats(license_key)

        # 检测异常1: 短时间内多设备尝试
        if stats["total_devices"] > 3:
            anomalies.append(
                {
                    "type": "multiple_devices",
                    "severity": "high",
                    "message": f"检测到{stats['total_devices']}个不同设备尝试使用同一许可证",
                    "data": {"device_count": stats["total_devices"]},
                }
            )

        # 检测异常2: 频繁失败尝试
        for device in stats["devices"]:
            if device["failed_attempts"] > 10:
                anomalies.append(
                    {
                        "type": "frequent_failures",
                        "severity": "medium",
                        "message": f"设备 {device['device_id'][:8]}... 有{device['failed_attempts']}次失败尝试",
                        "data": device,
                    }
                )

        # 检测异常3: 被封控的设备仍在尝试
        blocked_attempts = [d for d in stats["devices"] if d["is_blocked"]]
        if blocked_attempts:
            anomalies.append(
                {
                    "type": "blocked_device_attempts",
                    "severity": "critical",
                    "message": f"有{len(blocked_attempts)}个被封控设备仍在尝试访问",
                    "data": blocked_attempts,
                }
            )

        return anomalies

    def get_usage_report(self, license_key: str) -> dict[str, Any]:
        """获取使用报告

        Args:
            license_key: 许可证密钥

        Returns:
            使用报告
        """
        stats = self.device_auth_manager.get_device_usage_stats(license_key)
        anomalies = self.detect_anomalies(license_key)

        return {
            "license_key": license_key,
            "generated_at": datetime.now().isoformat(),
            "statistics": stats,
            "anomalies": anomalies,
            "health_status": "healthy" if not anomalies else "warning",
        }
