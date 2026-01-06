"""同义词相关的数据模型。"""
from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class SynonymGroup(Base):
    """同义词组（标准词及其同义词集合）。"""
    __tablename__ = "synonym_groups"

    group_id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(50), default="default", index=True, comment="领域")
    canonical = Column(String(100), nullable=False, index=True, comment="标准词")
    enabled = Column(Integer, default=1, comment="是否启用：1启用，0禁用")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联同义词
    terms = relationship("SynonymTerm", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SynonymGroup(id={self.group_id}, canonical='{self.canonical}')>"


class SynonymTerm(Base):
    """同义词项。"""
    __tablename__ = "synonym_terms"

    term_id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("synonym_groups.group_id"), nullable=False)
    term = Column(String(100), nullable=False, index=True, comment="同义词")
    weight = Column(Float, default=1.0, comment="权重")
    
    created_at = Column(DateTime, default=datetime.now)

    # 关联组
    group = relationship("SynonymGroup", back_populates="terms")

    def __repr__(self):
        return f"<SynonymTerm(term='{self.term}', weight={self.weight})>"


class SynonymCandidate(Base):
    """同义词候选（挖掘结果，待审核）。"""
    __tablename__ = "synonym_candidates"

    candidate_id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(50), default="default", index=True)
    canonical = Column(String(100), nullable=False, index=True)
    synonym = Column(String(100), nullable=False, index=True)
    score = Column(Float, default=0.0, comment="置信度分数")
    
    # 状态：pending(待审核), approved(已通过), rejected(已拒绝)
    status = Column(String(20), default="pending", index=True)
    source = Column(String(50), comment="来源：embedding, search_log, manual")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SynonymCandidate({self.canonical} -> {self.synonym}, score={self.score})>"
