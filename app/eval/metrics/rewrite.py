"""改写阶段评测指标。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from app.eval.core.interfaces import EvalSample, Metric
from app.eval.metrics.utils import get_metric_value, to_float


class SemanticPreservation(Metric):
    """语义保留度（占位，需在 runner 中提供 embedding 相似度）。"""

    def name(self) -> str:
        return "semantic_preservation"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "semantic_preservation", 0.0))


class RetrievalGain(Metric):
    """检索增益（占位，需在 runner 中提供增益值）。"""

    def name(self) -> str:
        return "retrieval_gain"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "retrieval_gain", 0.0))


class ZeroResultReduction(Metric):
    """零结果率下降（占位，需在 runner 中提供）。"""

    def name(self) -> str:
        return "zero_result_reduction"

    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        return to_float(get_metric_value(payload, "zero_result_reduction", 0.0))


def build_rewrite_metrics(names: Optional[List[str]] = None) -> List[Metric]:
    """构建改写指标集合。"""
    metric_map: Dict[str, Metric] = {
        "semantic_preservation": SemanticPreservation(),
        "retrieval_gain": RetrievalGain(),
        "zero_result_reduction": ZeroResultReduction(),
    }
    if not names:
        return list(metric_map.values())
    metrics: List[Metric] = []
    for name in names:
        key = str(name).strip().lower()
        if key not in metric_map:
            raise ValueError(f"未知改写指标: {name}")
        metrics.append(metric_map[key])
    return metrics
