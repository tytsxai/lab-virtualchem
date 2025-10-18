"""
API网关
提供RESTful API、请求路由、认证授权、限流和监控功能
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .common_exceptions import SystemError
from .error_handler import get_error_handler
from .enhanced_event_bus import Event, EventPriority, publish_event, subscribe_event
from .enhanced_observability import get_observability, LogLevel, trace_span, TraceType
from .security_manager import get_security_manager, Permission

logger = logging.getLogger(__name__)


class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ApiResponseStatus(Enum):
    """API响应状态"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ApiRequest:
    """API请求"""
    method: HttpMethod
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "method": self.method.value,
            "path": self.path,
            "headers": self.headers,
            "query_params": self.query_params,
            "body": self.body,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp
        }


@dataclass
class ApiResponse:
    """API响应"""
    status: ApiResponseStatus
    data: Optional[Any] = None
    message: str = ""
    error_code: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    status_code: int = 200
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error_code": self.error_code,
            "headers": self.headers,
            "status_code": self.status_code,
            "timestamp": self.timestamp
        }


@dataclass
class ApiRoute:
    """API路由"""
    method: HttpMethod
    path: str
    handler: Callable[[ApiRequest], ApiResponse]
    permissions: List[Permission] = field(default_factory=list)
    rate_limit: Optional[int] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "method": self.method.value,
            "path": self.path,
            "permissions": [p.value for p in self.permissions],
            "rate_limit": self.rate_limit,
            "description": self.description,
            "tags": self.tags
        }


@dataclass
class ApiStats:
    """API统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    requests_per_minute: float = 0.0
    error_rate: float = 0.0

    def update_stats(self, response_time: float, success: bool) -> None:
        """更新统计"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # 更新平均响应时间
        self.average_response_time = (
            (self.average_response_time * (self.total_requests - 1) + response_time) /
            self.total_requests
        )

        # 更新错误率
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0


class ApiHandler(ABC):
    """API处理器接口"""

    @abstractmethod
    def handle_request(self, request: ApiRequest) -> ApiResponse:
        """处理请求"""
        pass


