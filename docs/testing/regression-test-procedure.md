# Colosseum extended regression test procedure

Manual and semi-automated regression for **hardware benches**. This document is the canonical procedure when instruments or a DUT are available. Until then, use automated Tiers 1–3 (`python scripts/run_tests.py`) and scripted Tier 4A checks that require no hardware.

**Related:** [README.md](README.md) (pytest tiers), [templates/regression-signoff.md](templates/regression-signoff.md).

---

## 1. Purpose and scope

| Layer | What it validates | When to run |
|-------|-------------------|-------------|
| Tiers 1–3 (pytest) | Core logic, sim bench, CLI | Every change; before tagging |
| Tier 4A (scripts) | Soak stability, docgen build | Before release candidate |
| Tier 4B (this doc) | Real VISA/serial/SSH, vendor models | When a hardware bench is available |

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

---

## 4. Configuration

1. Copy [examples/configs/bench.local.toml.example](../../examples/configs/bench.local.toml.example) (or [examples/configs/bench.toml](../../examples/configs/bench.toml)) to a **gitignored** local file, e.g. `examples/configs/bench.local.toml`.
2. Set real `resource`, `port`, `host`, `key_filename` / `password`. Never commit secrets.
3. Optional vendor models:
   - DMM: `model = "keysight-edu34450a"`
   - PSU: `model = "tdk-genesys"`
4. Export nothing sensitive in shell history; use env vars only for non-secret overrides if needed.

---

## 5. Test cases

Each case lists **objective**, **preconditions**, **steps**, **expected results**, and **evidence**.

### R-HW-01 — Real PSU/DMM power rail

**Objective:** Real PSU/DMM power-rail scenario on physical instruments.

**Preconditions:** PSU and DMM powered; outputs off; `bench.local.toml` wired to correct VISA/COM resources.

**Steps:**

1. `colosseum run examples/test_power_rails.py --config examples/configs/bench.local.toml`
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

### R-HW-04 — SSH DUT health check

**Objective:** `col.shared.ssh.measure_stdout` against a real SSH endpoint.

**Preconditions:** Reachable DUT with SSH credentials in `bench.local.toml`.

**Steps:**

1. `colosseum run examples/test_ssh_health.py --config examples/configs/bench.local.toml`
2. Confirm verifications and measured stdout in SQLite.

**Expected:** Exit `0` when the DUT responds as expected; FAIL/ERROR recorded when credentials or host are wrong.

---

### R-SOAK-HW-01 — Long-run on hardware

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
| R-SOAK-01 | `python tests/regression/run_soak_sim.py` (default 50 iterations, `smoke.toml` suite; use `--count 5` for a quick check) |
| R-DOC-01 | `python tests/regression/run_docgen_check.py` (requires `requirements-dev.txt`; CI uses `--verify-only` after phased build) |
| R-OFFLINE-00 | `python tests/regression/run_offline_install_check.py` (staging + tarball extract; also in `run_tests.py --regression`) |

R-OFFLINE-00 validates staging install and release tarball extract on the host.
