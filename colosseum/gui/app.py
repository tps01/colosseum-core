from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
import warnings
from pathlib import Path
from tkinter import filedialog
from typing import Any, Literal

from ._browser import (
    RunSnapshot,
    format_summary_text,
    load_run_snapshot,
)
from ._icon import apply_window_icon, init_windows_taskbar, wrap_icon_photo
from ._results import load_run_evidence
from ._results_ui import ResultsPanel, set_text
from ._run_browser_ui import RunBrowserPanel
from .run_worker import RunFinished, RunKind, RunRequest, RunWorker


def _pane_bg(root: Any, ctk: Any) -> str:  # noqa: ANN401
    try:
        return str(root._apply_appearance_mode(root.cget("fg_color")))
    except (AttributeError, tk.TclError, TypeError, ValueError):
        return "#2b2b2b" if str(ctk.get_appearance_mode()).lower() == "dark" else "#ebebeb"


def _make_paned(
    parent: Any,
    orient: Literal["horizontal", "vertical"],
    bg: str,
) -> tk.PanedWindow:
    return tk.PanedWindow(
        parent,
        orient=orient,
        sashwidth=6,
        sashrelief=tk.FLAT,
        sashpad=0,
        bd=0,
        relief=tk.FLAT,
        bg=bg,
        background=bg,
        borderwidth=0,
    )


def _set_initial_sashes(body: tk.PanedWindow) -> None:
    try:
        body.update_idletasks()
        body.sash_place(0, int(max(body.winfo_width(), 1) * 0.62), 1)
    except tk.TclError:
        pass


