"""
BFF层 (Backend For Frontend)
聚合多个后端接口，减少前端请求次数
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResponse:
    """聚合响应"""

    success: bool
    data: dict[str, Any]
    errors: list[str] = None
    execution_time: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ServiceAggregator:
    """服务聚合器 - 聚合多个后端服务"""

    def __init__(self):
        self._services: dict[str, Callable] = {}

    def register_service(self, name: str, service: Callable) -> None:
        """
        注册服务

        Args:
            name: 服务名称
            service: 服务函数
        """
        self._services[name] = service
        logger.info(f"注册服务: {name}")

    async def aggregate(self, requests: dict[str, dict[str, Any]], parallel: bool = True) -> AggregatedResponse:
        """
        聚合多个服务请求

        Args:
            requests: 请求字典 {service_name: params}
            parallel: 是否并行执行

        Returns:
            聚合响应
        """
        import time

        start_time = time.time()

        results = {}
        errors = []

        try:
            if parallel:
                # 并行执行所有服务
                tasks = []
                for service_name, params in requests.items():
                    if service_name in self._services:
                        service = self._services[service_name]
                        tasks.append(self._call_service(service_name, service, params))
                    else:
                        errors.append(f"未知服务: {service_name}")

                # 等待所有任务完成
                task_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 收集结果
                for service_name, result in zip(requests.keys(), task_results, strict=False):
                    if isinstance(result, Exception):
                        errors.append(f"{service_name}: {str(result)}")
                        results[service_name] = None
                    else:
                        results[service_name] = result
            else:
                # 顺序执行
                for service_name, params in requests.items():
                    if service_name in self._services:
                        try:
                            service = self._services[service_name]
                            result = await self._call_service(service_name, service, params)
                            results[service_name] = result
                        except Exception as e:
                            errors.append(f"{service_name}: {str(e)}")
                            results[service_name] = None
                    else:
                        errors.append(f"未知服务: {service_name}")

            execution_time = time.time() - start_time

            return AggregatedResponse(
                success=len(errors) == 0, data=results, errors=errors, execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"聚合请求失败: {e}", exc_info=True)
            return AggregatedResponse(success=False, data={}, errors=[str(e)], execution_time=time.time() - start_time)

    async def _call_service(self, name: str, service: Callable, params: dict[str, Any]) -> Any:
        """
        调用服务

        Args:
            name: 服务名称
            service: 服务函数
            params: 参数

        Returns:
            服务响应
        """
        logger.debug(f"调用服务: {name}")

        # 判断是否为异步函数
        if asyncio.iscoroutinefunction(service):
            return await service(**params)
        else:
            # 在线程池中执行同步函数
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: service(**params))


class BFFEndpoint:
    """BFF端点 - 为特定前端页面提供定制接口"""

    def __init__(self, aggregator: ServiceAggregator):
        self.aggregator = aggregator

    async def get_experiment_page_data(self, experiment_id: str) -> dict[str, Any]:
        """
        获取实验页面所需的所有数据

        Args:
            experiment_id: 实验ID

        Returns:
            页面数据
        """
        # 聚合多个服务请求
        requests = {
            "experiment": {"id": experiment_id},
            "user_record": {"experiment_id": experiment_id},
            "knowledge_cards": {"experiment_id": experiment_id},
            "related_experiments": {"experiment_id": experiment_id},
        }

        response = await self.aggregator.aggregate(requests, parallel=True)

        if response.success:
            return {
                "experiment": response.data.get("experiment"),
                "record": response.data.get("user_record"),
                "knowledge": response.data.get("knowledge_cards"),
                "related": response.data.get("related_experiments"),
                "meta": {"execution_time": response.execution_time},
            }
        else:
            raise Exception(f"聚合失败: {response.errors}")

    async def get_dashboard_data(self, user_id: str) -> dict[str, Any]:
        """
        获取仪表板数据

        Args:
            user_id: 用户ID

        Returns:
            仪表板数据
        """
        requests = {
            "user_profile": {"user_id": user_id},
            "recent_experiments": {"user_id": user_id, "limit": 10},
            "statistics": {"user_id": user_id},
            "achievements": {"user_id": user_id},
        }

        response = await self.aggregator.aggregate(requests, parallel=True)

        return {
            "profile": response.data.get("user_profile"),
            "recent": response.data.get("recent_experiments"),
            "stats": response.data.get("statistics"),
            "achievements": response.data.get("achievements"),
        }


class ResponseTransformer:
    """响应转换器 - 将后端数据转换为前端需要的格式"""

    @staticmethod
    def transform_experiment(raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        转换实验数据

        Args:
            raw_data: 原始数据

        Returns:
            转换后的数据
        """
        return {
            "id": raw_data.get("id"),
            "title": raw_data.get("name"),
            "description": raw_data.get("desc"),
            "difficulty": raw_data.get("difficulty", "medium"),
            "steps": ResponseTransformer._transform_steps(raw_data.get("steps", [])),
            "metadata": {
                "duration": raw_data.get("estimated_time"),
                "category": raw_data.get("category"),
            },
        }

    @staticmethod
    def _transform_steps(steps: list[dict]) -> list[dict]:
        """转换步骤数据"""
        return [
            {
                "id": step.get("id"),
                "title": step.get("title"),
                "description": step.get("description"),
                "type": step.get("checkpoint_type"),
            }
            for step in steps
        ]

    @staticmethod
    def transform_list(items: list[dict], transformer: Callable) -> list[dict]:
        """
        批量转换

        Args:
            items: 项列表
            transformer: 转换函数

        Returns:
            转换后的列表
        """
        return [transformer(item) for item in items]


