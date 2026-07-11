import shutil
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"

CONFIG_YAML = """\
known_names:
  - [Marisol Vega, Marisol]
  - Dr. Okafor
  - [Tanner Hollis, Tanner]
known_sites:
  - [St. Aurelia Hospital, St. Aurelia, SAH]
  - Brookfield Campus
known_units:
  - B4
custom_terms:
  - Project Nightingale
ollama_model: test-model
"""


class FakeDetector:
    """Stands in for OllamaClient in tests. Returns `always` spans on every
    call plus any `if_present` spans whose text occurs in the chunk (so the
    verification pass naturally comes back clean once text is replaced)."""

    def __init__(self, always=None, if_present=None):
        self.always = always or []
        self.if_present = if_present or []
        self.calls = 0

    def ensure_available(self):
        pass

    def detect_spans(self, chunk):
        self.calls += 1
        spans = list(self.always)
        spans += [s for s in self.if_present if s["text"] in chunk]
        return spans


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """A working directory with project.yaml and a transcripts/ folder
    containing the two synthetic transcripts."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "project.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    for name in ("synthetic_focus_group.txt", "synthetic_followup.vtt"):
        shutil.copy(DATA_DIR / name, transcripts / name)
    return tmp_path
