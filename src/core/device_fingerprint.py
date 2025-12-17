"""
设备指纹识别模块

用于采集和验证设备唯一标识信息，防止作弊和滥用

增强功能:
1. 多维度设备识别和验证
2. 设备行为分析和异常检测
3. 设备信任度评估
4. 设备迁移和克隆检测
5. 实时设备监控和告警
6. 设备性能分析和优化建议
7. 设备合规性检查
8. 设备生命周期管理
"""

import hashlib
import json
import logging
import platform
import socket
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DeviceTrustLevel(Enum):
    """设备信任级别"""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TRUSTED = "trusted"


class DeviceStatus(Enum):
    """设备状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLACKLISTED = "blacklisted"
    MAINTENANCE = "maintenance"


@dataclass
class DeviceFingerprint:
    """设备指纹信息"""

    device_id: str  # 设备唯一ID（基于多个硬件信息生成）
    hostname: str  # 主机名
    mac_address: str  # MAC地址
    cpu_info: str  # CPU信息
    system_uuid: str  # 系统UUID
    platform_info: dict[str, str]  # 平台信息
    network_info: dict[str, Any]  # 网络信息
    timestamp: datetime  # 采集时间
    fingerprint_version: str = "2.0"  # 指纹版本

    # 新增字段
    trust_level: DeviceTrustLevel = DeviceTrustLevel.UNKNOWN  # 信任级别
    status: DeviceStatus = DeviceStatus.ACTIVE  # 设备状态
    last_seen: datetime | None = None  # 最后活跃时间
    usage_count: int = 0  # 使用次数
    performance_score: float = 0.0  # 性能评分
    compliance_status: dict[str, bool] = None  # 合规状态
    security_features: list[str] = None  # 安全特性
    hardware_hash: str = ""  # 硬件哈希
    software_hash: str = ""  # 软件哈希

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data: dict[str, Any] = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.last_seen:
            data["last_seen"] = self.last_seen.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceFingerprint":
        """从字典创建"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("last_seen"):
            data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def update_usage(self) -> None:
        """更新使用统计"""
        self.usage_count += 1
        self.last_seen = datetime.now()

    def calculate_performance_score(self) -> float:
        """计算性能评分"""
        score = 0.0

        # 基于CPU信息评分
        if "Intel" in self.cpu_info or "AMD" in self.cpu_info:
            score += 30

        # 基于平台信息评分
        if self.platform_info.get("system") == "Windows":
            score += 20
        elif self.platform_info.get("system") == "Darwin":
            score += 25
        elif self.platform_info.get("system") == "Linux":
            score += 15

        # 基于网络信息评分
        if self.network_info.get("ip_address"):
            score += 10

        # 基于使用历史评分
        if self.usage_count > 10:
            score += 15
        elif self.usage_count > 5:
            score += 10

        self.performance_score = min(100.0, score)
        return self.performance_score

    def check_compliance(self) -> dict[str, bool]:
        """检查合规性"""
        compliance = {
            "has_security_features": len(self.security_features or []) > 0,
            "recent_activity": self.last_seen
            and (datetime.now() - self.last_seen).days < 30,
            "stable_fingerprint": self.hardware_hash == self._calculate_hardware_hash(),
            "valid_platform": self.platform_info.get("system")
            in ["Windows", "Darwin", "Linux"],
            "has_network": bool(self.network_info.get("ip_address")),
        }

        self.compliance_status = compliance
        return compliance

    def _calculate_hardware_hash(self) -> str:
        """计算硬件哈希"""
        hardware_string = f"{self.mac_address}{self.cpu_info}{self.system_uuid}"
        return hashlib.sha256(hardware_string.encode()).hexdigest()[:16]


