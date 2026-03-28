"""指标通用工具函数。"""

from __future__ import annotations

from typing import Any, Mapping


def _get_nested_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def get_metric_value(payload: Mapping[str, Any], key: str, default: Any = 0.0) -> Any:
    """从 payload 中读取指标值（支持常见嵌套结构）。"""
    if key in payload:
        return payload.get(key)
    metrics = _get_nested_mapping(payload, "metrics")
    if key in metrics:
        return metrics.get(key)
    scores = _get_nested_mapping(payload, "scores")
    if key in scores:
        return scores.get(key)
    return default


def to_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    try:
        return float(value)
    except Exception:
        return float(default)
