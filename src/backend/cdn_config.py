"""
CDN配置模块
静态资源CDN加速配置
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CDNConfig:
    """CDN配置"""

    provider: str  # 'cloudflare', 'aws', 'aliyun', 'local'
    base_url: str
    api_key: str | None = None
    zone_id: str | None = None
    cache_rules: dict[str, int] | None = None  # 文件类型 -> 缓存时间(秒)

    def __post_init__(self) -> None:
        if self.cache_rules is None:
            self.cache_rules = {
                "image": 86400 * 30,  # 图片: 30天
                "css": 86400 * 7,  # CSS: 7天
                "js": 86400 * 7,  # JS: 7天
                "font": 86400 * 365,  # 字体: 1年
                "video": 86400 * 30,  # 视频: 30天
            }


class CDNManager:
    """CDN管理器"""

    def __init__(self, config: CDNConfig):
        """
        初始化CDN管理器

        Args:
            config: CDN配置
        """
        self.config = config
        self._url_cache: dict[str, str] = {}

    def get_url(self, resource_path: str) -> str:
        """
        获取资源的CDN URL

        Args:
            resource_path: 资源路径

        Returns:
            CDN URL
        """
        # 检查缓存
        if resource_path in self._url_cache:
            return self._url_cache[resource_path]

        # 生成CDN URL
        if self.config.provider == "local":
            # 本地模式，直接返回原路径
            cdn_url = f"/static/{resource_path}"
        else:
            # CDN模式
            cdn_url = f"{self.config.base_url}/{resource_path}"

        # 缓存
        self._url_cache[resource_path] = cdn_url

        return cdn_url

    def get_cache_control(self, file_extension: str) -> str:
        """
        获取缓存控制头

        Args:
            file_extension: 文件扩展名

        Returns:
            Cache-Control值
        """
        # 确定文件类型
        file_type = self._get_file_type(file_extension)

        # 获取缓存时间
        cache_rules = self.config.cache_rules or {}
        cache_time = cache_rules.get(file_type, 3600)

        return f"public, max-age={cache_time}"

    def _get_file_type(self, extension: str) -> str:
        """
        根据扩展名判断文件类型

        Args:
            extension: 文件扩展名

        Returns:
            文件类型
        """
        extension = extension.lower().lstrip(".")

        type_mapping = {
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gi": "image",
            "webp": "image",
            "svg": "image",
            "css": "css",
            "js": "js",
            "mjs": "js",
            "wof": "font",
            "woff2": "font",
            "tt": "font",
            "eot": "font",
            "mp4": "video",
            "webm": "video",
            "ogg": "video",
        }

        return type_mapping.get(extension, "other")

    def purge_cache(self, paths: list[str] | None = None) -> bool:
        """
        清除CDN缓存

        Args:
            paths: 要清除的路径列表(None表示全部)

        Returns:
            是否成功
        """
        if self.config.provider == "local":
            logger.info("本地模式，无需清除CDN缓存")
            return True

        # 这里需要调用具体CDN提供商的API
        # 以下是示例逻辑
        try:
            if self.config.provider == "cloudflare":
                return self._purge_cloudflare(paths)
            elif self.config.provider == "aws":
                return self._purge_aws(paths)
            elif self.config.provider == "aliyun":
                return self._purge_aliyun(paths)
            else:
                logger.warning(f"未知的CDN提供商: {self.config.provider}")
                return False
        except Exception as e:
            logger.error(f"清除CDN缓存失败: {e}")
            return False

    def _purge_cloudflare(self, paths: list[str] | None) -> bool:
        """清除Cloudflare缓存"""
        # 实际实现需要调用Cloudflare API
        _ = paths  # 未来使用
        logger.info("清除Cloudflare缓存")
        return True

    def _purge_aws(self, paths: list[str] | None) -> bool:
        """清除AWS CloudFront缓存"""
        # 实际实现需要调用AWS API
        _ = paths  # 未来使用
        logger.info("清除AWS CloudFront缓存")
        return True

    def _purge_aliyun(self, paths: list[str] | None) -> bool:
        """清除阿里云CDN缓存"""
        # 实际实现需要调用阿里云API
        _ = paths  # 未来使用
        logger.info("清除阿里云CDN缓存")
        return True


class StaticResourceOptimizer:
    """静态资源优化器"""

    def __init__(self, cdn_manager: CDNManager):
        """
        初始化优化器

        Args:
            cdn_manager: CDN管理器
        """
        self.cdn_manager = cdn_manager

    def optimize_html(self, html: str) -> str:
        """
        优化HTML中的静态资源引用

        Args:
            html: HTML内容

        Returns:
            优化后的HTML
        """
        import re

        # 替换图片src
        def replace_img(match: re.Match[str]) -> str:
            src = match.group(1)
            cdn_url = self.cdn_manager.get_url(src)
            return f'src="{cdn_url}"'

        html = re.sub(r'src="([^"]+\.(jpg|jpeg|png|gif|webp|svg))"', replace_img, html)

        # 替换CSS href
        def replace_css(match: re.Match[str]) -> str:
            href = match.group(1)
            cdn_url = self.cdn_manager.get_url(href)
            return f'href="{cdn_url}"'

        html = re.sub(r'href="([^"]+\.css)"', replace_css, html)

        # 替换JS src
        def replace_js(match: re.Match[str]) -> str:
            src = match.group(1)
            cdn_url = self.cdn_manager.get_url(src)
            return f'src="{cdn_url}"'

        html = re.sub(r'src="([^"]+\.js)"', replace_js, html)

        return html

    def generate_manifest(self, static_dir: Path) -> dict[str, str]:
        """
        生成资源清单

        Args:
            static_dir: 静态资源目录

        Returns:
            资源清单 {本地路径: CDN URL}
        """
        manifest = {}

        for file_path in static_dir.rglob("*"):
            if file_path.is_file():
                # 相对路径
                rel_path = file_path.relative_to(static_dir)
                cdn_url = self.cdn_manager.get_url(str(rel_path))
                manifest[str(rel_path)] = cdn_url

        return manifest

    def add_version_hash(self, url: str, content_hash: str) -> str:
        """
        添加版本哈希到URL

        Args:
            url: 原始URL
            content_hash: 内容哈希

        Returns:
            带版本的URL
        """
        if "?" in url:
            return f"{url}&v={content_hash[:8]}"
        else:
            return f"{url}?v={content_hash[:8]}"


class ResourcePreloader:
    """资源预加载器"""

    @staticmethod
    def generate_preload_links(resources: list[dict[str, str]]) -> str:
        """
        生成预加载链接标签

        Args:
            resources: 资源列表 [{'url': '...', 'type': 'font|image|script|style'}]

        Returns:
            HTML link标签
        """
        links = []

        for resource in resources:
            url = resource["url"]
            res_type = resource["type"]

            if res_type == "font":
                links.append(f'<link rel="preload" href="{url}" as="font" type="font/woff2" crossorigin>')
            elif res_type == "image":
                links.append(f'<link rel="preload" href="{url}" as="image">')
            elif res_type == "script":
                links.append(f'<link rel="preload" href="{url}" as="script">')
            elif res_type == "style":
                links.append(f'<link rel="preload" href="{url}" as="style">')

        return "\n".join(links)

    @staticmethod
    def generate_dns_prefetch(domains: list[str]) -> str:
        """
        生成DNS预取标签

        Args:
            domains: 域名列表

        Returns:
            HTML link标签
        """
        return "\n".join([f'<link rel="dns-prefetch" href="//{domain}">' for domain in domains])


class CDNConfigBuilder:
    """CDN配置构建器"""

    @staticmethod
    def from_file(config_path: str) -> CDNConfig:
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            CDN配置
        """
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        return CDNConfig(**data)

    @staticmethod
    def create_local_config(base_url: str = "/static") -> CDNConfig:
        """
        创建本地配置

        Args:
            base_url: 基础URL

        Returns:
            CDN配置
        """
        return CDNConfig(provider="local", base_url=base_url)

    @staticmethod
    def create_cloudflare_config(zone_id: str, api_key: str, base_url: str) -> CDNConfig:
        """
        创建Cloudflare配置

        Args:
            zone_id: Zone ID
            api_key: API密钥
            base_url: 基础URL

        Returns:
            CDN配置
        """
        return CDNConfig(provider="cloudflare", base_url=base_url, zone_id=zone_id, api_key=api_key)


