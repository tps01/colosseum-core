"""Host configuration snapshots (``col.host.config``)."""

from __future__ import annotations

from colosseum.decorators import VerificationResult, command, verification
from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_host.host.profile import write_profile

_DOMAIN = "host"


@command
def capture_host_profile(*, path: str = "host_profile.json", disk_path: str | None = None) -> str:
    """Write a host profile JSON artifact and register it on the active run.

    :param path: Relative artifact path under the run directory.
    :type path: str, optional
    :param disk_path: Optional disk path for free-space measurement (default: cwd).
    :type disk_path: str | None, optional

    :returns: Resolved artifact path string.
    :rtype: str
    """
    artifact_path = resolve_artifact_path(path)
    write_profile(str(artifact_path), disk_path=disk_path)
    register_artifact("host_profile", artifact_path, description="Bench PC host profile snapshot")
    return str(artifact_path)


@verification()
def verify_bench_config_loaded(*, key: str, optional: bool = False) -> VerificationResult:
    """Verify ``col.config.load_config`` has been called for this run.

    :param key: Verification evidence key (not tied to a measurement source).
    :type key: str
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS or FAIL status.
    :rtype: VerificationResult
    """
    _ = key
    from colosseum.context import get_context

    ctx = get_context()
    if ctx is not None and ctx.config_path is not None:
        return VerificationResult(status="PASS", message="", optional=optional)
    return VerificationResult(
        status="FAIL",
        message="bench config is not loaded (config_path is unset)",
        optional=optional,
    )
