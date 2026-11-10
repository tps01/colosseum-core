"""Tk canvas painters for the result limit and XY views.

Pure math lives in ``_plots``. These helpers take a canvas plus data, and
``ResultPlots`` owns the two canvases embedded in the results tab.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any, Literal

from ._evidence import links_for_row
from ._plots import explicit_xy, limit_fraction, limit_view, reduce_xy

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ._plots import XySeries
    from ._results import EvidenceRow

    _XyPrepared = tuple[
        XySeries,
        list[tuple[float | None, float | None]],
        Callable[[float], float],
        Callable[[float], float],
        int,
    ]


def series_for_row(
    row: EvidenceRow,
    evidence_rows: list[EvidenceRow],
    *,
    run_dir: Path | None,
    import_origin: str | None,
) -> XySeries | None:
    series = explicit_xy(row.actual_raw)
    if series is not None or run_dir is None:
        return series
    linked = links_for_row(
        row,
        evidence_rows,
        run_dir=run_dir,
        import_origin=import_origin,
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


def place_limit_label(
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


def draw_limit(canvas: tk.Canvas, row: EvidenceRow, units: str) -> bool:
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
        place_limit_label(canvas, x, label_y, caption(limit), width, occupied)
    actual_x = x_of(view.actual)
    canvas.create_oval(
        actual_x - 5,
        line_y - 5,
        actual_x + 5,
        line_y + 5,
        fill="#f0f6fc",
        outline="#f0f6fc",
    )
    same_as_limit = any(limit is not None and limit == view.actual for limit in (view.low, view.high))
    if not same_as_limit:
        place_limit_label(canvas, actual_x, label_y, caption(view.actual), width, occupied)
    return True


def prep_xy(
    canvas: tk.Canvas,
    row: EvidenceRow,
    series: XySeries | None,
) -> _XyPrepared | Literal[False] | None:
    """Return stroke inputs, ``False`` when canvas is too small, or ``None`` to abort."""
    if series is None:
        return None
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width < 80 or height < 40:
        return False
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
        return None
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

    return series, points, map_x, map_y, height


def stroke_xy(
    canvas: tk.Canvas,
    series: XySeries,
    points: list[tuple[float | None, float | None]],
    map_x: Callable[[float], float],
    map_y: Callable[[float], float],
    height: int,
) -> None:
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
        8,
        height - 8,
        anchor="w",
        fill="#cccccc",
        text=f"x ({series.x_unit})  y ({series.y_unit})",
    )


def draw_xy(canvas: tk.Canvas, row: EvidenceRow, series: XySeries | None) -> bool:
    canvas.delete("all")
    prepared = prep_xy(canvas, row, series)
    if prepared is None:
        return False
    if prepared is False:
        return True
    stroke_xy(canvas, *prepared)
    return True


class ResultPlots:
    """The limit and XY canvases under the result list, with show/hide/repaint."""

    def __init__(
        self,
        tab: Any,  # noqa: ANN401
        *,
        current: Callable[[], tuple[EvidenceRow, str] | None],
        series_for: Callable[[EvidenceRow], XySeries | None],
    ) -> None:
        self._tab = tab
        self._current = current
        self._series_for = series_for
        self._pixels: dict[int, tuple[int, int]] = {}
        self.limit_canvas = tk.Canvas(tab, height=92, highlightthickness=0, bg="#1e1e1e")
        self.limit_canvas.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        self.limit_canvas.grid_remove()
        self.xy_canvas = tk.Canvas(tab, height=160, highlightthickness=0, bg="#1e1e1e")
        self.xy_canvas.grid(row=3, column=0, sticky="nsew", padx=2, pady=2)
        self.xy_canvas.grid_remove()
        self.limit_canvas.bind("<Configure>", self._on_configure)
        self.xy_canvas.bind("<Configure>", self._on_configure)

    def show(self, row: EvidenceRow, units: str) -> None:
        has_limit = (
            limit_view(
                compare_op=row.compare_op,
                expected_raw=row.expected_raw,
                tolerance_raw=row.tolerance_raw,
                actual_raw=row.actual_raw,
                units=units,
            )
            is not None
        )
        series = self._series_for(row)
        has_xy = series is not None
        self._tab.grid_rowconfigure(3, weight=1 if has_xy else 0)
        self._show_canvas(self.limit_canvas, visible=has_limit)
        self._show_canvas(self.xy_canvas, visible=has_xy)
        self.limit_canvas.update_idletasks()
        self._paint(row, units, series)

    def hide(self) -> None:
        self._tab.grid_rowconfigure(3, weight=0)
        self._show_canvas(self.limit_canvas, visible=False)
        self._show_canvas(self.xy_canvas, visible=False)

    def _show_canvas(self, canvas: tk.Canvas, *, visible: bool) -> None:
        if visible:
            canvas.grid()
            return
        canvas.delete("all")
        canvas.grid_remove()
        self._pixels.pop(id(canvas), None)

    def _on_configure(self, event: Any) -> None:  # noqa: ANN401
        widget = event.widget
        if widget is not self.limit_canvas and widget is not self.xy_canvas:
            return
        size = (int(event.width), int(event.height))
        if size[0] < 80 or size == self._pixels.get(id(widget)):
            return
        current = self._current()
        if current is None or not widget.winfo_manager():
            return
        row, units = current
        self._pixels[id(widget)] = size
        if widget is self.limit_canvas:
            draw_limit(self.limit_canvas, row, units)
        else:
            draw_xy(self.xy_canvas, row, self._series_for(row))

    def _paint(self, row: EvidenceRow, units: str, series: XySeries | None) -> None:
        for canvas in (self.limit_canvas, self.xy_canvas):
            if not str(canvas.winfo_manager()):
                continue
            if canvas is self.limit_canvas:
                draw_limit(canvas, row, units)
            else:
                draw_xy(canvas, row, series)
            self._pixels[id(canvas)] = (canvas.winfo_width(), canvas.winfo_height())
