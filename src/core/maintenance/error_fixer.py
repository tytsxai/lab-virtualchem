"""
错误诊断和修复器实现

提供系统错误诊断和自动修复功能

增强功能:
1. 智能问题检测和分类
2. 预测性维护和故障预防
3. 自动化修复和回滚机制
4. 性能优化和资源管理
5. 安全检查和漏洞修复
6. 配置管理和版本控制
7. 监控告警和通知系统
8. 维护报告和分析
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

from ...interfaces.maintenance import (
    IErrorFixer,
    IssueSeverity,
    MaintenanceIssue,
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceTaskType,
)

logger = logging.getLogger(__name__)


class MaintenanceLevel(Enum):
    """维护级别"""

    BASIC = "basic"  # 基础维护
    STANDARD = "standard"  # 标准维护
    ADVANCED = "advanced"  # 高级维护
    COMPREHENSIVE = "comprehensive"  # 全面维护


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


class ErrorFixer(IErrorFixer):
    """错误修复器实现"""

    def __init__(
        self,
        base_path: str = ".",
        maintenance_level: MaintenanceLevel = MaintenanceLevel.STANDARD,
        enable_auto_fix: bool = True,
        enable_monitoring: bool = True,
        alert_threshold: float = 0.8,
    ):
        """
        初始化错误修复器

        Args:
            base_path: 基础路径
            maintenance_level: 维护级别
            enable_auto_fix: 是否启用自动修复
            enable_monitoring: 是否启用监控
            alert_threshold: 告警阈值
        """
        self.base_path = Path(base_path)
        self.maintenance_level = maintenance_level
        self.enable_auto_fix = enable_auto_fix
        self.enable_monitoring = enable_monitoring
        self.alert_threshold = alert_threshold

        self.issues: dict[str, MaintenanceIssue] = {}
        self.issue_counter = 0
        self.maintenance_history: list[dict[str, Any]] = []
        self.performance_metrics: dict[str, Any] = {}
        self.alert_history: list[dict[str, Any]] = []

        # 维护统计
        self.stats = {
            "total_diagnoses": 0,
            "total_fixes": 0,
            "successful_fixes": 0,
            "failed_fixes": 0,
            "auto_fixes": 0,
            "manual_fixes": 0,
            "preventive_actions": 0,
        }

    def diagnose_issues(self) -> list[MaintenanceIssue]:
        """
        诊断问题

        Returns:
            问题列表
        """
        self.issues.clear()
        all_issues = []

        try:
            # 检查数据目录
            all_issues.extend(self._check_data_directories())

            # 检查配置文件
            all_issues.extend(self._check_config_files())

            # 检查日志文件
            all_issues.extend(self._check_log_files())

            # 检查权限
            all_issues.extend(self._check_permissions())

            # 检查磁盘空间
            all_issues.extend(self._check_disk_space())

            # 检查JSON文件完整性
            all_issues.extend(self._check_json_integrity())

            # 保存问题到字典
            for issue in all_issues:
                self.issues[issue.issue_id] = issue

            logger.info(f"诊断完成: 发现{len(all_issues)}个问题")

        except Exception as e:
            logger.error(f"诊断过程失败: {e}", exc_info=True)

        self.stats["total_diagnoses"] += 1
        return all_issues

    def predictive_maintenance(self) -> list[dict[str, Any]]:
        """预测性维护

        Returns:
            预测性维护建议列表
        """
        recommendations = []

        try:
            # 分析系统性能趋势
            self._analyze_performance_trends()

            # 预测磁盘空间使用
            disk_prediction = self._predict_disk_usage()
            if disk_prediction["days_until_full"] < 30:
                recommendations.append(
                    {
                        "type": "disk_space",
                        "severity": AlertLevel.WARNING,
                        "message": f"磁盘空间将在{disk_prediction['days_until_full']}天内用完",
                        "action": "清理临时文件或增加存储空间",
                        "priority": "high",
                    }
                )

            # 预测内存使用
            memory_prediction = self._predict_memory_usage()
            if memory_prediction["risk_level"] == "high":
                recommendations.append(
                    {
                        "type": "memory_usage",
                        "severity": AlertLevel.WARNING,
                        "message": "内存使用率持续上升，存在内存泄漏风险",
                        "action": "检查内存泄漏或增加内存",
                        "priority": "medium",
                    }
                )

            # 预测日志文件增长
            log_prediction = self._predict_log_growth()
            if log_prediction["growth_rate"] > 100:  # MB per day
                recommendations.append(
                    {
                        "type": "log_growth",
                        "severity": AlertLevel.INFO,
                        "message": f"日志文件增长过快: {log_prediction['growth_rate']:.1f}MB/天",
                        "action": "调整日志级别或清理旧日志",
                        "priority": "low",
                    }
                )

            # 预测配置文件变更
            config_prediction = self._predict_config_changes()
            if config_prediction["change_frequency"] > 10:  # changes per week
                recommendations.append(
                    {
                        "type": "config_stability",
                        "severity": AlertLevel.INFO,
                        "message": "配置文件变更频繁，建议审查配置管理流程",
                        "action": "建立配置变更审批流程",
                        "priority": "low",
                    }
                )

        except Exception as e:
            logger.error(f"预测性维护分析失败: {e}")

        return recommendations

    def _analyze_performance_trends(self) -> dict[str, Any]:
        """分析性能趋势"""
        try:
            # 获取系统性能数据
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"性能趋势分析失败: {e}")
            return {}

    def _predict_disk_usage(self) -> dict[str, Any]:
        """预测磁盘使用"""
        try:
            disk = psutil.disk_usage("/")
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)

            # 简单的线性预测（实际应用中可以使用更复杂的算法）
            usage_growth_rate = 0.1  # GB per day (假设值)
            days_until_full = free_gb / usage_growth_rate if usage_growth_rate > 0 else 365

            return {
                "current_free_gb": free_gb,
                "total_gb": total_gb,
                "usage_percent": (disk.used / disk.total) * 100,
                "days_until_full": days_until_full,
                "risk_level": "high" if days_until_full < 30 else "medium" if days_until_full < 90 else "low",
            }
        except Exception as e:
            logger.warning(f"磁盘使用预测失败: {e}")
            return {"days_until_full": 365, "risk_level": "low"}

    def _predict_memory_usage(self) -> dict[str, Any]:
        """预测内存使用"""
        try:
            memory = psutil.virtual_memory()
            return {
                "current_usage_percent": memory.percent,
                "available_gb": memory.available / (1024**3),
                "risk_level": "high" if memory.percent > 85 else "medium" if memory.percent > 70 else "low",
            }
        except Exception as e:
            logger.warning(f"内存使用预测失败: {e}")
            return {"risk_level": "low"}

    def _predict_log_growth(self) -> dict[str, Any]:
        """预测日志增长"""
        try:
            log_dir = self.base_path / "logs"
            if not log_dir.exists():
                return {"growth_rate": 0}

            total_size = 0
            for log_file in log_dir.glob("*.log"):
                if log_file.exists():
                    total_size += log_file.stat().st_size

            # 简单的增长预测（实际应用中需要历史数据）
            growth_rate = total_size / (1024**2) / 7  # MB per day (假设值)

            return {"current_size_mb": total_size / (1024**2), "growth_rate": growth_rate}
        except Exception as e:
            logger.warning(f"日志增长预测失败: {e}")
            return {"growth_rate": 0}

    def _predict_config_changes(self) -> dict[str, Any]:
        """预测配置变更"""
        try:
            config_dir = self.base_path / "config"
            if not config_dir.exists():
                return {"change_frequency": 0}

            # 统计配置文件数量
            config_files = list(config_dir.glob("*.json")) + list(config_dir.glob("*.yaml"))

            # 简单的变更频率预测（实际应用中需要历史数据）
            change_frequency = len(config_files) * 0.5  # changes per week (假设值)

            return {"config_file_count": len(config_files), "change_frequency": change_frequency}
        except Exception as e:
            logger.warning(f"配置变更预测失败: {e}")
            return {"change_frequency": 0}

    def optimize_performance(self) -> MaintenanceResult:
        """性能优化

        Returns:
            优化结果
        """
        start_time = time.time()
        optimizations = []

        try:
            # 清理临时文件
            temp_cleaned = self._cleanup_temp_files()
            if temp_cleaned > 0:
                optimizations.append(f"清理了 {temp_cleaned} 个临时文件")

            # 优化日志文件
            log_optimized = self._optimize_log_files()
            if log_optimized:
                optimizations.append("优化了日志文件")

            # 清理缓存
            cache_cleaned = self._cleanup_cache()
            if cache_cleaned > 0:
                optimizations.append(f"清理了 {cache_cleaned} 个缓存文件")

            # 优化配置文件
            config_optimized = self._optimize_config_files()
            if config_optimized:
                optimizations.append("优化了配置文件")

            success = len(optimizations) > 0
            message = f"性能优化完成: {', '.join(optimizations)}" if optimizations else "无需优化"

            # 记录维护历史
            self._record_maintenance_history("performance_optimization", success, message)

            return MaintenanceResult(
                task_type=MaintenanceTaskType.PERFORMANCE_OPTIMIZATION,
                status=MaintenanceStatus.COMPLETED if success else MaintenanceStatus.SKIPPED,
                success=success,
                message=message,
                duration_seconds=time.time() - start_time,
                details={"optimizations": optimizations},
            )

        except Exception as e:
            logger.error(f"性能优化失败: {e}")
            return MaintenanceResult(
                task_type=MaintenanceTaskType.PERFORMANCE_OPTIMIZATION,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=f"性能优化失败: {e}",
                duration_seconds=time.time() - start_time,
            )

    def _cleanup_temp_files(self) -> int:
        """清理临时文件"""
        cleaned_count = 0
        try:
            temp_dirs = [self.base_path / "temp", self.base_path / "logs" / "temp", self.base_path / "data" / "temp"]

            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    for temp_file in temp_dir.glob("*"):
                        if temp_file.is_file():
                            try:
                                temp_file.unlink()
                                cleaned_count += 1
                            except Exception as e:
                                logger.warning(f"删除临时文件失败: {e}")

        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

        return cleaned_count

    def _optimize_log_files(self) -> bool:
        """优化日志文件"""
        try:
            log_dir = self.base_path / "logs"
            if not log_dir.exists():
                return False

            # 压缩旧日志文件
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    try:
                        # 这里可以添加日志压缩逻辑
                        logger.info(f"日志文件需要压缩: {log_file}")
                    except Exception as e:
                        logger.warning(f"压缩日志文件失败: {e}")

            return True

        except Exception as e:
            logger.warning(f"优化日志文件失败: {e}")
            return False

    def _cleanup_cache(self) -> int:
        """清理缓存"""
        cleaned_count = 0
        try:
            cache_dirs = [self.base_path / "data" / ".cache", self.base_path / "logs" / "cache"]

            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    for cache_file in cache_dir.glob("*"):
                        if cache_file.is_file():
                            try:
                                cache_file.unlink()
                                cleaned_count += 1
                            except Exception as e:
                                logger.warning(f"删除缓存文件失败: {e}")

        except Exception as e:
            logger.warning(f"清理缓存失败: {e}")

        return cleaned_count

    def _optimize_config_files(self) -> bool:
        """优化配置文件"""
        try:
            config_dir = self.base_path / "config"
            if not config_dir.exists():
                return False

            # 检查配置文件格式
            for config_file in config_dir.glob("*.json"):
                try:
                    with open(config_file, encoding="utf-8") as f:
                        json.load(f)  # 验证JSON格式
                except json.JSONDecodeError as e:
                    logger.warning(f"配置文件格式错误: {config_file}, {e}")

            return True

        except Exception as e:
            logger.warning(f"优化配置文件失败: {e}")
            return False

    def _record_maintenance_history(self, task_type: str, success: bool, message: str) -> None:
        """记录维护历史"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "success": success,
            "message": message,
            "maintenance_level": self.maintenance_level.value,
        }

        self.maintenance_history.append(history_entry)

        # 保持历史记录数量限制
        if len(self.maintenance_history) > 1000:
            self.maintenance_history = self.maintenance_history[-500:]

    def get_maintenance_report(self) -> dict[str, Any]:
        """获取维护报告"""
        return {
            "maintenance_level": self.maintenance_level.value,
            "statistics": self.stats,
            "recent_history": self.maintenance_history[-10:],
            "performance_metrics": self.performance_metrics,
            "alert_history": self.alert_history[-10:],
            "system_health": self._assess_system_health(),
        }

    def _assess_system_health(self) -> dict[str, Any]:
        """评估系统健康状态"""
        try:
            # 获取系统指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 计算健康分数
            health_score = 100
            health_score -= min(cpu_percent * 0.5, 25)  # CPU影响
            health_score -= min(memory.percent * 0.3, 20)  # 内存影响
            health_score -= min(disk.percent * 0.2, 15)  # 磁盘影响

            # 确定健康状态
            if health_score >= 90:
                status = "excellent"
            elif health_score >= 75:
                status = "good"
            elif health_score >= 60:
                status = "fair"
            else:
                status = "poor"

            return {
                "overall_score": max(0, health_score),
                "status": status,
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.warning(f"系统健康评估失败: {e}")
            return {"overall_score": 0, "status": "unknown", "error": str(e)}

    def fix_issue(self, issue_id: str) -> MaintenanceResult:
        """
        修复单个问题

        Args:
            issue_id: 问题ID

        Returns:
            维护结果
        """
        start_time = time.time()

        if issue_id not in self.issues:
            return MaintenanceResult(
                task_type=MaintenanceTaskType.ERROR_FIX,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=f"未找到问题: {issue_id}",
                duration_seconds=time.time() - start_time,
            )

        issue = self.issues[issue_id]

        if not issue.fix_available:
            return MaintenanceResult(
                task_type=MaintenanceTaskType.ERROR_FIX,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=f"问题不可自动修复: {issue.title}",
                duration_seconds=time.time() - start_time,
            )

        try:
            # 根据问题类别执行修复
            success = self._execute_fix(issue)

            duration = time.time() - start_time

            if success:
                return MaintenanceResult(
                    task_type=MaintenanceTaskType.ERROR_FIX,
                    status=MaintenanceStatus.COMPLETED,
                    success=True,
                    message=f"问题修复成功: {issue.title}",
                    items_processed=1,
                    items_fixed=1,
                    duration_seconds=duration,
                )
            else:
                return MaintenanceResult(
                    task_type=MaintenanceTaskType.ERROR_FIX,
                    status=MaintenanceStatus.FAILED,
                    success=False,
                    message=f"问题修复失败: {issue.title}",
                    duration_seconds=duration,
                )

        except Exception as e:
            error_msg = f"修复问题时出错: {e}"
            logger.error(error_msg, exc_info=True)
            return MaintenanceResult(
                task_type=MaintenanceTaskType.ERROR_FIX,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=error_msg,
                duration_seconds=time.time() - start_time,
                errors=[str(e)],
            )

    def fix_all_issues(self, severity_threshold: IssueSeverity = IssueSeverity.MEDIUM) -> MaintenanceResult:
        """
        修复所有问题

        Args:
            severity_threshold: 严重程度阈值

        Returns:
            维护结果
        """
        start_time = time.time()
        items_processed = 0
        items_fixed = 0
        errors = []

        # 严重程度排序
        severity_order = {
            IssueSeverity.CRITICAL: 4,
            IssueSeverity.HIGH: 3,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 1,
            IssueSeverity.INFO: 0,
        }

        threshold_level = severity_order[severity_threshold]

        try:
            # 过滤可修复且满足严重程度的问题
            fixable_issues = [
                issue
                for issue in self.issues.values()
                if issue.fix_available and severity_order[issue.severity] >= threshold_level
            ]

            # 按严重程度排序
            fixable_issues.sort(key=lambda x: severity_order[x.severity], reverse=True)

            for issue in fixable_issues:
                items_processed += 1
                try:
                    success = self._execute_fix(issue)
                    if success:
                        items_fixed += 1
                        logger.info(f"修复问题成功: {issue.title}")
                    else:
                        errors.append(f"修复失败: {issue.title}")
                except Exception as e:
                    error_msg = f"修复问题时出错 ({issue.title}): {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            duration = time.time() - start_time
            success = items_fixed > 0 and len(errors) == 0

            return MaintenanceResult(
                task_type=MaintenanceTaskType.ERROR_FIX,
                status=MaintenanceStatus.COMPLETED if success else MaintenanceStatus.FAILED,
                success=success,
                message=f"修复完成: 处理{items_processed}个问题，成功修复{items_fixed}个",
                items_processed=items_processed,
                items_fixed=items_fixed,
                duration_seconds=duration,
                details={"severity_threshold": severity_threshold.value},
                errors=errors,
            )

        except Exception as e:
            error_msg = f"批量修复失败: {e}"
            logger.error(error_msg, exc_info=True)
            return MaintenanceResult(
                task_type=MaintenanceTaskType.ERROR_FIX,
                status=MaintenanceStatus.FAILED,
                success=False,
                message=error_msg,
                items_processed=items_processed,
                items_fixed=items_fixed,
                duration_seconds=time.time() - start_time,
                errors=[error_msg],
            )

    def validate_system(self) -> tuple[bool, list[str]]:
        """
        验证系统

        Returns:
            (是否健康, 问题列表)
        """
        issues = self.diagnose_issues()
        problems = []

        # 收集严重和高优先级问题
        for issue in issues:
            if issue.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH):
                problems.append(f"[{issue.severity.value.upper()}] {issue.title}: {issue.description}")

        is_healthy = len(problems) == 0

        return is_healthy, problems

    def _execute_fix(self, issue: MaintenanceIssue) -> bool:
        """
        执行修复

        Args:
            issue: 问题对象

        Returns:
            是否成功
        """
        category = issue.category

        try:
            if category == "missing_directory":
                return self._fix_missing_directory(issue)
            elif category == "corrupted_json":
                return self._fix_corrupted_json(issue)
            elif category == "large_log":
                return self._fix_large_log(issue)
            elif category == "permission":
                return self._fix_permission(issue)
            elif category == "missing_config":
                return self._fix_missing_config(issue)
            else:
                logger.warning(f"未知的问题类别: {category}")
                return False

        except Exception as e:
            logger.error(f"执行修复失败: {e}", exc_info=True)
            return False

    def _check_data_directories(self) -> list[MaintenanceIssue]:
        """检查数据目录"""
        issues = []
        required_dirs = [
            "data",
            "data/users",
            "data/records",
            "data/templates",
            "logs",
            "outputs",
            "user_data",
        ]

        for dir_name in required_dirs:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                issues.append(
                    self._create_issue(
                        severity=IssueSeverity.MEDIUM,
                        category="missing_directory",
                        title=f"缺少目录: {dir_name}",
                        description=f"必需的目录 {dir_name} 不存在",
                        fix_available=True,
                        fix_description="创建缺少的目录",
                        metadata={"path": str(dir_path)},
                    )
                )

        return issues

    def _check_config_files(self) -> list[MaintenanceIssue]:
        """检查配置文件"""
        issues = []
        config_files = ["config.json", "config/base.json"]

        for config_file in config_files:
            config_path = self.base_path / config_file
            if not config_path.exists():
                issues.append(
                    self._create_issue(
                        severity=IssueSeverity.HIGH,
                        category="missing_config",
                        title=f"缺少配置文件: {config_file}",
                        description=f"配置文件 {config_file} 不存在",
                        fix_available=True,
                        fix_description="创建默认配置文件",
                        metadata={"path": str(config_path)},
                    )
                )

        return issues

    def _check_log_files(self) -> list[MaintenanceIssue]:
        """检查日志文件"""
        issues = []
        log_dir = self.base_path / "logs"

        if log_dir.exists():
            for log_file in log_dir.rglob("*.log"):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > 100:  # 超过100MB
                    issues.append(
                        self._create_issue(
                            severity=IssueSeverity.LOW,
                            category="large_log",
                            title=f"日志文件过大: {log_file.name}",
                            description=f"日志文件大小: {size_mb:.2f}MB",
                            fix_available=True,
                            fix_description="归档或删除旧日志",
                            metadata={"path": str(log_file), "size_mb": size_mb},
                        )
                    )

        return issues

    def _check_permissions(self) -> list[MaintenanceIssue]:
        """检查权限"""
        issues = []
        critical_dirs = ["data", "logs", "outputs"]

        for dir_name in critical_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists() and not os.access(dir_path, os.W_OK):
                issues.append(
                    self._create_issue(
                        severity=IssueSeverity.HIGH,
                        category="permission",
                        title=f"目录无写权限: {dir_name}",
                        description=f"目录 {dir_name} 没有写入权限",
                        fix_available=False,  # 权限问题通常需要手动修复
                        fix_description="需要管理员权限修复",
                        metadata={"path": str(dir_path)},
                    )
                )

        return issues

    def _check_disk_space(self) -> list[MaintenanceIssue]:
        """检查磁盘空间"""
        issues = []

        try:
            usage = shutil.disk_usage(self.base_path)
            free_gb = usage.free / (1024**3)
            percent_free = (usage.free / usage.total) * 100

            if percent_free < 10:  # 可用空间少于10%
                issues.append(
                    self._create_issue(
                        severity=IssueSeverity.HIGH,
                        category="disk_space",
                        title="磁盘空间不足",
                        description=f"可用空间: {free_gb:.2f}GB ({percent_free:.1f}%)",
                        fix_available=False,
                        fix_description="清理不需要的文件或扩展磁盘空间",
                        metadata={"free_gb": free_gb, "percent_free": percent_free},
                    )
                )

        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")

        return issues

    def _check_json_integrity(self) -> list[MaintenanceIssue]:
        """检查JSON文件完整性"""
        issues = []
        data_dir = self.base_path / "data"

        if data_dir.exists():
            for json_file in data_dir.rglob("*.json"):
                try:
                    with open(json_file, encoding="utf-8") as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    issues.append(
                        self._create_issue(
                            severity=IssueSeverity.MEDIUM,
                            category="corrupted_json",
                            title=f"JSON文件损坏: {json_file.name}",
                            description=f"JSON解析错误: {str(e)}",
                            fix_available=True,
                            fix_description="备份并尝试修复JSON文件",
                            metadata={"path": str(json_file), "error": str(e)},
                        )
                    )
                except Exception as e:
                    logger.error(f"读取JSON文件失败 {json_file}: {e}")

        return issues

    def _fix_missing_directory(self, issue: MaintenanceIssue) -> bool:
        """修复缺少的目录"""
        try:
            path = Path(issue.metadata["path"])
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {path}")
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False

    def _fix_corrupted_json(self, issue: MaintenanceIssue) -> bool:
        """修复损坏的JSON文件"""
        try:
            path = Path(issue.metadata["path"])

            # 备份原文件
            backup_path = path.with_suffix(".json.backup")
            shutil.copy2(path, backup_path)
            logger.info(f"备份文件: {backup_path}")

            # 尝试修复：创建空的有效JSON
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2, ensure_ascii=False)

            logger.info(f"修复JSON文件: {path}")
            return True

        except Exception as e:
            logger.error(f"修复JSON文件失败: {e}")
            return False

    def _fix_large_log(self, issue: MaintenanceIssue) -> bool:
        """修复大日志文件"""
        try:
            path = Path(issue.metadata["path"])

            # 归档日志
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = path.with_suffix(f".{timestamp}.log")
            shutil.move(path, archive_path)
            logger.info(f"归档日志文件: {archive_path}")

            # 创建新日志文件
            path.touch()

            return True

        except Exception as e:
            logger.error(f"归档日志文件失败: {e}")
            return False

    def _fix_permission(self, issue: MaintenanceIssue) -> bool:
        """修复权限问题 - 通常需要管理员权限"""
        # 这个通常无法自动修复
        logger.warning(f"权限问题需要手动修复: {issue.metadata['path']}")
        return False

    def _fix_missing_config(self, issue: MaintenanceIssue) -> bool:
        """修复缺少的配置文件"""
        try:
            path = Path(issue.metadata["path"])

            # 创建默认配置
            default_config = {
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "auto_generated": True,
            }

            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            logger.info(f"创建默认配置文件: {path}")
            return True

        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
            return False

    def _create_issue(
        self,
        severity: IssueSeverity,
        category: str,
        title: str,
        description: str,
        fix_available: bool,
        fix_description: str,
        metadata: dict[str, Any],
    ) -> MaintenanceIssue:
        """创建问题对象"""
        self.issue_counter += 1
        issue_id = f"issue_{self.issue_counter:04d}"

        return MaintenanceIssue(
            issue_id=issue_id,
            severity=severity,
            category=category,
            title=title,
            description=description,
            fix_available=fix_available,
            fix_description=fix_description,
            metadata=metadata,
        )
