from deident.deterministic import apply_regexes, replace_terms
from deident.readers import transform_text


def test_simple_term_case_insensitive():
    text, n = replace_terms("MARISOL: I saw marisol today.", [("Marisol", "Participant 01")])
    assert text == "Participant 01: I saw Participant 01 today."
    assert n == 2


def test_possessive_preserved():
    text, n = replace_terms("Marisol's badge", [("Marisol", "Participant 01")])
    assert text == "Participant 01's badge"
    assert n == 1


def test_curly_apostrophe_possessive():
    text, _ = replace_terms("Marisol’s badge", [("Marisol", "Participant 01")])
    assert text == "Participant 01’s badge"


def test_doctor_title_variants():
    terms = [("Dr. Okafor", "Participant 02")]
    for variant in ("Dr. Okafor", "Dr Okafor", "Doctor Okafor", "doctor okafor"):
        text, n = replace_terms(f"Ask {variant} about it.", terms)
        assert text == "Ask Participant 02 about it.", variant
        assert n == 1


def test_no_partial_word_match():
    text, n = replace_terms("The B4X protocol and AB4 form.", [("B4", "Unit 1")])
    assert n == 0
    assert "Unit 1" not in text


def test_abbreviation_trailing_period_optional():
    terms = [("St. Aurelia", "Site A")]
    text, n = replace_terms("At St Aurelia and St. Aurelia today.", terms)
    assert text == "At Site A and Site A today."
    assert n == 2


def test_longest_alias_wins():
    terms = [("Marisol", "Participant 01"), ("Marisol Vega", "Participant 01")]
    text, _ = replace_terms("Marisol Vega spoke.", terms)
    assert text == "Participant 01 spoke."


def test_regex_phone():
    text, _ = apply_regexes("Call 555-867-5309 or (312) 555-0142 now.")
    assert text == "Call [PHONE] or [PHONE] now."


def test_regex_email():
    text, _ = apply_regexes("Write to tanner@example.com please.")
    assert text == "Write to [EMAIL] please."


def test_regex_dates():
    text, _ = apply_regexes("On January 14, 2025 and 3/14/2025 and 2025-03-14.")
    assert text == "On [DATE] and [DATE] and [DATE]."
    text, _ = apply_regexes("We met on February 2nd near the lobby.")
    assert text == "We met on [DATE] near the lobby."
    text, _ = apply_regexes("It was the 3rd of March, 2024.")
    assert text == "It was the [DATE]."


def test_regex_age():
    text, _ = apply_regexes("I'm 47 years old, for the record.")
    assert text == "I'm [AGE] years old, for the record."


def test_regex_room_and_bed():
    text, _ = apply_regexes("Moved to room 12B, then bed 4.")
    assert text == "Moved to [ROOM], then [ROOM]."


def test_regex_mrn_and_id():
    text, _ = apply_regexes("MRN: 8231457 and badge 4482913.")
    assert text == "[MRN] and badge [ID]."


def test_regex_url():
    text, _ = apply_regexes("See https://intranet.example.org/notes today.")
    assert text == "See [URL] today."


def test_vtt_timestamps_protected():
    vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:06.500\nCall 555-867-5309.\n"
    out = transform_text(vtt, "vtt", lambda t: apply_regexes(t)[0])
    assert "00:00:01.000 --> 00:00:06.500" in out
    assert "[PHONE]" in out
    assert out.startswith("WEBVTT\n\n1\n")