def ensure_display_available() -> None:
    if sys.platform == "win32":
        return
    # Host platform makes one branch unreachable; keep both for the other OS.
    if not os.environ.get("DISPLAY"):  # type: ignore[unused-ignore, unreachable]
        print(
            "Colosseum GUI requires a display. Set DISPLAY or use SSH X11 forwarding (ssh -X).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except tk.TclError as exc:
        print(f"Colosseum GUI cannot open a display: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _browse_file(title: str, filetypes: list[tuple[str, str]], initialdir: Path) -> str:
    selected = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
        initialdir=str(initialdir),
    )
    return selected or ""


class ColosseumApp:
    def __init__(self, ctk: Any) -> None:  # noqa: ANN401
        self._ctk = ctk
        self._root = ctk.CTk()
        self._root.title("Colosseum")
        apply_window_icon(self._root)
        self._root.geometry("1100x720")
        self._cwd = Path.cwd()
        self._worker = RunWorker(cwd=self._cwd)
        self._ui_events: queue.Queue[Any] = queue.Queue()
        self._test_path = ctk.StringVar(value="")
        self._suite_path = ctk.StringVar(value="")
        self._config_path = ctk.StringVar(value=os.environ.get("COLOSSEUM_BENCH_CONFIG", ""))
        self._parameters_path = ctk.StringVar(value="")
        self._metadata_path = ctk.StringVar(value=os.environ.get("COLOSSEUM_METADATA_PATH", ""))
        self._debug = ctk.BooleanVar(value=False)
        self._no_sleep = ctk.BooleanVar(value=False)
        self._status = ctk.StringVar(value="Ready")
        self._detail_generation = 0
        self._selected_run_dir: Path | None = None
        self._build_layout()
        self._runs.refresh()
        self._root.after(200, self._poll_worker)

    def run(self) -> None:
        self._root.mainloop()

    def _build_layout(self) -> None:
        ctk, root = self._ctk, self._root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)
        self._build_form()
        self._build_body(_pane_bg(root, ctk))
        ctk.CTkLabel(root, textvariable=self._status).grid(
            row=1,
            column=0,
            sticky="w",
            padx=12,
            pady=(0, 4),
        )

    def _build_form(self) -> None:
        ctk, root = self._ctk, self._root
        form = ctk.CTkFrame(root)
        form.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        form.grid_columnconfigure(1, weight=1)
        rows = (
            ("Test (.py)", self._test_path, [("Python", "*.py")]),
            ("Suite (.toml)", self._suite_path, [("TOML", "*.toml")]),
            ("Config", self._config_path, [("TOML", "*.toml"), ("All", "*.*")]),
            ("Parameters", self._parameters_path, [("TOML", "*.toml"), ("All", "*.*")]),
            # Separate globs. One "*.yaml;*.yml" pattern makes the Windows dialog ignore pwd.
            ("Metadata", self._metadata_path, [("YAML", "*.yaml"), ("YML", "*.yml"), ("All", "*.*")]),
        )
        for i, (label, var, fts) in enumerate(rows):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, padx=4, pady=2, sticky="w")
            ctk.CTkEntry(form, textvariable=var).grid(row=i, column=1, padx=4, pady=2, sticky="ew")
            ctk.CTkButton(
                form,
                text="Browse",
                width=80,
                command=lambda ft=fts, v=var: v.set(_browse_file("Select file", ft, self._cwd)),
            ).grid(row=i, column=2, padx=4)
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=len(rows), column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ctk.CTkButton(actions, text="Run test", command=self._run_test).grid(row=0, column=0, padx=4)
        ctk.CTkButton(actions, text="Run suite", command=self._run_suite).grid(row=0, column=1, padx=4)
        self._stop_btn = ctk.CTkButton(actions, text="Stop", state="disabled", command=self._stop_run)
        self._stop_btn.grid(row=0, column=2, padx=4)
        ctk.CTkCheckBox(actions, text="Debug", variable=self._debug).grid(row=0, column=3, padx=8)
        ctk.CTkCheckBox(actions, text="No sleep", variable=self._no_sleep).grid(
            row=0,
            column=4,
            padx=8,
        )

    def _build_log_tab(self, *, scale: float) -> None:
        ctk = self._ctk
        log_tab = self._tabs.tab("Log")
        log_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        self._log_text = ctk.CTkTextbox(log_tab, state="disabled", wrap="none")
        self._log_text.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self._log_wrapped = False
        dark = str(ctk.get_appearance_mode()).lower() != "light"
        self._log_wrap_icons = {
            False: wrap_icon_photo(scale=scale, wrapped=False, dark=dark),
            True: wrap_icon_photo(scale=scale, wrapped=True, dark=dark),
        }
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*not CTkImage.*")
            self._log_wrap_btn = ctk.CTkButton(
                self._log_text,
                text="",
                image=self._log_wrap_icons[False],
                width=18,
                height=18,
                fg_color="transparent",
                hover_color=("gray75", "gray30"),
                border_width=0,
                command=self._toggle_log_wrap,
            )
        self._log_wrap_btn.place(relx=1.0, rely=0.0, x=-4, y=4, anchor="ne")
        self._log_wrap_btn.lift()

    def _build_summary_tab(self) -> Any:  # noqa: ANN401
        ctk = self._ctk
        summary_tab = self._tabs.tab("Summary")
        summary_tab.grid_rowconfigure(0, weight=0)
        summary_tab.grid_rowconfigure(1, weight=1)
        summary_tab.grid_columnconfigure(0, weight=1)
        slot_list = ctk.CTkFrame(summary_tab, fg_color="transparent")
        slot_list.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        slot_list.grid_remove()
        self._summary_text = ctk.CTkTextbox(summary_tab, state="disabled")
        self._summary_text.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        return slot_list

    def _build_body(self, pane_bg: str) -> None:
        ctk, root = self._ctk, self._root
        body = _make_paned(root, tk.HORIZONTAL, pane_bg)
        body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        scale = float(ctk.ScalingTracker.get_widget_scaling(root))
        viewer = ctk.CTkFrame(body, width=620)
        viewer.grid_rowconfigure(1, weight=1)
        viewer.grid_columnconfigure(0, weight=1)
        viewer_bar = ctk.CTkFrame(viewer, fg_color="transparent")
        viewer_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ctk.CTkButton(
            viewer_bar,
            text="Open output folder",
            width=140,
            command=self._open_selected_folder,
        ).pack(side="left", padx=2)
        self._tabs = ctk.CTkTabview(viewer)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._tabs.add("Log")
        self._tabs.add("Summary")
        self._tabs.add("Results")
        self._build_log_tab(scale=scale)
        slot_list = self._build_summary_tab()
        self._results = ResultsPanel(
            ctk,
            self._tabs.tab("Results"),
            slot_list,
            selected_run_dir=lambda: self._selected_run_dir,
            on_select_run=self._select_run,
            set_status=self._status.set,
            set_clipboard=self._set_clipboard,
            focus_tab=lambda: self._tabs.set("Results"),
        )
        self._runs = RunBrowserPanel(
            ctk,
            body,
            cwd=self._cwd,
            events=self._ui_events,
            on_select_run=self._select_run,
        )
        runs_panel = self._runs.frame
        viewer.grid_propagate(False)
        runs_panel.grid_propagate(False)
        viewer_min = int(640 * scale)
        runs_min = int(360 * scale)
        root.minsize(viewer_min + runs_min + int(48 * scale), int(720 * scale))
        body.add(viewer, minsize=viewer_min, stretch="always")
        body.add(runs_panel, minsize=runs_min, stretch="always")
        self._root.after(100, lambda: _set_initial_sashes(body))

    def _set_clipboard(self, text: str) -> None:
        self._root.clipboard_clear()
        self._root.clipboard_append(text)

    def _config_value(self) -> str | None:
        v = self._config_path.get().strip()
        return v or None

    def _metadata_value(self) -> str | None:
        v = self._metadata_path.get().strip()
        return v or None

    def _parameters_value(self) -> str | None:
        v = self._parameters_path.get().strip()
        return v or None

    def _run_test(self) -> None:
        p = self._test_path.get().strip()
        if not p:
            return
        from colosseum.paths import absolute_path

        path = absolute_path(p)
        if path.is_file():
            self._start_run(
                RunRequest(
                    RunKind.TEST,
                    path,
                    self._config_value(),
                    self._metadata_value(),
                    self._debug.get(),
                    parameters_path=self._parameters_value(),
                    no_sleep=self._no_sleep.get(),
                ),
            )

    def _run_suite(self) -> None:
        p = self._suite_path.get().strip()
        if not p:
            return
        from colosseum.paths import absolute_path

        path = absolute_path(p)
        if path.is_file():
            self._start_run(
                RunRequest(
                    RunKind.SUITE,
                    path,
                    self._config_value(),
                    self._metadata_value(),
                    self._debug.get(),
                    parameters_path=self._parameters_value(),
                    no_sleep=self._no_sleep.get(),
                ),
            )

    def _start_run(self, request: RunRequest) -> None:
        if self._worker.is_running():
            return
        self._selected_run_dir = None
        set_text(self._log_text, "")
        set_text(self._summary_text, "")
        self._stop_btn.configure(state="normal")
        try:
            self._worker.start(request)
        except RuntimeError:
            self._stop_btn.configure(state="disabled")

    def _stop_run(self) -> None:
        self._worker.stop()

    def _toggle_log_wrap(self) -> None:
        self._log_wrapped = not self._log_wrapped
        self._log_text.configure(wrap="word" if self._log_wrapped else "none")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*not CTkImage.*")
            self._log_wrap_btn.configure(image=self._log_wrap_icons[self._log_wrapped])

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", line + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _select_run(self, run_dir: Path) -> None:
        self._selected_run_dir = run_dir
        self._detail_generation += 1
        gen = self._detail_generation
        set_text(self._log_text, f"Loading debug.log for {run_dir.name}...")
        set_text(self._summary_text, f"Loading summary for {run_dir.name}...")
        self._results.begin_load(run_dir)
        threading.Thread(
            target=lambda: self._ui_events.put(("run", gen, load_run_snapshot(run_dir))),
            daemon=True,
        ).start()
        threading.Thread(
            target=lambda: self._ui_events.put(("evidence", gen, load_run_evidence(run_dir))),
            daemon=True,
        ).start()

    def _apply_run_snapshot(self, snap: RunSnapshot) -> None:
        if self._selected_run_dir != snap.run_dir:
            return
        if snap.log_error:
            log = snap.log_error
        elif not snap.log_text:
            log = "debug.log is empty."
        else:
            log = snap.log_text if snap.log_text.endswith("\n") else snap.log_text + "\n"
        set_text(self._log_text, log)
        set_text(self._summary_text, format_summary_text(snap.summary))
        self._results.apply_summary(snap.summary)

    def _open_selected_folder(self) -> None:
        folder = self._selected_run_dir
        if folder is None or not folder.is_dir():
            self._status.set("No output folder selected")
            return
        self._open_path(folder)

    def _open_path(self, path: Path) -> None:
        target = path if path.is_dir() else path.parent
        if sys.platform == "win32":
            os.startfile(target)  # noqa: S606
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", str(target)])  # noqa: S603
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(target)])  # noqa: S603

    def _on_worker_log(self, payload: list[Any]) -> None:
        if self._selected_run_dir is None and self._worker.is_running():
            self._append_log(payload[0])

    def _on_worker_started(self, payload: list[Any]) -> None:
        self._selected_run_dir = None
        self._tabs.set("Log")
        self._append_log(f"--- Run started: {payload[0]} ---")
        self._status.set(f"Running: {payload[0]}")

    def _on_worker_error(self, payload: list[Any]) -> None:
        self._append_log(f"ERROR: {payload[0]}")
        self._stop_btn.configure(state="disabled")
        self._status.set("Run failed to start")

    def _on_worker_finished(self, payload: list[Any]) -> None:
        finished: RunFinished = payload[0]
        self._append_log(f"--- Run finished (exit {finished.exit_code}) ---")
        self._stop_btn.configure(state="disabled")
        self._status.set(
            f"Last run: {finished.run_dir}" if finished.run_dir else f"Finished (exit {finished.exit_code})",
        )
        self._runs.refresh()

    def _on_ui_browser(self, payload: list[Any]) -> None:
        self._runs.apply_snapshot(payload[0], payload[1])

    def _on_ui_run(self, payload: list[Any]) -> None:
        if payload[0] == self._detail_generation:
            self._apply_run_snapshot(payload[1])

    def _on_ui_evidence(self, payload: list[Any]) -> None:
        if payload[0] == self._detail_generation:
            self._results.apply_evidence(payload[1])

    def _drain_event_queue(
        self,
        events: queue.Queue[Any],
        handlers: dict[str, Any],
    ) -> None:
        while True:
            try:
                kind, *payload = events.get_nowait()
            except queue.Empty:
                break
            handler = handlers.get(kind)
            if handler is not None:
                handler(payload)

    def _poll_worker(self) -> None:
        self._drain_event_queue(
            self._worker.events,
            {
                "log": self._on_worker_log,
                "started": self._on_worker_started,
                "error": self._on_worker_error,
                "finished": self._on_worker_finished,
            },
        )
        self._drain_event_queue(
            self._ui_events,
            {
                "browser": self._on_ui_browser,
                "run": self._on_ui_run,
                "evidence": self._on_ui_evidence,
            },
        )
        self._root.after(200, self._poll_worker)


def main() -> None:
    ensure_display_available()
    try:
        import customtkinter as ctk
    except ImportError as exc:
        print(
            "Colosseum GUI requires customtkinter. Reinstall with: pip install --force-reinstall colosseum-core",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    init_windows_taskbar()
    ColosseumApp(ctk).run()
