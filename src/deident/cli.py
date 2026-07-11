"""deident command-line interface.

Commands:
  deident init                     write an example project.yaml
  deident run <file-or-folder>     full pipeline (add --skip-llm to run
                                   the deterministic pass only)
  deident status                   key file summary (counts only)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import EXAMPLE_YAML, ConfigError, load_config
from .keyfile import KeyManager
from .llm import OllamaClient, OllamaError, OllamaUnavailable
from .pipeline import process_file, register_config_terms
from .readers import SUPPORTED_EXTENSIONS
from .report import write_report

KEY_FILENAME = "deident_key.json"
CLEANED_DIRNAME = "cleaned"
REPORT_FILENAME = "review_report.md"


def _err(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def cmd_init(args: argparse.Namespace) -> int:
    target = Path("project.yaml")
    if target.exists() and not args.force:
        _err(f"{target} already exists (use --force to overwrite)")
        return 1
    target.write_text(EXAMPLE_YAML, encoding="utf-8")
    print(f"Wrote example config to {target}")
    print("Edit the known_names / known_sites / known_units lists, then run:")
    print("  deident run <transcript-file-or-folder>")
    return 0


def _collect_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        files = sorted(
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        return files
    raise FileNotFoundError(f"no such file or directory: {path}")


def _warn_missing_key(key_path: Path, cleaned_dir: Path) -> None:
    if key_path.exists():
        return
    if cleaned_dir.is_dir() and any(cleaned_dir.iterdir()):
        banner = "!" * 70
        print(banner, file=sys.stderr)
        print(
            f"WARNING: previous cleaned output exists in {cleaned_dir}/ but\n"
            f"the key file ({key_path}) was NOT found.\n"
            "Pseudonyms assigned in this run will NOT match earlier runs.\n"
            "If you moved or deleted the key file, restore it before "
            "continuing.",
            file=sys.stderr,
        )
        print(banner, file=sys.stderr)


def cmd_run(args: argparse.Namespace) -> int:
    try:
        config = load_config(Path(args.config))
    except ConfigError as exc:
        _err(str(exc))
        return 2

    try:
        inputs = _collect_inputs(Path(args.path))
    except FileNotFoundError as exc:
        _err(str(exc))
        return 2
    if not inputs:
        _err(
            f"no transcript files (.txt, .vtt, .docx) found in {args.path}"
        )
        return 2

    base = Path(args.out)
    key_path = base / KEY_FILENAME
    cleaned_dir = base / CLEANED_DIRNAME
    report_path = base / REPORT_FILENAME
    _warn_missing_key(key_path, cleaned_dir)

    detector = None
    if not args.skip_llm:
        detector = OllamaClient(config.ollama_url, config.ollama_model)
        try:
            detector.ensure_available()
        except OllamaUnavailable as exc:
            _err(str(exc))
            return 2
        print(
            f"Ollama OK: {config.ollama_model} at {config.ollama_url}"
        )
    else:
        print("Running deterministic pass only (--skip-llm).")

    keymgr = KeyManager(key_path)
    register_config_terms(keymgr, config)

    results = []
    started = time.monotonic()
    for i, path in enumerate(inputs, start=1):
        print(f"[{i}/{len(inputs)}] {path}")
        try:
            result = process_file(
                path,
                keymgr=keymgr,
                out_dir=cleaned_dir,
                detector=detector,
                log=print,
            )
        except (OllamaError, ValueError, OSError) as exc:
            _err(f"{path}: {exc}")
            keymgr.save()
            return 1
        keymgr.save()  # crash-safe: persist mappings after every file
        results.append(result)
        print(f"    -> {result.output_path} ({result.seconds:.1f}s)")

    needs_decision = write_report(report_path, results, args.skip_llm)
    elapsed = time.monotonic() - started
    counts = keymgr.summary()

    print()
    print(f"Done: {len(results)} file(s) in {elapsed:.1f}s")
    print(
        f"  key file:      {key_path} "
        f"(names: {counts['name']}, sites: {counts['site']}, "
        f"units: {counts['unit']}, custom: {counts['custom']})"
    )
    print(f"  cleaned files: {cleaned_dir}/")
    print(
        f"  review report: {report_path} "
        f"({needs_decision} item(s) need your decision)"
    )
    if needs_decision:
        print(
            "\nReview the report before sharing any cleaned transcript "
            "with a cloud service."
        )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    key_path = Path(args.out) / KEY_FILENAME
    if not key_path.exists():
        print(f"No key file found at {key_path} — nothing mapped yet.")
        return 1
    keymgr = KeyManager(key_path)
    counts = keymgr.summary()
    print(f"Key file: {key_path}")
    print(f"  created: {keymgr.data.get('created', 'unknown')}")
    print(f"  updated: {keymgr.data.get('updated', 'unknown')}")
    print(f"  names mapped:  {counts['name']}")
    print(f"  sites mapped:  {counts['site']}")
    print(f"  units mapped:  {counts['unit']}")
    print(f"  custom terms:  {counts['custom']}")
    print("(counts only — no identifying mappings are shown)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deident",
        description="Local transcript de-identification for qualitative "
        "research. Runs fully offline except a local Ollama server.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init", help="write an example project.yaml to the current directory"
    )
    p_init.add_argument(
        "--force", action="store_true", help="overwrite an existing file"
    )
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser(
        "run", help="de-identify a transcript file or a folder of transcripts"
    )
    p_run.add_argument("path", help="a .txt/.vtt/.docx file, or a folder")
    p_run.add_argument(
        "--config",
        default="project.yaml",
        help="project config file (default: ./project.yaml)",
    )
    p_run.add_argument(
        "--skip-llm",
        action="store_true",
        help="deterministic pass only; do not call Ollama",
    )
    p_run.add_argument(
        "--out",
        default=".",
        help="base directory for cleaned/, deident_key.json, and "
        "review_report.md (default: current directory)",
    )
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser(
        "status",
        help="show key file summary counts (safe to screen-share)",
    )
    p_status.add_argument(
        "--out",
        default=".",
        help="base directory containing deident_key.json (default: .)",
    )
    p_status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
