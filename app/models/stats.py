from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.core.database import Base


class UserProfile(Base):
    """用户基础画像表。"""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gender = Column(String(10), nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String(50), nullable=False)
    signup_ts = Column(DateTime, nullable=False, comment="注册时间")


class BehaviorLog(Base):
    """用户行为聚合日志。"""

    __tablename__ = "behavior_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    pv = Column(Integer, nullable=False, comment="页面浏览量")
    uv = Column(Integer, nullable=False, comment="独立访客数")
    duration = Column(Integer, nullable=False, comment="平均停留秒数")


class SearchLog(Base):
    """搜索行为日志。"""

    __tablename__ = "search_logs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "timestamp",
            name="uq_search_log_user_time",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    query = Column(String(500), nullable=True, index=True, comment="搜索查询词")
    clicked_doc_id = Column(String(255), nullable=True, index=True, comment="点击的文档ID")
    clicked_doc_title = Column(String(500), nullable=True, comment="点击的文档标题")
