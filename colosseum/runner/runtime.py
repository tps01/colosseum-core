"""Runtime output paths and suite slots."""

from __future__ import annotations

import logging
import re
import sys
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from colosseum.database import DatabaseManager, initialize_database_if_needed
from colosseum.results.aggregation import ResultAggregator
from colosseum.runner.run_options import resolve_outputs_root

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext

_NO_ARTIFACTS_OUTPUT_ERROR = (
    "Output directory is unavailable in no-artifacts mode; "
    "disable no_artifacts or use persisted output for file artifacts."
)
_RENAME_RETRIES = 8
_RENAME_INITIAL_DELAY_S = 0.05


class OutputNotWritableError(RuntimeError):
    """The outputs root cannot accept a run directory."""


def ensure_outputs_writable(outputs_root: Path) -> None:
    """Create the outputs root if needed and refuse the run when it is not writable.

    ``os.access`` is not reliable on Windows, so this writes a temporary file and
    deletes it. Failure raises :class:`OutputNotWritableError` before a timestamped
    run folder exists.
    """
    try:
        outputs_root.mkdir(parents=True, exist_ok=True)
        probe = outputs_root / f".colosseum-write-{uuid.uuid4().hex}"
        probe.write_bytes(b"")
    except OSError as exc:
        raise OutputNotWritableError(
            f"Output directory is not writable: {outputs_root}: {exc}",
        ) from exc
    with suppress(OSError):
        probe.unlink(missing_ok=True)


def sanitize_logical_name(logical_name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]", "_", logical_name).strip("_")
    return (value or "run")[:64]


def allocate_run_directory(
    outputs_root: Path,
    logical_name: str,
    *,
    parent: Path | None = None,
) -> Path:
    base = parent if parent is not None else outputs_root
    if parent is None:
        base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_name = f"{stamp}_{sanitize_logical_name(logical_name)}"
    candidate = base / run_name
    suffix = 1
    while candidate.exists():
        candidate = base / f"{run_name}_{suffix}"
        suffix += 1
    return candidate


def _strip_result_suffix(name: str) -> str:
    """Remove a trailing ``-pass`` / ``-fail`` suffix if present."""
    for result_suffix in ("-pass", "-fail"):
        if name.endswith(result_suffix):
            return name[: -len(result_suffix)]
    return name


def rename_run_directory_for_result(
    output_dir: Path,
    overall: str,
    *,
    retries: int = _RENAME_RETRIES,
    initial_delay_s: float = _RENAME_INITIAL_DELAY_S,
) -> Path:
    """Rename ``output_dir`` with a ``-pass`` / ``-fail`` suffix.

    An existing ``-pass`` / ``-fail`` suffix is replaced so a slot can be
    re-stamped after post-``endex`` failure. Retries briefly on ``OSError``
    (common on Windows when a handle is briefly held). On persistent failure,
    logs to stderr and returns ``output_dir`` unchanged so callers can still
    write summaries into the original path.
    """
    normalized = overall.lower()
    if normalized not in {"pass", "fail"}:
        raise ValueError(f"Unsupported run result: {overall}")
    base_name = _strip_result_suffix(output_dir.name)
    target_base = output_dir.with_name(f"{base_name}-{normalized}")
    candidate = target_base
    suffix = 1
    while candidate.exists() and candidate != output_dir:
        candidate = target_base.with_name(f"{target_base.name}_{suffix}")
        suffix += 1
    if candidate == output_dir:
        return output_dir
    attempts = max(1, retries)
    last_error: OSError | None = None
    delay = max(0.0, initial_delay_s)
    for attempt in range(attempts):
        try:
            output_dir.rename(candidate)
            return candidate
        except OSError as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            if delay > 0:
                time.sleep(delay)
                delay = min(delay * 2, 0.5)
    print(
        f"Colosseum: failed to rename {output_dir} -> {candidate.name}: {last_error}; leaving directory unrenamed",
        file=sys.stderr,
    )
    return output_dir


def ensure_runtime_ready(ctx: RuntimeContext, logical_name: str | None = None) -> None:
    if ctx.runtime_ready:
        return
    # Suite slots allocate under suite_output_dir via begin_script_slot. After a
    # slot clears, do not mint a sibling under the outputs root.
    if ctx.suite_output_dir is not None and ctx.output_dir is None:
        raise RuntimeError(
            "suite script slot is not active; decorated evidence APIs require "
            "an open suite script slot (the slot may already be finalized)",
        )
    if logical_name is None:
        logical_name = ctx.suite_name or ctx.test_case_name
    console_level = logging.DEBUG if ctx.debug_logging else logging.INFO
    if ctx.no_artifacts:
        ctx.logger = ctx.session.start_logging(
            ctx,
            console=True,
            console_level=console_level,
            file=False,
        )
        ctx.logger.debug("Runtime ready (no-artifacts mode)")
        initialize_database_if_needed(ctx)
    else:
        if ctx.output_dir is None:
            outputs_root = resolve_outputs_root(ctx.run_options)
            ensure_outputs_writable(outputs_root)
            output_dir = allocate_run_directory(outputs_root, logical_name)
            output_dir.mkdir(parents=True, exist_ok=True)
            ctx.output_dir = output_dir
        ctx.logger = ctx.session.start_logging(
            ctx,
            console=True,
            console_level=console_level,
            file=True,
        )
        ctx.logger.debug("Allocated output directory: %s", ctx.output_dir)
        initialize_database_if_needed(ctx)
    from colosseum.config.loader import log_loaded_config

    if ctx.config is not None:
        log_loaded_config(ctx)
    for warning in ctx.config_warnings:
        if ctx.logger is not None:
            ctx.logger.warning(warning)
    ctx.runtime_ready = True


