"""Reading transcripts and format-aware text transformation.

Originals are only ever opened for reading. For .vtt files, structural
lines (WEBVTT header, cue timings, cue numbers, NOTE/STYLE blocks) are
protected: they are never altered and never sent to the LLM, so timestamp
digits can't be mangled by the regex pass or flagged as dates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

SUPPORTED_EXTENSIONS = {".txt", ".vtt", ".docx"}


def transcript_format(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported file type '{ext}' ({path.name}); "
            "supported: .txt, .vtt, .docx"
        )
    return ext.lstrip(".")


def read_transcript(path: Path) -> str:
    fmt = transcript_format(path)
    if fmt in ("txt", "vtt"):
        return path.read_text(encoding="utf-8-sig", errors="replace")
    import docx  # imported lazily; only needed for .docx inputs

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def output_name(path: Path) -> str:
    """cleaned filename: same base + _deid; .docx is emitted as .txt."""
    ext = path.suffix.lower()
    if ext == ".docx":
        ext = ".txt"
    return f"{path.stem}_deid{ext}"


def is_vtt_protected_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if "-->" in s:
        return True
    if s.upper().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
        return True
    if s.isdigit():  # cue sequence numbers
        return True
    return False


def transform_text(text: str, fmt: str, fn: Callable[[str], str]) -> str:
    """Apply fn to the transcript content, leaving VTT structure untouched."""
    if fmt != "vtt":
        return fn(text)
    return "\n".join(
        line if is_vtt_protected_line(line) else fn(line)
        for line in text.split("\n")
    )


def content_text(text: str, fmt: str) -> str:
    """The spoken content only — what the LLM is allowed to read."""
    if fmt != "vtt":
        return text
    return "\n".join(
        line for line in text.split("\n") if not is_vtt_protected_line(line)
    )
