import asyncio
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

"""微服务架构"""

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class ServiceType(Enum):
    """服务类型"""

    WEB = "web"
    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    GATEWAY = "gateway"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"


@dataclass
class ServiceInfo:
    """服务信息"""

    service_id: str
    name: str
    service_type: ServiceType
    version: str
    host: str
    port: int
    status: ServiceStatus = ServiceStatus.STOPPED
    health_check_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime | None = None


@dataclass
class ServiceRequest:
    """服务请求"""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    method: str = "GET"
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    data: Any = None
    timeout: float = 30.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceResponse:
    """服务响应"""

    request_id: str
    status_code: int
    data: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


class IService(ABC):
    """服务接口"""

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass

    @abstractmethod
    def get_info(self) -> ServiceInfo:
        """获取服务信息"""
        pass


class ServiceRegistry:
    """服务注册中心"""

    def __init__(self):
        """初始化服务注册中心"""
        self.services: dict[str, ServiceInfo] = {}
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {"total_services": 0, "active_services": 0, "failed_services": 0}

        logger.info("服务注册中心已初始化")

    def register_service(self, service_info: ServiceInfo) -> bool:
        """注册服务

        Args:
            service_info: 服务信息

        Returns:
            是否成功注册
        """
        with self._lock:
            if service_info.service_id in self.services:
                logger.warning(f"服务已存在: {service_info.service_id}")
                return False

            self.services[service_info.service_id] = service_info
            self.stats["total_services"] += 1

            if service_info.status == ServiceStatus.RUNNING:
                self.stats["active_services"] += 1

            logger.info(f"服务已注册: {service_info.name} ({service_info.service_id})")
            return True

    def unregister_service(self, service_id: str) -> bool:
        """注销服务

        Args:
            service_id: 服务ID

        Returns:
            是否成功注销
        """
        with self._lock:
            if service_id not in self.services:
                return False

            service_info = self.services[service_id]
            del self.services[service_id]

            if service_info.status == ServiceStatus.RUNNING:
                self.stats["active_services"] -= 1

            self.stats["total_services"] -= 1

            logger.info(f"服务已注销: {service_info.name} ({service_id})")
            return True

    def update_service_status(self, service_id: str, status: ServiceStatus) -> bool:
        """更新服务状态

        Args:
            service_id: 服务ID
            status: 新状态

        Returns:
            是否成功更新
        """
        with self._lock:
            if service_id not in self.services:
                return False

            old_status = self.services[service_id].status
            self.services[service_id].status = status

            # 更新统计信息
            if old_status == ServiceStatus.RUNNING and status != ServiceStatus.RUNNING:
                self.stats["active_services"] -= 1
            elif old_status != ServiceStatus.RUNNING and status == ServiceStatus.RUNNING:
                self.stats["active_services"] += 1

            if status == ServiceStatus.FAILED:
                self.stats["failed_services"] += 1

            logger.debug(f"服务状态已更新: {service_id} -> {status.value}")
            return True

    def get_service(self, service_id: str) -> ServiceInfo | None:
        """获取服务信息

        Args:
            service_id: 服务ID

        Returns:
            服务信息或None
        """
        with self._lock:
            return self.services.get(service_id)

    def get_services_by_name(self, name: str) -> list[ServiceInfo]:
        """根据名称获取服务

        Args:
            name: 服务名称

        Returns:
            服务信息列表
        """
        with self._lock:
            return [service for service in self.services.values() if service.name == name]

    def get_services_by_type(self, service_type: ServiceType) -> list[ServiceInfo]:
        """根据类型获取服务

        Args:
            service_type: 服务类型

        Returns:
            服务信息列表
        """
        with self._lock:
            return [service for service in self.services.values() if service.service_type == service_type]

    def get_healthy_services(self) -> list[ServiceInfo]:
        """获取健康服务

        Returns:
            健康服务列表
        """
        with self._lock:
            return [
                service
                for service in self.services.values()
                if service.status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
            ]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        with self._lock:
            return {
                "total_services": len(self.services),
                "active_services": self.stats["active_services"],
                "failed_services": self.stats["failed_services"],
                "services_by_type": {
                    service_type.value: len(self.get_services_by_type(service_type)) for service_type in ServiceType
                },
            }


