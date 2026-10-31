"""Platform, environment, and input-file fingerprint captured once per run."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import Distribution, PackageNotFoundError, distribution, distributions
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from colosseum.config.parameters import resolve_parameters_path
from colosseum.database.manager import DatabaseManager

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from colosseum.context import RuntimeContext

_LOG_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
_PROVENANCE_SECTIONS = ("platform", "packages", "inputs", "repositories")
# Cache git probes by resolved path (including misses) so editable installs and
# ``_repositories`` do not re-run the same three subprocesses.
_git_repository_cache: dict[str, dict[str, object] | None] = {}


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


def _location(dist: Distribution) -> str:
    path = getattr(dist, "_path", None)
    if path is not None:
        return str(path)
    locate = getattr(dist, "locate_file", None)
    if callable(locate):
        return str(locate(""))
    return ""


def _file_url_path(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    path = unquote(parsed.path)
    if path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


def _read_json(dist: Distribution, name: str) -> dict[str, object] | None:
    read_text = getattr(dist, "read_text", None)
    if not callable(read_text):
        return None
    raw = read_text(name)
    if not raw:
        return None
    loaded = json.loads(raw)
    if isinstance(loaded, dict):
        return loaded
    return None


def _resolve_git_dir(work_tree: Path, git_entry: Path) -> Path | None:
    """Resolve ``work_tree/.git`` (dir or ``gitdir:`` file) to the git directory."""
    if git_entry.is_dir():
        return git_entry
    if not git_entry.is_file():
        return None
    try:
        text = git_entry.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    target = text.split(":", 1)[1].strip()
    git_dir = Path(target)
    if not git_dir.is_absolute():
        git_dir = (work_tree / git_dir)
    try:
        return git_dir.resolve()
    except OSError:
        return None


def _git_common_dir(git_dir: Path) -> Path:
    """Return the object/ref store directory (handles linked worktrees)."""
    marker = git_dir / "commondir"
    if not marker.is_file():
        return git_dir
    try:
        raw = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return git_dir
    common = Path(raw)
    if not common.is_absolute():
        common = git_dir / common
    try:
        return common.resolve()
    except OSError:
        return git_dir


def _discover_git(start: Path) -> tuple[Path, Path, Path] | None:
    """Return ``(work_tree, git_dir, common_dir)`` by walking parents for ``.git``."""
    try:
        probe = start.resolve()
    except OSError:
        return None
    if probe.is_file():
        probe = probe.parent
    for directory in (probe, *probe.parents):
        git_entry = directory / ".git"
        git_dir = _resolve_git_dir(directory, git_entry)
        if git_dir is None:
            continue
        return directory, git_dir, _git_common_dir(git_dir)
    return None


def _read_git_ref(common_dir: Path, ref_name: str) -> str | None:
    ref_path = common_dir / ref_name
    try:
        if ref_path.is_file():
            return ref_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    packed = common_dir / "packed-refs"
    try:
        if not packed.is_file():
            return None
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1] == ref_name:
                return parts[0].strip()
    except OSError:
        return None
    return None


def _read_git_commit(git_dir: Path, common_dir: Path) -> str | None:
    """Read HEAD's commit SHA from git metadata (no subprocess)."""
    head_path = git_dir / "HEAD"
    try:
        if not head_path.is_file():
            head_path = common_dir / "HEAD"
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if head.startswith("ref:"):
        return _read_git_ref(common_dir, head[4:].strip())
    if len(head) >= 40:
        return head.split()[0]
    return None


