# deident

Local transcript de-identification CLI for qualitative research. Prepares
focus group transcripts for AI-assisted analysis by scrubbing identifiers
**before** any transcript content touches a cloud service.

Everything runs on your machine. The only network traffic is to a local
Ollama server at `http://localhost:11434` (the tool refuses any other host),
and even that is optional (`--skip-llm`). No telemetry, ever.

## The core safety principle

**The LLM never generates or rewrites transcript text.** The pipeline is:

1. **Deterministic pass** — Python replaces every config-listed term
   (case-insensitive, possessives, "Dr."/"Doctor" variants) and
   regex-matchable identifiers (phones, emails, dates, ages, room/bed
   numbers, MRN-like numbers, URLs).
2. **LLM detection pass** — the local model reads the transcript in
   overlapping speaker-turn chunks and returns *only* a JSON list of
   suspected residual identifier spans (exact string, category, reason).
3. **Deterministic application** — Python verifies each proposed span exists
   **verbatim** in the text before replacing it. Spans that don't match are
   logged for human review, never guessed at.
4. **Verification pass** — the detector runs again on the cleaned output;
   anything still flagged lands in the review report for your decision.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync            # install dependencies into .venv
uv run deident --help
```

You'll also need [Ollama](https://ollama.com) running locally with a model
pulled (unless you only use `--skip-llm`):

```bash
ollama pull qwen2.5:14b-instruct
```

## Usage

```bash
uv run deident init                       # writes an example project.yaml
# edit project.yaml: known_names, known_sites, known_units, custom_terms
uv run deident run transcripts/           # full pipeline on a folder
uv run deident run --skip-llm session1.vtt  # deterministic pass only
uv run deident status                     # key-file counts (safe to screen-share)
```

Inputs: `.txt`, `.vtt`, `.docx` (single file or folder). Originals are never
modified. Outputs per run (in the current directory, or `--out DIR`):

- `cleaned/` — de-identified transcripts, `<name>_deid.<ext>` (`.docx` is
  emitted as `.txt`; `.vtt` timestamps and structure are preserved).
- `deident_key.json` — the original → pseudonym crosswalk. **Keep this
  file local and back it up**; it is what keeps "Participant 03" meaning
  the same person across every file and every re-run. The tool warns
  loudly if it disappears between runs.
- `review_report.md` — every flagged span with 3 lines of context, its
  category, whether it was auto-replaced or needs your decision, and
  per-file counts. Read it before uploading anything anywhere.

## Pseudonym scheme

| Category | Replacement |
|---|---|
| people (config or LLM-found) | `Participant 01`, `Participant 02`, … |
| sites | `Site A`, `Site B`, … |
| units | `Unit 1`, `Unit 2`, … |
| custom terms | `[REDACTED 1]`, … |
| regex hits | `[PHONE]` `[EMAIL]` `[DATE]` `[AGE]` `[ROOM]` `[MRN]` `[ID]` `[URL]` |
| LLM-found dates/roles/locations | `[DATE]` `[ROLE]` `[LOCATION]` |

LLM-flagged spans in category `other`, spans that don't match verbatim, and
chunks the model failed to analyze are **never** auto-replaced — they go to
`review_report.md` for you.

## Tests

```bash
uv run pytest
```

All tests run offline against synthetic transcripts with invented names;
Ollama is mocked.
