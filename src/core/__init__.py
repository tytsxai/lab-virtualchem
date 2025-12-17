#!/usr/bin/env python3
"""
VirtualChemLab 核心模块
提供代码健壮性增强功能
"""

from .enhanced_error_recovery import (
    EnhancedErrorRecovery,
    ErrorSeverity,
    RecoveryStrategy,
    error_recovery,
    get_error_recovery,
    recoverable,
    recovery_context,
)
from .enhanced_logging import (
    EnhancedLogger,
    LogCategory,
    LogLevel,
    enhanced_logger,
    get_enhanced_logger,
    log_context,
    log_errors,
    log_performance,
)
from .enhanced_performance import (
    EnhancedPerformanceManager,
    OptimizationStrategy,
    PerformanceLevel,
    get_performance_manager,
    performance_context,
    performance_manager,
    performance_monitor,
)
from .enhanced_security import (
    AccessLevel,
    EnhancedSecurityManager,
    SecurityLevel,
    ThreatType,
    get_security_manager,
    require_access,
    secure_input,
    security_manager,
)
from .enhanced_testing import (
    EnhancedTestingFramework,
    TestSeverity,
    TestStatus,
    TestType,
    benchmark,
    get_testing_framework,
    security_test,
    test_case,
    testing_framework,
)
from .enhanced_validation import (
    EnhancedValidator,
    ValidationLevel,
    ValidationSeverity,
    enhanced_validator,
    get_enhanced_validator,
    register_validator,
    validate_data,
)
from .robustness_enhancer import (
    RobustnessConfig,
    RobustnessEnhancer,
    RobustnessLevel,
    enhance_function,
    get_robustness_enhancer,
    robustness_context,
    robustness_enhancer,
)
from .robustness_integration import (
    IntegrationLevel,
    RobustnessIntegrationManager,
    RobustnessSettings,
    enhance_robustness,
    get_robustness_integration,
    log_operation,
    robustness_integration,
    secure_operation,
    validate_input,
)

__all__ = [
    # 集成管理器
    "RobustnessIntegrationManager",
    "RobustnessSettings",
    "IntegrationLevel",
    "robustness_integration",
    "enhance_robustness",
    "validate_input",
    "secure_operation",
    "log_operation",
    "get_robustness_integration",
    # 健壮性增强器
    "RobustnessEnhancer",
    "RobustnessLevel",
    "RobustnessConfig",
    "robustness_enhancer",
    "enhance_function",
    "robustness_context",
    "get_robustness_enhancer",
    # 错误恢复
    "EnhancedErrorRecovery",
    "RecoveryStrategy",
    "ErrorSeverity",
    "error_recovery",
    "recoverable",
    "recovery_context",
    "get_error_recovery",
    # 数据验证
    "EnhancedValidator",
    "ValidationLevel",
    "ValidationSeverity",
    "enhanced_validator",
    "validate_data",
    "register_validator",
    "get_enhanced_validator",
    # 日志记录
    "EnhancedLogger",
    "LogLevel",
    "LogCategory",
    "enhanced_logger",
    "get_enhanced_logger",
    "log_context",
    "log_performance",
    "log_errors",
    # 性能监控
    "EnhancedPerformanceManager",
    "PerformanceLevel",
    "OptimizationStrategy",
    "performance_manager",
    "performance_monitor",
    "performance_context",
    "get_performance_manager",
    # 安全防护
    "EnhancedSecurityManager",
    "SecurityLevel",
    "ThreatType",
    "AccessLevel",
    "security_manager",
    "secure_input",
    "require_access",
    "get_security_manager",
    # 测试框架
    "EnhancedTestingFramework",
    "TestType",
    "TestStatus",
    "TestSeverity",
    "testing_framework",
    "test_case",
    "benchmark",
    "security_test",
    "get_testing_framework",
]
