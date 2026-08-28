"""Structure-aware markdown chunking for merchant knowledge documents.

The default fixed-window chunker splits mid-answer and strands a policy clause from
its heading. Merchant knowledge here is small and highly structured (Q&A FAQs,
one-paragraph policies, label+bullet guides), so we chunk on *semantic units*:

  * FAQ docs .............. one chunk per ``Q:``/``A:`` pair
  * policy docs ........... one chunk per ``#``/``##`` section (whole doc if flat)
  * guide docs ........... one chunk per ``Label:`` + its bullet list
  * anything oversized ... hard-split on sentence boundaries with a small overlap

Every chunk is prefixed with the document's ``# Title`` so a bare ``A: ...`` still
carries its context into the vector.

Token counts are a deliberate ~4-chars/token estimate (tiktoken is not a runtime
dependency); the bounds in ``config.py`` have generous headroom for the error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_FAQ_Q_RE = re.compile(r"^\s*Q:\s*", re.IGNORECASE)
_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 /&'-]{0,60}:\s*$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    heading: str
    token_estimate: int


def _extract_title(lines: list[str]) -> tuple[str, list[str]]:
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line.strip())
        if m and m.group(1) == "#":
            return m.group(2).strip(), lines[:i] + lines[i + 1 :]
    return "", lines


def _semantic_units(body: str) -> list[tuple[str, str]]:
    """Split a document body into (heading, text) semantic units."""
    lines = body.splitlines()

    if any(_FAQ_Q_RE.match(line) for line in lines):
        return _split_faq(lines)

    sections = _split_headings(lines)
    units: list[tuple[str, str]] = []
    for heading, text in sections:
        units.extend(_split_label_groups(heading, text))
    return units or [("", body.strip())]


def _split_faq(lines: list[str]) -> list[tuple[str, str]]:
    """One unit per Q&A. The question line becomes the heading, which also keeps
    the merge pass in ``chunk_markdown`` from folding distinct answers together."""
    units: list[tuple[str, str]] = []
    current: list[str] = []

    def emit(block: list[str]) -> None:
        text = "\n".join(block).strip()
        if not text:
            return
        q = next((ln for ln in block if _FAQ_Q_RE.match(ln)), "")
        units.append((_FAQ_Q_RE.sub("", q).strip()[:80], text))

    for line in lines:
        if _FAQ_Q_RE.match(line) and current:
            emit(current)
            current = [line]
        else:
            current.append(line)
    emit(current)
    return units


def _split_headings(lines: list[str]) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    buf: list[str] = []
    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if buf:
                sections.append((heading, buf))
            heading = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append((heading, buf))
    return [(h, "\n".join(b).strip()) for h, b in sections if "\n".join(b).strip()]


def _split_label_groups(heading: str, text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    if not any(_LABEL_RE.match(line.strip()) for line in lines):
        return [(heading, text)]

    groups: list[tuple[str, str]] = []
    label = heading
    buf: list[str] = []
    for line in lines:
        if _LABEL_RE.match(line.strip()):
            if buf:
                groups.append((label, "\n".join(buf).strip()))
            label = line.strip().rstrip(":")
            buf = [line]
        else:
            buf.append(line)
    if buf and "\n".join(buf).strip():
        groups.append((label, "\n".join(buf).strip()))
    return groups


def _hard_split(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text)
    out: list[str] = []
    buf: list[str] = []
    for sent in sentences:
        buf.append(sent)
        if estimate_tokens(" ".join(buf)) >= max_tokens:
            out.append(" ".join(buf).strip())
            carry = buf[-1:] if estimate_tokens(buf[-1]) <= overlap_tokens else []
            buf = list(carry)
    if buf and " ".join(buf).strip():
        out.append(" ".join(buf).strip())
    return out or [text]


def chunk_markdown(
    raw: str,
    *,
    target_tokens: int = 512,
    max_tokens: int = 800,
    overlap_tokens: int = 64,
) -> list[Chunk]:
    """One chunk per semantic unit (Q&A pair / policy section / label group).

    Units are only merged when *consecutive*, *under the same heading*, and their
    combined size stays under ``target_tokens`` — so a stray one-line note folds
    into its neighbour but two distinct FAQ answers never share a vector. Units
    larger than ``max_tokens`` are sentence-split with a small overlap.
    """
    title, body_lines = _extract_title(raw.splitlines())
    units = _semantic_units("\n".join(body_lines))
    prefix = f"# {title}\n\n" if title else ""

    pieces: list[tuple[str, str]] = []
    for heading, text in units:
        if estimate_tokens(text) > max_tokens:
            pieces.extend((heading, p) for p in _hard_split(text, max_tokens, overlap_tokens))
        else:
            pieces.append((heading, text.strip()))

    merged: list[tuple[str, str]] = []
    for heading, text in pieces:
        if (
            merged
            and merged[-1][0] == heading
            and estimate_tokens(prefix + merged[-1][1] + "\n\n" + text) <= target_tokens
        ):
            merged[-1] = (heading, f"{merged[-1][1]}\n\n{text}".strip())
        else:
            merged.append((heading, text))

    chunks: list[Chunk] = []
    for i, (heading, text) in enumerate(merged):
        full = f"{prefix}{text}".strip()
        chunks.append(
            Chunk(
                index=i, text=full, heading=heading or title, token_estimate=estimate_tokens(full)
            )
        )
    return chunks
