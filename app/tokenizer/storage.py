from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable, Set, Tuple

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


@dataclass(frozen=True)
class TokenizerStoragePaths:
    state_dir: Path
    tokenizer_config_path: Path
    terms_path: Path


class FileBackedTokenizerState:
    def __init__(self, paths: TokenizerStoragePaths) -> None:
        self._paths = paths
        self._lock = RLock()

    def load_tokenizer_id(self, default_id: str) -> str:
        with self._lock:
            path = self._paths.tokenizer_config_path
            if not path.exists():
                return default_id
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                tokenizer_id = str(data.get("tokenizerId", "")).strip()
                return tokenizer_id or default_id
            except Exception:
                return default_id

    def save_tokenizer_id(self, tokenizer_id: str) -> None:
        with self._lock:
            payload = {"tokenizerId": tokenizer_id}
            _atomic_write_text(
                self._paths.tokenizer_config_path,
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            )

    def load_terms(self) -> Set[str]:
        with self._lock:
            path = self._paths.terms_path
            if not path.exists():
                return set()
            terms: Set[str] = set()
            for line in path.read_text(encoding="utf-8").splitlines():
                term = line.strip()
                if term:
                    terms.add(term)
            return terms

    def save_terms(self, terms: Iterable[str]) -> None:
        with self._lock:
            normalized = sorted({t.strip() for t in terms if t and t.strip()})
            content = "\n".join(normalized) + ("\n" if normalized else "")
            _atomic_write_text(self._paths.terms_path, content)


_schema_lock = RLock()
_initialized_binds: Set[int] = set()


def ensure_tokenizer_tables(db: Session) -> None:
    """
    在无迁移工具的前提下，尽量安全地确保 tokenizer 相关表存在。
    """
    from app.models.tokenizer import TokenizerConfig, TokenizerTerm

    bind = db.get_bind()
    bind_id = id(bind)
    with _schema_lock:
        if bind_id in _initialized_binds:
            return
        from app.core.database import Base

        Base.metadata.create_all(bind=bind, tables=[TokenizerConfig.__table__, TokenizerTerm.__table__])
        _initialized_binds.add(bind_id)


class SqlAlchemyTokenizerState:
    def __init__(self, db: Session) -> None:
        self._db = db
        ensure_tokenizer_tables(db)

    def load_tokenizer_id(self, default_id: str) -> str:
        from app.models.tokenizer import TokenizerConfig

        row = self._db.execute(select(TokenizerConfig).where(TokenizerConfig.id == 1)).scalar_one_or_none()
        if row is None:
            return default_id
        tokenizer_id = (row.tokenizer_id or "").strip()
        return tokenizer_id or default_id

    def save_tokenizer_id(self, tokenizer_id: str) -> None:
        from app.models.tokenizer import TokenizerConfig

        existing = self._db.execute(select(TokenizerConfig).where(TokenizerConfig.id == 1)).scalar_one_or_none()
        if existing is None:
            self._db.add(TokenizerConfig(id=1, tokenizer_id=tokenizer_id))
        else:
            existing.tokenizer_id = tokenizer_id
        self._db.commit()

    def load_terms(self) -> Set[str]:
        from app.models.tokenizer import TokenizerTerm

        rows = self._db.execute(select(TokenizerTerm.term)).all()
        return {term for (term,) in rows if term and str(term).strip()}

    def add_term(self, term: str) -> bool:
        from app.models.tokenizer import TokenizerTerm

        try:
            self._db.add(TokenizerTerm(term=term))
            self._db.commit()
            return True
        except IntegrityError:
            self._db.rollback()
            return False

    def delete_term(self, term: str) -> bool:
        from app.models.tokenizer import TokenizerTerm

        result = self._db.execute(delete(TokenizerTerm).where(TokenizerTerm.term == term))
        self._db.commit()
        return (result.rowcount or 0) > 0

    def batch_upsert(self, terms: list[str], operation: str) -> Tuple[int, int, bool]:
        """
        返回：(success_count, fail_count, changed)
        - success_count：非空行计为成功（与幂等语义一致）
        - fail_count：空行/全空白行
        - changed：是否对 DB 产生了实际变更（新增或删除）
        """
        success = 0
        fail = 0
        changed = False
        op = operation.strip().upper()
        if op not in {"ADD", "DELETE"}:
            raise ValueError("operation 仅支持 ADD/DELETE")

        for raw in terms:
            term = (raw or "").strip()
            if not term:
                fail += 1
                continue
            success += 1
            if op == "ADD":
                if self.add_term(term):
                    changed = True
            else:
                if self.delete_term(term):
                    changed = True
        return success, fail, changed
