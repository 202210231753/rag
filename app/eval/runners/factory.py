"""Runner 工厂：根据配置自动组装评测流程。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine, Runner
from app.eval.core.pipeline import EvalPipeline
from app.eval.judges import EmbeddingJudge, LLMJudge
from app.eval.judges.llm_judge import LLMJudgeConfig
from app.eval.runners.e2e_runner import E2ERunner
from app.eval.runners.generation_runner import GenerationRunner
from app.eval.runners.rerank_runner import RerankRunner
from app.eval.runners.retrieval_runner import RetrievalRunner
from app.eval.runners.rewrite_runner import RewriteRunner
from app.eval.runners.ragas_runner import RagasRunner


def _get_section(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key, {})
    if isinstance(value, Mapping):
        return value
    return {}


def _merge_dict(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    merged.update({k: v for k, v in override.items() if v is not None})
    return merged


def _build_embedding_judge(config: Mapping[str, Any]) -> Optional[EmbeddingJudge]:
    judge_cfg = _get_section(config, "judges").get("embedding", {})
    if not isinstance(judge_cfg, Mapping):
        return None
    if not judge_cfg.get("enabled"):
        return None
    return EmbeddingJudge(
        model_name=str(judge_cfg.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")),
        normalize=bool(judge_cfg.get("normalize", True)),
    )


def _build_llm_judge(config: Mapping[str, Any], local_override: Optional[Mapping[str, Any]] = None) -> Optional[LLMJudge]:
    global_cfg = _get_section(config, "judges").get("llm", {})
    if not isinstance(global_cfg, Mapping):
        global_cfg = {}
    merged = _merge_dict(global_cfg, local_override or {})
    if not merged.get("enabled"):
        return None
    judge_config = LLMJudgeConfig(
        provider=str(merged.get("provider", "openai")),
        api_key=str(merged.get("api_key", "")),
        base_url=merged.get("base_url") or None,
        model=str(merged.get("model", "gpt-4o-mini")),
        temperature=float(merged.get("temperature", 0.0)),
        max_tokens=int(merged.get("max_tokens", 512)),
        timeout_seconds=int(merged.get("timeout_seconds", 30)),
    )
    return LLMJudge(judge_config)


def build_runners(config: Mapping[str, Any], engine: Engine) -> List[Runner]:
    runners_cfg = _get_section(config, "runners")
    runners: List[Runner] = []

    # retrieval
    retrieval_cfg = _get_section(runners_cfg, "retrieval")
    if retrieval_cfg.get("enabled"):
        runners.append(
            RetrievalRunner(
                engine,
                metric_names=retrieval_cfg.get("metrics"),
                k_values=retrieval_cfg.get("k_values"),
                top_n=int(retrieval_cfg.get("top_n", 10)),
                recall_top_k=int(retrieval_cfg.get("recall_top_k", 100)),
                include_context_recall=bool(retrieval_cfg.get("include_context_recall", False)),
                save_raw_payload=bool(retrieval_cfg.get("save_raw_payload", False)),
            )
        )

    # rerank
    rerank_cfg = _get_section(runners_cfg, "rerank")
    if rerank_cfg.get("enabled"):
        runners.append(
            RerankRunner(
                engine,
                metric_names=rerank_cfg.get("metrics"),
                k_values=rerank_cfg.get("k_values"),
                top_n=int(rerank_cfg.get("top_n", 5)),
                recall_top_k=int(rerank_cfg.get("recall_top_k", 100)),
                candidate_source=str(rerank_cfg.get("candidate_source", "retrieval")),
                baseline_source=str(rerank_cfg.get("baseline_source", "retrieval")),
                boost_metric_name=rerank_cfg.get("boost_metric_name"),
                save_raw_payload=bool(rerank_cfg.get("save_raw_payload", False)),
            )
        )

    # rewrite
    rewrite_cfg = _get_section(runners_cfg, "rewrite")
    if rewrite_cfg.get("enabled"):
        embedding_judge = _build_embedding_judge(config)
        semantic_similarity = str(rewrite_cfg.get("semantic_similarity", "auto")).lower()
        similarity_fn = None
        if semantic_similarity in {"auto", "embedding"} and embedding_judge is not None:
            similarity_fn = embedding_judge.similarity_async

        runners.append(
            RewriteRunner(
                engine,
                metric_names=rewrite_cfg.get("metrics"),
                top_n=int(rewrite_cfg.get("top_n", 10)),
                recall_top_k=int(rewrite_cfg.get("recall_top_k", 100)),
                rewrite_source=str(rewrite_cfg.get("rewrite_source", "field")),
                compare_with_original=bool(rewrite_cfg.get("compare_with_original", True)),
                gain_metric_name=str(rewrite_cfg.get("gain_metric", "ndcg@10")),
                semantic_similarity_fn=similarity_fn,
                save_raw_payload=bool(rewrite_cfg.get("save_raw_payload", False)),
            )
        )

    # generation
    generation_cfg = _get_section(runners_cfg, "generation")
    if generation_cfg.get("enabled"):
        llm_judge = _build_llm_judge(config, _get_section(generation_cfg, "llm_judge"))
        if llm_judge:
            async def judge_fn(query: str, answer: str, contexts: Sequence[str], sample: Any) -> Mapping[str, Any]:
                ref = getattr(sample, "answers", None)
                return await llm_judge.score_generation(query, answer, contexts, reference_answers=ref)
        else:
            judge_fn = None
        runners.append(
            GenerationRunner(
                engine,
                metric_names=generation_cfg.get("metrics"),
                context_source=str(generation_cfg.get("context_source", "retrieval")),
                top_n=int(generation_cfg.get("max_contexts", 5)),
                recall_top_k=int(generation_cfg.get("recall_top_k", 100)),
                judge_fn=judge_fn,
                save_raw_payload=bool(generation_cfg.get("save_raw_payload", False)),
            )
        )

    # e2e
    e2e_cfg = _get_section(runners_cfg, "e2e")
    if e2e_cfg.get("enabled"):
        llm_judge = _build_llm_judge(config, _get_section(e2e_cfg, "llm_judge"))
        if llm_judge:
            async def judge_fn(query: str, answer: str, contexts: Sequence[str], sample: Any) -> Mapping[str, Any]:
                ref = getattr(sample, "answers", None)
                return await llm_judge.score_e2e(query, answer, contexts, reference_answers=ref)
        else:
            judge_fn = None
        runners.append(
            E2ERunner(
                engine,
                metric_names=e2e_cfg.get("metrics"),
                top_n=int(e2e_cfg.get("top_n", 5)),
                recall_top_k=int(e2e_cfg.get("recall_top_k", 100)),
                record_latency=bool(e2e_cfg.get("record_latency", True)),
                cost_config=_get_section(e2e_cfg, "cost"),
                judge_fn=judge_fn,
                save_raw_payload=bool(e2e_cfg.get("save_raw_payload", False)),
            )
        )

    # ragas
    ragas_cfg = _get_section(runners_cfg, "ragas")
    if ragas_cfg.get("enabled"):
        runners.append(
            RagasRunner(
                engine,
                metrics=ragas_cfg.get("metrics"),
                save_raw_payload=bool(ragas_cfg.get("save_raw_payload", False)),
            )
        )

    return runners


def build_pipeline(config: Mapping[str, Any], engine: Engine) -> EvalPipeline:
    """构建评测流水线。"""
    runners = build_runners(config, engine)
    if not runners:
        raise ValueError("未启用任何 runner")
    pipeline_cfg = _get_section(config, "pipeline")
    return EvalPipeline(
        runners=runners,
        fail_fast=bool(pipeline_cfg.get("fail_fast", False)),
    )
