"""Per-file de-identification pipeline.

Order of operations (the LLM never rewrites text — it only points):
  1. Deterministic pass: known terms from the key file + regex patterns.
  2. LLM detection: chunks in, JSON span list out.
  3. Deterministic application: each span is verified to exist verbatim
     before Python applies the replacement; anything else is logged for
     human review, never guessed at.
  4. Verification pass: LLM detection re-runs on the cleaned text; leftovers
     go to the review report.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .chunking import make_chunks
from .deterministic import apply_regexes, compile_term_pattern, replace_terms
from .keyfile import KeyManager, normalize_term
from .readers import (
    content_text,
    output_name,
    read_transcript,
    transcript_format,
    transform_text,
)

# LLM-flagged categories applied automatically once verified verbatim.
# name/site/unit get persistent pseudonyms from the key file so they stay
# consistent across every file in the project.
_STATIC_TOKENS = {"date": "[DATE]", "role": "[ROLE]", "location": "[LOCATION]"}
_KEYED_CATEGORIES = {"name", "site", "unit"}

# Spans that are already replacement tokens — the model was told not to
# flag these, but defend anyway.
_PLACEHOLDER_RE = re.compile(
    r"^\[(?:DATE|PHONE|EMAIL|AGE|ROOM|MRN|ID|URL|ROLE|LOCATION"
    r"|REDACTED(?:\s+\d+)?)\]$"
    r"|^(?:participant|site|unit)\s+\w{1,4}$",
    re.IGNORECASE,
)

# A "span" longer than this is almost certainly the model dumping or
# rewriting transcript text rather than pointing at an identifier.
_MAX_SPAN_CHARS = 120


@dataclass
class Flag:
    """One review-report entry."""

    file: str
    phase: str  # "detection" | "verification"
    category: str
    text: str
    reason: str
    status: str
    auto_replaced: bool
    context: str = ""


@dataclass
class FileResult:
    input_path: Path
    output_path: Path
    fmt: str
    term_replacements: int = 0
    regex_replacements: int = 0
    llm_auto_replacements: int = 0
    llm_chunk_failures: int = 0
    flags: list[Flag] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def needs_decision(self) -> int:
        return sum(1 for f in self.flags if not f.auto_replaced)


class Detector(Protocol):
    def detect_spans(self, chunk: str) -> list[dict[str, str]] | None: ...


def register_config_terms(keymgr: KeyManager, config) -> None:
    """Seed the key file with every config-listed term group."""
    for category, groups in (
        ("name", config.known_names),
        ("site", config.known_sites),
        ("unit", config.known_units),
        ("custom", config.custom_terms),
    ):
        for group in groups:
            keymgr.get_or_assign(
                category, group.canonical, group.aliases[1:], source="config"
            )


def _context_around(text: str, span: str) -> str:
    """The flagged line plus one line either side (3 lines of context)."""
    idx = text.find(span)
    if idx < 0:
        return ""
    line_no = text[:idx].count("\n")
    lines = text.split("\n")
    return "\n".join(lines[max(0, line_no - 1) : line_no + 2])


def _dedupe_spans(
    spans: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for span in spans:
        key = (span["text"], span["category"])
        if key not in seen:
            seen.add(key)
            unique.append(span)
    # Longest spans first so overlapping shorter spans don't break them.
    unique.sort(key=lambda s: -len(s["text"]))
    return unique


def _run_detection(
    detector: Detector,
    text: str,
    fmt: str,
    result: FileResult,
    phase: str,
) -> list[dict[str, str]]:
    """Detect spans over all chunks; malformed chunks become review flags."""
    collected: list[dict[str, str]] = []
    chunks = make_chunks(content_text(text, fmt))
    for i, chunk in enumerate(chunks, start=1):
        spans = detector.detect_spans(chunk)
        if spans is None:
            result.llm_chunk_failures += 1
            result.flags.append(
                Flag(
                    file=result.input_path.name,
                    phase=phase,
                    category="error",
                    text=f"(chunk {i} of {len(chunks)})",
                    reason="model returned malformed JSON twice; "
                    "chunk was not analyzed",
                    status="NEEDS DECISION — review this section manually",
                    auto_replaced=False,
                    context="\n".join(chunk.splitlines()[:3]),
                )
            )
            continue
        collected.extend(spans)
    return _dedupe_spans(collected)


def process_file(
    path: Path,
    *,
    keymgr: KeyManager,
    out_dir: Path,
    detector: Detector | None = None,
    log: Callable[[str], None] = lambda _msg: None,
) -> FileResult:
    """De-identify one transcript. Never writes to the input path."""
    started = time.monotonic()
    fmt = transcript_format(path)
    text = read_transcript(path)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_name(path)
    if out_path.resolve() == path.resolve():
        raise ValueError(f"refusing to overwrite the original file: {path}")

    result = FileResult(input_path=path, output_path=out_path, fmt=fmt)

    # 1. Deterministic pass. Regex patterns run first so structured tokens
    #    (emails, URLs, phones) are replaced whole even when they contain a
    #    known name (e.g. tanner@example.com); then all known terms
    #    (config + previously LLM-discovered, via the key file).
    text = transform_text(text, fmt, lambda t: _apply_rules(t, result))
    terms = keymgr.all_terms()
    text = transform_text(
        text, fmt, lambda t: _apply_terms(t, terms, result)
    )
    log(
        f"    deterministic: {result.term_replacements} term + "
        f"{result.regex_replacements} pattern replacements"
    )

    if detector is not None:
        # 2. LLM detection pass.
        spans = _run_detection(detector, text, fmt, result, phase="detection")
        log(f"    llm detection: {len(spans)} unique span(s) flagged")

        # 3. Deterministic, verified application.
        for span in spans:
            text = _apply_span(span, text, fmt, keymgr, result)

        # 4. Verification pass on the cleaned text.
        leftovers = _run_detection(
            detector, text, fmt, result, phase="verification"
        )
        for span in leftovers:
            if _PLACEHOLDER_RE.match(span["text"]):
                continue
            result.flags.append(
                Flag(
                    file=path.name,
                    phase="verification",
                    category=span["category"],
                    text=span["text"],
                    reason=span["reason"],
                    status="NEEDS DECISION — still flagged after cleaning",
                    auto_replaced=False,
                    context=_context_around(content_text(text, fmt), span["text"]),
                )
            )
        log(
            "    verification: clean"
            if not leftovers
            else f"    verification: {len(leftovers)} span(s) still flagged"
        )

    out_path.write_text(text, encoding="utf-8")
    result.seconds = time.monotonic() - started
    return result


def _apply_terms(
    text: str, terms: list[tuple[str, str]], result: FileResult
) -> str:
    text, n = replace_terms(text, terms)
    result.term_replacements += n
    return text


def _apply_rules(text: str, result: FileResult) -> str:
    text, counts = apply_regexes(text)
    result.regex_replacements += sum(counts.values())
    return text


def _apply_span(
    span: dict[str, str],
    text: str,
    fmt: str,
    keymgr: KeyManager,
    result: FileResult,
) -> str:
    """Verify a proposed span verbatim, then apply it deterministically."""
    span_text = span["text"]
    category = span["category"]
    file_name = result.input_path.name

    if _PLACEHOLDER_RE.match(span_text):
        return text  # model flagged an existing placeholder; ignore

    if len(span_text) > _MAX_SPAN_CHARS:
        result.flags.append(
            Flag(
                file=file_name,
                phase="detection",
                category=category,
                text=span_text[:200],
                reason=span["reason"],
                status="NOT APPLIED — span too long to be an identifier "
                "(model may have returned rewritten text); review manually",
                auto_replaced=False,
            )
        )
        return text

    searchable = content_text(text, fmt)
    if span_text not in searchable:
        result.flags.append(
            Flag(
                file=file_name,
                phase="detection",
                category=category,
                text=span_text,
                reason=span["reason"],
                status="NOT APPLIED — span not found verbatim in transcript; "
                "review manually",
                auto_replaced=False,
            )
        )
        return text

    context = _context_around(searchable, span_text)

    if category in _KEYED_CATEGORIES:
        label = keymgr.get_or_assign(
            category, normalize_term(span_text), source="llm"
        )
    elif category in _STATIC_TOKENS:
        label = _STATIC_TOKENS[category]
    else:
        result.flags.append(
            Flag(
                file=file_name,
                phase="detection",
                category=category,
                text=span_text,
                reason=span["reason"],
                status=f"NEEDS DECISION — category '{category}' is not "
                "auto-replaced",
                auto_replaced=False,
                context=context,
            )
        )
        return text

    pattern = compile_term_pattern(span_text)
    new_text = transform_text(
        text,
        fmt,
        lambda t: pattern.sub(
            lambda m: label + (m.group("poss") or ""), t
        ),
    )
    result.llm_auto_replacements += 1
    result.flags.append(
        Flag(
            file=file_name,
            phase="detection",
            category=category,
            text=span_text,
            reason=span["reason"],
            status=f"AUTO-REPLACED with '{label}'",
            auto_replaced=True,
            context=context,
        )
    )
    return new_text
