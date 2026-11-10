"""Suite TOML loading and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from colosseum.config.toml_relaxed import coerce_config_bool, read_relaxed_toml
from colosseum.paths import absolute_path

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_DURATION_RE = re.compile(
    r"^(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s?)?$",
    re.IGNORECASE,
)


class SuiteError(RuntimeError):
    pass


@dataclass
class SuiteTestEntry:
    path: Path
    repeat_count: int = 1
    repeat_for: timedelta | None = None
    parameters: Path | None = None


@dataclass
class SuiteDefinition:
    name: str
    setup: list[Path]
    tests: list[SuiteTestEntry]
    between_tests: list[Path]
    teardown: list[Path]
    fail_fast: bool = False
    cycle_count: int = 1
    cycle_for: timedelta | None = None
    parameters: Path | None = None
    parameter_stacking: bool = True


def parse_repeat_duration(value: str, *, field: str = "repeat_for") -> timedelta:
    text = value.strip()
    if not text:
        raise SuiteError(f"{field} duration must not be empty")
    match = _DURATION_RE.fullmatch(text)
    if not match or not any(match.group(n) for n in ("days", "hours", "minutes", "seconds")):
        raise SuiteError(
            f"Invalid {field} duration {value!r}; use suffixes s, m, h, d (e.g. 30s, 24h)",
        )
    return timedelta(
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )


def _as_path_list(value: object, field: str, base_dir: Path) -> list[Path]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SuiteError(f"Suite field `{field}` must be a list of paths")
    paths: list[Path] = []
    for item in value:
        if not isinstance(item, str):
            raise SuiteError(f"Suite field `{field}` entries must be strings")
        paths.append(absolute_path(base_dir / item))
    return paths


def _parse_parameters_field(item: dict[str, object], base_dir: Path, *, index: int) -> Path | None:
    raw = item.get("parameters")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise SuiteError(f"Suite tests[{index}] parameters must be a non-empty string path")
    return absolute_path(base_dir / raw)


def _parse_test_entry(item: object, base_dir: Path, *, index: int) -> SuiteTestEntry:
    if isinstance(item, str):
        return SuiteTestEntry(path=absolute_path(base_dir / item))
    if not isinstance(item, dict):
        raise SuiteError(f"Suite tests[{index}] must be a path string or inline table")
    path = item.get("path")
    if not path or not isinstance(path, str):
        raise SuiteError(f"Suite tests[{index}] table requires string field `path`")
    resolved = absolute_path(base_dir / path)
    parameters = _parse_parameters_field(item, base_dir, index=index)
    repeat_count = item.get("repeat_count")
    repeat_for = item.get("repeat_for")
    if repeat_count is not None and repeat_for is not None:
        raise SuiteError(f"Suite tests[{index}] cannot set both repeat_count and repeat_for")
    if repeat_count is not None:
        if not isinstance(repeat_count, int) or isinstance(repeat_count, bool):
            raise SuiteError(f"Suite tests[{index}] repeat_count must be an integer")
        if repeat_count < 1:
            raise SuiteError(f"Suite tests[{index}] repeat_count must be >= 1")
        return SuiteTestEntry(path=resolved, repeat_count=repeat_count, parameters=parameters)
    if repeat_for is not None:
        if not isinstance(repeat_for, str):
            raise SuiteError(f"Suite tests[{index}] repeat_for must be a string")
        return SuiteTestEntry(
            path=resolved,
            repeat_for=parse_repeat_duration(repeat_for),
            parameters=parameters,
        )
    return SuiteTestEntry(path=resolved, parameters=parameters)


def _parse_tests(value: object, base_dir: Path) -> list[SuiteTestEntry]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SuiteError("Suite field `tests` must be a list")
    return [_parse_test_entry(item, base_dir, index=index) for index, item in enumerate(value)]


def _parse_cycle(raw: dict[str, Any]) -> tuple[int, timedelta | None]:
    cycle_count = raw.get("cycle_count")
    cycle_for = raw.get("cycle_for")
    if cycle_count is not None and cycle_for is not None:
        raise SuiteError("Suite cannot set both cycle_count and cycle_for")
    if cycle_count is not None:
        if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
            raise SuiteError("Suite field `cycle_count` must be an integer")
        if cycle_count < 1:
            raise SuiteError("Suite field `cycle_count` must be >= 1")
        return cycle_count, None
    if cycle_for is not None:
        if not isinstance(cycle_for, str):
            raise SuiteError("Suite field `cycle_for` must be a string")
        return 1, parse_repeat_duration(cycle_for, field="cycle_for")
    return 1, None


def _as_bool(value: object, field: str) -> bool:
    if value is None:
        return False
    parsed = coerce_config_bool(value)
    if parsed is None:
        raise SuiteError(f"Suite field `{field}` must be a boolean")
    return parsed


def _parse_suite_parameters(raw: object, base_dir: Path) -> Path | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise SuiteError("Suite field `parameters` must be a non-empty string path")
    return absolute_path(base_dir / raw)


def _parse_parameter_stacking(raw: object) -> bool:
    if raw is None:
        return True
    parsed = coerce_config_bool(raw)
    if parsed is None:
        raise SuiteError("Suite field `parameter_stacking` must be a boolean")
    return parsed


def _read_suite_toml(suite_path: Path) -> dict[str, Any]:
    if not suite_path.exists():
        raise SuiteError(f"Suite file not found: {suite_path}")
    try:
        return read_relaxed_toml(suite_path)
    except UnicodeDecodeError as exc:
        raise SuiteError(f"Suite file is not valid UTF-8: {suite_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SuiteError(f"Invalid suite TOML: {exc}") from exc


def _require_suite_scripts_exist(
    tests: list[SuiteTestEntry],
    setup: list[Path],
    between_tests: list[Path],
    teardown: list[Path],
) -> None:
    for entry in tests:
        if not entry.path.exists():
            raise SuiteError(f"Test script not found: {entry.path}")
    for script_path in setup + between_tests + teardown:
        if not script_path.exists():
            raise SuiteError(f"Suite script not found: {script_path}")


def load_suite_toml(path: Path) -> SuiteDefinition:
    suite_path = absolute_path(path)
    raw = _read_suite_toml(suite_path)

    if "rip_cord" in raw:
        raise SuiteError(
            "Suite field `rip_cord` was removed; use `fail_fast = true` instead "
            "(abort remaining setup/between/test work after any of those slots fail, "
            "always run teardown, and fail the suite)",
        )

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise SuiteError("Suite TOML requires string field `name`")
    base = suite_path.parent
    tests = _parse_tests(raw.get("tests"), base)
    if not tests:
        raise SuiteError("Suite TOML requires non-empty `tests` list")
    setup = _as_path_list(raw.get("setup"), "setup", base)
    between_tests = _as_path_list(raw.get("between_tests"), "between_tests", base)
    teardown = _as_path_list(raw.get("teardown"), "teardown", base)
    _require_suite_scripts_exist(tests, setup, between_tests, teardown)
    cycle_count, cycle_for = _parse_cycle(raw)
    return SuiteDefinition(
        name=name,
        setup=setup,
        tests=tests,
        between_tests=between_tests,
        teardown=teardown,
        fail_fast=_as_bool(raw.get("fail_fast"), "fail_fast"),
        cycle_count=cycle_count,
        cycle_for=cycle_for,
        parameters=_parse_suite_parameters(raw.get("parameters"), base),
        parameter_stacking=_parse_parameter_stacking(raw.get("parameter_stacking")),
    )
