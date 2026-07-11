"""Local Ollama detection client.

The model is used ONLY as a detector: it receives transcript chunks and
returns a JSON array of suspected identifier spans. It never produces
rewritten transcript text, and nothing it returns is trusted until Python
verifies the span exists verbatim in the transcript.
"""

from __future__ import annotations

import json
import re

import httpx

SPAN_CATEGORIES = {"name", "site", "unit", "role", "date", "location", "other"}

SYSTEM_PROMPT = """\
You are a de-identification screening assistant for qualitative research \
focus group transcripts. Read the transcript excerpt and find any remaining \
information that could identify a person, hospital, or place.

Respond with ONLY a JSON array. Each element must be an object:
  {"text": "<exact substring copied verbatim from the excerpt>",
   "category": "<one of: name, site, unit, role, date, location, other>",
   "reason": "<short explanation>"}

Rules:
- "text" MUST be copied character-for-character from the excerpt. Do not
  paraphrase, extend, trim words, or fix spelling.
- Do NOT rewrite, summarize, translate, or return any transcript text other
  than the flagged spans.
- Do NOT flag placeholder tokens that are already de-identified, such as
  [DATE], [PHONE], [EMAIL], [AGE], [ROOM], [MRN], [ID], [URL], [ROLE],
  [LOCATION], [REDACTED 1], Participant 01, Site A, or Unit 1.
- Flag: person names and nicknames, hospital/clinic/site names, unit or
  ward names, uniquely identifying job roles or titles, specific dates,
  and specific places (cities, neighborhoods, landmarks).
- If nothing needs flagging, return [].

Output the JSON array only — no prose, no markdown, no code fences.\
"""


class OllamaError(Exception):
    pass


class OllamaUnavailable(OllamaError):
    """Ollama is not running, unreachable, or the model is not pulled."""


def parse_spans(raw: str) -> list[dict[str, str]] | None:
    """Defensively parse model output into a span list; None on failure."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw).strip()
    data: object = None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                return None
        else:
            return None
    if isinstance(data, dict):
        for key in ("spans", "identifiers", "results", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            return [] if not data else None
    if not isinstance(data, list):
        return None
    spans: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        category = str(item.get("category", "other")).strip().lower()
        if category not in SPAN_CATEGORIES:
            category = "other"
        spans.append(
            {
                "text": text,
                "category": category,
                "reason": str(item.get("reason", "")).strip(),
            }
        )
    return spans


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        # trust_env=False: never route localhost traffic through a proxy.
        self._client = httpx.Client(
            base_url=self.base_url, timeout=timeout, trust_env=False
        )

    def ensure_available(self) -> None:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaUnavailable(
                f"Cannot reach Ollama at {self.base_url} ({exc}).\n"
                "Is the Ollama server running? Start it with `ollama serve`, "
                "or use `deident run --skip-llm` for the deterministic pass "
                "only."
            ) from exc
        models = {
            m.get("name", "") for m in response.json().get("models", [])
        }
        wanted = {self.model, f"{self.model}:latest"}
        if not wanted & models:
            available = ", ".join(sorted(models)) or "(none)"
            raise OllamaUnavailable(
                f"Model '{self.model}' is not pulled in Ollama.\n"
                f"Run `ollama pull {self.model}`.\n"
                f"Models currently available: {available}"
            )

    def detect_spans(self, chunk: str) -> list[dict[str, str]] | None:
        """Return verified-parseable spans, or None if the model produced
        malformed JSON twice (caller logs the chunk for human review)."""
        for _attempt in range(2):
            try:
                content = self._chat(chunk)
            except httpx.HTTPError as exc:
                raise OllamaError(f"Ollama request failed: {exc}") from exc
            spans = parse_spans(content)
            if spans is not None:
                return spans
        return None

    def _chat(self, chunk: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk},
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
        response = self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")
