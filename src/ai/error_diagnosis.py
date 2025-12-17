"""
错误诊断模块
提供智能错误诊断和分析功能
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误类别"""

    SYNTAX = "syntax"  # 语法错误
    LOGIC = "logic"  # 逻辑错误
    RUNTIME = "runtime"  # 运行时错误
    CONFIGURATION = "configuration"  # 配置错误
    DEPENDENCY = "dependency"  # 依赖错误
    PERMISSION = "permission"  # 权限错误
    NETWORK = "network"  # 网络错误
    DATA = "data"  # 数据错误
    UNKNOWN = "unknown"  # 未知错误


@dataclass
class ErrorPattern:
    """错误模式"""

    pattern_id: str
    category: ErrorCategory
    pattern_regex: str
    description: str
    typical_causes: list[str]
    suggested_fixes: list[str]
    severity: str = "medium"  # low, medium, high, critical

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "pattern_regex": self.pattern_regex,
            "description": self.description,
            "typical_causes": self.typical_causes,
            "suggested_fixes": self.suggested_fixes,
            "severity": self.severity,
        }


@dataclass
class DiagnosisResult:
    """诊断结果"""

    error_message: str
    category: ErrorCategory
    matched_patterns: list[ErrorPattern]
    root_cause: str
    suggested_fixes: list[str]
    confidence: float  # 0-1
    additional_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "error_message": self.error_message,
            "category": self.category.value,
            "matched_patterns": [p.to_dict() for p in self.matched_patterns],
            "root_cause": self.root_cause,
            "suggested_fixes": self.suggested_fixes,
            "confidence": self.confidence,
            "additional_info": self.additional_info or {},
        }


