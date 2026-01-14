from __future__ import annotations

from typing import List, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.tokenizer import get_tokenizer_manager
from app.tokenizer.manager import Operation


class TokenizerService:
    """中文分词服务：封装分词器切换与自定义词库管理。"""

    def __init__(self, db: Session) -> None:
        self._manager = get_tokenizer_manager(db)

    def select_tokenizer(self, tokenizer_id: str) -> None:
        self._manager.select_tokenizer(tokenizer_id)

    def upsert_term(self, term: str, operation: Operation) -> None:
        self._manager.upsert_term(term, operation)

    async def batch_upsert_terms(
        self,
        upload_file: UploadFile,
        operation: Operation,
    ) -> Tuple[int, int]:
        raw = await upload_file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("文件编码仅支持 UTF-8") from exc

        terms = self._parse_terms_text(text)
        result = self._manager.batch_upsert(terms, operation)
        return result.success_count, result.fail_count

    def _parse_terms_text(self, text: str) -> List[str]:
        return [line.strip() for line in text.splitlines()]