class ApiGateway:
    """API网关"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._error_handler = get_error_handler()
        self._observability = get_observability()
        self._security_manager = get_security_manager()

        # 路由管理
        self._routes: Dict[str, ApiRoute] = {}
        self._route_patterns: Dict[str, str] = {}

        # 中间件
        self._middleware: List[Callable[[ApiRequest], ApiRequest]] = []
        self._post_middleware: List[Callable[[ApiResponse], ApiResponse]] = []

        # 限流
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._rate_limit_window = self._config.get("rate_limit_window", 60)  # 1分钟

        # 统计信息
        self._stats = ApiStats()
        self._route_stats: Dict[str, ApiStats] = {}

        # 线程安全
        self._lock = threading.RLock()

        # 事件订阅
        self._setup_event_subscriptions()

        # 初始化默认路由
        self._setup_default_routes()

    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        subscribe_event("api_request", self._handle_api_request)
        subscribe_event("api_route_register", self._handle_route_register)
        subscribe_event("api_stats_request", self._handle_stats_request)

    def _setup_default_routes(self) -> None:
        """设置默认路由"""
        # 健康检查
        self.register_route(
            HttpMethod.GET,
            "/health",
            self._health_check_handler,
            description="Health check endpoint"
        )

        # API信息
        self.register_route(
            HttpMethod.GET,
            "/api/info",
            self._api_info_handler,
            description="API information"
        )

        # 统计信息
        self.register_route(
            HttpMethod.GET,
            "/api/stats",
            self._api_stats_handler,
            permissions=[Permission.ADMIN],
            description="API statistics"
        )

        # 路由列表
        self.register_route(
            HttpMethod.GET,
            "/api/routes",
            self._routes_list_handler,
            permissions=[Permission.ADMIN],
            description="List all routes"
        )

    def register_route(
        self,
        method: HttpMethod,
        path: str,
        handler: Callable[[ApiRequest], ApiResponse],
        permissions: Optional[List[Permission]] = None,
        rate_limit: Optional[int] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> None:
        """注册路由"""
        route_key = f"{method.value}:{path}"

        route = ApiRoute(
            method=method,
            path=path,
            handler=handler,
            permissions=permissions or [],
            rate_limit=rate_limit,
            description=description,
            tags=tags or []
        )

        with self._lock:
            self._routes[route_key] = route
            self._route_stats[route_key] = ApiStats()

        # 发布路由注册事件
        publish_event(
            "route_registered",
            route.to_dict(),
            priority=EventPriority.NORMAL
        )

        # 记录日志
        self._observability.log(
            LogLevel.INFO,
            f"Route registered: {route_key}",
            module="ApiGateway",
            function="register_route"
        )

    def add_middleware(self, middleware: Callable[[ApiRequest], ApiRequest]) -> None:
        """添加中间件"""
        self._middleware.append(middleware)

    def add_post_middleware(self, middleware: Callable[[ApiResponse], ApiResponse]) -> None:
        """添加后置中间件"""
        self._post_middleware.append(middleware)

    def handle_request(self, request: ApiRequest) -> ApiResponse:
        """处理请求"""
        start_time = time.time()

        try:
            # 应用前置中间件
            for middleware in self._middleware:
                request = middleware(request)

            # 查找路由
            route = self._find_route(request.method, request.path)
            if not route:
                return self._create_error_response(
                    "Route not found",
                    status_code=404,
                    error_code="ROUTE_NOT_FOUND"
                )

            # 检查权限
            if route.permissions and request.user_id:
                has_permission = any(
                    self._security_manager.check_permission(request.user_id, perm)
                    for perm in route.permissions
                )
                if not has_permission:
                    return self._create_error_response(
                        "Insufficient permissions",
                        status_code=403,
                        error_code="INSUFFICIENT_PERMISSIONS"
                    )

            # 检查限流
            if route.rate_limit:
                if not self._check_rate_limit(request, route):
                    return self._create_error_response(
                        "Rate limit exceeded",
                        status_code=429,
                        error_code="RATE_LIMIT_EXCEEDED"
                    )

            # 处理请求
            response = route.handler(request)

            # 应用后置中间件
            for middleware in self._post_middleware:
                response = middleware(response)

            # 更新统计
            response_time = time.time() - start_time
            self._update_stats(route, response_time, response.status_code < 400)

            # 记录日志
            self._observability.log(
                LogLevel.INFO,
                f"API request processed: {request.method.value} {request.path}",
                module="ApiGateway",
                function="handle_request",
                extra_data={
                    "status_code": response.status_code,
                    "response_time": response_time
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error handling API request: {e}")

            # 更新统计
            response_time = time.time() - start_time
            self._update_stats(None, response_time, False)

            return self._create_error_response(
                "Internal server error",
                status_code=500,
                error_code="INTERNAL_ERROR"
            )

    def _find_route(self, method: HttpMethod, path: str) -> Optional[ApiRoute]:
        """查找路由"""
        route_key = f"{method.value}:{path}"
        return self._routes.get(route_key)

    def _check_rate_limit(self, request: ApiRequest, route: ApiRoute) -> bool:
        """检查限流"""
        # 简单的限流实现
        client_key = request.ip_address or "unknown"
        current_time = time.time()

        if client_key not in self._rate_limits:
            self._rate_limits[client_key] = {
                "requests": [],
                "limit": route.rate_limit
            }

        client_limits = self._rate_limits[client_key]

        # 清理过期请求
        client_limits["requests"] = [
            req_time for req_time in client_limits["requests"]
            if current_time - req_time < self._rate_limit_window
        ]

        # 检查是否超过限制
        if len(client_limits["requests"]) >= client_limits["limit"]:
            return False

        # 记录当前请求
        client_limits["requests"].append(current_time)
        return True

    def _update_stats(self, route: Optional[ApiRoute], response_time: float, success: bool) -> None:
        """更新统计"""
        with self._lock:
            self._stats.update_stats(response_time, success)

            if route:
                route_key = f"{route.method.value}:{route.path}"
                if route_key in self._route_stats:
                    self._route_stats[route_key].update_stats(response_time, success)

    def _create_error_response(
        self,
        message: str,
        status_code: int = 400,
        error_code: Optional[str] = None
    ) -> ApiResponse:
        """创建错误响应"""
        return ApiResponse(
            status=ApiResponseStatus.ERROR,
            message=message,
            error_code=error_code,
            status_code=status_code
        )

    def _create_success_response(
        self,
        data: Any,
        message: str = "",
        status_code: int = 200
    ) -> ApiResponse:
        """创建成功响应"""
        return ApiResponse(
            status=ApiResponseStatus.SUCCESS,
            data=data,
            message=message,
            status_code=status_code
        )

    # 默认处理器
    def _health_check_handler(self, request: ApiRequest) -> ApiResponse:
        """健康检查处理器"""
        return self._create_success_response({
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0"
        })

    def _api_info_handler(self, request: ApiRequest) -> ApiResponse:
        """API信息处理器"""
        return self._create_success_response({
            "name": "VirtualChemLab API",
            "version": "1.0.0",
            "description": "Virtual Chemistry Laboratory API",
            "endpoints": len(self._routes),
            "timestamp": time.time()
        })

    def _api_stats_handler(self, request: ApiRequest) -> ApiResponse:
        """API统计处理器"""
        return self._create_success_response({
            "global_stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "average_response_time": self._stats.average_response_time,
                "error_rate": self._stats.error_rate
            },
            "route_stats": {
                route: {
                    "total_requests": stats.total_requests,
                    "successful_requests": stats.successful_requests,
                    "failed_requests": stats.failed_requests,
                    "average_response_time": stats.average_response_time,
                    "error_rate": stats.error_rate
                }
                for route, stats in self._route_stats.items()
            }
        })

    def _routes_list_handler(self, request: ApiRequest) -> ApiResponse:
        """路由列表处理器"""
        routes_data = []
        for route_key, route in self._routes.items():
            route_data = route.to_dict()
            route_data["stats"] = self._route_stats.get(route_key, {}).__dict__
            routes_data.append(route_data)

        return self._create_success_response({
            "routes": routes_data,
            "total_routes": len(routes_data)
        })

    def get_routes(self) -> Dict[str, ApiRoute]:
        """获取所有路由"""
        return self._routes.copy()

    def get_route(self, method: HttpMethod, path: str) -> Optional[ApiRoute]:
        """获取特定路由"""
        route_key = f"{method.value}:{path}"
        return self._routes.get(route_key)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "global_stats": self._stats.__dict__,
            "route_stats": {
                route: stats.__dict__
                for route, stats in self._route_stats.items()
            }
        }

    def _handle_api_request(self, event: Event) -> None:
        """处理API请求事件"""
        request_data = event.data.get("request")
        if request_data:
            # 创建请求对象
            request = ApiRequest(
                method=HttpMethod(request_data["method"]),
                path=request_data["path"],
                headers=request_data.get("headers", {}),
                query_params=request_data.get("query_params", {}),
                body=request_data.get("body"),
                user_id=request_data.get("user_id"),
                session_id=request_data.get("session_id"),
                ip_address=request_data.get("ip_address"),
                user_agent=request_data.get("user_agent")
            )

            # 处理请求
            response = self.handle_request(request)

            # 发布响应事件
            publish_event(
                "api_response",
                response.to_dict(),
                priority=EventPriority.NORMAL
            )

    def _handle_route_register(self, event: Event) -> None:
        """处理路由注册事件"""
        method = HttpMethod(event.data["method"])
        path = event.data["path"]
        handler_name = event.data["handler"]
        permissions = [Permission(p) for p in event.data.get("permissions", [])]
        rate_limit = event.data.get("rate_limit")
        description = event.data.get("description", "")
        tags = event.data.get("tags", [])

        # 这里需要根据handler_name找到实际的处理器函数
        # 简化实现，实际应用中需要更复杂的处理器查找机制
        def dummy_handler(request: ApiRequest) -> ApiResponse:
            return self._create_success_response({"message": f"Handler {handler_name} not implemented"})

        self.register_route(
            method, path, dummy_handler, permissions, rate_limit, description, tags
        )

    def _handle_stats_request(self, event: Event) -> None:
        """处理统计请求事件"""
        stats = self.get_stats()

        # 发布统计事件
        publish_event(
            "api_stats_response",
            stats,
            priority=EventPriority.NORMAL
        )

    def export_api_data(self, output_dir: Path) -> None:
        """导出API数据"""
        output_dir.mkdir(exist_ok=True)

        # 导出路由信息
        routes_file = output_dir / "routes.json"
        routes_data = {
            "routes": [route.to_dict() for route in self._routes.values()],
            "total_routes": len(self._routes)
        }

        with open(routes_file, 'w', encoding='utf-8') as f:
            json.dump(routes_data, f, indent=2, ensure_ascii=False)

        # 导出统计信息
        stats_file = output_dir / "api_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)


# 全局API网关实例
_global_api_gateway = ApiGateway()


def get_api_gateway() -> ApiGateway:
    """获取全局API网关"""
    return _global_api_gateway


def register_api_route(
    method: HttpMethod,
    path: str,
    handler: Callable[[ApiRequest], ApiResponse],
    permissions: Optional[List[Permission]] = None,
    rate_limit: Optional[int] = None,
    description: str = "",
    tags: Optional[List[str]] = None
) -> None:
    """注册API路由"""
    _global_api_gateway.register_route(
        method, path, handler, permissions, rate_limit, description, tags
    )


def handle_api_request(request: ApiRequest) -> ApiResponse:
    """处理API请求"""
    return _global_api_gateway.handle_request(request)
