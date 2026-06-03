# FFO: Host and DUT Utilities

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Summary

The shared extension provides cross-domain helpers: SSH command execution and stdout capture, regex verification against stored measurements, minimal file and subprocess utilities—all using the same measurement/verification model as equipment.

## Actors

- Test engineer integrating embedded Linux DUTs
- Plugin author extending shared patterns

## Preconditions

- `colosseum-shared` installed
- SSH targets defined in config (`[shared.ssh]` / `[[shared.ssh]]`)
- Prior measurement for regex verify targets

## Main flow

1. User runs `col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")`.
2. Decorator opens SSH session (or uses pooled session per run), runs command, stores stdout in measurements.
3. User runs `col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")`.
4. Verification reads stored stdout, applies regex, records PASS/FAIL.

## MVP scope (minimal helpers)

| API | Purpose |
|-----|---------|
| `ssh.measure_stdout` | Capture command output |
| `ssh.run` (optional) | Run without measure wrapper |
| `regex.verify_match` | Pattern check on prior key |
| `filesystem.file_exists` | Host file check (measure + verify pair) |
| `subprocess.run_checked` | Run host command, fail on non-zero |
| `parsing.*` | Strip/parse floats, key=value lines, regex groups (helpers, not stored alone) |

## Outputs

SQLite rows; no separate protocol log unless DEBUG.

## Failure modes

| Condition | Result |
|-----------|--------|
| SSH auth failure | ERROR |
| Command timeout | ERROR |
| Regex no match | FAIL |
| Missing measurement key | ERROR |

## Exit code impact

Through required verifications.

## Non-goals

- Full expect-style interactive shells
- File transfer (SCP/SFTP) in MVP unless trivial add
- Container orchestration

## Related design

- [ddd-shared-architecture.md](../design/ddd-shared-architecture.md)
- [ddd-shared-ssh-regex.md](../design/ddd-shared-ssh-regex.md)
