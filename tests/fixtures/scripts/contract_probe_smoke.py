"""Subprocess smoke for the contract_probe fixture plugin."""

from __future__ import annotations

import json
import os
import sys
from importlib.metadata import entry_points
from pathlib import Path

import colosseum as col
from colosseum.context import get_context


def _eps_for_group(group: str) -> list[object]:
    discovered = entry_points()
    select = getattr(discovered, "select", None)
    if select is not None:
        return list(select(group=group))
    get = getattr(discovered, "get", None)
    if get is not None:
        return list(get(group, []))
    return [ep for ep in discovered if getattr(ep, "group", None) == group]


def main() -> None:
    config = Path(os.environ["CONTRACT_PROBE_CONFIG"])
    col.config.load_config(str(config))

    ep_names = sorted(ep.name for ep in _eps_for_group("colosseum.plugins"))
    if "contract_probe" not in ep_names:
        raise SystemExit(f"contract_probe entry point missing; have={ep_names!r}")

    if col.contract_probe.ping() != "pong":
        raise SystemExit("ping() did not return pong")

    serial = col.contract_probe.arm_device(device_id=1)
    if serial != "PROBE-1":
        raise SystemExit(f"unexpected serial: {serial!r}")

    col.contract_probe.measure_token(key="token")
    row = get_context().db.get_measurement(
        "contract_probe",
        "measure_token",
        "token",
        row_index=0,
    )
    if row is None or row.value != "token-ok":
        raise SystemExit(f"measurement missing or wrong: {row!r}")

    payload = {
        "ep_names": ep_names,
        "serial": serial,
        "measurement": row.value,
    }
    # Marker line so parent can ignore logging noise on stdout.
    print("CONTRACT_PROBE_OK:" + json.dumps(payload))


if __name__ == "__main__":
    main()
    col.endex()
    sys.exit(0)
