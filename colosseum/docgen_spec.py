"""
Public contract for Colosseum modular documentation generation.

Third-party extensions ship a ``colosseum.docgen`` entry point whose target is
``your_package.docgen_entry:spec`` returning :class:`DocgenModuleSpec`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

DOCGEN_ENTRY_GROUP = "colosseum.docgen"


@dataclass(frozen=True)
class DocgenModuleSpec:
    """Describes one installable unit (core or plugin) for autodoc staging."""

    module_id: str
    title: str
    import_packages: Sequence[str]
    autodoc_modules: Sequence[str]
    order: int = 100
    namespace: str | None = None
    extra_rst_dirs: Sequence[str | Path] = field(default_factory=list)

    def normalized_extra_rst_dirs(self) -> list[Path]:
        return [Path(p) for p in self.extra_rst_dirs]