def _git_worktree_dirty(work_tree: Path) -> bool | None:
    """Return whether the work tree is dirty, or ``None`` if git is unavailable."""
    try:
        status = subprocess.run(
            ["git", "-C", str(work_tree), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if status.returncode != 0:
        return None
    return bool(status.stdout.strip())


def _git_repository(start: Path) -> dict[str, object] | None:
    """Return commit and dirty flag when ``start`` is inside a git work tree.

    Work-tree root and HEAD commit are read from ``.git`` metadata (no
    subprocess). Dirty detection still uses one ``git status --porcelain`` call.
    """
    try:
        probe = start.resolve()
    except OSError:
        return None
    if probe.is_file():
        probe = probe.parent
    cache_key = str(probe)
    if cache_key in _git_repository_cache:
        cached = _git_repository_cache[cache_key]
        return None if cached is None else dict(cached)
    if not probe.exists():
        _git_repository_cache[cache_key] = None
        return None

    discovered = _discover_git(probe)
    if discovered is None:
        _git_repository_cache[cache_key] = None
        return None
    root, git_dir, common_dir = discovered
    root_key = str(root)
    if root_key in _git_repository_cache and root_key != cache_key:
        cached = _git_repository_cache[root_key]
        _git_repository_cache[cache_key] = None if cached is None else dict(cached)
        return None if cached is None else dict(cached)

    commit = _read_git_commit(git_dir, common_dir)
    if commit is None:
        _git_repository_cache[cache_key] = None
        return None
    dirty = _git_worktree_dirty(root)
    if dirty is None:
        _git_repository_cache[cache_key] = None
        return None
    result = {"path": root_key, "commit": commit, "dirty": dirty}
    _git_repository_cache[root_key] = dict(result)
    _git_repository_cache[cache_key] = dict(result)
    return dict(result)


def _editable_checkout(dist: Distribution) -> dict[str, object] | None:
    payload = _read_json(dist, "direct_url.json")
    if payload is None:
        return None
    dir_info = payload.get("dir_info")
    if not isinstance(dir_info, dict) or not dir_info.get("editable"):
        return None
    url = payload.get("url")
    if not isinstance(url, str):
        return None
    path = _file_url_path(url)
    if path is None:
        return None
    checkout: dict[str, object] = {"path": str(path)}
    try:
        if not path.exists():
            return checkout
    except OSError:
        return checkout
    repository = _git_repository(path)
    if repository is not None:
        checkout["commit"] = repository["commit"]
        checkout["dirty"] = repository["dirty"]
    return checkout


def _selected_distribution(name: str, copies: list[Distribution]) -> Distribution:
    """Prefer the copy ``importlib.metadata.version`` would report."""
    try:
        chosen = distribution(name)
    except PackageNotFoundError:
        return copies[0]
    chosen_location = _location(chosen)
    if chosen_location:
        for copy in copies:
            if _location(copy) == chosen_location:
                return copy
    return copies[0]


def installed_packages() -> tuple[dict[str, str], list[str], list[dict[str, object]]]:
    """Return selected versions, plugin names, and every installed copy.

    ``versions`` is the distribution ``importlib.metadata.version`` resolves.
    ``installs`` keeps leftover copies, each with its location. Plugin names are
    selected distributions that expose ``colosseum.plugins``.
    """
    grouped: dict[str, list[Distribution]] = {}
    for dist in distributions():
        name = _distribution_name(dist)
        if name is None:
            continue
        grouped.setdefault(name, []).append(dist)
    versions: dict[str, str] = {}
    plugins: list[str] = []
    installs: list[dict[str, object]] = []
    for name in sorted(grouped, key=str.casefold):
        copies = grouped[name]
        selected = _selected_distribution(name, copies)
        versions[name] = str(selected.version)
        if _provides_plugin(selected):
            plugins.append(name)
        selected_location = _location(selected)
        for copy in copies:
            record: dict[str, object] = {
                "name": name,
                "version": str(copy.version),
                "location": _location(copy),
                "selected": copy is selected or (
                    bool(selected_location) and _location(copy) == selected_location
                ),
            }
            checkout = _editable_checkout(copy)
            if checkout is not None:
                record["editable"] = checkout
            installs.append(record)
    installs.sort(
        key=lambda item: (
            str(item["name"]).casefold(),
            str(item["version"]),
            str(item["location"]),
        ),
    )
    return versions, sorted(plugins, key=str.casefold), installs


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


def suite_input_files(
    ctx: RuntimeContext,
    *,
    suite_path: Path,
    setup: Sequence[Path],
    tests: Sequence[tuple[Path, Path | None]],
    between_tests: Sequence[Path],
    teardown: Sequence[Path],
) -> list[InputFile]:
    """Input files known when a suite starts, before any slot runs.

    A CLI ``--parameters`` file is included once. Otherwise each test contributes
    its entry parameters path, or the sibling ``parameters.toml`` the slot would
    load.
    """
    files: list[InputFile] = [InputFile("suite", suite_path)]
    if ctx.config_path:
        files.append(InputFile("config", Path(ctx.config_path)))
    if ctx.metadata_path:
        files.append(InputFile("metadata", Path(ctx.metadata_path)))
    cli_parameters = ctx.run_options.parameters_path
    if cli_parameters is not None:
        files.append(InputFile("parameters", cli_parameters))
    for script_path in setup:
        files.append(InputFile("setup", script_path))
    for script_path in between_tests:
        files.append(InputFile("between_tests", script_path))
    for script_path in teardown:
        files.append(InputFile("teardown", script_path))
    for script_path, entry_parameters in tests:
        files.append(InputFile("test", script_path))
        if cli_parameters is not None:
            continue
        resolved = resolve_parameters_path(
            script_path=script_path,
            cli_path=None,
            entry_path=entry_parameters,
        )
        if resolved is not None:
            files.append(InputFile("parameters", resolved))
    return files


def _repositories(paths: Sequence[Path]) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    seen_starts: set[str] = set()
    for path in paths:
        try:
            start = path.resolve()
        except OSError:
            continue
        if start.is_file():
            start = start.parent
        start_key = str(start)
        if start_key in seen_starts:
            continue
        seen_starts.add(start_key)
        if not start.exists():
            continue
        record = _git_repository(start)
        if record is None:
            continue
        found[str(record["path"])] = record
    return [found[key] for key in sorted(found, key=str.casefold)]


def collect_provenance(files: Sequence[InputFile]) -> dict[str, object]:
    """Build the snapshot stored in the log, database, and summary."""
    versions, plugins, installs = installed_packages()
    hashed = hash_inputs(files)
    found: dict[str, dict[str, object]] = {}
    # Prefer git facts already gathered while scanning editable installs.
    for install in installs:
        checkout = install.get("editable")
        if not isinstance(checkout, dict):
            continue
        commit = checkout.get("commit")
        path_raw = checkout.get("path")
        if not isinstance(commit, str) or not isinstance(path_raw, str):
            continue
        repo = _git_repository(Path(path_raw))
        if repo is not None:
            found[str(repo["path"])] = repo
            continue
        found[path_raw] = {
            "path": path_raw,
            "commit": commit,
            "dirty": bool(checkout.get("dirty")),
        }
    for record in _repositories([Path(str(row["path"])) for row in hashed]):
        found[str(record["path"])] = record
    return {
        "platform": platform_info(),
        "packages": {"versions": versions, "plugins": plugins, "installs": installs},
        "inputs": hashed,
        "repositories": [found[key] for key in sorted(found, key=str.casefold)],
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
    lines = [
        _provenance_line(section, snapshot[section])
        for section in _PROVENANCE_SECTIONS
        if section in snapshot
    ]
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
