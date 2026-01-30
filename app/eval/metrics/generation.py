"""生成阶段评测指标（占位实现）。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from app.eval.core.interfaces import EvalSample, Metric
from app.eval.metrics.utils import get_metric_value, to_float


class Faithfulness(Metric):
    """忠实度（占位）。"""

    def name(self) -> str:
        return "faithfulness"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "faithfulness", 0.0))


class AnswerRelevance(Metric):
    """答案相关性（占位）。"""

    def name(self) -> str:
        return "answer_relevance"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "answer_relevance", 0.0))


class AnswerCorrectness(Metric):
    """答案正确性（占位）。"""

    def name(self) -> str:
        return "answer_correctness"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "answer_correctness", 0.0))


class HallucinationRate(Metric):
    """幻觉率（占位）。"""

    def name(self) -> str:
        return "hallucination_rate"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "hallucination_rate", 0.0))


def build_generation_metrics(names: Optional[List[str]] = None) -> List[Metric]:
    """构建生成指标集合。"""
    metric_map: Dict[str, Metric] = {
        "faithfulness": Faithfulness(),
        "answer_relevance": AnswerRelevance(),
        "answer_correctness": AnswerCorrectness(),
        "hallucination_rate": HallucinationRate(),
    }
    if not names:
        return list(metric_map.values())
    metrics: List[Metric] = []
    for name in names:
        key = str(name).strip().lower()
        if key not in metric_map:
            raise ValueError(f"未知生成指标: {name}")
        metrics.append(metric_map[key])
    return metrics
