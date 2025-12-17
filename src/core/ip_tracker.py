"""
IP地址追踪模块

用于追踪和记录用户的IP地址信息，包括地理位置查询
"""

import ipaddress
import json
import logging
import socket
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _is_valid_ip(ip_address: str) -> bool:
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False


@dataclass
class IPInfo:
    """IP地址信息"""

    ip_address: str  # IP地址
    timestamp: datetime  # 记录时间
    country: str = ""  # 国家
    region: str = ""  # 地区
    city: str = ""  # 城市
    isp: str = ""  # ISP提供商
    is_proxy: bool = False  # 是否使用代理
    is_vpn: bool = False  # 是否使用VPN

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IPInfo":
        """从字典创建"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class IPTracker:
    """IP地址追踪器"""

    def __init__(self, storage_path: Path | None = None):
        """初始化

        Args:
            storage_path: 存储路径
        """
        if storage_path is None:
            storage_path = Path("data") / "ip_tracking"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.ip_history_file = self.storage_path / "ip_history.json"
        self.suspicious_ips_file = self.storage_path / "suspicious_ips.json"

        # 加载可疑IP列表
        self._suspicious_ips = self._load_suspicious_ips()

    def track_ip(
        self, license_key: str, device_id: str, ip_address: str | None = None
    ) -> IPInfo:
        """追踪IP地址

        Args:
            license_key: 许可证密钥
            device_id: 设备ID
            ip_address: IP地址（如果为None，自动获取）

        Returns:
            IP信息
        """
        # 获取IP地址
        if ip_address is None:
            ip_address = self._get_public_ip()

        # 创建IP信息对象
        ip_info = IPInfo(ip_address=ip_address, timestamp=datetime.now())

        # 获取地理位置信息（可选）
        try:
            self._enrich_ip_info(ip_info)
        except Exception as e:
            logger.debug(f"获取IP地理信息失败: {e}")

        # 检查是否可疑
        if self._is_suspicious_ip(ip_address):
            logger.warning(f"检测到可疑IP: {ip_address}")

        # 记录历史
        self._record_ip_history(license_key, device_id, ip_info)

        return ip_info

    def get_ip_history(
        self, license_key: str | None = None, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        """获取IP历史记录

        Args:
            license_key: 许可证密钥（可选）
            device_id: 设备ID（可选）

        Returns:
            IP历史记录列表
        """
        if not self.ip_history_file.exists():
            return []

        try:
            with open(self.ip_history_file, encoding="utf-8") as f:
                history = json.load(f)

            # 过滤
            if license_key:
                history = [r for r in history if r.get("license_key") == license_key]
            if device_id:
                history = [r for r in history if r.get("device_id") == device_id]

            return history

        except Exception as e:
            logger.error(f"读取IP历史失败: {e}")
            return []

    def mark_suspicious_ip(self, ip_address: str, reason: str = "") -> None:
        """标记可疑IP

        Args:
            ip_address: IP地址
            reason: 原因
        """
        self._suspicious_ips[ip_address] = {
            "marked_at": datetime.now().isoformat(),
            "reason": reason,
        }
        self._save_suspicious_ips()
        logger.warning(f"IP已标记为可疑: {ip_address}, 原因: {reason}")

    def unmark_suspicious_ip(self, ip_address: str) -> bool:
        """取消可疑IP标记

        Args:
            ip_address: IP地址

        Returns:
            是否成功
        """
        if ip_address in self._suspicious_ips:
            del self._suspicious_ips[ip_address]
            self._save_suspicious_ips()
            logger.info(f"IP可疑标记已取消: {ip_address}")
            return True
        return False

    def get_ip_stats(self, license_key: str) -> dict[str, Any]:
        """获取IP统计信息

        Args:
            license_key: 许可证密钥

        Returns:
            统计信息
        """
        history = self.get_ip_history(license_key=license_key)

        unique_ips = {r["ip_info"]["ip_address"] for r in history}
        countries = {
            r["ip_info"].get("country", "")
            for r in history
            if r["ip_info"].get("country")
        }

        suspicious_count = sum(
            1 for r in history if self._is_suspicious_ip(r["ip_info"]["ip_address"])
        )

        return {
            "license_key": license_key,
            "total_records": len(history),
            "unique_ips": len(unique_ips),
            "unique_countries": len(countries),
            "suspicious_ips": suspicious_count,
            "countries": list(countries),
            "recent_ips": [r["ip_info"]["ip_address"] for r in history[-10:]],
        }

    def detect_ip_anomalies(self, license_key: str) -> list[dict[str, Any]]:
        """检测IP相关异常

        Args:
            license_key: 许可证密钥

        Returns:
            异常列表
        """
        anomalies = []
        history = self.get_ip_history(license_key=license_key)

        if not history:
            return anomalies

        # 异常1: 短时间内多个不同IP
        recent_ips = [r["ip_info"]["ip_address"] for r in history[-20:]]
        unique_recent_ips = set(recent_ips)

        if len(unique_recent_ips) > 5:
            anomalies.append(
                {
                    "type": "multiple_ips",
                    "severity": "high",
                    "message": f"最近20次连接使用了{len(unique_recent_ips)}个不同IP地址",
                    "data": {
                        "ip_count": len(unique_recent_ips),
                        "ips": list(unique_recent_ips),
                    },
                }
            )

        # 异常2: 来自多个国家
        countries = {
            r["ip_info"].get("country", "")
            for r in history
            if r["ip_info"].get("country")
        }
        if len(countries) > 3:
            anomalies.append(
                {
                    "type": "multiple_countries",
                    "severity": "medium",
                    "message": f"检测到来自{len(countries)}个不同国家的连接",
                    "data": {"countries": list(countries)},
                }
            )

        # 异常3: 使用可疑IP
        suspicious = [
            r["ip_info"]["ip_address"]
            for r in history
            if self._is_suspicious_ip(r["ip_info"]["ip_address"])
        ]
        if suspicious:
            anomalies.append(
                {
                    "type": "suspicious_ip",
                    "severity": "critical",
                    "message": f"检测到{len(suspicious)}次使用可疑IP",
                    "data": {"suspicious_ips": suspicious},
                }
            )

        return anomalies

    def _get_public_ip(self) -> str:
        """获取公网IP地址"""
        from src.utils.safe_network import (
            HAS_REQUESTS,
            RetryStrategy,
            SafeNetworkClient,
        )

        if not HAS_REQUESTS:
            return self._get_local_ip()

        services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]

        client = SafeNetworkClient(
            timeout=3,
            retry_strategy=RetryStrategy(
                max_retries=2, initial_delay=0.2, max_delay=1.0
            ),
        )

        for service in services:
            try:
                result = client.request("GET", service)
                if not isinstance(result, dict):
                    continue

                ip_text = str(result.get("text", "")).strip()
                if ip_text and _is_valid_ip(ip_text):
                    return ip_text
            except Exception:
                continue

        # 返回本地IP作为fallback
        return self._get_local_ip()

    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def _enrich_ip_info(self, ip_info: IPInfo) -> None:
        """丰富IP信息（地理位置等）

        注意: 这需要使用第三方API服务，这里提供一个简单实现
        生产环境建议使用 ip2location, MaxMind GeoIP 等专业服务
        """
        from src.utils.safe_network import (
            HAS_REQUESTS,
            RetryStrategy,
            SafeNetworkClient,
        )

        if not HAS_REQUESTS:
            return

        ip_address = ip_info.ip_address.strip()
        if not _is_valid_ip(ip_address):
            return

        client = SafeNetworkClient(
            timeout=5,
            retry_strategy=RetryStrategy(
                max_retries=1, initial_delay=0.2, max_delay=0.5
            ),
        )

        try:
            # 使用 https 的免费服务，返回字段更丰富（proxy/vpn 等）
            url = f"https://ipwho.is/{ip_address}"
            data = client.request("GET", url)
            if not isinstance(data, dict):
                return
            if data.get("success") is False:
                return

            ip_info.country = str(data.get("country") or "")
            ip_info.region = str(data.get("region") or "")
            ip_info.city = str(data.get("city") or "")

            connection = data.get("connection")
            if isinstance(connection, dict):
                ip_info.isp = str(connection.get("isp") or "")

            security = data.get("security")
            if isinstance(security, dict):
                ip_info.is_proxy = bool(security.get("proxy") or False)
                ip_info.is_vpn = bool(security.get("vpn") or False)
        except Exception as e:
            logger.debug(f"获取IP地理信息失败: {e}")

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """检查IP是否可疑"""
        return ip_address in self._suspicious_ips

    def _record_ip_history(
        self, license_key: str, device_id: str, ip_info: IPInfo
    ) -> None:
        """记录IP历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "license_key": license_key,
            "device_id": device_id,
            "ip_info": ip_info.to_dict(),
        }

        # 读取现有历史
        history = []
        if self.ip_history_file.exists():
            try:
                with open(self.ip_history_file, encoding="utf-8") as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"读取IP历史失败: {e}")

        # 添加新记录
        history.append(record)

        # 保持最近10000条记录
        if len(history) > 10000:
            history = history[-10000:]

        # 保存
        try:
            with open(self.ip_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存IP历史失败: {e}")

    def _load_suspicious_ips(self) -> dict:
        """加载可疑IP列表"""
        if not self.suspicious_ips_file.exists():
            return {}

        try:
            with open(self.suspicious_ips_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载可疑IP列表失败: {e}")
            return {}

    def _save_suspicious_ips(self) -> None:
        """保存可疑IP列表"""
        try:
            with open(self.suspicious_ips_file, "w", encoding="utf-8") as f:
                json.dump(self._suspicious_ips, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存可疑IP列表失败: {e}")


# 全局实例
_ip_tracker: IPTracker | None = None


def get_ip_tracker() -> IPTracker:
    """获取全局IP追踪器"""
    global _ip_tracker
    if _ip_tracker is None:
        _ip_tracker = IPTracker()
    return _ip_tracker
