#!/usr/bin/env python3
"""
系统健康与兼容性检查工具
检查系统是否满足运行要求，生成详细的健康报告
"""

import json
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@dataclass
class CheckResult:
    """检查结果"""

    name: str
    status: str  # "pass", "warning", "fail"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class HealthReport:
    """健康报告"""

    timestamp: str
    overall_status: str
    checks: list[CheckResult]
    system_info: dict[str, Any]
    compatibility_score: float


class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.results: list[CheckResult] = []
        self.config_dir = PROJECT_ROOT / "config"

        # 加载配置
        self.sla_config = self._load_config("sla_config.json")
        self.compat_config = self._load_config("compatibility_config.json")
        self.perf_config = self._load_config("performance.json")

    def _load_config(self, filename: str) -> dict:
        """加载配置文件"""
        try:
            config_path = self.config_dir / filename
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  无法加载配置文件 {filename}: {e}")
        return {}

    def check_platform_compatibility(self) -> CheckResult:
        """检查平台兼容性"""
        system = platform.system()
        version = platform.version()
        machine = platform.machine()

        compat_platforms = (
            self.compat_config.get("compatibility", {})
            .get("platform_support", {})
            .get("operating_systems", {})
        )

        status = "pass"
        message = f"运行在 {system} {version} ({machine})"
        details = {
            "system": system,
            "version": version,
            "machine": machine,
            "python_version": platform.python_version(),
        }
        recommendations = []

        # 检查操作系统支持
        if system == "Windows":
            win_version = platform.win32_ver()[0]
            supported = compat_platforms.get("windows", {}).get("supported_versions", [])
            if win_version not in supported:
                status = "warning"
                recommendations.append(f"推荐使用 Windows {', '.join(supported)}")

        elif system == "Linux":
            # 检查Linux发行版
            try:
                import distro

                dist_name = distro.id()
                dist_version = distro.version()
                details["distribution"] = f"{dist_name} {dist_version}"
            except ImportError:
                details["distribution"] = "Unknown"

        elif system == "Darwin":
            mac_version = platform.mac_ver()[0]
            details["macos_version"] = mac_version
            supported = compat_platforms.get("macos", {}).get("supported_versions", [])
            major_version = mac_version.split(".")[0]
            if major_version not in supported:
                status = "warning"
                recommendations.append(f"推荐使用 macOS {', '.join(supported)}")

        return CheckResult(
            name="平台兼容性",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_python_version(self) -> CheckResult:
        """检查Python版本"""
        current_version = sys.version_info
        version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"

        python_compat = self.compat_config.get("compatibility", {}).get("python_compatibility", {})
        supported_versions = python_compat.get("supported_versions", [])
        min_version = python_compat.get("minimum_version", "3.10.0")

        status = "pass"
        message = f"Python {version_str}"
        recommendations = []

        # 检查版本
        version_tuple = f"{current_version.major}.{current_version.minor}"
        if supported_versions and version_tuple not in supported_versions:
            status = "warning"
            message += f" (推荐: {', '.join(supported_versions)})"
            recommendations.append(f"建议升级到 Python {supported_versions[-1]}")

        if min_version:
            min_parts = min_version.split(".")
            if len(min_parts) >= 3 and current_version < (
                int(min_parts[0]),
                int(min_parts[1]),
                int(min_parts[2]),
            ):
                status = "fail"
                message = f"Python 版本过低 ({version_str} < {min_version})"
                recommendations.append(f"必须升级到 Python {min_version} 或更高版本")

        return CheckResult(
            name="Python版本",
            status=status,
            message=message,
            details={"version": version_str, "required": min_version},
            recommendations=recommendations,
        )

    def check_dependencies(self) -> CheckResult:
        """检查依赖包"""
        required_packages = {
            "PySide6": "6.6.0",
            "numpy": "1.24.0",
            "pydantic": "2.5.0",
            "yaml": "6.0.0",
        }

        optional_packages = {
            "matplotlib": "3.7.0",
            "reportlab": "4.0.0",
            "psutil": "5.9.0",
            "redis": "4.5.0",
        }

        missing = []
        outdated = []
        optional_missing = []

        # 检查必需包
        for package, min_version in required_packages.items():
            try:
                if package == "yaml":
                    import yaml

                    pkg = yaml
                else:
                    pkg = __import__(package)

                # 检查版本
                if hasattr(pkg, "__version__"):
                    version = pkg.__version__
                    if self._compare_versions(version, min_version) < 0:
                        outdated.append(f"{package} (当前: {version}, 需要: {min_version})")
            except ImportError:
                missing.append(f"{package}>={min_version}")

        # 检查可选包
        for package, min_version in optional_packages.items():
            try:
                __import__(package)
            except ImportError:
                optional_missing.append(f"{package}>={min_version}")

        # 确定状态
        if missing:
            status = "fail"
            message = f"缺少 {len(missing)} 个必需依赖"
        elif outdated:
            status = "warning"
            message = f"{len(outdated)} 个依赖版本过低"
        else:
            status = "pass"
            message = "所有必需依赖已安装"

        recommendations = []
        if missing:
            recommendations.append(f"运行: pip install {' '.join(missing)}")
        if outdated:
            recommendations.append(
                f"运行: pip install --upgrade {' '.join([p.split()[0] for p in outdated])}"
            )
        if optional_missing:
            recommendations.append(f"可选依赖: pip install {' '.join(optional_missing)}")

        return CheckResult(
            name="依赖包检查",
            status=status,
            message=message,
            details={
                "missing": missing,
                "outdated": outdated,
                "optional_missing": optional_missing,
            },
            recommendations=recommendations,
        )

    def check_hardware_resources(self) -> CheckResult:
        """检查硬件资源"""
        try:
            import psutil

            # CPU信息
            cpu_count = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存信息
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            memory_available_gb = memory.available / (1024**3)

            # 磁盘信息
            disk = psutil.disk_usage("/")
            disk_total_gb = disk.total / (1024**3)
            disk_free_gb = disk.free / (1024**3)

            details = {
                "cpu_cores": cpu_count,
                "cpu_frequency_ghz": round(cpu_freq.current / 1000, 2) if cpu_freq else 0,
                "cpu_usage_percent": cpu_percent,
                "memory_total_gb": round(memory_gb, 2),
                "memory_available_gb": round(memory_available_gb, 2),
                "memory_usage_percent": memory.percent,
                "disk_total_gb": round(disk_total_gb, 2),
                "disk_free_gb": round(disk_free_gb, 2),
                "disk_usage_percent": disk.percent,
            }

            # 获取最低要求
            hw_req = (
                self.compat_config.get("compatibility", {})
                .get("platform_support", {})
                .get("hardware_requirements", {})
            )

            min_req = hw_req.get("minimum", {})
            rec_req = hw_req.get("recommended", {})

            status = "pass"
            recommendations = []

            # 检查CPU
            if cpu_count < min_req.get("cpu_cores", 2):
                status = "warning"
                recommendations.append(f"CPU核心数不足 (最低: {min_req['cpu_cores']}核)")
            elif cpu_count < rec_req.get("cpu_cores", 4):
                recommendations.append(f"建议使用 {rec_req['cpu_cores']}核或更多CPU")

            # 检查内存
            if memory_gb < min_req.get("ram_gb", 4):
                status = "fail"
                recommendations.append(f"内存不足 (最低: {min_req['ram_gb']}GB)")
            elif memory_gb < rec_req.get("ram_gb", 8):
                status = "warning" if status == "pass" else status
                recommendations.append(f"建议使用 {rec_req['ram_gb']}GB或更多内存")

            # 检查磁盘
            if disk_free_gb < min_req.get("storage_gb", 10):
                status = "fail"
                recommendations.append(f"磁盘空间不足 (最低: {min_req['storage_gb']}GB)")

            message = f"CPU: {cpu_count}核, 内存: {memory_gb:.1f}GB, 磁盘: {disk_free_gb:.1f}GB可用"

        except ImportError:
            status = "warning"
            message = "无法检查硬件资源 (需要 psutil)"
            details = {}
            recommendations = ["安装 psutil: pip install psutil"]

        return CheckResult(
            name="硬件资源",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_performance_targets(self) -> CheckResult:
        """检查性能目标可达性"""
        try:
            import psutil

            # 获取当前资源使用
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # 获取性能目标
            perf_targets = self.perf_config.get("performance_targets", {})
            resource_usage = perf_targets.get("resource_usage", {})

            max_cpu = resource_usage.get("max_cpu", 70)
            max_memory_mb = resource_usage.get("max_memory_mb", 512)

            status = "pass"
            message = "性能目标可达"
            recommendations = []

            # 检查CPU余量
            cpu_headroom = 100 - cpu_percent
            if cpu_headroom < max_cpu:
                status = "warning"
                recommendations.append(f"当前CPU使用率较高 ({cpu_percent}%), 可能影响性能")

            # 检查内存余量
            memory_available_mb = memory.available / (1024**2)
            if memory_available_mb < max_memory_mb * 2:
                status = "warning"
                recommendations.append(
                    f"可用内存较少 ({memory_available_mb:.0f}MB), 建议关闭其他应用"
                )

            details = {
                "current_cpu_percent": cpu_percent,
                "target_max_cpu_percent": max_cpu,
                "available_memory_mb": round(memory_available_mb, 2),
                "target_memory_mb": max_memory_mb,
                "cpu_headroom_percent": round(cpu_headroom, 2),
            }

        except ImportError:
            status = "warning"
            message = "无法评估性能目标"
            details = {}
            recommendations = ["安装 psutil 以进行性能检查"]

        return CheckResult(
            name="性能目标",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_sla_compliance(self) -> CheckResult:
        """检查SLA合规性"""
        sla = self.sla_config.get("sla", {})

        availability_target = sla.get("availability", {}).get("target_uptime_percentage", 99.5)

        # 检查监控配置
        monitoring_req = sla.get("monitoring_requirements", {})
        health_check_config = monitoring_req.get("health_checks", {})

        status = "pass"
        message = f"SLA目标: {availability_target}% 可用性"
        recommendations = []

        # 检查是否启用了监控
        try:
            monitoring_config_path = self.config_dir / "monitoring_config.json"
            if monitoring_config_path.exists():
                with open(monitoring_config_path, encoding="utf-8") as f:
                    monitoring_config = json.load(f)

                monitoring_enabled = monitoring_config.get("monitoring", {}).get("enabled", False)
                if not monitoring_enabled:
                    status = "warning"
                    recommendations.append("建议启用监控系统以确保SLA合规")
            else:
                status = "warning"
                recommendations.append("未找到监控配置文件")
        except Exception:
            pass

        details = {
            "target_uptime_percent": availability_target,
            "health_check_interval_seconds": health_check_config.get("interval_seconds", 60),
            "alerting_enabled": monitoring_req.get("alerting", {}).get("enabled", False),
        }

        return CheckResult(
            name="SLA合规性",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_scalability_config(self) -> CheckResult:
        """检查伸缩性配置"""
        try:
            scalability_config_path = self.config_dir / "scalability_config.json"
            if not scalability_config_path.exists():
                return CheckResult(
                    name="伸缩性配置",
                    status="warning",
                    message="未找到伸缩性配置文件",
                    details={},
                    recommendations=["创建 config/scalability_config.json"],
                )

            with open(scalability_config_path, encoding="utf-8") as f:
                scalability_config = json.load(f)

            scaling = scalability_config.get("scalability", {})
            auto_scaling = scaling.get("scaling_strategy", {}).get("auto_scaling", {})

            status = "pass"
            message = "伸缩性配置完整"
            recommendations = []

            if not auto_scaling.get("enabled", False):
                status = "warning"
                recommendations.append("考虑启用自动伸缩以应对负载变化")

            # 检查缓存配置
            caching = scaling.get("caching_strategy", {})
            if not caching.get("multi_level", {}).get("enabled", False):
                recommendations.append("建议启用多级缓存以提升性能")

            # 检查限流配置
            rate_limiting = scaling.get("rate_limiting", {})
            if not rate_limiting.get("enabled", False):
                status = "warning"
                recommendations.append("建议启用限流以防止过载")

            details = {
                "auto_scaling_enabled": auto_scaling.get("enabled", False),
                "caching_enabled": caching.get("multi_level", {}).get("enabled", False),
                "rate_limiting_enabled": rate_limiting.get("enabled", False),
            }

        except Exception as e:
            return CheckResult(
                name="伸缩性配置",
                status="fail",
                message=f"配置检查失败: {str(e)}",
                details={},
                recommendations=["检查伸缩性配置文件格式"],
            )

        return CheckResult(
            name="伸缩性配置",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_ui_compatibility(self) -> CheckResult:
        """检查UI兼容性"""
        try:
            from PySide6.QtCore import QT_VERSION_STR
            from PySide6.QtWidgets import QApplication

            # 获取屏幕信息
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            screen = app.primaryScreen()
            geometry = screen.geometry()
            dpi = screen.logicalDotsPerInch()

            width = geometry.width()
            height = geometry.height()

            # 获取UI兼容性配置
            ui_compat = self.compat_config.get("compatibility", {}).get("ui_compatibility", {})
            display_config = ui_compat.get("display", {})

            min_resolution = display_config.get("minimum_resolution", "1024x768")
            min_w, min_h = map(int, min_resolution.split("x"))

            status = "pass"
            message = f"屏幕: {width}x{height} @ {dpi:.0f} DPI, Qt {QT_VERSION_STR}"
            recommendations = []

            if width < min_w or height < min_h:
                status = "warning"
                recommendations.append(f"屏幕分辨率低于推荐值 ({min_resolution})")

            # 检查DPI缩放
            dpi_scaling = display_config.get("dpi_scaling", {})
            if dpi_scaling.get("supported", False):
                scale = int(dpi / 96 * 100)
                tested_scales = dpi_scaling.get("tested_scales", [])
                if scale not in tested_scales:
                    status = "warning" if status == "pass" else status
                    recommendations.append(f"DPI缩放 {scale}% 未经充分测试")

            details = {
                "resolution": f"{width}x{height}",
                "dpi": round(dpi, 2),
                "qt_version": QT_VERSION_STR,
                "meets_minimum": width >= min_w and height >= min_h,
            }

        except ImportError:
            status = "fail"
            message = "无法检查UI兼容性 (PySide6未安装)"
            details = {}
            recommendations = ["安装 PySide6: pip install PySide6>=6.6.0"]
        except Exception as e:
            status = "warning"
            message = f"UI检查部分失败: {str(e)}"
            details = {}
            recommendations = []

        return CheckResult(
            name="UI兼容性",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def check_network_connectivity(self) -> CheckResult:
        """检查网络连通性"""
        import socket

        status = "pass"
        message = "网络连接正常"
        recommendations = []

        # 检查本地网络
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            details = {"hostname": hostname, "local_ip": local_ip}
        except Exception:
            status = "warning"
            message = "无法获取本地网络信息"
            details = {}

        # 检查Internet连接 (可选)
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            details["internet"] = "connected"
        except OSError:
            details["internet"] = "disconnected"
            recommendations.append("无Internet连接 (离线模式)")

        return CheckResult(
            name="网络连通性",
            status=status,
            message=message,
            details=details,
            recommendations=recommendations,
        )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号"""

        def normalize(v):
            return [int(x) for x in v.split(".")]

        try:
            parts1 = normalize(v1)
            parts2 = normalize(v2)

            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except Exception:
            return 0

    def run_all_checks(self) -> HealthReport:
        """运行所有检查"""
        print("\n" + "=" * 70)
        print("🔍 VirtualChemLab 系统健康与兼容性检查")
        print("=" * 70 + "\n")

        # 运行所有检查
        checks = [
            self.check_platform_compatibility(),
            self.check_python_version(),
            self.check_dependencies(),
            self.check_hardware_resources(),
            self.check_performance_targets(),
            self.check_sla_compliance(),
            self.check_scalability_config(),
            self.check_ui_compatibility(),
            self.check_network_connectivity(),
        ]

        self.results = checks

        # 计算总体状态
        fail_count = sum(1 for r in checks if r.status == "fail")
        warning_count = sum(1 for r in checks if r.status == "warning")
        pass_count = sum(1 for r in checks if r.status == "pass")

        if fail_count > 0:
            overall_status = "fail"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "pass"

        # 计算兼容性得分
        total_checks = len(checks)
        compatibility_score = (pass_count + warning_count * 0.5) / total_checks * 100

        # 获取系统信息
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.machine(),
            "timestamp": datetime.now().isoformat(),
        }

        report = HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            checks=checks,
            system_info=system_info,
            compatibility_score=compatibility_score,
        )

        return report

    def print_report(self, report: HealthReport):
        """打印报告"""
        # 打印检查结果
        for check in report.checks:
            icon = {"pass": "✅", "warning": "⚠️ ", "fail": "❌"}.get(check.status, "❓")

            print(f"{icon} {check.name}: {check.message}")

            if check.details:
                for key, value in check.details.items():
                    print(f"   - {key}: {value}")

            if check.recommendations:
                for rec in check.recommendations:
                    print(f"   💡 {rec}")
            print()

        # 打印总结
        print("=" * 70)
        print("📊 检查总结")
        print("=" * 70)
        print(f"总体状态: {report.overall_status.upper()}")
        print(f"兼容性得分: {report.compatibility_score:.1f}/100")
        print(f"检查时间: {report.timestamp}")

        pass_count = sum(1 for c in report.checks if c.status == "pass")
        warning_count = sum(1 for c in report.checks if c.status == "warning")
        fail_count = sum(1 for c in report.checks if c.status == "fail")

        print(f"\n✅ 通过: {pass_count}")
        print(f"⚠️  警告: {warning_count}")
        print(f"❌ 失败: {fail_count}")
        print("=" * 70 + "\n")

    def save_report(self, report: HealthReport, filepath: Path):
        """保存报告到JSON文件"""
        report_data = {
            "timestamp": report.timestamp,
            "overall_status": report.overall_status,
            "compatibility_score": report.compatibility_score,
            "system_info": report.system_info,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                    "details": check.details,
                    "recommendations": check.recommendations,
                }
                for check in report.checks
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"📄 详细报告已保存到: {filepath}")


def main():
    """主函数"""
    # 设置UTF-8输出
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    checker = SystemHealthChecker()
    report = checker.run_all_checks()
    checker.print_report(report)

    # 保存报告
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"system_health_{timestamp}.json"
    checker.save_report(report, report_file)

    # 返回退出码
    return 0 if report.overall_status != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
