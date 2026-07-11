"""Project configuration (project.yaml) loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

DEFAULT_MODEL = "qwen2.5:14b-instruct"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

_ALLOWED_KEYS = {
    "known_names",
    "known_sites",
    "known_units",
    "custom_terms",
    "ollama_model",
    "ollama_url",
}

EXAMPLE_YAML = """\
# deident project configuration
# ==============================
# List every identifier you already know about. Matching is
# case-insensitive and automatically also catches:
#   - possessives            ("Sarah's" -> "Participant 01's")
#   - "Dr." / "Doctor" title variants ("Dr. Smith" matches "Doctor Smith")
#
# An entry can be a single string, or a list of strings when several
# spellings / nicknames refer to the SAME person, site, or unit — every
# alias in the list shares one pseudonym.

known_names:
  - [Marisol Vega, Marisol, Mari]   # one person, three spellings
  - Dr. Okafor
  - Tanner Hollis

known_sites:
  - [St. Aurelia Hospital, St. Aurelia, SAH]
  - Brookfield Campus

known_units:
  - B4
  - SICU
  - vICU

# Any other project-specific strings that must always be replaced
# (program names, internal committee names, etc.):
custom_terms:
  - Project Nightingale

# Local Ollama model used for the detection pass. The model only FLAGS
# suspected identifiers as JSON — it never rewrites transcript text.
ollama_model: qwen2.5:14b-instruct

# Ollama server URL. Must be localhost — the tool refuses anything else.
ollama_url: http://localhost:11434
"""


class ConfigError(Exception):
    """Raised for a missing, malformed, or unsafe project.yaml."""


@dataclass
class TermGroup:
    """One real-world entity plus all of its aliases (canonical first)."""

    canonical: str
    aliases: list[str]


@dataclass
class Config:
    known_names: list[TermGroup] = field(default_factory=list)
    known_sites: list[TermGroup] = field(default_factory=list)
    known_units: list[TermGroup] = field(default_factory=list)
    custom_terms: list[TermGroup] = field(default_factory=list)
    ollama_model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL


def _parse_groups(raw: object, key: str) -> list[TermGroup]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError(f"'{key}' must be a list")
    groups: list[TermGroup] = []
    for item in raw:
        if isinstance(item, str):
            aliases = [item.strip()]
        elif isinstance(item, list):
            aliases = [str(a).strip() for a in item if str(a).strip()]
        else:
            raise ConfigError(
                f"each entry in '{key}' must be a string or a list of alias "
                f"strings, got: {item!r}"
            )
        aliases = [a for a in aliases if a]
        if aliases:
            groups.append(TermGroup(canonical=aliases[0], aliases=aliases))
    return groups


def load_config(path: Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"config file not found: {path}\n"
            "Run `deident init` to create an example project.yaml."
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse {path}: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping")

    unknown = set(data) - _ALLOWED_KEYS
    if unknown:
        raise ConfigError(
            f"unknown key(s) in {path}: {', '.join(sorted(unknown))}\n"
            f"allowed keys: {', '.join(sorted(_ALLOWED_KEYS))}"
        )

    cfg = Config(
        known_names=_parse_groups(data.get("known_names"), "known_names"),
        known_sites=_parse_groups(data.get("known_sites"), "known_sites"),
        known_units=_parse_groups(data.get("known_units"), "known_units"),
        custom_terms=_parse_groups(data.get("custom_terms"), "custom_terms"),
        ollama_model=str(data.get("ollama_model") or DEFAULT_MODEL),
        ollama_url=str(data.get("ollama_url") or DEFAULT_OLLAMA_URL),
    )

    host = urlparse(cfg.ollama_url).hostname
    if host not in _LOCAL_HOSTS:
        raise ConfigError(
            f"ollama_url points at '{host}', which is not localhost. "
            "This tool never sends transcript text off this machine; "
            "only a local Ollama server is allowed."
        )
    return cfg
