from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MeasurementRecord:
    id: int
    domain: str
    command: str
    key: str
    row_index: int
    value: Any
    units: str | None
    artifact_path: str | None
    status: str
    timestamp: str


@dataclass(frozen=True)
class VerificationRecord:
    id: int
    domain: str
    command: str
    key: str
    expected: Any
    actual: Any
    status: str
    optional: bool
    message: str | None
    timestamp: str


@dataclass(frozen=True)
class RunMetadataRecord:
    key: str
    value: str
