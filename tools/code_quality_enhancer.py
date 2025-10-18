#!/usr/bin/env python
"""
代码质量提升工具

自动化改进代码质量，包括：
- 添加类型注解
- 改进错误处理
- 添加日志记录
- 优化代码结构
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class CodeIssue:
    """代码问题"""

    file: str
    line: int
    type: str
    description: str
    suggestion: str


class CodeQualityEnhancer:
    """代码质量提升器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.issues: list[CodeIssue] = []

    def analyze_all(self):
        """分析所有文件"""
        print("[SCAN] Starting code quality analysis...")

        py_files = list(self.src_dir.rglob("*.py"))
        print(f"[FILES] Found {len(py_files)} Python files")

        for py_file in py_files:
            self.analyze_file(py_file)

        print(f"\n[DONE] Analysis complete, found {len(self.issues)} improvement points")

    def analyze_file(self, file_path: Path):
        """分析单个文件"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))

            # 检查函数定义
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._check_function(node, file_path)
                elif isinstance(node, ast.ExceptHandler):
                    self._check_exception_handler(node, file_path)

        except SyntaxError:
            # 跳过语法错误文件
            pass
        except Exception as e:
            print(f"[WARN] Failed to analyze {file_path}: {e}")

    def _check_function(self, node: ast.FunctionDef, file_path: Path):
        """检查函数定义"""
        # 检查返回值类型注解
        if node.returns is None and node.name not in ["__init__", "__str__", "__repr__"]:
            self.issues.append(
                CodeIssue(
                    file=str(file_path.relative_to(project_root)),
                    line=node.lineno,
                    type="type_hint",
                    description=f"函数 '{node.name}' 缺少返回值类型注解",
                    suggestion="添加 -> ReturnType 注解",
                )
            )

        # 检查参数类型注解
        for arg in node.args.args:
            if arg.annotation is None and arg.arg != "self" and arg.arg != "cls":
                self.issues.append(
                    CodeIssue(
                        file=str(file_path.relative_to(project_root)),
                        line=node.lineno,
                        type="type_hint",
                        description=f"函数 '{node.name}' 的参数 '{arg.arg}' 缺少类型注解",
                        suggestion=f"添加 {arg.arg}: Type 注解",
                    )
                )

    def _check_exception_handler(self, node: ast.ExceptHandler, file_path: Path):
        """检查异常处理"""
        # 检查是否捕获了泛型Exception
        if node.type and isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self.issues.append(
                CodeIssue(
                    file=str(file_path.relative_to(project_root)),
                    line=node.lineno,
                    type="error_handling",
                    description="捕获了泛型Exception",
                    suggestion="使用更具体的异常类型，如 ValueError, IOError 等",
                )
            )

        # 检查是否有日志记录
        has_logging = False
        for stmt in ast.walk(node):
            if (
                isinstance(stmt, ast.Call)
                and isinstance(stmt.func, ast.Attribute)
                and stmt.func.attr in ["error", "exception", "warning", "critical"]
            ):
                has_logging = True
                break

        if not has_logging:
            self.issues.append(
                CodeIssue(
                    file=str(file_path.relative_to(project_root)),
                    line=node.lineno,
                    type="logging",
                    description="异常处理中缺少日志记录",
                    suggestion="添加 logger.error() 或 logger.exception()",
                )
            )

    def generate_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("代码质量改进建议报告")
        lines.append("=" * 80)
        lines.append(f"\n总改进点数: {len(self.issues)}\n")

        # 按类型分组
        issues_by_type: dict[str, list[CodeIssue]] = {}
        for issue in self.issues:
            if issue.type not in issues_by_type:
                issues_by_type[issue.type] = []
            issues_by_type[issue.type].append(issue)

        # 统计
        lines.append("## 问题类型统计")
        for issue_type, issues in issues_by_type.items():
            lines.append(f"- {issue_type}: {len(issues)} 个")
        lines.append("")

        # 详细列表 (只显示前50个)
        lines.append("## 详细建议 (前50项)")
        lines.append("-" * 80)
        for i, issue in enumerate(self.issues[:50], 1):
            lines.append(f"\n{i}. [{issue.type}] {issue.file}:{issue.line}")
            lines.append(f"   问题: {issue.description}")
            lines.append(f"   建议: {issue.suggestion}")

        if len(self.issues) > 50:
            lines.append(f"\n... 还有 {len(self.issues) - 50} 个改进点未显示")

        lines.append("\n" + "=" * 80)
        lines.append("## Priority Recommendations")
        lines.append("=" * 80)
        lines.append("1. [OK] Add complete type annotations for public API functions")
        lines.append("2. [OK] Replace generic Exception with specific exception types")
        lines.append("3. [OK] Add logging to all exception handlers")
        lines.append("4. [OK] Add docstrings to explain function purpose and parameters")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, output_file: str = "code_quality_report.txt"):
        """保存报告"""
        report = self.generate_report()

        output_path = project_root / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n[SAVED] Report saved to: {output_path}")
        print(report)


def main():
    """主函数"""
    enhancer = CodeQualityEnhancer()
    enhancer.analyze_all()
    enhancer.save_report()


if __name__ == "__main__":
    main()