class DataPrefetcher:
    """数据预取器 - 预测并预加载数据"""

    def __init__(self, cache):
        """
        初始化预取器

        Args:
            cache: 缓存实例
        """
        self.cache = cache
        self._prefetch_rules: dict[str, Callable] = {}

    def register_rule(self, trigger: str, prefetch_func: Callable) -> None:
        """
        注册预取规则

        Args:
            trigger: 触发条件
            prefetch_func: 预取函数
        """
        self._prefetch_rules[trigger] = prefetch_func

    async def trigger_prefetch(self, trigger: str, context: dict[str, Any]) -> None:
        """
        触发预取

        Args:
            trigger: 触发条件
            context: 上下文
        """
        if trigger in self._prefetch_rules:
            prefetch_func = self._prefetch_rules[trigger]

            # 后台执行预取
            asyncio.create_task(self._execute_prefetch(prefetch_func, context))

    async def _execute_prefetch(self, prefetch_func: Callable, context: dict[str, Any]) -> None:
        """
        执行预取

        Args:
            prefetch_func: 预取函数
            context: 上下文
        """
        try:
            data = await prefetch_func(context)
            # 存入缓存
            if data and "cache_key" in context:
                self.cache.set(context["cache_key"], data)
                logger.info(f"预取完成: {context.get('cache_key')}")
        except Exception as e:
            logger.error(f"预取失败: {e}")


class BFFRouter:
    """BFF路由器 - 路由前端请求到合适的BFF端点"""

    def __init__(self):
        self._routes: dict[str, Callable] = {}

    def route(self, path: str):
        """
        路由装饰器

        Args:
            path: 路由路径
        """

        def decorator(func):
            self._routes[path] = func

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    async def handle_request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        处理请求

        Args:
            path: 请求路径
            params: 请求参数

        Returns:
            响应数据
        """
        if path in self._routes:
            handler = self._routes[path]
            return await handler(**params)
        else:
            raise ValueError(f"未知路由: {path}")


# 全局BFF组件
_aggregator: ServiceAggregator | None = None
_bff_endpoint: BFFEndpoint | None = None
_router: BFFRouter | None = None


def get_aggregator() -> ServiceAggregator:
    """获取全局服务聚合器"""
    global _aggregator
    if _aggregator is None:
        _aggregator = ServiceAggregator()
    return _aggregator


def get_bff_endpoint() -> BFFEndpoint:
    """获取全局BFF端点"""
    global _bff_endpoint
    if _bff_endpoint is None:
        _bff_endpoint = BFFEndpoint(get_aggregator())
    return _bff_endpoint


def get_router() -> BFFRouter:
    """获取全局路由器"""
    global _router
    if _router is None:
        _router = BFFRouter()
    return _router


if __name__ == "__main__":
    # 演示使用
    async def demo():
        logger.info("=== BFF层演示 ===\n")

        # 创建聚合器
        aggregator = ServiceAggregator()

        # 注册模拟服务
        async def get_experiment(id: str):
            await asyncio.sleep(0.1)
            return {"id": id, "name": f"实验{id}"}

        async def get_user_record(experiment_id: str):
            await asyncio.sleep(0.15)
            return {"experiment_id": experiment_id, "score": 85}

        aggregator.register_service("experiment", get_experiment)
        aggregator.register_service("user_record", get_user_record)

        # 聚合请求
        requests = {"experiment": {"id": "123"}, "user_record": {"experiment_id": "123"}}

        response = await aggregator.aggregate(requests, parallel=True)

        logger.info(f"成功: {response.success}")
        logger.info(f"执行时间: {response.execution_time:.3f}s")
        logger.info(f"数据: {response.data}")

    # 运行演示
    asyncio.run(demo())
