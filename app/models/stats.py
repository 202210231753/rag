"""统计相关的数据模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class BehaviorLog(Base):
    """行为日志。"""
    __tablename__ = "behavior_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, comment="用户ID")
    timestamp = Column(DateTime, default=datetime.now, index=True, comment="时间戳")
    action = Column(String(50), comment="行为类型")
    content = Column(Text, comment="内容")
    
    def __repr__(self):
        return f"<BehaviorLog(log_id={self.log_id}, user_id={self.user_id})>"


class SearchLog(Base):
    """搜索日志。"""
    __tablename__ = "search_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, comment="用户ID")
    timestamp = Column(DateTime, default=datetime.now, index=True, comment="时间戳")
    query = Column(String(500), index=True, comment="搜索查询词")
    clicked_doc_id = Column(String(200), index=True, comment="点击的文档ID")
    clicked_doc_title = Column(String(500), comment="点击的文档标题")
    
    def __repr__(self):
        return f"<SearchLog(log_id={self.log_id}, query='{self.query}')>"


class UserProfile(Base):
    """用户画像。"""
    __tablename__ = "user_profiles"
    
    profile_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, comment="用户ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    profile_data = Column(Text, comment="画像数据（JSON格式）")
    
    def __repr__(self):
        return f"<UserProfile(profile_id={self.profile_id}, user_id={self.user_id})>"









