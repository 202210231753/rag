"""评测数据校验器。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.eval.core.interfaces import EvalSample
from app.eval.datasets.schema import FieldNames


class ValidationError(Exception):
    """评测数据校验异常。"""


def _ensure_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _parse_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            parsed = json.loads(value)
            return parsed
        except json.JSONDecodeError:
            return value
    return value


def _parse_json_list(value: Any) -> Any:
    parsed = _parse_json_value(value)
    if parsed is None:
        return None
    if isinstance(parsed, list):
        return parsed
    return parsed


def validate_sample(
    sample: EvalSample,
    require_query: bool = True,
    allow_empty_query: bool = False,
) -> None:
    """校验样本合法性。"""
    if require_query and not sample.query and not allow_empty_query:
        raise ValidationError(f"样本 {sample.id} 缺少 query")


def normalize_raw_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """对原始记录进行基础规范化。"""
    return normalize_raw_record_with_fields(raw)


def normalize_raw_record_with_fields(
    raw: Dict[str, Any],
    list_fields: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """对原始记录进行基础规范化（可自定义 list 字段）。"""
    normalized: Dict[str, Any] = dict(raw)
    fields = list(list_fields) if list_fields else list(FieldNames().list_fields())
    for field in fields:
        normalized[field] = _parse_json_list(normalized.get(field))
    # metadata 允许 dict / JSON 字符串
    normalized["metadata"] = _parse_json_value(normalized.get("metadata"))
    return normalized


def build_sample_from_record(
    record: Dict[str, Any],
    field_map: Dict[str, str],
    default_id: str,
) -> EvalSample:
    """将原始记录构造成 EvalSample。"""
    def _get(field: str) -> Any:
        return record.get(field_map.get(field, field))

    sample = EvalSample(
        id=str(_get("id") or default_id),
        query=str(_get("query") or ""),
        answers=_ensure_list(_get("answers")),
        relevant_doc_ids=_ensure_list(_get("relevant_doc_ids")),
        relevant_texts=_ensure_list(_get("relevant_texts")),
        rewrite=_get("rewrite"),
        metadata=_get("metadata") or None,
        candidate_doc_ids=_ensure_list(_get("candidate_doc_ids")),
        candidate_texts=_ensure_list(_get("candidate_texts")),
        contexts=_ensure_list(_get("contexts")),
        split=_get("split"),
    )
    return sample


def validate_and_collect(
    samples: List[EvalSample],
    require_query: bool = True,
) -> Tuple[List[EvalSample], List[str]]:
    """批量校验样本，返回有效样本与错误信息。"""
    valid: List[EvalSample] = []
    errors: List[str] = []
    for sample in samples:
        try:
            validate_sample(sample, require_query=require_query)
            valid.append(sample)
        except ValidationError as exc:
            errors.append(str(exc))
    return valid, errors
