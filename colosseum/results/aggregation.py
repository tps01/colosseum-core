from __future__ import annotations

from collections import Counter


class ResultAggregator:
    def __init__(self) -> None:
        self._records: list[dict] = []
        self.suite_error: bool = False
        self.teardown_failed: bool = False

    def record_verification(self, result, *, key: str = "", command: str = "", domain: str = "") -> None:
        self._records.append(
            {
                "status": result.status,
                "optional": bool(result.optional),
                "message": result.message,
                "key": key,
                "command": command,
                "domain": domain,
            }
        )

    def mark_suite_error(self, message: str) -> None:
        self.suite_error = True
        self._records.append(
            {"status": "ERROR", "optional": False, "message": message, "key": "", "command": "suite", "domain": "runner"}
        )

    def mark_teardown_failed(self) -> None:
        self.teardown_failed = True

    def overall_pass(self) -> bool:
        if self.suite_error or self.teardown_failed:
            return False
        for row in self._records:
            if row["optional"]:
                continue
            if row["status"] in {"FAIL", "ERROR"}:
                return False
        return True

    def failed_required_verifications(self) -> list[dict]:
        return [
            row
            for row in self._records
            if not row["optional"] and row["status"] in {"FAIL", "ERROR"}
        ]

    def optional_verifications(self) -> list[dict]:
        return [row for row in self._records if row["optional"]]

    def counts(self) -> dict:
        required = Counter()
        optional = Counter()
        for row in self._records:
            target = optional if row["optional"] else required
            target[row["status"]] += 1
        return {"required": dict(required), "optional": dict(optional), "total": len(self._records)}

    def exit_code(self) -> int:
        return 0 if self.overall_pass() else 1
