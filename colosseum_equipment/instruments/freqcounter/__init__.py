from __future__ import annotations

from colosseum_equipment.instruments.registry import register, register_aliases

from .generic import GenericFreqCounter
from .keysight_53220a import Keysight53220AFreqCounter
from .tek_fca3000 import TekFca3000FreqCounter


def register_instruments() -> None:
    register_aliases(
        "freqcounter",
        ("keysight-53220a", "keysight-53230a"),
        lambda transport, config: Keysight53220AFreqCounter(transport, config),
    )
    register_aliases(
        "freqcounter",
        ("tektronix-fca3000", "tektronix-fca3100", "tektronix-mca3000"),
        lambda transport, config: TekFca3000FreqCounter(transport, config),
    )
    register(
        "freqcounter", "generic", lambda transport, config: GenericFreqCounter(transport, config)
    )
