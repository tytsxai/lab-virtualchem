"""REST API middleware helpers (auth / validation / rate limiting).

This module is shared by the stdlib-based REST API server (`src/api/server.py`).

Maintenance-safety notes:
- `AuthMiddleware` is the only supported API Key verifier; there is intentionally
  no hard-coded default key.
- API keys are loaded from `VCL_API_KEYS` (comma-separated). In non-production
  development, a key can be generated and persisted under the user runtime
  directory (`~/.virtualchemlab/config.json` + `api_key.txt`) to make local
  testing easy without weakening production defaults.
"""

import logging
import os
import secrets
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from ..utils.config import Config

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口(秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求

        Args:
            client_id: 客户端标识(IP地址等)

        Returns:
            是否允许
        """
        now = time.time()
        cutoff = now - self.time_window

        # 清理过期记录
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id] if req_time > cutoff
        ]

        # 检查是否超限
        if len(self._requests[client_id]) >= self.max_requests:
            return False

        # 记录本次请求
        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """获取剩余请求次数"""
        now = time.time()
        cutoff = now - self.time_window

        current_count = sum(
            1 for req_time in self._requests.get(client_id, []) if req_time > cutoff
        )

        return max(0, self.max_requests - current_count)


class AuthMiddleware:
    """认证中间件"""

    def __init__(self, enabled: bool = True):
        """初始化认证中间件

        Args:
            enabled: 是否启用认证
        """
        self.enabled = enabled
        # API密钥存储(生产环境应使用数据库/密钥管理服务)
        self._api_keys: dict[str, dict[str, Any]] = {}
        if self.enabled:
            self._load_or_initialize_keys()

    def verify_api_key(self, api_key: str) -> dict[str, Any] | None:
        """验证API密钥

        Args:
            api_key: API密钥

        Returns:
            客户端信息或None
        """
        if not self.enabled:
            return {"name": "Anonymous", "permissions": ["read", "write"]}

        return self._api_keys.get(api_key)

    def _load_or_initialize_keys(self) -> None:
        """从环境变量/用户配置加载密钥；若未配置则生成随机密钥并落盘到用户目录。

        安全默认值：不提供任何硬编码“默认密钥”，避免被浏览器跨站或本地回环攻击复用。
        """
        environment = (os.getenv("ENVIRONMENT") or "").strip().lower()
        is_production = environment == "production"

        # 1) 环境变量优先（支持多把密钥，用逗号分隔）
        raw = (os.getenv("VCL_API_KEYS") or "").strip()
        if raw:
            for idx, key in enumerate([p.strip() for p in raw.split(",") if p.strip()]):
                self._api_keys[key] = {
                    "name": f"Env Client {idx + 1}",
                    "permissions": ["read", "write"],
                    "created_at": datetime.now().isoformat(),
                }
            return

        # 2) 用户配置（~/.virtualchemlab/config.json）
        cfg = Config()
        configured_key = cfg.get("security.api_key")
        if isinstance(configured_key, str) and configured_key.strip():
            key = configured_key.strip()
            self._api_keys[key] = {
                "name": "User Config Client",
                "permissions": ["read", "write"],
                "created_at": datetime.now().isoformat(),
            }
            return

        # 生产环境禁止自动生成/落盘（容器/多副本会导致 key 漂移且难以回收）
        if is_production:
            raise RuntimeError(
                "生产环境必须显式配置 API Key：请设置环境变量 VCL_API_KEYS（可逗号分隔多把）"
                "或在挂载的用户配置文件中提供 security.api_key。"
            )

        # 3) 没有任何配置 -> 生成随机 key，并保存到用户可写目录
        generated = secrets.token_urlsafe(32)

        # 先注册到内存（确保本次进程内可用）
        self._api_keys[generated] = {
            "name": "Auto Generated Client",
            "permissions": ["read", "write"],
            "created_at": datetime.now().isoformat(),
        }

        cfg.set("security.api_key", generated)
        try:
            cfg.save()
        except Exception as e:
            raise RuntimeError(
                "未检测到 API 密钥配置，且无法写入用户配置文件。"
                "请设置环境变量 VCL_API_KEYS 提供至少一把密钥。"
            ) from e

        api_key_path = cfg.config_path.parent / "api_key.txt"
        try:
            api_key_path.write_text(generated + "\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            # 仅作为辅助文件；写失败不影响主配置落盘
            pass

        # 不在日志中输出密钥本体（避免落到集中日志/截图）；只提示路径
        logger.warning(
            "未检测到 API 密钥配置，已自动生成并保存到 %s；"
            "请在请求头使用 X-API-Key 或 Authorization: Bearer <key>。",
            str(api_key_path),
        )

    def add_api_key(self, api_key: str, name: str, permissions: list):
        """添加API密钥"""
        self._api_keys[api_key] = {
            "name": name,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
        }
        logger.info(f"已添加API密钥: {name}")

    def revoke_api_key(self, api_key: str):
        """撤销API密钥"""
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            logger.info(f"已撤销API密钥: {api_key}")


class RequestValidator:
    """请求验证器"""

    @staticmethod
    def validate_content_type(
        content_type: str, expected: str = "application/json"
    ) -> bool:
        """验证Content-Type

        Args:
            content_type: 实际Content-Type
            expected: 期望的Content-Type

        Returns:
            是否匹配
        """
        return content_type.startswith(expected)

    @staticmethod
    def validate_body_size(
        content_length: int, max_size: int = 10 * 1024 * 1024
    ) -> bool:
        """验证请求体大小

        Args:
            content_length: 请求体大小
            max_size: 最大大小(默认10MB)

        Returns:
            是否在限制内
        """
        return content_length <= max_size

    @staticmethod
    def validate_required_fields(
        data: dict, required_fields: list
    ) -> tuple[bool, str | None]:
        """验证必填字段

        Args:
            data: 请求数据
            required_fields: 必填字段列表

        Returns:
            (是否有效, 错误信息)
        """
        for field in required_fields:
            if field not in data:
                return False, f"缺少必填字段: {field}"
        return True, None


def require_auth(auth_middleware: AuthMiddleware):
    """需要认证的装饰器

    Args:
        auth_middleware: 认证中间件实例
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            # 提取API密钥
            api_key = handler.headers.get("X-API-Key") or handler.headers.get(
                "Authorization", ""
            ).replace("Bearer ", "")

            # 验证API密钥
            client_info = auth_middleware.verify_api_key(api_key)
            if not client_info:
                handler._send_error(401, "未授权: 无效的API密钥")
                return

            # 将客户端信息附加到handler
            handler.client_info = client_info

            # 调用原函数
            return func(handler, *args, **kwargs)

        return wrapper

    return decorator


def rate_limit(limiter: RateLimiter):
    """速率限制装饰器

    Args:
        limiter: 速率限制器实例
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            # 获取客户端标识
            client_id = handler.client_address[0]  # IP地址

            # 检查速率限制
            if not limiter.is_allowed(client_id):
                remaining = limiter.get_remaining(client_id)
                handler._send_error(
                    429, f"请求过于频繁,请稍后再试。剩余次数: {remaining}"
                )
                return

            # 调用原函数
            return func(handler, *args, **kwargs)

        return wrapper

    return decorator


def validate_request(required_fields: list | None = None):
    """请求验证装饰器

    Args:
        required_fields: 必填字段列表
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, body: dict, *args, **kwargs):
            validator = RequestValidator()

            # 验证必填字段
            if required_fields:
                valid, error = validator.validate_required_fields(body, required_fields)
                if not valid:
                    handler._send_error(400, error)
                    return

            # 调用原函数
            return func(handler, body, *args, **kwargs)

        return wrapper

    return decorator


