"""Sphinx-style docstring fragments for ``col.equipment`` APIs."""

from __future__ import annotations

from colosseum.docstrings import ParamSpec
from colosseum.docstrings import sphinx_param as _sphinx_param


def _equipment_raises() -> str:
    return (
        ":raises EquipmentConnectionError: Transport or instrument connection failed.\n"
        ":raises EquipmentCapabilityError: Operation not supported by the configured model."
    )


def _key_param(domain: str = "equipment") -> str:
    return _sphinx_param(
        "key",
        "str",
        f"Unique measurement key within domain ``{domain}`` and this command name. "
        "Must not collide with another instrument's measurement using the same command name.",
    )


def equipment_id_param(param: str, kind: str, *, type_name: str = "int") -> str:
    return _sphinx_param(
        param,
        type_name,
        f"Configured ``equipment.{kind}`` id from bench TOML.",
    )


def _format_params(
    id_param: str,
    kind: str,
    extra_params: list[ParamSpec],
    *,
    include_key: bool = False,
    key_domain: str = "equipment",
) -> str:
    blocks = [equipment_id_param(id_param, kind)]
    blocks.extend(_sphinx_param(n, t, d) for n, t, d in extra_params)
    if include_key:
        blocks.append(_key_param(key_domain))
    return "\n".join(blocks)


def command_doc(
    summary: str,
    *,
    id_param: str,
    kind: str,
    extra_params: list[ParamSpec] | None = None,
    returns: str = "None",
    rtype: str | None = None,
) -> str:
    params = _format_params(id_param, kind, extra_params or [])
    rtype_line = f"\n:rtype: {rtype}" if rtype else ""
    return (
        f"{summary}\n\n{params}\n\n:returns: {returns}{rtype_line}\n\n{_equipment_raises()}"
    )


def measurement_doc(
    summary: str,
    *,
    id_param: str,
    kind: str,
    quantity: str,
    extra_params: list[ParamSpec] | None = None,
    rtype: str = "float",
) -> str:
    params = _format_params(
        id_param, kind, extra_params or [], include_key=True, key_domain="equipment"
    )
    return (
        f"{summary}\n\n{params}\n\n:returns: Measured {quantity}.\n"
        f":rtype: {rtype}\n\n{_equipment_raises()}"
    )


def tolerance_verify_doc(measure_command: str, *, unit: str = "") -> str:
    unit_note = f" in {unit}" if unit else ""
    expected_desc = "Expected numeric value in the same units as the measurement."
    tolerance_desc = "Maximum allowed absolute deviation from ``expected_val``."
    optional_desc = "When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``."
    return (
        f"Compare a prior ``{measure_command}`` measurement to an expected value{unit_note}.\n\n"
        f"{_key_param('equipment')}\n"
        f"{_sphinx_param('expected_val', 'float', expected_desc)}\n"
        f"{_sphinx_param('tolerance', 'float', tolerance_desc)}\n"
        f"{_sphinx_param('optional', 'bool', optional_desc, optional=True)}\n\n"
        ":returns: VerificationResult with PASS, FAIL, or ERROR status.\n"
        ":rtype: VerificationResult"
    )
