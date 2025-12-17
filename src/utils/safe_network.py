"""安全的网络操作

提供带错误处理和重试机制的网络请求
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from enum import Enum
from types import SimpleNamespace

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

    # Provide a stub so callers/tests can monkeypatch `safe_network.requests`
    # even when `requests` isn't installed.
    class _RequestError(Exception):
        pass

    class _ConnectionError(_RequestError):
        pass

    class _Timeout(_RequestError):
        pass

    class _HTTPError(_RequestError):
        pass

    class _SSLError(_RequestError):
        pass

    def _missing(*_args, **_kwargs):
        raise ImportError("requests库未安装，无法发送网络请求")

    requests = SimpleNamespace(
        request=_missing,
        get=_missing,
        exceptions=SimpleNamespace(
            ConnectionError=_ConnectionError,
            Timeout=_Timeout,
            HTTPError=_HTTPError,
            SSLError=_SSLError,
        ),
    )

from .enhanced_error_handler import (
    ErrorSeverity,
    handle_errors,
)

logger = logging.getLogger(__name__)


class NetworkErrorType(Enum):
    """网络错误类型"""

    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    SSL_ERROR = "ssl_error"
    UNKNOWN = "unknown"


class RetryStrategy:
    """重试策略"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 30.0,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.initial_delay * (self.backoff_factor**attempt)
        return min(delay, self.max_delay)


