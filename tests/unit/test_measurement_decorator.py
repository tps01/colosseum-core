"""U-MV-01: @measurement duplicate key rules."""

from __future__ import annotations

import pytest

from colosseum.decorators.measurement import MeasurementKeyError, measurement


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


@measurement
def _once(*, key: str) -> int:
    return 1


@measurement(multi_row=True)
def _multi(*, key: str, row_index: int) -> int:
    return row_index


@pytest.mark.requirement("U-MV-01")
def test_duplicate_key_raises(ctx) -> None:
    _once(key="dup")
    with pytest.raises(MeasurementKeyError, match="Duplicate measurement key"):
        _once(key="dup")


def test_multi_row_requires_row_index(ctx) -> None:
    with pytest.raises(MeasurementKeyError, match="row_index"):
        _multi(key="series")


def test_multi_row_allows_distinct_indexes(ctx) -> None:
    _multi(key="series", row_index=0)
    _multi(key="series", row_index=1)
    assert ctx.db.count_rows("measurements", "key=?", ("series",)) == 2
