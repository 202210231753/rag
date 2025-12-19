from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, BigInteger, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    
    # 关联 Document
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # 核心内容
    content = Column(Text, nullable=False, comment="切片文本内容")
    
    # 向量数据库关联
    # Milvus 的 ID 通常是 int64，这里用 BigInteger
    vector_id = Column(BigInteger, nullable=True, index=True, comment="Milvus中的VectorID")
    
    # 干预控制
    is_active = Column(Boolean, default=True, comment="是否启用(软删除)")
    
    # 排序与定位
    index = Column(Integer, default=0, comment="在原文中的顺序索引")
    page_number = Column(Integer, nullable=True, comment="所在页码")
    
    # 元数据 (预留给未来扩展，比如存切分算法版本)
    meta_info = Column(JSON, nullable=True)
