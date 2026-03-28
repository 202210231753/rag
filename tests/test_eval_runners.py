import asyncio

from app.eval.core.interfaces import EvalSample
from app.eval.runners import RetrievalRunner, RewriteRunner, GenerationRunner

# 用来模拟 EvalEngine 行为的 DummyEngine
class DummyEngine:
    async def retrieve(self, query: str, top_n: int, recall_top_k: int):
        return {"results": [{"doc_id": "1", "content": "alpha"}]}

    async def rerank(self, query, candidates):
        return {"results": candidates}

    async def rewrite(self, query: str) -> str:
        return query + " rewritten"

    async def generate(self, query: str, contexts):
        return {"answer": "answer", "faithfulness": 1.0}

    async def close(self) -> None:
        return None


def test_retrieval_runner():
    engine = DummyEngine()
    runner = RetrievalRunner(engine, metric_names=["recall@1"])
    sample = EvalSample(id="1", query="q", relevant_doc_ids=["1"])
    results = asyncio.run(runner.run([sample]))
    assert results[0].metrics["recall@1"] == 1.0


def test_rewrite_runner_semantic():
    engine = DummyEngine()
    runner = RewriteRunner(engine, rewrite_source="engine", compare_with_original=False)
    sample = EvalSample(id="1", query="hello")
    results = asyncio.run(runner.run([sample]))
    assert "semantic_preservation" in results[0].metrics


def test_generation_runner_with_judge():
    async def judge_fn(query, answer, contexts, sample):
        return {"faithfulness": 0.8, "answer_relevance": 0.9, "answer_correctness": 0.7, "hallucination_rate": 0.1}

    engine = DummyEngine()
    runner = GenerationRunner(engine, judge_fn=judge_fn, context_source="retrieval")
    sample = EvalSample(id="1", query="q")
    results = asyncio.run(runner.run([sample]))
    assert results[0].metrics["faithfulness"] == 0.8
