"""Fail closed on installed distribution licenses outside RULES.md.

This checks metadata, not copied source or native components hidden by metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

from packaging.licenses import InvalidLicenseExpression, canonicalize_license_expression

REPO = Path(__file__).resolve().parents[2]
POLICY = Path(__file__).with_name("license_policy.json")
PYINSTALLER_LEGACY_LICENSE = (
    "GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute "
    "non-free programs (including commercial ones)"
)


def rule_labels(text: str) -> list[str]:
    """Read the normative allowlist, including wrapped bullet text."""
    section = text.split("Only the following licenses are allowed:", 1)[1].split("---", 1)[0]
    labels: list[str] = []
    for line in section.splitlines():
        if line.startswith("- "):
            labels.append(line[2:].strip())
        elif line.strip() and labels:
            labels[-1] += " " + line.strip()
    return labels


def load_policy() -> tuple[set[str], dict[str, str]]:
    """Load SPDX mappings, refusing policy drift or unrecognized identifiers."""
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if set(rule_labels((REPO / "RULES.md").read_text(encoding="utf-8"))) != set(policy["rules"]):
        raise ValueError("RULES.md and license_policy.json differ; review license mappings")
    allowed = {str(canonicalize_license_expression(item)) for entries in policy["rules"].values() for item in entries}
    if any(" " in item for item in allowed):
        raise ValueError("Policy entries must be individual SPDX identifiers")
    aliases = policy["aliases"]
    if any(value not in allowed for value in aliases.values()):
        raise ValueError("License aliases must refer to approved identifiers")
    return allowed, aliases


def expression_allowed(expression: str, allowed: set[str]) -> bool:
    """Evaluate validated SPDX syntax with AND precedence and atomic WITH terms."""
    canonical = canonicalize_license_expression(expression)
    tokens = canonical.replace("(", "( ").replace(")", " )").split()
    position = 0

    def atom() -> bool:
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "(":
            result = either()
            position += 1  # Closing parenthesis; grammar validated by packaging.
            return result
        if position < len(tokens) and tokens[position] == "WITH":
            token += " WITH " + tokens[position + 1]
            position += 2
        return token in allowed

    def both() -> bool:
        nonlocal position
        result = atom()
        while position < len(tokens) and tokens[position] == "AND":
            position += 1
            right = atom()  # Always consume the expression, even if left failed.
            result = result and right
        return result

    def either() -> bool:
        nonlocal position
        result = both()
        while position < len(tokens) and tokens[position] == "OR":
            position += 1
            right = both()
            result = result or right
        return result

    return either()


def inspect_distribution(
    dist: metadata.Distribution,
    allowed: set[str],
    aliases: dict[str, str],
) -> dict:
    """Classify one installed artifact without guessing ambiguous license names."""
    info = dist.metadata
    source = "License-Expression"
    declared = info.get(source)
    if not declared:
        source = "License"
        declared = info.get(source)
    if not declared or declared.strip().upper() == "UNKNOWN":
        source = "Classifier"
        classifiers = [
            value.rsplit(" :: ", 1)[-1] for value in info.get_all("Classifier", []) if value.startswith("License :: ")
        ]
        declared = classifiers[0] if len(classifiers) == 1 else ""
    expression = aliases.get(declared, declared) if source != "License-Expression" else declared
    row = {
        "name": info.get("Name", "UNKNOWN"),
        "version": dist.version,
        "source": source,
        "declared": declared,
        "expression": expression,
    }
    if info.get("Name", "").lower().replace("_", "-") == "pyinstaller" and (
        (source == "License" and declared == PYINSTALLER_LEGACY_LICENSE)
        or (source == "License-Expression" and declared == "GPL-2.0-or-later WITH Bootloader-exception")
    ):
        row.update(passed=True, reason="approved PyInstaller-specific exception")
        return row
    try:
        canonical = str(canonicalize_license_expression(expression))
        row["expression"] = canonical
        passed = expression_allowed(canonical, allowed)
        reason = (
            "approved expression"
            if passed
            else (
                "LGPL requires an unmodified-artifact review"
                if "LGPL" in canonical
                else "unapproved license or exception"
            )
        )
    except (InvalidLicenseExpression, RecursionError):
        passed = False
        reason = "missing, ambiguous, or unrecognized license metadata; review required"
    row.update(passed=passed, reason=reason)
    return row


def main(argv: list[str] | None = None) -> int:
    """Audit every installed distribution, write evidence, and return nonzero on failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPO / "build/license-report.json")
    args = parser.parse_args(argv)
    try:
        allowed, aliases = load_policy()
    except (ValueError, KeyError) as exc:
        print(f"STATIC FAIL: licenses: {exc}", file=sys.stderr)
        return 1
    rows = sorted(
        (inspect_distribution(dist, allowed, aliases) for dist in metadata.distributions()),
        key=lambda row: (row["name"], row["version"]),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    failures = [row for row in rows if not row["passed"]]
    for row in failures:
        print(f"FAIL {row['name']}=={row['version']}: {row['declared'][:100]!r}: {row['reason']}")
    print(
        f"STATIC {'FAIL' if failures else 'PASS'}: licenses "
        f"({len(failures)}/{len(rows)} rejected); report: {args.report}",
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
