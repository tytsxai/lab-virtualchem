"""
许可证健康检查工具

用于检查许可证系统的健康状态
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.license_manager import (  # noqa: E402
    LicenseManager,
    LicenseStatus,
    get_machine_id,
)


def _resolve_license_secret() -> str:
    """从环境变量读取许可证密钥，避免硬编码"""
    secret = os.getenv("LICENSE_SECRET_KEY", "").strip()
    if not secret:
        raise ValueError("未设置 LICENSE_SECRET_KEY，禁止使用默认/硬编码密钥")
    if secret.startswith("YOUR_") or len(secret) < 32:
        raise ValueError("LICENSE_SECRET_KEY 长度不足或仍为占位值，请提供>=32位的生产密钥")
    return secret


class HealthCheckResult:
    """健康检查结果"""

    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []

    def add_check(self, name: str, status: str, message: str):
        """添加检查结果"""
        self.checks.append({"name": name, "status": status, "message": message})

        if status == "WARNING":
            self.warnings.append(name)
        elif status == "ERROR":
            self.errors.append(name)

    def is_healthy(self) -> bool:
        """是否健康"""
        return len(self.errors) == 0

    def print_report(self):
        """打印报告"""
        print("\n" + "=" * 80)
        print("VirtualChemLab 许可证健康检查报告")
        print("=" * 80)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 打印检查项
        for check in self.checks:
            status_icon = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(check["status"], "❓")

            print(f"{status_icon} {check['name']}")
            print(f"   {check['message']}")
            print()

        # 总结
        print("=" * 80)
        print(f"总检查项: {len(self.checks)}")
        print(f"通过: {len([c for c in self.checks if c['status'] == 'OK'])}")
        print(f"警告: {len(self.warnings)}")
        print(f"错误: {len(self.errors)}")
        print()

        if self.is_healthy():
            print("✅ 系统健康")
        else:
            print("❌ 系统存在问题,请检查错误项")

        print("=" * 80)


class LicenseHealthChecker:
    """许可证健康检查器"""

    def __init__(self, license_manager: LicenseManager):
        self.license_manager = license_manager
        self.result = HealthCheckResult()

    def run_all_checks(self) -> HealthCheckResult:
        """运行所有检查"""
        self.check_license_file_exists()
        self.check_license_valid()
        self.check_license_expiry()
        self.check_machine_binding()
        self.check_signature()
        self.check_activation()
        self.check_revocation()
        self.check_features()

        return self.result

    def check_license_file_exists(self):
        """检查许可证文件是否存在"""
        if self.license_manager.license_file.exists():
            self.result.add_check("许可证文件", "OK", f"文件存在: {self.license_manager.license_file}")
        else:
            self.result.add_check("许可证文件", "ERROR", f"文件不存在: {self.license_manager.license_file}")

    def check_license_valid(self):
        """检查许可证是否有效"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            self.result.add_check("许可证加载", "ERROR", "无法加载许可证文件")
            return

        self.result.add_check("许可证加载", "OK", f"许可证类型: {license_obj.license_type.value}")

        # 验证许可证
        machine_id = get_machine_id()
        status, error_msg = self.license_manager.validate_license(license_obj, machine_id)

        if status == LicenseStatus.VALID:
            self.result.add_check("许可证状态", "OK", "许可证有效")
        elif status == LicenseStatus.EXPIRED:
            self.result.add_check("许可证状态", "ERROR", f"许可证已过期: {error_msg}")
        elif status == LicenseStatus.NOT_ACTIVATED:
            self.result.add_check("许可证状态", "WARNING", f"许可证未激活: {error_msg}")
        elif status == LicenseStatus.INVALID:
            self.result.add_check("许可证状态", "ERROR", f"许可证无效: {error_msg}")
        elif status == LicenseStatus.REVOKED:
            self.result.add_check("许可证状态", "ERROR", f"许可证已撤销: {error_msg}")

    def check_license_expiry(self):
        """检查许可证过期时间"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        info = self.license_manager.get_license_info(license_obj)
        days_remaining = info["days_remaining"]

        if days_remaining > 90:
            self.result.add_check("许可证有效期", "OK", f"剩余 {days_remaining} 天")
        elif days_remaining > 30:
            self.result.add_check("许可证有效期", "WARNING", f"剩余 {days_remaining} 天,建议准备续费")
        elif days_remaining > 0:
            self.result.add_check("许可证有效期", "WARNING", f"剩余 {days_remaining} 天,请尽快续费!")
        else:
            self.result.add_check("许可证有效期", "ERROR", "许可证已过期")

    def check_machine_binding(self):
        """检查机器绑定"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        current_machine_id = get_machine_id()

        if license_obj.machine_id == current_machine_id:
            self.result.add_check("设备绑定", "OK", f"设备ID匹配: {current_machine_id[:16]}...")
        else:
            self.result.add_check(
                "设备绑定",
                "ERROR",
                f"设备ID不匹配\n   当前: {current_machine_id[:16]}...\n   许可证: {license_obj.machine_id[:16]}...",
            )

    def check_signature(self):
        """检查数字签名"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        if self.license_manager._verify_signature(license_obj):
            self.result.add_check("数字签名", "OK", "签名有效,许可证未被篡改")
        else:
            self.result.add_check("数字签名", "ERROR", "签名无效,许可证可能已被篡改!")

    def check_activation(self):
        """检查激活状态"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        if license_obj.is_activated:
            activated_at = license_obj.activated_at
            if activated_at:
                self.result.add_check("激活状态", "OK", f"已激活 (时间: {activated_at.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                self.result.add_check("激活状态", "WARNING", "已激活但缺少激活时间")
        else:
            self.result.add_check("激活状态", "WARNING", "许可证未激活,请先激活后使用")

    def check_revocation(self):
        """检查撤销状态"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        if license_obj.license_key in self.license_manager._revoked_keys:
            self.result.add_check("撤销检查", "ERROR", "许可证已在撤销列表中")
        else:
            self.result.add_check("撤销检查", "OK", "许可证未被撤销")

    def check_features(self):
        """检查功能列表"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return

        features = license_obj.features

        if features:
            self.result.add_check("功能列表", "OK", f"包含 {len(features)} 个功能: {', '.join(features[:3])}...")
        else:
            self.result.add_check("功能列表", "WARNING", "许可证未配置任何功能")


def main():
    """主函数"""
    print("正在进行许可证健康检查...")

    # 创建许可证管理器
    secret_key = _resolve_license_secret()
    license_file = PROJECT_ROOT / "data" / "license.json"
    license_manager = LicenseManager(secret_key, license_file)

    # 创建健康检查器
    checker = LicenseHealthChecker(license_manager)

    # 运行所有检查
    result = checker.run_all_checks()

    # 打印报告
    result.print_report()

    # 返回退出代码
    sys.exit(0 if result.is_healthy() else 1)


if __name__ == "__main__":
    main()
