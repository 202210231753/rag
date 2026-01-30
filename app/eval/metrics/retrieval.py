"""检索阶段评测指标。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import EvalSample, Metric


def _get_results(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    if "results" in payload:
        return payload.get("results") or []
    data = payload.get("data")
    if isinstance(data, Mapping):
        return data.get("results") or []
    return []


def _extract_result_ids(payload: Mapping[str, Any]) -> List[str]:
    results = _get_results(payload)
    doc_ids: List[str] = []
    for item in results:
        doc_id = item.get("doc_id") or item.get("id")
        if doc_id is not None:
            doc_ids.append(str(doc_id))
    return doc_ids


def _extract_result_texts(payload: Mapping[str, Any]) -> List[str]:
    results = _get_results(payload)
    texts: List[str] = []
    for item in results:
        text = item.get("content") or item.get("text")
        if text is None:
            continue
        texts.append(str(text))
    return texts


def _get_relevant_ids(sample: EvalSample) -> List[str]:
    if sample.relevant_doc_ids:
        return [str(x) for x in sample.relevant_doc_ids]
    return []


def _dcg(relevances: List[int]) -> float:
    score = 0.0
    for idx, rel in enumerate(relevances, start=1):
        score += rel / math.log2(idx + 1)
    return score


def _ndcg_at_k(relevances: List[int], k: int) -> float:
    if k <= 0:
        return 0.0
    rel_k = relevances[:k]
    dcg_val = _dcg(rel_k)
    ideal = sorted(relevances, reverse=True)[:k]
    idcg_val = _dcg(ideal)
    if idcg_val == 0:
        return 0.0
    return dcg_val / idcg_val


class RecallAtK(Metric):
    """Recall@K 指标。"""

    def __init__(self, k: int) -> None:
        self.k = k

    def name(self) -> str:
        return f"recall@{self.k}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        retrieved = _extract_result_ids(payload)[: self.k]
        hit = sum(1 for doc_id in retrieved if doc_id in relevant)
        return hit / float(len(relevant))


class HitRateAtK(Metric):
    """HitRate@K 指标。"""

    def __init__(self, k: int) -> None:
        self.k = k

    def name(self) -> str:
        return f"hit@{self.k}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        retrieved = _extract_result_ids(payload)[: self.k]
        return 1.0 if any(doc_id in relevant for doc_id in retrieved) else 0.0


class MRR(Metric):
    """MRR 指标。"""

    def name(self) -> str:
        return "mrr"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        for idx, doc_id in enumerate(_extract_result_ids(payload), start=1):
            if doc_id in relevant:
                return 1.0 / idx
        return 0.0


class NDCGAtK(Metric):
    """NDCG@K 指标。"""

    def __init__(self, k: int) -> None:
        self.k = k

    def name(self) -> str:
        return f"ndcg@{self.k}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        retrieved = _extract_result_ids(payload)
        relevances = [1 if doc_id in relevant else 0 for doc_id in retrieved]
        return _ndcg_at_k(relevances, self.k)


class ContextRecallAtK(Metric):
    """Context Recall@K（基于 relevant_texts 与检索内容的粗匹配）。"""

    def __init__(self, k: int) -> None:
        self.k = k

    def name(self) -> str:
        return f"context_recall@{self.k}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        if not sample.relevant_texts:
            return 0.0
        retrieved_texts = _extract_result_texts(payload)[: self.k]
        if not retrieved_texts:
            return 0.0

        joined = "\n".join(retrieved_texts).lower()
        hits = 0
        for text in sample.relevant_texts:
            if not text:
                continue
            if str(text).lower() in joined:
                hits += 1
        return hits / float(len(sample.relevant_texts))


def build_retrieval_metrics(
    k_values: Optional[List[int]] = None,
    *,
    include_context_recall: bool = False,
    context_k: Optional[int] = None,
) -> List[Metric]:
    """构建检索指标集合。"""
    k_values = k_values or [1, 3, 5, 10]
    metrics: List[Metric] = [MRR()]
    for k in k_values:
        metrics.append(RecallAtK(k))
        metrics.append(NDCGAtK(k))
        metrics.append(HitRateAtK(k))
    if include_context_recall:
        k_ctx = context_k or max(k_values)
        metrics.append(ContextRecallAtK(k_ctx))
    return metrics
