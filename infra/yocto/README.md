# Yocto / QEMU regression lab

Tier **4C** manual regression on a Poky `qemux86-64` image. Validates three modes on one guest:

| Mode | Colosseum runs on | Driver |
|------|-------------------|--------|
| Offline runtime | Guest (after offline pip install) | `run_offline_regression.sh` |
| DUT endpoint | Host → SSH guest | `run_ssh_regression.sh` |
| X11 GUI | Guest via `ssh -X` | `run_gui_regression.sh` |

This is **not** part of GitHub Actions CI (BitBake builds take hours and need ~100 GB disk).

## Layout

| Path | Purpose |
|------|---------|
| `meta-colosseum-test/` | BitBake layer (`colosseum-qemu-image`) |
| `scripts/` | QEMU lifecycle + offline install helpers |
| `conf/bench.qemu.toml` | Host-side SSH bench config (port 2222) |
| `suites/embedded_smoke.toml` | R-EMU-03 suite |
| `examples/regex_noisy_stdout.py` | R-EMU-02 script |
| `build/` | BitBake tree (gitignored) |
| `cache/` | `DL_DIR` + `SSTATE_DIR` (gitignored) |
| `artifacts/` | Regression logs |

## Prerequisites

- Linux host with Yocto Kirkstone build dependencies
- ~100 GB free disk for first build + sstate cache
- Colosseum installed on **host** for SSH regression (`pip install -e .`)
- Build offline bundles on **Linux** (`python scripts/package_offline.py`) — bundles are platform-specific

Clone Poky outside the repo:

```bash
git clone git://git.yoctoproject.org/poky -b kirkstone ../poky-kirkstone
```

## Build the image (first time)

```bash
source ../poky-kirkstone/oe-init-build-env infra/yocto/build
bitbake-layers add-layer "$OLDPWD/meta-colosseum-test"
cp "$OLDPWD/meta-colosseum-test/conf/local.conf.sample" conf/local.conf
bitbake colosseum-qemu-image
```

Expect **2–6+ hours** on first build. Subsequent builds reuse `infra/yocto/cache/sstate`.

**Security note:** the image enables `debug-tweaks` (empty root password) for regression only. Do not deploy to production.

## Run QEMU

```bash
source ../poky-kirkstone/oe-init-build-env infra/yocto/build
./infra/yocto/scripts/qemu-up.sh
./infra/yocto/scripts/qemu-wait-ssh.sh
```

SSH contract: host port **2222** → guest port 22 (configured in `local.conf.sample` via `QB_SLIRP_OPT`).

Stop the guest:

```bash
./infra/yocto/scripts/qemu-down.sh
```

## Regression drivers

| ID | Command |
|----|---------|
| R-OFFLINE-01 | `./infra/yocto/run_offline_regression.sh` |
| R-EMU-01 | `./infra/yocto/run_ssh_regression.sh` |
| R-EMU-02 | `./infra/yocto/run_ssh_regression.sh --extended` |
| R-EMU-03 | `./infra/yocto/run_ssh_regression.sh --suite` |
| R-GUI-QEMU-01 | `./infra/yocto/run_gui_regression.sh` (interactive; requires host `DISPLAY`) |
| R-GUI-QEMU-01b | `./infra/yocto/run_gui_regression.sh --headless` |
| All | `./infra/yocto/run_all_regression.sh` |

Colosseum is **always** installed on the guest via offline wheel bundle (`scripts/install-offline-bundle.sh`), never baked into the image.

## X11 on Windows

1. Start **VcXsrv** or **X410** before GUI regression
2. Set `DISPLAY=localhost:0.0` (or your X server display)
3. Run `./infra/yocto/run_gui_regression.sh` from WSL or Git Bash with OpenSSH

WSL2 with WSLg sets `DISPLAY` automatically.

## Documentation

- Canonical procedure: [`docs/testing/qemu-yocto-regression.md`](../../docs/testing/qemu-yocto-regression.md)
- Sign-off: [`docs/testing/templates/regression-signoff.md`](../../docs/testing/templates/regression-signoff.md)

## Disk hygiene

```bash
python scripts/cleanup.py --dry-run --include-infra
python scripts/cleanup.py --include-infra
```

## Future work

- `qemuarm64` image variant
- Self-hosted GitHub Actions (out of scope until requested)
