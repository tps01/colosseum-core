"""Run-browser panel: the grouped, collapsible list of recorded runs."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from ._browser import (
    RunBrowserRow,
    RunBrowserSnapshot,
    load_run_browser_snapshot,
    suite_run_dirs,
)

if TYPE_CHECKING:
    import queue
    from collections.abc import Callable
    from pathlib import Path

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


def status_button_color(status: str) -> tuple[str, str] | str:
    return _STATUS_BUTTON_COLORS.get(_normalize_status(status), "gray40")


class RunBrowserPanel:
    def __init__(
        self,
        ctk: Any,  # noqa: ANN401
        body: Any,  # noqa: ANN401
        *,
        cwd: Path,
        events: queue.Queue[Any],
        on_select_run: Callable[[Path], None],
    ) -> None:
        self._ctk = ctk
        self._cwd = cwd
        self._events = events
        self._on_select_run = on_select_run
        self._run_widgets: dict[tuple[str, Path], Any] = {}
        self._snapshot = RunBrowserSnapshot(rows=[])
        self._generation = 0
        self._expanded_output_dirs: set[Path] = set()
        self._expanded_suites: set[Path] = set()
        self.frame = self._build(body)

    def _build(self, body: Any) -> Any:  # noqa: ANN401
        ctk = self._ctk
        runs_panel = ctk.CTkFrame(body, width=280)
        runs_panel.grid_rowconfigure(1, weight=1)
        runs_panel.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(runs_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 2))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Runs").grid(row=0, column=0, sticky="w")
        ctrls = ctk.CTkFrame(header, fg_color="transparent")
        ctrls.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(ctrls, text="Refresh", width=70, command=self.refresh).grid(
            row=0,
            column=0,
            padx=2,
        )
        ctk.CTkButton(ctrls, text="Expand", width=70, command=self._expand_all_output_dirs).grid(
            row=0,
            column=1,
            padx=2,
        )
        ctk.CTkButton(ctrls, text="Collapse", width=70, command=self._collapse_all_output_dirs).grid(
            row=0,
            column=2,
            padx=2,
        )
        self._run_list = ctk.CTkScrollableFrame(runs_panel)
        self._run_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        return runs_panel

    def refresh(self) -> None:
        self._generation += 1
        gen = self._generation
        threading.Thread(
            target=lambda: self._events.put(("browser", gen, load_run_browser_snapshot(self._cwd))),
            daemon=True,
        ).start()

    def apply_snapshot(self, generation: int, snapshot: RunBrowserSnapshot) -> None:
        if generation == self._generation:
            self._snapshot = snapshot
            self._render_run_list()

    def _outputs_dir_label(self, outputs_dir: Path) -> str:
        try:
            return str(outputs_dir.relative_to(self._cwd))
        except ValueError:
            return str(outputs_dir)

    @staticmethod
    def _run_list_label(row: RunBrowserRow) -> str:
        return f"{row.entry.path.name}  [{row.status}]"

    def _expand_all_output_dirs(self) -> None:
        self._expanded_output_dirs = set(self._snapshot.output_dirs)
        self._expanded_suites = suite_run_dirs(self._snapshot.rows)
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
        self._on_select_run(run_dir)

    def _render_run_list(self) -> None:
        for w in self._run_widgets.values():
            w.pack_forget()
        ctk, rows = self._ctk, self._snapshot.rows
        grouped = len(self._snapshot.output_dirs) > 1
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
                    self._run_list,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=("gray85", "gray25"),
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
                text_color=status_button_color(row.status),
            )
            header.pack(fill="x", padx=(18 * level, 0), pady=1)
            if expanded:
                for child in row.children:
                    self._add_run_button(child, level=level + 1, active=active)
            return
        key = ("run", run_dir)
        active.add(key)
        btn = self._run_widgets.get(key) or self._ctk.CTkButton(
            self._run_list,
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._on_select_run(rd),
        )
        self._run_widgets[key] = btn
        btn.configure(text=self._run_list_label(row), text_color=status_button_color(row.status))
        btn.pack(fill="x", padx=(18 * level, 0), pady=1)

    def _suite_header(self, run_dir: Path) -> Any:  # noqa: ANN401
        """Expand marker stays white. The suite name keeps the result color."""
        ctk = self._ctk
        frame = ctk.CTkFrame(self._run_list, fg_color="transparent")
        mark = ctk.CTkButton(
            frame,
            text="[+]",
            width=36,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "white"),
            hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._toggle_suite(rd),
        )
        name = ctk.CTkButton(
            frame,
            text="",
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda rd=run_dir: self._toggle_suite(rd),
        )
        mark.pack(side="left")
        name.pack(side="left", fill="x", expand=True)
        frame._mark = mark
        frame._name = name
        return frame
