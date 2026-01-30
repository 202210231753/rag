"""Rerank 评测执行器。"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.eval.core.interfaces import Engine, EvalContext, EvalResult, EvalSample, Metric, Runner
from app.eval.metrics.rerank import BoostRatio, HitRateAt1, NDCGAtK, PrecisionAtK
from app.eval.metrics.retrieval import _extract_result_ids


def _parse_k(name: str) -> Optional[int]:
    if "@" not in name:
        return None
    try:
        return int(name.split("@", 1)[1])
    except Exception:
        return None


def _metric_from_name(name: str) -> Optional[Metric]:
    key = str(name).strip().lower()
    if key.startswith("ndcg@"):
        k = _parse_k(key)
        return NDCGAtK(k) if k else None
    if key.startswith("precision@"):
        k = _parse_k(key)
        return PrecisionAtK(k) if k else None
    if key == "hit@1":
        return HitRateAt1()
    return None


def _build_metrics(
    metric_names: Optional[Sequence[str]],
    k_values: Optional[Sequence[int]],
    boost_metric_name: Optional[str],
) -> Tuple[List[Metric], Optional[str], bool]:
    if not metric_names:
        metric_names = ["ndcg@k", "precision@k", "hit@1"]
    k_values = list(k_values or [1, 3, 5, 10])
    metrics: List[Metric] = []
    boost_requested = False
    for name in metric_names:
        key = str(name).strip().lower()
        if key in {"ndcg@k", "ndcg"}:
            metrics.extend([NDCGAtK(k) for k in k_values])
        elif key.startswith("ndcg@"):
            k = _parse_k(key)
            if k is not None:
                metrics.append(NDCGAtK(k))
        elif key in {"precision@k", "precision"}:
            metrics.extend([PrecisionAtK(k) for k in k_values])
        elif key.startswith("precision@"):
            k = _parse_k(key)
            if k is not None:
                metrics.append(PrecisionAtK(k))
        elif key == "hit@1":
            metrics.append(HitRateAt1())
        elif key == "boost_ratio":
            boost_requested = True
        else:
            raise ValueError(f"未知 rerank 指标: {name}")

    if boost_requested and not boost_metric_name:
        boost_metric_name = f"ndcg@{max(k_values)}"
    return metrics, boost_metric_name, boost_requested


def _build_candidates_from_sample(sample: EvalSample) -> List[Dict[str, Any]]:
    if not sample.candidate_doc_ids:
        return []
    candidates: List[Dict[str, Any]] = []
    texts = sample.candidate_texts or []
    for idx, doc_id in enumerate(sample.candidate_doc_ids):
        item: Dict[str, Any] = {"doc_id": doc_id}
        if idx < len(texts):
            item["content"] = texts[idx]
        candidates.append(item)
    return candidates


class RerankRunner(Runner):
    """Rerank 评测执行器。"""

    def __init__(
        self,
        engine: Engine,
        *,
        metrics: Optional[Sequence[Metric]] = None,
        metric_names: Optional[Sequence[str]] = None,
        k_values: Optional[Sequence[int]] = None,
        top_n: int = 5,
        recall_top_k: int = 100,
        candidate_source: str = "retrieval",
        baseline_source: str = "retrieval",
        boost_metric_name: Optional[str] = None,
        stage: str = "rerank",
        save_raw_payload: bool = False,
        include_sample: bool = True,
    ) -> None:
        self.engine = engine
        base_metrics, boost_metric_name, boost_requested = _build_metrics(
            metric_names, k_values, boost_metric_name
        )
        self.base_metrics = list(metrics) if metrics is not None else base_metrics
        self.boost_metric_name = boost_metric_name
        self.boost_requested = boost_requested
        self.top_n = int(top_n)
        self.recall_top_k = int(recall_top_k)
        self.candidate_source = candidate_source
        self.baseline_source = baseline_source
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
        baseline_scores: Dict[str, float] = {}
        baseline_metric = _metric_from_name(self.boost_metric_name or "") if self.boost_requested else None

        for sample in samples:
            start = time.perf_counter()
            error: Optional[str] = None
            metrics: Dict[str, float] = {}
            payload: Mapping[str, Any] = {}
            retrieval_payload: Optional[Mapping[str, Any]] = None

            try:
                candidates: List[Dict[str, Any]] = []
                if self.candidate_source == "retrieval":
                    retrieval_payload = await self.engine.retrieve(
                        query=sample.query,
                        top_n=max(self.top_n, self.recall_top_k),
                        recall_top_k=self.recall_top_k,
                    )
                    candidates = list(retrieval_payload.get("results") or [])
                elif self.candidate_source == "dataset":
                    candidates = _build_candidates_from_sample(sample)
                else:
                    raise ValueError(f"未知 candidate_source: {self.candidate_source}")

                if not candidates:
                    raise ValueError("候选列表为空")

                # baseline
                if self.boost_requested and baseline_metric:
                    if self.baseline_source == "retrieval":
                        if retrieval_payload is None:
                            retrieval_payload = await self.engine.retrieve(
                                query=sample.query,
                                top_n=max(self.top_n, self.recall_top_k),
                                recall_top_k=self.recall_top_k,
                            )
                        baseline_payload = retrieval_payload
                    else:
                        baseline_payload = {"results": candidates}
                    baseline_value = baseline_metric.compute(sample, baseline_payload)
                    baseline_scores[f"{sample.id}:{baseline_metric.name()}"] = baseline_value

                payload = await self.engine.rerank(sample.query, candidates)

                for metric in self.base_metrics:
                    metrics[metric.name()] = metric.compute(sample, payload)

                if self.boost_requested and baseline_metric:
                    boost_metric = BoostRatio(metric_name=baseline_metric.name(), baseline_scores=baseline_scores)
                    metrics[boost_metric.name()] = boost_metric.compute(sample, payload)
            except Exception as exc:
                error = str(exc)

            latency_ms = (time.perf_counter() - start) * 1000.0

            details: Dict[str, Any] = {
                "candidate_source": self.candidate_source,
                "baseline_source": self.baseline_source,
            }
            if self.include_sample:
                details["sample"] = {
                    "id": sample.id,
                    "query": sample.query,
                    "metadata": sample.metadata,
                }
            if isinstance(payload, Mapping):
                details["result_count"] = len(_extract_result_ids(payload))

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
