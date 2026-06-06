"""Sphinx-style docstring helpers for ``col.host`` APIs."""

from __future__ import annotations

from colosseum_equipment.api._docstrings import ParamSpec, _sphinx_param

_KEY_PARAM = _sphinx_param(
    "key",
    "str",
    "Unique measurement key within domain ``host``.",
)


def host_measurement_doc(
    summary: str,
    *,
    quantity: str,
    extra_params: list[ParamSpec] | None = None,
    rtype: str = "float",
) -> str:
    blocks = [_KEY_PARAM]
    blocks.extend(_sphinx_param(n, t, d) for n, t, d in extra_params or [])
    params = "\n".join(blocks)
    return f"{summary}\n\n{params}\n\n:returns: {quantity}.\n:rtype: {rtype}"
