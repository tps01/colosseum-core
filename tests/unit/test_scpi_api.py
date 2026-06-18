"""SCPI helper API: instrument id resolution and command dispatch."""

from __future__ import annotations

import pytest

from colosseum_equipment.api import scpi


def test_resolve_kind_requires_exactly_one_id() -> None:
    with pytest.raises(ValueError, match="Specify exactly one"):
        scpi._resolve_kind()
    with pytest.raises(ValueError, match="Specify exactly one"):
        scpi._resolve_kind(psu_id=1, dmm_id=2)


def test_resolve_kind_maps_psu_id() -> None:
    kind, equipment_id = scpi._resolve_kind(psu_id=3)
    assert kind == "psu"
    assert equipment_id == 3


def test_scpi_api_functions_expose_instrument_signature() -> None:
    params = list(scpi.write.__signature__.parameters)
    assert params[0] == "command"
    assert "psu_id" in params
    assert "vna_id" in params
    assert "rtsa_id" in params
