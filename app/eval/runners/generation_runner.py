"""Generation 评测执行器。"""

from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine, EvalContext, EvalResult, EvalSample, Metric, Runner
from app.eval.metrics.generation import build_generation_metrics


def _extract_contexts(payload: Mapping[str, Any], max_contexts: int) -> List[str]:
    results = payload.get("results") or []
    contexts: List[str] = []
    for item in results:
        text = item.get("content") or item.get("text")
        if text is None:
            continue
        contexts.append(str(text))
        if len(contexts) >= max_contexts:
            break
    return contexts


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class GenerationRunner(Runner):
    """Generation 评测执行器。"""

    def __init__(
        self,
        engine: Engine,
        *,
        metrics: Optional[Sequence[Metric]] = None,
        metric_names: Optional[Sequence[str]] = None,
        context_source: str = "retrieval",
        top_n: int = 5,
        recall_top_k: int = 100,
        judge_fn: Optional[Callable[[str, str, Sequence[str], EvalSample], Awaitable[Mapping[str, Any]] | Mapping[str, Any]]] = None,
        stage: str = "generation",
        save_raw_payload: bool = False,
        include_sample: bool = True,
    ) -> None:
        self.engine = engine
        self.metrics = list(metrics) if metrics is not None else build_generation_metrics(metric_names)
        self.context_source = context_source
        self.top_n = int(top_n)
        self.recall_top_k = int(recall_top_k)
        self.judge_fn = judge_fn
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
            retrieval_payload: Optional[Mapping[str, Any]] = None

            contexts: List[str] = []
            try:
                if self.context_source == "field":
                    contexts = list(sample.contexts or [])
                elif self.context_source == "retrieval":
                    retrieval_payload = await self.engine.retrieve(
                        query=sample.query,
                        top_n=self.top_n,
                        recall_top_k=self.recall_top_k,
                    )
                    contexts = _extract_contexts(retrieval_payload, self.top_n)
                else:
                    raise ValueError(f"未知 context_source: {self.context_source}")

                response = await self.engine.generate(sample.query, contexts)
                if isinstance(response, Mapping):
                    payload.update(response)
                else:
                    payload["response"] = response

                answer = ""
                if isinstance(response, Mapping):
                    answer = str(response.get("answer") or response.get("text") or "")

                if self.judge_fn:
                    judged = await _maybe_await(self.judge_fn(sample.query, answer, contexts, sample))
                    if isinstance(judged, Mapping):
                        payload.update(judged)

                for metric in self.metrics:
                    metrics[metric.name()] = metric.compute(sample, payload)
            except Exception as exc:
                error = str(exc)

            latency_ms = (time.perf_counter() - start) * 1000.0

            details: Dict[str, Any] = {
                "context_source": self.context_source,
                "context_count": len(contexts),
            }
            if self.include_sample:
                details["sample"] = {
                    "id": sample.id,
                    "query": sample.query,
                    "metadata": sample.metadata,
                }

            raw_payload = None
            if self.save_raw_payload:
                raw_payload = {
                    "retrieve": retrieval_payload,
                    "generate": payload,
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
