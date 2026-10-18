from __future__ import annotations

from collections import Counter
from typing import Protocol, TypedDict


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
            },
        )

    def record_verification(
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
            kind="verification",
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
        return [
            row
            for row in self._records
            if not row["optional"] and row["status"] in {"FAIL", "ERROR", "BLOCKED"}
        ]

    def has_required_procedural_command_error(self) -> bool:
        return any(
            row["kind"] == "command"
            and not row["optional"]
            and row["status"] == "ERROR"
            and row.get("cause") == "procedural"
            for row in self._records
        )

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