def ensure_output_dir(ctx: RuntimeContext, logical_name: str | None = None) -> Path:
    ensure_runtime_ready(ctx, logical_name)
    if ctx.no_artifacts or ctx.output_dir is None:
        raise RuntimeError(_NO_ARTIFACTS_OUTPUT_ERROR)
    return ctx.output_dir


def _stored_path(value: Path | str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


@dataclass
class SuiteSlotResult:
    phase: str
    script_path: Path
    output_dir: Path
    test_index: int | None = None
    repeat_index: int | None = None
    cycle_index: int | None = None
    affects_suite_result: bool = False
    overall: str | None = None
    exit_code: int | None = None
    config_path: str | None = None
    parameters_path: str | None = None
    metadata_path: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    slot_id: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return the existing outward slot metadata."""
        return {
            "phase": self.phase,
            "script": str(self.script_path),
            "output_directory": str(self.output_dir),
            "test_index": self.test_index,
            "repeat_index": self.repeat_index,
            "cycle_index": self.cycle_index,
            "overall_result": self.overall,
            "exit_code": self.exit_code,
            "config_path": self.config_path,
            "parameters_path": self.parameters_path,
            "metadata_path": self.metadata_path,
        }

    def persisted(self, root: Path) -> dict[str, Any]:
        """Include compact result facts and an occurrence ID for suite storage."""
        return {
            **self.as_dict(),
            "slot_id": self.slot_id,
            "output_directory": self.output_dir.relative_to(root).as_posix(),
            "affects_suite_result": self.affects_suite_result,
            "result": self.summary,
        }


def ensure_suite_runtime_ready(ctx: RuntimeContext, suite_name: str) -> None:
    if ctx.suite_started_at is None:
        ctx.suite_started_at = datetime.now(timezone.utc)
    if ctx.suite_output_dir is not None:
        return
    console_level = logging.DEBUG if ctx.debug_logging else logging.INFO
    if ctx.no_artifacts:
        ctx.suite_output_dir = None
        ctx.logger = ctx.session.start_logging(
            ctx,
            console=True,
            console_level=console_level,
            file=False,
        )
        return
    outputs_root = resolve_outputs_root(ctx.run_options)
    ensure_outputs_writable(outputs_root)
    container = allocate_run_directory(outputs_root, suite_name)
    container.mkdir(parents=True, exist_ok=True)
    ctx.suite_output_dir = container
    database = DatabaseManager()
    try:
        database.initialize(container / "execution.sqlite")
    finally:
        database.close()
    ctx.logger = ctx.session.start_logging(
        ctx,
        console=True,
        console_level=console_level,
        file=True,
    )
    if ctx.logger is not None:
        ctx.logger.info("Suite container: %s", container)


def begin_script_slot(
    ctx: RuntimeContext,
    logical_name: str,
    *,
    phase: str,
    affects_suite_result: bool,
) -> None:
    ctx.phase = phase
    ctx.slot_affects_suite_result = affects_suite_result
    ctx.slot_finalized = False
    ctx.test_case_name = logical_name
    ctx.result_aggregator = ResultAggregator()
    ctx.db = DatabaseManager()
    ctx.runtime_ready = False
    ctx.output_dir = None
    ctx.parameters_path = None
    ctx.parameters_map = None
    ctx.auto_key_enabled = False
    ctx.next_measurement_key = 0
    ctx.next_verification_key = 0
    ctx.auto_key_warned = False
    ctx.parameter_export = None
    ctx.export_errors.clear()
    ctx.dry_run_measurements.clear()
    ctx.dry_run_keys_seen.clear()
    ctx.dry_run_tips.clear()
    ctx.started_at = datetime.now(timezone.utc).astimezone()
    # Mode/phase bookkeeping must run before the no-artifacts early return so
    # procedure applies only to test slots and supporting phases stay full.
    ctx.active_execution_mode = (
        "procedure" if phase == "test" and ctx.session.requested_execution_mode == "procedure" else "full"
    )
    console_level = logging.DEBUG if ctx.debug_logging else logging.INFO
    if ctx.no_artifacts:
        ctx.logger = ctx.session.start_logging(
            ctx,
            console=True,
            console_level=console_level,
            file=False,
        )
        initialize_database_if_needed(ctx)
        ctx.runtime_ready = True
        return
    parent = ctx.suite_output_dir
    if parent is None:
        raise RuntimeError("Suite container is not allocated")
    slot_dir = allocate_run_directory(
        resolve_outputs_root(ctx.run_options),
        logical_name,
        parent=parent,
    )
    slot_dir.mkdir(parents=True, exist_ok=True)
    ctx.output_dir = slot_dir
    ctx.logger = ctx.session.start_logging(
        ctx,
        console=True,
        console_level=console_level,
        file=True,
    )
    initialize_database_if_needed(ctx)
    ctx.db.insert_run_metadata("phase", phase)
    ctx.db.insert_run_metadata("suite_name", ctx.suite_name or "")
    ctx.db.insert_event("INFO", "runner", f"phase_enter:{phase}")
    ctx.runtime_ready = True


def finalize_script_slot(
    ctx: RuntimeContext,
    *,
    script_path: Path,
    test_index: int | None = None,
    repeat_index: int | None = None,
    cycle_index: int | None = None,
) -> SuiteSlotResult:
    from colosseum.results.finalize import finalize_run
    from colosseum.results.finalize_policy import policy_for_suite_slot

    if ctx.slot_finalized:
        raise RuntimeError("Script slot is already finalized")
    affects = ctx.slot_affects_suite_result
    result_data = None
    finalize_error: BaseException | None = None
    try:
        result_data = finalize_run(
            ctx,
            policy=policy_for_suite_slot(affects_suite_result=affects),
        )
    except Exception as exc:  # noqa: BLE001 - slot must not abort the suite
        finalize_error = exc
        ctx.result_aggregator.mark_suite_error(f"slot finalize failed: {exc}")
        if affects:
            ctx.session.mark_suite_failed(f"slot_finalize_failed:{script_path}")

    final_dir = ctx.output_dir or Path.cwd()
    if result_data is not None:
        overall = result_data.overall if affects else None
        exit_code = result_data.exit_code
    else:
        overall = "FAIL" if affects else None
        exit_code = 1
    result = SuiteSlotResult(
        phase=ctx.phase,
        script_path=script_path,
        output_dir=final_dir,
        test_index=test_index,
        repeat_index=repeat_index,
        cycle_index=cycle_index,
        affects_suite_result=affects,
        overall=overall,
        exit_code=exit_code,
        config_path=_stored_path(ctx.config_path),
        parameters_path=_stored_path(ctx.parameters_path),
        metadata_path=_stored_path(ctx.metadata_path),
        summary=result_data.summary if result_data is not None else {},
        slot_id=len(ctx.suite_slot_results),
    )
    ctx.suite_slot_results.append(result)
    if ctx.suite_output_dir is not None and not ctx.no_artifacts:
        DatabaseManager.persist_results(
            ctx.suite_output_dir / "execution.sqlite",
            None,
            kind="suite",
            slots=[result.persisted(ctx.suite_output_dir)],
        )
    ctx.output_dir = None
    ctx.runtime_ready = False
    ctx.slot_finalized = True
    console_level = logging.DEBUG if ctx.debug_logging else logging.INFO
    # Never call start_logging here — that would reprint the identity header.
    try:
        ctx.logger = ctx.session.reattach_console(ctx, console_level=console_level)
    except Exception as exc:  # noqa: BLE001 - slot result is already recorded
        print(
            f"Colosseum: failed to reattach suite console after {script_path}: {exc}",
            file=sys.stderr,
        )
        ctx.logger = None
    if finalize_error is not None and ctx.logger is not None:
        ctx.logger.exception(
            "Script slot finalize failed for %s: %s",
            script_path,
            finalize_error,
        )
    return result


def refresh_slot_artifacts(ctx: RuntimeContext, slot: SuiteSlotResult) -> None:
    """Reconcile core-owned artifacts after a slot failure or container rename."""
    if ctx.no_artifacts or not slot.summary:
        return
    from colosseum.summary.writer import SummaryWriter

    slot.summary["output_directory"] = str(slot.output_dir)
    DatabaseManager.persist_results(
        slot.output_dir / "execution.sqlite",
        {
            **slot.summary,
            "stored_status": slot.summary["overall_result"] if slot.affects_suite_result else "N/A",
        },
        kind="slot",
    )
    if (slot.output_dir / "summary.json").is_file():
        SummaryWriter().write(slot.output_dir, ctx.result_aggregator, ctx, payload=slot.summary)
    if ctx.suite_output_dir is not None:
        DatabaseManager.persist_results(
            ctx.suite_output_dir / "execution.sqlite",
            None,
            kind="suite",
            slots=[slot.persisted(ctx.suite_output_dir)],
        )
