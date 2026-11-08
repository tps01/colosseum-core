"""Public API for ``col.contract_probe`` (fixture plugin)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

_callbacks = []


def shutdown():
    _callbacks.append("shutdown")


def report(output, result, ctx):
    import json

    assert _callbacks == ["shutdown"]
    assert not ctx.db.is_initialized()
    assert len(result.measurements) == result.measurement_count == 5
    assert [row.row_index for row in result.measurements] == [0, 4, 1, 4, 0]
    assert result.measurements[-1].value == 42
    assert result.overall == "PASS"
    assert json.loads((output / "summary.json").read_text())["measurement_count"] == 5
    _callbacks.append("report")
    print("CONTRACT_PROBE_REPORT_OK")


@command
def ping() -> str:
    """Return a fixed token so e2e can assert namespace attachment."""
    return "pong"


@command
def arm_device(*, device_id: int) -> str:
    """Read a configured device row and return its serial."""
    from colosseum.config.loader import ConfigError
    from colosseum.context import get_context

    ctx = get_context()
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded.")
    row = ctx.config.require_item("contract_probe.device", device_id)
    return str(row["serial"])


@measurement
def measure_token(*, key: str) -> str:
    """Record a simple measurement for evidence-domain checks."""
    from importlib.resources import files

    return files("colosseum_contract_probe").joinpath("token.txt").read_text().strip()


def record_series() -> list[int]:
    """Record legacy-style rows directly, without decorator duplicate/scoring rules."""
    from colosseum.context import get_context
    from colosseum.database import MeasurementRow

    db = get_context().db
    ids = [
        db.insert_measurement(
            MeasurementRow(
                domain="contract_probe",
                command="series",
                key="legacy",
                row_index=index,
                value=value,
                status=status,
            )
        )
        for index, value, status in [
            (4, {"sample": 1}, "PASS"),
            (1, None, "ERROR"),
            (4, [2, 3], "PASS"),
        ]
    ]
    return ids