class ErrorDiagnosis:
    """错误诊断器"""

    def __init__(self):
        """初始化错误诊断器"""
        self.patterns: list[ErrorPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """加载默认错误模式"""
        self.patterns = [
            ErrorPattern(
                pattern_id="import_error_01",
                category=ErrorCategory.DEPENDENCY,
                pattern_regex=r"ModuleNotFoundError|ImportError",
                description="模块导入错误",
                typical_causes=[
                    "模块未安装",
                    "模块路径不正确",
                    "依赖版本不兼容",
                    "循环导入",
                ],
                suggested_fixes=[
                    "检查模块是否已安装: pip list | grep <module>",
                    "安装缺失的模块: pip install <module>",
                    "检查导入路径是否正确",
                    "检查是否存在循环导入",
                ],
                severity="high",
            ),
            ErrorPattern(
                pattern_id="attr_error_01",
                category=ErrorCategory.RUNTIME,
                pattern_regex=r"AttributeError",
                description="属性错误",
                typical_causes=[
                    "对象没有该属性",
                    "拼写错误",
                    "对象为 None",
                    "版本不兼容",
                ],
                suggested_fixes=[
                    "检查属性名称拼写",
                    "使用 hasattr() 检查属性是否存在",
                    "检查对象是否为 None",
                    "查看文档确认属性是否存在",
                ],
                severity="medium",
            ),
            ErrorPattern(
                pattern_id="type_error_01",
                category=ErrorCategory.RUNTIME,
                pattern_regex=r"TypeError",
                description="类型错误",
                typical_causes=[
                    "参数类型不匹配",
                    "对象不可调用",
                    "操作不支持该类型",
                ],
                suggested_fixes=[
                    "检查函数参数类型",
                    "使用 type() 或 isinstance() 检查类型",
                    "转换为正确的类型",
                    "查看函数签名和文档",
                ],
                severity="medium",
            ),
            ErrorPattern(
                pattern_id="value_error_01",
                category=ErrorCategory.DATA,
                pattern_regex=r"ValueError",
                description="值错误",
                typical_causes=[
                    "值超出有效范围",
                    "格式不正确",
                    "转换失败",
                ],
                suggested_fixes=[
                    "检查输入值的范围",
                    "验证数据格式",
                    "使用 try-except 处理转换错误",
                    "添加输入验证",
                ],
                severity="medium",
            ),
            ErrorPattern(
                pattern_id="key_error_01",
                category=ErrorCategory.DATA,
                pattern_regex=r"KeyError",
                description="键错误",
                typical_causes=[
                    "字典中不存在该键",
                    "配置文件缺少必需项",
                ],
                suggested_fixes=[
                    "使用 dict.get() 代替直接访问",
                    "检查键是否存在: if key in dict",
                    "检查配置文件是否完整",
                    "提供默认值",
                ],
                severity="medium",
            ),
            ErrorPattern(
                pattern_id="file_error_01",
                category=ErrorCategory.RUNTIME,
                pattern_regex=r"FileNotFoundError",
                description="文件未找到错误",
                typical_causes=[
                    "文件路径不存在",
                    "文件已被删除或移动",
                    "路径权限问题",
                ],
                suggested_fixes=[
                    "检查文件路径是否正确",
                    "使用绝对路径",
                    "检查文件权限",
                    "确保文件存在: os.path.exists()",
                ],
                severity="high",
            ),
            ErrorPattern(
                pattern_id="permission_error_01",
                category=ErrorCategory.PERMISSION,
                pattern_regex=r"PermissionError",
                description="权限错误",
                typical_causes=[
                    "没有读写权限",
                    "文件被其他进程占用",
                    "需要管理员权限",
                ],
                suggested_fixes=[
                    "检查文件权限",
                    "以管理员身份运行",
                    "关闭占用文件的其他进程",
                    "更改文件权限: chmod",
                ],
                severity="high",
            ),
            ErrorPattern(
                pattern_id="connection_error_01",
                category=ErrorCategory.NETWORK,
                pattern_regex=r"ConnectionError|TimeoutError",
                description="连接错误",
                typical_causes=[
                    "网络连接失败",
                    "服务器未响应",
                    "超时",
                    "防火墙阻止",
                ],
                suggested_fixes=[
                    "检查网络连接",
                    "检查服务器状态",
                    "增加超时时间",
                    "检查防火墙设置",
                ],
                severity="medium",
            ),
        ]

    def add_pattern(self, pattern: ErrorPattern):
        """添加错误模式"""
        self.patterns.append(pattern)
        logger.debug(f"添加错误模式: {pattern.pattern_id}")

    def diagnose(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> DiagnosisResult:
        """诊断错误

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            诊断结果
        """
        error_message = str(error)
        error_type = type(error).__name__

        # 匹配错误模式
        matched_patterns = []
        for pattern in self.patterns:
            import re

            if re.search(pattern.pattern_regex, error_type) or re.search(
                pattern.pattern_regex, error_message
            ):
                matched_patterns.append(pattern)

        # 确定错误类别
        if matched_patterns:
            category = matched_patterns[0].category
            confidence = 0.8
        else:
            category = ErrorCategory.UNKNOWN
            confidence = 0.3

        # 分析根本原因
        root_cause = self._analyze_root_cause(error, matched_patterns, context)

        # 收集建议修复方案
        suggested_fixes = []
        for pattern in matched_patterns:
            suggested_fixes.extend(pattern.suggested_fixes)

        # 去重
        suggested_fixes = list(dict.fromkeys(suggested_fixes))

        # 如果没有匹配的模式，提供通用建议
        if not suggested_fixes:
            suggested_fixes = [
                "查看完整的错误堆栈信息",
                "检查相关代码的输入和输出",
                "查阅官方文档",
                "在社区搜索相似问题",
            ]

        return DiagnosisResult(
            error_message=error_message,
            category=category,
            matched_patterns=matched_patterns,
            root_cause=root_cause,
            suggested_fixes=suggested_fixes,
            confidence=confidence,
            additional_info=context,
        )

    def _analyze_root_cause(
        self,
        error: Exception,
        patterns: list[ErrorPattern],
        context: dict[str, Any] | None,
    ) -> str:
        """分析根本原因"""
        if not patterns:
            return f"未知错误: {type(error).__name__}"

        # 使用第一个匹配的模式的描述
        primary_pattern = patterns[0]
        root_cause = primary_pattern.description

        # 如果有上下文信息，尝试提供更具体的分析
        if context:
            if "file_path" in context:
                root_cause += f" (文件: {context['file_path']})"
            if "line_number" in context:
                root_cause += f" (行号: {context['line_number']})"

        return root_cause

    def get_pattern_by_id(self, pattern_id: str) -> ErrorPattern | None:
        """根据ID获取错误模式"""
        for pattern in self.patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        return None

    def get_patterns_by_category(self, category: ErrorCategory) -> list[ErrorPattern]:
        """根据类别获取错误模式"""
        return [p for p in self.patterns if p.category == category]

    def clear_patterns(self):
        """清除所有自定义模式（保留默认模式）"""
        self.patterns.clear()
        self._load_default_patterns()


if __name__ == "__main__":
    # 示例使用
    diagnosis = ErrorDiagnosis()

    # 模拟错误
    try:
        raise ModuleNotFoundError("No module named 'some_module'")
    except Exception as e:
        result = diagnosis.diagnose(
            e, context={"file_path": "main.py", "line_number": 10}
        )

        print("错误诊断结果:")
        print(f"错误消息: {result.error_message}")
        print(f"类别: {result.category.value}")
        print(f"根本原因: {result.root_cause}")
        print(f"置信度: {result.confidence}")
        print("\n建议修复方案:")
        for i, fix in enumerate(result.suggested_fixes, 1):
            print(f"{i}. {fix}")
