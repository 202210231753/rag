"""E2E 评测执行器。"""

from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine, EvalContext, EvalResult, EvalSample, Metric, Runner
from app.eval.metrics.e2e import build_e2e_metrics


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


def _calc_cost(payload: Mapping[str, Any], cost_cfg: Mapping[str, Any]) -> Optional[float]:
    if not cost_cfg.get("enabled"):
        return None
    usage = payload.get("usage") or payload.get("token_usage") or {}
    if not isinstance(usage, Mapping):
        return None
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    try:
        prompt_tokens = float(prompt_tokens)
        completion_tokens = float(completion_tokens)
    except Exception:
        return None
    prompt_cost = float(cost_cfg.get("prompt_cost_per_1k", 0.0))
    completion_cost = float(cost_cfg.get("completion_cost_per_1k", 0.0))
    return (prompt_tokens / 1000.0) * prompt_cost + (completion_tokens / 1000.0) * completion_cost


class E2ERunner(Runner):
    """端到端评测执行器。"""

    def __init__(
        self,
        engine: Engine,
        *,
        metrics: Optional[Sequence[Metric]] = None,
        metric_names: Optional[Sequence[str]] = None,
        top_n: int = 5,
        recall_top_k: int = 100,
        record_latency: bool = True,
        cost_config: Optional[Mapping[str, Any]] = None,
        judge_fn: Optional[Callable[[str, str, Sequence[str], EvalSample], Awaitable[Mapping[str, Any]] | Mapping[str, Any]]] = None,
        stage: str = "e2e",
        save_raw_payload: bool = False,
        include_sample: bool = True,
    ) -> None:
        self.engine = engine
        self.metrics = list(metrics) if metrics is not None else build_e2e_metrics(metric_names)
        self.top_n = int(top_n)
        self.recall_top_k = int(recall_top_k)
        self.record_latency = record_latency
        self.cost_config = dict(cost_config or {})
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
                retrieval_payload = await self.engine.retrieve(
                    query=sample.query,
                    top_n=self.top_n,
                    recall_top_k=self.recall_top_k,
                )
                contexts = _extract_contexts(retrieval_payload, self.top_n)

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

                if self.record_latency:
                    payload["latency"] = (time.perf_counter() - start) * 1000.0

                cost = _calc_cost(payload, self.cost_config)
                if cost is not None:
                    payload["cost_per_query"] = cost

                for metric in self.metrics:
                    metrics[metric.name()] = metric.compute(sample, payload)
            except Exception as exc:
                error = str(exc)

            latency_ms = (time.perf_counter() - start) * 1000.0

            details: Dict[str, Any] = {"context_count": len(contexts)}
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
