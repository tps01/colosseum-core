"""Docgen bench config reference generation."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_build_config_reference_handles_core_only_install(tmp_path) -> None:
    sys.path.insert(0, str(REPO))
    docgen_dir = REPO / "scripts" / "docgen"
    sys.path.insert(0, str(docgen_dir))
    from build_config_reference import build_config_reference_rst

    output = tmp_path / "config_reference.rst"
    build_config_reference_rst(output_path=output)
    text = output.read_text(encoding="utf-8")
    assert "No plugin configuration sections are installed" in text
    assert "colosseum_equipment" not in text
