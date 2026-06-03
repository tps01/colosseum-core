"""PyVISA-sim transport (requires Python 3.10+ and .[test] extra)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.visa_sim,
    pytest.mark.skipif(sys.version_info < (3, 10), reason="pyvisa-sim requires Python 3.10+"),
]

REPO = Path(__file__).resolve().parents[2]
PSU_YAML = REPO / "tests" / "fixtures" / "pyvisa_sim" / "generic_psu.yaml"


@pytest.fixture
def visa_sim_transport(isolated_cwd):
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.transports.visa import VISATransport

    transport = VISATransport(
        "GPIB::1::INSTR",
        timeout=5.0,
        visa_backend="sim",
        sim_definition=str(PSU_YAML.relative_to(REPO)).replace("\\", "/"),
    )
    yield transport
    transport.close()


def test_idn_query(visa_sim_transport) -> None:
    response = visa_sim_transport.query("*IDN?")
    assert "Generic PSU" in response


def test_voltage_set_and_query(visa_sim_transport) -> None:
    visa_sim_transport.write("VOLT 5.0")
    assert float(visa_sim_transport.query("VOLT?")) == pytest.approx(5.0)
