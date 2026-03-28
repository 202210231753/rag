from app.eval.core.interfaces import EvalSample
from app.eval.metrics.retrieval import RecallAtK, HitRateAtK, NDCGAtK, ContextRecallAtK

# 测试 retrieval 评测指标的基本计算逻辑
def test_retrieval_metrics_basic():
    sample = EvalSample(id="1", query="q", relevant_doc_ids=["a", "b"])
    payload = {"results": [{"doc_id": "a"}, {"doc_id": "x"}, {"doc_id": "b"}]}
    assert RecallAtK(2).compute(sample, payload) == 0.5
    assert HitRateAtK(2).compute(sample, payload) == 1.0
    assert NDCGAtK(2).compute(sample, payload) > 0

# 测试 context recall 评测指标的基本计算逻辑
def test_context_recall():
    sample = EvalSample(id="1", query="q", relevant_texts=["hello world"])
    payload = {"results": [{"content": "hello world and more"}]}
    assert ContextRecallAtK(1).compute(sample, payload) == 1.0
