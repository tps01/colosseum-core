# Driver documentation requests

Public `col.equipment.*` / `col.io.*` APIs are implemented. **Vendor `model` drivers** below are wired when a programming manual was supplied.

## Implemented vendor models

| `model` slug | Kind | Manual | Notes |
|--------------|------|--------|-------|
| `keysight-edu34450a` | dmm | EDU34450A Programming Guide | DC V/I/R |
| `keysight-esg` | vsg | E4400-90506 | CW measure + arb (E4438C) |
| `keysight-e4407b` | speca | E4407B manual | |
| `tektronix-rsa5100b` | speca | RSA5100B manual | RTSA capture |
| `tdk-genesys` | psu | Genesys user guide | OVP/OCP |
| `adaura-r3` | attn | AdauraTech R3 manual | Text `SET`/`STATUS`; `driver = "serial"` + `port` |
| `itech-it8600` | eload | IT8600 Programming Guide | |
| `chroma-8600` | eload | 8600 Series Programming Manual | |
| `agilent-6050` | eload | 06060-90005 | |
| `keysight-53220a`, `keysight-53230a` | freqcounter | 53220A/53230A User's Guide | |
| `tektronix-fca3000`, `tektronix-fca3100`, `tektronix-mca3000` | freqcounter | 077-0494-00 | |
| `tektronix-mdo4000` | oscope | 077-0510-03 MDO4000 programmer | |
| `tektronix-t3dso2000` | oscope | T3DSO1000/2000 programming guide | |
| `tektronix-ttr500` | vna | 077-1257-00 TTR500 programmer | SCPI `SENS<n>:*` |
| `rohde-znb` | vna | R&S ZNB user manual | SCPI `SENS<n>:*` |
| **`anritsu-541xx`** | vna | 10410-00147 GPIB User's Guide | GPIB mnemonics `ST`/`SP`/`DP`/`SUS`; op. manual 10410-00141 |
| **`keysight-u2001a`**, **`keysight-u2000`**, **`keysight-u2000a`** | pwrmeter | U2001A operating guide + U2000-90411 SCPI | `SENS:FREQ`, `FETCh?`, `CAL:ZERO:AUTO ONCE` |
| **`minicircuits-rc`**, **`minicircuits-ztrc`** | rfswitch | Mini-Circuits Prog_Manual-2-Switch | `SETA=1`, `SETP=…`, `SWPORT?` |

### Bench TOML examples

**Keysight U2001A (USB VISA):**

```toml
[[equipment.pwrmeter]]
pwrmeter_id = 1
resource = "USB0::0x2A8D::0x2D18::INSTR"
model = "keysight-u2001a"
frequency = 1e9
```

**Mini-Circuits RC switch (Ethernet/TCP VISA or serial):**

```toml
[[equipment.rfswitch]]
rfswitch_id = 1
resource = "TCPIP0::192.168.100.100::inst0::INSTR"
model = "minicircuits-rc"
path = "A=1;B=0"
```

**Anritsu 541XXA (GPIB):**

```toml
[[equipment.vna]]
vna_id = 1
resource = "GPIB0::18::INSTR"
model = "anritsu-541xx"
frequency_unit = "GHz"
```

Use `frequency_unit = "MHz"` for 54107A/54109A/54111A per the GPIB guide.

## Still generic-only

| Kind | Please provide |
|------|----------------|
| sdr | Ettus UHD documentation |
| `col.io` `ni-845x` | NI DLL on host (manual 371746E on file; ctypes driver pending) |
| `col.io` `ni-6501` | 6501/6502 DIO programming reference |

## Implemented IO drivers

| `driver` slug | Kind | Dependency | Notes |
|---------------|------|------------|-------|
| `sim` | dio | (core) | In-memory GPIO for CI/offline |
| `ftdi-ft232h` | dio | `pip install colosseum[io]` (pyftdi) | FT232H ADBUS/ACBUS GPIO via pyftdi URL in `resource` |

### Bench TOML examples

**Simulated DIO:**

```toml
[[io.dio]]
dio_id = 1
driver = sim
port_lines = 8
direction = 0xFF
```

**FT232H GPIO:**

```toml
[[io.dio]]
dio_id = 1
driver = ftdi-ft232h
resource = ftdi://ftdi:232h/1
port_lines = 8
direction = 0x0F
```
