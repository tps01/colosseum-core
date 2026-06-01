"""Optional GUI smoke test (skipped without display)."""

from __future__ import annotations

import os
import sys

import pytest


@pytest.mark.gui
def test_gui_display_probe() -> None:
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        pytest.skip("DISPLAY not set")
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except tk.TclError as exc:
        pytest.skip(f"display unavailable: {exc}")
