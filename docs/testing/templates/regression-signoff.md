# Colosseum regression sign-off

| Field | Value |
|-------|--------|
| Tester | |
| Date (UTC) | |
| Repository commit | |
| Colosseum version | |
| Host OS | |
| Python version | |

## Automated tiers (before manual regression)

| Check | Command | Pass |
|-------|---------|------|
| Tiers 1–3 | `python scripts/run_tests.py` | [ ] |
| Tier 4A (soak + docgen + offline) | `python scripts/run_tests.py --regression` | [ ] |
| Sim soak only (optional) | `python tests/regression/run_soak_sim.py --count 10` | [ ] |
| Docgen only (optional) | `python tests/regression/run_docgen_check.py` | [ ] |
| Offline bundle only (optional) | `python tests/regression/run_offline_install_check.py` | [ ] |

## Manual procedure cases

| ID | Title | Pass | Notes |
|----|-------|------|-------|
| R-HW-01 | PSU/DMM power rail | [ ] | |
| R-HW-02 | Vendor instruments | [ ] | |
| R-HW-03 | Serial transport | [ ] | |
| R-EMU-01 | QEMU SSH version | [ ] | |
| R-EMU-02 | Regex on live stdout | [ ] | |
| R-EMU-03 | Full suite on DUT | [ ] | |
| R-SOAK-HW-01 | Long-run hardware/QEMU | [ ] | |
| R-OFFLINE-01 | Yocto offline pip install (manual) | [ ] | |
| R-GUI-QEMU-01 | X11 GUI on QEMU guest | [ ] | |

**Overall:** PASS / FAIL

**Waivers (if any):**
