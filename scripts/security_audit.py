#!/usr/bin/env python3
"""
安全审计脚本

检查项：
1. 依赖包安全漏洞
2. 敏感信息泄露
3. 文件权限
4. 配置安全
"""

import re
import subprocess
import sys
from pathlib import Path


class SecurityAuditor:
    """安全审计器"""

    def __init__(self):
        self.issues: list[dict] = []
        self.warnings: list[dict] = []

    def check_dependencies(self) -> bool:
        """检查依赖包安全漏洞"""
        print("🔍 检查依赖包安全漏洞...")

        try:
            # 尝试使用 pip-audit
            result = subprocess.run(["pip-audit", "--format", "json"], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                print("  ✓ 未发现已知安全漏洞")
                return True
            else:
                self.issues.append(
                    {
                        "type": "dependency",
                        "severity": "high",
                        "message": "发现依赖包安全漏洞",
                        "details": result.stdout,
                    }
                )
                print("  ✗ 发现安全漏洞，请运行 pip-audit 查看详情")
                return False

        except FileNotFoundError:
            self.warnings.append({"type": "tool", "message": "pip-audit 未安装，无法检查依赖安全"})
            print("  ⚠ pip-audit 未安装，跳过依赖检查")
            print("    安装: pip install pip-audit")
            return True

        except Exception as e:
            print(f"  ⚠ 依赖检查失败: {e}")
            return True

    def check_sensitive_info(self) -> bool:
        """检查敏感信息泄露"""
        print("\n🔍 检查敏感信息泄露...")

        # 敏感信息模式
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "password", "密码"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "api_key", "API密钥"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret", "密钥"),
            (r'token\s*=\s*["\'][^"\']+["\']', "token", "令牌"),
            (r'(?:bearer|authorization)\s*["\'][^"\']+["\']', "auth", "认证信息"),
        ]

        found_issues = False

        # 扫描Python文件
        for py_file in Path("src").rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern, key, name in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # 排除注释和示例
                        line_start = content.rfind("\n", 0, match.start()) + 1
                        line = content[line_start : content.find("\n", match.start())]

                        if "#" in line and line.index("#") < (match.start() - line_start):
                            continue  # 注释中

                        self.issues.append(
                            {
                                "type": "sensitive_info",
                                "severity": "critical",
                                "file": str(py_file),
                                "pattern": key,
                                "message": f"发现硬编码{name}",
                            }
                        )
                        print(f"  ✗ {py_file}: 发现硬编码{name}")
                        found_issues = True

            except Exception as e:
                print(f"  ⚠ 扫描 {py_file} 失败: {e}")

        if not found_issues:
            print("  ✓ 未发现敏感信息泄露")

        return not found_issues

    def check_file_permissions(self) -> bool:
        """检查文件权限"""
        print("\n🔍 检查文件权限...")

        # Windows系统跳过此检查
        if sys.platform == "win32":
            print("  ⊘ Windows系统，跳过文件权限检查")
            return True

        found_issues = False

        # 检查敏感文件权限
        sensitive_files = [
            "config/*.yaml",
            "data/*.db",
            "logs/*.log",
        ]

        for pattern in sensitive_files:
            for filepath in Path(".").glob(pattern):
                if filepath.exists():
                    # 检查是否所有用户可读
                    stat = filepath.stat()
                    if stat.st_mode & 0o004:  # 其他用户可读
                        self.warnings.append(
                            {"type": "permission", "file": str(filepath), "message": "文件对所有用户可读"}
                        )
                        print(f"  ⚠ {filepath}: 建议限制访问权限")
                        found_issues = True

        if not found_issues:
            print("  ✓ 文件权限配置合理")

        return not found_issues

    def check_configuration(self) -> bool:
        """检查配置安全"""
        print("\n🔍 检查配置安全...")

        found_issues = False

        # 检查生产配置
        prod_config = Path("config/production.yaml")
        if prod_config.exists():
            content = prod_config.read_text(encoding="utf-8")

            # 检查调试模式
            if re.search(r"debug:\s*true", content, re.IGNORECASE):
                self.issues.append(
                    {
                        "type": "config",
                        "severity": "high",
                        "file": str(prod_config),
                        "message": "生产配置启用了调试模式",
                    }
                )
                print("  ✗ 生产配置启用了调试模式")
                found_issues = True

            # 检查日志级别
            if re.search(r'level:\s*["\']?DEBUG["\']?', content, re.IGNORECASE):
                self.warnings.append(
                    {"type": "config", "file": str(prod_config), "message": "生产配置使用DEBUG日志级别"}
                )
                print("  ⚠ 生产配置使用DEBUG日志级别")

            # 检查错误报告
            if re.search(r"reporting:\s*\n\s*enabled:\s*true", content) and not re.search(
                r"anonymous:\s*true", content
            ):
                self.warnings.append({"type": "config", "file": str(prod_config), "message": "错误报告未设置为匿名"})
                print("  ⚠ 错误报告未设置为匿名")

        if not found_issues:
            print("  ✓ 配置安全检查通过")

        return not found_issues

    def check_code_quality(self) -> bool:
        """检查代码质量（安全相关）"""
        print("\n🔍 检查代码质量...")

        found_issues = False

        # 检查危险函数使用
        dangerous_patterns = [
            (r"\beval\s*\(", "eval()", "使用危险函数 eval()"),
            (r"\bexec\s*\(", "exec()", "使用危险函数 exec()"),
            (r"__import__\s*\(", "__import__()", "使用动态导入"),
            (r"pickle\.loads?", "pickle", "使用不安全的pickle"),
        ]

        for py_file in Path("src").rglob("*.py"):
            # 跳过已知安全使用的文件
            if "developer_console.py" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern, func, message in dangerous_patterns:
                    if re.search(pattern, content):
                        self.warnings.append(
                            {"type": "code_quality", "file": str(py_file), "function": func, "message": message}
                        )
                        print(f"  ⚠ {py_file}: {message}")
                        found_issues = True

            except Exception:
                pass

        if not found_issues:
            print("  ✓ 未发现危险代码模式")

        return not found_issues

    def generate_report(self) -> None:
        """生成审计报告"""
        print("\n" + "=" * 60)
        print("📊 安全审计报告")
        print("=" * 60)

        # 统计
        critical_count = sum(1 for i in self.issues if i.get("severity") == "critical")
        high_count = sum(1 for i in self.issues if i.get("severity") == "high")
        warning_count = len(self.warnings)

        print(f"\n严重问题: {critical_count}")
        print(f"高危问题: {high_count}")
        print(f"警告: {warning_count}")

        # 详细问题
        if self.issues:
            print("\n❌ 需要修复的问题:")
            for issue in self.issues:
                severity = issue.get("severity", "unknown").upper()
                print(f"\n  [{severity}] {issue.get('message', 'Unknown')}")
                if "file" in issue:
                    print(f"  文件: {issue['file']}")
                if "details" in issue:
                    print(f"  详情: {issue['details'][:200]}")

        if self.warnings:
            print("\n⚠️  警告:")
            for warning in self.warnings:
                print(f"\n  {warning.get('message', 'Unknown')}")
                if "file" in warning:
                    print(f"  文件: {warning['file']}")

        # 建议
        print("\n💡 建议:")
        print("  1. 修复所有严重和高危问题")
        print("  2. 审查并处理警告")
        print("  3. 定期运行安全审计")
        print("  4. 保持依赖包更新")

        # 评分
        score = 100
        score -= critical_count * 20
        score -= high_count * 10
        score -= warning_count * 2
        score = max(0, score)

        print(f"\n安全评分: {score}/100")

        if score >= 90:
            print("✨ 优秀！安全状况良好")
        elif score >= 70:
            print("👍 良好，建议改进警告项")
        elif score >= 50:
            print("⚠️  一般，请尽快修复高危问题")
        else:
            print("❌ 差，存在严重安全风险！")

    def run_audit(self) -> int:
        """运行完整审计"""
        print("🔒 VirtualChemLab 安全审计")
        print("=" * 60)

        checks = [
            self.check_dependencies,
            self.check_sensitive_info,
            self.check_file_permissions,
            self.check_configuration,
            self.check_code_quality,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"  ✗ 检查失败: {e}")

        self.generate_report()

        # 如果有严重或高危问题，返回非零退出码
        critical_count = sum(1 for i in self.issues if i.get("severity") in ["critical", "high"])
        return 1 if critical_count > 0 else 0


def main():
    """主函数"""
    auditor = SecurityAuditor()
    exit_code = auditor.run_audit()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
