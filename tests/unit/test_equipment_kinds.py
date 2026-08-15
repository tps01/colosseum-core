from __future__ import annotations

import pytest

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
        "rtsa",
    ],
)
def test_build_generic_kind_closes(kind: str) -> None:
    transport = NullTransport()
    instrument = build_instrument(kind, 1, {"model": "generic"}, transport)
    instrument.close()

