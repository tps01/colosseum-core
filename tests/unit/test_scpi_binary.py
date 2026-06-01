"""IEEE 488.2 definite-length block helpers."""

from __future__ import annotations

from colosseum_equipment.protocols.scpi import format_definite_length_block, parse_definite_length_block


def test_format_definite_length_block() -> None:
    payload = b"hello"
    assert format_definite_length_block(payload) == b"#15hello"


def test_parse_definite_length_block() -> None:
    data = b"#15hello"
    assert parse_definite_length_block(data) == b"hello"
