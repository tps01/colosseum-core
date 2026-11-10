"""Results tab: filtered, paged result rows, detail text, plots, and run slots."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._browser import display_status
from ._plot_canvas import ResultPlots, series_for_row
from ._results import detail_text, filter_rows, page_size, units_for
from ._run_browser_ui import status_button_color

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._plots import XySeries
    from ._results import EvidenceRow


def set_text(textbox: Any, text: str) -> None:  # noqa: ANN401
    textbox.configure(state="normal")
    textbox.delete("1.0", "end")
    if text:
        textbox.insert("end", text)
        textbox.see("1.0")
    textbox.configure(state="disabled")


class ResultsPanel:
    def __init__(
        self,
        ctk: Any,  # noqa: ANN401
        tab: Any,  # noqa: ANN401
        slot_list: Any,  # noqa: ANN401
        *,
        selected_run_dir: Callable[[], Path | None],
        on_select_run: Callable[[Path], None],
        set_status: Callable[[str], None],
        set_clipboard: Callable[[str], None],
        focus_tab: Callable[[], None],
    ) -> None:
        self._ctk = ctk
        self._slot_list = slot_list
        self._selected_run_dir = selected_run_dir
        self._on_select_run = on_select_run
        self._set_status = set_status
        self._set_clipboard = set_clipboard
        self._focus_tab = focus_tab
        self._evidence_rows: list[EvidenceRow] = []
        self._evidence_error: str | None = None
        self._import_origin: str | None = None
        self._filtered_rows: list[EvidenceRow] = []
        self._selected_result: EvidenceRow | None = None
        self._result_page = 0
        self._failures_only = True
        self._slot_buttons: list[Any] = []
        self._results_notice: str | None = None
        self._result_buttons: list[Any] = []
        self._build(tab)

    def _build(self, tab: Any) -> None:  # noqa: ANN401
        ctk = self._ctk
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
        self._plots = ResultPlots(tab, current=self._current_plot_target, series_for=self._series_for)
        self._result_detail = ctk.CTkTextbox(tab, height=140, state="disabled")
        self._result_detail.grid(row=4, column=0, sticky="ew", padx=2, pady=2)
        self._result_detail.grid_remove()

    def _current_plot_target(self) -> tuple[EvidenceRow, str] | None:
        row = self._selected_result
        if row is None:
            return None
        return row, units_for(row, self._evidence_rows)

    def _series_for(self, row: EvidenceRow) -> XySeries | None:
        return series_for_row(
            row,
            self._evidence_rows,
            run_dir=self._selected_run_dir(),
            import_origin=self._import_origin,
        )

    # -- load lifecycle -----------------------------------------------------

    def begin_load(self, run_dir: Path) -> None:
        """Clear everything for a newly selected run until its data arrives."""
        self._selected_result = None
        self._evidence_rows = []
        self._filtered_rows = []
        self._evidence_error = None
        self._results_notice = f"Loading results for {run_dir.name}..."
        self.clear_slot_buttons()
        self._hide_result_detail()
        self._render_result_rows()

    def apply_summary(self, summary: dict[str, Any] | None) -> None:
        self._render_slots(summary)
        status = display_status(summary)
        self._failures_only = status in {"FAIL", "ERROR"}
        self._result_page = 0
        self._apply_result_filter()

    def apply_evidence(self, loaded: Any) -> None:  # noqa: ANN401
        self._results_notice = None
        self._evidence_rows = list(loaded.rows)
        self._evidence_error = loaded.error
        self._import_origin = loaded.import_origin
        self._apply_result_filter()

    # -- slots --------------------------------------------------------------

    def _render_slots(self, summary: dict[str, Any] | None) -> None:
        self.clear_slot_buttons()
        slots = []
        if isinstance(summary, dict):
            raw = summary.get("all_slots") or summary.get("test_slots") or []
            slots = [slot for slot in raw if isinstance(slot, dict)]
        if not slots:
            self._slot_list.grid_remove()
            return
        self._slot_list.grid()
        for slot in slots:
            label = f"{slot.get('phase')} [{slot.get('overall_result')}] {Path(str(slot.get('script') or '')).name}"
            repeat = slot.get("repeat_index")
            if repeat is not None:
                label += f" repeat={repeat}"
            cycle = slot.get("cycle_index")
            if cycle is not None:
                label += f" cycle={cycle}"
            folder = Path(str(slot.get("output_directory") or ""))
            button = self._ctk.CTkButton(
                self._slot_list,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda path=folder: self._select_slot(path),
            )
            button.pack(fill="x", pady=1)
            self._slot_buttons.append(button)

    def clear_slot_buttons(self) -> None:
        for button in self._slot_buttons:
            button.destroy()
        self._slot_buttons = []
        self._slot_list.grid_remove()

    def _select_slot(self, folder: Path) -> None:
        if folder.is_dir():
            self._on_select_run(folder)

    # -- filter and paging --------------------------------------------------

    def _show_failures(self) -> None:
        self._failures_only = True
        self._result_page = 0
        self._apply_result_filter()
        self._focus_tab()

    def _show_all_results(self) -> None:
        self._failures_only = False
        self._result_page = 0
        self._apply_result_filter()
        self._focus_tab()

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
        if self._selected_run_dir() is None:
            return "Select a run to see its results."
        return "This run has no recorded results."

    # -- rows, detail, plots ------------------------------------------------

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
                self._result_list,
                text=label,
                anchor="w",
                fg_color="transparent",
                text_color=status_button_color(row.status),
                hover_color=("gray85", "gray25"),
                command=lambda item=row: self._show_result(item),
            )
            button.pack(fill="x", pady=1)
            self._result_buttons.append(button)

    def _show_result(self, row: EvidenceRow) -> None:
        self._selected_result = row
        units = units_for(row, self._evidence_rows)
        set_text(self._result_detail, detail_text(row, units=units))
        self._result_detail.grid()
        self._plots.show(row, units)

    def _hide_result_detail(self) -> None:
        self._plots.hide()
        self._result_detail.grid_remove()

    def _copy_result(self) -> None:
        row = self._selected_result
        if row is None:
            return
        self._set_clipboard(detail_text(row, units=units_for(row, self._evidence_rows)))
        self._set_status("Copied result")
