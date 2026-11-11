"""Platform, environment, and input-file fingerprint captured once per run."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import platform
import sys
from dataclasses import dataclass
from importlib.metadata import Distribution, PackageNotFoundError, distribution, distributions
from pathlib import Path
from typing import TYPE_CHECKING

from colosseum.config.parameters import _suite_parameter_paths
from colosseum.database.manager import DatabaseManager

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from colosseum.context import RuntimeContext

_LOG_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
_PROVENANCE_SECTIONS = ("platform", "packages", "inputs")


@dataclass(frozen=True)
class InputFile:
    """One file that contributed to the run, tagged with why it was included."""

    role: str
    path: Path


def platform_info() -> dict[str, str]:
    """Return the interpreter and OS fields recorded for a run."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": sys.executable,
    }


def _distribution_name(dist: Distribution) -> str | None:
    raw = dist.metadata.get("Name")
    if raw is None:
        return None
    name = str(raw).strip()
    return name or None


def _provides_plugin(dist: Distribution) -> bool:
    return any(getattr(ep, "group", None) == "colosseum.plugins" for ep in dist.entry_points)


def selected_packages() -> tuple[dict[str, str], list[str]]:
    """Return selected versions for colosseum-core plus plugin distributions."""
    versions: dict[str, str] = {}
    plugins: list[str] = []
    for dist in distributions():
        name = _distribution_name(dist)
        if name is None:
            continue
        is_plugin = _provides_plugin(dist)
        if name.casefold() == "colosseum-core" or is_plugin:
            versions[name] = str(dist.version)
        if is_plugin:
            plugins.append(name)
    if not any(key.casefold() == "colosseum-core" for key in versions):
        with contextlib.suppress(PackageNotFoundError):
            versions["colosseum-core"] = distribution("colosseum-core").version
    ordered = {key: versions[key] for key in sorted(versions, key=str.casefold)}
    return ordered, sorted(plugins, key=str.casefold)


def _md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_inputs(files: Sequence[InputFile]) -> list[dict[str, str]]:
    """MD5 each existing file once. The same path under two roles is read once."""
    hashed: dict[Path, str] = {}
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, Path]] = set()
    for item in files:
        path = item.path.resolve()
        key = (item.role, path)
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            continue
        digest = hashed.get(path)
        if digest is None:
            digest = _md5_file(path)
            hashed[path] = digest
        rows.append({"role": item.role, "path": str(path), "md5": digest})
    return rows


def single_input_files(
    *,
    script_path: Path | None,
    config_path: Path | str | None,
    metadata_path: Path | str | None,
    parameters_path: Path | None,
) -> list[InputFile]:
    """Input files for one ``colosseum run``."""
    files: list[InputFile] = []
    if script_path is not None:
        files.append(InputFile("script", script_path))
    if config_path:
        files.append(InputFile("config", Path(config_path)))
    if metadata_path:
        files.append(InputFile("metadata", Path(metadata_path)))
    if parameters_path is not None:
        files.append(InputFile("parameters", parameters_path))
    return files


def _append_suite_test_inputs(
    files: list[InputFile],
    tests: Sequence[tuple[Path, Path | None]],
    *,
    suite_parameters: Path | None,
    parameter_stacking: bool,
) -> None:
    for script_path, entry_parameters in tests:
        files.append(InputFile("test", script_path))
        for resolved in _suite_parameter_paths(
            script_path=script_path,
            entry_path=entry_parameters,
            suite_path=suite_parameters,
            stacking=parameter_stacking,
        ):
            if resolved != suite_parameters:
                files.append(InputFile("parameters", resolved))


