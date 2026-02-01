from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, Float

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
    # 移除唯一约束，允许同一时间戳多条记录（高并发场景）
    # __table_args__ = (
    #     UniqueConstraint(
    #         "user_id",
    #         "timestamp",
    #         name="uq_search_log_user_time",
    #     ),
    # )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)  # 修改为 String 支持 UUID
    timestamp = Column(DateTime, nullable=False, index=True)
    # 取消 index=True 以避免 "Specified key was too long" 错误 (UTF8MB4下 2000 chars * 4 > 3072 bytes)
    query = Column(String(2000), nullable=True, comment="搜索查询词")
    
    # RAG 新增字段
    answer = Column(Text, nullable=True, comment="RAG生成的回答")
    trace_id = Column(String(64), nullable=True, index=True, comment="追踪ID")
    latency = Column(Float, nullable=True, comment="耗时(秒)")
    status = Column(Integer, default=1, comment="0:失败 1:成功")

    # 兼容旧字段（可选保留）
    clicked_doc_id = Column(String(255), nullable=True, index=True, comment="点击的文档ID")
    clicked_doc_title = Column(String(500), nullable=True, comment="点击的文档标题")
