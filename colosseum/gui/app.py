from __future__ import annotations

import json
import os
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

from ..database.read_from_path import read_from_path
from ..output.runs import list_run_directories, read_summary_json
from .run_worker import RunFinished, RunKind, RunRequest, RunWorker

_CORE_DB_TABLES = (
    "measurements",
    "verifications",
    "commands",
    "events",
    "artifacts",
    "run_metadata",
)
_DB_CELL_MAX = 200

# Light/dark pairs for CTkButton ``text_color``.
_STATUS_BUTTON_COLORS: dict[str, tuple[str, str]] = {
    "PASS": ("#1a7f37", "#3fb950"),
    "FAIL": ("#cf222e", "#f85149"),
    "ERROR": ("#cf222e", "#f85149"),
    "NO TEST": ("#8250df", "#a371f7"),
    "INVALID": ("#bc4c00", "#db6d28"),
}

# Single foregrounds for CTkTextbox tags (readable on light and dark themes).
_STATUS_TAG_COLORS: dict[str, str] = {
    "PASS": "#2da44e",
    "FAIL": "#e5534b",
    "ERROR": "#e5534b",
    "NO TEST": "#8957e5",
    "INVALID": "#e16f24",
}


def _normalize_status(status: str) -> str:
    """Map stored status strings onto the GUI color vocabulary."""
    key = status.strip().upper().replace("-", " ").replace("_", " ")
    if key in {"NO TEST", "NOTEST"}:
        return "NO TEST"
    if key in {"FAILED", "FAIL"}:
        return "FAIL"
    return key


