"""端到端评测指标（占位实现）。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from app.eval.core.interfaces import EvalSample, Metric
from app.eval.metrics.utils import get_metric_value, to_float


class E2ECorrectness(Metric):
    """端到端正确性（占位）。"""

    def name(self) -> str:
        return "e2e_correctness"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "e2e_correctness", 0.0))


class E2EFaithfulness(Metric):
    """端到端忠实度（占位）。"""

    def name(self) -> str:
        return "e2e_faithfulness"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "e2e_faithfulness", 0.0))


class Latency(Metric):
    """端到端延迟（毫秒，占位）。"""

    def name(self) -> str:
        return "latency"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "latency", 0.0))


class TTFT(Metric):
    """首 Token 时间（毫秒，占位）。"""

    def name(self) -> str:
        return "ttft"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "ttft", 0.0))


class CostPerQuery(Metric):
    """单次成本（占位）。"""

    def name(self) -> str:
        return "cost_per_query"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "cost_per_query", 0.0))


def build_e2e_metrics(names: Optional[List[str]] = None) -> List[Metric]:
    """构建端到端指标集合。"""
    metric_map: Dict[str, Metric] = {
        "e2e_correctness": E2ECorrectness(),
        "e2e_faithfulness": E2EFaithfulness(),
        "latency": Latency(),
        "ttft": TTFT(),
        "cost_per_query": CostPerQuery(),
    }
    if not names:
        return list(metric_map.values())
    metrics: List[Metric] = []
    for name in names:
        key = str(name).strip().lower()
        if key not in metric_map:
            raise ValueError(f"未知 E2E 指标: {name}")
        metrics.append(metric_map[key])
    return metrics
