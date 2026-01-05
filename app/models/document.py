from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class DocStatus(str, enum.Enum):
    PENDING = "pending"     # 等待解析
    PARSING = "parsing"     # 解析中
    COMPLETED = "completed" # 解析完成
    FAILED = "failed"       # 解析失败

class Visibility(str, enum.Enum):
    PRIVATE = "private"     # 仅自己可见
    PUBLIC = "public"       # 全员可见
    GROUP = "group"         # 指定组可见

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(512), nullable=False, comment="文件存储路径")
    file_hash = Column(String(64), index=True, comment="文件Hash，防重复")
    
    # 状态管理
    status = Column(String(50), default=DocStatus.PENDING, comment="处理状态")
    is_active = Column(Boolean, default=True, comment="是否启用(上下线)")
    error_msg = Column(String(1024), nullable=True, comment="错误信息")

    # 权限控制
    visibility = Column(String(50), default=Visibility.PRIVATE, comment="可见性")
    authorized_group_ids = Column(JSON, nullable=True, comment="授权组ID列表(当visibility=group时有效)")
    
    # 统计信息
    chunk_count = Column(Integer, default=0, comment="切片数量")
    token_count = Column(Integer, default=0, comment="总Token数")
    
    # 元数据 (JSON格式，存作者、页数等)
    meta_info = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
