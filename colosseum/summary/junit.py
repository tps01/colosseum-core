"""JUnit XML report listener."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.database import CommandRecord, VerificationRecord
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


def _attach_skipped(case: ET.Element, row: VerificationRecord) -> None:
    skipped = ET.SubElement(case, "skipped")
    skipped.set("message", row.message or row.status)


def _attach_failure(case: ET.Element, row: VerificationRecord) -> None:
    failure = ET.SubElement(case, "failure")
    failure.set("message", row.message or row.status)
    failure.set("type", row.status)


def _attach_error(case: ET.Element, row: VerificationRecord) -> None:
    error = ET.SubElement(case, "error")
    error.set("message", row.message or row.status)
    error.set("type", row.status)


# status → element builder. Optional FAIL/ERROR/BLOCKED short-circuit to skipped.
_STATUS_ELEMENT: dict[str, Callable[[ET.Element, VerificationRecord], None]] = {
    "FAIL": _attach_failure,
    "BLOCKED": _attach_failure,
    "ERROR": _attach_error,
}


def _attach_verification_status(case: ET.Element, row: VerificationRecord) -> None:
    status = row.status
    if row.optional and status in {"FAIL", "ERROR", "BLOCKED"}:
        _attach_skipped(case, row)
        return
    attach = _STATUS_ELEMENT.get(status)
    if attach is not None:
        attach(case, row)


def _verification_case(
    row: VerificationRecord,
    *,
    abort_cause: str,
    parameters_file: str,
) -> ET.Element:
    case = ET.Element("testcase")
    case.set("classname", f"{row.domain}.{row.command}")
    case.set("name", row.description or row.key or row.command)
    props = ET.SubElement(case, "properties")
    if abort_cause:
        _add_property(props, "cause", abort_cause)
    if parameters_file:
        _add_property(props, "parameters_file", parameters_file)
    _attach_verification_status(case, row)
    return case


def _command_error_case(command: CommandRecord, *, parameters_file: str) -> ET.Element:
    case = ET.Element("testcase")
    case.set("classname", f"{command.domain}.{command.command}")
    case.set("name", command.key or command.command)
    props = ET.SubElement(case, "properties")
    if command.cause:
        _add_property(props, "cause", command.cause)
    if parameters_file:
        _add_property(props, "parameters_file", parameters_file)
    error = ET.SubElement(case, "error")
    error.set("message", command.message or "ERROR")
    error.set("type", "ERROR")
    return case


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
        cases.append(
            _verification_case(row, abort_cause=abort_cause, parameters_file=parameters_file),
        )

    if not result.verifications:
        for command in result.commands:
            if command.status != "ERROR" or command.optional:
                continue
            cases.append(_command_error_case(command, parameters_file=parameters_file))

    failure_count = sum(1 for case in cases if case.find("failure") is not None)
    error_count = sum(1 for case in cases if case.find("error") is not None)
    skipped_count = sum(1 for case in cases if case.find("skipped") is not None)
    suite.set("tests", str(len(cases)))
    suite.set("failures", str(failure_count))
    suite.set("errors", str(error_count))
    suite.set("skipped", str(skipped_count))
    for case in cases:
        suite.append(case)

    ET.indent(suite, space="  ")
    path = output_dir / "junit.xml"
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
    if ctx.logger is not None:
        ctx.logger.info("Wrote JUnit report: %s", path)
    return path
