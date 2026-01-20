from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class TokenizeEndpointTestCase(unittest.TestCase):
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

        def _fake_tokenize(self, text: str) -> list[str]:
            punctuation = set(" ,，。；;：:！!？?、\n\t")
            return [ch for ch in str(text) if ch and ch not in punctuation and str(ch).strip()]

        self._patches = [
            patch.object(tokenizers_module.JiebaTokenizer, "is_available", return_value=True),
            patch.object(tokenizers_module.HanLPTokenizer, "is_available", return_value=True),
            patch.object(tokenizers_module.JiebaTokenizer, "tokenize", _fake_tokenize),
            patch.object(tokenizers_module.HanLPTokenizer, "tokenize", _fake_tokenize),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(getattr(self, "_patches", [])):
            p.stop()
        self.db.close()
        self._engine.dispose()

    def test_tokenize_empty_returns_empty_list(self) -> None:
        from app.api.v1.endpoints.tokenizer import tokenize_text
        from app.schemas.tokenizer_schema import TokenizeRequest

        result = tokenize_text(TokenizeRequest(text=""), scene_id=0, db=self.db)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.data.tokens, [])

    def test_tokenize_includes_custom_term_overlay(self) -> None:
        from app.api.v1.endpoints.tokenizer import tokenize_text, upsert_term
        from app.schemas.tokenizer_schema import TermUpsertRequest, TokenizeRequest

        upsert_term(TermUpsertRequest(term="AI算法", operation="ADD"), scene_id=0, db=self.db)
        result = tokenize_text(TokenizeRequest(text="手机AI算法系统"), scene_id=0, db=self.db)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.data.tokens, ["手", "机", "AI算法", "系", "统"])


if __name__ == "__main__":
    unittest.main()
