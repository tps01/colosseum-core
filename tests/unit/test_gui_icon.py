from __future__ import annotations

import zlib
from pathlib import Path

from colosseum.gui._icon import _ASSETS, init_windows_taskbar, wrap_icon_png


def test_gui_icon_assets_exist() -> None:
    assert (_ASSETS / "colosseum.ico").is_file()
    assert (_ASSETS / "colosseum-512.png").is_file()
    assert Path(__file__).resolve().parents[2] / "colosseum" / "gui" / "assets" == _ASSETS


def _png_alpha_values(png: bytes) -> list[int]:
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    compressed = b""
    while offset < len(png):
        length = int.from_bytes(png[offset : offset + 4], "big")
        tag = png[offset + 4 : offset + 8]
        chunk = png[offset + 8 : offset + 8 + length]
        if tag == b"IDAT":
            compressed += chunk
        offset += 12 + length
    raw = zlib.decompress(compressed)
    alphas: list[int] = []
    stride = 16 * 4
    pos = 0
    for _ in range(16):
        pos += 1
        alphas.extend(raw[pos + 3 : pos + stride : 4])
        pos += stride
    return alphas


def test_wrap_icon_is_a_semi_transparent_png() -> None:
    faint = _png_alpha_values(wrap_icon_png(scale=1.0, wrapped=False, dark=True))
    strong = _png_alpha_values(wrap_icon_png(scale=1.0, wrapped=True, dark=True))
    assert 0 in faint
    assert max(faint) == 105
    assert max(strong) == 200


def test_init_windows_taskbar_is_safe_off_windows(monkeypatch) -> None:
    monkeypatch.setattr("colosseum.gui._icon.sys.platform", "linux")
    init_windows_taskbar()
