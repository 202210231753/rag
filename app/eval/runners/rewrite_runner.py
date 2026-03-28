"""Rewrite 评测执行器。"""

from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine, EvalContext, EvalResult, EvalSample, Metric, Runner
from app.eval.metrics.retrieval import HitRateAtK, MRR, NDCGAtK, RecallAtK
from app.eval.metrics.rewrite import build_rewrite_metrics


def _parse_k(name: str) -> Optional[int]:
    if "@" not in name:
        return None
    try:
        return int(name.split("@", 1)[1])
    except Exception:
        return None


def _metric_from_name(name: str) -> Metric:
    key = str(name).strip().lower()
    if key == "mrr":
        return MRR()
    if key.startswith("recall@"):
        k = _parse_k(key)
        if k is None:
            raise ValueError(f"无效指标: {name}")
        return RecallAtK(k)
    if key.startswith("ndcg@"):
        k = _parse_k(key)
        if k is None:
            raise ValueError(f"无效指标: {name}")
        return NDCGAtK(k)
    if key.startswith("hit@"):
        k = _parse_k(key)
        if k is None:
            raise ValueError(f"无效指标: {name}")
        return HitRateAtK(k)
    raise ValueError(f"未知增益指标: {name}")


def _simple_tokens(text: str) -> List[str]:
    if not text:
        return []
    if any(ch.isspace() for ch in text):
        tokens = text.lower().split()
    else:
        tokens = list(text.strip())
    return [t for t in tokens if t.strip()]


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / float(len(set_a | set_b))


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class RewriteRunner(Runner):
    """Rewrite 评测执行器。"""

    def __init__(
        self,
        engine: Engine,
        *,
        metrics: Optional[Sequence[Metric]] = None,
        metric_names: Optional[Sequence[str]] = None,
        top_n: int = 10,
        recall_top_k: int = 100,
        rewrite_source: str = "field",
        compare_with_original: bool = True,
        gain_metric_name: str = "ndcg@10",
        semantic_similarity_fn: Optional[Callable[[str, str], Awaitable[float] | float]] = None,
        stage: str = "rewrite",
        save_raw_payload: bool = False,
        include_sample: bool = True,
    ) -> None:
        self.engine = engine
        self.metrics = list(metrics) if metrics is not None else build_rewrite_metrics(metric_names)
        self.top_n = int(top_n)
        self.recall_top_k = int(recall_top_k)
        self.rewrite_source = rewrite_source
        self.compare_with_original = compare_with_original
        self.gain_metric = _metric_from_name(gain_metric_name)
        self.semantic_similarity_fn = semantic_similarity_fn
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
            metrics: Dict[str, float] = {}
            payload: Dict[str, Any] = {}
            original_payload: Optional[Mapping[str, Any]] = None
            rewrite_payload: Optional[Mapping[str, Any]] = None

            try:
                if self.rewrite_source == "field":
                    rewrite_query = sample.rewrite or ""
                elif self.rewrite_source == "engine":
                    rewrite_query = await self.engine.rewrite(sample.query)
                else:
                    raise ValueError(f"未知 rewrite_source: {self.rewrite_source}")

                if not rewrite_query:
                    raise ValueError("rewrite query 为空")

                semantic = 0.0
                if self.semantic_similarity_fn:
                    semantic = await _maybe_await(self.semantic_similarity_fn(sample.query, rewrite_query))
                else:
                    semantic = _jaccard(_simple_tokens(sample.query), _simple_tokens(rewrite_query))

                payload["semantic_preservation"] = semantic

                if self.compare_with_original:
                    original_payload = await self.engine.retrieve(
                        query=sample.query,
                        top_n=self.top_n,
                        recall_top_k=self.recall_top_k,
                    )
                    rewrite_payload = await self.engine.retrieve(
                        query=rewrite_query,
                        top_n=self.top_n,
                        recall_top_k=self.recall_top_k,
                    )
                    original_score = self.gain_metric.compute(sample, original_payload)
                    rewrite_score = self.gain_metric.compute(sample, rewrite_payload)
                    payload["retrieval_gain"] = rewrite_score - original_score

                    original_count = len(original_payload.get("results") or [])
                    rewrite_count = len(rewrite_payload.get("results") or [])
                    payload["zero_result_reduction"] = 1.0 if original_count == 0 and rewrite_count > 0 else 0.0
                    payload["original_score"] = original_score
                    payload["rewrite_score"] = rewrite_score

                for metric in self.metrics:
                    metrics[metric.name()] = metric.compute(sample, payload)
            except Exception as exc:
                error = str(exc)

            latency_ms = (time.perf_counter() - start) * 1000.0

            details: Dict[str, Any] = {
                "rewrite_source": self.rewrite_source,
                "compare_with_original": self.compare_with_original,
            }
            if self.include_sample:
                details["sample"] = {
                    "id": sample.id,
                    "query": sample.query,
                    "metadata": sample.metadata,
                    "rewrite": sample.rewrite,
                }
            if payload:
                details["payload"] = {
                    "original_score": payload.get("original_score"),
                    "rewrite_score": payload.get("rewrite_score"),
                }

            raw_payload = None
            if self.save_raw_payload:
                raw_payload = {
                    "original": original_payload,
                    "rewrite": rewrite_payload,
                    "payload": payload,
                }

            results.append(
                EvalResult(
                    sample_id=sample.id,
                    metrics=metrics,
                    details=details or None,
                    stage=self.stage,
                    latency_ms=latency_ms,
                    error=error,
                    raw_payload=raw_payload,
                    engine_type=ctx.engine_type,
                )
            )

        return results
