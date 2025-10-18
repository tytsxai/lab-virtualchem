"""
依赖冲突检测与健康检查工具
"""

import importlib
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DepStatus(Enum):
    """依赖状态"""

    INSTALLED = "installed"
    MISSING = "missing"
    VERSION_CONFLICT = "version_conflict"
    IMPORT_ERROR = "import_error"


@dataclass
class DependencyInfo:
    """依赖信息"""

    name: str
    required_version: str
    actual_version: str | None
    status: DepStatus
    license: str
    is_optional: bool = False
    error_msg: str | None = None


class DependencyChecker:
    """依赖检查器"""

    # 核心依赖定义
    CORE_DEPS = {
        "PySide6": {"version": ">=6.6.0", "license": "LGPL/Commercial"},
        "numpy": {"version": ">=1.26.0", "license": "BSD-3"},
        "scipy": {"version": ">=1.11.0", "license": "BSD-3"},
        "yaml": {"version": ">=6.0.1", "license": "MIT", "module": "yaml"},
        "pydantic": {"version": ">=2.5.0", "license": "MIT"},
        "matplotlib": {"version": ">=3.8.0", "license": "PSF"},
        "simpleeval": {"version": ">=0.9.13", "license": "MIT"},
        "PIL": {"version": ">=10.0.0", "license": "PIL License", "module": "PIL"},
    }

    # 可选依赖定义
    OPTIONAL_DEPS = {
        "rdkit": {"version": ">=2023.3.1", "license": "BSD-3"},
        "pyqtgraph": {"version": ">=0.13.0", "license": "MIT"},
        "reportlab": {"version": ">=4.0.0", "license": "BSD"},
        "weasyprint": {"version": ">=60.0", "license": "BSD"},
    }

    # 增强功能依赖
    ENHANCED_DEPS = {
        "langchain": {"version": ">=0.1.0", "license": "MIT"},
        "openai": {"version": ">=1.0.0", "license": "MIT"},
        "sphinx": {"version": ">=7.0.0", "license": "BSD"},
        "pubchempy": {"version": ">=1.0.0", "license": "MIT"},
        "qtawesome": {"version": ">=1.3.0", "license": "MIT"},
        "pint": {"version": ">=0.23", "license": "BSD-3"},
        "tinydb": {"version": ">=4.8.0", "license": "MIT"},
        "hypothesis": {"version": ">=6.100.0", "license": "MPL-2.0"},
        "bandit": {"version": ">=1.7.0", "license": "Apache-2.0"},
        "streamlit": {"version": ">=1.30.0", "license": "Apache-2.0"},
    }

    # 已知的依赖冲突
    KNOWN_CONFLICTS = [
        {
            "packages": ["matplotlib", "pyqtgraph"],
            "description": "PyQtGraph和Matplotlib可能存在Qt后端冲突",
            "solution": "使用插件系统隔离，PyQtGraph作为可选插件",
        },
        {
            "packages": ["reportlab", "weasyprint"],
            "description": "PDF生成库可能依赖冲突",
            "solution": "智能选择可用的库，互为备份",
        },
    ]

    def __init__(self):
        self.results: dict[str, DependencyInfo] = {}
        self.conflicts: list[dict[str, Any]] = []

    def check_all(self) -> dict[str, Any]:
        """检查所有依赖"""
        logger.info("开始依赖检查...")

        # 检查核心依赖
        core_results = self._check_deps(self.CORE_DEPS, is_optional=False)

        # 检查可选依赖
        optional_results = self._check_deps(self.OPTIONAL_DEPS, is_optional=True)

        # 检查增强依赖
        enhanced_results = self._check_deps(self.ENHANCED_DEPS, is_optional=True)

        # 合并结果
        self.results.update(core_results)
        self.results.update(optional_results)
        self.results.update(enhanced_results)

        # 检查冲突
        self._check_conflicts()

        # 生成报告
        return self._generate_report()

    def _check_deps(self, deps: dict[str, dict], is_optional: bool = False) -> dict[str, DependencyInfo]:
        """检查依赖列表"""
        results = {}

        for pkg_name, info in deps.items():
            module_name = info.get("module", pkg_name)
            required_version = info["version"]
            license_type = info["license"]

            try:
                # 尝试导入
                module = importlib.import_module(module_name)

                # 获取版本
                version = self._get_version(module, pkg_name)

                # 检查版本兼容性
                status = DepStatus.INSTALLED
                if required_version.startswith(">="):
                    min_version = required_version[2:]
                    if version and self._compare_version(version, min_version) < 0:
                        status = DepStatus.VERSION_CONFLICT

                results[pkg_name] = DependencyInfo(
                    name=pkg_name,
                    required_version=required_version,
                    actual_version=version,
                    status=status,
                    license=license_type,
                    is_optional=is_optional,
                )

            except ImportError as e:
                results[pkg_name] = DependencyInfo(
                    name=pkg_name,
                    required_version=required_version,
                    actual_version=None,
                    status=DepStatus.MISSING,
                    license=license_type,
                    is_optional=is_optional,
                    error_msg=str(e),
                )

            except Exception as e:
                results[pkg_name] = DependencyInfo(
                    name=pkg_name,
                    required_version=required_version,
                    actual_version=None,
                    status=DepStatus.IMPORT_ERROR,
                    license=license_type,
                    is_optional=is_optional,
                    error_msg=str(e),
                )

        return results

    def _get_version(self, module: Any, pkg_name: str) -> str | None:
        """获取模块版本"""
        # 尝试多种版本获取方式
        for attr in ["__version__", "VERSION", "version"]:
            if hasattr(module, attr):
                version = getattr(module, attr)
                if isinstance(version, str):
                    return version
                elif isinstance(version, tuple):
                    return ".".join(map(str, version))

        # 尝试从包元数据获取
        try:
            import importlib.metadata

            return importlib.metadata.version(pkg_name)
        except Exception:
            pass

        return None

    def _compare_version(self, v1: str, v2: str) -> int:
        """比较版本号
        返回: v1 > v2 返回1, v1 < v2 返回-1, v1 == v2 返回0
        """

        def parse_version(v: str) -> list[int]:
            return [int(x) for x in v.split(".") if x.isdigit()]

        try:
            parts1 = parse_version(v1)
            parts2 = parse_version(v2)

            # 补齐长度
            max_len = max(len(parts1), len(parts2))
            parts1 += [0] * (max_len - len(parts1))
            parts2 += [0] * (max_len - len(parts2))

            for p1, p2 in zip(parts1, parts2, strict=False):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1

            return 0
        except Exception:
            return 0

    def _check_conflicts(self):
        """检查已知冲突"""
        for conflict in self.KNOWN_CONFLICTS:
            packages = conflict["packages"]

            # 检查冲突的包是否都已安装
            all_installed = all(
                self.results.get(pkg) and self.results[pkg].status == DepStatus.INSTALLED for pkg in packages
            )

            if all_installed:
                self.conflicts.append(conflict)
                logger.warning(f"检测到潜在冲突: {conflict['description']}")

    def _generate_report(self) -> dict[str, Any]:
        """生成检查报告"""
        # 统计信息
        core_installed = sum(
            1 for dep in self.results.values() if not dep.is_optional and dep.status == DepStatus.INSTALLED
        )
        core_total = sum(1 for dep in self.results.values() if not dep.is_optional)

        optional_installed = sum(
            1 for dep in self.results.values() if dep.is_optional and dep.status == DepStatus.INSTALLED
        )
        optional_total = sum(1 for dep in self.results.values() if dep.is_optional)

        # 检测问题
        missing_core = [dep for dep in self.results.values() if not dep.is_optional and dep.status == DepStatus.MISSING]

        version_conflicts = [dep for dep in self.results.values() if dep.status == DepStatus.VERSION_CONFLICT]

        import_errors = [dep for dep in self.results.values() if dep.status == DepStatus.IMPORT_ERROR]

        # 生成报告
        report = {
            "summary": {
                "core_installed": core_installed,
                "core_total": core_total,
                "core_percentage": (core_installed / core_total * 100) if core_total > 0 else 0,
                "optional_installed": optional_installed,
                "optional_total": optional_total,
                "optional_percentage": (optional_installed / optional_total * 100) if optional_total > 0 else 0,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            },
            "issues": {
                "missing_core": [{"name": d.name, "required": d.required_version} for d in missing_core],
                "version_conflicts": [
                    {"name": d.name, "required": d.required_version, "actual": d.actual_version}
                    for d in version_conflicts
                ],
                "import_errors": [{"name": d.name, "error": d.error_msg} for d in import_errors],
                "potential_conflicts": self.conflicts,
            },
            "all_dependencies": {
                name: {
                    "version": dep.actual_version or "N/A",
                    "status": dep.status.value,
                    "license": dep.license,
                    "optional": dep.is_optional,
                }
                for name, dep in self.results.items()
            },
        }

        return report

    def print_report(self, report: dict[str, Any]):
        """打印检查报告"""
        print("\n" + "=" * 60)
        logger.info("依赖检查报告")
        print("=" * 60 + "\n")

        # 汇总信息
        summary = report["summary"]
        logger.info(f"Python版本: {summary['python_version']}")
        logger.info(
            f"\n核心依赖: {summary['core_installed']}/{summary['core_total']} ({summary['core_percentage']:.1f}%)"
        )
        logger.info(
            f"可选依赖: {summary['optional_installed']}/{summary['optional_total']} ({summary['optional_percentage']:.1f}%)"
        )

        # 问题报告
        issues = report["issues"]

        if issues["missing_core"]:
            logger.info("\n🔴 缺失的核心依赖:")
            for dep in issues["missing_core"]:
                logger.info(f"  - {dep['name']} {dep['required']}")

        if issues["version_conflicts"]:
            logger.info("\n⚠️  版本冲突:")
            for dep in issues["version_conflicts"]:
                logger.info(f"  - {dep['name']}: 需要 {dep['required']}, 实际 {dep['actual']}")

        if issues["import_errors"]:
            logger.info("\n❌ 导入错误:")
            for dep in issues["import_errors"]:
                logger.info(f"  - {dep['name']}: {dep['error']}")

        if issues["potential_conflicts"]:
            logger.info("\n⚠️  潜在冲突:")
            for conflict in issues["potential_conflicts"]:
                logger.info(f"  - {conflict['description']}")
                logger.info(f"    解决方案: {conflict['solution']}")

        if not any(
            [
                issues["missing_core"],
                issues["version_conflicts"],
                issues["import_errors"],
                issues["potential_conflicts"],
            ]
        ):
            logger.info("\n✅ 所有依赖检查通过!")

        print("\n" + "=" * 60 + "\n")


def run_dependency_check():
    """运行依赖检查"""
    checker = DependencyChecker()
    report = checker.check_all()
    checker.print_report(report)
    return report


if __name__ == "__main__":
    run_dependency_check()
