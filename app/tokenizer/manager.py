from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Set

from .tokenizers import HanLPTokenizer, JiebaTokenizer, Tokenizer
from .storage import SqlAlchemyTokenizerState
from .trie import TermTrie


Operation = Literal["ADD", "DELETE"]


@dataclass(frozen=True)
class BatchResult:
    success_count: int
    fail_count: int


class TokenizerManager:
    """
    分词器运行时管理器（进程内单例）：
    - 切换当前分词器
    - 管理自定义词条（增删/批量）
    - 对外提供 tokenize 能力（供后续 query 解析集成）
    """

    def __init__(self, state: SqlAlchemyTokenizerState) -> None:
        self._state = state
        self._tokenizers: Dict[str, Tokenizer] = {
            JiebaTokenizer.info.tokenizer_id: JiebaTokenizer(),
            HanLPTokenizer.info.tokenizer_id: HanLPTokenizer(),
        }
        self._current_tokenizer_id = state.load_tokenizer_id(
            default_id=JiebaTokenizer.info.tokenizer_id
        )
        if self._current_tokenizer_id not in self._tokenizers:
            self._current_tokenizer_id = JiebaTokenizer.info.tokenizer_id
        self._terms: Set[str] = state.load_terms()
        self._trie = TermTrie(self._terms)
        self._ensure_current_tokenizer_available()

    def _ensure_current_tokenizer_available(self) -> None:
        current = self._tokenizers[self._current_tokenizer_id]
        if current.is_available():
            return
        for tokenizer_id in sorted(self._tokenizers.keys()):
            candidate = self._tokenizers[tokenizer_id]
            if candidate.is_available():
                self._current_tokenizer_id = tokenizer_id
                self._state.save_tokenizer_id(tokenizer_id)
                return

    def list_tokenizers(self) -> List[str]:
        return list(self._tokenizers.keys())

    def current_tokenizer_id(self) -> str:
        return self._current_tokenizer_id

    def select_tokenizer(self, tokenizer_id: str) -> None:
        tokenizer_id = tokenizer_id.strip()
        if tokenizer_id not in self._tokenizers:
            supported = ", ".join(sorted(self._tokenizers.keys()))
            raise ValueError(f"不支持的 tokenizerId: {tokenizer_id}（可选：{supported}）")
        tokenizer = self._tokenizers[tokenizer_id]
        if not tokenizer.is_available():
            raise ValueError(f"分词器 {tokenizer_id} 依赖未安装或不可用")
        self._current_tokenizer_id = tokenizer_id
        self._state.save_tokenizer_id(tokenizer_id)

    def upsert_term(self, term: str, operation: Operation) -> bool:
        term = term.strip()
        if not term:
            raise ValueError("term 不能为空")
        if operation == "ADD":
            changed = self._state.add_term(term)
            if changed:
                self._terms.add(term)
        elif operation == "DELETE":
            changed = self._state.delete_term(term)
            if changed:
                self._terms.discard(term)
        else:
            raise ValueError("operation 仅支持 ADD/DELETE")

        if changed:
            self._trie = TermTrie(self._terms)
        return True

    def batch_upsert(self, terms: List[str], operation: Operation) -> BatchResult:
        success, fail, changed = self._state.batch_upsert(terms, operation)
        if changed:
            self._terms = self._state.load_terms()
            self._trie = TermTrie(self._terms)
        return BatchResult(success_count=success, fail_count=fail)

    def tokenize(self, text: str) -> List[str]:
        tokenizer = self._tokenizers[self._current_tokenizer_id]
        return self._tokenize_with_terms_overlay(text, tokenizer)

    def _tokenize_with_terms_overlay(self, text: str, tokenizer: Tokenizer) -> List[str]:
        """
        自定义词条覆盖层：
        - 先用专用词库做“最长匹配”切分，确保自定义词条整体输出
        - 非词条片段交给具体分词器（jieba/HanLP）处理
        """
        if not text:
            return []
        if self._trie.term_count == 0:
            return tokenizer.tokenize(text)

        tokens: List[str] = []
        buffer: List[str] = []

        def flush_buffer() -> None:
            if not buffer:
                return
            segment = "".join(buffer)
            buffer.clear()
            tokens.extend(tokenizer.tokenize(segment))

        i = 0
        while i < len(text):
            matched_len = self._trie.find_longest(text, i)
            if matched_len > 0:
                flush_buffer()
                tokens.append(text[i : i + matched_len])
                i += matched_len
                continue
            buffer.append(text[i])
            i += 1

        flush_buffer()
        return [t for t in tokens if t and t.strip()]


def get_tokenizer_manager(db) -> TokenizerManager:
    state = SqlAlchemyTokenizerState(db)
    return TokenizerManager(state)
