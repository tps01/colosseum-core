#!/usr/bin/env python3
"""Generate end-user API RST (commands, measurements, verifications only)."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable, Iterable
from pathlib import Path
from types import ModuleType

from _bootstrap import bootstrap

bootstrap()

from colosseum.decorators.command import COLOSSEUM_DECORATOR  # noqa: E402

_ROLE_LABELS = {
    "command": "Command",
    "measurement": "Measurement",
    "verification": "Verification",
}

_SCAN_TARGETS: list[tuple[str, str, list[str]]] = [
    (
        "col.equipment",
        "colosseum_equipment.api",
        [
            "asg",
            "attn",
            "dmm",
            "eload",
            "freqcounter",
            "oscope",
            "psu",
            "pwrmeter",
            "rfswitch",
            "rtsa",
            "scpi",
            "speca",
            "vna",
            "vsg",
        ],
    ),
    ("col.io", "colosseum_equipment.io.api", ["dio"]),
    (
        "col.shared",
        "colosseum_shared",
        [
            "ssh.api",
            "regex.api",
            "parsing.text",
        ],
    ),
    ("col.host", "colosseum_host.api", ["system", "bench", "config"]),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _decorated_entries(module: ModuleType) -> list[tuple[str, str, Callable[..., object]]]:
    entries: list[tuple[str, str, Callable[..., object]]] = []
    for name, obj in inspect.getmembers(module):
        if not inspect.isfunction(obj):
            continue
        if name.startswith("_"):
            continue
        role = getattr(obj, COLOSSEUM_DECORATOR, None)
        if role not in _ROLE_LABELS:
            continue
        entries.append((name, role, obj))
    entries.sort(key=lambda item: (item[1], item[0]))
    return entries


def _load_module(dotted: str) -> ModuleType:
    return importlib.import_module(dotted)


def _namespace_path(root: str, submodule: str) -> str:
    if root == "col.shared":
        if submodule == "ssh.api":
            return "col.shared.ssh"
        if submodule == "regex.api":
            return "col.shared.regex"
        if submodule == "parsing.text":
            return "col.shared.parsing"
    return f"{root}.{submodule.replace('.api', '')}"


def _format_signature(func: Callable[..., object]) -> str:
    try:
        return str(inspect.signature(func))
    except (TypeError, ValueError):
        return "(…)"


def _write_group_rst(
    path: Path, namespace: str, entries: Iterable[tuple[str, str, Callable[..., object]]]
) -> None:
    title = namespace
    lines = [title, "=" * len(title), ""]
    grouped = list(entries)
    if not grouped:
        lines.append("No public decorated APIs in this module.")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    for name, role, func in grouped:
        label = _ROLE_LABELS[role]
        lines.append(f"{name} ({label})")
        lines.append("-" * (len(name) + len(label) + 3))
        lines.append("")
        doc = inspect.getdoc(func) or ""
        if doc:
            lines.append("Description::")
            lines.append("")
            for doc_line in doc.splitlines():
                lines.append(f"   {doc_line}" if doc_line else "")
            lines.append("")
        lines.append(f"Signature: ``{name}{_format_signature(func)}``")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_user_api(*, output_root: Path | None = None) -> Path:
    """Generate filtered user API RST (commands, measurements, verifications only).

    :param output_root: Output directory for RST files (default: ``build/docgen/user_api/rst``).
    :type output_root: Path | None, optional

    :returns: Directory containing ``index.rst`` and per-namespace pages.
    :rtype: Path
    """
    repo_root = _repo_root()
    if str(repo_root) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(repo_root))

    root = output_root or (repo_root / "build" / "docgen" / "user_api" / "rst")
    if root.exists():
        for child in root.glob("*.rst"):
            child.unlink()
    root.mkdir(parents=True, exist_ok=True)

    index_lines = [
        "Colosseum user API",
        "====================",
        "",
        "Public ``col.*`` commands, measurements, and verifications. Evidence from",
        "``col.io.*`` calls is stored under domain ``equipment`` in ``execution.sqlite``.",
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]

    for root_ns, package, submodules in _SCAN_TARGETS:
        for sub in submodules:
            module_name = f"{package}.{sub}"
            module = _load_module(module_name)
            namespace = _namespace_path(root_ns, sub)
            slug = namespace.replace(".", "_")
            entries = _decorated_entries(module)
            if not entries:
                continue
            _write_group_rst(root / f"{slug}.rst", namespace, entries)
            index_lines.append(f"   {namespace} <{slug}>")

    index_lines.append("")
    (root / "index.rst").write_text("\n".join(index_lines), encoding="utf-8")
    return root


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for user API RST generation.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    import argparse

    parser = argparse.ArgumentParser(description="Build filtered user API RST for PDF docs")
    parser.add_argument("--output", type=Path, help="Default: build/docgen/user_api/rst")
    args = parser.parse_args(argv)
    out = build_user_api(output_root=args.output)
    print(f"User API RST: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
