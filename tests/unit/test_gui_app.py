"""Retained operator workflows using real Tk widgets when a display is available."""

from __future__ import annotations

import json
import time
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk
import pytest
from colosseum.gui._run_browser_ui import RunBrowserPanel
from colosseum.gui.app import ColosseumApp

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.gui
def test_log_summary_and_suite_navigation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(RunBrowserPanel, "refresh", lambda _self: None)
    try:
        app = ColosseumApp(ctk)
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    app._root.withdraw()
    try:
        assert list(app._tabs._tab_dict) == ["Log", "Summary"]
        slot = tmp_path / "slot-pass"
        slot.mkdir()
        (slot / "debug.log").write_text("slot evidence logged\n", encoding="utf-8")
        (slot / "summary.json").write_text(json.dumps({"overall_result": "PASS"}), encoding="utf-8")
        suite = tmp_path / "suite-pass"
        suite.mkdir()
        (suite / "debug.log").write_text("suite execution logged\n", encoding="utf-8")
        (suite / "summary.json").write_text(
            json.dumps(
                {
                    "overall_result": "PASS",
                    "all_slots": [
                        {
                            "phase": "test",
                            "overall_result": "PASS",
                            "script": "sample.py",
                            "output_directory": str(slot),
                            "repeat_index": 2,
                        },
                    ],
                },
            ),
            encoding="utf-8",
        )

        def wait_for_load() -> None:
            deadline = time.monotonic() + 5
            while "Loading" in app._summary_text.get("1.0", "end") and time.monotonic() < deadline:
                app._root.update()
                time.sleep(0.02)
            assert "Loading" not in app._summary_text.get("1.0", "end")

        app._select_run(suite)
        wait_for_load()
        assert "suite execution logged" in app._log_text.get("1.0", "end")
        assert "PASS" in app._summary_text.get("1.0", "end")
        assert len(app._slot_buttons) == 1
        assert "repeat=2" in app._slot_buttons[0].cget("text")
        app._slot_buttons[0].invoke()
        wait_for_load()
        assert app._selected_run_dir == slot
        assert "slot evidence logged" in app._log_text.get("1.0", "end")
        assert not app._slot_buttons
        app._append_log("live message")
        assert "live message" in app._log_text.get("1.0", "end")
        app._toggle_log_wrap()
        assert app._log_text._textbox.cget("wrap") == "word"
        app._toggle_log_wrap()
        assert app._log_text._textbox.cget("wrap") == "none"
    finally:
        app._root.destroy()
