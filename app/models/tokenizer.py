from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from app.core.database import Base


class TokenizerConfig(Base):
    """中文分词配置（单行配置表）。"""

    __tablename__ = "tokenizer_config"

    id = Column(Integer, primary_key=True, autoincrement=False, default=1)
    tokenizer_id = Column(String(64), nullable=False, comment="当前分词器ID")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TokenizerTerm(Base):
    """中文分词专用词条（自定义词库）。"""

    __tablename__ = "tokenizer_terms"
    __table_args__ = (UniqueConstraint("scene_id", "term", name="uq_tokenizer_term_scene_term"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, nullable=False, server_default="0", comment="场景ID（默认0）")
    term = Column(String(255), nullable=False, comment="词条")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