def ensure_display_available() -> None:
    if sys.platform == "win32":
        return
    if not os.environ.get("DISPLAY"):
        print(
            "Colosseum GUI requires a display. Set DISPLAY or use SSH X11 forwarding (ssh -X).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        import tkinter as tk
    except ImportError as exc:
        print(
            "Colosseum GUI requires tkinter (install the OS python3-tk package).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except tk.TclError as exc:
        print(f"Colosseum GUI cannot open a display: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    ensure_display_available()
    try:
        import customtkinter as ctk
    except ImportError as exc:
        print(
            "Colosseum GUI requires customtkinter, which should come with colosseum-core. "
            "Reinstall with: pip install --force-reinstall colosseum-core",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = ColosseumApp(ctk)
    app.run()


class ColosseumApp:
    def __init__(self, ctk: Any) -> None:  # noqa: ANN401
        self._ctk = ctk
        self._root = ctk.CTk()
        self._root.title("Colosseum")
        self._root.geometry("1000x700")
        self._root.minsize(800, 500)

        self._cwd = Path.cwd()
        self._worker = RunWorker(cwd=self._cwd)
        self._test_path = ctk.StringVar(value="")
        self._suite_path = ctk.StringVar(value="")
        self._config_path = ctk.StringVar(value=os.environ.get("COLOSSEUM_BENCH_CONFIG", ""))
        self._debug = ctk.BooleanVar(value=False)
        self._run_buttons: list[Any] = []
        self._selected_run_dir: Path | None = None
        self._db_table = ctk.StringVar(value=_CORE_DB_TABLES[0])

        self._build_layout()
        self._refresh_run_list()
        self._root.after(200, self._poll_worker)

    def run(self) -> None:
        self._root.mainloop()

    def _build_layout(self) -> None:
        ctk = self._ctk
        root = self._root

        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(1, weight=1)

        run_frame = ctk.CTkFrame(root)
        run_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        run_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(run_frame, text="Test (.py)").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        ctk.CTkEntry(run_frame, textvariable=self._test_path).grid(
            row=0, column=1, padx=4, pady=2, sticky="ew"
        )
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_test).grid(
            row=0, column=2, padx=4
        )
        ctk.CTkButton(run_frame, text="Run test", width=90, command=self._run_test).grid(
            row=0, column=3, padx=4
        )

        ctk.CTkLabel(run_frame, text="Suite (.toml)").grid(
            row=1, column=0, padx=4, pady=2, sticky="w"
        )
        ctk.CTkEntry(run_frame, textvariable=self._suite_path).grid(
            row=1, column=1, padx=4, pady=2, sticky="ew"
        )
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_suite).grid(
            row=1, column=2, padx=4
        )
        ctk.CTkButton(run_frame, text="Run suite", width=90, command=self._run_suite).grid(
            row=1, column=3, padx=4
        )

        ctk.CTkLabel(run_frame, text="Config").grid(row=2, column=0, padx=4, pady=2, sticky="w")
        ctk.CTkEntry(run_frame, textvariable=self._config_path).grid(
            row=2, column=1, padx=4, pady=2, sticky="ew"
        )
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_config).grid(
            row=2, column=2, padx=4
        )
        ctk.CTkCheckBox(run_frame, text="Debug", variable=self._debug).grid(
            row=2, column=3, padx=4, sticky="w"
        )

        self._stop_btn = ctk.CTkButton(
            run_frame, text="Stop", width=90, state="disabled", command=self._stop_run
        )
        self._stop_btn.grid(row=3, column=3, padx=4, pady=4, sticky="e")

        # Horizontal sash: log | results (user-resizable).
        body = self._make_paned(root, tk.HORIZONTAL)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        self._body_paned = body

        log_frame = ctk.CTkFrame(body, width=640)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self._left_tabs = ctk.CTkTabview(log_frame)
        self._left_tabs.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._left_tabs.add("Log")
        self._left_tabs.add("Database")

        log_tab = self._left_tabs.tab("Log")
        log_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        self._log_text = ctk.CTkTextbox(log_tab, state="disabled", wrap="none")
        self._log_text.grid(row=0, column=0, sticky="nsew")

        db_tab = self._left_tabs.tab("Database")
        db_tab.grid_rowconfigure(1, weight=1)
        db_tab.grid_columnconfigure(0, weight=1)
        db_controls = ctk.CTkFrame(db_tab, fg_color="transparent")
        db_controls.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        db_controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(db_controls, text="Table").grid(row=0, column=0, padx=(0, 4), sticky="w")
        self._db_table_menu = ctk.CTkOptionMenu(
            db_controls,
            variable=self._db_table,
            values=list(_CORE_DB_TABLES),
            command=self._on_db_table_changed,
        )
        self._db_table_menu.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(db_controls, text="Reload", width=80, command=self._reload_database).grid(
            row=0, column=2, padx=(4, 0)
        )
        self._db_text = ctk.CTkTextbox(db_tab, state="disabled", wrap="none")
        self._db_text.grid(row=1, column=0, sticky="nsew")
        self._configure_status_tags(self._db_text)
        self._db_text.configure(state="normal")
        self._db_text.insert("end", "Select a run to inspect execution.sqlite.")
        self._db_text.configure(state="disabled")

        # Vertical sash: run list | summary/verifications.
        results = self._make_paned(body, tk.VERTICAL)
        self._results_paned = results

        runs_frame = ctk.CTkFrame(results, height=140)
        runs_frame.grid_rowconfigure(1, weight=1)
        runs_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(runs_frame, text="Runs").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self._run_list = ctk.CTkScrollableFrame(runs_frame)
        self._run_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        ctk.CTkButton(runs_frame, text="Refresh runs", command=self._refresh_run_list).grid(
            row=2, column=0, padx=4, pady=4, sticky="ew"
        )

        detail_frame = ctk.CTkFrame(results)
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self._tabview = ctk.CTkTabview(detail_frame)
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._tabview.add("Summary")
        self._tabview.add("Verifications")
        self._summary_text = ctk.CTkTextbox(self._tabview.tab("Summary"), state="disabled")
        self._summary_text.pack(fill="both", expand=True)
        self._verify_text = ctk.CTkTextbox(self._tabview.tab("Verifications"), state="disabled")
        self._verify_text.pack(fill="both", expand=True)
        self._configure_status_tags(self._summary_text)
        self._configure_status_tags(self._verify_text)

        body.add(log_frame, minsize=240, stretch="always")
        body.add(results, minsize=220, stretch="always")
        results.add(runs_frame, minsize=100, stretch="always")
        results.add(detail_frame, minsize=160, stretch="always")
        # Prefer a wider log pane on first layout.
        self._root.after(50, lambda: self._set_initial_sashes(body, results))

    def _pane_chrome_color(self) -> str:
        """Match tk.PanedWindow chrome to the active CTk window background."""
        try:
            return str(self._root._apply_appearance_mode(self._root.cget("fg_color")))
        except (AttributeError, tk.TclError, TypeError, ValueError):
            mode = str(self._ctk.get_appearance_mode()).lower()
            return "#2b2b2b" if mode == "dark" else "#ebebeb"

    def _make_paned(self, parent: Any, orient: str) -> tk.PanedWindow:  # noqa: ANN401
        bg = self._pane_chrome_color()
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
            opaqueresize=True,
            showhandle=False,
        )

    def _set_initial_sashes(self, body: tk.PanedWindow, results: tk.PanedWindow) -> None:
        try:
            width = max(body.winfo_width(), 1)
            height = max(results.winfo_height(), 1)
            body.sash_place(0, int(width * 0.65), 1)
            results.sash_place(0, 1, int(height * 0.35))
        except tk.TclError:
            pass

    def _configure_status_tags(self, textbox: Any) -> None:  # noqa: ANN401
        for status, color in _STATUS_TAG_COLORS.items():
            textbox.tag_config(f"status_{status}", foreground=color)

    @staticmethod
    def _status_button_color(status: str) -> tuple[str, str] | str:
        normalized = _normalize_status(status)
        return _STATUS_BUTTON_COLORS.get(normalized, ("gray10", "gray90"))

    def _insert_status_token(self, textbox: Any, status: str) -> None:  # noqa: ANN401
        normalized = _normalize_status(status)
        tag = f"status_{normalized}" if normalized in _STATUS_TAG_COLORS else None
        textbox.insert("end", status, tag)

    def _browse_test(self) -> None:
        path = filedialog.askopenfilename(
            title="Select test script",
            filetypes=[("Python", "*.py"), ("All files", "*.*")],
        )
        if path:
            self._test_path.set(path)

    def _browse_suite(self) -> None:
        path = filedialog.askopenfilename(
            title="Select suite TOML",
            filetypes=[("TOML", "*.toml"), ("All files", "*.*")],
        )
        if path:
            self._suite_path.set(path)

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Select bench config",
            filetypes=[("TOML", "*.toml"), ("All files", "*.*")],
        )
        if path:
            self._config_path.set(path)

    def _config_value(self) -> str | None:
        value = self._config_path.get().strip()
        return value or None

    def _run_test(self) -> None:
        path_str = self._test_path.get().strip()
        if not path_str:
            return
        path = Path(path_str).resolve()
        if not path.is_file():
            return
        self._start_run(RunRequest(RunKind.TEST, path, self._config_value(), self._debug.get()))

    def _run_suite(self) -> None:
        path_str = self._suite_path.get().strip()
        if not path_str:
            return
        path = Path(path_str).resolve()
        if not path.is_file():
            return
        self._start_run(RunRequest(RunKind.SUITE, path, self._config_value(), self._debug.get()))

    def _start_run(self, request: RunRequest) -> None:
        if self._worker.is_running():
            return
        self._clear_log()
        self._stop_btn.configure(state="normal")
        try:
            self._worker.start(request)
        except RuntimeError:
            self._stop_btn.configure(state="disabled")

    def _stop_run(self) -> None:
        self._worker.stop()

    def _clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", line + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _poll_worker(self) -> None:
        while True:
            try:
                event = self._worker.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "log":
                self._append_log(event[1])
            elif kind == "started":
                self._append_log(f"--- Run started: {event[1]} ---")
            elif kind == "error":
                self._append_log(f"ERROR: {event[1]}")
                self._stop_btn.configure(state="disabled")
            elif kind == "finished":
                finished: RunFinished = event[1]
                self._append_log(f"--- Run finished (exit {finished.exit_code}) ---")
                self._stop_btn.configure(state="disabled")
                self._refresh_run_list()
                if finished.run_dir is not None:
                    self._select_run(finished.run_dir)

        self._root.after(200, self._poll_worker)

    def _run_status_label(self, run_dir: Path) -> str:
        summary = read_summary_json(run_dir)
        if summary is None:
            return "incomplete"
        return str(summary.get("overall_result", "?"))

    def _refresh_run_list(self) -> None:
        for btn in self._run_buttons:
            btn.destroy()
        self._run_buttons.clear()
        ctk = self._ctk

        for run_dir in list_run_directories(self._cwd):
            status = self._run_status_label(run_dir)
            label = f"{run_dir.name}  [{status}]"
            btn = ctk.CTkButton(
                self._run_list,
                text=label,
                anchor="w",
                fg_color="transparent",
                text_color=self._status_button_color(status),
                hover_color=("gray85", "gray25"),
                command=lambda rd=run_dir: self._select_run(rd),
            )
            btn.pack(fill="x", pady=1)
            self._run_buttons.append(btn)

    def _select_run(self, run_dir: Path) -> None:
        self._selected_run_dir = run_dir
        self._show_log(run_dir)
        self._show_database(run_dir)
        self._show_summary(run_dir)
        self._show_verifications(run_dir)

    def _on_db_table_changed(self, _choice: str) -> None:
        self._reload_database()

    def _reload_database(self) -> None:
        if self._selected_run_dir is not None:
            self._show_database(self._selected_run_dir)

    @staticmethod
    def _format_db_cell(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            text = str(value)
        text = text.replace("\n", "\\n")
        if len(text) > _DB_CELL_MAX:
            return text[: _DB_CELL_MAX - 3] + "..."
        return text

    def _show_database(self, run_dir: Path) -> None:
        db_path = run_dir / "execution.sqlite"
        table = self._db_table.get().strip() or _CORE_DB_TABLES[0]
        self._db_text.configure(state="normal")
        self._db_text.delete("1.0", "end")
        if not db_path.is_file():
            self._db_text.insert("end", f"No execution.sqlite in {run_dir.name}.")
            self._db_text.configure(state="disabled")
            return
        try:
            with read_from_path(db_path) as reader:
                rows = reader.read_table(table)
        except (OSError, FileNotFoundError, ValueError) as exc:
            self._db_text.insert("end", f"Cannot read {table}: {exc}")
            self._db_text.configure(state="disabled")
            return

        noun = "row" if len(rows) == 1 else "rows"
        self._db_text.insert("end", f"{run_dir.name} / {table}  ({len(rows)} {noun})\n")
        if not rows:
            self._db_text.insert("end", "(empty)\n")
            self._db_text.configure(state="disabled")
            return

        columns = list(rows[0].keys())
        self._db_text.insert("end", " | ".join(columns) + "\n")
        self._db_text.insert("end", "-+-".join("-" * max(len(c), 3) for c in columns) + "\n")
        for row in rows:
            for index, col in enumerate(columns):
                if index:
                    self._db_text.insert("end", " | ")
                cell = self._format_db_cell(row.get(col))
                if col == "status" and _normalize_status(cell) in _STATUS_TAG_COLORS:
                    self._insert_status_token(self._db_text, cell)
                else:
                    self._db_text.insert("end", cell)
            self._db_text.insert("end", "\n")
        self._db_text.see("1.0")
        self._db_text.configure(state="disabled")

    def _show_log(self, run_dir: Path) -> None:
        log_path = run_dir / "debug.log"
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        if not log_path.is_file():
            self._log_text.insert("end", f"No debug.log in {run_dir.name}.")
        else:
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self._log_text.insert("end", f"Cannot read debug.log: {exc}")
            else:
                if text:
                    self._log_text.insert("end", text)
                    if not text.endswith("\n"):
                        self._log_text.insert("end", "\n")
                    self._log_text.see("1.0")
                else:
                    self._log_text.insert("end", f"{log_path.name} is empty.")
        self._log_text.configure(state="disabled")

    def _show_summary(self, run_dir: Path) -> None:
        summary = read_summary_json(run_dir)
        self._summary_text.configure(state="normal")
        self._summary_text.delete("1.0", "end")
        if summary is None:
            self._summary_text.insert("end", "No summary.json (run incomplete or in progress).")
        else:
            overall = str(summary.get("overall_result", "?"))
            self._summary_text.insert("end", "Overall: ")
            self._insert_status_token(self._summary_text, overall)
            self._summary_text.insert("end", f" (exit {summary.get('exit_code')})\n")
            lines = [
                f"Test case: {summary.get('test_case')}",
                f"Suite: {summary.get('suite')}",
                f"Config: {summary.get('config_path')}",
                f"Output: {summary.get('output_directory')}",
                f"End time: {summary.get('end_time_utc')}",
                f"Measurements: {summary.get('measurement_count')}",
                (
                    "Verifications (required): "
                    f"{summary.get('verification_counts', {}).get('required', {})}"
                ),
                (
                    "Verifications (optional): "
                    f"{summary.get('verification_counts', {}).get('optional', {})}"
                ),
            ]
            self._summary_text.insert("end", "\n".join(lines))
            failed = summary.get("failed_required_verifications") or []
            if failed:
                self._summary_text.insert("end", "\n\nFailed required verifications:\n")
                for row in failed:
                    domain = row.get("domain")
                    command = row.get("command")
                    key = row.get("key")
                    message = row.get("message")
                    status = str(row.get("status") or "FAIL")
                    self._summary_text.insert("end", "  - ")
                    self._insert_status_token(self._summary_text, status)
                    self._summary_text.insert(
                        "end", f" {domain}.{command} key={key}: {message}\n"
                    )
        self._summary_text.configure(state="disabled")

    def _show_verifications(self, run_dir: Path) -> None:
        db_path = run_dir / "execution.sqlite"
        self._verify_text.configure(state="normal")
        self._verify_text.delete("1.0", "end")
        if not db_path.is_file():
            self._verify_text.insert("end", "No execution.sqlite.")
            self._verify_text.configure(state="disabled")
            return
        try:
            with read_from_path(db_path) as reader:
                rows = reader.read_verifications()
        except (OSError, FileNotFoundError) as exc:
            self._verify_text.insert("end", f"Cannot read database: {exc}")
            self._verify_text.configure(state="disabled")
            return

        if not rows:
            self._verify_text.insert("end", "No verifications recorded.")
        else:
            for row in rows:
                opt = "optional" if row.optional else "required"
                prefix = "FAIL" if row.status == "FAIL" and not row.optional else row.status
                self._verify_text.insert("end", "[")
                self._insert_status_token(self._verify_text, str(prefix))
                line = f"] {row.domain}.{row.command} key={row.key} ({opt})"
                if row.message:
                    line += f": {row.message}"
                self._verify_text.insert("end", line + "\n")
        self._verify_text.configure(state="disabled")
