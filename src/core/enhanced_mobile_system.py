#!/usr/bin/env python3
"""
增强的移动端支持系统
提供响应式设计、触摸优化、离线功能等移动端特性
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .robustness_integration import enhance_robustness, log_operation

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """设备类型"""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    TV = "tv"
    WATCH = "watch"


class ScreenSize(Enum):
    """屏幕尺寸"""
    SMALL = "small"      # < 576px
    MEDIUM = "medium"    # 576px - 768px
    LARGE = "large"      # 768px - 992px
    XLARGE = "xlarge"    # 992px - 1200px
    XXLARGE = "xxlarge"  # > 1200px


class TouchGesture(Enum):
    """触摸手势"""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH_ZOOM = "pinch_zoom"
    ROTATE = "rotate"


class NetworkStatus(Enum):
    """网络状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    SLOW = "slow"
    UNSTABLE = "unstable"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    device_type: DeviceType
    screen_width: int
    screen_height: int
    screen_density: float
    orientation: str  # portrait, landscape
    user_agent: str
    platform: str  # ios, android, windows, macos, linux
    browser: str
    version: str
    capabilities: dict[str, bool] = field(default_factory=dict)


@dataclass
class TouchEvent:
    """触摸事件"""
    event_id: str
    gesture: TouchGesture
    x: float
    y: float
    timestamp: datetime
    duration: float = 0.0
    pressure: float = 0.0
    target_element: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponsiveLayout:
    """响应式布局"""
    breakpoint: ScreenSize
    columns: int
    gutter: int
    container_width: int
    sidebar_width: int
    header_height: int
    footer_height: int
    font_size_base: int
    spacing_unit: int
    touch_target_size: int


@dataclass
class OfflineData:
    """离线数据"""
    data_id: str
    data_type: str
    content: Any
    last_updated: datetime
    size: int
    priority: int
    ttl: float | None = None
    dependencies: list[str] = field(default_factory=list)


