from __future__ import annotations

from dataclasses import dataclass
from math import log10
from threading import RLock
from typing import Dict, Iterable, Set, Tuple

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.models.term_weight import CorpusDocument, TermWeight
from app.tokenizer import get_tokenizer_manager
from app.tokenizer.tokenizers import JiebaTokenizer


_schema_lock = RLock()
_initialized_binds: Set[int] = set()

DEFAULT_SCENE_ID = 0


def ensure_term_weight_tables(db: Session) -> None:
    bind = db.get_bind()
    bind_id = id(bind)
    with _schema_lock:
        if bind_id in _initialized_binds:
            return
        from app.core.database import Base

        Base.metadata.create_all(bind=bind, tables=[CorpusDocument.__table__, TermWeight.__table__])
        _ensure_scene_id_schema(db)
        _initialized_binds.add(bind_id)


def _ensure_scene_id_schema(db: Session) -> None:
    """
    将 term_weights 升级为支持 scene_id：
    - 增加 scene_id 列（默认0）
    - 调整唯一约束：UNIQUE(scene_id, term)
    """
    bind = db.get_bind()
    inspector = inspect(bind)
    if "term_weights" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("term_weights")}
    if "scene_id" not in columns:
        db.execute(text("ALTER TABLE term_weights ADD COLUMN scene_id INT NOT NULL DEFAULT 0"))
        db.execute(text("UPDATE term_weights SET scene_id = 0 WHERE scene_id IS NULL"))
        db.commit()

    indexes = {idx["name"]: idx for idx in inspector.get_indexes("term_weights")}

    if "uq_term_weight_term" in indexes:
        try:
            db.execute(text("ALTER TABLE term_weights DROP INDEX uq_term_weight_term"))
            db.commit()
        except Exception:
            db.rollback()

    if "uq_term_weight_scene_term" not in indexes:
        try:
            db.execute(text("CREATE UNIQUE INDEX uq_term_weight_scene_term ON term_weights (scene_id, term)"))
            db.commit()
        except Exception:
            db.rollback()


@dataclass(frozen=True)
class AutoCalcConfig:
    min_df: int = 2


class TermWeightService:
    """词权重服务：人工配置与 IDF 自动计算。"""

    def __init__(self, db: Session, scene_id: int = DEFAULT_SCENE_ID) -> None:
        self._db = db
        self._scene_id = int(scene_id)
        ensure_term_weight_tables(db)
        self._tokenizer_manager = get_tokenizer_manager(db, scene_id=self._scene_id)

    def set_manual_weight(self, term: str, weight: float) -> None:
        normalized_term = (term or "").strip()
        if not normalized_term:
            raise ValueError("term 不能为空")
        if weight < 0:
            raise ValueError("weight 不能小于 0")

        existing = self._db.execute(
            select(TermWeight).where(
                TermWeight.scene_id == self._scene_id,
                TermWeight.term == normalized_term,
            )
        ).scalar_one_or_none()
        if existing is None:
            self._db.add(
                TermWeight(
                    scene_id=self._scene_id,
                    term=normalized_term,
                    weight=float(weight),
                    source="MANUAL",
                )
            )
        else:
            existing.weight = float(weight)
            existing.source = "MANUAL"
        self._db.commit()

    def auto_recalculate_idf_weights(self, config: AutoCalcConfig | None = None) -> int:
        """
        基于 IDF 的全量权重自动计算（仅更新 AUTO 来源权重，保留 MANUAL 干预）。

        返回：写入/更新的 AUTO 词条数量。
        """
        cfg = config or AutoCalcConfig()
        total_documents = self._db.query(CorpusDocument.id).count()
        if total_documents <= 0:
            raise ValueError("语料为空：请先写入 corpus_documents 再触发自动计算")

        df_map = self._build_document_frequency()
        df_map = self._denoise_df_map(df_map, min_df=cfg.min_df)
        weights = self._calc_idf_weights(total_documents, df_map)
        normalized_weights = self._minmax_normalize(weights)

        upserted = 0
        for term, weight in normalized_weights.items():
            existing = self._db.execute(
                select(TermWeight).where(
                    TermWeight.scene_id == self._scene_id,
                    TermWeight.term == term,
                )
            ).scalar_one_or_none()
            if existing is None:
                self._db.add(
                    TermWeight(scene_id=self._scene_id, term=term, weight=weight, source="AUTO")
                )
                upserted += 1
                continue

            if (existing.source or "").upper() == "MANUAL":
                continue

            existing.weight = weight
            existing.source = "AUTO"
            upserted += 1

        self._db.commit()
        return upserted

    def _build_document_frequency(self) -> Dict[str, int]:
        df_map: Dict[str, int] = {}
        documents = self._db.execute(select(CorpusDocument.content)).all()
        for (content,) in documents:
            tokens = self._safe_tokenize(str(content or ""))
            unique_terms = {t for t in tokens if self._is_candidate_term(t)}
            for term in unique_terms:
                df_map[term] = df_map.get(term, 0) + 1
        return df_map

    def _safe_tokenize(self, text: str) -> Iterable[str]:
        if not text:
            return []
        try:
            return self._tokenizer_manager.tokenize(text)
        except Exception:
            return JiebaTokenizer().tokenize(text)

    def _denoise_df_map(self, df_map: Dict[str, int], min_df: int) -> Dict[str, int]:
        if min_df <= 1:
            return {term: df for term, df in df_map.items() if self._is_candidate_term(term)}
        return {
            term: df
            for term, df in df_map.items()
            if df >= min_df and self._is_candidate_term(term)
        }

    def _calc_idf_weights(self, total_documents: int, df_map: Dict[str, int]) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for term, df in df_map.items():
            weights[term] = log10(total_documents / (df + 1))
        return weights

    def _minmax_normalize(self, weights: Dict[str, float]) -> Dict[str, float]:
        if not weights:
            return {}
        values = list(weights.values())
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return {term: 1.0 for term in weights}
        return {term: (value - min_v) / (max_v - min_v) for term, value in weights.items()}

    def _is_candidate_term(self, term: str) -> bool:
        token = (term or "").strip()
        if not token:
            return False
        if len(token) <= 1:
            return False
        if token.isdigit():
            return False
        if token in _DEFAULT_STOPWORDS:
            return False
        return True


_DEFAULT_STOPWORDS: Set[str] = {
    "的",
    "了",
    "和",
    "与",
    "及",
    "或",
    "在",
    "是",
    "为",
    "对",
    "这",
    "那",
    "你",
    "我",
    "他",
    "她",
    "它",
    "我们",
    "你们",
    "他们",
    "她们",
    "它们",
}
