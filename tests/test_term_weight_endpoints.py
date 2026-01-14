from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


class TermWeightEndpointsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.tokenizer import tokenizers as tokenizers_module

        self._engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._SessionLocal = sessionmaker(bind=self._engine, future=True)
        self.db: Session = self._SessionLocal()

        from app.core.database import Base
        from app.models.term_weight import CorpusDocument, TermWeight
        from app.models.tokenizer import TokenizerConfig, TokenizerTerm

        Base.metadata.create_all(
            bind=self._engine,
            tables=[
                TokenizerConfig.__table__,
                TokenizerTerm.__table__,
                CorpusDocument.__table__,
                TermWeight.__table__,
            ],
        )

        def _fake_tokenize(self, text: str) -> list[str]:
            return [t for t in str(text).replace("，", " ").replace("。", " ").split() if t.strip()]

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

    def _insert_docs(self, contents: list[str]) -> None:
        from app.models.term_weight import CorpusDocument

        for content in contents:
            self.db.add(CorpusDocument(content=content))
        self.db.commit()

    def _get_term_weight_row(self, term: str):
        from app.models.term_weight import TermWeight

        return self.db.execute(select(TermWeight).where(TermWeight.term == term)).scalar_one_or_none()

    def test_manual_set_term_weight(self) -> None:
        from app.api.v1.endpoints.term_weight import set_term_weight
        from app.schemas.term_weight_schema import TermWeightSetRequest

        result = set_term_weight(TermWeightSetRequest(term="AI手机", weight=2.5), db=self.db)
        self.assertEqual(result.code, 200)
        self.assertTrue(result.data.success)

        row = self._get_term_weight_row("AI手机")
        self.assertIsNotNone(row)
        self.assertEqual(row.source, "MANUAL")
        self.assertAlmostEqual(row.weight, 2.5)

    def test_auto_calc_inserts_auto_weights_and_keeps_manual(self) -> None:
        from app.api.v1.endpoints.term_weight import auto_calc_term_weights, set_term_weight
        from app.schemas.term_weight_schema import TermWeightSetRequest

        self._insert_docs(
            [
                "AI手机 核心产品 大模型",
                "AI手机 影像 算法",
                "RAG 分词 召回 重排序",
                "核心产品 销量",
            ]
        )

        set_term_weight(TermWeightSetRequest(term="AI手机", weight=9.9), db=self.db)
        result = auto_calc_term_weights(db=self.db)
        self.assertEqual(result.code, 200)
        self.assertTrue(result.data.success)

        manual = self._get_term_weight_row("AI手机")
        self.assertIsNotNone(manual)
        self.assertEqual(manual.source, "MANUAL")
        self.assertAlmostEqual(manual.weight, 9.9)

        auto_term = self._get_term_weight_row("核心产品")
        self.assertIsNotNone(auto_term)
        self.assertEqual(auto_term.source, "AUTO")
        self.assertGreaterEqual(auto_term.weight, 0.0)
        self.assertLessEqual(auto_term.weight, 1.0)