class EnhancedMobileSystem:
    """增强的移动端支持系统"""

    def __init__(self):
        self.devices: dict[str, DeviceInfo] = {}
        self.touch_events: list[TouchEvent] = []
        self.responsive_layouts: dict[ScreenSize, ResponsiveLayout] = {}
        self.offline_cache: dict[str, OfflineData] = {}
        self.network_status: NetworkStatus = NetworkStatus.ONLINE
        self.current_device: DeviceInfo | None = None

        # 初始化系统
        self._initialize_responsive_layouts()
        self._initialize_device_capabilities()

    def _initialize_responsive_layouts(self) -> None:
        """初始化响应式布局"""
        layouts = {
            ScreenSize.SMALL: ResponsiveLayout(
                breakpoint=ScreenSize.SMALL,
                columns=1,
                gutter=8,
                container_width=100,  # 百分比
                sidebar_width=0,  # 移动端隐藏侧边栏
                header_height=56,
                footer_height=60,
                font_size_base=14,
                spacing_unit=8,
                touch_target_size=44
            ),
            ScreenSize.MEDIUM: ResponsiveLayout(
                breakpoint=ScreenSize.MEDIUM,
                columns=2,
                gutter=12,
                container_width=100,
                sidebar_width=0,
                header_height=60,
                footer_height=64,
                font_size_base=15,
                spacing_unit=12,
                touch_target_size=48
            ),
            ScreenSize.LARGE: ResponsiveLayout(
                breakpoint=ScreenSize.LARGE,
                columns=3,
                gutter=16,
                container_width=100,
                sidebar_width=200,
                header_height=64,
                footer_height=68,
                font_size_base=16,
                spacing_unit=16,
                touch_target_size=48
            ),
            ScreenSize.XLARGE: ResponsiveLayout(
                breakpoint=ScreenSize.XLARGE,
                columns=4,
                gutter=20,
                container_width=1200,
                sidebar_width=250,
                header_height=68,
                footer_height=72,
                font_size_base=16,
                spacing_unit=20,
                touch_target_size=48
            ),
            ScreenSize.XXLARGE: ResponsiveLayout(
                breakpoint=ScreenSize.XXLARGE,
                columns=5,
                gutter=24,
                container_width=1400,
                sidebar_width=300,
                header_height=72,
                footer_height=76,
                font_size_base=18,
                spacing_unit=24,
                touch_target_size=52
            )
        }

        self.responsive_layouts = layouts
        logger.info("响应式布局已初始化")

    def _initialize_device_capabilities(self) -> None:
        """初始化设备能力"""
        # 这里可以添加设备能力检测逻辑
        pass

    @enhance_robustness(
        operation_name="detect_device",
        security_level="low",
        enable_caching=True
    )
    @log_operation(operation_name="detect_device")
    def detect_device(
        self,
        user_agent: str,
        screen_width: int,
        screen_height: int,
        screen_density: float = 1.0
    ) -> DeviceInfo:
        """检测设备信息"""
        device_id = f"device_{hash(user_agent)}_{screen_width}_{screen_height}"

        # 检测设备类型
        device_type = self._detect_device_type(screen_width, screen_height)

        # 检测平台
        platform = self._detect_platform(user_agent)

        # 检测浏览器
        browser = self._detect_browser(user_agent)

        # 检测能力
        capabilities = self._detect_capabilities(user_agent, device_type)

        device_info = DeviceInfo(
            device_id=device_id,
            device_type=device_type,
            screen_width=screen_width,
            screen_height=screen_height,
            screen_density=screen_density,
            orientation="portrait" if screen_height > screen_width else "landscape",
            user_agent=user_agent,
            platform=platform,
            browser=browser,
            version="1.0",
            capabilities=capabilities
        )

        self.devices[device_id] = device_info
        self.current_device = device_info

        logger.info(f"设备已检测: {device_type.value} - {screen_width}x{screen_height}")
        return device_info

    def _detect_device_type(self, width: int, height: int) -> DeviceType:
        """检测设备类型"""
        min_dimension = min(width, height)
        _max_dimension = max(width, height)

        if min_dimension < 576:
            return DeviceType.MOBILE
        elif min_dimension < 768:
            return DeviceType.TABLET
        elif min_dimension < 1024:
            return DeviceType.DESKTOP
        else:
            return DeviceType.DESKTOP

    def _detect_platform(self, user_agent: str) -> str:
        """检测平台"""
        user_agent_lower = user_agent.lower()

        if "iphone" in user_agent_lower or "ipad" in user_agent_lower:
            return "ios"
        elif "android" in user_agent_lower:
            return "android"
        elif "windows" in user_agent_lower:
            return "windows"
        elif "macintosh" in user_agent_lower or "mac os" in user_agent_lower:
            return "macos"
        elif "linux" in user_agent_lower:
            return "linux"
        else:
            return "unknown"

    def _detect_browser(self, user_agent: str) -> str:
        """检测浏览器"""
        user_agent_lower = user_agent.lower()

        if "chrome" in user_agent_lower:
            return "chrome"
        elif "firefox" in user_agent_lower:
            return "firefox"
        elif "safari" in user_agent_lower:
            return "safari"
        elif "edge" in user_agent_lower:
            return "edge"
        elif "opera" in user_agent_lower:
            return "opera"
        else:
            return "unknown"

    def _detect_capabilities(self, _user_agent: str, device_type: DeviceType) -> dict[str, bool]:
        """检测设备能力"""
        capabilities = {
            "touch": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "geolocation": True,
            "camera": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "microphone": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "accelerometer": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "gyroscope": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "vibration": device_type in [DeviceType.MOBILE, DeviceType.TABLET],
            "push_notifications": True,
            "offline_storage": True,
            "webgl": True,
            "websockets": True
        }

        return capabilities

    @enhance_robustness(
        operation_name="get_responsive_layout",
        security_level="low",
        enable_caching=True
    )
    def get_responsive_layout(self, screen_width: int) -> ResponsiveLayout:
        """获取响应式布局"""
        if screen_width < 576:
            return self.responsive_layouts[ScreenSize.SMALL]
        elif screen_width < 768:
            return self.responsive_layouts[ScreenSize.MEDIUM]
        elif screen_width < 992:
            return self.responsive_layouts[ScreenSize.LARGE]
        elif screen_width < 1200:
            return self.responsive_layouts[ScreenSize.XLARGE]
        else:
            return self.responsive_layouts[ScreenSize.XXLARGE]

    @enhance_robustness(
        operation_name="handle_touch_event",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="touch_event")
    def handle_touch_event(
        self,
        gesture: str,
        x: float,
        y: float,
        duration: float = 0.0,
        pressure: float = 0.0,
        target_element: str = ""
    ) -> TouchEvent:
        """处理触摸事件"""
        try:
            gesture_enum = TouchGesture(gesture)
        except ValueError:
            gesture_enum = TouchGesture.TAP

        touch_event = TouchEvent(
            event_id=f"touch_{int(time.time() * 1000)}",
            gesture=gesture_enum,
            x=x,
            y=y,
            timestamp=datetime.now(),
            duration=duration,
            pressure=pressure,
            target_element=target_element
        )

        self.touch_events.append(touch_event)

        # 保持最近1000个事件
        if len(self.touch_events) > 1000:
            self.touch_events = self.touch_events[-1000:]

        logger.debug(f"触摸事件已处理: {gesture} at ({x}, {y})")
        return touch_event

    @enhance_robustness(
        operation_name="cache_offline_data",
        security_level="medium",
        enable_caching=False
    )
    @log_operation(operation_name="cache_data")
    def cache_offline_data(
        self,
        data_id: str,
        data_type: str,
        content: Any,
        priority: int = 1,
        ttl: float | None = None,
        dependencies: list[str] | None = None
    ) -> OfflineData:
        """缓存离线数据"""
        # 计算数据大小
        try:
            size = len(json.dumps(content))
        except (TypeError, ValueError):
            size = 0

        offline_data = OfflineData(
            data_id=data_id,
            data_type=data_type,
            content=content,
            last_updated=datetime.now(),
            size=size,
            priority=priority,
            ttl=ttl,
            dependencies=dependencies or []
        )

        self.offline_cache[data_id] = offline_data

        logger.info(f"离线数据已缓存: {data_id} ({size} bytes)")
        return offline_data

    @enhance_robustness(
        operation_name="get_offline_data",
        security_level="low",
        enable_caching=True
    )
    def get_offline_data(self, data_id: str) -> OfflineData | None:
        """获取离线数据"""
        if data_id not in self.offline_cache:
            return None

        data = self.offline_cache[data_id]

        # 检查TTL
        if data.ttl:
            age = (datetime.now() - data.last_updated).total_seconds()
            if age > data.ttl:
                del self.offline_cache[data_id]
                return None

        return data

    @enhance_robustness(
        operation_name="update_network_status",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="network_status")
    def update_network_status(self, status: str) -> bool:
        """更新网络状态"""
        try:
            self.network_status = NetworkStatus(status)
            logger.info(f"网络状态已更新: {status}")
            return True
        except ValueError:
            logger.warning(f"无效的网络状态: {status}")
            return False

    @enhance_robustness(
        operation_name="get_mobile_optimizations",
        security_level="low",
        enable_caching=True
    )
    def get_mobile_optimizations(self, device_id: str) -> dict[str, Any]:
        """获取移动端优化建议"""
        if device_id not in self.devices:
            return {}

        device = self.devices[device_id]
        layout = self.get_responsive_layout(device.screen_width)

        optimizations = {
            "layout": {
                "columns": layout.columns,
                "gutter": layout.gutter,
                "container_width": layout.container_width,
                "sidebar_width": layout.sidebar_width,
                "header_height": layout.header_height,
                "footer_height": layout.footer_height
            },
            "typography": {
                "font_size_base": layout.font_size_base,
                "spacing_unit": layout.spacing_unit
            },
            "touch": {
                "target_size": layout.touch_target_size,
                "gestures_enabled": device.capabilities.get("touch", False)
            },
            "performance": {
                "lazy_loading": True,
                "image_optimization": True,
                "code_splitting": True,
                "caching": True
            },
            "features": {
                "offline_mode": device.capabilities.get("offline_storage", False),
                "push_notifications": device.capabilities.get("push_notifications", False),
                "geolocation": device.capabilities.get("geolocation", False),
                "camera": device.capabilities.get("camera", False),
                "microphone": device.capabilities.get("microphone", False)
            }
        }

        return optimizations

    @enhance_robustness(
        operation_name="generate_mobile_css",
        security_level="low",
        enable_caching=True
    )
    def generate_mobile_css(self, device_id: str) -> str:
        """生成移动端CSS"""
        if device_id not in self.devices:
            return ""

        device = self.devices[device_id]
        layout = self.get_responsive_layout(device.screen_width)

        css = f"""
/* 移动端优化CSS - {device.device_type.value} */
:root {{
    --mobile-columns: {layout.columns};
    --mobile-gutter: {layout.gutter}px;
    --mobile-container-width: {layout.container_width}%;
    --mobile-sidebar-width: {layout.sidebar_width}px;
    --mobile-header-height: {layout.header_height}px;
    --mobile-footer-height: {layout.footer_height}px;
    --mobile-font-size-base: {layout.font_size_base}px;
    --mobile-spacing-unit: {layout.spacing_unit}px;
    --mobile-touch-target-size: {layout.touch_target_size}px;
}}

/* 响应式网格 */
.mobile-grid {{
    display: grid;
    grid-template-columns: repeat(var(--mobile-columns), 1fr);
    gap: var(--mobile-gutter);
    padding: var(--mobile-spacing-unit);
}}

/* 触摸优化 */
.touch-target {{
    min-height: var(--mobile-touch-target-size);
    min-width: var(--mobile-touch-target-size);
    padding: calc(var(--mobile-spacing-unit) / 2);
}}

/* 移动端导航 */
.mobile-nav {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--mobile-footer-height);
    background: var(--surface);
    border-top: 1px solid var(--border);
    z-index: 1000;
}}

/* 移动端侧边栏 */
.mobile-sidebar {{
    position: fixed;
    top: var(--mobile-header-height);
    left: -100%;
    width: var(--mobile-sidebar-width);
    height: calc(100vh - var(--mobile-header-height));
    background: var(--surface);
    transition: left 0.3s ease;
    z-index: 999;
}}

.mobile-sidebar.open {{
    left: 0;
}}

/* 移动端内容区域 */
.mobile-content {{
    padding-top: var(--mobile-header-height);
    padding-bottom: var(--mobile-footer-height);
    min-height: 100vh;
}}

/* 移动端头部 */
.mobile-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--mobile-header-height);
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    z-index: 1001;
}}

/* 触摸手势反馈 */
.touch-feedback {{
    transition: transform 0.1s ease, opacity 0.1s ease;
}}

.touch-feedback:active {{
    transform: scale(0.95);
    opacity: 0.7;
}}

/* 移动端实验界面 */
.mobile-experiment {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
}}

.mobile-experiment-canvas {{
    flex: 1;
    touch-action: none;
    user-select: none;
}}

/* 移动端工具面板 */
.mobile-toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: var(--mobile-spacing-unit);
    padding: var(--mobile-spacing-unit);
    background: var(--surface);
    border-top: 1px solid var(--border);
}}

.mobile-tool {{
    flex: 1;
    min-width: calc(var(--mobile-touch-target-size) * 2);
    height: var(--mobile-touch-target-size);
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--background);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}}

/* 移动端模态框 */
.mobile-modal {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--mobile-spacing-unit);
}}

.mobile-modal-content {{
    background: var(--surface);
    border-radius: 8px;
    padding: var(--mobile-spacing-unit);
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
}}

/* 移动端表单 */
.mobile-form {{
    display: flex;
    flex-direction: column;
    gap: var(--mobile-spacing-unit);
}}

.mobile-input {{
    height: var(--mobile-touch-target-size);
    padding: 0 var(--mobile-spacing-unit);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: var(--mobile-font-size-base);
}}

.mobile-button {{
    height: var(--mobile-touch-target-size);
    padding: 0 var(--mobile-spacing-unit);
    border: none;
    border-radius: 4px;
    background: var(--primary);
    color: white;
    font-size: var(--mobile-font-size-base);
    cursor: pointer;
}}

/* 移动端列表 */
.mobile-list {{
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: var(--border);
}}

.mobile-list-item {{
    background: var(--surface);
    padding: var(--mobile-spacing-unit);
    min-height: var(--mobile-touch-target-size);
    display: flex;
    align-items: center;
    cursor: pointer;
}}

/* 移动端卡片 */
.mobile-card {{
    background: var(--surface);
    border-radius: 8px;
    padding: var(--mobile-spacing-unit);
    margin-bottom: var(--mobile-spacing-unit);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}}

/* 移动端加载状态 */
.mobile-loading {{
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100px;
    color: var(--text-secondary);
}}

/* 移动端错误状态 */
.mobile-error {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: var(--danger);
    text-align: center;
    padding: var(--mobile-spacing-unit);
}}

/* 移动端成功状态 */
.mobile-success {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: var(--success);
    text-align: center;
    padding: var(--mobile-spacing-unit);
}}
"""

        return css

    @enhance_robustness(
        operation_name="get_touch_analytics",
        security_level="low",
        enable_caching=True
    )
    def get_touch_analytics(self, limit: int = 100) -> dict[str, Any]:
        """获取触摸分析"""
        recent_events = self.touch_events[-limit:] if self.touch_events else []

        if not recent_events:
            return {
                "total_events": 0,
                "gesture_distribution": {},
                "average_pressure": 0.0,
                "average_duration": 0.0,
                "most_used_elements": {}
            }

        # 统计手势分布
        gesture_distribution = {}
        for event in recent_events:
            gesture = event.gesture.value
            gesture_distribution[gesture] = gesture_distribution.get(gesture, 0) + 1

        # 计算平均压力
        pressures = [event.pressure for event in recent_events if event.pressure > 0]
        average_pressure = sum(pressures) / len(pressures) if pressures else 0.0

        # 计算平均持续时间
        durations = [event.duration for event in recent_events if event.duration > 0]
        average_duration = sum(durations) / len(durations) if durations else 0.0

        # 统计最常用的元素
        element_usage = {}
        for event in recent_events:
            if event.target_element:
                element_usage[event.target_element] = element_usage.get(event.target_element, 0) + 1

        return {
            "total_events": len(recent_events),
            "gesture_distribution": gesture_distribution,
            "average_pressure": average_pressure,
            "average_duration": average_duration,
            "most_used_elements": dict(sorted(element_usage.items(), key=lambda x: x[1], reverse=True)[:10])
        }


# 全局实例
enhanced_mobile_system = EnhancedMobileSystem()
