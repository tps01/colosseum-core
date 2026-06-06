# Colosseum extended regression test procedure

Manual and semi-automated regression for **hardware benches** and **QEMU embedded targets**. This document is the canonical procedure when instruments or a DUT are available. Until then, use automated Tiers 1–3 (`python scripts/run_tests.py`) and scripted Tier 4A checks that require no hardware.

**Related:** [README.md](README.md) (pytest tiers), [templates/regression-signoff.md](templates/regression-signoff.md).

---

## 1. Purpose and scope

| Layer | What it validates | When to run |
|-------|-------------------|-------------|
| Tiers 1–3 (pytest) | Core logic, sim bench, CLI | Every change; before tagging |
| Tier 4A (scripts) | Soak stability, docgen build | Before release candidate |
| Tier 4B (this doc) | Real VISA/serial/SSH, QEMU DUT, vendor models | When bench or QEMU is available |
| Tier 4C (manual) | Offline pip install on Yocto/Poky QEMU guest | Before claiming embedded offline support |

Run 4B after plugin/transport changes, vendor driver changes, or before a release that claims hardware compatibility.

---

## 2. Prerequisites

1. Install Colosseum: `pip install -e .` and `pip install -r requirements-dev.txt`.
2. Python 3.9+ on Windows or Linux (match your supported matrix).
3. Complete automated tiers: `python scripts/run_tests.py` must pass.
4. **Safety:** confirm current limits, OVP/OCP, and emergency off for PSUs; no unattended high-power tests.
5. Fill the bench inventory table (Section 3) before first execution.

---

## 3. Bench inventory (fill before testing)

| Role | Make/model | Connection | Config id | Notes |
|------|------------|------------|-----------|-------|
| PSU 1 | | VISA/COM: | `psu_id = 1` | |
| PSU 2 | | | `psu_id = 2` | |
| DMM | | | `dmm_id = 1` | |
| Serial (if used) | | COM/USB: | `serial_id = 1` | `driver = "serial"` |
| DUT SSH | | host:port | `ssh_id = 1` | key or password |
| QEMU (if used) | image version | forwarded port | | |

---

## 4. Configuration

1. Copy [configs/bench.local.toml.example](../../configs/bench.local.toml.example) (or [examples/configs/bench.toml](../../examples/configs/bench.toml)) to a **gitignored** local file, e.g. `configs/bench.local.toml`.
2. Set real `resource`, `port`, `host`, `key_filename` / `password`. Never commit secrets.
3. For QEMU SSH, start from [templates/bench.qemu.toml.example](templates/bench.qemu.toml.example).
4. Optional vendor models:
   - DMM: `model = "keysight-edu34450a"`
   - PSU: `model = "tdk-genesys"`
5. Export nothing sensitive in shell history; use env vars only for non-secret overrides if needed.

---

## 5. Test cases

Each case lists **objective**, **preconditions**, **steps**, **expected results**, and **evidence**.

### R-HW-01 — Real PSU/DMM power rail

**Objective:** Real PSU/DMM power-rail scenario on physical instruments.

**Preconditions:** PSU and DMM powered; outputs off; `bench.local.toml` wired to correct VISA/COM resources.

**Steps:**

1. `colosseum run examples/test_power_rails.py --config configs/bench.local.toml`
2. Open latest `outputs/<timestamp>_test_power_rails/execution.sqlite`.
3. Query: `SELECT key, status, optional FROM verifications ORDER BY id;`

**Expected:**

- Process exit code `0`.
- `vrail_3v3` verification `PASS` (required).
- `engineering_probe_point` may be `FAIL` with `optional=1`; run still passes.
- `summary.txt` shows `Overall result: PASS`, exit code `0`.

**Evidence:** Retain output directory path and attach `summary.txt` to sign-off.

---

### R-HW-02 — Vendor instrument models

**Objective:** Vendor drivers (`keysight-edu34450a`, `tdk-genesys`) on real hardware when available.

**Preconditions:** Instruments support configured models; limits set conservatively.

**Steps:**

1. Set `model = "keysight-edu34450a"` on `[equipment.dmm]` (or Genesys on PSU).
2. Run a minimal script that calls `col.equipment.dmm.measure_voltage` / PSU setup APIs (or reuse `examples/test_power_rails.py` with adjusted ids).
3. Confirm SCPI traffic succeeds (instrument display or bus trace if available).

**Expected:** Measurements `PASS` in SQLite; no transport exceptions in `debug.log`.

**Evidence:** Note model serial and firmware in sign-off.

---

### R-HW-03 — Serial transport

**Objective:** `driver = "serial"` path for SCPI over UART.

**Preconditions:** USB-UART or bench serial connected; loopback fixture acceptable for bring-up.

**Steps:**

1. Set `[equipment.serial]` with `driver = "serial"`, correct `port`, `baudrate`.
2. Use `col.equipment.scpi.query` / `write` against `serial_id` in a short script.
3. `col.endex()` via `if __name__ == "__main__"` block.

**Expected:** Responses match fixture/instrument; rows in `measurements` or events without ERROR.

---

### R-EMU-01 — QEMU / Poky SSH version check

**Objective:** SSH on the Yocto `colosseum-qemu-image` guest (qemux86-64).

**Preconditions:** Guest running via `infra/yocto/scripts/qemu-up.sh`; SSH on `127.0.0.1:2222`.

**Steps:**

1. `./infra/yocto/scripts/qemu-wait-ssh.sh`
2. `./infra/yocto/run_ssh_regression.sh`

