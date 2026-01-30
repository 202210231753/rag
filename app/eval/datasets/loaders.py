"""评测数据加载器（JSONL / CSV）。"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.eval.core.interfaces import EvalSample
from app.eval.datasets.schema import FieldNames, build_field_map
from app.eval.datasets.validators import (
    ValidationError,
    build_sample_from_record,
    normalize_raw_record_with_fields,
    validate_sample,
)


def _read_jsonl(path: Path, encoding: str) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _read_csv(path: Path, encoding: str) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _get_record_value(record: Dict[str, Any], key: str) -> Any:
    """支持 a.b 形式的字段获取。"""
    if "." not in key:
        return record.get(key)
    cur: Any = record
    for part in key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _matches_filters(metadata: Any, filters: Dict[str, Any]) -> bool:
    if not filters:
        return True
    if not isinstance(metadata, dict):
        return False
    for key, expected in filters.items():
        value = metadata.get(key)
        if isinstance(expected, list):
            if value not in expected:
                return False
        else:
            if value != expected:
                return False
    return True


def load_samples(
    path: str,
    format: str,
    encoding: str = "utf-8",
    field_map: Optional[Dict[str, str]] = None,
    *,
    list_fields: Optional[Sequence[str]] = None,
    split: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    sample_limit: Optional[int] = None,
    shuffle: bool = False,
    shuffle_seed: int = 42,
    deduplicate: bool = False,
    dedup_key: str = "id",
    validate: bool = True,
    on_validation_error: str = "fail",
    drop_empty_query: bool = True,
) -> List[EvalSample]:
    """加载评测样本。

    参数:
        list_fields: 需要按 JSON list 解析的字段
        split: 仅保留指定 split 的样本
        filters: 基于 metadata 的过滤条件
        sample_limit: 抽样数量
        shuffle: 是否随机打乱
        deduplicate: 是否去重
        dedup_key: 去重键（支持 metadata.xxx）
        validate: 是否校验样本
        on_validation_error: fail | skip
        drop_empty_query: 是否过滤空 query
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")

    fmt = format.strip().lower()
    if fmt not in {"jsonl", "csv"}:
        raise ValueError(f"不支持的数据格式: {format}")

    mapping = build_field_map(field_map).mapping
    records: Iterable[Dict[str, Any]]
    if fmt == "jsonl":
        records = _read_jsonl(file_path, encoding)
    else:
        records = _read_csv(file_path, encoding)

    record_list = list(records)
    if shuffle:
        rng = random.Random(shuffle_seed)
        rng.shuffle(record_list)

    samples: List[EvalSample] = []
    seen: set[str] = set()
    f_names = FieldNames()
    list_fields = list(list_fields) if list_fields else list(f_names.list_fields())
    filters = filters or {}

    for idx, record in enumerate(record_list, start=1):
        normalized = normalize_raw_record_with_fields(record, list_fields=list_fields)
        sample = build_sample_from_record(normalized, mapping, default_id=str(idx))

        if drop_empty_query and not sample.query.strip():
            if on_validation_error == "fail":
                raise ValidationError(f"样本 {sample.id} 缺少 query")
            continue

        if split and (sample.split or "").strip() != split:
            continue

        if not _matches_filters(sample.metadata, filters):
            continue

        if deduplicate:
            if dedup_key.startswith("metadata."):
                meta_key = dedup_key.split(".", 1)[1]
                dedup_value = None
                if isinstance(sample.metadata, dict):
                    dedup_value = sample.metadata.get(meta_key)
            elif hasattr(sample, dedup_key):
                dedup_value = getattr(sample, dedup_key)
            else:
                dedup_value = _get_record_value(normalized, dedup_key)
            dedup_value = str(dedup_value) if dedup_value is not None else ""
            if dedup_value in seen:
                continue
            seen.add(dedup_value)

        if validate:
            try:
                validate_sample(sample, require_query=True)
            except ValidationError:
                if on_validation_error == "skip":
                    continue
                raise

        samples.append(sample)
        if sample_limit is not None and len(samples) >= int(sample_limit):
            break

    return samples
