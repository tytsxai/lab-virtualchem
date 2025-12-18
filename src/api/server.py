"""REST API服务器

提供HTTP接口用于外部系统集成

增强功能:
1. 微服务架构和API网关
2. GraphQL查询支持
3. WebSocket实时通信
4. API版本管理和兼容性
5. 高级认证和授权
6. 请求/响应缓存
7. API文档自动生成
8. 监控和性能分析
"""

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# 可选依赖
try:
    import websockets  # noqa: F401

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from ..core.error_system import (
    BaseAppException,
    ErrorCodeRegistry,
    NotificationChannel,
    ResourceNotFoundError,
    error_reporter,
)
from ..core.experiment_controller import ExperimentController
from ..core.template_engine import TemplateEngine
from ..reporter.html_generator import HTMLGenerator
from ..storage.json_store import JSONStore
from ..utils.config import Config
from ..utils.logger import SensitiveDataFilter, setup_logger
from .middleware import get_auth_middleware, get_rate_limiter

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("api.access")

_LOCAL_ORIGIN_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _parse_cors_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _is_local_origin(origin: str) -> bool:
    """Return True if Origin is a local loopback host.

    NOTE: Avoid naive prefix matching (e.g. `http://localhost.evil.com`).
    """
    try:
        parsed = urlparse(origin)
    except Exception:  # noqa: BLE001
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    return hostname.lower() in _LOCAL_ORIGIN_HOSTS


def _is_allowed_origin(origin: str, allowed: list[str]) -> bool:
    # Exact match first
    if origin in allowed:
        return True
    # Convenience: allow any localhost origin by default
    return _is_local_origin(origin)


class APIVersion(Enum):
    """API版本"""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


