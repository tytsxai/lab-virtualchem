"""
前端性能优化模块
"""

from .lazy_loader import (
    AsyncLoader,
    CodeSplitter,
    ImageLazyLoader,
    LazyLoader,
    ViewportLoader,
    lazy_load,
)
from .request_merger import (
    DataLoader,
    RequestDeduplicator,
    RequestMerger,
    RequestQueue,
    get_data_loader,
    get_request_merger,
    register_data_loader,
)
from .virtual_list import InfiniteScrollList, VirtualListWidget, VirtualTreeWidget

__all__ = [
    # 懒加载
    "LazyLoader",
    "ImageLazyLoader",
    "AsyncLoader",
    "lazy_load",
    "CodeSplitter",
    "ViewportLoader",
    # 虚拟列表
    "VirtualListWidget",
    "VirtualTreeWidget",
    "InfiniteScrollList",
    # 请求合并
    "RequestMerger",
    "DataLoader",
    "RequestDeduplicator",
    "RequestQueue",
    "get_request_merger",
    "register_data_loader",
    "get_data_loader",
]
