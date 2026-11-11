from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol, TypedDict

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext
    from colosseum.runner.runtime import SuiteSlotResult


def coerce_requirements(value: object) -> list[str]:
    """Return requirement ids from a string or list of strings.

    A string is split on commas. A list keeps each stripped item (not split again).
    Empty tokens are dropped. Raises ``TypeError`` for other types.

    :param value: Requirement metadata attached to a verification.
    :returns: Ordered IDs, retaining repeated attachments.
    :raises TypeError: If the value or a list item has an unsupported type.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        ids: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    f"requirements list items must be strings, got {type(item).__name__}",
                )
            text = item.strip()
            if text:
                ids.append(text)
        return ids
    raise TypeError(
        f"requirements must be a string or list of strings, got {type(value).__name__}",
    )


class OutcomeResult(Protocol):
    status: str
    optional: bool
    message: str


class OutcomeRecord(TypedDict):
    kind: str
    status: str
    optional: bool
    message: str
    key: str
    command: str
    domain: str
    cause: str
    description: str
    requirements: list[str]


class OutcomeCounts(TypedDict):
    required: dict[str, int]
    optional: dict[str, int]
    total: int


class ResultAggregator:
    def __init__(self) -> None:
        self._records: list[OutcomeRecord] = []
        self.suite_error: bool = False
        self.teardown_failed: bool = False

    def _record_outcome(
        self,
        result: OutcomeResult,
        *,
        key: str = "",
        command: str = "",
        domain: str = "",
        kind: str,
        cause: str = "",
        description: str = "",
        requirements: list[str] | None = None,
    ) -> None:
        self._records.append(
            {
                "kind": kind,
                "status": result.status,
                "optional": bool(result.optional),
                "message": result.message,
                "key": key,
                "command": command,
                "domain": domain,
                "cause": cause,
                "description": description,
                "requirements": list(requirements or []),
            },
        )

    def record_verification(
        self,
        result: OutcomeResult,
        *,
        key: str = "",
        command: str = "",
        domain: str = "",
        description: str = "",
        requirements: list[str] | None = None,
    ) -> None:
        self._record_outcome(
            result,
            key=key,
            command=command,
            domain=domain,
            kind="verification",
            description=description,
            requirements=requirements,
        )

    def record_command(
        self,
        result: OutcomeResult,
        *,
        key: str = "",
        command: str = "",
        domain: str = "",
        cause: str = "",
    ) -> None:
        self._record_outcome(
            result,
            key=key,
            command=command,
            domain=domain,
            kind="command",
            cause=cause,
        )

    def record_measurement(
        self,
        result: OutcomeResult,
        *,
        key: str = "",
        command: str = "",
        domain: str = "",
    ) -> None:
        self._record_outcome(
            result,
            key=key,
            command=command,
            domain=domain,
            kind="measurement",
        )

    def mark_suite_error(self, message: str) -> None:
        self.suite_error = True
        self._records.append(
            {
                "kind": "suite",
                "status": "ERROR",
                "optional": False,
                "message": message,
                "key": "",
                "command": "suite",
                "domain": "runner",
                "cause": "",
                "description": "",
                "requirements": [],
            },
        )

    def mark_teardown_failed(self) -> None:
        self.teardown_failed = True

    def overall_pass(self) -> bool:
        if self.suite_error or self.teardown_failed:
            return False
        for row in self._records:
            if row["optional"]:
                continue
            if row["status"] in {"FAIL", "ERROR", "BLOCKED"}:
                return False
        return True

    def failed_required_outcomes(self) -> list[OutcomeRecord]:
        return [row for row in self._records if not row["optional"] and row["status"] in {"FAIL", "ERROR", "BLOCKED"}]

    def has_required_procedural_command_error(self) -> bool:
        return bool(self.required_command_errors(cause="procedural"))

    def required_command_errors(self, *, cause: str | None = None) -> list[OutcomeRecord]:
        """Return scored command errors in execution order."""
        return [
            row
            for row in self._records
            if row["kind"] == "command"
            and not row["optional"]
            and row["status"] == "ERROR"
            and (cause is None or row.get("cause", "unit") == cause)
        ]

    def optional_outcomes(self) -> list[OutcomeRecord]:
        return [row for row in self._records if row["optional"]]

    def counts(self) -> OutcomeCounts:
        required: Counter[str] = Counter()
        optional: Counter[str] = Counter()
        for row in self._records:
            target = optional if row["optional"] else required
            target[row["status"]] += 1
        return {"required": dict(required), "optional": dict(optional), "total": len(self._records)}

    def exit_code(self) -> int:
        return 0 if self.overall_pass() else 1


def build_run_summary(
    ctx: RuntimeContext,
    aggregator: ResultAggregator,
    *,
    measurement_count: int,
    command_count: int,
) -> dict[str, Any]:
    """Build one finalized projection for persistence, stdout, and report rendering.

    :param ctx: Runtime identity and execution metadata.
    :param aggregator: Scored outcomes; raw plugin rows are evidence only.
    :param measurement_count: Settled measurement row count.
    :param command_count: Settled command row count.
    :returns: Version-one compact result payload, without sample values.
    """
    records = [row.copy() for row in aggregator._records]  # noqa: SLF001
    verification_counts: dict[str, dict[str, int]] = {"required": {}, "optional": {}}
    command_counts: dict[str, dict[str, int]] = {"required": {}, "optional": {}}
    for row in records:
        counts = verification_counts if row["kind"] == "verification" else command_counts
        if row["kind"] not in {"verification", "command"}:
            continue
        statuses = counts["optional" if row["optional"] else "required"]
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    failed = aggregator.failed_required_outcomes()
    code = aggregator.exit_code()
    payload: dict[str, Any] = {
        "colosseum_version": ctx.framework_version,
        "test_case": ctx.test_case_name,
        "suite": ctx.suite_name,
        "config_path": str(ctx.config_path) if ctx.config_path else None,
        "parameters_path": str(ctx.parameters_path) if ctx.parameters_path else None,
        "metadata_path": ctx.metadata_path or None,
        "output_directory": str(ctx.output_dir) if ctx.output_dir else None,
        "end_time_utc": datetime.now(timezone.utc).isoformat(),
        "overall_result": "PASS" if code == 0 else "FAIL",
        "exit_code": code,
        "measurement_count": measurement_count,
        "command_count": command_count,
        "verification_counts": verification_counts,
        "command_counts": command_counts,
        "failed_required_outcomes": [
            {name: row.get(name, "") for name in ("kind", "domain", "command", "key", "status", "message")}
            for row in failed
        ],
        "failed_required_verifications": [
            {name: row.get(name, "") for name in ("domain", "command", "key", "status", "message", "description")}
            for row in failed
            if row["kind"] == "verification"
        ],
        "suite_error": aggregator.suite_error,
        "teardown_failed": aggregator.teardown_failed,
        "requirements": aggregate_requirements(aggregator._records),  # noqa: SLF001
        "outcomes": records,
        "optional_outcomes": aggregator.optional_outcomes(),
    }
    if ctx.session.kind != "suite" and ctx.provenance is not None:
        payload["provenance"] = ctx.provenance
    if ctx.run_options.dry_run:
        payload["dry_run"] = True
        payload["dry_run_calls"] = [
            {name: row.get(name, "") for name in ("kind", "domain", "command", "key", "status")} for row in records
        ]
    return payload


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _test_slot_counts(slots: list[SuiteSlotResult]) -> dict[str, int | float]:
    total = len(slots)
    passed = sum(1 for slot in slots if slot.overall == "PASS")
    failed = total - passed
    counts: dict[str, int | float] = {"total": total, "pass": passed, "fail": failed}
    if total > 0:
        counts["pass_percent"] = round(100.0 * passed / total, 1)
        counts["fail_percent"] = round(100.0 * failed / total, 1)
    return counts


def _slot_failure_identities(slot: SuiteSlotResult) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for row in slot.summary.get("failed_required_verifications", []):
        found.add(
            (
                _text(row.get("domain")),
                _text(row.get("command")),
                _text(row.get("key")),
            ),
        )
    return found


def _repeated_test_indexes(slots: list[SuiteSlotResult]) -> set[int]:
    counts: dict[int, int] = {}
    for slot in slots:
        if slot.test_index is None:
            continue
        counts[slot.test_index] = counts.get(slot.test_index, 0) + 1
    return {index for index, count in counts.items() if count > 1}


def _failure_rank_key(
    item: tuple[tuple[int, str, str, str, str], int],
) -> tuple[int, str, str, str, str, int]:
    identity, count = item
    test_index, script, domain, command, key = identity
    return (-count, script, domain, command, key, test_index)


def _common_failed_verifications(
    slots: list[SuiteSlotResult],
) -> list[dict[str, int | str]]:
    repeated = _repeated_test_indexes(slots)
    totals: dict[tuple[int, str, str, str, str], int] = {}
    for slot in slots:
        test_index = slot.test_index
        if not isinstance(test_index, int) or test_index not in repeated:
            continue
        script = slot.script_path.name
        for domain, command, key in _slot_failure_identities(slot):
            identity = (test_index, script, domain, command, key)
            totals[identity] = totals.get(identity, 0) + 1
    ranked = sorted(totals.items(), key=_failure_rank_key)
    return [
        {
            "count": count,
            "test_index": test_index,
            "script": script,
            "domain": domain,
            "command": command,
            "key": key,
        }
        for (test_index, script, domain, command, key), count in ranked[:10]
    ]


def build_suite_summary(ctx: RuntimeContext, *, exit_code: int, overall: str) -> dict[str, Any]:
    """Reduce finalized slot facts once, independently of emitted summary files.

    :param ctx: Ordered slot occurrences and suite scheduling flags.
    :param exit_code: Existing suite-policy conclusion.
    :param overall: Corresponding PASS/FAIL label.
    :returns: The existing suite summary projection.
    """
    ended_at = datetime.now(timezone.utc)
    started = ctx.suite_started_at
    started_utc = started.astimezone(timezone.utc) if started is not None else None
    test_slots = ctx.suite_test_results
    slot_counts = _test_slot_counts(test_slots)
    common_failures = _common_failed_verifications(test_slots)
    requirement_rows = rollup_suite_requirements(test_slots)
    payload: dict[str, Any] = {
        "colosseum_version": ctx.framework_version,
        "suite": ctx.suite_name,
        "config_path": str(ctx.config_path) if ctx.config_path else None,
        "output_directory": str(ctx.suite_output_dir) if ctx.suite_output_dir else None,
        "end_time_utc": ended_at.isoformat(),
        "overall_result": overall,
        "exit_code": exit_code,
        "suite_failed": ctx.session.suite_failed,
        "suite_fail_reason": ctx.session.suite_fail_reason,
        "fail_fast_stopped": ctx.session.fail_fast_stopped,
        "fail_fast_stop_reason": ctx.session.fail_fast_stop_reason,
        "fail_fast_stop_script": ctx.session.fail_fast_stop_script,
        "test_slots": [slot.as_dict() for slot in test_slots],
        "all_slots": [slot.as_dict() for slot in ctx.suite_slot_results],
        "test_slot_counts": slot_counts,
        "common_failed_verifications": common_failures,
        "requirements": requirement_rows,
    }
    if ctx.provenance is not None:
        payload["provenance"] = ctx.provenance
    if started_utc is not None:
        payload["start_time_utc"] = started_utc.isoformat()
        payload["duration_seconds"] = (ended_at - started_utc).total_seconds()
    return payload


_PASSING = frozenset({"PASS", "DRY"})


def _identity(row: OutcomeRecord) -> dict[str, str]:
    return {
        "domain": str(row.get("domain") or ""),
        "command": str(row.get("command") or ""),
        "key": str(row.get("key") or ""),
    }


def aggregate_requirements(records: list[OutcomeRecord]) -> list[dict[str, Any]]:
    """Build first-seen requirement rows from verification outcomes."""
    order: list[str] = []
    failures: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()
    for row in records:
        if row["kind"] != "verification":
            continue
        ids = row["requirements"]
        if not ids:
            continue
        for req_id in ids:
            if not req_id:
                continue
            if req_id not in seen:
                seen.add(req_id)
                order.append(req_id)
                failures[req_id] = []
            if row["status"] not in _PASSING:
                failures[req_id].append(_identity(row))
    return [
        {
            "id": req_id,
            "status": "PASS" if not failures[req_id] else "FAIL",
            "failures": failures[req_id],
        }
        for req_id in order
    ]


def rollup_suite_requirements(slots: list[SuiteSlotResult]) -> list[dict[str, Any]]:
    """Roll requirement ids across test slots that reported them."""
    order: list[str] = []
    failures: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for slot in slots:
        script = slot.script_path.name
        for row in slot.summary.get("requirements", []):
            req_id = row.get("id")
            if not isinstance(req_id, str) or not req_id:
                continue
            if req_id not in seen:
                seen.add(req_id)
                order.append(req_id)
                failures[req_id] = []
            if row.get("status") == "PASS":
                continue
            for fail in row.get("failures") or []:
                if not isinstance(fail, dict):
                    continue
                failures[req_id].append(
                    {
                        "test_index": slot.test_index,
                        "script": script,
                        "domain": str(fail.get("domain") or ""),
                        "command": str(fail.get("command") or ""),
                        "key": str(fail.get("key") or ""),
                    },
                )
            if not (row.get("failures") or []):
                failures[req_id].append(
                    {
                        "test_index": slot.test_index,
                        "script": script,
                        "domain": "",
                        "command": "",
                        "key": "",
                    },
                )
    return [
        {
            "id": req_id,
            "status": "PASS" if not failures[req_id] else "FAIL",
            "failures": failures[req_id],
        }
        for req_id in order
    ]
