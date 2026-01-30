"""Retrieval 评测执行器。"""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine, EvalContext, EvalResult, EvalSample, Metric, Runner
from app.eval.metrics.retrieval import (
    ContextRecallAtK,
    HitRateAtK,
    MRR,
    NDCGAtK,
    RecallAtK,
)


def _parse_k(name: str) -> Optional[int]:
    if "@" not in name:
        return None
    try:
        return int(name.split("@", 1)[1])
    except Exception:
        return None


def _build_metrics(
    metric_names: Optional[Sequence[str]],
    k_values: Optional[Sequence[int]],
    include_context_recall: bool,
) -> List[Metric]:
    if not metric_names:
        metric_names = ["recall@k", "mrr", "ndcg@k", "hit@k"]
    k_values = list(k_values or [1, 3, 5, 10])
    metrics: List[Metric] = []
    for name in metric_names:
        key = str(name).strip().lower()
        if key == "mrr":
            metrics.append(MRR())
        elif key in {"recall@k", "recall"}:
            metrics.extend([RecallAtK(k) for k in k_values])
        elif key.startswith("recall@"):
            k = _parse_k(key)
            if k is None:
                continue
            metrics.append(RecallAtK(k))
        elif key in {"ndcg@k", "ndcg"}:
            metrics.extend([NDCGAtK(k) for k in k_values])
        elif key.startswith("ndcg@"):
            k = _parse_k(key)
            if k is None:
                continue
            metrics.append(NDCGAtK(k))
        elif key in {"hit@k", "hit"}:
            metrics.extend([HitRateAtK(k) for k in k_values])
        elif key.startswith("hit@"):
            k = _parse_k(key)
            if k is None:
                continue
            metrics.append(HitRateAtK(k))
        elif key in {"context_recall@k", "context_recall"}:
            include_context_recall = True
        elif key.startswith("context_recall@"):
            k = _parse_k(key)
            if k is None:
                continue
            metrics.append(ContextRecallAtK(k))
        else:
            raise ValueError(f"未知 retrieval 指标: {name}")
    if include_context_recall and not any(isinstance(m, ContextRecallAtK) for m in metrics):
        metrics.append(ContextRecallAtK(max(k_values)))
    return metrics


class RetrievalRunner(Runner):
    """Retrieval 评测执行器。"""

    def __init__(
        self,
        engine: Engine,
        *,
        metrics: Optional[Sequence[Metric]] = None,
        metric_names: Optional[Sequence[str]] = None,
        k_values: Optional[Sequence[int]] = None,
        top_n: int = 10,
        recall_top_k: int = 100,
        stage: str = "retrieval",
        include_context_recall: bool = False,
        save_raw_payload: bool = False,
        include_sample: bool = True,
    ) -> None:
        self.engine = engine
        self.metrics = list(metrics) if metrics is not None else _build_metrics(
            metric_names, k_values, include_context_recall
        )
        self.top_n = int(top_n)
        self.recall_top_k = int(recall_top_k)
        self.stage = stage
        self.save_raw_payload = save_raw_payload
        self.include_sample = include_sample

    async def run(
        self,
        samples: Iterable[EvalSample],
        context: Optional[EvalContext] = None,
    ) -> List[EvalResult]:
        ctx = context or EvalContext()
        results: List[EvalResult] = []

        for sample in samples:
            start = time.perf_counter()
            error: Optional[str] = None
            payload: Mapping[str, object] = {}
            metrics: Dict[str, float] = {}
            try:
                payload = await self.engine.retrieve(
                    query=sample.query,
                    top_n=self.top_n,
                    recall_top_k=self.recall_top_k,
                )
                for metric in self.metrics:
                    metrics[metric.name()] = metric.compute(sample, payload)
            except Exception as exc:
                error = str(exc)
            latency_ms = (time.perf_counter() - start) * 1000.0

            details: Dict[str, object] = {}
            if self.include_sample:
                details["sample"] = {
                    "id": sample.id,
                    "query": sample.query,
                    "metadata": sample.metadata,
                }
            if isinstance(payload, Mapping) and payload.get("recall_stats"):
                details["recall_stats"] = payload.get("recall_stats")

            results.append(
                EvalResult(
                    sample_id=sample.id,
                    metrics=metrics,
                    details=details or None,
                    stage=self.stage,
                    latency_ms=latency_ms,
                    error=error,
                    raw_payload=payload if self.save_raw_payload else None,
                    engine_type=ctx.engine_type,
                )
            )
        return results
