from deident.keyfile import KeyManager, _letters


def test_letters_sequence():
    assert _letters(1) == "A"
    assert _letters(26) == "Z"
    assert _letters(27) == "AA"
    assert _letters(28) == "AB"


def test_aliases_share_one_pseudonym(tmp_path):
    km = KeyManager(tmp_path / "key.json")
    label = km.get_or_assign("name", "Marisol Vega", ["Marisol", "Mari"])
    assert label == "Participant 01"
    assert km.lookup("name", "mari") == "Participant 01"
    assert km.lookup("name", "MARISOL") == "Participant 01"
    # possessives normalize to the same entry
    assert km.lookup("name", "Marisol's") == "Participant 01"


def test_categories_use_distinct_label_schemes(tmp_path):
    km = KeyManager(tmp_path / "key.json")
    assert km.get_or_assign("name", "Marisol Vega") == "Participant 01"
    assert km.get_or_assign("site", "St. Aurelia Hospital") == "Site A"
    assert km.get_or_assign("site", "Brookfield Campus") == "Site B"
    assert km.get_or_assign("unit", "B4") == "Unit 1"
    assert km.get_or_assign("custom", "Project Nightingale") == "[REDACTED 1]"


def test_persistence_across_reload(tmp_path):
    key_path = tmp_path / "key.json"
    km = KeyManager(key_path)
    assert km.get_or_assign("name", "Marisol Vega") == "Participant 01"
    assert km.get_or_assign("name", "Tanner Hollis") == "Participant 02"
    km.save()

    km2 = KeyManager(key_path)
    # existing mappings are stable, counters continue where they left off
    assert km2.get_or_assign("name", "Marisol Vega") == "Participant 01"
    assert km2.get_or_assign("name", "New Person") == "Participant 03"


def test_summary_counts_only(tmp_path):
    km = KeyManager(tmp_path / "key.json")
    km.get_or_assign("name", "Marisol Vega", ["Marisol"])
    km.get_or_assign("site", "St. Aurelia Hospital")
    assert km.summary() == {"name": 1, "site": 1, "unit": 0, "custom": 0}
