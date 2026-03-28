"""Ragas 评测执行器。"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import EvalContext, EvalResult, EvalSample, Runner
from app.eval.engines.ragas_engine import RagasEngine


class RagasRunner(Runner):
    """基于 ragas 的评测执行器。"""

    def __init__(
        self,
        engine: RagasEngine,
        *,
        metrics: Optional[Sequence[str]] = None,
        stage: str = "ragas",
        save_raw_payload: bool = False,
    ) -> None:
        if not isinstance(engine, RagasEngine):
            raise ValueError("RagasRunner 需要 RagasEngine")
        if metrics is not None:
            engine.metrics = list(metrics)
        self.engine = engine
        self.stage = stage
        self.save_raw_payload = save_raw_payload

    async def run(
        self,
        samples: Iterable[EvalSample],
        context: Optional[EvalContext] = None,
    ) -> List[EvalResult]:
        ctx = context or EvalContext()
        sample_list = list(samples)
        start = time.perf_counter()
        error: Optional[str] = None
        records: List[Mapping[str, Any]] = []
        summary: Mapping[str, Any] = {}
        try:
            payload = await self.engine.evaluate(sample_list)
            records = list(payload.get("records") or [])
            summary = payload.get("summary") or {}
        except Exception as exc:
            error = str(exc)

        latency_ms = (time.perf_counter() - start) * 1000.0
        results: List[EvalResult] = []

        for idx, sample in enumerate(sample_list):
            row = records[idx] if idx < len(records) else {}
            metrics = {k: v for k, v in row.items() if isinstance(v, (int, float))}
            details = {
                "sample": {"id": sample.id, "query": sample.query, "metadata": sample.metadata},
                "ragas_summary": summary if idx == 0 else None,
            }
            results.append(
                EvalResult(
                    sample_id=sample.id,
                    metrics=metrics,
                    details=details,
                    stage=self.stage,
                    latency_ms=latency_ms,
                    error=error,
                    raw_payload=row if self.save_raw_payload else None,
                    engine_type=ctx.engine_type,
                )
            )

        return results
