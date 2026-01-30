"""ragas 评测引擎适配器。"""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine


class RagasEngine(Engine):
    """ragas 框架适配器。

    说明：
    - 本引擎用于对接 ragas 的评测流程，不直接负责检索或生成。
    - 目前仅保留接口，待后续接入 ragas 后实现。
    """

    def __init__(
        self,
        *,
        metrics: Optional[Iterable[str]] = None,
        llm_provider: str = "",
        embedding_provider: str = "",
        batch_size: int = 8,
    ) -> None:
        try:
            import ragas  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("ragas 未安装，无法使用 ragas 引擎") from exc
        self.metrics = list(metrics or [])
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.batch_size = max(1, int(batch_size))
        self._metric_objects: Optional[Sequence[Any]] = None

    def _resolve_metrics(self) -> Sequence[Any]:
        if self._metric_objects is not None:
            return self._metric_objects
        try:
            from ragas import metrics as ragas_metrics  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("ragas metrics 导入失败") from exc

        metric_map = {
            "faithfulness": ragas_metrics.faithfulness,
            "answer_relevancy": ragas_metrics.answer_relevancy,
            "answer_relevance": ragas_metrics.answer_relevancy,
            "context_precision": ragas_metrics.context_precision,
            "context_recall": ragas_metrics.context_recall,
            "context_relevancy": getattr(ragas_metrics, "context_relevancy", None),
            "context_relevance": getattr(ragas_metrics, "context_relevancy", None),
        }
        objects: list[Any] = []
        for name in self.metrics:
            key = str(name).strip().lower()
            metric_obj = metric_map.get(key)
            if metric_obj is None:
                raise ValueError(f"未知 ragas 指标: {name}")
            objects.append(metric_obj)
        self._metric_objects = objects
        return objects

    async def evaluate(self, samples: Sequence[Any]) -> Mapping[str, Any]:
        """执行 ragas 评测，返回每样本分数与汇总。"""
        try:
            from datasets import Dataset  # type: ignore
            from ragas import evaluate  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("ragas 或 datasets 未安装，无法评测") from exc

        metric_objs = self._resolve_metrics()
        rows = []
        for sample in samples:
            answer = ""
            if getattr(sample, "answers", None):
                answer = str(sample.answers[0])
            contexts = list(getattr(sample, "contexts", None) or getattr(sample, "relevant_texts", None) or [])
            row = {
                "question": getattr(sample, "query", ""),
                "answer": answer,
                "contexts": contexts,
            }
            if getattr(sample, "answers", None):
                row["ground_truths"] = list(sample.answers)
                row["ground_truth"] = str(sample.answers[0])
            rows.append(row)

        dataset = Dataset.from_list(rows)

        def _run() -> Any:
            return evaluate(dataset, metrics=metric_objs, batch_size=self.batch_size)

        result = await asyncio.to_thread(_run)

        # to pandas
        records = None
        if hasattr(result, "to_pandas"):
            df = result.to_pandas()
            records = df.to_dict(orient="records")
        elif isinstance(result, Mapping):
            records = result.get("scores") or result.get("records")

        if records is None:
            raise RuntimeError("ragas 结果解析失败")

        # summary
        summary: dict[str, Any] = {}
        for name in self.metrics:
            vals = [r.get(name) for r in records if isinstance(r.get(name), (int, float))]
            summary[name] = sum(vals) / len(vals) if vals else 0.0

        return {"records": records, "summary": summary}

    async def retrieve(self, query: str, top_n: int, recall_top_k: int) -> Mapping[str, object]:
        raise NotImplementedError("ragas 引擎不提供 retrieve 接口")

    async def rerank(self, query: str, candidates: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
        raise NotImplementedError("ragas 引擎不提供 rerank 接口")

    async def rewrite(self, query: str) -> str:
        raise NotImplementedError("ragas 引擎不提供 rewrite 接口")

    async def generate(self, query: str, contexts: Sequence[str]) -> Mapping[str, object]:
        raise NotImplementedError("ragas 引擎不提供 generate 接口")
