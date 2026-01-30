"""Embedding 判分器（用于语义相似度等指标）。"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional


class EmbeddingJudge:
    """基于 sentence-transformers 的语义相似度判分器。"""

    def __init__(
        self,
        *,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        normalize: bool = True,
    ) -> None:
        self.model_name = model_name
        self.normalize = normalize
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:  # pragma: no cover
                raise RuntimeError("sentence-transformers 未安装，无法使用 EmbeddingJudge") from exc
            self._model = SentenceTransformer(self.model_name)

    def similarity(self, text_a: str, text_b: str) -> float:
        self._ensure_model()
        if not text_a or not text_b:
            return 0.0
        from sentence_transformers import util

        emb = self._model.encode([text_a, text_b], normalize_embeddings=self.normalize)
        score = util.cos_sim(emb[0], emb[1])
        return float(score)

    async def similarity_async(self, text_a: str, text_b: str) -> float:
        return await asyncio.to_thread(self.similarity, text_a, text_b)