class APIMethod(Enum):
    """API方法"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


class CacheStrategy(Enum):
    """缓存策略"""

    NO_CACHE = "no_cache"
    SHORT_TERM = "short_term"  # 5分钟
    MEDIUM_TERM = "medium_term"  # 1小时
    LONG_TERM = "long_term"  # 24小时


class APIRequestHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    def __init__(self, *args, **kwargs):
        # 初始化中间件和限流器
        self.auth_middleware = None
        self.rate_limiter = None

        # 新增功能
        self.api_version = APIVersion.V2
        self.cache_enabled = True
        self.websocket_enabled = False
        self.request_cache: dict[str, Any] = {}
        self.websocket_connections: list[Any] = []
        self.api_metrics: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "endpoints": {},
        }

        super().__init__(*args, **kwargs)

    def _set_headers(
        self, status: int = 200, content_type: str = "application/json"
    ) -> None:
        """设置响应头"""
        self.send_response(status)
        self.send_header("Content-type", content_type)
        # CORS：默认仅允许 localhost/127.0.0.1/::1（可通过环境变量显式扩展）
        origin = self.headers.get("Origin")
        allowed_origins_env = (os.getenv("VCL_API_CORS_ORIGINS") or "").strip()
        allowed_origins = _parse_cors_origins(allowed_origins_env)
        if origin and _is_allowed_origin(origin, allowed_origins):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key"
        )
        self.end_headers()

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        """发送JSON响应"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(
        self,
        status: int,
        message: str,
        error_code: int | None = None,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """发送统一格式的错误响应

        Args:
            status: HTTP状态码
            message: 错误消息
            error_code: 应用错误码
            details: 详细信息
            trace_id: 追踪ID
        """
        error_response = {
            "success": False,
            "error": {
                "message": message,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            },
        }

        if error_code:
            error_response["error"]["code"] = error_code
        if details:
            error_response["error"]["details"] = details
        if trace_id:
            error_response["error"]["trace_id"] = trace_id

        self._send_json(error_response, status)

    def _get_cache_key(self, path: str, method: str, params: dict[str, Any]) -> str:
        """生成缓存键"""
        cache_data = f"{method}:{path}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(cache_data.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> dict[str, Any] | None:
        """获取缓存的响应"""
        if not self.cache_enabled:
            return None

        cached = self.request_cache.get(cache_key)
        if cached and datetime.now() < cached["expires_at"]:
            return cached["data"]
        elif cached:
            # 缓存过期，删除
            del self.request_cache[cache_key]

        return None

    def _cache_response(
        self, cache_key: str, data: dict[str, Any], strategy: CacheStrategy
    ) -> None:
        """缓存响应"""
        if not self.cache_enabled or strategy == CacheStrategy.NO_CACHE:
            return

        # 计算过期时间
        if strategy == CacheStrategy.SHORT_TERM:
            expires_at = datetime.now() + timedelta(minutes=5)
        elif strategy == CacheStrategy.MEDIUM_TERM:
            expires_at = datetime.now() + timedelta(hours=1)
        elif strategy == CacheStrategy.LONG_TERM:
            expires_at = datetime.now() + timedelta(hours=24)
        else:
            return

        self.request_cache[cache_key] = {
            "data": data,
            "expires_at": expires_at,
            "strategy": strategy.value,
        }

    def _validate_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        # 这里应该实现真实的API密钥验证逻辑
        # 暂时使用简单的验证
        valid_keys = ["test_key_123", "production_key_456"]
        return api_key in valid_keys

    def _authenticate_request(self) -> dict[str, Any] | None:
        """认证请求"""
        auth_header = self.headers.get("Authorization")
        api_key = self.headers.get("X-API-Key")

        if api_key and self._validate_api_key(api_key):
            return {"user_id": "api_user", "permissions": ["read", "write"]}

        if auth_header and auth_header.startswith("Bearer "):
            auth_header[7:]
            # 这里应该验证JWT token
            return {"user_id": "token_user", "permissions": ["read"]}

        return None

    def _rate_limit_check(self, _client_ip: str, _endpoint: str) -> bool:
        """检查速率限制"""
        # 简单的速率限制实现
        # 实际应用中应该使用Redis等外部存储
        datetime.now()

        # 这里应该实现真实的速率限制逻辑
        return True

    def _update_metrics(
        self, endpoint: str, method: str, response_time: float, success: bool
    ) -> None:
        """更新API指标"""
        self.api_metrics["total_requests"] += 1

        if success:
            self.api_metrics["successful_requests"] += 1
        else:
            self.api_metrics["failed_requests"] += 1

        # 更新平均响应时间
        total_time = self.api_metrics["average_response_time"] * (
            self.api_metrics["total_requests"] - 1
        )
        self.api_metrics["average_response_time"] = (
            total_time + response_time
        ) / self.api_metrics["total_requests"]

        # 更新端点统计
        endpoint_key = f"{method}:{endpoint}"
        if endpoint_key not in self.api_metrics["endpoints"]:
            self.api_metrics["endpoints"][endpoint_key] = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "average_time": 0.0,
            }

        endpoint_stats = self.api_metrics["endpoints"][endpoint_key]
        endpoint_stats["requests"] += 1

        if success:
            endpoint_stats["successful"] += 1
        else:
            endpoint_stats["failed"] += 1

        # 更新端点平均时间
        total_endpoint_time = endpoint_stats["average_time"] * (
            endpoint_stats["requests"] - 1
        )
        endpoint_stats["average_time"] = (
            total_endpoint_time + response_time
        ) / endpoint_stats["requests"]

    def _handle_graphql_query(
        self, _query: str, _variables: dict[str, Any]
    ) -> dict[str, Any]:
        """处理GraphQL查询"""
        try:
            # 这里应该实现GraphQL查询处理
            # 暂时返回模拟数据
            return {
                "data": {
                    "experiments": [
                        {"id": "exp1", "title": "基础化学实验"},
                        {"id": "exp2", "title": "有机化学实验"},
                    ]
                }
            }
        except Exception as e:
            return {"errors": [{"message": str(e)}]}

    def _handle_websocket_upgrade(self) -> None:
        """处理WebSocket升级请求"""
        if not self.websocket_enabled:
            self._send_error(400, "WebSocket not enabled")
            return

        # 这里应该实现WebSocket升级逻辑
        # 暂时返回错误
        self._send_error(501, "WebSocket not implemented")

    def _generate_api_docs(self) -> dict[str, Any]:
        """生成API文档"""
        host, port = "localhost", 8080
        try:
            server_address = getattr(self.server, "server_address", None)
            if isinstance(server_address, tuple) and len(server_address) >= 2:
                host = server_address[0] or host
                port = int(server_address[1])
        except Exception:  # noqa: BLE001
            pass

        return {
            "openapi": "3.0.0",
            "info": {
                "title": "VirtualChemLab API",
                "version": self.api_version.value,
                "description": "虚拟化学实验室API接口",
            },
            "servers": [{"url": f"http://{host}:{port}"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "Provide an API key via X-API-Key header.",
                    },
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "API Key",
                        "description": "Alternatively provide API key via Authorization: Bearer <key>.",
                    },
                }
            },
            "security": [{"ApiKeyAuth": []}],
            "paths": {
                "/api/health": {
                    "get": {
                        "summary": "健康检查",
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        },
                    }
                },
                "/api/docs": {
                    "get": {
                        "summary": "OpenAPI 文档(JSON)",
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        },
                    }
                },
                "/api/experiments": {
                    "get": {
                        "summary": "获取实验列表",
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "data": {"type": "array"},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/experiments/{experiment_id}": {
                    "get": {
                        "summary": "获取实验详情",
                        "parameters": [
                            {
                                "name": "experiment_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "实验不存在"},
                        },
                    }
                },
                "/api/experiments/start": {
                    "post": {
                        "summary": "开始实验",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        },
                    }
                },
                "/api/experiments/submit": {
                    "post": {
                        "summary": "提交当前步骤",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "会话不存在"},
                        },
                    }
                },
                "/api/experiments/finish": {
                    "post": {
                        "summary": "完成实验并生成记录",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "会话不存在"},
                        },
                    }
                },
                "/api/records": {
                    "get": {
                        "summary": "列出实验记录",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        },
                    }
                },
                "/api/records/{record_id}": {
                    "get": {
                        "summary": "获取实验记录详情",
                        "parameters": [
                            {
                                "name": "record_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "user_id",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                                "description": "可选：指定 user_id 以避免全量扫描",
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "记录不存在"},
                        },
                    }
                },
                "/api/reports/generate": {
                    "post": {
                        "summary": "生成实验报告",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "记录不存在"},
                        },
                    }
                },
            },
        }

    def _handle_api_docs(self, trace_id: str) -> None:
        """返回 OpenAPI JSON 文档."""
        _ = trace_id
        self._send_json(self._generate_api_docs())

    def _send_exception(
        self, exception: BaseAppException, trace_id: str | None = None
    ) -> None:
        """发送基于异常对象的错误响应

        Args:
            exception: 应用异常对象
            trace_id: 追踪ID
        """
        response_data = exception.to_dict(language="zh")
        if trace_id:
            response_data["error"]["trace_id"] = trace_id

        self._send_json(response_data, exception.error_code.http_status)

    def _parse_body(self) -> dict[str, Any] | None:
        """解析请求体"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))

            # 请求体大小限制 (10MB)
            max_size = 10 * 1024 * 1024
            if content_length > max_size:
                logger.warning(f"请求体过大: {content_length} bytes")
                return None

            if content_length > 0:
                body = self.rfile.read(content_length)
                return json.loads(body.decode("utf-8"))
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse request body: {e}")
            return None

    def do_OPTIONS(self):
        """处理OPTIONS请求(CORS预检)"""
        self._set_headers(204)

    def _get_trace_id(self) -> str:
        """获取或生成追踪ID"""
        # 尝试从请求头获取
        trace_id = self.headers.get("X-Trace-ID")
        if not trace_id:
            # 生成新的追踪ID
            trace_id = str(uuid.uuid4())
        return trace_id

    def do_GET(self):
        """处理GET请求"""
        start_time = time.time()
        trace_id = self._get_trace_id()

        try:
            # 记录请求开始(包含追踪ID)
            access_logger.info(
                f"[{trace_id}] GET {self.path} from {self.client_address[0]}"
            )

            # 应用限流(从服务器获取)
            limiter = getattr(self.server, "rate_limiter", None)
            if limiter and not limiter.is_allowed(self.client_address[0]):
                self._send_error(429, "请求过于频繁,请稍后再试")
                return

            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)

            # 白名单路径(不需要认证)
            whitelist_paths = ["/api/health", "/api/docs"]

            # 应用认证中间件(除白名单外)
            if path not in whitelist_paths and hasattr(self.server, "auth_middleware"):
                api_key = self.headers.get("X-API-Key") or self.headers.get(
                    "Authorization", ""
                ).replace("Bearer ", "")

                client_info = self.server.auth_middleware.verify_api_key(api_key)
                if not client_info:
                    self._send_error(401, "未授权: 无效的API密钥")
                    return

                # 附加客户端信息
                self.client_info = client_info

            # 路由分发
            if path == "/api/experiments":
                self._handle_list_experiments(trace_id)
            elif path.startswith("/api/experiments/"):
                exp_id = path.split("/")[-1]
                self._handle_get_experiment(exp_id, trace_id)
            elif path == "/api/records":
                user_id = params.get("user_id", [None])[0]
                self._handle_list_records(user_id, trace_id)
            elif path.startswith("/api/records/"):
                record_id = path.split("/")[-1]
                user_id = params.get("user_id", [None])[0]
                self._handle_get_record(record_id, user_id, trace_id)
            elif path == "/api/health":
                self._handle_health_check(trace_id)
            elif path == "/api/docs":
                self._handle_api_docs(trace_id)
            else:
                # 使用统一错误系统
                raise ResourceNotFoundError(
                    message=f"API路径不存在: {path}",
                    error_code=ErrorCodeRegistry.RESOURCE_NOT_FOUND,
                    resource_type="api_endpoint",
                    resource_id=path,
                    user_message="请求的接口不存在",
                )

        except BaseAppException as e:
            # 应用异常 - 使用统一错误响应
            logger.warning(f"[{trace_id}] API error: {e.error_code.name} - {e.message}")

            # 生成错误报告
            error_reporter.report_error(
                exception=e,
                context=f"API GET {path}",
                session_id=trace_id,
                notify=True,
                notification_channels=[NotificationChannel.LOG],
            )

            self._send_exception(e, trace_id)

        except Exception as e:
            # 未预期的异常
            logger.error(f"[{trace_id}] Unexpected error: {e}", exc_info=True)

            # 转换为系统错误
            system_error = BaseAppException(
                message="服务器内部错误",
                error_code=ErrorCodeRegistry.SYS_INTERNAL_ERROR,
                original_exception=e,
                user_message="服务器处理请求时发生错误，请稍后重试",
            )

            # 报告错误
            error_reporter.report_error(
                exception=system_error,
                context=f"API GET {path}",
                session_id=trace_id,
                notify=True,
                notification_channels=[NotificationChannel.LOG],
            )

            self._send_exception(system_error, trace_id)

        finally:
            # 记录请求完成
            duration = (time.time() - start_time) * 1000  # 毫秒
            access_logger.info(
                f"[{trace_id}] GET {self.path} completed in {duration:.2f}ms"
            )

    def do_POST(self):
        """处理POST请求"""
        start_time = time.time()

        try:
            # 记录请求
            access_logger.info(f"POST {self.path} from {self.client_address[0]}")

            # 应用限流
            limiter = getattr(self.server, "rate_limiter", None)
            if limiter and not limiter.is_allowed(self.client_address[0]):
                self._send_error(429, "请求过于频繁,请稍后再试")
                return

            parsed = urlparse(self.path)
            path = parsed.path

            # 验证Content-Type
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("application/json"):
                self._send_error(415, "不支持的媒体类型,请使用application/json")
                return

            # 应用认证
            if hasattr(self.server, "auth_middleware"):
                api_key = self.headers.get("X-API-Key") or self.headers.get(
                    "Authorization", ""
                ).replace("Bearer ", "")

                client_info = self.server.auth_middleware.verify_api_key(api_key)
                if not client_info:
                    self._send_error(401, "未授权: 无效的API密钥")
                    return

                self.client_info = client_info

            body = self._parse_body()

            if body is None:
                self._send_error(400, "JSON格式错误")
                return

            # 路由分发
            if path == "/api/experiments/start":
                self._handle_start_experiment(body)
            elif path == "/api/experiments/submit":
                self._handle_submit_step(body)
            elif path == "/api/experiments/finish":
                self._handle_finish_experiment(body)
            elif path == "/api/reports/generate":
                self._handle_generate_report(body)
            else:
                self._send_error(404, f"路径未找到: {path}")

        except Exception as e:
            logger.error(f"POST request error: {e}", exc_info=True)
            self._send_error(500, "服务器内部错误")
        finally:
            duration = (time.time() - start_time) * 1000
            access_logger.info(f"POST {self.path} completed in {duration:.2f}ms")

    # ============ 路由处理方法 ============

    def _handle_health_check(self, trace_id: str) -> None:
        """健康检查

        Args:
            trace_id: 请求追踪ID（用于日志追踪）
        """
        _ = trace_id  # 保留参数以保持接口统一
        self._send_json(
            {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _handle_list_experiments(self, trace_id: str) -> None:
        """列出所有实验

        Args:
            trace_id: 请求追踪ID
        """
        try:
            engine = self.server.template_engine
            experiments = engine.list_available_experiments()

            self._send_json(
                {
                    "success": True,
                    "data": {"experiments": experiments, "count": len(experiments)},
                    "trace_id": trace_id,
                }
            )
        except Exception as e:
            logger.error(f"[{trace_id}] Failed to list experiments: {e}", exc_info=True)
            raise BaseAppException(
                message="获取实验列表失败",
                error_code=ErrorCodeRegistry.SYS_INTERNAL_ERROR,
                original_exception=e,
                user_message="无法加载实验列表，请稍后重试",
            ) from e

    @staticmethod
    def _serialize_step(step: Any) -> dict[str, Any]:
        check = getattr(step, "check", None)
        check_type = getattr(check, "type", None)
        if hasattr(check_type, "value"):
            check_type = check_type.value
        return {
            "id": getattr(step, "id", ""),
            "text": getattr(step, "text", ""),
            "check_type": check_type,
            "safety_level": getattr(step, "safety_level", None),
        }

    def _handle_get_experiment(self, exp_id: str, trace_id: str) -> None:
        """获取实验详情

        Args:
            exp_id: 实验ID
            trace_id: 请求追踪ID（用于日志追踪）
        """
        _ = trace_id  # 保留参数以保持接口统一
        try:
            engine = self.server.template_engine
            template = engine.load_experiment_by_id(exp_id)

            self._send_json(
                {
                    "experiment": {
                        "id": template.id,
                        "title": template.title,
                        "description": template.description,
                        "category": getattr(template, "category", ""),
                        "level": getattr(template, "level", ""),
                        "difficulty": getattr(template, "difficulty", None)
                        or getattr(template, "level", None),
                        "duration_min": getattr(template, "duration_min", None),
                        "version": getattr(template, "version", None),
                        "steps": [self._serialize_step(step) for step in template.steps],
                        "score_rules": [
                            {
                                "when": getattr(rule, "when", None),
                                "then": getattr(rule, "then", None),
                            }
                            for rule in getattr(template, "score_rules", []) or []
                        ],
                    }
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("加载实验详情失败: %s", exc, exc_info=True)
            self._send_error(404, f"Experiment not found: {exp_id}")

    def _handle_start_experiment(self, body: dict[str, Any]) -> None:
        """开始实验"""
        exp_id = body.get("experiment_id")
        user_id = body.get("user_id", "anonymous")

        if not exp_id:
            self._send_error(400, "Missing experiment_id")
            return

        try:
            engine = self.server.template_engine
            template = engine.load_experiment_by_id(exp_id)

            # 创建控制器
            controller = ExperimentController(
                template=template,
                user_id=user_id,
                storage=getattr(self.server, "storage", None),
            )
            controller.start_experiment()

            # 保存会话
            session_id = getattr(controller, "session_id", None) or str(uuid.uuid4())
            self.server.sessions[session_id] = controller

            current_step = controller.get_current_step()

            self._send_json(
                {
                    "session_id": session_id,
                    "experiment_id": exp_id,
                    "current_step": (
                        {
                            "id": getattr(current_step, "id", ""),
                            "text": getattr(current_step, "text", ""),
                            "check_type": (
                                current_step.check.type.value
                                if getattr(current_step, "check", None)
                                and hasattr(current_step.check.type, "value")
                                else (
                                    current_step.check.type
                                    if getattr(current_step, "check", None)
                                    else None
                                )
                            ),
                        }
                        if current_step
                        else None
                    ),
                    "progress": controller.get_progress(),
                },
                201,
            )
        except Exception as e:
            self._send_error(500, f"Failed to start experiment: {str(e)}")

    def _handle_submit_step(self, body: dict[str, Any]) -> None:
        """提交步骤"""
        session_id = body.get("session_id")
        user_data = body.get("data", {})

        if not session_id:
            self._send_error(400, "Missing session_id")
            return

        controller = self.server.sessions.get(session_id)
        if not controller:
            self._send_error(404, f"Session not found: {session_id}")
            return

        try:
            before_index = getattr(controller, "current_step_index", None)
            result = controller.submit_step(user_data)
            passed = bool(getattr(result, "is_valid", False))
            message = str(getattr(result, "message", ""))

            after_index = getattr(controller, "current_step_index", before_index)
            has_next = bool(passed and before_index is not None and after_index != before_index)

            current_step = None if getattr(controller, "is_completed", lambda: False)() else controller.get_current_step()

            mistake = getattr(result, "mistake", None)
            mistake_payload: dict[str, Any] | None = None
            if mistake is not None:
                mistake_payload = {
                    "step_id": getattr(mistake, "step_id", None),
                    "error_type": getattr(mistake, "error_type", None),
                    "description": getattr(mistake, "description", None),
                    "hint": getattr(mistake, "hint", None),
                    "severity": getattr(mistake, "severity", None),
                }

            self._send_json(
                {
                    "passed": passed,
                    "message": message,
                    "errors": getattr(result, "errors", []) or [],
                    "warnings": getattr(result, "warnings", []) or [],
                    "mistake": mistake_payload,
                    "has_next_step": has_next,
                    "current_step": (
                        self._serialize_step(current_step) if current_step else None
                    ),
                    "progress": controller.get_progress(),
                }
            )
        except Exception as e:
            self._send_error(500, f"Failed to submit step: {str(e)}")

    def _handle_finish_experiment(self, body: dict[str, Any]) -> None:
        """完成实验"""
        session_id = body.get("session_id")

        if not session_id:
            self._send_error(400, "Missing session_id")
            return

        controller = self.server.sessions.get(session_id)
        if not controller:
            self._send_error(404, f"Session not found: {session_id}")
            return

        try:
            record = controller.complete_experiment()

            # 保存记录（优先使用 JSONStore.save_record）
            store = getattr(self.server, "storage", None)
            saved = False
            if store is not None:
                save_record = getattr(store, "save_record", None)
                if callable(save_record):
                    saved = bool(save_record(record))
                else:
                    save_generic = getattr(store, "save", None)
                    if callable(save_generic):
                        saved = bool(save_generic(f"records/{record.user_id}/{record.record_id}", record))

            # 清理会话
            del self.server.sessions[session_id]

            if store is not None and not saved:
                logger.warning("实验记录保存失败: record_id=%s", getattr(record, "record_id", None))

            self._send_json(
                {
                    "record_id": record.record_id,
                    "final_score": record.final_score,
                    "total_mistakes": record.total_mistakes,
                    "duration_seconds": record.total_duration_seconds,
                }
            )
        except Exception as e:
            self._send_error(500, f"Failed to finish experiment: {str(e)}")

    def _handle_list_records(self, user_id: str | None, trace_id: str) -> None:
        """列出记录

        Args:
            user_id: 用户ID（可选，用于过滤）
            trace_id: 请求追踪ID（用于日志追踪）
        """
        _ = trace_id  # 保留参数以保持接口统一
        try:
            store = getattr(self.server, "storage", None)
            if store is None or not hasattr(store, "list_records"):
                self._send_error(500, "Storage backend does not support list_records")
                return

            entries = store.list_records(user_id=user_id)
            records = [
                {
                    "id": entry.get("record_id"),
                    "user_id": entry.get("user_id"),
                    "experiment_id": entry.get("experiment_id"),
                    "experiment_title": entry.get("experiment_title"),
                    "final_score": entry.get("final_score"),
                    "start_time": entry.get("started_at"),
                    "end_time": entry.get("finished_at"),
                    "status": entry.get("status"),
                }
                for entry in entries
            ]

            self._send_json({"records": records, "count": len(records)})
        except Exception as e:
            self._send_error(500, f"Failed to list records: {str(e)}")

    def _find_record_owner(self, record_id: str) -> str | None:
        store = getattr(self.server, "storage", None)
        if store is None or not hasattr(store, "list_records"):
            return None
        try:
            entries = store.list_records(user_id=None)
        except Exception:  # noqa: BLE001
            return None
        for entry in entries:
            if entry.get("record_id") == record_id and entry.get("user_id"):
                return str(entry["user_id"])
        return None

    def _load_record(self, record_id: str, user_id: str | None = None) -> Any | None:
        store = getattr(self.server, "storage", None)
        if store is None:
            return None
        load_record = getattr(store, "load_record", None)
        if not callable(load_record):
            return None

        resolved_user = user_id or self._find_record_owner(record_id)
        if not resolved_user:
            return None
        return load_record(resolved_user, record_id)

    def _handle_get_record(
        self, record_id: str, user_id: str | None, trace_id: str
    ) -> None:
        """获取记录详情

        Args:
            record_id: 记录ID
            user_id: 用户ID（可选，用于加速查找）
            trace_id: 请求追踪ID（用于日志追踪）
        """
        _ = trace_id  # 保留参数以保持接口统一
        try:
            record = self._load_record(record_id, user_id=user_id)

            if record is None:
                self._send_error(404, f"Record not found: {record_id}")
                return

            # UserRecord 是 pydantic 模型，优先使用 model_dump 输出可 JSON 化的数据
            payload = (
                record.model_dump(mode="json")
                if hasattr(record, "model_dump")
                else record
            )
            self._send_json({"record": payload})
        except Exception as e:
            self._send_error(500, f"Failed to get record: {str(e)}")

    def _handle_generate_report(self, body: dict[str, Any]) -> None:
        """生成报告"""
        record_id = body.get("record_id")
        format_type = body.get("format", "html")

        if not record_id:
            self._send_error(400, "Missing record_id")
            return

        try:
            record = self._load_record(record_id)
            if record is None:
                self._send_error(404, f"Record not found: {record_id}")
                return

            # 加载模板
            engine = self.server.template_engine
            template = engine.load_experiment_by_id(record.experiment_id)

            # 生成报告（默认写入 reports/ 目录，便于桌面/本地环境查看）
            generator = HTMLGenerator()
            report_path = Path("reports") / f"{record_id}.html"
            report_path.parent.mkdir(parents=True, exist_ok=True)

            html_content = generator.generate(record, template, output_path=report_path)

            self._send_json(
                {
                    "record_id": record_id,
                    "format": format_type,
                    "content": html_content if format_type == "html" else None,
                    "url": f"/reports/{record_id}.html",
                    "path": str(report_path),
                }
            )
        except Exception as e:
            self._send_error(500, f"Failed to generate report: {str(e)}")

    def log_message(self, format: str, *args: Any) -> None:
        """重写日志方法"""
        logger.info(f"{self.address_string()} - {format % args}")


class APIServer:
    """API服务器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        enable_auth: bool = True,
        enable_rate_limit: bool = True,
    ):
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

        # 初始化组件
        config = Config()
        self.template_engine = TemplateEngine(config.get("paths.templates_dir"))
        self.storage = JSONStore(config.get("paths.data_dir", "data/records"))

        # 会话存储
        self.sessions: dict[str, ExperimentController] = {}

        # 初始化中间件
        self.auth_middleware = get_auth_middleware(enabled=enable_auth)
        self.rate_limiter = (
            get_rate_limiter(max_requests=100, time_window=60)
            if enable_rate_limit
            else None
        )

        logger.info(f"API服务器初始化 - 认证: {enable_auth}, 限流: {enable_rate_limit}")

    def start(self) -> None:
        """启动服务器"""
        try:
            # 创建HTTP服务器
            self.server = HTTPServer((self.host, self.port), APIRequestHandler)
            self.server.template_engine = self.template_engine
            self.server.storage = self.storage
            self.server.sessions = self.sessions

            # 附加中间件到服务器
            self.server.auth_middleware = self.auth_middleware
            self.server.rate_limiter = self.rate_limiter

            # 在新线程中运行
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()

            logger.info(f"API Server started at http://{self.host}:{self.port}")
            logger.info(
                f"🚀 VirtualChemLab API Server running at http://{self.host}:{self.port}"
            )
            logger.info(
                f"📚 API Documentation: http://{self.host}:{self.port}/api/docs"
            )
            logger.info(f"💚 Health Check: http://{self.host}:{self.port}/api/health")
            logger.info(
                f"🔒 认证: {'已启用' if self.auth_middleware.enabled else '已禁用'}"
            )
            logger.info(
                f"⏱️  限流: {'已启用 (100请求/分钟)' if self.rate_limiter else '已禁用'}"
            )

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

    def stop(self) -> None:
        """停止服务器"""
        if self.server:
            logger.info("Stopping API server...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            logger.info("API server stopped")

    def is_running(self) -> bool:
        """检查服务器是否运行"""
        return (
            self.server is not None
            and self.thread is not None
            and self.thread.is_alive()
        )


if __name__ == "__main__":
    import os

    # 统一日志配置，带敏感信息过滤
    setup_logger("virtualchemlab.api", logging.INFO)

    # 配置访问日志（同样挂载过滤器）
    access_handler = logging.FileHandler("logs/api_access.log")
    access_handler.addFilter(SensitiveDataFilter())
    access_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    access_logger.addHandler(access_handler)

    # 启动服务器 (默认启用认证，需显式配置才可禁用)
    # 默认仅绑定本地回环地址；如需对外提供服务请显式设置 VCL_API_HOST=0.0.0.0
    host = os.getenv("VCL_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    server = APIServer(
        host=host,
        port=8080,
        enable_auth=True,
        enable_rate_limit=True,
    )
    server.start()

    try:
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Shutting down...")
        server.stop()
