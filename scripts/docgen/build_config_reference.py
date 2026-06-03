#!/usr/bin/env python3
"""Generate bench TOML config reference RST from plugin ConfigSectionSpec."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from colosseum.plugins.loader import ensure_plugins_loaded
from colosseum.plugins.registry import PluginRegistry
from colosseum_equipment.transports.factory import default_driver_for_kind


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _kind_from_section(dotted_path: str) -> str | None:
    if not dotted_path.startswith("equipment."):
        return None
    return dotted_path.split(".", 1)[1]


def _default_driver_for_section(dotted_path: str) -> str:
    if dotted_path == "shared.ssh":
        return "ssh"
    kind = _kind_from_section(dotted_path)
    if kind is None:
        return "—"
    return default_driver_for_kind(kind)


def _format_keys(keys: tuple[str, ...]) -> str:
    if not keys:
        return "*(none)*"
    return ", ".join(f"``{key}``" for key in keys)


def build_config_reference_rst(*, output_path: Path) -> Path:
    registry = PluginRegistry()
    ensure_plugins_loaded(registry)
    specs = sorted(registry.config_section_specs(), key=lambda spec: spec.dotted_path)

    lines = [
        "Bench configuration reference",
        "=============================",
        "",
        "Generated from plugin ``ConfigSectionSpec`` registration. Re-run "
        "``python scripts/docgen/build_all.py`` after changing required or optional keys.",
        "",
        "Defaults",
        "--------",
        "",
        "- Lab hardware: omit ``driver`` on ``equipment.*`` sections (default **visa**, PyVISA + SCPI).",
        "- ``equipment.serial``: omit ``driver`` (default **serial**).",
        "- ``shared.ssh``: omit ``driver`` (default **ssh**).",
        "- Offline CI / smoke: ``driver = \"sim\"`` (see ``examples/configs/bench.sim.toml``).",
        "- PyVISA-sim: ``visa_backend = \"sim\"`` and ``sim_definition`` (see ``examples/configs/bench.rf.visa-sim.toml``).",
        "- Multiple VISA runtimes: optional ``visa_library`` (PyVISA ``ResourceManager`` argument); see :doc:`platform_notes`.",
        "",
    ]

    for spec in specs:
        title = spec.dotted_path.replace(".", " ").title()
        lines.extend(
            [
                title,
                "-" * len(title),
                "",
                f":ID field: ``{spec.id_field}``",
                "",
                f":Default driver: ``{_default_driver_for_section(spec.dotted_path)}`` (when ``driver`` is omitted)",
                "",
                ".. list-table::",
                "   :header-rows: 1",
                "   :widths: 28 72",
                "",
                "   * - Key class",
                "     - Keys",
                "   * - Required",
                f"     - {_format_keys(spec.required_keys)}",
                "   * - Optional",
                f"     - {_format_keys(spec.optional_keys)}",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate bench config reference RST")
    parser.add_argument(
        "--output",
        type=Path,
        help="Default: build/docgen/config_reference.rst",
    )
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    output = args.output or (repo_root / "build" / "docgen" / "config_reference.rst")
    path = build_config_reference_rst(output_path=output)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
