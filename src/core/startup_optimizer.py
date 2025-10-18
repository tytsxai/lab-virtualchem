"""
启动优化器
优化应用程序启动流程，减少启动时间
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ComponentPriority(str, Enum):
    """组件优先级"""

    CRITICAL = "critical"  # 关键组件，必须立即加载
    HIGH = "high"  # 高优先级组件
    MEDIUM = "medium"  # 中优先级组件
    LOW = "low"  # 低优先级组件
    DEFERRED = "deferred"  # 延迟加载组件


@dataclass
class StartupComponent:
    """启动组件"""

    name: str
    priority: ComponentPriority
    load_func: Callable[[], Any]
    dependencies: list[str]
    estimated_time_ms: int
    loaded: bool = False
    result: Any = None
    error: Exception | None = None


class StartupOptimizer:
    """启动优化器"""

    def __init__(self):
        self.components: dict[str, StartupComponent] = {}
        self.load_order: list[str] = []
        self.parallel_groups: list[list[str]] = []
        self.startup_metrics: dict[str, float] = {}

        # 优化设置
        self.max_parallel_workers = 4
        self.critical_timeout = 5.0  # 关键组件超时时间
        self.max_total_timeout = 30.0  # 总启动超时时间

        # 性能统计
        self.startup_start_time = 0.0
        self.startup_end_time = 0.0
        self.component_load_times: dict[str, float] = {}

        logger.info("启动优化器初始化完成")

    def register_component(
        self,
        name: str,
        priority: ComponentPriority,
        load_func: Callable[[], Any],
        dependencies: list[str] = None,
        estimated_time_ms: int = 100,
    ) -> None:
        """注册启动组件"""
        component = StartupComponent(
            name=name,
            priority=priority,
            load_func=load_func,
            dependencies=dependencies or [],
            estimated_time_ms=estimated_time_ms,
        )

        self.components[name] = component
        logger.debug(f"注册启动组件: {name} (优先级: {priority.value})")

    def optimize_startup_order(self) -> None:
        """优化启动顺序"""
        try:
            # 1. 拓扑排序确定依赖顺序
            self.load_order = self._topological_sort()

            # 2. 分组并行加载
            self.parallel_groups = self._create_parallel_groups()

            # 3. 优化关键路径
            self._optimize_critical_path()

            logger.info(f"启动顺序优化完成: {len(self.load_order)}个组件, {len(self.parallel_groups)}个并行组")

        except Exception as e:
            logger.error(f"优化启动顺序失败: {e}")
            # 使用简单的优先级排序作为后备方案
            self.load_order = sorted(self.components.keys(), key=lambda x: self.components[x].priority.value)
            self.parallel_groups = [[comp] for comp in self.load_order]

    def _topological_sort(self) -> list[str]:
        """拓扑排序确定依赖顺序"""
        visited = set()
        temp_visited = set()
        result = []

        def visit(component_name: str):
            if component_name in temp_visited:
                raise ValueError(f"循环依赖检测到: {component_name}")
            if component_name in visited:
                return

            temp_visited.add(component_name)

            # 访问依赖
            component = self.components.get(component_name)
            if component:
                for dep in component.dependencies:
                    if dep in self.components:
                        visit(dep)

            temp_visited.remove(component_name)
            visited.add(component_name)
            result.append(component_name)

        # 按优先级排序，优先级高的先处理
        priority_order = [
            ComponentPriority.CRITICAL,
            ComponentPriority.HIGH,
            ComponentPriority.MEDIUM,
            ComponentPriority.LOW,
            ComponentPriority.DEFERRED,
        ]

        for priority in priority_order:
            for name, component in self.components.items():
                if component.priority == priority and name not in visited:
                    visit(name)

        return result

    def _create_parallel_groups(self) -> list[list[str]]:
        """创建并行加载组"""
        groups = []
        current_group = []
        current_dependencies = set()

        for component_name in self.load_order:
            component = self.components[component_name]

            # 检查是否可以加入当前组
            can_parallelize = (
                len(current_group) < self.max_parallel_workers
                and not any(dep in current_group for dep in component.dependencies)
                and not any(component_name in self.components[dep].dependencies for dep in current_group)
            )

            if can_parallelize and component.priority != ComponentPriority.CRITICAL:
                current_group.append(component_name)
                current_dependencies.update(component.dependencies)
            else:
                # 开始新组
                if current_group:
                    groups.append(current_group)
                current_group = [component_name]
                current_dependencies = set(component.dependencies)

        if current_group:
            groups.append(current_group)

        return groups

    def _optimize_critical_path(self) -> None:
        """优化关键路径"""
        # 将关键组件移到最前面
        critical_components = [
            name for name, comp in self.components.items() if comp.priority == ComponentPriority.CRITICAL
        ]

        # 重新排列加载顺序
        new_order = []
        for name in self.load_order:
            if name not in critical_components:
                new_order.append(name)

        self.load_order = critical_components + new_order

    def execute_optimized_startup(self) -> dict[str, Any]:
        """执行优化的启动流程"""
        self.startup_start_time = time.time()

        try:
            logger.info("开始优化启动流程")

            # 1. 优化启动顺序
            self.optimize_startup_order()

            # 2. 执行并行加载
            results = self._execute_parallel_loading()

            # 3. 验证启动结果
            validation_result = self._validate_startup_results()

            # 4. 生成启动报告
            report = self._generate_startup_report(results, validation_result)

            self.startup_end_time = time.time()
            total_time = self.startup_end_time - self.startup_start_time

            logger.info(f"优化启动完成，总耗时: {total_time:.3f}秒")

            return {
                "success": True,
                "total_time": total_time,
                "components_loaded": len([c for c in self.components.values() if c.loaded]),
                "components_failed": len([c for c in self.components.values() if c.error]),
                "report": report,
                "metrics": self.startup_metrics,
            }

        except Exception as e:
            logger.error(f"优化启动失败: {e}")
            self.startup_end_time = time.time()
            return {
                "success": False,
                "error": str(e),
                "total_time": self.startup_end_time - self.startup_start_time,
                "components_loaded": len([c for c in self.components.values() if c.loaded]),
                "components_failed": len([c for c in self.components.values() if c.error]),
            }

    def _execute_parallel_loading(self) -> dict[str, Any]:
        """执行并行加载"""
        results = {"loaded": [], "failed": [], "skipped": []}

        for group in self.parallel_groups:
            if len(group) == 1:
                # 单组件加载
                result = self._load_single_component(group[0])
                if result["success"]:
                    results["loaded"].append(group[0])
                else:
                    results["failed"].append(group[0])
            else:
                # 并行加载
                group_results = self._load_parallel_group(group)
                results["loaded"].extend(group_results["loaded"])
                results["failed"].extend(group_results["failed"])

        return results

    def _load_single_component(self, component_name: str) -> dict[str, Any]:
        """加载单个组件"""
        start_time = time.time()

        try:
            component = self.components[component_name]

            # 检查依赖是否已加载
            for dep in component.dependencies:
                if dep not in self.components or not self.components[dep].loaded:
                    logger.warning(f"组件 {component_name} 的依赖 {dep} 未加载")
                    return {"success": False, "error": f"依赖 {dep} 未加载"}

            # 执行加载
            result = component.load_func()
            component.result = result
            component.loaded = True

            load_time = time.time() - start_time
            self.component_load_times[component_name] = load_time

            logger.debug(f"组件 {component_name} 加载成功，耗时: {load_time:.3f}秒")

            return {"success": True, "result": result, "load_time": load_time}

        except Exception as e:
            load_time = time.time() - start_time
            self.component_load_times[component_name] = load_time

            component = self.components[component_name]
            component.error = e
            component.loaded = False

            logger.error(f"组件 {component_name} 加载失败: {e}")

            return {"success": False, "error": str(e), "load_time": load_time}

    def _load_parallel_group(self, group: list[str]) -> dict[str, Any]:
        """并行加载组件组"""
        results = {"loaded": [], "failed": []}

        try:
            with ThreadPoolExecutor(max_workers=len(group)) as executor:
                # 提交加载任务
                future_to_component = {executor.submit(self._load_single_component, name): name for name in group}

                # 收集结果
                for future in as_completed(future_to_component):
                    component_name = future_to_component[future]
                    try:
                        result = future.result(timeout=self.critical_timeout)
                        if result["success"]:
                            results["loaded"].append(component_name)
                        else:
                            results["failed"].append(component_name)
                    except Exception as e:
                        logger.error(f"并行加载组件 {component_name} 失败: {e}")
                        results["failed"].append(component_name)

        except Exception as e:
            logger.error(f"并行加载组失败: {e}")
            # 回退到串行加载
            for component_name in group:
                result = self._load_single_component(component_name)
                if result["success"]:
                    results["loaded"].append(component_name)
                else:
                    results["failed"].append(component_name)

        return results

    def _validate_startup_results(self) -> dict[str, Any]:
        """验证启动结果"""
        validation = {
            "critical_loaded": True,
            "high_priority_loaded": True,
            "total_loaded": 0,
            "total_failed": 0,
            "errors": [],
        }

        for name, component in self.components.items():
            if component.loaded:
                validation["total_loaded"] += 1
            else:
                validation["total_failed"] += 1
                if component.error:
                    validation["errors"].append(f"{name}: {component.error}")

                # 检查关键组件
                if component.priority == ComponentPriority.CRITICAL:
                    validation["critical_loaded"] = False
                elif component.priority == ComponentPriority.HIGH:
                    validation["high_priority_loaded"] = False

        return validation

    def _generate_startup_report(self, results: dict[str, Any], validation: dict[str, Any]) -> str:
        """生成启动报告"""
        total_time = self.startup_end_time - self.startup_start_time

        report = f"""
