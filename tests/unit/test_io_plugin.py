from __future__ import annotations

import pytest

import colosseum as col
from colosseum.context import init_context
from colosseum_equipment.io.exceptions import IoNotImplementedError


def test_io_write_pin_stub_raises() -> None:
    init_context(test_case_name="io_stub_test")
    with pytest.raises(IoNotImplementedError, match="NI 6501"):
        col.io.dio.write_pin(dio_id=1, line=0, value=True)
