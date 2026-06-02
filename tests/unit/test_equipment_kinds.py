from __future__ import annotations

import pytest

from colosseum_equipment.exceptions import EquipmentCapabilityError
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.transports.null_transport import NullTransport

@pytest.mark.parametrize(
    "kind",
    [
        "attn",
        "pwrmeter",
        "rfswitch",
        "oscope",
        "eload",
        "freqcounter",
        "vna",
        "sdr",
    ],
)
def test_build_generic_kind_closes(kind: str) -> None:
    transport = NullTransport()
    instrument = build_instrument(kind, 1, {"model": "generic"}, transport)
    instrument.close()


def test_sdr_set_frequency_raises_capability() -> None:
    instrument = build_instrument("sdr", 1, {"model": "generic"}, NullTransport())
    with pytest.raises(EquipmentCapabilityError):
        instrument.set_center_frequency(1e9)
    instrument.close()

