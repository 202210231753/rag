from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.tokenizer.manager import Operation
from app.tokenizer import get_tokenizer_manager


DEFAULT_SCENE_ID = 0


class TokenizerAdminService:
    """
    中文分词“管理端”服务：
    - 切换当前分词器（全局）
    - 管理自定义词条（按 scene_id 隔离）
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def select_tokenizer(self, tokenizer_id: str) -> None:
        manager = get_tokenizer_manager(self._db, scene_id=DEFAULT_SCENE_ID)
        manager.select_tokenizer(tokenizer_id)

    def upsert_term(self, term: str, operation: Operation, scene_id: int = DEFAULT_SCENE_ID) -> None:
        manager = get_tokenizer_manager(self._db, scene_id=int(scene_id))
        manager.upsert_term(term, operation)

    async def batch_upsert_terms(
        self,
        upload_file: UploadFile,
        operation: Operation,
        scene_id: int = DEFAULT_SCENE_ID,
    ) -> tuple[int, int]:
        content = await upload_file.read()
        try:
            text = content.decode("utf-8")
        except Exception as exc:
            raise ValueError("文件编码必须为 UTF-8") from exc

        terms = [line.strip() for line in text.splitlines()]
        manager = get_tokenizer_manager(self._db, scene_id=int(scene_id))
        result = manager.batch_upsert(terms, operation)
        return result.success_count, result.fail_count

