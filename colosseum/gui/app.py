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
    RunBrowserRow,
    RunBrowserSnapshot,
    RunSnapshot,
    display_status,
    format_summary_text,
    load_run_browser_snapshot,
    load_run_snapshot,
    suite_run_dirs,
)
from ._evidence import links_for_row
from ._icon import apply_window_icon, init_windows_taskbar, wrap_icon_photo
from ._plots import explicit_xy, limit_fraction, limit_view, reduce_xy
from ._results import detail_text, filter_rows, load_run_evidence, page_size, units_for
from .run_worker import RunFinished, RunKind, RunRequest, RunWorker

_PURPLE = ("#8250df", "#a371f7")
_STATUS_BUTTON_COLORS: dict[str, tuple[str, str]] = {
    "PASS": ("#1a7f37", "#3fb950"),
    "FAIL": ("#cf222e", "#f85149"),
    "ERROR": _PURPLE,
    "INCOMPLETE": _PURPLE,
    "NO TEST": _PURPLE,
    "INVALID": ("#bc4c00", "#db6d28"),
}


def _normalize_status(status: str) -> str:
    key = status.strip().upper().replace("-", " ").replace("_", " ")
    if key in {"NO TEST", "NOTEST"}:
        return "NO TEST"
    if key in {"FAILED", "FAIL"}:
        return "FAIL"
    return key


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
        parent, orient=orient, sashwidth=6, sashrelief=tk.FLAT, sashpad=0,
        bd=0, relief=tk.FLAT, bg=bg, background=bg, borderwidth=0,
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
    if not os.environ.get("DISPLAY"):
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


