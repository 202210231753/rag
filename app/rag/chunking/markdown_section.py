from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from llama_index.core.node_parser import SentenceSplitter


_FENCE_RE = re.compile(r"^\s*```")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ChunkUnit:
    text: str
    heading_path: List[str]
    block_type: str  # section|code|table
    section_index: int


@dataclass(frozen=True)
class SectionBlock:
    heading_path: List[str]
    body: str
    section_index: int


def parse_markdown_sections(markdown: str) -> List[SectionBlock]:
    """Parse markdown into heading-aware sections.

    - Headings (#..######) start new sections (outside fenced code blocks).
    - Fenced code blocks are treated as opaque content (headings inside ignored).

    Returns sections in document order. A section may have empty heading_path.
    """

    lines = (markdown or "").splitlines()
    heading_stack: List[str] = []
    current_lines: List[str] = []
    sections: List[SectionBlock] = []

    in_code_block = False
    section_index = 0

    def flush() -> None:
        nonlocal section_index
        body = "\n".join(current_lines).strip("\n")
        if body.strip():
            sections.append(
                SectionBlock(
                    heading_path=list(heading_stack),
                    body=body,
                    section_index=section_index,
                )
            )
            section_index += 1
        current_lines.clear()

    for line in lines:
        if _FENCE_RE.match(line):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if not in_code_block:
            m = _HEADING_RE.match(line)
            if m:
                # New heading starts a new section.
                flush()
                level = len(m.group(1))
                title = m.group(2).strip()

                # Maintain stack for heading path.
                if level <= 0:
                    level = 1
                if len(heading_stack) >= level:
                    heading_stack[:] = heading_stack[: level - 1]
                heading_stack.append(title)

                # Keep the heading line in content for context.
                current_lines.append(line)
                continue

        current_lines.append(line)

    flush()

    # Fallback: if everything was empty, return one empty section.
    if not sections and (markdown or "").strip():
        sections.append(SectionBlock(heading_path=[], body=str(markdown), section_index=0))

    return sections


_TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


def _looks_like_table_header(line: str, next_line: str | None) -> bool:
    if next_line is None:
        return False
    if "|" not in line:
        return False
    return bool(_TABLE_SEPARATOR_RE.match(next_line))


def _split_section_into_blocks(section_text: str) -> List[tuple[str, str]]:
    """Split a section into blocks of (block_type, text).

    block_type: text|code|table

    Notes:
    - Fenced code blocks are treated as atomic.
    - Markdown tables are treated as atomic (simple heuristic: header+separator).
    """

    lines = (section_text or "").splitlines()
    blocks: List[tuple[str, str]] = []
    buf: List[str] = []

    def flush_text() -> None:
        if not buf:
            return
        text = "\n".join(buf).strip("\n")
        if text.strip():
            blocks.append(("text", text))
        buf.clear()

    i = 0
    in_code = False
    code_buf: List[str] = []

    while i < len(lines):
        line = lines[i]

        # fenced code block
        if _FENCE_RE.match(line):
            if not in_code:
                flush_text()
                in_code = True
                code_buf = [line]
            else:
                code_buf.append(line)
                blocks.append(("code", "\n".join(code_buf)))
                code_buf = []
                in_code = False
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # markdown table (header + separator)
        next_line = lines[i + 1] if i + 1 < len(lines) else None
        if _looks_like_table_header(line, next_line):
            flush_text()
            table_lines = [line, next_line]
            i += 2
            while i < len(lines):
                l2 = lines[i]
                if "|" in l2 and l2.strip():
                    table_lines.append(l2)
                    i += 1
                    continue
                break
            blocks.append(("table", "\n".join(table_lines)))
            continue

        buf.append(line)
        i += 1

    if in_code and code_buf:
        # Unclosed fence: treat as text to avoid dropping content.
        buf.extend(code_buf)

    flush_text()
    return blocks


def chunk_markdown_structure_aware(
    markdown: str,
    splitter: SentenceSplitter,
    chunking_version: str,
) -> List[ChunkUnit]:
    """Chunk markdown using heading-aware sections + block-aware splitting.

    Strategy:
    1) Split markdown into sections by headings.
    2) Within each section, keep code/table blocks atomic.
    3) Split remaining text blocks via SentenceSplitter.

    Returns ChunkUnit list in order.
    """

    sections = parse_markdown_sections(markdown)
    units: List[ChunkUnit] = []

    for section in sections:
        blocks = _split_section_into_blocks(section.body)
        for block_type, block_text in blocks:
            if block_type == "text":
                parts = splitter.split_text(block_text or "")
                for part in parts:
                    text = (part or "").strip()
                    if not text:
                        continue
                    units.append(
                        ChunkUnit(
                            text=text,
                            heading_path=list(section.heading_path),
                            block_type="section",
                            section_index=section.section_index,
                        )
                    )
                continue

            # code/table are emitted as atomic chunks
            text = (block_text or "").strip("\n")
            if not text.strip():
                continue
            units.append(
                ChunkUnit(
                    text=text,
                    heading_path=list(section.heading_path),
                    block_type=block_type,
                    section_index=section.section_index,
                )
            )

    # Keep version available to callers via metadata; passed separately here.
    # (We don't store it in ChunkUnit to keep it pure content/structure.)
    _ = chunking_version

    return units
