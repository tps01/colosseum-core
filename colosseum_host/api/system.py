"""Host system facts and prerequisite verifiers (``col.host.system``)."""

from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_host.api._verify import minimum_verifier
from colosseum_host.host.collectors import common, memory_available_mb, uptime_s

_DOMAIN = "host"


@measurement
def measure_python_version(*, key: str) -> str:
    """Record the interpreter version string.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: ``platform.python_version()`` value.
    :rtype: str
    """
    _ = key
    return common.python_version()


@measurement
def measure_platform(*, key: str) -> str:
    """Record ``platform.system()``.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: Platform name string.
    :rtype: str
    """
    _ = key
    return common.platform_name()


@measurement
def measure_machine(*, key: str) -> str:
    """Record machine hardware type.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: Machine identifier string.
    :rtype: str
    """
    _ = key
    return common.machine()


@measurement
def measure_hostname(*, key: str) -> str:
    """Record network hostname.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: Hostname string.
    :rtype: str
    """
    _ = key
    return common.hostname()


@measurement
def measure_cpu_count(*, key: str) -> float:
    """Record logical CPU count.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: CPU count as float.
    :rtype: float
    """
    _ = key
    return common.cpu_count()


@measurement
def measure_memory_available_mb(*, key: str) -> float:
    """Record available system memory.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: Available memory in megabytes.
    :rtype: float
    """
    _ = key
    return memory_available_mb()


@measurement
def measure_disk_free_gb(*, key: str, path: str | None = None) -> float:
    """Record free disk space.

    :param key: Unique measurement key within domain ``host``.
    :type key: str
    :param path: Path to check (default: current working directory).
    :type path: str | None, optional

    :returns: Free space in gigabytes.
    :rtype: float
    """
    _ = key
    return common.disk_free_gb(path)


@measurement
def measure_uptime_s(*, key: str) -> float:
    """Record system uptime.

    :param key: Unique measurement key within domain ``host``.
    :type key: str

    :returns: Uptime in seconds.
    :rtype: float
    """
    _ = key
    return uptime_s()


verify_memory_available_mb = minimum_verifier(
    "measure_memory_available_mb",
    name="verify_memory_available_mb",
    unit="MB",
    domain=_DOMAIN,
)
verify_disk_free_gb = minimum_verifier(
    "measure_disk_free_gb",
    name="verify_disk_free_gb",
    unit="GB",
    domain=_DOMAIN,
)


@verification(sources=[MeasurementSource(domain=_DOMAIN, command="system.measure_python_version")])
def verify_python_version(
    *,
    key: str,
    version_prefix: str,
    optional: bool = False,
) -> VerificationResult:
    """Verify a prior ``measure_python_version`` result starts with a prefix.

    :param key: Measurement key shared with ``measure_python_version``.
    :type key: str
    :param version_prefix: Required version prefix (for example ``3.11``).
    :type version_prefix: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    from colosseum.context import require_context
    from colosseum.decorators import missing_measurement_result

    row = require_context().db.get_measurement(
        _DOMAIN, "system.measure_python_version", key, row_index=0
    )
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = str(row.value)
    if actual.startswith(version_prefix):
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"expected python version prefix {version_prefix!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )


@verification(sources=[MeasurementSource(domain=_DOMAIN, command="system.measure_platform")])
def verify_platform(
    *,
    key: str,
    expected_platform: str,
    optional: bool = False,
) -> VerificationResult:
    """Verify a prior ``measure_platform`` result matches exactly.

    :param key: Measurement key shared with ``measure_platform``.
    :type key: str
    :param expected_platform: Expected ``platform.system()`` string.
    :type expected_platform: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    from colosseum.context import require_context
    from colosseum.decorators import missing_measurement_result

    row = require_context().db.get_measurement(_DOMAIN, "system.measure_platform", key, row_index=0)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = str(row.value)
    if actual == expected_platform:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"expected platform {expected_platform!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )
