"""Subprocess smoke for the contract_probe fixture plugin."""

from __future__ import annotations

import json
import os
import sys
from contextlib import closing
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
    get_context().enabled_reports = frozenset({"contract_probe"})

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

    ids = col.contract_probe.record_series()
    db = get_context().db
    rows = db.list_measurements("contract_probe", "series", "legacy")
    assert [item.id for item in rows] == ids
    assert [item.row_index for item in rows] == [4, 1, 4]
    assert [item.value for item in rows] == [{"sample": 1}, None, [2, 3]]
    assert db.get_measurement("contract_probe", "series", "legacy", 4).id == ids[-1]
    assert [item.id for item in db.fetch_all_measurements()] == [row.id, *ids]
    # Independent SQL writers retain their own commit responsibility.
    import sqlite3

    with closing(sqlite3.connect(get_context().output_dir / "execution.sqlite")) as connection:
        connection.execute(
            "INSERT INTO measurements(domain,command,key,row_index,value_json,status,timestamp) "
            "VALUES ('contract_probe','series','legacy',0,'42','PASS','2026-01-01T00:00:00+00:00')",
        )
        connection.commit()
    assert db.list_measurements("contract_probe", "series", "legacy")[-1].value == 42
    assert get_context().result_aggregator.overall_pass()

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
