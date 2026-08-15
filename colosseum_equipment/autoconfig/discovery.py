"""VISA scan, probe, classify, and bench config construction for autoconfig."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from colosseum.config.loader import ConfigError
from colosseum_shared.network import IPv4NetworkBinding

from .idn_registry import KIND_SECTIONS, classify_idn
from .network_filter import BlockedSubnet, filter_resources, resolve_blacklist
from .sort import sort_resources


@dataclass(frozen=True)
class AutoconfigAssignment:
    """One autoconfigured instrument row."""

    section: str
    item_id: int
    kind: str
    resource: str
    model: str
    idn: str


@dataclass(frozen=True)
class AutoconfigSkip:
    """A resource that was not added to generated config."""

    resource: str
    reason: str
    idn: str | None = None


@dataclass
class AutoconfigResult:
    """Outcome of VISA autoconfig discovery."""

    raw: dict[str, Any]
    scanned_count: int
    assignments: list[AutoconfigAssignment] = field(default_factory=list)
    blacklisted: list[tuple[str, BlockedSubnet]] = field(default_factory=list)
    skipped: list[AutoconfigSkip] = field(default_factory=list)
    blacklist_subnets: list[BlockedSubnet] = field(default_factory=list)
    unresolved_blacklist: list[str] = field(default_factory=list)


def _probe_idn(
    rm: object,
    resource: str,
    *,
    timeout: float,
) -> str:
    inst = rm.open_resource(resource)  # type: ignore[attr-defined]
    try:
        inst.timeout = int(timeout * 1000)
        return str(inst.query("*IDN?")).strip()
    finally:
        inst.close()


def _build_raw_config(assignments: Sequence[AutoconfigAssignment]) -> dict[str, Any]:
    raw: dict[str, Any] = {"equipment": {}}
    equipment = raw["equipment"]
    for assignment in assignments:
        section_name = assignment.section.split(".", 1)[1]
        id_field = KIND_SECTIONS[assignment.kind][1]
        row = {
            id_field: assignment.item_id,
            "resource": assignment.resource,
            "model": assignment.model,
        }
        existing = equipment.get(section_name)
        if existing is None:
            equipment[section_name] = [row]
        elif isinstance(existing, list):
            existing.append(row)
        else:
            equipment[section_name] = [existing, row]
    return raw


def discover_equipment_config(
    *,
    timeout: float = 5.0,
    visa_library: str | None = None,
    blacklist: str | Sequence[str] | None = None,
    network_bindings: Sequence[IPv4NetworkBinding] | None = None,
    resource_manager: object | None = None,
) -> AutoconfigResult:
    """Scan VISA resources and build a normalized-ready raw equipment config dict."""
    try:
        import pyvisa
    except ImportError as exc:
        raise ConfigError(
            "pyvisa is required for col.equipment.autoconfig(). "
            "Install with: pip install colosseum-equipment[hardware]"
        ) from exc

    blacklist_resolution = resolve_blacklist(blacklist, bindings=network_bindings)
    blocked = list(blacklist_resolution.blocked)

    if resource_manager is None:
        rm: object = (
            pyvisa.ResourceManager(visa_library) if visa_library else pyvisa.ResourceManager()
        )
    else:
        rm = resource_manager

    try:
        resources = list(rm.list_resources("?*INSTR"))  # type: ignore[attr-defined]
    except Exception as exc:
        raise ConfigError(f"VISA resource scan failed: {exc}") from exc

    scanned_count = len(resources)
    if not resources:
        raise ConfigError("no VISA INSTR resources found")

    allowed, blacklisted = filter_resources(resources, blocked)
    if not allowed:
        raise ConfigError("no VISA INSTR resources found")

    sorted_resources = sort_resources(allowed)
    assignments: list[AutoconfigAssignment] = []
    skipped: list[AutoconfigSkip] = []
    seen_resources: set[str] = set()
    next_id: dict[str, int] = {}

    for resource in sorted_resources:
        if resource in seen_resources:
            skipped.append(AutoconfigSkip(resource=resource, reason="duplicate_resource"))
            continue
        seen_resources.add(resource)

        try:
            idn = _probe_idn(rm, resource, timeout=timeout)
        except Exception as exc:
            skipped.append(AutoconfigSkip(resource=resource, reason=f"probe_failed: {exc}"))
            continue

        match = classify_idn(idn)
        if match is None:
            skipped.append(AutoconfigSkip(resource=resource, reason="no_kind_match", idn=idn))
            continue

        section, id_field = KIND_SECTIONS[match.kind]
        item_id = next_id.get(match.kind, 0) + 1
        next_id[match.kind] = item_id
        assignments.append(
            AutoconfigAssignment(
                section=section,
                item_id=item_id,
                kind=match.kind,
                resource=resource,
                model=match.model,
                idn=idn,
            )
        )

    if not assignments:
        summary = ", ".join(f"{skip.resource} ({skip.reason})" for skip in skipped)
        raise ConfigError(f"no classifiable VISA INSTR resources found; skipped: {summary}")

    raw = _build_raw_config(assignments)
    return AutoconfigResult(
        raw=raw,
        scanned_count=scanned_count,
        assignments=assignments,
        blacklisted=blacklisted,
        skipped=skipped,
        blacklist_subnets=list(blocked),
        unresolved_blacklist=list(blacklist_resolution.unresolved_entries),
    )
