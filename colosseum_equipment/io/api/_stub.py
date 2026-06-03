from __future__ import annotations

from colosseum_equipment.io.exceptions import IoNotImplementedError


def require_driver(driver: str | None, operation: str, *, vendor_doc: str) -> None:
    if driver in (None, "", "stub"):
        raise IoNotImplementedError(
            f"col.io {operation} requires driver documentation ({vendor_doc}); "
            f"configure driver= in bench TOML once implemented."
        )
    if driver in ("ni-6501", "ni-845x"):
        raise IoNotImplementedError(
            f"col.io {operation}: driver `{driver}` is reserved; provide NI programming "
            f"documentation to implement ({vendor_doc})."
        )
    raise IoNotImplementedError(f"col.io {operation}: unsupported driver `{driver}`")
