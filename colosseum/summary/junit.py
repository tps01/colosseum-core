"""JUnit XML report listener."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING
from xml.dom import minidom

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.database import CommandRecord
    from colosseum.results.finalize import FinalizeRunResult


def _add_property(properties: ET.Element, name: str, value: str) -> None:
    prop = ET.SubElement(properties, "property")
    prop.set("name", name)
    prop.set("value", value)


def _first_abort_cause(commands: list[CommandRecord]) -> str:
    for row in commands:
        if not row.optional and row.status == "ERROR" and row.cause:
            return row.cause
    return ""


def write_junit_report(
    output_dir: Path,
    ctx: RuntimeContext,
    result: FinalizeRunResult,
) -> Path:
    """Write ``junit.xml`` for one slot."""
    suite = ET.Element("testsuite")
    suite.set("name", ctx.test_case_name)
    cases: list[ET.Element] = []
    parameters_file = str(ctx.parameters_path) if ctx.parameters_path is not None else ""
    abort_cause = _first_abort_cause(result.commands)

    for row in result.verifications:
        case = ET.Element("testcase")
        case.set("classname", f"{row.domain}.{row.command}")
        case.set("name", row.key)
        props = ET.SubElement(case, "properties")
        if abort_cause:
            _add_property(props, "cause", abort_cause)
        if parameters_file:
            _add_property(props, "parameters_file", parameters_file)
        status = row.status
        if row.optional and status in {"FAIL", "ERROR", "BLOCKED"}:
            skipped = ET.SubElement(case, "skipped")
            skipped.set("message", row.message or status)
        elif status in {"FAIL", "BLOCKED"}:
            failure = ET.SubElement(case, "failure")
            failure.set("message", row.message or status)
            failure.set("type", status)
        elif status == "ERROR":
            error = ET.SubElement(case, "error")
            error.set("message", row.message or status)
            error.set("type", status)
        cases.append(case)

    if not result.verifications:
        for row in result.commands:
            if row.status != "ERROR" or row.optional:
                continue
            case = ET.Element("testcase")
            case.set("classname", f"{row.domain}.{row.command}")
            case.set("name", row.key or row.command)
            props = ET.SubElement(case, "properties")
            if row.cause:
                _add_property(props, "cause", row.cause)
            if parameters_file:
                _add_property(props, "parameters_file", parameters_file)
            error = ET.SubElement(case, "error")
            error.set("message", row.message or "ERROR")
            error.set("type", "ERROR")
            cases.append(case)

    failures = sum(1 for case in cases if case.find("failure") is not None)
    errors = sum(1 for case in cases if case.find("error") is not None)
    skipped = sum(1 for case in cases if case.find("skipped") is not None)
    suite.set("tests", str(len(cases)))
    suite.set("failures", str(failures))
    suite.set("errors", str(errors))
    suite.set("skipped", str(skipped))
    for case in cases:
        suite.append(case)

    rough = ET.tostring(suite, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    path = output_dir / "junit.xml"
    path.write_bytes(pretty)
    if ctx.logger is not None:
        ctx.logger.info("Wrote JUnit report: %s", path)
    return path
