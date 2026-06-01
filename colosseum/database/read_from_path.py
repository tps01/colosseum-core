from __future__ import annotations

from pathlib import Path
from typing import List

from .manager import DatabaseManager
from .records import MeasurementRecord, RunMetadataRecord, VerificationRecord
from .read import is_allowed_table


class OfflineDatabaseReader:
    """Read-only access to a completed run's execution.sqlite."""

    def __init__(self, db_path: Path) -> None:
        self._db = DatabaseManager()
        self._db.open_readonly(db_path)

    def close(self) -> None:
        self._db.close()

    def read_measurements(self) -> List[MeasurementRecord]:
        return self._db.fetch_all_measurements()

    def read_verifications(self) -> List[VerificationRecord]:
        return self._db.fetch_all_verifications()

    def read_run_metadata(self) -> List[RunMetadataRecord]:
        return self._db.fetch_run_metadata()

    def read_table(self, name: str) -> List[dict]:
        if not is_allowed_table(name):
            raise ValueError(f"Unknown or disallowed table: {name}")
        return self._db.fetch_table_rows(name)

    def __enter__(self) -> OfflineDatabaseReader:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def read_from_path(db_path: Path) -> OfflineDatabaseReader:
    return OfflineDatabaseReader(db_path)
