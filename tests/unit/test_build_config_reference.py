"""Docgen bench config reference generation."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_build_config_reference_contains_psu_resource(tmp_path) -> None:
    sys.path.insert(0, str(REPO))
    docgen_dir = REPO / "scripts" / "docgen"
    sys.path.insert(0, str(docgen_dir))
    from build_config_reference import build_config_reference_rst

    output = tmp_path / "config_reference.rst"
    build_config_reference_rst(output_path=output)
    text = output.read_text(encoding="utf-8")
    assert "``psu_id``" in text
    assert "``resource``" in text
    assert "``visa_library``" in text
