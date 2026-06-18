from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .anritsu_541xx import Anritsu541xxVna
from .generic import GenericVna
from .rohde_znb import RohdeZnbVna
from .tek_ttr500 import TekTtr500Vna


def register_instruments() -> None:
    register("vna", "tektronix-ttr500", lambda transport, config: TekTtr500Vna(transport, config))
    register("vna", "rohde-znb", lambda transport, config: RohdeZnbVna(transport, config))
    register("vna", "anritsu-541xx", lambda transport, config: Anritsu541xxVna(transport, config))
    register("vna", "generic", lambda transport, config: GenericVna(transport, config))