# 全局CDN管理器
_cdn_manager: CDNManager | None = None


def init_cdn(config: CDNConfig) -> CDNManager:
    """
    初始化全局CDN管理器

    Args:
        config: CDN配置

    Returns:
        CDN管理器
    """
    global _cdn_manager
    _cdn_manager = CDNManager(config)
    return _cdn_manager


def get_cdn_manager() -> CDNManager | None:
    """获取全局CDN管理器"""
    return _cdn_manager


if __name__ == "__main__":
    # 演示使用
    logger.info("=== CDN配置演示 ===\n")

    # 创建本地配置
    config = CDNConfigBuilder.create_local_config()
    manager = CDNManager(config)

    # 获取CDN URL
    urls = ["images/logo.png", "styles/main.css", "scripts/app.js"]

    logger.info("CDN URLs:")
    for url in urls:
        cdn_url = manager.get_url(url)
        logger.info(f"  {url} -> {cdn_url}")

    # 缓存控制
    logger.info("\n缓存控制:")
    extensions = ["png", "css", "js", "woff2"]
    for ext in extensions:
        cache_control = manager.get_cache_control(ext)
        logger.info(f"  .{ext}: {cache_control}")

    # 预加载
    logger.info("\n预加载链接:")
    resources = [
        {"url": "/static/fonts/main.woff2", "type": "font"},
        {"url": "/static/images/hero.jpg", "type": "image"},
    ]
    preload_html = ResourcePreloader.generate_preload_links(resources)
    logger.info(preload_html)
