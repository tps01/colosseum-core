"""Mini-Circuits RC / ZTRC mechanical switch (ASCII SCPI).

Manual: Prog_Manual-2-Switch — ``SET[switch]=[state]``, ``SETP=[states]``, ``SWPORT?``.
"""

from __future__ import annotations

from typing import Any

from colosseum_equipment.transports.base import Transport


class MiniCircuitsRcSwitch:
    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._transport = transport
        self._config = config
        if "path" in config:
            self.set_path(str(config["path"]))

    def _expect_ok(self, response: str, command: str) -> None:
        if response.strip() != "1":
            raise RuntimeError(f"Mini-Circuits command failed: {command!r} -> {response!r}")

    def set_switch(self, switch: str, state: int) -> None:
        letter = switch.strip().upper()[:1]
        cmd = f"SET{letter}={int(state)}"
        self._expect_ok(self._transport.query(cmd), cmd)

    def set_path(self, path: str) -> None:
        path = path.strip()
        if path.upper().startswith("SETP="):
            cmd = path if path.upper().startswith("SETP=") else f"SETP={path.split('=', 1)[1]}"
            self._expect_ok(self._transport.query(cmd), cmd)
            return
        for segment in path.split(";"):
            segment = segment.strip()
            if not segment or "=" not in segment:
                continue
            switch, _, value = segment.partition("=")
            self.set_switch(switch, int(value))

    def measure_path(self) -> str:
        return self._transport.query("SWPORT?").strip()

    def preset(self) -> None:
        self._transport.write("*RST")

    def close(self) -> None:
        self._transport.close()
