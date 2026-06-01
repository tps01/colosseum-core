from __future__ import annotations

import os
import queue
import sys
from pathlib import Path
from tkinter import filedialog
from typing import Any

from ..database.read_from_path import read_from_path
from ..output.runs import list_run_directories, read_summary_json
from .run_worker import RunFinished, RunKind, RunRequest, RunWorker


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
            "Colosseum GUI requires customtkinter. Reinstall colosseum.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = ColosseumApp(ctk)
    app.run()


class ColosseumApp:
    def __init__(self, ctk: Any) -> None:
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
        self._verbose = ctk.BooleanVar(value=False)
        self._run_buttons: list[Any] = []

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
        ctk.CTkEntry(run_frame, textvariable=self._test_path).grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_test).grid(row=0, column=2, padx=4)
        ctk.CTkButton(run_frame, text="Run test", width=90, command=self._run_test).grid(row=0, column=3, padx=4)

        ctk.CTkLabel(run_frame, text="Suite (.toml)").grid(row=1, column=0, padx=4, pady=2, sticky="w")
        ctk.CTkEntry(run_frame, textvariable=self._suite_path).grid(row=1, column=1, padx=4, pady=2, sticky="ew")
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_suite).grid(row=1, column=2, padx=4)
        ctk.CTkButton(run_frame, text="Run suite", width=90, command=self._run_suite).grid(row=1, column=3, padx=4)

        ctk.CTkLabel(run_frame, text="Config").grid(row=2, column=0, padx=4, pady=2, sticky="w")
        ctk.CTkEntry(run_frame, textvariable=self._config_path).grid(row=2, column=1, padx=4, pady=2, sticky="ew")
        ctk.CTkButton(run_frame, text="Browse", width=80, command=self._browse_config).grid(row=2, column=2, padx=4)
        ctk.CTkCheckBox(run_frame, text="Verbose", variable=self._verbose).grid(row=2, column=3, padx=4, sticky="w")

        self._stop_btn = ctk.CTkButton(run_frame, text="Stop", width=90, state="disabled", command=self._stop_run)
        self._stop_btn.grid(row=3, column=3, padx=4, pady=4, sticky="e")

        body = ctk.CTkFrame(root)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        log_frame = ctk.CTkFrame(body)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="Log (debug.log)").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self._log_text = ctk.CTkTextbox(log_frame, state="disabled", wrap="none")
        self._log_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        results_frame = ctk.CTkFrame(body)
        results_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        results_frame.grid_rowconfigure(1, weight=1)
        results_frame.grid_rowconfigure(2, weight=2)
        results_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(results_frame, text="Runs").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self._run_list = ctk.CTkScrollableFrame(results_frame, height=120)
        self._run_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self._tabview = ctk.CTkTabview(results_frame)
        self._tabview.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        self._tabview.add("Summary")
        self._tabview.add("Verifications")
        self._summary_text = ctk.CTkTextbox(self._tabview.tab("Summary"), state="disabled")
        self._summary_text.pack(fill="both", expand=True)
        self._verify_text = ctk.CTkTextbox(self._tabview.tab("Verifications"), state="disabled")
        self._verify_text.pack(fill="both", expand=True)

        ctk.CTkButton(results_frame, text="Refresh runs", command=self._refresh_run_list).grid(
            row=3, column=0, padx=4, pady=4, sticky="ew"
        )

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
        self._start_run(RunRequest(RunKind.TEST, path, self._config_value(), self._verbose.get()))

    def _run_suite(self) -> None:
        path_str = self._suite_path.get().strip()
        if not path_str:
            return
        path = Path(path_str).resolve()
        if not path.is_file():
            return
        self._start_run(RunRequest(RunKind.SUITE, path, self._config_value(), self._verbose.get()))

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
            label = f"{run_dir.name}  [{self._run_status_label(run_dir)}]"
            btn = ctk.CTkButton(
                self._run_list,
                text=label,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray25"),
                command=lambda rd=run_dir: self._select_run(rd),
            )
            btn.pack(fill="x", pady=1)
            self._run_buttons.append(btn)

    def _select_run(self, run_dir: Path) -> None:
        self._show_summary(run_dir)
        self._show_verifications(run_dir)

    def _show_summary(self, run_dir: Path) -> None:
        summary = read_summary_json(run_dir)
        self._summary_text.configure(state="normal")
        self._summary_text.delete("1.0", "end")
        if summary is None:
            self._summary_text.insert("end", "No summary.json (run incomplete or in progress).")
        else:
            lines = [
                f"Overall: {summary.get('overall_result')} (exit {summary.get('exit_code')})",
                f"Test case: {summary.get('test_case')}",
                f"Suite: {summary.get('suite')}",
                f"Config: {summary.get('config_path')}",
                f"Output: {summary.get('output_directory')}",
                f"End time: {summary.get('end_time_utc')}",
                f"Measurements: {summary.get('measurement_count')}",
                f"Verifications (required): {summary.get('verification_counts', {}).get('required', {})}",
                f"Verifications (optional): {summary.get('verification_counts', {}).get('optional', {})}",
            ]
            failed = summary.get("failed_required_verifications") or []
            if failed:
                lines.append("")
                lines.append("Failed required verifications:")
                for row in failed:
                    lines.append(
                        f"  - {row.get('domain')}.{row.get('command')} key={row.get('key')}: {row.get('message')}"
                    )
            self._summary_text.insert("end", "\n".join(lines))
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
                line = f"[{prefix}] {row.domain}.{row.command} key={row.key} ({opt})"
                if row.message:
                    line += f": {row.message}"
                self._verify_text.insert("end", line + "\n")
        self._verify_text.configure(state="disabled")
