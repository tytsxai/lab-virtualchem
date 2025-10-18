"""
协作功能模块
提供多用户协作、实时同步、团队管理等功能
"""

from .collaboration_manager import CollaborationManager, CollaborationSession
from .real_time_sync import RealTimeSync, SyncEvent
from .shared_workspace import SharedWorkspace, WorkspaceItem
from .team_manager import Team, TeamManager, TeamMember

__all__ = [
    # 协作管理
    "CollaborationManager",
    "CollaborationSession",
    # 实时同步
    "RealTimeSync",
    "SyncEvent",
    # 团队管理
    "TeamManager",
    "Team",
    "TeamMember",
    # 共享工作区
    "SharedWorkspace",
    "WorkspaceItem",
]