# 启动优化报告

## 总体统计
- 总启动时间: {total_time:.3f}秒
- 成功加载组件: {len(results["loaded"])}
- 失败组件: {len(results["failed"])}
- 跳过组件: {len(results["skipped"])}

## 组件加载详情
"""

        # 按优先级分组显示
        for priority in ComponentPriority:
            priority_components = [name for name, comp in self.components.items() if comp.priority == priority]

            if priority_components:
                report += f"\n### {priority.value.upper()} 优先级组件\n"
                for name in priority_components:
                    component = self.components[name]
                    status = "✅ 成功" if component.loaded else "❌ 失败"
                    load_time = self.component_load_times.get(name, 0)
                    report += f"- {name}: {status} ({load_time:.3f}s)\n"

        # 性能分析
        report += "\n## 性能分析\n"
        if self.component_load_times:
            avg_load_time = sum(self.component_load_times.values()) / len(self.component_load_times)
            max_load_time = max(self.component_load_times.values())
            min_load_time = min(self.component_load_times.values())

            report += f"- 平均加载时间: {avg_load_time:.3f}秒\n"
            report += f"- 最长加载时间: {max_load_time:.3f}秒\n"
            report += f"- 最短加载时间: {min_load_time:.3f}秒\n"

        # 优化建议
        report += "\n## 优化建议\n"
        if total_time > 10:
            report += "- 启动时间较长，建议进一步优化\n"

        if not validation["critical_loaded"]:
            report += "- 关键组件加载失败，需要修复\n"

        if len(results["failed"]) > 0:
            report += f"- {len(results['failed'])}个组件加载失败，需要检查\n"

        return report

    def get_component_status(self, component_name: str) -> dict[str, Any] | None:
        """获取组件状态"""
        component = self.components.get(component_name)
        if not component:
            return None

        return {
            "name": component.name,
            "priority": component.priority.value,
            "loaded": component.loaded,
            "error": str(component.error) if component.error else None,
            "load_time": self.component_load_times.get(component_name, 0),
            "dependencies": component.dependencies,
        }

    def get_startup_metrics(self) -> dict[str, Any]:
        """获取启动指标"""
        total_time = self.startup_end_time - self.startup_start_time if self.startup_end_time > 0 else 0

        return {
            "total_startup_time": total_time,
            "components_total": len(self.components),
            "components_loaded": len([c for c in self.components.values() if c.loaded]),
            "components_failed": len([c for c in self.components.values() if c.error]),
            "parallel_groups": len(self.parallel_groups),
            "component_load_times": self.component_load_times.copy(),
            "startup_order": self.load_order.copy(),
        }

    def preload_resources(self, resource_paths: list[str]) -> None:
        """预加载资源"""
        try:
            logger.info(f"开始预加载 {len(resource_paths)} 个资源")

            def load_resource(path: str) -> bool:
                try:
                    # 这里应该实现具体的资源加载逻辑
                    # 比如加载图片、配置文件等
                    time.sleep(0.1)  # 模拟加载时间
                    return True
                except Exception as e:
                    logger.error(f"预加载资源失败 {path}: {e}")
                    return False

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(load_resource, path) for path in resource_paths]
                results = [future.result() for future in as_completed(futures)]

            success_count = sum(results)
            logger.info(f"资源预加载完成: {success_count}/{len(resource_paths)} 成功")

        except Exception as e:
            logger.error(f"预加载资源失败: {e}")


# 全局启动优化器实例
startup_optimizer = StartupOptimizer()