def _place_limit_label(
    canvas: tk.Canvas,
    x: float,
    y: float,
    text: str,
    width: int,
    occupied: list[tuple[float, float]],
) -> None:
    """Put a value above its mark, shifting up when a neighbor already owns that space."""
    import tkinter.font as tkfont

    half = tkfont.nametofont("TkDefaultFont").measure(text) / 2 + 6
    center = min(max(x, half + 2), max(half + 2, width - half - 2))
    top = y
    for _ in range(3):
        if all(abs(center - other_x) >= half + other_half for other_x, other_half in occupied):
            break
        top -= 16
    canvas.create_text(center, top, text=text, anchor="s", fill="#cccccc")
    occupied.append((center, half))


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
        self._run_widgets: dict[tuple[str, Path], Any] = {}
        self._browser_snapshot = RunBrowserSnapshot(rows=[])
        self._browser_generation = 0
        self._detail_generation = 0
        self._expanded_output_dirs: set[Path] = set()
        self._expanded_suites: set[Path] = set()
        self._selected_run_dir: Path | None = None
        self._evidence_rows: list[Any] = []
        self._evidence_error: str | None = None
        self._import_origin: str | None = None
        self._filtered_rows: list[Any] = []
        self._selected_result: Any = None
        self._result_page = 0
        self._failures_only = True
        self._plot_pixels: dict[int, tuple[int, int]] = {}
        self._slot_buttons: list[Any] = []
        self._results_notice: str | None = None
        self._build_layout()
        self._refresh_runs()
        self._root.after(200, self._poll_worker)

    def run(self) -> None:
        self._root.mainloop()

    def _build_layout(self) -> None:
        ctk, root = self._ctk, self._root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)
        pane_bg = _pane_bg(root, ctk)

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
                form, text="Browse", width=80,
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
            row=0, column=4, padx=8,
        )

        body = _make_paned(root, tk.HORIZONTAL, pane_bg)
        body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        scale = float(ctk.ScalingTracker.get_widget_scaling(root))
        viewer = ctk.CTkFrame(body, width=620)
        viewer.grid_rowconfigure(1, weight=1)
        viewer.grid_columnconfigure(0, weight=1)
        viewer_bar = ctk.CTkFrame(viewer, fg_color="transparent")
        viewer_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ctk.CTkButton(
            viewer_bar, text="Open output folder", width=140, command=self._open_selected_folder,
        ).pack(side="left", padx=2)
        self._tabs = ctk.CTkTabview(viewer)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._tabs.add("Log")
        self._tabs.add("Summary")
        self._tabs.add("Results")
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
        summary_tab = self._tabs.tab("Summary")
        summary_tab.grid_rowconfigure(0, weight=0)
        summary_tab.grid_rowconfigure(1, weight=1)
        summary_tab.grid_columnconfigure(0, weight=1)
        self._slot_list = ctk.CTkFrame(summary_tab, fg_color="transparent")
        self._slot_list.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        self._slot_list.grid_remove()
        self._summary_text = ctk.CTkTextbox(summary_tab, state="disabled")
        self._summary_text.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self._build_results_tab()

        runs_panel = ctk.CTkFrame(body, width=280)
        runs_panel.grid_rowconfigure(1, weight=1)
        runs_panel.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(runs_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 2))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Runs").grid(row=0, column=0, sticky="w")
        ctrls = ctk.CTkFrame(header, fg_color="transparent")
        ctrls.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(ctrls, text="Refresh", width=70, command=self._refresh_runs).grid(row=0, column=0, padx=2)
        ctk.CTkButton(ctrls, text="Expand", width=70, command=self._expand_all_output_dirs).grid(row=0, column=1, padx=2)
        ctk.CTkButton(ctrls, text="Collapse", width=70, command=self._collapse_all_output_dirs).grid(row=0, column=2, padx=2)
        self._run_list = ctk.CTkScrollableFrame(runs_panel)
        self._run_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))

        viewer.grid_propagate(False)
        runs_panel.grid_propagate(False)
        viewer_min = int(640 * scale)
        runs_min = int(360 * scale)
        root.minsize(viewer_min + runs_min + int(48 * scale), int(720 * scale))
        body.add(viewer, minsize=viewer_min, stretch="always")
        body.add(runs_panel, minsize=runs_min, stretch="always")
        self._root.after(100, lambda: _set_initial_sashes(body))

        ctk.CTkLabel(root, textvariable=self._status).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))

    @staticmethod
    def _set_text(textbox: Any, text: str) -> None:  # noqa: ANN401
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        if text:
            textbox.insert("end", text)
            textbox.see("1.0")
        textbox.configure(state="disabled")

    def _build_results_tab(self) -> None:
        ctk = self._ctk
        tab = self._tabs.tab("Results")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=0)
        tab.grid_rowconfigure(3, weight=0)
        tab.grid_rowconfigure(4, weight=0)
        filters = ctk.CTkFrame(tab, fg_color="transparent")
        filters.grid(row=0, column=0, sticky="ew", pady=(2, 2))
        ctk.CTkButton(filters, text="Failures", width=70, command=self._show_failures).pack(side="left", padx=2)
        ctk.CTkButton(filters, text="All results", width=90, command=self._show_all_results).pack(side="left", padx=2)
        ctk.CTkButton(filters, text="Copy", width=60, command=self._copy_result).pack(side="left", padx=2)
        self._result_page_label = ctk.CTkLabel(filters, text="", width=120)
        self._result_page_label.pack(side="left", padx=4)
        ctk.CTkButton(filters, text="Prev", width=50, command=self._result_prev).pack(side="left", padx=2)
        ctk.CTkButton(filters, text="Next", width=50, command=self._result_next).pack(side="left", padx=2)
        self._result_list = ctk.CTkScrollableFrame(tab)
        self._result_list.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self._result_buttons: list[Any] = []
        self._limit_canvas = tk.Canvas(tab, height=92, highlightthickness=0, bg="#1e1e1e")
        self._limit_canvas.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        self._limit_canvas.grid_remove()
        self._xy_canvas = tk.Canvas(tab, height=160, highlightthickness=0, bg="#1e1e1e")
        self._xy_canvas.grid(row=3, column=0, sticky="nsew", padx=2, pady=2)
        self._xy_canvas.grid_remove()
        self._limit_canvas.bind("<Configure>", self._on_plot_configure)
        self._xy_canvas.bind("<Configure>", self._on_plot_configure)
        self._result_detail = ctk.CTkTextbox(tab, height=140, state="disabled")
        self._result_detail.grid(row=4, column=0, sticky="ew", padx=2, pady=2)
        self._result_detail.grid_remove()

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
            self._start_run(RunRequest(
                RunKind.TEST, path, self._config_value(), self._metadata_value(), self._debug.get(),
                parameters_path=self._parameters_value(),
                no_sleep=self._no_sleep.get(),
            ))

    def _run_suite(self) -> None:
        p = self._suite_path.get().strip()
        if not p:
            return
        from colosseum.paths import absolute_path

        path = absolute_path(p)
        if path.is_file():
            self._start_run(RunRequest(
                RunKind.SUITE, path, self._config_value(), self._metadata_value(), self._debug.get(),
                parameters_path=self._parameters_value(),
                no_sleep=self._no_sleep.get(),
            ))

    def _start_run(self, request: RunRequest) -> None:
        if self._worker.is_running():
            return
        self._selected_run_dir = None
        self._set_text(self._log_text, "")
        self._set_text(self._summary_text, "")
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

    def _status_button_color(self, status: str) -> tuple[str, str] | str:
        return _STATUS_BUTTON_COLORS.get(_normalize_status(status), "gray40")

    def _outputs_dir_label(self, outputs_dir: Path) -> str:
        try:
            return str(outputs_dir.relative_to(self._cwd))
        except ValueError:
            return str(outputs_dir)

    def _run_list_label(self, row: RunBrowserRow) -> str:
        return f"{row.entry.path.name}  [{row.status}]"

    def _refresh_runs(self) -> None:
        self._browser_generation += 1
        gen = self._browser_generation
        threading.Thread(target=lambda: self._ui_events.put(("browser", gen, load_run_browser_snapshot(self._cwd))), daemon=True).start()

    def _expand_all_output_dirs(self) -> None:
        self._expanded_output_dirs = set(self._browser_snapshot.output_dirs)
        self._expanded_suites = suite_run_dirs(self._browser_snapshot.rows)
        self._render_run_list()

    def _collapse_all_output_dirs(self) -> None:
        self._expanded_output_dirs.clear()
        self._expanded_suites.clear()
        self._render_run_list()

    def _toggle_outputs_dir(self, outputs_dir: Path) -> None:
        if outputs_dir in self._expanded_output_dirs:
            self._expanded_output_dirs.remove(outputs_dir)
        else:
            self._expanded_output_dirs.add(outputs_dir)
        self._render_run_list()

    def _toggle_suite(self, run_dir: Path) -> None:
        if run_dir in self._expanded_suites:
            self._expanded_suites.remove(run_dir)
        else:
            self._expanded_suites.add(run_dir)
        self._render_run_list()
        self._select_run(run_dir)

    def _render_run_list(self) -> None:
        for w in self._run_widgets.values():
            w.pack_forget()
        ctk, rows = self._ctk, self._browser_snapshot.rows
        grouped = len(self._browser_snapshot.output_dirs) > 1
        active: set[tuple[str, Path]] = set()
        if grouped:
            by_dir: dict[Path, list[RunBrowserRow]] = {}
            for row in rows:
                by_dir.setdefault(row.entry.outputs_dir, []).append(row)
            for outputs_dir in sorted(by_dir, key=lambda d: max(r.mtime for r in by_dir[d]), reverse=True):
                exp = outputs_dir in self._expanded_output_dirs
                key = ("outputs", outputs_dir)
                active.add(key)
                hdr = self._run_widgets.get(key) or ctk.CTkButton(
                    self._run_list, anchor="w", fg_color="transparent", hover_color=("gray85", "gray25"),
                    command=lambda od=outputs_dir: self._toggle_outputs_dir(od),
                )
                self._run_widgets[key] = hdr
                hdr.configure(text=f"{'[-]' if exp else '[+]'} {self._outputs_dir_label(outputs_dir)}")
                hdr.pack(fill="x", pady=(3, 1))
                if exp:
                    for row in by_dir[outputs_dir]:
                        self._add_run_button(row, level=1, active=active)
        else:
            for row in rows:
                self._add_run_button(row, level=0, active=active)
        for key, w in list(self._run_widgets.items()):
            if key not in active:
                w.destroy()
                del self._run_widgets[key]

    def _add_run_button(
        self,
        row: RunBrowserRow,
        *,
        level: int,
        active: set[tuple[str, Path]],
    ) -> None:
        run_dir = row.entry.path
        if row.children:
            key = ("suite", run_dir)
            active.add(key)
            expanded = run_dir in self._expanded_suites
            header = self._run_widgets.get(key) or self._suite_header(run_dir)
            self._run_widgets[key] = header
            mark = "[-]" if expanded else "[+]"
            header._mark.configure(text=mark, text_color=("gray10", "white"))
            header._name.configure(
                text=self._run_list_label(row),
                text_color=self._status_button_color(row.status),
            )
            header.pack(fill="x", padx=(18 * level, 0), pady=1)
            if expanded:
                for child in row.children:
                    self._add_run_button(child, level=level + 1, active=active)
            return
        key = ("run", run_dir)
        active.add(key)
        btn = self._run_widgets.get(key) or self._ctk.CTkButton(
            self._run_list, anchor="w", fg_color="transparent", hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._select_run(rd),
        )
        self._run_widgets[key] = btn
        btn.configure(text=self._run_list_label(row), text_color=self._status_button_color(row.status))
        btn.pack(fill="x", padx=(18 * level, 0), pady=1)

    def _suite_header(self, run_dir: Path) -> Any:  # noqa: ANN401
        """Expand marker stays white. The suite name keeps the result color."""
        ctk = self._ctk
        frame = ctk.CTkFrame(self._run_list, fg_color="transparent")
        mark = ctk.CTkButton(
            frame, text="[+]", width=36, anchor="w",
            fg_color="transparent", text_color=("gray10", "white"),
            hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._toggle_suite(rd),
        )
        name = ctk.CTkButton(
            frame, text="", anchor="w", fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._toggle_suite(rd),
        )
        mark.pack(side="left")
        name.pack(side="left", fill="x", expand=True)
        frame._mark = mark
        frame._name = name
        return frame

    def _select_run(self, run_dir: Path) -> None:
        self._selected_run_dir = run_dir
        self._selected_result = None
        self._evidence_rows = []
        self._filtered_rows = []
        self._evidence_error = None
        self._results_notice = f"Loading results for {run_dir.name}..."
        self._detail_generation += 1
        gen = self._detail_generation
        self._set_text(self._log_text, f"Loading debug.log for {run_dir.name}...")
        self._set_text(self._summary_text, f"Loading summary for {run_dir.name}...")
        self._clear_slot_buttons()
        self._hide_result_detail()
        self._render_result_rows()
        threading.Thread(
            target=lambda: self._ui_events.put(("run", gen, load_run_snapshot(run_dir))), daemon=True,
        ).start()
        threading.Thread(
            target=lambda: self._ui_events.put(("evidence", gen, load_run_evidence(run_dir))), daemon=True,
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
        self._set_text(self._log_text, log)
        self._set_text(self._summary_text, format_summary_text(snap.summary))
        self._render_slots(snap.summary)
        status = display_status(snap.summary)
        self._failures_only = status in {"FAIL", "ERROR"}
        self._result_page = 0
        self._apply_result_filter()

    def _apply_evidence(self, generation: int, loaded: Any) -> None:  # noqa: ANN401
        if generation != self._detail_generation:
            return
        self._results_notice = None
        self._evidence_rows = list(loaded.rows)
        self._evidence_error = loaded.error
        self._import_origin = loaded.import_origin
        self._apply_result_filter()

    def _render_slots(self, summary: dict[str, Any] | None) -> None:
        self._clear_slot_buttons()
        slots = []
        if isinstance(summary, dict):
            raw = summary.get("all_slots") or summary.get("test_slots") or []
            slots = [slot for slot in raw if isinstance(slot, dict)]
        if not slots:
            self._slot_list.grid_remove()
            return
        self._slot_list.grid()
        for slot in slots:
            label = (
                f"{slot.get('phase')} [{slot.get('overall_result')}] "
                f"{Path(str(slot.get('script') or '')).name}"
            )
            repeat = slot.get("repeat_index")
            if repeat is not None:
                label += f" repeat={repeat}"
            cycle = slot.get("cycle_index")
            if cycle is not None:
                label += f" cycle={cycle}"
            folder = Path(str(slot.get("output_directory") or ""))
            button = self._ctk.CTkButton(
                self._slot_list, text=label, anchor="w", fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda path=folder: self._select_slot(path),
            )
            button.pack(fill="x", pady=1)
            self._slot_buttons.append(button)

    def _clear_slot_buttons(self) -> None:
        for button in self._slot_buttons:
            button.destroy()
        self._slot_buttons = []
        self._slot_list.grid_remove()

    def _select_slot(self, folder: Path) -> None:
        if folder.is_dir():
            self._select_run(folder)

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

    def _show_failures(self) -> None:
        self._failures_only = True
        self._result_page = 0
        self._apply_result_filter()
        self._tabs.set("Results")

    def _show_all_results(self) -> None:
        self._failures_only = False
        self._result_page = 0
        self._apply_result_filter()
        self._tabs.set("Results")

    def _result_prev(self) -> None:
        if self._result_page > 0:
            self._result_page -= 1
            self._render_result_rows()

    def _result_next(self) -> None:
        self._result_page += 1
        self._render_result_rows()

    def _apply_result_filter(self) -> None:
        self._filtered_rows = filter_rows(
            self._evidence_rows,
            failures_only=self._failures_only,
        )
        if self._selected_result not in self._filtered_rows:
            self._selected_result = self._filtered_rows[0] if self._filtered_rows else None
        self._render_result_rows()
        if self._selected_result is not None:
            self._show_result(self._selected_result)
        else:
            self._hide_result_detail()

    def _results_empty_message(self) -> str:
        if self._results_notice:
            return self._results_notice
        if self._evidence_error:
            return self._evidence_error
        if self._evidence_rows:
            return "No results match this filter."
        if self._selected_run_dir is None:
            return "Select a run to see its results."
        return "This run has no recorded results."

    def _render_result_rows(self) -> None:
        for button in self._result_buttons:
            button.destroy()
        self._result_buttons = []
        size = page_size()
        start = self._result_page * size
        window = self._filtered_rows[start : start + size]
        if start and not window:
            self._result_page = 0
            start = 0
            window = self._filtered_rows[:size]
        total = len(self._filtered_rows)
        if total:
            self._result_page_label.configure(
                text=f"{start + 1}-{start + len(window)} of {total}",
            )
        else:
            self._result_page_label.configure(text="")
            note = self._ctk.CTkLabel(
                self._result_list,
                text=self._results_empty_message(),
                anchor="w",
                justify="left",
                wraplength=420,
            )
            note.pack(fill="x", padx=4, pady=6)
            self._result_buttons.append(note)
            return
        for row in window:
            label = f"{row.status}  {row.step or row.key}  {row.actual}  {row.comparison}"
            button = self._ctk.CTkButton(
                self._result_list, text=label, anchor="w", fg_color="transparent",
                text_color=self._status_button_color(row.status),
                hover_color=("gray85", "gray25"),
                command=lambda item=row: self._show_result(item),
            )
            button.pack(fill="x", pady=1)
            self._result_buttons.append(button)

    def _show_result(self, row: Any) -> None:  # noqa: ANN401
        self._selected_result = row
        units = units_for(row, self._evidence_rows)
        self._set_text(self._result_detail, detail_text(row, units=units))
        self._result_detail.grid()
        has_limit = limit_view(
            compare_op=row.compare_op,
            expected_raw=row.expected_raw,
            tolerance_raw=row.tolerance_raw,
            actual_raw=row.actual_raw,
            units=units,
        ) is not None
        has_xy = self._series_for_row(row) is not None
        self._tabs.tab("Results").grid_rowconfigure(3, weight=1 if has_xy else 0)
        self._show_plot_canvas(self._limit_canvas, visible=has_limit)
        self._show_plot_canvas(self._xy_canvas, visible=has_xy)
        self._root.update_idletasks()
        self._paint_result_plots(row, units)

    def _hide_result_detail(self) -> None:
        self._tabs.tab("Results").grid_rowconfigure(3, weight=0)
        self._result_detail.grid_remove()
        self._show_plot_canvas(self._limit_canvas, visible=False)
        self._show_plot_canvas(self._xy_canvas, visible=False)

    def _show_plot_canvas(self, canvas: tk.Canvas, *, visible: bool) -> None:
        if visible:
            canvas.grid()
            return
        canvas.delete("all")
        canvas.grid_remove()
        self._plot_pixels.pop(id(canvas), None)

    def _on_plot_configure(self, event: Any) -> None:  # noqa: ANN401
        widget = event.widget
        if widget is not self._limit_canvas and widget is not self._xy_canvas:
            return
        size = (int(event.width), int(event.height))
        if size[0] < 80 or size == self._plot_pixels.get(id(widget)):
            return
        row = self._selected_result
        if row is None or not widget.winfo_manager():
            return
        self._plot_pixels[id(widget)] = size
        units = units_for(row, self._evidence_rows)
        if widget is self._limit_canvas:
            self._draw_limit(row, units)
        else:
            self._draw_xy(row)

    def _paint_result_plots(self, row: Any, units: str) -> None:  # noqa: ANN401
        if str(self._limit_canvas.winfo_manager()):
            self._draw_limit(row, units)
            self._plot_pixels[id(self._limit_canvas)] = (
                self._limit_canvas.winfo_width(),
                self._limit_canvas.winfo_height(),
            )
        if str(self._xy_canvas.winfo_manager()):
            self._draw_xy(row)
            self._plot_pixels[id(self._xy_canvas)] = (
                self._xy_canvas.winfo_width(),
                self._xy_canvas.winfo_height(),
            )

    def _copy_result(self) -> None:
        row = self._selected_result
        if row is None:
            return
        text = detail_text(row, units=units_for(row, self._evidence_rows))
        self._root.clipboard_clear()
        self._root.clipboard_append(text)
        self._status.set("Copied result")

    def _series_for_row(self, row: Any) -> Any:  # noqa: ANN401
        series = explicit_xy(row.actual_raw)
        if series is not None or self._selected_run_dir is None:
            return series
        linked = links_for_row(
            row, self._evidence_rows, run_dir=self._selected_run_dir, import_origin=self._import_origin,
        )
        for link in linked:
            if not link.exists or link.path.suffix.lower() != ".json":
                continue
            try:
                series = explicit_xy(link.path.read_text(encoding="utf-8"))
            except OSError:
                series = None
            if series is not None:
                return series
        return None

    def _draw_limit(self, row: Any, units: str) -> bool:  # noqa: ANN401
        canvas = self._limit_canvas
        canvas.delete("all")
        view = limit_view(
            compare_op=row.compare_op,
            expected_raw=row.expected_raw,
            tolerance_raw=row.tolerance_raw,
            actual_raw=row.actual_raw,
            units=units,
        )
        if view is None:
            return False
        width = canvas.winfo_width()
        if width < 80:
            return True
        margin = 28
        line_y = 68

        def x_of(value: float) -> float:
            fraction = limit_fraction(value, view.low, view.high)
            return margin + fraction * (width - margin * 2)

        def caption(value: float) -> str:
            text = format(value, ".12g")
            if view.units:
                return f"{text} {view.units}"
            return text

        canvas.create_line(margin, line_y, width - margin, line_y, fill="#8b949e", width=2)
        label_y = line_y - 16
        occupied: list[tuple[float, float]] = []
        drawn_limits: set[float] = set()
        for limit in (view.low, view.high):
            if limit is None or limit in drawn_limits:
                continue
            drawn_limits.add(limit)
            x = x_of(limit)
            canvas.create_line(x, line_y - 12, x, line_y + 12, fill="#3fb950", width=2)
            _place_limit_label(canvas, x, label_y, caption(limit), width, occupied)
        actual_x = x_of(view.actual)
        canvas.create_oval(
            actual_x - 5, line_y - 5, actual_x + 5, line_y + 5, fill="#f0f6fc", outline="#f0f6fc",
        )
        same_as_limit = any(
            limit is not None and limit == view.actual for limit in (view.low, view.high)
        )
        if not same_as_limit:
            _place_limit_label(canvas, actual_x, label_y, caption(view.actual), width, occupied)
        return True

    def _draw_xy(self, row: Any) -> bool:  # noqa: ANN401
        canvas = self._xy_canvas
        canvas.delete("all")
        series = self._series_for_row(row)
        if series is None:
            return False
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 80 or height < 40:
            return True
        view = limit_view(
            compare_op=row.compare_op,
            expected_raw=row.expected_raw,
            tolerance_raw=row.tolerance_raw,
            actual_raw=row.actual_raw,
            units="",
        )
        low = view.low if view is not None else None
        high = view.high if view is not None else None
        points = reduce_xy(series.points, low=low, high=high, max_points=600)
        finite = [(x, y) for x, y in points if x is not None and y is not None]
        if not finite:
            return False
        xs = [item[0] for item in finite]
        ys = [item[1] for item in finite]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if max_x == min_x:
            max_x += 1
        if max_y == min_y:
            max_y += 1

        def map_x(value: float) -> float:
            return 36 + (value - min_x) / (max_x - min_x) * (width - 48)

        def map_y(value: float) -> float:
            return 12 + (max_y - value) / (max_y - min_y) * (height - 28)

        previous: tuple[float, float] | None = None
        for x_value, y_value in points:
            if x_value is None or y_value is None:
                previous = None
                continue
            current = (map_x(x_value), map_y(y_value))
            if previous is not None:
                canvas.create_line(*previous, *current, fill="#58a6ff")
            previous = current
        canvas.create_text(
            8, height - 8, anchor="w", fill="#cccccc",
            text=f"x ({series.x_unit})  y ({series.y_unit})",
        )
        return True

    def _poll_worker(self) -> None:
        while True:
            try:
                kind, *payload = self._worker.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log" and self._selected_run_dir is None and self._worker.is_running():
                self._append_log(payload[0])
            elif kind == "started":
                self._selected_run_dir = None
                self._tabs.set("Log")
                self._append_log(f"--- Run started: {payload[0]} ---")
                self._status.set(f"Running: {payload[0]}")
            elif kind == "error":
                self._append_log(f"ERROR: {payload[0]}")
                self._stop_btn.configure(state="disabled")
                self._status.set("Run failed to start")
            elif kind == "finished":
                finished: RunFinished = payload[0]
                self._append_log(f"--- Run finished (exit {finished.exit_code}) ---")
                self._stop_btn.configure(state="disabled")
                self._status.set(f"Last run: {finished.run_dir}" if finished.run_dir else f"Finished (exit {finished.exit_code})")
                self._refresh_runs()
        while True:
            try:
                kind, *payload = self._ui_events.get_nowait()
            except queue.Empty:
                break
            if kind == "browser" and payload[0] == self._browser_generation:
                self._browser_snapshot = payload[1]
                self._render_run_list()
            elif kind == "run" and payload[0] == self._detail_generation:
                self._apply_run_snapshot(payload[1])
            elif kind == "evidence" and payload[0] == self._detail_generation:
                self._apply_evidence(payload[0], payload[1])
        self._root.after(200, self._poll_worker)


def main() -> None:
    ensure_display_available()
    try:
        import customtkinter as ctk
    except ImportError as exc:
        print("Colosseum GUI requires customtkinter. Reinstall with: pip install --force-reinstall colosseum-core", file=sys.stderr)
        raise SystemExit(1) from exc
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    init_windows_taskbar()
    ColosseumApp(ctk).run()
