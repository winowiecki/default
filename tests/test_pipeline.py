from pathlib import Path

from conftest import FakeDetector

from deident.config import load_config
from deident.keyfile import KeyManager
from deident.pipeline import process_file, register_config_terms


def _setup(project_dir):
    config = load_config(project_dir / "project.yaml")
    keymgr = KeyManager(project_dir / "deident_key.json")
    register_config_terms(keymgr, config)
    return config, keymgr


def test_pseudonyms_consistent_across_two_files(project_dir):
    _, keymgr = _setup(project_dir)
    out_dir = project_dir / "cleaned"
    results = [
        process_file(path, keymgr=keymgr, out_dir=out_dir, detector=None)
        for path in sorted((project_dir / "transcripts").iterdir())
    ]
    texts = {r.output_path.name: r.output_path.read_text() for r in results}
    txt = texts["synthetic_focus_group_deid.txt"]
    vtt = texts["synthetic_followup_deid.vtt"]

    # Same person -> same pseudonym in both files, including speaker labels.
    for cleaned in (txt, vtt):
        assert "Marisol" not in cleaned
        assert "Okafor" not in cleaned
        assert "Aurelia" not in cleaned
        assert "B4" not in cleaned
        assert "Participant 01" in cleaned
    assert txt.count("Participant 01") >= 2  # MARISOL: label + mentions
    assert "Participant 01" in vtt and "Participant 02" in vtt
    # Site aliases (St. Aurelia Hospital / St. Aurelia / SAH) share one label.
    assert "Site A" in txt and "Site A" in vtt
    assert "SAH" not in txt
    # VTT structure survives untouched.
    assert vtt.startswith("WEBVTT")
    assert "00:00:07.000 --> 00:00:14.250" in vtt


def test_possessive_and_regexes_in_full_file(project_dir):
    _, keymgr = _setup(project_dir)
    result = process_file(
        project_dir / "transcripts" / "synthetic_focus_group.txt",
        keymgr=keymgr,
        out_dir=project_dir / "cleaned",
        detector=None,
    )
    cleaned = result.output_path.read_text()
    assert "Participant 02's rounding schedule" in cleaned
    assert "Participant 01's shift" in cleaned
    assert "[PHONE]" in cleaned and "555-867-5309" not in cleaned
    # the whole address becomes [EMAIL] even though it contains a known name
    assert "at [PHONE] or [EMAIL]." in cleaned
    assert "tanner@example.com" not in cleaned
    assert "[DATE]" in cleaned and "January 14, 2025" not in cleaned
    assert "[AGE] years old" in cleaned
    assert "[ROOM]" in cleaned and "room 12B" not in cleaned
    assert "[ID]" in cleaned and "4482913" not in cleaned
    assert "[URL]" in cleaned
    assert "[REDACTED 1]" in cleaned and "Nightingale" not in cleaned


def test_originals_never_modified(project_dir):
    _, keymgr = _setup(project_dir)
    src = project_dir / "transcripts" / "synthetic_focus_group.txt"
    before = src.read_text()
    process_file(src, keymgr=keymgr, out_dir=project_dir / "cleaned", detector=None)
    assert src.read_text() == before


def test_llm_span_verified_and_applied(project_dir):
    _, keymgr = _setup(project_dir)
    # "Rosewood Clinic" is not in the config; pretend the model finds it.
    src = project_dir / "transcripts" / "extra.txt"
    src.write_text(
        "MODERATOR: Any transfers?\n"
        "SPEAKER: Yes, two went to Rosewood Clinic last week.\n"
    )
    detector = FakeDetector(
        if_present=[
            {"text": "Rosewood Clinic", "category": "site", "reason": "clinic name"}
        ]
    )
    result = process_file(
        src, keymgr=keymgr, out_dir=project_dir / "cleaned", detector=detector
    )
    cleaned = result.output_path.read_text()
    assert "Rosewood" not in cleaned
    # Sites A and B are taken by the config; the discovery becomes Site C.
    assert "Site C" in cleaned
    assert result.llm_auto_replacements == 1
    flags = [f for f in result.flags if f.auto_replaced]
    assert len(flags) == 1 and "Site C" in flags[0].status
    # Discovery persists in the key file for later files in the batch.
    assert keymgr.lookup("site", "Rosewood Clinic") == "Site C"
    # Verification pass came back clean (nothing left to find).
    assert result.needs_decision == 0


def test_fabricated_span_rejected_not_guessed(project_dir):
    _, keymgr = _setup(project_dir)
    src = project_dir / "transcripts" / "synthetic_focus_group.txt"
    detector = FakeDetector(
        always=[
            {"text": "Zebulon Frank", "category": "name", "reason": "hallucinated"}
        ]
    )
    result = process_file(
        src, keymgr=keymgr, out_dir=project_dir / "cleaned", detector=detector
    )
    cleaned = result.output_path.read_text()
    assert "Zebulon" not in cleaned  # never inserted or guessed at
    rejected = [f for f in result.flags if "not found verbatim" in f.status]
    assert rejected and rejected[0].text == "Zebulon Frank"
    assert not rejected[0].auto_replaced
    # The fabricated name never enters the key file.
    assert keymgr.lookup("name", "Zebulon Frank") is None


def test_other_category_needs_decision(project_dir):
    _, keymgr = _setup(project_dir)
    src = project_dir / "transcripts" / "extra.txt"
    src.write_text("SPEAKER: My cousin works the night shift too.\n")
    detector = FakeDetector(
        if_present=[
            {"text": "cousin", "category": "other", "reason": "family relation"}
        ]
    )
    result = process_file(
        src, keymgr=keymgr, out_dir=project_dir / "cleaned", detector=detector
    )
    assert "cousin" in result.output_path.read_text()  # not auto-replaced
    assert result.needs_decision >= 1
    flag = next(f for f in result.flags if f.text == "cousin")
    assert "NEEDS DECISION" in flag.status
    assert "night shift" in flag.context
