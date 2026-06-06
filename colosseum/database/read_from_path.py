from __future__ import annotations

from pathlib import Path
from types import TracebackType

from .manager import DatabaseManager
from .read import is_allowed_table
from .records import MeasurementRecord, RunMetadataRecord, VerificationRecord


class OfflineDatabaseReader:
    """Read-only access to a completed run's execution.sqlite."""

    def __init__(self, db_path: Path) -> None:
        self._db = DatabaseManager()
        self._db.open_readonly(db_path)

    def close(self) -> None:
        self._db.close()

    def read_measurements(self) -> list[MeasurementRecord]:
        return self._db.fetch_all_measurements()

    def read_verifications(self) -> list[VerificationRecord]:
        return self._db.fetch_all_verifications()

    def read_run_metadata(self) -> list[RunMetadataRecord]:
        return self._db.fetch_run_metadata()

    def read_table(self, name: str) -> list[dict[str, object]]:
        if not is_allowed_table(name):
            raise ValueError(f"Unknown or disallowed table: {name}")
        return self._db.fetch_table_rows(name)

    def __enter__(self) -> OfflineDatabaseReader:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        self.close()


def read_from_path(db_path: Path) -> OfflineDatabaseReader:
    return OfflineDatabaseReader(db_path)
