"""
SQLAlchemy数据库模型
定义所有数据表结构
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, index=True)
    role = Column(
        Enum(
            "student",
            "teacher",
            "admin",
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default="student",
        nullable=False,
    )

    # 元数据
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # 偏好设置（JSON格式）
    preferences = Column(JSON, default=dict)

    # 统计数据
    total_experiments = Column(Integer, default=0)
    total_score = Column(Float, default=0.0)

    # 关系
    experiment_records = relationship(
        "ExperimentRecord", back_populates="user", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_user_role_active", "role", "is_active"),
        Index("idx_user_created", "created_at"),
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"


class ExperimentRecord(Base):
    """实验记录表"""

    __tablename__ = "experiment_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(200), unique=True, nullable=False, index=True)
    user_id = Column(
        String(100), ForeignKey("users.user_id"), nullable=False, index=True
    )
    experiment_id = Column(String(200), nullable=False, index=True)
    experiment_title = Column(String(500), nullable=False)

    # 状态
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed
    current_step_index = Column(Integer, default=0)

    # 时间
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime)

    # 评分
    total_score = Column(Float, default=0.0)
    scientific_score = Column(Float, default=0.0)
    procedural_score = Column(Float, default=0.0)
    safety_score = Column(Float, default=0.0)
    score_details = Column(JSON, default=dict)

    # 实验数据（JSON格式存储复杂数据）
    step_records = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    curve_data = Column(JSON, default=dict)
    mistakes_summary = Column(JSON, default=list)

    # 元数据
    version = Column(String(50), default="1.0.0")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # 关系
    user = relationship("User", back_populates="experiment_records")

    # 索引
    __table_args__ = (
        Index("idx_exp_user_status", "user_id", "status"),
        Index("idx_exp_started", "started_at"),
        Index("idx_exp_completed", "completed_at"),
        Index("idx_exp_score", "total_score"),
    )

    def __repr__(self):
        return f"<ExperimentRecord(record_id='{self.record_id}', experiment_id='{self.experiment_id}')>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "experiment_id": self.experiment_id,
            "experiment_title": self.experiment_title,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "score": {
                "total": self.total_score,
                "scientific": self.scientific_score,
                "procedural": self.procedural_score,
                "safety": self.safety_score,
                "details": self.score_details,
            },
            "step_records": self.step_records,
            "context": self.context,
            "curve_data": self.curve_data,
            "mistakes_summary": self.mistakes_summary,
            "version": self.version,
        }


class Template(Base):
    """实验模板表"""

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(50), default="medium")  # easy, medium, hard

    # 模板内容（YAML/JSON格式）
    content = Column(Text, nullable=False)

    # 元数据
    version = Column(String(50), default="1.0.0")
    author = Column(String(200))
    description = Column(Text)
    tags = Column(JSON, default=list)

    # 使用统计
    usage_count = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)

    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # 索引
    __table_args__ = (
        Index("idx_template_category", "category"),
        Index("idx_template_difficulty", "difficulty"),
        Index("idx_template_usage", "usage_count"),
    )

    def __repr__(self):
        return f"<Template(template_id='{self.template_id}', name='{self.name}')>"


class Configuration(Base):
    """配置表"""

    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), default="string")  # string, int, float, bool, json
    category = Column(String(100), default="general", index=True)

    # 元数据
    description = Column(Text)
    is_system = Column(Boolean, default=False)  # 系统配置不可删除

    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # 索引
    __table_args__ = (Index("idx_config_category", "category"),)

    def __repr__(self):
        return f"<Configuration(key='{self.key}', category='{self.category}')>"

    def get_value(self) -> Any:
        """获取配置值（根据类型转换）"""
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return self.value
        else:
            return self.value


class License(Base):
    """许可证表"""

    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(
        String(100), ForeignKey("users.user_id"), nullable=False, index=True
    )
    device_id = Column(String(500), nullable=False, index=True)

    # 许可证信息
    license_type = Column(
        String(50), default="trial"
    )  # trial, standard, premium, enterprise
    max_devices = Column(Integer, default=1)

    # 时间
    issued_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime)
    activated_at = Column(DateTime)
    last_checked = Column(DateTime)

    # 状态
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)

    # 额外信息
    extra_data = Column(JSON, default=dict)

    # 索引
    __table_args__ = (
        Index("idx_license_user_device", "user_id", "device_id"),
        Index("idx_license_expires", "expires_at"),
        Index("idx_license_active", "is_active"),
    )

    def __repr__(self):
        return f"<License(user_id='{self.user_id}', device_id='{self.device_id}')>"


class CacheEntry(Base):
    """缓存条目表（持久化缓存）"""

    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(500), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)

    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, index=True)
    last_accessed = Column(DateTime, default=datetime.now)

    # 统计
    access_count = Column(Integer, default=0)

    # 索引
    __table_args__ = (Index("idx_cache_expires", "expires_at"),)

    def __repr__(self):
        return f"<CacheEntry(key='{self.key}')>"


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), index=True)
    resource_id = Column(String(200))

    # 详细信息
    details = Column(JSON, default=dict)
    ip_address = Column(String(100))
    user_agent = Column(String(500))

    # 结果
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # 时间
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 索引
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<AuditLog(user_id='{self.user_id}', action='{self.action}')>"


# 数据库版本信息
class DatabaseVersion(Base):
    """数据库版本表"""

    __tablename__ = "database_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False)
    applied_at = Column(DateTime, default=datetime.now, nullable=False)
    description = Column(Text)

    def __repr__(self):
        return f"<DatabaseVersion(version='{self.version}')>"
