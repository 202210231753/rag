"""重排阶段评测指标。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from app.eval.core.interfaces import EvalSample, Metric
from app.eval.metrics.retrieval import _extract_result_ids, _get_relevant_ids, _ndcg_at_k
from app.eval.metrics.utils import get_metric_value, to_float


class PrecisionAtK(Metric):
    """Precision@K 指标。"""

    def __init__(self, k: int) -> None:
        self.k = k

    def name(self) -> str:
        return f"precision@{self.k}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        retrieved = _extract_result_ids(payload)[: self.k]
        if not retrieved:
            return 0.0
        hit = sum(1 for doc_id in retrieved if doc_id in relevant)
        return hit / float(len(retrieved))


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


class HitRateAt1(Metric):
    """Top-1 命中率。"""

    def name(self) -> str:
        return "hit@1"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        relevant = set(_get_relevant_ids(sample))
        if not relevant:
            return 0.0
        retrieved = _extract_result_ids(payload)[:1]
        if not retrieved:
            return 0.0
        return 1.0 if retrieved[0] in relevant else 0.0


class BoostRatio(Metric):
    """重排提升率（需传入基线分数）。"""

    def __init__(self, metric_name: str, baseline_scores: Dict[str, float]) -> None:
        self.metric_name = metric_name
        self.baseline_scores = baseline_scores

    def name(self) -> str:
        return f"boost_{self.metric_name}"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        key = f"{sample.id}:{self.metric_name}"
        baseline = self.baseline_scores.get(key, 0.0)
        current = get_metric_value(payload, self.metric_name, 0.0)
        baseline = to_float(baseline, 0.0)
        current = to_float(current, 0.0)
        if baseline <= 0:
            return 0.0
        return (current - baseline) / baseline


def build_rerank_metrics(k_values: Optional[List[int]] = None) -> List[Metric]:
    """构建重排指标集合（不含 BoostRatio）。"""
    k_values = k_values or [1, 3, 5, 10]
    metrics: List[Metric] = []
    for k in k_values:
        metrics.append(PrecisionAtK(k))
        metrics.append(NDCGAtK(k))
    metrics.append(HitRateAt1())
    return metrics
