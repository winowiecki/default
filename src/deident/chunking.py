"""Chunk transcripts by speaker turns with overlap for LLM detection."""

from __future__ import annotations

import re

# "MODERATOR:", "Marisol Vega:", "[P3]:", "(Facilitator):" ...
SPEAKER_LINE = re.compile(r"^\s*[\[\(]?[A-Za-z][\w .'\-]{0,40}[\]\)]?\s*:")

DEFAULT_MAX_CHARS = 4000
DEFAULT_OVERLAP_TURNS = 2


def split_turns(text: str) -> list[str]:
    """Split into speaker turns; a new turn starts at each speaker label."""
    turns: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if SPEAKER_LINE.match(line) and current:
            turns.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        turns.append("\n".join(current))
    return [t for t in turns if t.strip()]


def make_chunks(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_turns: int = DEFAULT_OVERLAP_TURNS,
) -> list[str]:
    """Group turns into chunks of ~max_chars, repeating the last
    overlap_turns turns at the start of the next chunk so identifiers
    spanning a chunk boundary are seen in full at least once."""
    turns: list[str] = []
    for turn in split_turns(text):
        # A single enormous turn still has to fit in a chunk.
        while len(turn) > max_chars:
            turns.append(turn[:max_chars])
            turn = turn[max_chars:]
        turns.append(turn)

    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for turn in turns:
        if buf and size + len(turn) + 1 > max_chars:
            chunks.append("\n".join(buf))
            buf = buf[-overlap_turns:] if overlap_turns else []
            size = sum(len(t) + 1 for t in buf)
        buf.append(turn)
        size += len(turn) + 1
    if buf:
        chunks.append("\n".join(buf))
    return chunks
