"""Relaxed TOML parsing for config and suite files."""

from __future__ import annotations

import pytest

from colosseum.config.toml_relaxed import loads_relaxed, prepare_toml_text


def test_bare_words_become_strings() -> None:
    raw = loads_relaxed(
        """
[equipment.speca]
speca_id = 1
visa_backend = sim
model = keysight-e4407b
resource = GPIB::18::INSTR
"""
    )
    item = raw["equipment"]["speca"]
    assert item["visa_backend"] == "sim"
    assert item["model"] == "keysight-e4407b"
    assert item["resource"] == "GPIB::18::INSTR"


def test_booleans_and_numbers_unchanged() -> None:
    raw = loads_relaxed(
        """
[equipment.psu]
psu_id = 1
driver = sim
output = false
voltage = 3.3
timeout = 5
"""
    )
    item = raw["equipment"]["psu"]
    assert item["driver"] == "sim"
    assert item["output"] is False
    assert item["voltage"] == pytest.approx(3.3)
    assert item["timeout"] == 5


def test_quoted_values_preserved() -> None:
    raw = loads_relaxed('model = "already-quoted"\n')
    assert raw["model"] == "already-quoted"


def test_bool_spellings_become_bools() -> None:
    raw = loads_relaxed(
        """
[colosseum.reports]
wats = True
junit = F
custom = yes
other = "no"
label = "yes"
"""
    )
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
