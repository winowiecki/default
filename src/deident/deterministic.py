"""Deterministic replacement pass: known terms and regex patterns."""

from __future__ import annotations

import re
from collections import Counter

_TITLE_WORDS = {"dr", "dr.", "doctor"}


def compile_term_pattern(term: str) -> re.Pattern[str]:
    """Case-insensitive pattern for a term.

    Handles possessives ("Sarah's"), flexible whitespace inside multi-word
    terms, optional trailing periods on abbreviations ("St." vs "St"), and
    "Dr." / "Doctor" title interchangeability.
    """
    parts: list[str] = []
    for word in term.split():
        lower = word.lower()
        if lower in _TITLE_WORDS:
            parts.append(r"(?:Dr\.?|Doctor)")
        elif word.endswith(".") and len(word) > 1:
            parts.append(re.escape(word[:-1]) + r"\.?")
        else:
            parts.append(re.escape(word))
    body = r"\s+".join(parts)
    return re.compile(
        rf"(?<!\w)(?:{body})(?P<poss>['’]s)?(?!\w)", re.IGNORECASE
    )


def replace_terms(text: str, terms: list[tuple[str, str]]) -> tuple[str, int]:
    """Replace every (alias, label) pair; longest aliases win first.

    Possessives are preserved: "Marisol's" -> "Participant 01's".
    Returns (new_text, replacement_count).
    """
    total = 0
    for alias, label in sorted(terms, key=lambda t: -len(t[0])):
        pattern = compile_term_pattern(alias)

        def repl(m: re.Match[str], label: str = label) -> str:
            return label + (m.group("poss") or "")

        text, n = pattern.subn(repl, text)
        total += n
    return text, total


_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)"
)

# Order matters: URLs and emails first (they contain digits/dots that other
# rules could partially eat), then phones before numeric dates.
REGEX_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("url", re.compile(r"\b(?:https?://|www\.)[^\s<>\"]+", re.IGNORECASE), "[URL]"),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "[EMAIL]"),
    (
        "phone",
        re.compile(
            r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\d)"
        ),
        "[PHONE]",
    ),
    (
        "date",
        re.compile(
            rf"\b{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b",
            re.IGNORECASE,
        ),
        "[DATE]",
    ),
    (
        "date",
        re.compile(
            rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\b(?:,?\s+\d{{4}})?",
            re.IGNORECASE,
        ),
        "[DATE]",
    ),
    ("date", re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"), "[DATE]"),
    ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "[DATE]"),
    (
        "age",
        re.compile(
            r"\b\d{1,3}(?:[\s\-]+years?[\s\-]old|\s+years\s+of\s+age)\b",
            re.IGNORECASE,
        ),
        "[AGE] years old",
    ),
    (
        "room",
        re.compile(r"\b(?:room|rm\.?|bed)\s*#?\s*\d+[A-Za-z]?\b", re.IGNORECASE),
        "[ROOM]",
    ),
    (
        "mrn",
        re.compile(
            r"\b(?:MRN|medical record(?:\s+number)?)[\s:#]*\d{4,}\b", re.IGNORECASE
        ),
        "[MRN]",
    ),
    # Standalone 6-10 digit strings (badge numbers, MRNs without a label).
    # A sentence-ending period is fine; a decimal point / version dot is not.
    ("id", re.compile(r"(?<![\w.\-/:])\d{6,10}(?![\w\-/:])(?!\.\d)"), "[ID]"),
]


def apply_regexes(text: str) -> tuple[str, Counter[str]]:
    counts: Counter[str] = Counter()
    for name, pattern, replacement in REGEX_RULES:
        text, n = pattern.subn(replacement, text)
        if n:
            counts[name] += n
    return text, counts
