"""评测数据集字段与映射定义。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class FieldNames:
    """标准字段名集合。"""

    id: str = "id"
    query: str = "query"
    answers: str = "answers"
    relevant_doc_ids: str = "relevant_doc_ids"
    relevant_texts: str = "relevant_texts"
    rewrite: str = "rewrite"
    metadata: str = "metadata"
    candidate_doc_ids: str = "candidate_doc_ids"
    candidate_texts: str = "candidate_texts"
    contexts: str = "contexts"
    split: str = "split"

    def list_fields(self) -> Tuple[str, ...]:
        """默认需要按 list 解析的字段。"""
        return (
            self.answers,
            self.relevant_doc_ids,
            self.relevant_texts,
            self.candidate_doc_ids,
            self.candidate_texts,
            self.contexts,
        )


@dataclass
class FieldMap:
    """数据集字段映射。"""

    mapping: Dict[str, str]

    def resolve(self, field: str) -> str:
        return self.mapping.get(field, field)


def build_field_map(raw_map: Optional[Dict[str, str]] = None) -> FieldMap:
    """构建字段映射对象。"""
    return FieldMap(mapping=raw_map or {})
