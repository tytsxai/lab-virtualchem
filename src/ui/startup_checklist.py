"""
启动检查清单
在应用启动时执行一系列检查，确保系统状态良好
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class CheckStatus(Enum):
    """检查状态"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """检查结果"""

    name: str
    status: CheckStatus
    message: str = ""
    details: str = ""
    suggestions: list[str] | None = None
    critical: bool = False

    def is_ok(self) -> bool:
        """是否通过检查"""
        return self.status in [CheckStatus.PASSED, CheckStatus.WARNING, CheckStatus.SKIPPED]


class StartupChecker:
    """启动检查器"""

    def __init__(self):
        self.checks: list[tuple[str, Callable[[], CheckResult], bool]] = []
        self.results: list[CheckResult] = []

    def add_check(self, name: str, check_func: Callable[[], CheckResult], critical: bool = False):
        """添加检查项

        Args:
            name: 检查项名称
            check_func: 检查函数
            critical: 是否为关键检查（失败则不能继续）
        """
        self.checks.append((name, check_func, critical))

    def run_all_checks(self) -> tuple[bool, list[CheckResult]]:
        """运行所有检查

        Returns:
            (是否全部通过, 检查结果列表)
        """
        self.results.clear()
        all_passed = True

        for name, check_func, critical in self.checks:
            logger.info(f"执行检查: {name}")
            try:
                result = check_func()
                self.results.append(result)

                if not result.is_ok():
                    if critical:
                        logger.error(f"关键检查失败: {name} - {result.message}")
                        all_passed = False
                    else:
                        logger.warning(f"检查警告: {name} - {result.message}")

            except Exception as e:
                logger.error(f"检查执行失败: {name} - {e}")
                self.results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.FAILED,
                        message=f"检查执行失败: {e}",
                        critical=critical,
                    )
                )
                if critical:
                    all_passed = False

        return all_passed, self.results

    def get_summary(self) -> str:
        """获取检查摘要"""
        if not self.results:
            return "未执行任何检查"

        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        total = len(self.results)

        return f"检查完成: {passed}/{total} 通过, {failed} 失败, {warnings} 警告"


def check_python_version() -> CheckResult:
    """检查Python版本"""
    required_version = (3, 8)
    current_version = sys.version_info[:2]

    if current_version >= required_version:
        return CheckResult(
            name="Python版本",
            status=CheckStatus.PASSED,
            message=f"Python {current_version[0]}.{current_version[1]} [OK]",
        )
    else:
        return CheckResult(
            name="Python版本",
            status=CheckStatus.FAILED,
            message=f"需要 Python {required_version[0]}.{required_version[1]}+，当前为 {current_version[0]}.{current_version[1]}",
            suggestions=["请升级到 Python 3.8 或更高版本"],
            critical=True,
        )


def check_required_directories() -> CheckResult:
    """检查必需的目录"""
    required_dirs = [
        "data",
        "logs",
        "reports",
        "assets/templates",
        "assets/knowledge",
        "assets/i18n",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"已创建目录: {dir_path}")
            except Exception as e:
                missing_dirs.append(f"{dir_path} ({e})")

    if not missing_dirs:
        return CheckResult(
            name="目录结构",
            status=CheckStatus.PASSED,
            message="所有必需目录已就绪 [OK]",
        )
    else:
        return CheckResult(
            name="目录结构",
            status=CheckStatus.WARNING,
            message=f"部分目录创建失败: {', '.join(missing_dirs)}",
            suggestions=["请检查文件系统权限"],
        )


def check_config_file() -> CheckResult:
    """检查配置文件"""
    config_file = Path("config.json")

    if not config_file.exists():
        return CheckResult(
            name="配置文件",
            status=CheckStatus.WARNING,
            message="配置文件不存在，将使用默认配置",
            suggestions=["建议创建 config.json 文件以自定义配置"],
        )

    try:
        import json

        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)

        # 检查关键配置项
        required_keys = ["app", "paths"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            return CheckResult(
                name="配置文件",
                status=CheckStatus.WARNING,
                message=f"配置文件缺少关键配置项: {', '.join(missing_keys)}",
                suggestions=["请参考 config.example.json 补充配置"],
            )

        return CheckResult(
            name="配置文件",
            status=CheckStatus.PASSED,
            message="配置文件有效 [OK]",
        )

    except Exception as e:
        return CheckResult(
            name="配置文件",
            status=CheckStatus.FAILED,
            message=f"配置文件解析失败: {e}",
            suggestions=["请检查 config.json 的 JSON 格式是否正确"],
            critical=True,
        )


def check_templates() -> CheckResult:
    """检查实验模板"""
    template_dir = Path("assets/templates")

    if not template_dir.exists():
        return CheckResult(
            name="实验模板",
            status=CheckStatus.WARNING,
            message="模板目录不存在",
            suggestions=["将无法加载实验模板，请添加模板文件到 assets/templates"],
        )

    template_files = list(template_dir.glob("*.yaml")) + list(template_dir.glob("*.yml"))

    if not template_files:
        return CheckResult(
            name="实验模板",
            status=CheckStatus.WARNING,
            message="未找到实验模板文件",
            suggestions=["请添加 .yaml 或 .yml 格式的实验模板到 assets/templates 目录"],
        )

    return CheckResult(
        name="实验模板",
        status=CheckStatus.PASSED,
        message=f"找到 {len(template_files)} 个实验模板 [OK]",
    )


def check_disk_space() -> CheckResult:
    """检查磁盘空间"""
    try:
        import shutil

        # 检查当前目录所在磁盘的空间
        stat = shutil.disk_usage(Path.cwd())
        free_mb = stat.free / (1024 * 1024)
        required_mb = 100  # 至少需要100MB

        if free_mb >= required_mb:
            return CheckResult(
                name="磁盘空间",
                status=CheckStatus.PASSED,
                message=f"可用空间: {free_mb:.1f} MB [OK]",
            )
        else:
            return CheckResult(
                name="磁盘空间",
                status=CheckStatus.WARNING,
                message=f"可用空间不足: {free_mb:.1f} MB (建议至少 {required_mb} MB)",
                suggestions=["请清理磁盘空间以确保应用正常运行"],
            )

    except Exception as e:
        return CheckResult(
            name="磁盘空间",
            status=CheckStatus.WARNING,
            message=f"无法检查磁盘空间: {e}",
        )


def check_dependencies() -> CheckResult:
    """检查依赖库"""
    required_modules = {
        "PySide6": "PySide6>=6.6.0",
        "numpy": "numpy>=1.26.0",
        "yaml": "PyYAML>=6.0.1",
        "pydantic": "pydantic>=2.5.0",
    }

    missing = []
    for module_name, package_info in required_modules.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_info)

    if not missing:
        return CheckResult(
            name="依赖库",
            status=CheckStatus.PASSED,
            message=f"所有必需依赖已安装 ({len(required_modules)} 个) [OK]",
        )
    else:
        return CheckResult(
            name="依赖库",
            status=CheckStatus.FAILED,
            message=f"缺少必需的依赖库: {', '.join(missing)}",
            suggestions=[
                "请运行: pip install -r requirements.txt",
                "或单独安装缺失的包",
            ],
            critical=True,
        )


def create_default_checker() -> StartupChecker:
    """创建默认的启动检查器"""
    checker = StartupChecker()

    # 添加各种检查（按重要性排序）
    checker.add_check("Python版本", check_python_version, critical=True)
    checker.add_check("依赖库", check_dependencies, critical=True)
    checker.add_check("配置文件", check_config_file, critical=False)
    checker.add_check("目录结构", check_required_directories, critical=False)
    checker.add_check("实验模板", check_templates, critical=False)
    checker.add_check("磁盘空间", check_disk_space, critical=False)

    return checker


def format_check_results(results: list[CheckResult]) -> str:
    """格式化检查结果为用户友好的文本

    Args:
        results: 检查结果列表

    Returns:
        格式化的文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("系统检查报告")
    lines.append("=" * 60)
    lines.append("")

    # 按状态分组
    passed = [r for r in results if r.status == CheckStatus.PASSED]
    warnings = [r for r in results if r.status == CheckStatus.WARNING]
    failed = [r for r in results if r.status == CheckStatus.FAILED]

    # 显示通过的检查
    if passed:
        lines.append("通过的检查:")
        for result in passed:
            lines.append(f"  - {result.name}: {result.message}")
        lines.append("")

    # 显示警告
    if warnings:
        lines.append("警告:")
        for result in warnings:
            lines.append(f"  - {result.name}: {result.message}")
            if result.suggestions:
                for suggestion in result.suggestions:
                    lines.append(f"    建议: {suggestion}")
        lines.append("")

    # 显示失败
    if failed:
        lines.append("失败的检查:")
        for result in failed:
            lines.append(f"  - {result.name}: {result.message}")
            if result.suggestions:
                for suggestion in result.suggestions:
                    lines.append(f"    建议: {suggestion}")
        lines.append("")

    # 总结
    total = len(results)
    lines.append(f"总计: {len(passed)} 通过, {len(warnings)} 警告, {len(failed)} 失败 (共 {total} 项)")
    lines.append("=" * 60)

    return "\n".join(lines)
