from __future__ import annotations

from pathlib import Path

from colosseum_equipment.exceptions import EquipmentConnectionError, EquipmentTimeoutError
from colosseum_equipment.transports.base import Transport


def _find_repo_root() -> Path | None:
    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "pyproject.toml").is_file() and (package_root / "colosseum").is_dir():
        return package_root
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "colosseum").is_dir():
            return directory
    return None


def resolve_sim_definition(path: str) -> Path:
    """Resolve a bench ``sim_definition`` path to an existing YAML file."""
    candidate = Path(path)
    if candidate.is_file():
        return candidate.resolve()
    for base in (Path.cwd(), _find_repo_root() or Path()):
        if base == Path():
            continue
        resolved = (base / candidate).resolve()
        if resolved.is_file():
            return resolved
    raise EquipmentConnectionError(f"PyVISA-sim definition file not found: {path}")


class VISATransport(Transport):
    def __init__(
        self,
        resource: str,
        timeout: float = 5.0,
        *,
        visa_backend: str | None = None,
        sim_definition: str | None = None,
    ) -> None:
        try:
            import pyvisa
        except ImportError as exc:  # pragma: no cover
            raise EquipmentConnectionError(
                "pyvisa is required for driver=visa. Reinstall colosseum."
            ) from exc

        self._timeout = timeout
        backend = (visa_backend or "").lower()
        try:
            if backend == "sim":
                if not sim_definition:
                    raise EquipmentConnectionError("visa_backend=sim requires `sim_definition` in bench config")
                sim_path = resolve_sim_definition(sim_definition)
                self._rm = pyvisa.ResourceManager(f"{sim_path}@sim")
            else:
                self._rm = pyvisa.ResourceManager()
            if backend == "sim":
                self._inst = self._rm.open_resource(
                    resource,
                    read_termination="\n",
                    write_termination="\n",
                )
            else:
                self._inst = self._rm.open_resource(resource)
            self._inst.timeout = int(timeout * 1000)
        except EquipmentConnectionError:
            raise
        except Exception as exc:
            raise EquipmentConnectionError(f"Failed to open VISA resource `{resource}`: {exc}") from exc

    def write(self, data: str) -> None:
        try:
            self._inst.write(data)
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def read(self) -> str:
        try:
            return str(self._inst.read())
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def query(self, data: str) -> str:
        try:
            return str(self._inst.query(data))
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def write_raw(self, data: bytes) -> None:
        try:
            self._inst.write_raw(data)
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def read_raw(self, size: int = 655360) -> bytes:
        try:
            return bytes(self._inst.read_raw(size))
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def close(self) -> None:
        try:
            self._inst.close()
        except Exception:
            pass
        try:
            self._rm.close()
        except Exception:
            pass