def suite_input_files(
    ctx: RuntimeContext,
    *,
    suite_path: Path,
    setup: Sequence[Path],
    tests: Sequence[tuple[Path, Path | None]],
    between_tests: Sequence[Path],
    teardown: Sequence[Path],
    suite_parameters: Path | None = None,
    parameter_stacking: bool = True,
) -> list[InputFile]:
    """Input files known when a suite starts, before any slot runs.

    The suite-level parameters file (CLI ``--parameters`` or suite TOML
    ``parameters``) is included once when set. With stacking on, each test also
    contributes its entry parameters path or sibling ``parameters.toml``. With
    stacking off, per-test parameter files are skipped when a suite-level file
    is set.
    """
    files: list[InputFile] = [InputFile("suite", suite_path)]
    if ctx.config_path:
        files.append(InputFile("config", Path(ctx.config_path)))
    if ctx.metadata_path:
        files.append(InputFile("metadata", Path(ctx.metadata_path)))
    if suite_parameters is None:
        suite_parameters = ctx.run_options.parameters_path
    if suite_parameters is not None:
        files.append(InputFile("parameters", suite_parameters))
    for script_path in setup:
        files.append(InputFile("setup", script_path))
    for script_path in between_tests:
        files.append(InputFile("between_tests", script_path))
    for script_path in teardown:
        files.append(InputFile("teardown", script_path))
    _append_suite_test_inputs(
        files,
        tests,
        suite_parameters=suite_parameters,
        parameter_stacking=parameter_stacking,
    )
    return files


def collect_provenance(files: Sequence[InputFile]) -> dict[str, object]:
    """Build the snapshot stored in the log, database, and summary."""
    versions, plugins = selected_packages()
    return {
        "platform": platform_info(),
        "packages": {"versions": versions, "plugins": plugins},
        "inputs": hash_inputs(files),
    }


def _provenance_line(section: str, payload: object) -> str:
    message = f"Provenance: {section}={json.dumps(payload, sort_keys=True)}"
    record = logging.LogRecord(
        name="colosseum",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    return _LOG_FORMATTER.format(record)


def append_provenance_log(path: Path, snapshot: Mapping[str, object]) -> None:
    """Append the snapshot to ``debug.log`` without sending it to the console."""
    lines = [_provenance_line(section, snapshot[section]) for section in _PROVENANCE_SECTIONS if section in snapshot]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def flush_file_handlers(logger: logging.Logger | None) -> None:
    """Flush file handlers so a direct append follows lines they already formatted."""
    if logger is None:
        return
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            handler.flush()


def write_provenance_database(database: DatabaseManager, snapshot: Mapping[str, object]) -> None:
    """Insert each provenance section."""
    for section in _PROVENANCE_SECTIONS:
        if section not in snapshot:
            continue
        database.insert_provenance(section, snapshot[section])


def publish_provenance(
    snapshot: Mapping[str, object],
    *,
    log_path: Path | None,
    database: DatabaseManager | None,
) -> None:
    """Write the snapshot to the log file and database when those sinks exist."""
    if log_path is not None:
        append_provenance_log(log_path, snapshot)
    if database is not None:
        write_provenance_database(database, snapshot)


def record_single_provenance(
    ctx: RuntimeContext,
    script_path: Path | None,
    parameters_path: Path | None,
) -> None:
    """Capture and store provenance for one test run. A second call does nothing."""
    if ctx.provenance is not None:
        return
    snapshot = collect_provenance(
        single_input_files(
            script_path=script_path,
            config_path=ctx.config_path,
            metadata_path=ctx.metadata_path,
            parameters_path=parameters_path,
        ),
    )
    ctx.provenance = snapshot
    log_path = None
    if not ctx.no_artifacts and ctx.output_dir is not None:
        flush_file_handlers(ctx.logger)
        log_path = ctx.output_dir / "debug.log"
    database = ctx.db if ctx.db.is_initialized() else None
    publish_provenance(snapshot, log_path=log_path, database=database)


def record_suite_provenance(
    ctx: RuntimeContext,
    *,
    suite_path: Path,
    setup: Sequence[Path],
    tests: Sequence[tuple[Path, Path | None]],
    between_tests: Sequence[Path],
    teardown: Sequence[Path],
    suite_parameters: Path | None = None,
    parameter_stacking: bool = True,
) -> None:
    """Capture suite provenance once onto the container. Slots are not updated."""
    if ctx.provenance is not None:
        return
    snapshot = collect_provenance(
        suite_input_files(
            ctx,
            suite_path=suite_path,
            setup=setup,
            tests=tests,
            between_tests=between_tests,
            teardown=teardown,
            suite_parameters=suite_parameters,
            parameter_stacking=parameter_stacking,
        ),
    )
    ctx.provenance = snapshot
    if ctx.no_artifacts or ctx.suite_output_dir is None:
        return
    append_provenance_log(ctx.suite_output_dir / "debug.log", snapshot)
    database = DatabaseManager()
    try:
        database.initialize(ctx.suite_output_dir / "execution.sqlite")
        write_provenance_database(database, snapshot)
    finally:
        database.close()
