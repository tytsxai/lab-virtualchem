"""
布局比例分析器
分析前端窗口和板块之间的比例设置，提供优化建议

功能特性:
1. 实时布局比例分析
2. 响应式设计验证
3. 用户体验评估
4. 性能优化建议
5. 用户偏好管理
6. 可视化报告生成
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil  # type: ignore
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


class LayoutRatioAnalyzer(QObject):
    """布局比例分析器"""

    # 分析完成信号
    analysis_completed = Signal(dict)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 当前布局比例配置
        self._current_ratios: dict[str, dict[str, Any]] = {}

        # 布局历史记录
        self._layout_history: list[dict[str, Any]] = []
        self._max_history_size = 100

        # 用户偏好设置
        self._user_preferences: dict[str, Any] = {}
        self._preferences_file = Path("user_data/layout_preferences.json")

        # 性能监控数据
        self._performance_metrics: dict[str, list[float]] = {"render_time": [], "layout_time": [], "memory_usage": []}

        # 推荐的布局比例
        self._recommended_ratios = {
            "main_window": {
                "experiment_list": 1,
                "content_area": 4,
                "description": "主窗口：实验列表1份，内容区域4份",
                "golden_ratio": True,
                "accessibility_score": 8.5,
            },
            "experiment_view": {
                "interactive_scene": 2,
                "step_content": 1,
                "description": "实验视图：交互场景2份，步骤内容1份",
                "golden_ratio": True,
                "accessibility_score": 9.0,
            },
            "record_browser": {
                "record_list": 3,
                "detail_panel": 2,
                "description": "记录浏览器：记录列表3份，详情面板2份",
                "golden_ratio": False,
                "accessibility_score": 8.0,
            },
            "mistake_viewer": {
                "mistake_list": 2,
                "detail_panel": 1,
                "description": "错题查看器：错题列表2份，详情面板1份",
                "golden_ratio": False,
                "accessibility_score": 8.5,
            },
            "knowledge_browser": {
                "knowledge_tree": 300,
                "detail_browser": 600,
                "description": "知识浏览器：知识树300px，详情浏览器600px",
                "golden_ratio": True,
                "accessibility_score": 9.0,
            },
            "game_experiment_view": {
                "game_area": 3,
                "control_panel": 1,
                "description": "游戏实验视图：游戏区域3份，控制面板1份",
                "golden_ratio": True,
                "accessibility_score": 8.0,
            },
        }

        # 屏幕尺寸相关的比例调整
        self._screen_size_adjustments = {
            "mobile": {
                "main_window": {"experiment_list": 0, "content_area": 1},
                "description": "移动端：隐藏实验列表，全屏显示内容",
                "min_width": 320,
                "max_width": 767,
            },
            "tablet": {
                "main_window": {"experiment_list": 1, "content_area": 3},
                "description": "平板端：实验列表1份，内容区域3份",
                "min_width": 768,
                "max_width": 1023,
            },
            "desktop": {
                "main_window": {"experiment_list": 1, "content_area": 4},
                "description": "桌面端：实验列表1份，内容区域4份",
                "min_width": 1024,
                "max_width": 1919,
            },
            "large_desktop": {
                "main_window": {"experiment_list": 1, "content_area": 5},
                "description": "大屏桌面：实验列表1份，内容区域5份",
                "min_width": 1920,
                "max_width": 9999,
            },
        }

        # 初始化用户偏好
        self._load_user_preferences()

        # 性能监控定时器
        self._performance_timer = QTimer(self)
        self._performance_timer.timeout.connect(self._collect_performance_metrics)
        self._performance_timer.start(5000)  # 每5秒收集一次性能数据

    def analyze_current_layouts(self) -> dict[str, Any]:
        """分析当前布局比例"""
        try:
            start_time = datetime.now()

            analysis_result = {
                "timestamp": self._get_timestamp(),
                "screen_info": self._get_screen_info(),
                "current_ratios": self._current_ratios.copy(),
                "recommendations": [],
                "issues": [],
                "optimization_suggestions": [],
                "performance_metrics": self._get_performance_summary(),
                "user_preferences": self._user_preferences.copy(),
                "accessibility_score": 0.0,
                "golden_ratio_compliance": 0.0,
                "responsive_score": 0.0,
            }

            # 分析主窗口比例
            self._analyze_main_window_ratio(analysis_result)

            # 分析各个对话框比例
            self._analyze_dialog_ratios(analysis_result)

            # 计算综合评分
            self._calculate_comprehensive_scores(analysis_result)

            # 生成优化建议
            self._generate_optimization_suggestions(analysis_result)

            # 记录分析历史
            self._record_analysis_history(analysis_result)

            # 计算分析耗时
            analysis_time = (datetime.now() - start_time).total_seconds()
            analysis_result["analysis_time"] = analysis_time

            logger.info(f"布局比例分析完成，耗时: {analysis_time:.3f}秒")
            self.analysis_completed.emit(analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"布局比例分析失败: {e}", exc_info=True)
            return {}

    def _analyze_main_window_ratio(self, result: dict[str, Any]) -> None:
        """分析主窗口比例"""
        try:
            # 主窗口当前比例：实验列表1份，内容区域4份
            current_ratio = {"experiment_list": 1, "content_area": 4}
            recommended_ratio = self._recommended_ratios["main_window"]

            # 检查比例是否合理
            if current_ratio == recommended_ratio:
                result["recommendations"].append(
                    {"component": "main_window", "status": "optimal", "message": "主窗口比例设置合理"}
                )
            else:
                result["issues"].append(
                    {
                        "component": "main_window",
                        "issue": "比例不匹配",
                        "current": current_ratio,
                        "recommended": recommended_ratio,
                    }
                )

        except Exception as e:
            logger.error(f"分析主窗口比例失败: {e}", exc_info=True)

    def _analyze_dialog_ratios(self, result: dict[str, Any]) -> None:
        """分析对话框比例"""
        try:
            # 记录浏览器比例
            record_browser_ratio = {"record_list": 3, "detail_panel": 2}
            if record_browser_ratio == self._recommended_ratios["record_browser"]:
                result["recommendations"].append(
                    {"component": "record_browser", "status": "optimal", "message": "记录浏览器比例设置合理"}
                )
            else:
                result["issues"].append(
                    {
                        "component": "record_browser",
                        "issue": "比例不匹配",
                        "current": record_browser_ratio,
                        "recommended": self._recommended_ratios["record_browser"],
                    }
                )

            # 错题查看器比例
            mistake_viewer_ratio = {"mistake_list": 2, "detail_panel": 1}
            if mistake_viewer_ratio == self._recommended_ratios["mistake_viewer"]:
                result["recommendations"].append(
                    {"component": "mistake_viewer", "status": "optimal", "message": "错题查看器比例设置合理"}
                )
            else:
                result["issues"].append(
                    {
                        "component": "mistake_viewer",
                        "issue": "比例不匹配",
                        "current": mistake_viewer_ratio,
                        "recommended": self._recommended_ratios["mistake_viewer"],
                    }
                )

            # 知识浏览器比例
            knowledge_browser_ratio = {"knowledge_tree": 300, "detail_browser": 600}
            if knowledge_browser_ratio == self._recommended_ratios["knowledge_browser"]:
                result["recommendations"].append(
                    {"component": "knowledge_browser", "status": "optimal", "message": "知识浏览器比例设置合理"}
                )
            else:
                result["issues"].append(
                    {
                        "component": "knowledge_browser",
                        "issue": "比例不匹配",
                        "current": knowledge_browser_ratio,
                        "recommended": self._recommended_ratios["knowledge_browser"],
                    }
                )

        except Exception as e:
            logger.error(f"分析对话框比例失败: {e}", exc_info=True)

    def _generate_optimization_suggestions(self, result: dict[str, Any]) -> None:
        """生成优化建议"""
        try:
            screen_info = result["screen_info"]
            screen_type = screen_info["size_type"]

            # 根据屏幕类型生成建议
            if screen_type in self._screen_size_adjustments:
                adjustment = self._screen_size_adjustments[screen_type]
                result["optimization_suggestions"].append(
                    {
                        "type": "screen_adaptation",
                        "screen_type": screen_type,
                        "suggestion": adjustment["description"],
                        "ratios": adjustment,
                    }
                )

            # 通用优化建议
            result["optimization_suggestions"].extend(
                [
                    {
                        "type": "responsive_design",
                        "suggestion": "实现响应式布局，根据屏幕尺寸自动调整比例",
                        "priority": "high",
                    },
                    {
                        "type": "user_preference",
                        "suggestion": "允许用户自定义布局比例，保存个人偏好",
                        "priority": "medium",
                    },
                    {
                        "type": "accessibility",
                        "suggestion": "考虑无障碍访问需求，提供更大的点击区域",
                        "priority": "medium",
                    },
                    {"type": "performance", "suggestion": "优化布局渲染性能，减少不必要的重绘", "priority": "low"},
                ]
            )

        except Exception as e:
            logger.error(f"生成优化建议失败: {e}", exc_info=True)

    def _get_screen_info(self) -> dict[str, Any]:
        """获取屏幕信息"""
        try:
            app = QApplication.instance()
            if not app:
                return {"width": 1920, "height": 1080, "dpi": 96, "size_type": "desktop"}

            screen = QApplication.primaryScreen()
            if not screen:
                return {"width": 1920, "height": 1080, "dpi": 96, "size_type": "desktop"}

            width = screen.size().width()
            height = screen.size().height()
            dpi = screen.logicalDotsPerInch()

            # 确定屏幕类型
            if width < 768:
                size_type = "mobile"
            elif width < 1024:
                size_type = "tablet"
            elif width < 1920:
                size_type = "desktop"
            else:
                size_type = "large_desktop"

            return {"width": width, "height": height, "dpi": dpi, "size_type": size_type}

        except Exception as e:
            logger.error(f"获取屏幕信息失败: {e}", exc_info=True)
            return {"width": 1920, "height": 1080, "dpi": 96, "size_type": "desktop"}

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def get_recommended_ratio(self, component: str) -> dict[str, Any]:
        """获取推荐比例"""
        return self._recommended_ratios.get(component, {})

    def get_screen_adjustment(self, screen_type: str) -> dict[str, Any]:
        """获取屏幕调整建议"""
        return self._screen_size_adjustments.get(screen_type, {})

    def validate_ratio(self, component: str, ratio: dict[str, Any]) -> bool:
        """验证比例是否合理"""
        try:
            recommended = self._recommended_ratios.get(component, {})
            if not recommended:
                return True

            # 检查比例是否在合理范围内
            for key, value in ratio.items():
                if key in recommended:
                    recommended_value = recommended[key]
                    if isinstance(recommended_value, int) and isinstance(value, int):
                        # 允许20%的偏差
                        tolerance = recommended_value * 0.2
                        if abs(value - recommended_value) > tolerance:
                            return False

            return True

        except Exception as e:
            logger.error(f"验证比例失败: {e}", exc_info=True)
            return False

    def optimize_ratio_for_screen(self, component: str, screen_type: str) -> dict[str, Any]:
        """根据屏幕类型优化比例"""
        try:
            base_ratio = self._recommended_ratios.get(component, {})
            screen_adjustment = self._screen_size_adjustments.get(screen_type, {})

            if not base_ratio or not screen_adjustment:
                return base_ratio

            # 应用屏幕调整
            optimized_ratio = base_ratio.copy()
            if component in screen_adjustment:
                component_adjustment = screen_adjustment[component]
                if isinstance(component_adjustment, dict):
                    optimized_ratio.update(component_adjustment)

            return optimized_ratio

        except Exception as e:
            logger.error(f"优化比例失败: {e}", exc_info=True)
            return {}

    def _load_user_preferences(self) -> None:
        """加载用户偏好设置"""
        try:
            if self._preferences_file.exists():
                with open(self._preferences_file, encoding="utf-8") as f:
                    self._user_preferences = json.load(f)
                logger.info("用户布局偏好已加载")
            else:
                self._user_preferences = {
                    "layout_ratios": {},
                    "screen_preferences": {},
                    "accessibility_settings": {},
                    "performance_settings": {},
                }
                self._save_user_preferences()
        except Exception as e:
            logger.error(f"加载用户偏好失败: {e}", exc_info=True)
            self._user_preferences = {}

    def _save_user_preferences(self) -> None:
        """保存用户偏好设置"""
        try:
            self._preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._preferences_file, "w", encoding="utf-8") as f:
                json.dump(self._user_preferences, f, ensure_ascii=False, indent=2)
            logger.info("用户布局偏好已保存")
        except Exception as e:
            logger.error(f"保存用户偏好失败: {e}", exc_info=True)

    def _collect_performance_metrics(self) -> None:
        """收集性能指标"""
        try:
            import time

            # 收集内存使用
            memory_percent = psutil.virtual_memory().percent
            self._performance_metrics["memory_usage"].append(memory_percent)

            # 收集CPU使用
            _ = psutil.cpu_percent(interval=0.1)

            # 模拟布局渲染时间
            start_time = time.time()
            # 这里可以添加实际的布局计算
            render_time = (time.time() - start_time) * 1000  # 转换为毫秒
            self._performance_metrics["render_time"].append(render_time)

            # 保持历史记录在合理范围内
            for key in self._performance_metrics:
                if len(self._performance_metrics[key]) > 100:
                    self._performance_metrics[key] = self._performance_metrics[key][-100:]

        except Exception as e:
            logger.error(f"收集性能指标失败: {e}", exc_info=True)

    def _get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        try:
            summary = {}
            for key, values in self._performance_metrics.items():
                if values:
                    summary[key] = {
                        "current": values[-1],
                        "average": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                    }
                else:
                    summary[key] = {"current": 0, "average": 0, "min": 0, "max": 0, "count": 0}
            return summary
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}", exc_info=True)
            return {}

    def _calculate_comprehensive_scores(self, result: dict[str, Any]) -> None:
        """计算综合评分"""
        try:
            # 计算无障碍访问评分
            accessibility_scores: list[float] = []
            for ratio_info in self._recommended_ratios.values():
                if "accessibility_score" in ratio_info:
                    score: Any = ratio_info["accessibility_score"]
                    if isinstance(score, (int, float)):
                        accessibility_scores.append(float(score))

            if accessibility_scores:
                result["accessibility_score"] = sum(accessibility_scores) / len(accessibility_scores)

            # 计算黄金比例合规性
            golden_ratio_count = 0
            total_components = 0
            for _, ratio_info in self._recommended_ratios.items():
                if "golden_ratio" in ratio_info:
                    total_components += 1
                    if ratio_info["golden_ratio"]:
                        golden_ratio_count += 1

            if total_components > 0:
                result["golden_ratio_compliance"] = (golden_ratio_count / total_components) * 100

            # 计算响应式设计评分
            screen_info = result["screen_info"]
            screen_type = screen_info["size_type"]
            if screen_type in self._screen_size_adjustments:
                result["responsive_score"] = 90.0  # 基础分数
                # 根据屏幕尺寸调整分数
                width = screen_info["width"]
                if width < 768:
                    result["responsive_score"] += 5  # 移动端优化加分
                elif width > 1920:
                    result["responsive_score"] += 10  # 大屏优化加分
            else:
                result["responsive_score"] = 70.0  # 默认分数

        except Exception as e:
            logger.error(f"计算综合评分失败: {e}", exc_info=True)

    def _record_analysis_history(self, result: dict[str, Any]) -> None:
        """记录分析历史"""
        try:
            history_entry = {
                "timestamp": result["timestamp"],
                "screen_type": result["screen_info"]["size_type"],
                "accessibility_score": result["accessibility_score"],
                "golden_ratio_compliance": result["golden_ratio_compliance"],
                "responsive_score": result["responsive_score"],
                "issues_count": len(result["issues"]),
                "recommendations_count": len(result["recommendations"]),
            }

            self._layout_history.append(history_entry)

            # 保持历史记录在合理范围内
            if len(self._layout_history) > self._max_history_size:
                self._layout_history = self._layout_history[-self._max_history_size :]

        except Exception as e:
            logger.error(f"记录分析历史失败: {e}", exc_info=True)

    def get_layout_history(self) -> list[dict[str, Any]]:
        """获取布局历史"""
        return self._layout_history.copy()

    def get_user_preferences(self) -> dict[str, Any]:
        """获取用户偏好"""
        return self._user_preferences.copy()

    def set_user_preference(self, key: str, value: Any) -> None:
        """设置用户偏好"""
        try:
            self._user_preferences[key] = value
            self._save_user_preferences()
            logger.info(f"用户偏好已更新: {key}")
        except Exception as e:
            logger.error(f"设置用户偏好失败: {e}", exc_info=True)

    def export_analysis_report(self, file_path: str) -> bool:
        """导出分析报告"""
        try:
            analysis_result = self.analyze_current_layouts()

            report = {
                "report_info": {
                    "generated_at": analysis_result["timestamp"],
                    "version": "1.0.0",
                    "analyzer": "LayoutRatioAnalyzer",
                },
                "summary": {
                    "accessibility_score": analysis_result["accessibility_score"],
                    "golden_ratio_compliance": analysis_result["golden_ratio_compliance"],
                    "responsive_score": analysis_result["responsive_score"],
                    "total_issues": len(analysis_result["issues"]),
                    "total_recommendations": len(analysis_result["recommendations"]),
                },
                "detailed_analysis": analysis_result,
                "layout_history": self._layout_history,
                "performance_metrics": analysis_result["performance_metrics"],
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"分析报告已导出: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出分析报告失败: {e}", exc_info=True)
            return False


class LayoutRatioOptimizer:
    """布局比例优化器"""

    def __init__(self) -> None:
        self.analyzer = LayoutRatioAnalyzer()
        self._optimization_cache: dict[str, dict[str, Any]] = {}

    def optimize_main_window_layout(self, main_window: QWidget) -> bool:
        """优化主窗口布局"""
        try:
            # 获取屏幕信息
            screen_info = self.analyzer._get_screen_info()
            screen_type = screen_info["size_type"]

            # 获取优化后的比例
            optimized_ratio = self.analyzer.optimize_ratio_for_screen("main_window", screen_type)

            if optimized_ratio:
                # 应用优化后的比例到实际的分割器
                self._apply_ratio_to_splitter(main_window, optimized_ratio)

                # 缓存优化结果
                self._optimization_cache["main_window"] = {
                    "screen_type": screen_type,
                    "ratio": optimized_ratio,
                    "timestamp": datetime.now().isoformat(),
                }

                logger.info(f"主窗口布局已优化: {screen_type}, 比例: {optimized_ratio}")
                return True

            return False

        except Exception as e:
            logger.error(f"优化主窗口布局失败: {e}", exc_info=True)
            return False

    def optimize_dialog_layout(self, dialog: QWidget, dialog_type: str) -> bool:
        """优化对话框布局"""
        try:
            # 获取屏幕信息
            screen_info = self.analyzer._get_screen_info()
            screen_type = screen_info["size_type"]

            # 获取优化后的比例
            optimized_ratio = self.analyzer.optimize_ratio_for_screen(dialog_type, screen_type)

            if optimized_ratio:
                # 应用优化后的比例到实际的分割器
                self._apply_ratio_to_splitter(dialog, optimized_ratio)

                # 缓存优化结果
                self._optimization_cache[dialog_type] = {
                    "screen_type": screen_type,
                    "ratio": optimized_ratio,
                    "timestamp": datetime.now().isoformat(),
                }

                logger.info(f"对话框布局已优化: {dialog_type}, 比例: {optimized_ratio}")
                return True

            return False

        except Exception as e:
            logger.error(f"优化对话框布局失败: {e}", exc_info=True)
            return False

    def _apply_ratio_to_splitter(self, widget: QWidget, ratio: dict[str, Any]) -> None:
        """将比例应用到分割器"""
        try:
            from PySide6.QtWidgets import QSplitter

            # 查找分割器
            splitters = widget.findChildren(QSplitter)
            if not splitters:
                logger.warning("未找到分割器组件")
                return

            # 应用比例到第一个分割器
            splitter = splitters[0]

            # 根据比例类型应用设置
            if "experiment_list" in ratio and "content_area" in ratio:
                # 主窗口比例
                splitter.setStretchFactor(0, ratio["experiment_list"])
                splitter.setStretchFactor(1, ratio["content_area"])
            elif "record_list" in ratio and "detail_panel" in ratio:
                # 记录浏览器比例
                splitter.setStretchFactor(0, ratio["record_list"])
                splitter.setStretchFactor(1, ratio["detail_panel"])
            elif "mistake_list" in ratio and "detail_panel" in ratio:
                # 错题查看器比例
                splitter.setStretchFactor(0, ratio["mistake_list"])
                splitter.setStretchFactor(1, ratio["detail_panel"])
            elif "knowledge_tree" in ratio and "detail_browser" in ratio:
                # 知识浏览器比例（使用固定像素）
                splitter.setSizes([ratio["knowledge_tree"], ratio["detail_browser"]])
            elif "game_area" in ratio and "control_panel" in ratio:
                # 游戏实验视图比例
                splitter.setStretchFactor(0, ratio["game_area"])
                splitter.setStretchFactor(1, ratio["control_panel"])

        except Exception as e:
            logger.error(f"应用比例到分割器失败: {e}", exc_info=True)

    def get_layout_report(self) -> dict[str, Any]:
        """获取布局报告"""
        return self.analyzer.analyze_current_layouts()

    def get_optimization_cache(self) -> dict[str, dict[str, Any]]:
        """获取优化缓存"""
        return self._optimization_cache.copy()

    def clear_optimization_cache(self) -> None:
        """清除优化缓存"""
        self._optimization_cache.clear()
        logger.info("优化缓存已清除")

    def batch_optimize_layouts(self, widgets: list[tuple[QWidget, str]]) -> dict[str, bool]:
        """批量优化布局"""
        results = {}
        for widget, widget_type in widgets:
            try:
                if widget_type == "main_window":
                    results[widget_type] = self.optimize_main_window_layout(widget)
                else:
                    results[widget_type] = self.optimize_dialog_layout(widget, widget_type)
            except Exception as e:
                logger.error(f"批量优化失败 {widget_type}: {e}", exc_info=True)
                results[widget_type] = False
        return results

    def validate_optimization(self, widget_type: str) -> bool:
        """验证优化结果"""
        try:
            if widget_type not in self._optimization_cache:
                return False

            cached_result = self._optimization_cache[widget_type]
            current_screen_info = self.analyzer._get_screen_info()

            # 检查屏幕类型是否匹配
            if cached_result["screen_type"] != current_screen_info["size_type"]:
                logger.info(f"屏幕类型已变化，需要重新优化: {widget_type}")
                return False

            return True

        except Exception as e:
            logger.error(f"验证优化结果失败: {e}", exc_info=True)
            return False


# 全局布局比例分析器实例
_global_layout_analyzer: LayoutRatioAnalyzer | None = None
_global_layout_optimizer: LayoutRatioOptimizer | None = None


def get_layout_analyzer() -> LayoutRatioAnalyzer:
    """获取全局布局比例分析器实例"""
    global _global_layout_analyzer
    if _global_layout_analyzer is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        _global_layout_analyzer = LayoutRatioAnalyzer(app) if app else LayoutRatioAnalyzer()
    return _global_layout_analyzer


def get_layout_optimizer() -> "LayoutRatioOptimizer":
    """获取全局布局比例优化器实例"""
    global _global_layout_optimizer
    if _global_layout_optimizer is None:
        _global_layout_optimizer = LayoutRatioOptimizer()
    return _global_layout_optimizer


def analyze_layout_ratios() -> dict[str, Any]:
    """分析布局比例"""
    analyzer = get_layout_analyzer()
    return analyzer.analyze_current_layouts()


def optimize_layout_for_screen(component: str, screen_type: str) -> dict[str, Any]:
    """根据屏幕类型优化布局"""
    analyzer = get_layout_analyzer()
    return analyzer.optimize_ratio_for_screen(component, screen_type)


def optimize_main_window_layout(main_window: QWidget) -> bool:
    """优化主窗口布局"""
    optimizer = get_layout_optimizer()
    return optimizer.optimize_main_window_layout(main_window)


def optimize_dialog_layout(dialog: QWidget, dialog_type: str) -> bool:
    """优化对话框布局"""
    optimizer = get_layout_optimizer()
    return optimizer.optimize_dialog_layout(dialog, dialog_type)


def export_layout_analysis_report(file_path: str) -> bool:
    """导出布局分析报告"""
    analyzer = get_layout_analyzer()
    return analyzer.export_analysis_report(file_path)


def get_layout_performance_summary() -> dict[str, Any]:
    """获取布局性能摘要"""
    analyzer = get_layout_analyzer()
    return analyzer._get_performance_summary()


def set_user_layout_preference(key: str, value: Any) -> None:
    """设置用户布局偏好"""
    analyzer = get_layout_analyzer()
    analyzer.set_user_preference(key, value)


def get_user_layout_preferences() -> dict[str, Any]:
    """获取用户布局偏好"""
    analyzer = get_layout_analyzer()
    return analyzer.get_user_preferences()


def validate_layout_ratio(component: str, ratio: dict[str, Any]) -> bool:
    """验证布局比例"""
    analyzer = get_layout_analyzer()
    return analyzer.validate_ratio(component, ratio)


def get_layout_history() -> list[dict[str, Any]]:
    """获取布局历史"""
    analyzer = get_layout_analyzer()
    return analyzer.get_layout_history()


def batch_optimize_all_layouts(widgets: list[tuple[QWidget, str]]) -> dict[str, bool]:
    """批量优化所有布局"""
    optimizer = get_layout_optimizer()
    return optimizer.batch_optimize_layouts(widgets)


def clear_layout_optimization_cache() -> None:
    """清除布局优化缓存"""
    optimizer = get_layout_optimizer()
    optimizer.clear_optimization_cache()


def get_layout_optimization_cache() -> dict[str, dict[str, Any]]:
    """获取布局优化缓存"""
    optimizer = get_layout_optimizer()
    return optimizer.get_optimization_cache()


def validate_layout_optimization(widget_type: str) -> bool:
    """验证布局优化结果"""
    optimizer = get_layout_optimizer()
    return optimizer.validate_optimization(widget_type)
