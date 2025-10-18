"""
后端代码健康检查工具

自动化检查后端代码的健壮性、完整性和潜在问题
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HealthIssue:
    """健康问题"""

    severity: str  # critical, warning, info
    category: str
    file: str
    line: int
    message: str
    suggestion: str = ""


@dataclass
class HealthReport:
    """健康报告"""

    timestamp: datetime = field(default_factory=datetime.now)
    total_files: int = 0
    issues: list[HealthIssue] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)

    def add_issue(self, severity: str, category: str, file: str, line: int, message: str, suggestion: str = ""):
        """添加问题"""
        self.issues.append(HealthIssue(severity, category, file, line, message, suggestion))

    def get_critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    def get_warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def calculate_scores(self):
        """计算健康分数"""
        critical = self.get_critical_count()
        warnings = self.get_warning_count()

        # 基础分 100, 每个严重问题扣10分, 每个警告扣2分
        security_score = max(0, 100 - critical * 10 - warnings * 2)

        self.scores = {
            "总体评分": security_score,
            "安全性": security_score,
            "可维护性": 100 - len([i for i in self.issues if i.category == "maintainability"]) * 5,
            "性能": 100 - len([i for i in self.issues if i.category == "performance"]) * 3,
        }

        for key in self.scores:
            self.scores[key] = max(0, min(100, self.scores[key]))


class BackendHealthChecker:
    """后端健康检查器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.report = HealthReport()

    def check_all(self):
        """执行所有检查"""
        logger.info("开始后端健康检查...")

        # 检查Python文件
        py_files = list(self.src_dir.rglob("*.py"))
        self.report.total_files = len(py_files)

        logger.info(f"找到 {len(py_files)} 个Python文件")

        for py_file in py_files:
            self.check_file(py_file)

        # 检查关键配置
        self.check_configurations()

        # 检查中间件集成
        self.check_middleware_integration()

        # 计算分数
        self.report.calculate_scores()

        logger.info("健康检查完成")

    def check_file(self, file_path: Path):
        """检查单个文件"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            try:
                rel_path = str(file_path.relative_to(project_root))
            except ValueError:
                # Windows路径问题,使用绝对路径的basename
                rel_path = str(file_path)

            # 检查TODO/FIXME
            for i, line in enumerate(lines, 1):
                if "TODO" in line or "FIXME" in line:
                    self.report.add_issue(
                        "warning", "completeness", rel_path, i, f"未完成的TODO: {line.strip()}", "完成或移除TODO注释"
                    )

            # 检查异常处理
            if "except Exception as e:" in content and "logger.error" not in content and "logging.error" not in content:
                self.report.add_issue(
                    "warning", "error_handling", rel_path, 0, "捕获异常但未记录日志", "在except块中添加日志记录"
                )

            # 检查密码相关安全
            if "password" in content.lower():
                if "hashlib.md5" in content or "hashlib.sha1" in content:
                    self.report.add_issue(
                        "critical", "security", rel_path, 0, "使用了不安全的MD5/SHA1哈希算法", "使用PBKDF2或bcrypt"
                    )

                if "password ==" in content or "== password" in content:
                    self.report.add_issue(
                        "critical", "security", rel_path, 0, "使用明文密码比较", "使用时间安全的hmac.compare_digest"
                    )

            # 检查SQL注入风险
            if ".execute(" in content and "+" in content and ('f"' in content or "f'" in content):
                self.report.add_issue("critical", "security", rel_path, 0, "可能存在SQL注入风险", "使用参数化查询")

            # 检查硬编码敏感信息
            for i, line in enumerate(lines, 1):
                if (
                    any(keyword in line.lower() for keyword in ["api_key", "secret_key", "password"])
                    and "=" in line
                    and ('"' in line or "'" in line)
                    and "config" not in line.lower()
                    and "env" not in line.lower()
                ):
                    self.report.add_issue(
                        "warning", "security", rel_path, i, "可能存在硬编码的敏感信息", "从配置文件或环境变量读取"
                    )

            # 检查大函数
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    func_end = self.find_function_end(lines, i)
                    func_length = func_end - i
                    if func_length > 100:
                        self.report.add_issue(
                            "warning",
                            "maintainability",
                            rel_path,
                            i + 1,
                            f"函数过长 ({func_length}行)",
                            "考虑拆分为更小的函数",
                        )

        except Exception as e:
            logger.error(f"检查文件失败 {file_path}: {e}")

    def find_function_end(self, lines: list[str], start: int) -> int:
        """查找函数结束位置"""
        indent = len(lines[start]) - len(lines[start].lstrip())

        for i in range(start + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#"):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent:
                    return i

        return len(lines)

    def check_configurations(self):
        """检查配置"""
        config_file = project_root / "config.json"

        if not config_file.exists():
            self.report.add_issue("warning", "configuration", "config.json", 0, "缺少主配置文件", "创建config.json")
        else:
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = json.load(f)

                # 检查必要配置
                if "teacher" not in config or "password_hash" not in config.get("teacher", {}):
                    self.report.add_issue(
                        "warning",
                        "configuration",
                        "config.json",
                        0,
                        "未设置教师密码哈希",
                        "在config.json中配置teacher.password_hash",
                    )

            except Exception as e:
                self.report.add_issue(
                    "warning", "configuration", "config.json", 0, f"配置文件格式错误: {e}", "检查JSON格式"
                )

    def check_middleware_integration(self):
        """检查中间件集成"""
        server_file = self.src_dir / "api" / "server.py"

        if server_file.exists():
            with open(server_file, encoding="utf-8") as f:
                content = f.read()

            # 检查是否导入了中间件
            if "from .middleware import" not in content and "from ..api.middleware import" not in content:
                self.report.add_issue(
                    "critical",
                    "integration",
                    str(server_file.relative_to(project_root)),
                    0,
                    "API服务器未导入中间件",
                    "导入并使用中间件",
                )

            # 检查是否使用了认证
            if "auth_middleware" not in content:
                self.report.add_issue(
                    "warning",
                    "integration",
                    str(server_file.relative_to(project_root)),
                    0,
                    "API服务器未集成认证中间件",
                    "集成AuthMiddleware",
                )

    def generate_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("VirtualChemLab 后端代码健康检查报告")
        lines.append("=" * 80)
        lines.append(f"检查时间: {self.report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"检查文件数: {self.report.total_files}")
        lines.append(f"发现问题数: {len(self.report.issues)}")
        lines.append(f"  - 严重问题: {self.report.get_critical_count()}")
        lines.append(f"  - 警告: {self.report.get_warning_count()}")
        lines.append("")

        # 评分
        lines.append("健康评分:")
        for name, score in self.report.scores.items():
            stars = "★" * (score // 20) + "☆" * (5 - score // 20)
            lines.append(f"  {name}: {score}/100 {stars}")
        lines.append("")

        # 按严重性分组
        critical_issues = [i for i in self.report.issues if i.severity == "critical"]
        warning_issues = [i for i in self.report.issues if i.severity == "warning"]

        if critical_issues:
            lines.append("🔴 严重问题:")
            lines.append("-" * 80)
            for issue in critical_issues:
                lines.append(f"[{issue.category}] {issue.file}:{issue.line}")
                lines.append(f"  问题: {issue.message}")
                lines.append(f"  建议: {issue.suggestion}")
                lines.append("")

        if warning_issues:
            lines.append("⚠️ 警告:")
            lines.append("-" * 80)
            for issue in warning_issues[:20]:  # 只显示前20个
                lines.append(f"[{issue.category}] {issue.file}:{issue.line}")
                lines.append(f"  问题: {issue.message}")
                lines.append(f"  建议: {issue.suggestion}")
                lines.append("")

            if len(warning_issues) > 20:
                lines.append(f"... 还有 {len(warning_issues) - 20} 个警告未显示")
                lines.append("")

        # 总结
        lines.append("=" * 80)
        lines.append("总结:")
        if self.report.scores["总体评分"] >= 90:
            lines.append("✅ 代码质量优秀")
        elif self.report.scores["总体评分"] >= 75:
            lines.append("✅ 代码质量良好,有少量改进空间")
        elif self.report.scores["总体评分"] >= 60:
            lines.append("⚠️ 代码质量中等,需要改进")
        else:
            lines.append("🔴 代码质量较差,需要重点改进")

        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, output_file: str = "后端健康检查报告.txt"):
        """保存报告"""
        report_text = self.generate_report()

        output_path = project_root / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        logger.info(f"报告已保存到: {output_path}")

        # 同时打印到控制台 (Windows兼容)
        try:
            print(report_text)
        except UnicodeEncodeError:
            # Windows控制台编码问题,使用ASCII友好输出
            print(report_text.encode("gbk", errors="replace").decode("gbk"))


def main():
    """主函数"""
    checker = BackendHealthChecker()
    checker.check_all()
    checker.save_report()


if __name__ == "__main__":
    main()