class SafeNetworkClient:
    """安全的网络客户端"""

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        retry_strategy: RetryStrategy | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_strategy = retry_strategy or RetryStrategy()

        if not HAS_REQUESTS:
            logger.warning("requests库未安装，网络功能将受限")

    @handle_errors(
        context="发送HTTP请求",
        user_message="网络请求失败",
        severity=ErrorSeverity.ERROR,
        default_return=None,
    )
    def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> dict | None:
        """发送HTTP请求（带重试）

        Args:
            method: HTTP方法
            url: URL
            **kwargs: requests参数

        Returns:
            响应数据
        """
        if not HAS_REQUESTS:
            raise ImportError("requests库未安装，无法发送网络请求")

        # 构建完整URL
        if not url.startswith("http"):
            url = f"{self.base_url}{url}"

        # 设置超时
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        last_error = None
        for attempt in range(self.retry_strategy.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()

                # 尝试解析JSON
                try:
                    return response.json()
                except ValueError:
                    return {"text": response.text}

            except requests.exceptions.ConnectionError as e:
                last_error = e
                error_type = NetworkErrorType.CONNECTION_ERROR
                logger.warning(
                    f"连接错误 (尝试 {attempt + 1}/{self.retry_strategy.max_retries}): {e}"
                )

            except requests.exceptions.Timeout as e:
                last_error = e
                error_type = NetworkErrorType.TIMEOUT
                logger.warning(
                    f"请求超时 (尝试 {attempt + 1}/{self.retry_strategy.max_retries}): {e}"
                )

            except requests.exceptions.HTTPError as e:
                # HTTP错误通常不重试
                last_error = e
                error_type = NetworkErrorType.HTTP_ERROR
                status_code = e.response.status_code

                if status_code >= 500:
                    # 服务器错误，可以重试
                    logger.warning(
                        f"服务器错误 {status_code} (尝试 {attempt + 1}/{self.retry_strategy.max_retries}): {e}"
                    )
                else:
                    # 客户端错误，不重试
                    raise self._create_friendly_http_error(status_code, e)

            except requests.exceptions.SSLError as e:
                last_error = e
                error_type = NetworkErrorType.SSL_ERROR
                raise ConnectionError(f"SSL证书验证失败: {e}") from e

            except Exception as e:
                last_error = e
                error_type = NetworkErrorType.UNKNOWN
                logger.warning(
                    f"未知错误 (尝试 {attempt + 1}/{self.retry_strategy.max_retries}): {e}"
                )

            # 如果还有重试机会，等待后重试
            if attempt < self.retry_strategy.max_retries - 1:
                delay = self.retry_strategy.get_delay(attempt)
                logger.info(f"等待{delay:.1f}秒后重试...")
                time.sleep(delay)

        # 所有重试都失败
        if last_error:
            raise self._create_friendly_network_error(error_type, last_error)

        return None

    def _create_friendly_http_error(
        self, status_code: int, original_error: Exception
    ) -> Exception:
        """创建友好的HTTP错误"""
        error_messages = {
            400: "请求参数错误",
            401: "未授权，请先登录",
            403: "没有权限访问此资源",
            404: "请求的资源不存在",
            405: "不支持的请求方法",
            408: "请求超时",
            429: "请求过于频繁，请稍后重试",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务暂时不可用",
            504: "网关超时",
        }

        message = error_messages.get(status_code, f"HTTP错误 {status_code}")
        return ValueError(f"{message}: {original_error}")

    def _create_friendly_network_error(
        self, error_type: NetworkErrorType, original_error: Exception
    ) -> Exception:
        """创建友好的网络错误"""
        error_messages = {
            NetworkErrorType.CONNECTION_ERROR: "无法连接到服务器，请检查网络连接",
            NetworkErrorType.TIMEOUT: "请求超时，请检查网络连接或稍后重试",
            NetworkErrorType.HTTP_ERROR: "服务器返回错误",
            NetworkErrorType.SSL_ERROR: "SSL证书验证失败，连接不安全",
            NetworkErrorType.UNKNOWN: "网络请求失败",
        }

        message = error_messages.get(error_type, "网络请求失败")
        return ConnectionError(f"{message}: {original_error}")

    def get(self, url: str, params: dict = None, **kwargs) -> dict | None:
        """GET请求"""
        return self.request("GET", url, params=params, **kwargs)

    def post(
        self, url: str, data: dict = None, json: dict = None, **kwargs
    ) -> dict | None:
        """POST请求"""
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(
        self, url: str, data: dict = None, json: dict = None, **kwargs
    ) -> dict | None:
        """PUT请求"""
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> dict | None:
        """DELETE请求"""
        return self.request("DELETE", url, **kwargs)

    @handle_errors(
        context="检查网络连接",
        user_message="无法检查网络连接",
        severity=ErrorSeverity.WARNING,
        default_return=False,
    )
    def check_connection(self, test_url: str = "https://www.baidu.com") -> bool:
        """检查网络连接

        Args:
            test_url: 用于测试的URL

        Returns:
            是否连接正常
        """
        if not HAS_REQUESTS:
            logger.warning("requests库未安装，无法检查网络连接")
            return False

        try:
            response = requests.get(test_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"网络连接检查失败: {e}")
            return False

    @handle_errors(
        context="下载文件",
        user_message="文件下载失败",
        severity=ErrorSeverity.ERROR,
        default_return=False,
    )
    def download_file(
        self,
        url: str,
        save_path: str,
        chunk_size: int = 8192,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> bool:
        """下载文件

        Args:
            url: 文件URL
            save_path: 保存路径
            chunk_size: 分块大小
            progress_callback: 进度回调函数(已下载, 总大小)

        Returns:
            是否成功
        """
        if not HAS_REQUESTS:
            raise ImportError("requests库未安装，无法下载文件")

        response = requests.get(url, stream=True, timeout=self.timeout)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        logger.info(f"文件下载完成: {save_path} ({downloaded} 字节)")
        return True


class NetworkHealthMonitor:
    """网络健康监控"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.is_online = True
        self.last_check_time = 0

    def is_network_available(self) -> bool:
        """检查网络是否可用"""
        current_time = time.time()

        # 如果距离上次检查不到check_interval秒，返回缓存结果
        if current_time - self.last_check_time < self.check_interval:
            return self.is_online

        # 执行新的检查
        client = SafeNetworkClient()
        self.is_online = client.check_connection()
        self.last_check_time = current_time

        return self.is_online

    def wait_for_network(self, timeout: int = 60, check_interval: int = 5) -> bool:
        """等待网络恢复

        Args:
            timeout: 最大等待时间（秒）
            check_interval: 检查间隔（秒）

        Returns:
            网络是否恢复
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_network_available():
                logger.info("网络连接已恢复")
                return True

            logger.debug(f"等待网络恢复... ({int(time.time() - start_time)}s)")
            time.sleep(check_interval)

        logger.warning(f"等待网络恢复超时 ({timeout}s)")
        return False


# 便捷函数
def safe_get(url: str, **kwargs) -> dict | None:
    """安全的GET请求"""
    client = SafeNetworkClient()
    return client.get(url, **kwargs)


def safe_post(url: str, **kwargs) -> dict | None:
    """安全的POST请求"""
    client = SafeNetworkClient()
    return client.post(url, **kwargs)


def check_network() -> bool:
    """检查网络连接"""
    monitor = NetworkHealthMonitor()
    return monitor.is_network_available()


__all__ = [
    "NetworkErrorType",
    "RetryStrategy",
    "SafeNetworkClient",
    "NetworkHealthMonitor",
    "safe_get",
    "safe_post",
    "check_network",
]
