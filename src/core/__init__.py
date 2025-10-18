#!/usr/bin/env python3
"""
VirtualChemLab 核心模块
提供代码健壮性增强功能
"""

from .robustness_integration import (
    RobustnessIntegrationManager,
    RobustnessSettings,
    IntegrationLevel,
    robustness_integration,
    enhance_robustness,
    validate_input,
    secure_operation,
    log_operation,
    get_robustness_integration
)

from .robustness_enhancer import (
    RobustnessEnhancer,
    RobustnessLevel,
    RobustnessConfig,
    robustness_enhancer,
    enhance_function,
    robustness_context,
    get_robustness_enhancer
)

from .enhanced_error_recovery import (
    EnhancedErrorRecovery,
    RecoveryStrategy,
    ErrorSeverity,
    error_recovery,
    recoverable,
    recovery_context,
    get_error_recovery
)

from .enhanced_validation import (
    EnhancedValidator,
    ValidationLevel,
    ValidationSeverity,
    enhanced_validator,
    validate_data,
    register_validator,
    get_enhanced_validator
)

from .enhanced_logging import (
    EnhancedLogger,
    LogLevel,
    LogCategory,
    enhanced_logger,
    get_enhanced_logger,
    log_context,
    log_performance,
    log_errors
)

from .enhanced_performance import (
    EnhancedPerformanceManager,
    PerformanceLevel,
    OptimizationStrategy,
    performance_manager,
    performance_monitor,
    performance_context,
    get_performance_manager
)

from .enhanced_security import (
    EnhancedSecurityManager,
    SecurityLevel,
    ThreatType,
    AccessLevel,
    security_manager,
    secure_input,
    require_access,
    get_security_manager
)

from .enhanced_testing import (
    EnhancedTestingFramework,
    TestType,
    TestStatus,
    TestSeverity,
    testing_framework,
    test_case,
    benchmark,
    security_test,
    get_testing_framework
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
    "get_testing_framework"
]