class DeviceFingerprintCollector:
    """设备指纹采集器"""

    def __init__(self):
        self.cache_file = Path("data") / "device_fingerprint.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.device_registry_file = Path("data") / "device_registry.json"
        self.device_registry: dict[str, DeviceFingerprint] = {}
        self._load_device_registry()

    def collect(self, force_refresh: bool = False) -> DeviceFingerprint:
        """采集设备指纹信息

        Args:
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            设备指纹对象
        """
        # 如果有缓存且不强制刷新，返回缓存
        if not force_refresh and self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    cached_data = json.load(f)
                    cached_fingerprint = DeviceFingerprint.from_dict(cached_data)

                    # 验证缓存是否仍然有效
                    if self._verify_fingerprint(cached_fingerprint):
                        logger.info("使用缓存的设备指纹")
                        return cached_fingerprint
            except Exception as e:
                logger.warning(f"加载缓存指纹失败: {e}")

        # 采集新的指纹
        logger.info("开始采集设备指纹...")

        fingerprint = DeviceFingerprint(
            device_id=self._generate_device_id(),
            hostname=self._get_hostname(),
            mac_address=self._get_mac_address(),
            cpu_info=self._get_cpu_info(),
            system_uuid=self._get_system_uuid(),
            platform_info=self._get_platform_info(),
            network_info=self._get_network_info(),
            timestamp=datetime.now(),
            security_features=self._detect_security_features(),
            hardware_hash=self._calculate_hardware_hash(),
            software_hash=self._calculate_software_hash(),
        )

        # 更新设备信息
        fingerprint.update_usage()
        fingerprint.calculate_performance_score()
        fingerprint.check_compliance()

        # 更新设备注册表
        self._update_device_registry(fingerprint)

        # 保存到缓存
        self._save_cache(fingerprint)

        logger.info(f"设备指纹采集完成: {fingerprint.device_id}")
        return fingerprint

    def _generate_device_id(self) -> str:
        """生成设备唯一ID

        基于多个硬件信息的组合生成稳定的设备ID
        """
        # 采集多个硬件标识
        identifiers = [
            platform.node(),  # 主机名
            platform.machine(),  # 机器类型
            str(uuid.getnode()),  # MAC地址数值
            self._get_system_uuid(),  # 系统UUID
            self._get_cpu_info(),  # CPU信息
            self._get_disk_serial(),  # 磁盘序列号
        ]

        # 组合所有标识并生成哈希
        combined = ":".join(filter(None, identifiers))
        device_hash = hashlib.sha256(combined.encode()).hexdigest()

        return device_hash[:32].upper()

    def _get_hostname(self) -> str:
        """获取主机名"""
        try:
            return socket.gethostname()
        except Exception as e:
            logger.warning(f"获取主机名失败: {e}")
            return "unknown"

    def _get_mac_address(self) -> str:
        """获取MAC地址"""
        try:
            mac = uuid.getnode()
            mac_str = ":".join(
                [f"{(mac >> elements) & 0xFF:02x}" for elements in range(0, 8 * 6, 8)][
                    ::-1
                ]
            )
            return mac_str
        except Exception as e:
            logger.warning(f"获取MAC地址失败: {e}")
            return "00:00:00:00:00:00"

    def _get_cpu_info(self) -> str:
        """获取CPU信息"""
        try:
            system = platform.system()
            if system == "Windows":
                return self._get_cpu_info_windows()
            if system == "Linux":
                return self._get_cpu_info_linux()
            if system == "Darwin":
                return self._get_cpu_info_macos()
            return platform.processor()
        except Exception as e:
            logger.warning(f"获取CPU信息失败: {e}")
            return "unknown"

    def _get_cpu_info_windows(self) -> str:
        """Windows系统获取CPU信息"""
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,  # 不检查返回码
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                return lines[1].strip()
        except Exception as e:
            logger.debug(f"WMIC获取CPU ID失败: {e}")

        return platform.processor()

    def _get_cpu_info_linux(self) -> str:
        """Linux系统获取CPU信息"""
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        except Exception:
            pass
        return platform.processor()

    def _get_cpu_info_macos(self) -> str:
        """macOS系统获取CPU信息"""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.stdout.strip()
        except Exception:
            pass
        return platform.processor()

    def _get_system_uuid(self) -> str:
        """获取系统UUID"""
        try:
            system = platform.system()

            if system == "Windows":
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].strip()

            elif system == "Linux":
                # 尝试读取machine-id
                try:
                    with open("/etc/machine-id", encoding="utf-8") as f:
                        return f.read().strip()
                except FileNotFoundError:
                    with open("/var/lib/dbus/machine-id", encoding="utf-8") as f:
                        return f.read().strip()

            elif system == "Darwin":
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        return line.split('"')[3]

        except Exception as e:
            logger.warning(f"获取系统UUID失败: {e}")

        # 如果都失败，生成一个基于MAC地址的UUID
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.getnode())))

    def _get_disk_serial(self) -> str:
        """获取磁盘序列号"""
        try:
            system = platform.system()

            if system == "Windows":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].strip()

            elif system == "Linux":
                result = subprocess.run(
                    ["lsblk", "-o", "SERIAL", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                return result.stdout.strip().split("\n")[0]

            elif system == "Darwin":
                result = subprocess.run(
                    ["system_profiler", "SPSerialATADataType"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                for line in result.stdout.split("\n"):
                    if "Serial Number" in line:
                        return line.split(":")[1].strip()

        except Exception as e:
            logger.debug(f"获取磁盘序列号失败: {e}")

        return ""

    def _get_platform_info(self) -> dict[str, str]:
        """获取平台信息"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

    def _get_network_info(self) -> dict[str, Any]:
        """获取网络信息"""
        network_info = {
            "hostname": self._get_hostname(),
            "local_ip": self._get_local_ip(),
            "public_ip": "",  # 需要外部服务获取
            "mac_address": self._get_mac_address(),
        }

        return network_info

    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.debug(f"获取本地IP失败: {e}")
            return "127.0.0.1"

    def _verify_fingerprint(self, fingerprint: DeviceFingerprint) -> bool:
        """验证指纹是否仍然有效

        检查关键硬件信息是否发生变化

        Args:
            fingerprint: 待验证的指纹

        Returns:
            是否有效
        """
        try:
            current_mac = self._get_mac_address()
            current_system_uuid = self._get_system_uuid()

            # 检查关键信息是否匹配
            if fingerprint.mac_address != current_mac:
                logger.warning("MAC地址已变化")
                return False

            if fingerprint.system_uuid != current_system_uuid:
                logger.warning("系统UUID已变化")
                return False

            # hostname可能会改变，不作为强制验证项
            return True

        except Exception as e:
            logger.error(f"验证指纹失败: {e}")
            return False

    def _save_cache(self, fingerprint: DeviceFingerprint) -> None:
        """保存指纹缓存"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                f.write(fingerprint.to_json())
            logger.debug(f"设备指纹已缓存: {self.cache_file}")
        except Exception as e:
            logger.warning(f"保存指纹缓存失败: {e}")

    def _load_device_registry(self) -> None:
        """加载设备注册表"""
        try:
            if self.device_registry_file.exists():
                with open(self.device_registry_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for device_id, device_data in data.items():
                        self.device_registry[device_id] = DeviceFingerprint.from_dict(
                            device_data
                        )
                logger.info(f"已加载 {len(self.device_registry)} 个设备记录")
        except Exception as e:
            logger.warning(f"加载设备注册表失败: {e}")

    def _save_device_registry(self) -> None:
        """保存设备注册表"""
        try:
            data = {
                device_id: device.to_dict()
                for device_id, device in self.device_registry.items()
            }
            with open(self.device_registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存设备注册表失败: {e}")

    def _update_device_registry(self, fingerprint: DeviceFingerprint) -> None:
        """更新设备注册表"""
        self.device_registry[fingerprint.device_id] = fingerprint
        self._save_device_registry()

    def _detect_security_features(self) -> list[str]:
        """检测安全特性"""
        features = []

        try:
            # 检测虚拟化
            if self._is_virtualized():
                features.append("virtualized")

            # 检测安全启动
            if self._has_secure_boot():
                features.append("secure_boot")

            # 检测TPM
            if self._has_tpm():
                features.append("tpm")

            # 检测防火墙
            if self._has_firewall():
                features.append("firewall")

        except Exception as e:
            logger.warning(f"检测安全特性失败: {e}")

        return features

    def _calculate_hardware_hash(self) -> str:
        """计算硬件哈希"""
        try:
            hardware_string = f"{self._get_mac_address()}{self._get_cpu_info()}{self._get_system_uuid()}"
            return hashlib.sha256(hardware_string.encode()).hexdigest()[:16]
        except Exception:
            return ""

    def _calculate_software_hash(self) -> str:
        """计算软件哈希"""
        try:
            software_string = (
                f"{platform.system()}{platform.release()}{platform.version()}"
            )
            return hashlib.sha256(software_string.encode()).hexdigest()[:16]
        except Exception:
            return ""

    def _is_virtualized(self) -> bool:
        """检测是否在虚拟环境中运行"""
        try:
            # 检测常见的虚拟化标识
            vm_indicators = [
                "VMware",
                "VirtualBox",
                "QEMU",
                "Xen",
                "Hyper-V",
                "Parallels",
                "Docker",
                "KVM",
            ]

            system_info = platform.platform().lower()
            return any(indicator.lower() in system_info for indicator in vm_indicators)
        except Exception:
            return False

    def _has_secure_boot(self) -> bool:
        """检测是否有安全启动"""
        try:
            if platform.system() == "Windows":
                # Windows安全启动检测
                result = subprocess.run(
                    ["powershell", "-Command", "Get-SecureBootUEFI"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "True" in result.stdout
            return False
        except Exception:
            return False

    def _has_tpm(self) -> bool:
        """检测是否有TPM"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Tpm"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "TpmPresent" in result.stdout and "True" in result.stdout
            return False
        except Exception:
            return False

    def _has_firewall(self) -> bool:
        """检测是否有防火墙"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles", "state"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "ON" in result.stdout
            return False
        except Exception:
            return False

    def get_device_analytics(self) -> dict[str, Any]:
        """获取设备分析数据"""
        analytics = {
            "total_devices": len(self.device_registry),
            "active_devices": 0,
            "trust_levels": {},
            "platform_distribution": {},
            "performance_scores": [],
            "compliance_rate": 0.0,
            "security_features": {},
        }

        if not self.device_registry:
            return analytics

        active_count = 0
        compliance_count = 0
        security_features_count = {}

        for device in self.device_registry.values():
            # 活跃设备统计
            if device.last_seen and (datetime.now() - device.last_seen).days < 30:
                active_count += 1

            # 信任级别统计
            trust_level = device.trust_level.value
            analytics["trust_levels"][trust_level] = (
                analytics["trust_levels"].get(trust_level, 0) + 1
            )

            # 平台分布统计
            platform_name = device.platform_info.get("system", "unknown")
            analytics["platform_distribution"][platform_name] = (
                analytics["platform_distribution"].get(platform_name, 0) + 1
            )

            # 性能评分
            analytics["performance_scores"].append(device.performance_score)

            # 合规性统计
            if device.compliance_status:
                compliance_count += sum(device.compliance_status.values())

            # 安全特性统计
            if device.security_features:
                for feature in device.security_features:
                    security_features_count[feature] = (
                        security_features_count.get(feature, 0) + 1
                    )

        analytics["active_devices"] = active_count
        analytics["compliance_rate"] = (
            compliance_count / (len(self.device_registry) * 5)
            if self.device_registry
            else 0.0
        )
        analytics["security_features"] = security_features_count

        return analytics

    def detect_device_anomalies(self) -> list[dict[str, Any]]:
        """检测设备异常"""
        anomalies = []

        for device_id, device in self.device_registry.items():
            # 检测硬件哈希变化
            current_hardware_hash = device._calculate_hardware_hash()
            if device.hardware_hash and device.hardware_hash != current_hardware_hash:
                anomalies.append(
                    {
                        "device_id": device_id,
                        "type": "hardware_change",
                        "severity": "high",
                        "description": "检测到硬件配置变化",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检测长时间未活跃
            if device.last_seen and (datetime.now() - device.last_seen).days > 90:
                anomalies.append(
                    {
                        "device_id": device_id,
                        "type": "inactive_device",
                        "severity": "medium",
                        "description": "设备长时间未活跃",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检测性能异常
            if device.performance_score < 30:
                anomalies.append(
                    {
                        "device_id": device_id,
                        "type": "low_performance",
                        "severity": "medium",
                        "description": "设备性能评分较低",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return anomalies


class DeviceAuthManager:
    """设备授权管理器"""

    def __init__(self, storage_path: Path | None = None):
        """初始化

        Args:
            storage_path: 存储路径
        """
        if storage_path is None:
            storage_path = Path("data") / "device_auth"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.fingerprint_collector = DeviceFingerprintCollector()
        self.auth_history_file = self.storage_path / "auth_history.json"
        self.blocked_devices_file = self.storage_path / "blocked_devices.json"

        # 加载封控列表
        self._blocked_devices = self._load_blocked_devices()

    def check_device_authorization(
        self, license_key: str, max_devices: int = 1
    ) -> tuple[bool, str, DeviceFingerprint]:
        """检查设备授权

        Args:
            license_key: 许可证密钥
            max_devices: 最大设备数量

        Returns:
            (是否授权, 消息, 设备指纹)
        """
        # 采集当前设备指纹
        fingerprint = self.fingerprint_collector.collect()

        # 检查是否被封控
        if self._is_device_blocked(fingerprint.device_id):
            self._record_auth_attempt(
                license_key, fingerprint, success=False, reason="设备已被封控"
            )

            # 记录审计日志
            try:
                from .audit_logger import get_audit_logger

                audit_logger = get_audit_logger()
                audit_logger.log_license_validated(
                    license_key, fingerprint.device_id, False, "设备已被封控"
                )
            except Exception:
                pass

            return False, "设备已被封控", fingerprint

        # 加载该许可证的授权历史
        history = self._load_auth_history(license_key)

        # 获取已授权的设备列表
        authorized_devices = set()
        for record in history:
            if record.get("success"):
                authorized_devices.add(record.get("device_id"))

        # 检查设备数量限制
        if (
            fingerprint.device_id not in authorized_devices
            and len(authorized_devices) >= max_devices
        ):
            self._record_auth_attempt(
                license_key, fingerprint, success=False, reason="超出设备数量限制"
            )

            # 记录审计日志
            try:
                from .audit_logger import get_audit_logger

                audit_logger = get_audit_logger()
                audit_logger.log_license_validated(
                    license_key, fingerprint.device_id, False, "超出设备数量限制"
                )
            except Exception:
                pass

            return False, f"已超出最大设备数量限制({max_devices})", fingerprint

        # 记录授权成功
        self._record_auth_attempt(license_key, fingerprint, success=True)

        # 记录审计日志和IP追踪
        try:
            from .audit_logger import get_audit_logger
            from .ip_tracker import get_ip_tracker

            audit_logger = get_audit_logger()
            ip_tracker = get_ip_tracker()

            ip_info = ip_tracker.track_ip(license_key, fingerprint.device_id)
            audit_logger.log_license_validated(
                license_key, fingerprint.device_id, True, "", ip_info.ip_address
            )
        except Exception:
            pass

        logger.info(f"设备授权检查通过: {fingerprint.device_id}")
        return True, "授权成功", fingerprint

    def block_device(self, device_id: str, reason: str = "") -> bool:
        """封控设备

        Args:
            device_id: 设备ID
            reason: 封控原因

        Returns:
            是否成功
        """
        self._blocked_devices[device_id] = {
            "blocked_at": datetime.now().isoformat(),
            "reason": reason,
        }
        self._save_blocked_devices()
        logger.warning(f"设备已封控: {device_id}, 原因: {reason}")
        return True

    def unblock_device(self, device_id: str) -> bool:
        """解除设备封控

        Args:
            device_id: 设备ID

        Returns:
            是否成功
        """
        if device_id in self._blocked_devices:
            del self._blocked_devices[device_id]
            self._save_blocked_devices()
            logger.info(f"设备已解除封控: {device_id}")
            return True
        return False

    def get_device_usage_stats(self, license_key: str) -> dict[str, Any]:
        """获取设备使用统计

        Args:
            license_key: 许可证密钥

        Returns:
            统计信息
        """
        history = self._load_auth_history(license_key)

        devices = {}
        for record in history:
            device_id = record.get("device_id")
            if device_id not in devices:
                devices[device_id] = {
                    "device_id": device_id,
                    "hostname": record.get("hostname"),
                    "first_seen": record.get("timestamp"),
                    "last_seen": record.get("timestamp"),
                    "total_attempts": 0,
                    "successful_attempts": 0,
                    "failed_attempts": 0,
                    "is_blocked": self._is_device_blocked(device_id),
                }

            devices[device_id]["last_seen"] = record.get("timestamp")
            devices[device_id]["total_attempts"] += 1

            if record.get("success"):
                devices[device_id]["successful_attempts"] += 1
            else:
                devices[device_id]["failed_attempts"] += 1

        return {
            "license_key": license_key,
            "total_devices": len(devices),
            "total_attempts": len(history),
            "devices": list(devices.values()),
        }

    def _is_device_blocked(self, device_id: str) -> bool:
        """检查设备是否被封控"""
        return device_id in self._blocked_devices

    def _record_auth_attempt(
        self,
        license_key: str,
        fingerprint: DeviceFingerprint,
        success: bool,
        reason: str = "",
    ) -> None:
        """记录授权尝试"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "license_key": license_key,
            "device_id": fingerprint.device_id,
            "hostname": fingerprint.hostname,
            "mac_address": fingerprint.mac_address,
            "local_ip": fingerprint.network_info.get("local_ip"),
            "success": success,
            "reason": reason,
        }

        # 读取现有历史
        history = []
        if self.auth_history_file.exists():
            try:
                with open(self.auth_history_file, encoding="utf-8") as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"读取授权历史失败: {e}")

        # 添加新记录
        history.append(record)

        # 保持最近10000条记录
        if len(history) > 10000:
            history = history[-10000:]

        # 保存
        try:
            with open(self.auth_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存授权历史失败: {e}")

    def _load_auth_history(self, license_key: str | None = None) -> list[dict]:
        """加载授权历史"""
        if not self.auth_history_file.exists():
            return []

        try:
            with open(self.auth_history_file, encoding="utf-8") as f:
                history = json.load(f)

            # 如果指定了许可证，筛选记录
            if license_key:
                history = [r for r in history if r.get("license_key") == license_key]

            return history

        except Exception as e:
            logger.error(f"加载授权历史失败: {e}")
            return []

    def _load_blocked_devices(self) -> dict:
        """加载封控设备列表"""
        if not self.blocked_devices_file.exists():
            return {}

        try:
            with open(self.blocked_devices_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载封控列表失败: {e}")
            return {}

    def _save_blocked_devices(self) -> None:
        """保存封控设备列表"""
        try:
            with open(self.blocked_devices_file, "w", encoding="utf-8") as f:
                json.dump(self._blocked_devices, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存封控列表失败: {e}")


# 全局实例
_device_auth_manager: DeviceAuthManager | None = None


def get_device_auth_manager() -> DeviceAuthManager:
    """获取全局设备授权管理器"""
    global _device_auth_manager
    if _device_auth_manager is None:
        _device_auth_manager = DeviceAuthManager()
    return _device_auth_manager
