"""Relaxed TOML parsing for config and suite files."""

from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

import pytest

from colosseum.config.toml_relaxed import loads_relaxed, prepare_toml_text


def test_bare_words_become_strings() -> None:
    raw = loads_relaxed("""
[equipment.speca]
speca_id = 1
visa_backend = sim
model = keysight-e4407b
resource = GPIB::18::INSTR
""")
    item = raw["equipment"]["speca"]
    assert item["visa_backend"] == "sim"
    assert item["model"] == "keysight-e4407b"
    assert item["resource"] == "GPIB::18::INSTR"


def test_booleans_and_numbers_unchanged() -> None:
    raw = loads_relaxed("""
[equipment.psu]
psu_id = 1
driver = sim
output = false
voltage = 3.3
timeout = 5
""")
    item = raw["equipment"]["psu"]
    assert item["driver"] == "sim"
    assert item["output"] is False
    assert item["voltage"] == pytest.approx(3.3)
    assert item["timeout"] == 5


def test_quoted_values_preserved() -> None:
    raw = loads_relaxed('model = "already-quoted"\n')
    assert raw["model"] == "already-quoted"


def test_bool_spellings_become_bools() -> None:
    raw = loads_relaxed("""
[colosseum.reports]
wats = True
junit = F
custom = yes
other = "no"
label = "yes"
""")
    reports = raw["colosseum"]["reports"]
    # Bare spellings become TOML bools; quoted strings stay strings.
    assert reports == {
        "wats": True,
        "junit": False,
        "custom": True,
        "other": "no",
        "label": "yes",
    }


def test_numeric_ids_stay_integers() -> None:
    raw = loads_relaxed("psu_id = 1\nchannel = 0\n")
    assert raw["psu_id"] == 1
    assert raw["channel"] == 0
    assert isinstance(raw["psu_id"], int)


def test_prepare_quotes_bare_word_only() -> None:
    prepared = prepare_toml_text("model = keysight-esg\noutput = false\n")
    assert 'model = "keysight-esg"' in prepared
    assert "output = false" in prepared


def test_multiline_string_body_not_rewritten() -> None:
    snippet = '''
notes = """
status = pending
ready = yes
"""
'''
    expected = tomllib.loads(snippet)
    assert loads_relaxed(snippet) == expected
    assert "status = pending" in expected["notes"]
    assert "ready = yes" in expected["notes"]


def test_multiline_literal_string_body_not_rewritten() -> None:
    snippet = """
notes = '''
status = pending
ready = yes
'''
"""
    expected = tomllib.loads(snippet)
    assert loads_relaxed(snippet) == expected


@pytest.mark.parametrize("note", ['\'"""\'', "\"'''\"", '"escaped \\" # quote"'])
def test_delimiters_in_ordinary_strings_do_not_hide_following_values(note) -> None:
    assert loads_relaxed(f"note = {note}\nflag = yes\n")["flag"] is True


def test_fuzz_seed_invariants():
    from pathlib import Path

    from tests.fuzz.toml_relaxed import check_input

    for seed in (Path(__file__).parents[1] / "fuzz/corpus").iterdir():
        check_input(seed.read_bytes())


@pytest.mark.parametrize("separator", ["\x85", "\u2028", "\u2029"])
def test_unicode_line_separator_inside_quoted_string_is_preserved(separator):
    text = f'value = "a{separator}b"\n'
    assert loads_relaxed(text) == {"value": f"a{separator}b"}


@pytest.mark.parametrize("token", ["inf", "+inf", "-inf", "nan", "+nan", "-nan"])
def test_special_float_literals_remain_numbers(token):
    import math

    result = loads_relaxed(f"value = {token}\n")["value"]
    assert isinstance(result, float)
    expected = float(token)
    assert math.isnan(result) if math.isnan(expected) else result == expected


@pytest.mark.parametrize("data", [bytes([value]) for value in range(20)])
def test_fuzz_incremental_generated_shapes(data):
    from tests.fuzz.toml_relaxed import check_input

    check_input(data)
