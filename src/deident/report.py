"""Review report (review_report.md) generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .pipeline import FileResult


def write_report(
    path: Path, results: list[FileResult], skip_llm: bool
) -> int:
    """Write the markdown review report; returns the number of items that
    need a human decision."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "deterministic only (--skip-llm)" if skip_llm else "full pipeline"
    needs_decision = sum(r.needs_decision for r in results)

    lines: list[str] = [
        "# De-identification review report",
        "",
        f"- Run: {now}",
        f"- Mode: {mode}",
        f"- Files processed: {len(results)}",
        f"- Items needing your decision: **{needs_decision}**",
        "",
        "## Per-file summary",
        "",
        "| File | Term replacements | Pattern replacements "
        "| LLM auto-replaced | Needs decision | Chunk failures |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.input_path.name} | {r.term_replacements} "
            f"| {r.regex_replacements} | {r.llm_auto_replacements} "
            f"| {r.needs_decision} | {r.llm_chunk_failures} |"
        )
    lines.append("")

    for r in results:
        if not r.flags:
            continue
        lines.append(f"## {r.input_path.name}")
        lines.append("")
        for flag in r.flags:
            lines.append(
                f"### `{flag.text}` — {flag.category} ({flag.phase} pass)"
            )
            lines.append("")
            lines.append(f"- **Status:** {flag.status}")
            if flag.reason:
                lines.append(f"- **Model reasoning:** {flag.reason}")
            if flag.context:
                lines.append("- **Context:**")
                lines.append("")
                lines.append("  ```text")
                for ctx_line in flag.context.splitlines():
                    lines.append(f"  {ctx_line}")
                lines.append("  ```")
            lines.append("")

    if not any(r.flags for r in results):
        lines.append("_No spans were flagged for review._")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return needs_decision
