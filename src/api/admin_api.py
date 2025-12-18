"""
管理后台API接口

提供许可证管理、设备监控、异常处理等功能
"""

import hmac
import logging
import os
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, jsonify, request, send_file
    from flask_cors import CORS

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from ..core.device_fingerprint import DeviceAuthManager
from ..core.license_manager import LicenseManager
from ..core.license_validator import EnhancedLicenseValidator, LicenseMonitor

logger = logging.getLogger(__name__)

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _parse_cors_origins(raw: str) -> str | list[str]:
    """Parse `VCL_ADMIN_CORS_ORIGINS` into a Flask-CORS compatible value."""
    value = raw.strip()
    if value == "*":
        return "*"
    return [part.strip() for part in value.split(",") if part.strip()]


class AdminAPI:
    """管理后台API"""

    def __init__(
        self,
        license_manager: LicenseManager,
        device_auth_manager: DeviceAuthManager,
        admin_secret: str | None = None,
        host: str = "127.0.0.1",
        port: int = 5000,
    ):
        """初始化

        Args:
            license_manager: 许可证管理器
            device_auth_manager: 设备授权管理器
            admin_secret: 管理后台密钥
            host: 主机地址
            port: 端口
        """
        if not FLASK_AVAILABLE:
            raise ImportError(
                "Flask 未安装或导入失败。请运行: pip install flask flask-cors"
            )

        self.license_manager = license_manager
        self.device_auth_manager = device_auth_manager
        self.validator = EnhancedLicenseValidator(license_manager, device_auth_manager)
        self.monitor = LicenseMonitor(license_manager, device_auth_manager)

        # 安全：优先使用环境变量提供的密钥，避免硬编码
        resolved_secret = admin_secret or os.getenv("VCL_ADMIN_SECRET_KEY")
        if not resolved_secret:
            raise ValueError(
                "必须提供管理后台 SECRET_KEY，可通过参数或环境变量 VCL_ADMIN_SECRET_KEY 设置"
            )
        if len(resolved_secret) < 32:
            raise ValueError("管理后台密钥长度必须>=32")
        self._admin_secret = resolved_secret

        # 创建Flask应用
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = resolved_secret
        self.app.config["JSON_AS_ASCII"] = False

        self.host = host
        self.port = port

        # 启用CORS（默认关闭，避免误配置导致对公网放开；如需跨域请显式配置）
        cors_origins_env = os.getenv("VCL_ADMIN_CORS_ORIGINS", "").strip()
        if cors_origins_env:
            CORS(
                self.app,
                resources={
                    r"/api/*": {"origins": _parse_cors_origins(cors_origins_env)}
                },
            )
        else:
            if self.host not in _LOCAL_HOSTS:
                logger.warning(
                    "AdminAPI 绑定到非本地主机 (%s) 且未设置 VCL_ADMIN_CORS_ORIGINS，"
                    "已默认禁用 CORS；如需浏览器跨域访问请显式设置该变量。",
                    self.host,
                )

        # 注册路由
        self._register_routes()

    def _register_routes(self):
        """注册路由"""

        dashboard_path = Path(__file__).with_name("admin_dashboard.html")

        @self.app.route("/", methods=["GET"])
        @self.app.route("/dashboard", methods=["GET"])
        def dashboard_page():
            """管理后台页面（同源访问，避免依赖 CORS）"""
            if not dashboard_path.exists():
                return jsonify({"error": "管理后台页面缺失"}), 404
            return send_file(dashboard_path, mimetype="text/html")

        def _auth_guard():
            """简单的共享密钥校验，保护敏感API"""
            header = request.headers.get("X-Admin-Secret") or request.headers.get(
                "Authorization", ""
            )
            token = header.removeprefix("Bearer ").strip() if header else ""
            if not token:
                logger.warning("管理后台请求缺少密钥头")
                return jsonify({"error": "未提供管理后台密钥"}), 401
            if not hmac.compare_digest(token, self._admin_secret):
                logger.warning("管理后台密钥验证失败")
                return jsonify({"error": "无效的管理后台密钥"}), 403
            return None

        @self.app.route("/api/health", methods=["GET"])
        def health_check():
            """健康检查"""
            return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

        @self.app.route("/api/licenses", methods=["GET"])
        def list_licenses():
            """获取所有许可证列表"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                # 这里需要实现获取所有许可证的逻辑
                # 暂时返回空列表
                return jsonify({"licenses": [], "total": 0})
            except Exception as e:
                logger.error(f"获取许可证列表失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>", methods=["GET"])
        def get_license(license_key):
            """获取许可证详情"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                license_obj = self.license_manager.load_license()

                if not license_obj or license_obj.license_key != license_key:
                    return jsonify({"error": "许可证不存在"}), 404

                info = self.license_manager.get_license_info(license_obj)
                return jsonify({"license": info})

            except Exception as e:
                logger.error(f"获取许可证详情失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>/validate", methods=["POST"])
        def validate_license(license_key):
            """验证许可证"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                license_obj = self.license_manager.load_license()

                if not license_obj or license_obj.license_key != license_key:
                    return jsonify({"error": "许可证不存在"}), 404

                report = self.validator.validate(license_obj)

                return jsonify(
                    {
                        "result": report.result.value,
                        "message": report.message,
                        "timestamp": report.timestamp.isoformat(),
                        "license_info": report.license_info,
                        "device_info": (
                            {
                                "device_id": report.device_fingerprint.device_id,
                                "hostname": report.device_fingerprint.hostname,
                                "mac_address": report.device_fingerprint.mac_address,
                            }
                            if report.device_fingerprint
                            else None
                        ),
                    }
                )

            except Exception as e:
                logger.error(f"验证许可证失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>/revoke", methods=["POST"])
        def revoke_license(license_key):
            """撤销许可证"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                success = self.license_manager.revoke_license(license_key)

                if success:
                    return jsonify(
                        {"message": "许可证已撤销", "license_key": license_key}
                    )
                else:
                    return jsonify({"error": "撤销失败"}), 500

            except Exception as e:
                logger.error(f"撤销许可证失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/devices", methods=["GET"])
        def list_devices():
            """获取所有设备列表"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                # 获取所有授权历史
                history = self.device_auth_manager._load_auth_history()

                # 按设备分组
                devices: dict[str, dict] = {}
                for record in history:
                    device_id = record.get("device_id")
                    if device_id not in devices:
                        devices[device_id] = {
                            "device_id": device_id,
                            "hostname": record.get("hostname"),
                            "mac_address": record.get("mac_address"),
                            "first_seen": record.get("timestamp"),
                            "last_seen": record.get("timestamp"),
                            "total_attempts": 0,
                            "licenses": set(),
                            "is_blocked": self.device_auth_manager._is_device_blocked(
                                device_id
                            ),
                        }

                    devices[device_id]["last_seen"] = record.get("timestamp")
                    devices[device_id]["total_attempts"] += 1
                    devices[device_id]["licenses"].add(record.get("license_key"))

                # 转换为列表
                device_list = []
                for device in devices.values():
                    device["licenses"] = list(device["licenses"])
                    device_list.append(device)

                return jsonify({"devices": device_list, "total": len(device_list)})

            except Exception as e:
                logger.error(f"获取设备列表失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/devices/<device_id>", methods=["GET"])
        def get_device(device_id):
            """获取设备详情"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                history = self.device_auth_manager._load_auth_history()

                device_records = [r for r in history if r.get("device_id") == device_id]

                if not device_records:
                    return jsonify({"error": "设备不存在"}), 404

                # 统计信息
                device_info = {
                    "device_id": device_id,
                    "hostname": device_records[0].get("hostname"),
                    "mac_address": device_records[0].get("mac_address"),
                    "first_seen": device_records[0].get("timestamp"),
                    "last_seen": device_records[-1].get("timestamp"),
                    "total_attempts": len(device_records),
                    "successful_attempts": sum(
                        1 for r in device_records if r.get("success")
                    ),
                    "failed_attempts": sum(
                        1 for r in device_records if not r.get("success")
                    ),
                    "licenses_used": list(
                        {r.get("license_key") for r in device_records}
                    ),
                    "is_blocked": self.device_auth_manager._is_device_blocked(
                        device_id
                    ),
                    "recent_activities": device_records[-20:],  # 最近20条活动
                }

                return jsonify({"device": device_info})

            except Exception as e:
                logger.error(f"获取设备详情失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/devices/<device_id>/block", methods=["POST"])
        def block_device(device_id):
            """封控设备"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                data = request.get_json() or {}
                reason = data.get("reason", "管理员手动封控")

                success = self.device_auth_manager.block_device(device_id, reason)

                if success:
                    return jsonify(
                        {
                            "message": "设备已封控",
                            "device_id": device_id,
                            "reason": reason,
                        }
                    )
                else:
                    return jsonify({"error": "封控失败"}), 500

            except Exception as e:
                logger.error(f"封控设备失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/devices/<device_id>/unblock", methods=["POST"])
        def unblock_device(device_id):
            """解除设备封控"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                success = self.device_auth_manager.unblock_device(device_id)

                if success:
                    return jsonify(
                        {"message": "设备已解除封控", "device_id": device_id}
                    )
                else:
                    return jsonify({"error": "该设备未被封控"}), 400

            except Exception as e:
                logger.error(f"解除封控失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>/usage", methods=["GET"])
        def get_license_usage(license_key):
            """获取许可证使用统计"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                stats = self.device_auth_manager.get_device_usage_stats(license_key)
                return jsonify({"usage": stats})

            except Exception as e:
                logger.error(f"获取使用统计失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>/report", methods=["GET"])
        def get_usage_report(license_key):
            """获取许可证使用报告"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                report = self.monitor.get_usage_report(license_key)
                return jsonify({"report": report})

            except Exception as e:
                logger.error(f"获取使用报告失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/licenses/<license_key>/anomalies", methods=["GET"])
        def detect_anomalies(license_key):
            """检测异常行为"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                anomalies = self.monitor.detect_anomalies(license_key)
                return jsonify({"anomalies": anomalies, "total": len(anomalies)})

            except Exception as e:
                logger.error(f"检测异常失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/dashboard/stats", methods=["GET"])
        def get_dashboard_stats():
            """获取仪表板统计数据"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                # 获取所有设备
                history = self.device_auth_manager._load_auth_history()

                devices = {r.get("device_id") for r in history if r.get("device_id")}
                licenses = {
                    r.get("license_key") for r in history if r.get("license_key")
                }

                blocked_devices = [
                    d for d in devices if self.device_auth_manager._is_device_blocked(d)
                ]

                # 统计最近24小时的活动
                from datetime import timedelta

                now = datetime.now()
                recent_cutoff = (now - timedelta(hours=24)).isoformat()
                recent_activities = [
                    r for r in history if r.get("timestamp", "") > recent_cutoff
                ]

                stats = {
                    "total_licenses": len(licenses),
                    "total_devices": len(devices),
                    "blocked_devices": len(blocked_devices),
                    "recent_activities": len(recent_activities),
                    "total_auth_attempts": len(history),
                    "successful_attempts": sum(1 for r in history if r.get("success")),
                    "failed_attempts": sum(1 for r in history if not r.get("success")),
                }

                return jsonify({"stats": stats})

            except Exception as e:
                logger.error(f"获取统计数据失败: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/activities", methods=["GET"])
        def get_activities():
            """获取最近活动"""
            unauthorized = _auth_guard()
            if unauthorized:
                return unauthorized
            try:
                limit = request.args.get("limit", 100, type=int)
                license_key = request.args.get("license_key")
                device_id = request.args.get("device_id")

                history = self.device_auth_manager._load_auth_history()

                # 过滤
                if license_key:
                    history = [
                        r for r in history if r.get("license_key") == license_key
                    ]
                if device_id:
                    history = [r for r in history if r.get("device_id") == device_id]

                # 限制数量
                activities = history[-limit:]

                return jsonify({"activities": activities, "total": len(activities)})

            except Exception as e:
                logger.error(f"获取活动记录失败: {e}")
                return jsonify({"error": str(e)}), 500

    def run(self, debug: bool = False):
        """运行API服务器

        Args:
            debug: 是否启用调试模式
        """
        logger.info(f"启动管理后台API服务器: http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)


def create_admin_api(
    license_file: Path,
    secret_key: str,
    host: str = "127.0.0.1",
    port: int = 5000,
    admin_secret: str | None = None,
) -> AdminAPI:
    """创建管理后台API实例

    Args:
        license_file: 许可证文件路径
        secret_key: 许可证密钥
        admin_secret: 管理后台密钥（Flask SECRET_KEY）
        host: 主机地址
        port: 端口

    Returns:
        AdminAPI实例
    """
    license_manager = LicenseManager(secret_key, license_file)
    device_auth_manager = DeviceAuthManager()

    return AdminAPI(
        license_manager=license_manager,
        device_auth_manager=device_auth_manager,
        admin_secret=admin_secret,
        host=host,
        port=port,
    )
