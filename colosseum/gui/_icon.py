"""Window icon helpers for the Colosseum GUI."""

from __future__ import annotations

import base64
import struct
import sys
import tkinter as tk
import zlib
from pathlib import Path
from typing import Any

# 16x16 wrap-text mark. '#' is ink; the arrow returns the first line onto the next.
_WRAP_GLYPH = (
    "................",
    "................",
    ".###########....",
    "............#...",
    ".#######....#...",
    "..........#.#...",
    ".........#..#...",
    ".########.#.....",
    "................",
    "................",
    ".#########......",
    "................",
    "................",
    "................",
    "................",
    "................",
)

_ASSETS = Path(__file__).resolve().parent / "assets"
_APP_USER_MODEL_ID = "Colosseum.GUI.1"


def init_windows_taskbar() -> None:
    """Prepare Windows taskbar identity and DPI handling before creating the window."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return
        if hasattr(windll, "shcore"):
            windll.shcore.SetProcessDpiAwareness(2)
        else:
            windll.user32.SetProcessDPIAware()
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        return


def _apply_windows_native_icon(window: Any, icon_path: str) -> None:  # noqa: ANN401
    """Set title-bar and taskbar icons via Win32 (sharper than tk iconbitmap on high-DPI)."""
    if sys.platform != "win32":
        return
    import ctypes

    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return
    hwnd = window.winfo_id()
    try:
        dpi = windll.user32.GetDpiForWindow(hwnd)
    except (AttributeError, OSError):
        dpi = 96
    scale = max(1, round(dpi / 96))
    image_icon = 1
    load_from_file = 0x0010
    wm_seticon = 0x0080
    icon_small, icon_big = 0, 1
    sizes = ((icon_small, min(64, 16 * scale)), (icon_big, min(256, 32 * scale)))
    for icon_type, size in sizes:
        handle = windll.user32.LoadImageW(
            None,
            icon_path,
            image_icon,
            size,
            size,
            load_from_file,
        )
        if handle:
            windll.user32.SendMessageW(hwnd, wm_seticon, icon_type, handle)


def apply_window_icon(window: Any) -> None:  # noqa: ANN401
    """Set title-bar and taskbar icons when bundled assets are available."""
    ico = _ASSETS / "colosseum.ico"
    try:
        if sys.platform == "win32" and ico.is_file():
            icon_path = str(ico.resolve())

            def _finalize_icon() -> None:
                window.iconbitmap(default=icon_path)
                _apply_windows_native_icon(window, icon_path)

            window.after_idle(_finalize_icon)
            return
        png = _ASSETS / "colosseum-512.png"
        if png.is_file():
            photo = tk.PhotoImage(file=str(png))
            window.iconphoto(True, photo)
            window._colosseum_icon = photo  # noqa: SLF001 — keep reference alive
    except tk.TclError:
        return


def wrap_icon_png(*, scale: float, wrapped: bool, dark: bool) -> bytes:
    """Semi-transparent wrap-text glyph. Wrapped state uses a stronger alpha."""
    logical = len(_WRAP_GLYPH)
    block = max(1, int(round(scale)))
    size = logical * block
    ink = (236, 236, 236) if dark else (28, 28, 28)
    alpha = 200 if wrapped else 105
    canvas = bytearray(size * size * 4)
    for row, pattern in enumerate(_WRAP_GLYPH):
        for col, pixel in enumerate(pattern):
            if pixel != "#":
                continue
            for dy in range(block):
                y = row * block + dy
                if y >= size:
                    continue
                for dx in range(block):
                    x = col * block + dx
                    if x >= size:
                        continue
                    start = (y * size + x) * 4
                    canvas[start : start + 4] = bytes((*ink, alpha))
    return _png_rgba(size, size, bytes(canvas))


def wrap_icon_photo(*, scale: float, wrapped: bool, dark: bool) -> tk.PhotoImage:
    encoded = base64.b64encode(wrap_icon_png(scale=scale, wrapped=wrapped, dark=dark))
    return tk.PhotoImage(data=encoded.decode("ascii"))


def _png_rgba(width: int, height: int, pixels: bytes) -> bytes:
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])

    def chunk(tag: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), 9)
    body = chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + body
