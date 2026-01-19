from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint, func

from app.core.database import Base


class CorpusDocument(Base):
    """语料/问答历史文档表：用于词权重（IDF）计算。"""

    __tablename__ = "corpus_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False, comment="文档内容")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class TermWeight(Base):
    """词权重表：保存自动计算与人工干预的权重。"""

    __tablename__ = "term_weights"
    __table_args__ = (UniqueConstraint("scene_id", "term", name="uq_term_weight_scene_term"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, nullable=False, server_default="0", comment="场景ID（默认0）")
    term = Column(String(255), nullable=False, comment="词条")
    weight = Column(Float, nullable=False, comment="权重")
    source = Column(String(16), nullable=False, comment="来源：AUTO/MANUAL")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
