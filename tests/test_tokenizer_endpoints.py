from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@dataclass
class _FakeUploadFile:
    content: bytes

    async def read(self) -> bytes:
        return self.content


class TokenizerEndpointsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.tokenizer import tokenizers as tokenizers_module

        self._engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._SessionLocal = sessionmaker(bind=self._engine, future=True)
        self.db: Session = self._SessionLocal()

        from app.core.database import Base
        from app.models.tokenizer import TokenizerConfig, TokenizerTerm

        Base.metadata.create_all(
            bind=self._engine,
            tables=[TokenizerConfig.__table__, TokenizerTerm.__table__],
        )

        self._patches = [
            patch.object(tokenizers_module.JiebaTokenizer, "is_available", return_value=True),
            patch.object(tokenizers_module.HanLPTokenizer, "is_available", return_value=True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(getattr(self, "_patches", [])):
            p.stop()
        self.db.close()
        self._engine.dispose()

    def _load_tokenizer_id(self) -> str | None:
        from app.models.tokenizer import TokenizerConfig

        row = self.db.execute(select(TokenizerConfig).where(TokenizerConfig.id == 1)).scalar_one_or_none()
        return None if row is None else row.tokenizer_id

    def _list_terms(self) -> list[str]:
        from app.models.tokenizer import TokenizerTerm

        rows = self.db.execute(select(TokenizerTerm.term)).all()
        return sorted([term for (term,) in rows if term and str(term).strip()])

    def _run_async(self, awaitable):
        return asyncio.run(awaitable)

    def test_select_tokenizer_success(self) -> None:
        from app.api.v1.endpoints.tokenizer import select_tokenizer
        from app.schemas.tokenizer_schema import TokenizerSelectRequest

        result = select_tokenizer(TokenizerSelectRequest(tokenizerId="jieba"), db=self.db)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.msg, "success")
        self.assertTrue(result.data.success)
        self.assertEqual(self._load_tokenizer_id(), "jieba")

    def test_select_tokenizer_invalid_id(self) -> None:
        from app.api.v1.endpoints.tokenizer import select_tokenizer
        from app.schemas.tokenizer_schema import TokenizerSelectRequest

        with self.assertRaises(HTTPException) as ctx:
            select_tokenizer(TokenizerSelectRequest(tokenizerId="unknown"), db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("不支持的 tokenizerId", str(ctx.exception.detail))

    def test_term_add_then_delete(self) -> None:
        from app.api.v1.endpoints.tokenizer import upsert_term
        from app.schemas.tokenizer_schema import TermUpsertRequest

        add_result = upsert_term(TermUpsertRequest(term="遥遥领先", operation="ADD"), db=self.db)
        self.assertEqual(add_result.code, 200)
        self.assertTrue(add_result.data.success)
        self.assertEqual(self._list_terms(), ["遥遥领先"])

        del_result = upsert_term(TermUpsertRequest(term="遥遥领先", operation="DELETE"), db=self.db)
        self.assertEqual(del_result.code, 200)
        self.assertTrue(del_result.data.success)
        self.assertEqual(self._list_terms(), [])

    def test_term_validation_error(self) -> None:
        from app.api.v1.endpoints.tokenizer import upsert_term
        from app.schemas.tokenizer_schema import TermUpsertRequest

        with self.assertRaises(HTTPException) as ctx:
            upsert_term(TermUpsertRequest(term="", operation="ADD"), db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("term 不能为空", str(ctx.exception.detail))

    def test_batch_add_counts_and_persistence(self) -> None:
        from app.api.v1.endpoints.tokenizer import batch_upsert_terms

        content = "遥遥领先\n\n大模型\n  \nRAG\n"
        result = self._run_async(
            batch_upsert_terms(
                file=_FakeUploadFile(content=content.encode("utf-8")),
                operation="ADD",
                db=self.db,
            )
        )
        self.assertEqual(result.code, 200)
        self.assertEqual(result.msg, "success")
        self.assertEqual(result.data.success_count, 3)
        self.assertEqual(result.data.fail_count, 2)
        self.assertEqual(self._list_terms(), ["RAG", "大模型", "遥遥领先"])

    def test_batch_delete_is_idempotent(self) -> None:
        from app.api.v1.endpoints.tokenizer import batch_upsert_terms

        self._run_async(
            batch_upsert_terms(
                file=_FakeUploadFile(content="A\nB\n".encode("utf-8")),
                operation="ADD",
                db=self.db,
            )
        )

        result = self._run_async(
            batch_upsert_terms(
                file=_FakeUploadFile(content="A\nC\n\n".encode("utf-8")),
                operation="DELETE",
                db=self.db,
            )
        )
        self.assertEqual(result.code, 200)
        self.assertEqual(result.data.success_count, 2)
        self.assertEqual(result.data.fail_count, 1)
        self.assertEqual(self._list_terms(), ["B"])

    def test_batch_invalid_operation(self) -> None:
        from app.api.v1.endpoints.tokenizer import batch_upsert_terms

        with self.assertRaises(HTTPException) as ctx:
            self._run_async(
                batch_upsert_terms(
                    file=_FakeUploadFile(content="A\n".encode("utf-8")),
                    operation="UPSERT",
                    db=self.db,
                )
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("operation 仅支持 ADD/DELETE", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()