class ServiceDiscovery:
    """服务发现"""

    def __init__(self, registry: ServiceRegistry):
        """初始化服务发现

        Args:
            registry: 服务注册中心
        """
        self.registry = registry
        self.cache: dict[str, list[ServiceInfo]] = {}
        self.cache_ttl = 60  # 缓存TTL（秒）
        self.last_cache_update = 0

        logger.info("服务发现已初始化")

    def discover_service(self, service_name: str, service_type: ServiceType | None = None) -> ServiceInfo | None:
        """发现服务

        Args:
            service_name: 服务名称
            service_type: 服务类型

        Returns:
            服务信息或None
        """
        # 检查缓存
        cache_key = f"{service_name}:{service_type.value if service_type else 'any'}"
        current_time = time.time()

        if cache_key in self.cache and current_time - self.last_cache_update < self.cache_ttl:
            services = self.cache[cache_key]
            if services:
                return services[0]  # 返回第一个可用服务

        # 从注册中心查找
        services = self.registry.get_services_by_name(service_name)

        if service_type:
            services = [s for s in services if s.service_type == service_type]

        # 过滤健康服务
        healthy_services = [s for s in services if s.status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]]

        if healthy_services:
            # 更新缓存
            self.cache[cache_key] = healthy_services
            self.last_cache_update = current_time

            return healthy_services[0]

        return None

    def discover_services(self, service_name: str, service_type: ServiceType | None = None) -> list[ServiceInfo]:
        """发现多个服务

        Args:
            service_name: 服务名称
            service_type: 服务类型

        Returns:
            服务信息列表
        """
        services = self.registry.get_services_by_name(service_name)

        if service_type:
            services = [s for s in services if s.service_type == service_type]

        # 过滤健康服务
        healthy_services = [s for s in services if s.status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]]

        return healthy_services

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.last_cache_update = 0
        logger.info("服务发现缓存已清空")


