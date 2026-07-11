"""Persistent pseudonym crosswalk (deident_key.json).

The key file is the ONLY place original identifiers are stored next to
their replacements. It must never leave the machine.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ("name", "site", "unit", "custom")

_POSSESSIVE_RE = re.compile(r"['’]s$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _letters(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA ..."""
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def _label_for(category: str, n: int) -> str:
    if category == "name":
        return f"Participant {n:02d}"
    if category == "site":
        return f"Site {_letters(n)}"
    if category == "unit":
        return f"Unit {n}"
    return f"[REDACTED {n}]"


def normalize_term(term: str) -> str:
    """Strip a trailing possessive and surrounding whitespace."""
    return _POSSESSIVE_RE.sub("", term.strip())


class KeyManager:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {
                "version": 1,
                "created": _now(),
                "updated": _now(),
                "categories": {
                    c: {"counter": 0, "entries": {}} for c in CATEGORIES
                },
            }
        # (category, alias.lower()) -> canonical
        self._index: dict[tuple[str, str], str] = {}
        for cat, bucket in self.data["categories"].items():
            for canonical, entry in bucket["entries"].items():
                for alias in entry["aliases"]:
                    self._index[(cat, alias.lower())] = canonical

    def lookup(self, category: str, term: str) -> str | None:
        canonical = self._index.get((category, normalize_term(term).lower()))
        if canonical is None:
            return None
        return self.data["categories"][category]["entries"][canonical]["label"]

    def get_or_assign(
        self,
        category: str,
        term: str,
        aliases: list[str] | None = None,
        source: str = "config",
    ) -> str:
        if category not in CATEGORIES:
            raise ValueError(f"unknown key category: {category}")
        term = normalize_term(term)
        all_aliases = [term] + [normalize_term(a) for a in (aliases or [])]
        all_aliases = [a for a in dict.fromkeys(all_aliases) if a]
        bucket = self.data["categories"][category]

        # If any alias is already known, merge the rest into that entry.
        for alias in all_aliases:
            canonical = self._index.get((category, alias.lower()))
            if canonical is not None:
                entry = bucket["entries"][canonical]
                known = {a.lower() for a in entry["aliases"]}
                for a in all_aliases:
                    if a.lower() not in known:
                        entry["aliases"].append(a)
                        self._index[(category, a.lower())] = canonical
                return entry["label"]

        bucket["counter"] += 1
        label = _label_for(category, bucket["counter"])
        bucket["entries"][term] = {
            "label": label,
            "aliases": all_aliases,
            "source": source,
        }
        for alias in all_aliases:
            self._index[(category, alias.lower())] = term
        return label

    def all_terms(self) -> list[tuple[str, str]]:
        """Every (alias, label) pair across all categories."""
        pairs: list[tuple[str, str]] = []
        for bucket in self.data["categories"].values():
            for entry in bucket["entries"].values():
                for alias in entry["aliases"]:
                    pairs.append((alias, entry["label"]))
        return pairs

    def summary(self) -> dict[str, int]:
        return {
            cat: len(bucket["entries"])
            for cat, bucket in self.data["categories"].items()
        }

    def save(self) -> None:
        self.data["updated"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
