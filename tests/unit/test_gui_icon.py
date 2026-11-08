from __future__ import annotations

from pathlib import Path

from colosseum.gui._icon import _ASSETS, init_windows_taskbar, wrap_icon_png


def test_gui_icon_assets_exist() -> None:
    assert (_ASSETS / "colosseum.ico").is_file()
    assert (_ASSETS / "colosseum-512.png").is_file()
    assert Path(__file__).resolve().parents[2] / "colosseum" / "gui" / "assets" == _ASSETS


def test_wrap_icon_png_is_readable() -> None:
    png = wrap_icon_png(scale=1.0, wrapped=True, dark=True)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 32


def test_init_windows_taskbar_is_noop_off_windows(monkeypatch) -> None:
    monkeypatch.setattr("colosseum.gui._icon.sys.platform", "linux")
    assert init_windows_taskbar() is None