class ServiceGateway:
    """服务网关"""

    def __init__(self, discovery: ServiceDiscovery):
        """初始化服务网关

        Args:
            discovery: 服务发现
        """
        self.discovery = discovery
        self.session = None

        # 统计信息
        self.stats = {"requests_total": 0, "requests_success": 0, "requests_failed": 0, "response_time_avg": 0.0}

        logger.info("服务网关已初始化")

    async def start(self) -> None:
        """启动服务网关"""
        if AIOHTTP_AVAILABLE:
            self.session = aiohttp.ClientSession()
        logger.info("服务网关已启动")

    async def stop(self) -> None:
        """停止服务网关"""
        if self.session:
            await self.session.close()
        logger.info("服务网关已停止")

    async def call_service(self, request: ServiceRequest) -> ServiceResponse:
        """调用服务

        Args:
            request: 服务请求

        Returns:
            服务响应
        """
        start_time = time.time()

        try:
            # 发现服务
            service = self.discovery.discover_service(request.service_name)
            if not service:
                return ServiceResponse(
                    request_id=request.request_id, status_code=404, error=f"服务未找到: {request.service_name}"
                )

            # 构建URL
            url = f"http://{service.host}:{service.port}{request.path}"

            # 调用服务
            if AIOHTTP_AVAILABLE and self.session:
                response = await self._call_service_async(url, request)
            else:
                response = await self._call_service_sync(url, request)

            # 更新统计信息
            self.stats["requests_total"] += 1
            self.stats["requests_success"] += 1

            response_time = time.time() - start_time
            self.stats["response_time_avg"] = (
                self.stats["response_time_avg"] * (self.stats["requests_success"] - 1) + response_time
            ) / self.stats["requests_success"]

            return response

        except Exception as e:
            logger.error(f"调用服务失败: {e}")

            # 更新统计信息
            self.stats["requests_total"] += 1
            self.stats["requests_failed"] += 1

            return ServiceResponse(request_id=request.request_id, status_code=500, error=str(e))

    async def _call_service_async(self, url: str, request: ServiceRequest) -> ServiceResponse:
        """异步调用服务"""
        async with self.session.request(
            method=request.method,
            url=url,
            headers=request.headers,
            json=request.data,
            timeout=aiohttp.ClientTimeout(total=request.timeout),
        ) as response:
            data = await response.json() if response.content_type == "application/json" else await response.text()

            return ServiceResponse(
                request_id=request.request_id, status_code=response.status, data=data, headers=dict(response.headers)
            )

    async def _call_service_sync(self, url: str, request: ServiceRequest) -> ServiceResponse:
        """同步调用服务"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests库未安装")

        # 在线程池中执行同步请求
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.request(
                method=request.method, url=url, headers=request.headers, json=request.data, timeout=request.timeout
            ),
        )

        return ServiceResponse(
            request_id=request.request_id,
            status_code=response.status_code,
            data=(
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else response.text
            ),
            headers=dict(response.headers),
        )

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "requests_total": self.stats["requests_total"],
            "requests_success": self.stats["requests_success"],
            "requests_failed": self.stats["requests_failed"],
            "success_rate": self.stats["requests_success"] / max(1, self.stats["requests_total"]),
            "response_time_avg": self.stats["response_time_avg"],
        }


class BaseService(IService):
    """基础服务"""

    def __init__(self, service_info: ServiceInfo, registry: ServiceRegistry):
        """初始化基础服务

        Args:
            service_info: 服务信息
            registry: 服务注册中心
        """
        self.service_info = service_info
        self.registry = registry
        self.running = False

        logger.info(f"基础服务已初始化: {service_info.name}")

    async def start(self) -> None:
        """启动服务"""
        self.running = True
        self.service_info.status = ServiceStatus.STARTING

        # 注册服务
        self.registry.register_service(self.service_info)

        # 更新状态
        self.service_info.status = ServiceStatus.RUNNING
        self.registry.update_service_status(self.service_info.service_id, ServiceStatus.RUNNING)

        logger.info(f"服务已启动: {self.service_info.name}")

    async def stop(self) -> None:
        """停止服务"""
        self.running = False
        self.service_info.status = ServiceStatus.STOPPING

        # 更新状态
        self.registry.update_service_status(self.service_info.service_id, ServiceStatus.STOPPING)

        # 注销服务
        self.registry.unregister_service(self.service_info.service_id)

        # 更新状态
        self.service_info.status = ServiceStatus.STOPPED

        logger.info(f"服务已停止: {self.service_info.name}")

    async def health_check(self) -> bool:
        """健康检查"""
        if not self.running:
            return False

        # 更新心跳时间
        self.service_info.last_heartbeat = datetime.now()

        # 执行自定义健康检查
        is_healthy = await self._custom_health_check()

        # 更新状态
        status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
        self.registry.update_service_status(self.service_info.service_id, status)

        return is_healthy

    async def _custom_health_check(self) -> bool:
        """自定义健康检查

        Returns:
            是否健康
        """
        return True

    def get_info(self) -> ServiceInfo:
        """获取服务信息"""
        return self.service_info


class MicroservicesManager:
    """微服务管理器"""

    def __init__(self):
        """初始化微服务管理器"""
        self.registry = ServiceRegistry()
        self.discovery = ServiceDiscovery(self.registry)
        self.gateway = ServiceGateway(self.discovery)
        self.services: dict[str, IService] = {}

        logger.info("微服务管理器已初始化")

    def register_service(self, service: IService) -> None:
        """注册服务

        Args:
            service: 服务实例
        """
        service_info = service.get_info()
        self.services[service_info.service_id] = service

        logger.info(f"服务已注册到管理器: {service_info.name}")

    def unregister_service(self, service_id: str) -> bool:
        """注销服务

        Args:
            service_id: 服务ID

        Returns:
            是否成功注销
        """
        if service_id in self.services:
            del self.services[service_id]
            logger.info(f"服务已从管理器注销: {service_id}")
            return True
        return False

    async def start_all_services(self) -> None:
        """启动所有服务"""
        logger.info("正在启动所有服务...")

        for service in self.services.values():
            try:
                await service.start()
            except Exception as e:
                logger.error(f"启动服务失败: {e}")

        # 启动网关
        await self.gateway.start()

        logger.info("所有服务已启动")

    async def stop_all_services(self) -> None:
        """停止所有服务"""
        logger.info("正在停止所有服务...")

        # 停止网关
        await self.gateway.stop()

        # 停止所有服务
        for service in self.services.values():
            try:
                await service.stop()
            except Exception as e:
                logger.error(f"停止服务失败: {e}")

        logger.info("所有服务已停止")

    async def health_check_all_services(self) -> dict[str, bool]:
        """健康检查所有服务

        Returns:
            服务健康状态
        """
        health_status = {}

        for service_id, service in self.services.items():
            try:
                is_healthy = await service.health_check()
                health_status[service_id] = is_healthy
            except Exception as e:
                logger.error(f"健康检查失败 {service_id}: {e}")
                health_status[service_id] = False

        return health_status

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "registry": self.registry.get_statistics(),
            "gateway": self.gateway.get_statistics(),
            "services_count": len(self.services),
        }


# 全局微服务管理器
microservices_manager = MicroservicesManager()


def service(service_type: ServiceType, name: str, version: str = "1.0.0", host: str = "localhost", port: int = 8000):
    """服务装饰器

    Args:
        service_type: 服务类型
        name: 服务名称
        version: 服务版本
        host: 服务主机
        port: 服务端口
    """

    def decorator(cls: type[IService]) -> type[IService]:
        # 创建服务信息
        service_info = ServiceInfo(
            service_id=f"{name}_{version}_{int(time.time())}",
            name=name,
            service_type=service_type,
            version=version,
            host=host,
            port=port,
        )

        # 创建服务实例
        service_instance = cls(service_info, microservices_manager.registry)

        # 注册服务
        microservices_manager.register_service(service_instance)

        return cls

    return decorator
