from __future__ import annotations

from typing import Any, Dict

from colosseum.context import get_context

from colosseum_equipment.transports.base import Transport


def _state_map() -> Dict[str, Dict[str, Any]]:
    ctx = get_context()
    key = "sim:state"
    if key not in ctx.resource_cache:
        ctx.resource_cache[key] = {}
    return ctx.resource_cache[key]


class SimTransport(Transport):
    """In-memory transport for offline tests and CI (driver=sim)."""

    def __init__(self, kind: str, equipment_id: int, config: dict) -> None:
        self.kind = kind
        self.equipment_id = equipment_id
        self.config = config
        states = _state_map()
        run_key = f"{kind}:{equipment_id}"
        if run_key not in states:
            states[run_key] = {
                "voltage": float(config.get("voltage", 3.3)),
                "current_limit": float(config.get("ocp", config.get("current", 1.0))),
                "output_enabled": False,
            }
        self._state = states[run_key]

    def write(self, data: str) -> None:
        cmd = data.strip().upper()
        if cmd.startswith("VOLT"):
            parts = cmd.split()
            if len(parts) >= 2:
                self._state["voltage"] = float(parts[-1])
        elif cmd.startswith("CURR"):
            parts = cmd.split()
            if len(parts) >= 2:
                self._state["current_limit"] = float(parts[-1])
        elif cmd in ("OUTP ON", "OUTP 1", "OUTP:STAT ON"):
            self._state["output_enabled"] = True
        elif cmd in ("OUTP OFF", "OUTP 0", "OUTP:STAT OFF"):
            self._state["output_enabled"] = False

    def read(self) -> str:
        return self.query("")

    def query(self, data: str) -> str:
        cmd = data.strip().upper()
        voltage = self._read_voltage()
        if cmd in ("VOLT?", "MEAS:VOLT?"):
            return f"{voltage:.6f}"
        if cmd in ("CURR?", "MEAS:CURR?"):
            return f"{self._state['current_limit']:.6f}"
        if cmd in ("READ?", "MEAS?", "MEAS:VOLT:DC?"):
            return f"{voltage:.6E}"
        if cmd.startswith("CONF"):
            return ""
        return "0"

    def _read_voltage(self) -> float:
        if self.kind == "dmm":
            psu_state = _state_map().get("psu:1")
            if psu_state is not None:
                return float(psu_state["voltage"])
        return float(self._state["voltage"])

    def close(self) -> None:
        return None