# 全局实例
_rate_limiter: RateLimiter | None = None
_auth_middleware: AuthMiddleware | None = None


def get_rate_limiter(max_requests: int = 100, time_window: int = 60) -> RateLimiter:
    """获取全局速率限制器"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests, time_window)
    return _rate_limiter


def get_auth_middleware(enabled: bool = True) -> AuthMiddleware:
    """获取全局认证中间件"""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware(enabled)
    return _auth_middleware


if __name__ == "__main__":
    # 演示使用
    logger.info("=== API中间件演示 ===\n")

    # 速率限制器
    limiter = RateLimiter(max_requests=5, time_window=10)

    for i in range(7):
        allowed = limiter.is_allowed("client_1")
        remaining = limiter.get_remaining("client_1")
        logger.info(
            f"请求 {i + 1}: {'允许' if allowed else '拒绝'}, 剩余次数: {remaining}"
        )
        time.sleep(1)

    logger.info("\n" + "=" * 50 + "\n")

    # 认证中间件
    auth = AuthMiddleware()

    # 验证无效密钥
    client = auth.verify_api_key("invalid-key")
    logger.info(f"无效密钥: {client}")

    # 添加新密钥
    auth.add_api_key("new-key", "New Client", ["read"])
    logger.info("已添加新密钥")
