"""License policy decisions must fail closed without misreading SPDX choices."""

from __future__ import annotations

from email.message import Message
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from packaging.licenses import InvalidLicenseExpression
from tests.static import run_licenses as audit

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("MIT", True),
        ("Apache-2.0 OR GPL-3.0-only", True),
        ("GPL-3.0-only OR MIT", True),
        ("MIT AND GPL-3.0-only", False),
        ("MIT OR Apache-2.0 AND GPL-3.0-only", True),
        ("(MIT OR Apache-2.0) AND GPL-3.0-only", False),
        ("MIT AND (BSD-2-Clause OR GPL-3.0-only)", True),
        ("MPL-2.0", False),
        ("AGPL-3.0-only", False),
        ("LGPL-2.1-or-later", False),
        ("GPL-2.0-only WITH Bootloader-exception", False),
        ("MIT-0", False),
        ("LicenseRef-Unknown", False),
    ],
)
def test_spdx_policy(expression: str, *, expected: bool) -> None:
    allowed, _ = audit.load_policy()
    assert audit.expression_allowed(expression, allowed) is expected


def distribution(
    expression: str | None = None,
    legacy: str | None = None,
    classifiers: tuple[str, ...] = (),
) -> SimpleNamespace:
    info = Message()
    info["Name"] = "example-package"
    if expression is not None:
        info["License-Expression"] = expression
    if legacy is not None:
        info["License"] = legacy
    for classifier in classifiers:
        info["Classifier"] = f"License :: OSI Approved :: {classifier}"
    return SimpleNamespace(metadata=info, version="1.0")


@pytest.mark.parametrize(
    ("dist", "expected"),
    [
        (distribution(expression="MIT"), True),
        (distribution(legacy="MIT License"), True),
        (distribution(classifiers=("MIT License",)), True),
        (distribution(expression="MPL-2.0", legacy="MIT"), False),
        (distribution(expression="not MIT", classifiers=("MIT License",)), False),
        (distribution(legacy="BSD"), False),
        (distribution(classifiers=("BSD License",)), False),
        (distribution(classifiers=("MIT License", "Apache Software License")), False),
        (
            distribution(
                legacy="Creative Commons Zero v1.0 Universal",
                classifiers=("MIT License",),
            ),
            False,
        ),
        (distribution(), False),
    ],
)
def test_metadata_and_ambiguity(dist: SimpleNamespace, *, expected: bool) -> None:
    allowed, aliases = audit.load_policy()
    assert audit.inspect_distribution(dist, allowed, aliases)["passed"] is expected


def test_invalid_spdx_is_rejected() -> None:
    with pytest.raises(InvalidLicenseExpression):
        audit.expression_allowed("MIT OR", {"MIT"})


def test_rules_drift_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "RULES.md").write_text(
        "Only the following licenses are allowed:\n- MIT License\n---",
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "REPO", tmp_path)
    with pytest.raises(ValueError, match="differ"):
        audit.load_policy()


def test_command_checks_all_distributions_and_reports_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json

    monkeypatch.setattr(
        audit.metadata,
        "distributions",
        lambda: [
            distribution(expression="MIT"),
            distribution(expression="MPL-2.0"),
        ],
    )
    report = tmp_path / "licenses.json"
    assert audit.main(["--report", str(report)]) == 1
    rows = json.loads(report.read_text(encoding="utf-8"))
    assert len(rows) == 2
    assert sum(not row["passed"] for row in rows) == 1
    monkeypatch.setattr(audit.metadata, "distributions", lambda: [distribution(expression="MIT")])
    assert audit.main(["--report", str(report)]) == 0