Or manually: `colosseum run examples/test_ssh_health.py --config infra/yocto/conf/bench.qemu.toml` with `COLOSSEUM_BENCH_CONFIG=bench.qemu.toml`.

**Expected:** Exit `0`; `uut_version` verify `PASS` against guest `/etc/version` (`v0.1.0-colosseum-qemu`).

**Evidence:** Save raw `measure_stdout` value from SQLite; log in `infra/yocto/artifacts/ssh-regression-*.log`.

See also [qemu-yocto-regression.md](qemu-yocto-regression.md).

---

### R-EMU-02 — Regex on noisy live stdout

**Objective:** `col.shared.regex.verify_match` tolerates real shell output.

**Preconditions:** R-EMU-01 guest reachable.

**Steps:**

1. `./infra/yocto/run_ssh_regression.sh --extended`

Or: `colosseum run infra/yocto/examples/regex_noisy_stdout.py --config infra/yocto/conf/bench.qemu.toml`

**Expected:** Required verifications `PASS` when DUT is healthy; `FAIL` when pattern deliberately wrong (negative check once).

---

### R-EMU-03 — Full suite on DUT

**Objective:** Suite lifecycle on embedded target.

**Preconditions:** Suite TOML paths valid; setup/teardown scripts safe for DUT.

**Steps:**

1. `./infra/yocto/run_ssh_regression.sh --suite`

Or: `colosseum run-suite infra/yocto/suites/embedded_smoke.toml --config infra/yocto/conf/bench.qemu.toml`
2. Inspect single `execution.sqlite` for test phases in `events` and `run_metadata`.

**Expected:** Exit `0` on success; `summary.txt` present; setup failure case (dry run) exits `1` and skips tests (see automated `setup_fail` fixture behavior).

---

### R-OFFLINE-01 — Yocto Poky offline pip install (manual)

**Objective:** Prove the offline wheel bundle installs and runs on a minimal embedded Linux with no PyPI access.

**Preconditions:** Linux host with Yocto build dependencies; ~100 GB free disk for first Poky build; `colosseum-qemu-image` built per [`infra/yocto/README.md`](../../infra/yocto/README.md).

**Steps:**

1. On a connected host: `python scripts/package_offline.py`
2. Build image: follow `infra/yocto/README.md` (`bitbake colosseum-qemu-image`)
3. Boot QEMU: `runqemu colosseum-qemu-image nographic` (SSH forwarded to host port 2222)
4. Run driver: `./infra/yocto/run_offline_regression.sh`
5. Collect log from `infra/yocto/artifacts/offline-regression-*.log`

**Expected:**

- `colosseum --help` exits `0` on the guest
- Smoke run exits `0`; guest `outputs/*/summary.txt` shows `Overall result: PASS`
- No GitHub Actions workflow is required for sign-off (manual Tier 4C only)

**Evidence:** Attach regression log and guest `summary.txt` path to sign-off.

---

### R-GUI-QEMU-01 — X11 GUI on QEMU guest (manual)

**Objective:** `colosseum --gui` on guest after offline install, forwarded to host via `ssh -X`.

**Preconditions:** Guest running; offline bundle installed (`install-offline-bundle.sh` or `run_gui_regression.sh`); host X server running (`DISPLAY` set).

**Steps:**

1. `./infra/yocto/run_gui_regression.sh`
2. Confirm GUI window appears on host; run smoke script from GUI (optional)
3. Optional automated headless probe: `./infra/yocto/run_gui_regression.sh --headless` (R-GUI-QEMU-01b; does not validate X11 forward)

**Expected:** Interactive GUI usable on host display; manual sign-off with screenshot or notes.

**Evidence:** `infra/yocto/artifacts/gui-regression-*.log`

See [qemu-yocto-regression.md](qemu-yocto-regression.md) for Windows VcXsrv / WSLg setup.

---

### R-SOAK-HW-01 — Long-run on hardware or QEMU

**Objective:** Resource leaks and connection stability (complement to sim soak).

**Preconditions:** Bench stable; cooling and power adequate.

**Steps:**

1. Run the same suite or test script **N ≥ 20** times in a shell loop, or overnight if policy allows.
2. After run, confirm host can still open VISA/SSH without power cycle.

**Expected:** All iterations exit `0`; no accumulating handles (OS-specific check); `debug.log` free of repeated transport errors.

**Abort:** Any smoke, smell, over-temperature, or DUT hang — stop and power down.

---

## 6. Failure handling

| Situation | Action |
|-----------|--------|
| Required verify FAIL | Stop suite; capture `outputs/`; file defect |
| Optional verify FAIL | Note in sign-off; may still release if waived |
| Setup script ERROR | Do not continue tests; fix bench state |
| SSH host key changed | Update known_hosts or key policy; document |
| Instrument timeout | Check cabling/resource string; retry once |

**Waiver template:** Case ID, reason, approver, date.

---

## 7. Sign-off

Copy [templates/regression-signoff.md](templates/regression-signoff.md), complete the matrix, and archive with the release artifact.

---

## 8. Scripted Tier 4A (no hardware)

| ID | Command |
|----|---------|
| R-SOAK-01 | `python tests/regression/run_soak_sim.py` (default 50 iterations; use `--count 5` for a quick check) |
| R-DOC-01 | `python tests/regression/run_docgen_check.py` (requires `requirements-dev.txt`) |
| R-OFFLINE-00 | `python tests/regression/run_offline_install_check.py` |
| R-MUT-01 | `python tests/regression/run_mutation.py` (instructions only); install `requirements-dev.txt`, then run `python tests/regression/run_mutation.py --run` |
