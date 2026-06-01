# QEMU / Yocto regression (Tier 4C)

Manual regression on a Poky-built `qemux86-64` guest. Complements automated Tier 4A checks and Tier 4B hardware procedure.

**Related:** [regression-test-procedure.md](regression-test-procedure.md), [infra/yocto/README.md](../../infra/yocto/README.md), [templates/regression-signoff.md](templates/regression-signoff.md).

---

## Purpose

| Mode | What it validates |
|------|-------------------|
| **Offline install** | Air-gapped `pip install --no-index` on embedded Linux (R-OFFLINE-01) |
| **SSH DUT endpoint** | Host runs Colosseum; paramiko SSH into guest (R-EMU-01/02/03) |
| **X11 GUI** | `colosseum --gui` on guest forwarded to host display (R-GUI-QEMU-01) |

Colosseum is installed on the guest **only** via offline wheel bundle at regression time.

---

## Prerequisites

1. Automated tiers pass: `python scripts/run_tests.py`
2. R-OFFLINE-00 passes: `python tests/regression/run_offline_install_check.py`
3. Linux host with Yocto Kirkstone dependencies and ~100 GB disk
4. `colosseum-qemu-image` built per [infra/yocto/README.md](../../infra/yocto/README.md)
5. Colosseum on **host** for SSH cases: `pip install -e .`

---

## Quick start

```bash
# Terminal 1: build env + start guest
source ../poky-kirkstone/oe-init-build-env infra/yocto/build
./infra/yocto/scripts/qemu-up.sh
./infra/yocto/scripts/qemu-wait-ssh.sh

# Terminal 2: run full matrix (from repo root)
./infra/yocto/run_all_regression.sh --skip-gui-interactive
```

---

## Regression matrix

| ID | Driver | Pass criteria |
|----|--------|---------------|
| R-OFFLINE-01 | `run_offline_regression.sh` | Guest smoke exits 0; `summary.txt` PASS |
| R-EMU-01 | `run_ssh_regression.sh` | `test_ssh_health.py` exit 0; `uut_version` PASS |
| R-EMU-02 | `run_ssh_regression.sh --extended` | `regex_noisy_stdout.py` exit 0 |
| R-EMU-03 | `run_ssh_regression.sh --suite` | `embedded_smoke.toml` exit 0 |
| R-GUI-QEMU-01 | `run_gui_regression.sh` | GUI window on host; manual sign-off |
| R-GUI-QEMU-01b | `run_gui_regression.sh --headless` | `xvfb-run colosseum --help` on guest (optional) |

Bench config: [`infra/yocto/conf/bench.qemu.toml`](../../infra/yocto/conf/bench.qemu.toml) (SSH `127.0.0.1:2222`).

---

## X11 forwarding notes

### Linux / WSL

- WSLg: `DISPLAY` is set automatically
- Native X: ensure `DISPLAY` is exported before `run_gui_regression.sh`

### Windows

1. Install and start **VcXsrv** or **X410**
2. Allow connections from WSL/localhost
3. From WSL: `export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0`
4. Run `./infra/yocto/run_gui_regression.sh`

The GUI runs **on the guest** (after offline install); only the window is forwarded to the host.

---

## Evidence and sign-off

Logs under `infra/yocto/artifacts/`:

- `offline-regression-*.log`
- `ssh-regression-*.log`
- `gui-regression-*.log`
- `full-regression-*.log`

Complete [templates/regression-signoff.md](templates/regression-signoff.md) and attach log paths.

---

## CI boundary

| Check | Automation |
|-------|------------|
| R-OFFLINE-00 (host venv, no QEMU) | GitHub Actions CI |
| Yocto build + QEMU regression | **Manual only** |

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| SSH timeout on 2222 | Guest booted? `qemu-wait-ssh.sh`; `local.conf` has `QB_SLIRP_OPT` |
| Offline install fails | Bundle built on Linux for qemux86-64; guest Python version matches bundle |
| R-EMU-01 version FAIL | Guest `/etc/version` is `v0.1.0-colosseum-qemu` (colosseum-guest-identify recipe) |
| GUI does not appear | Host `DISPLAY` set; `ssh -X` works; guest has `python3-tkinter` |
| `runqemu` not found | Source `oe-init-build-env` in same shell as `qemu-up.sh` |
