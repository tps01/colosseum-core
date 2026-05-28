# Colosseum Architecture Document

## 1. Purpose and Scope

Colosseum is a Python-importable, offline, plugin-oriented test automation framework for embedded system integration and acceptance testing.

The framework is intended to be used directly from Python test scripts:

```python
import colosseum as col


def main():
    col.config.load_config("bench.toml")

    col.equipment.psu.set_output(psu_id=1, enabled=True)

    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")

    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)


if __name__ == "__main__":
    main()
    col.endex()
```

The primary use case is bench-top embedded system testing where a device under test is evaluated against requirements using laboratory equipment, host-side utilities, communications interfaces, and automated verification logic.

The first supported adaptation targets are:

- Serial communication through `pyserial`
- SSH communication through `paramiko`
- VISA/SCPI communication through `pyvisa`

The framework should eventually support plugins for other testing domains, such as desktop application testing, web testing, vendor-specific equipment packages, and product-line-specific acceptance test libraries.

## 2. Relationship to Generic Test Automation Architecture

Colosseum follows the spirit of the Generic Test Automation Architecture by separating the framework into concerns that correspond to test definition, test execution, test adaptation, configuration management, and test management support.

For the first implementation phase, Colosseum will focus on:

1. Test definition
2. Test execution
3. Test adaptation
4. Runtime artifact capture
5. Extension/plugin support

Test generation is acknowledged as a future capability but is intentionally excluded from the initial architecture. The core should be modular enough that generated tests, model-based tests, or requirement-derived test scripts can be introduced later without redesigning the runtime model.

## 3. Design Principles

Colosseum should follow these design principles:

1. **Python-first usage**  
   Test cases are ordinary Python files that import and call Colosseum APIs.

2. **Global runtime context for v1**  
   The framework uses a global active runtime context initialized by configuration loading or runner startup. A context-managed API may be considered later, but it is not part of the first architecture.

3. **Offline and local by default**  
   Colosseum must not require cloud services. All required execution artifacts should be produced locally.

4. **Windows and Linux compatibility**  
   File paths, subprocess behavior, serial resources, logging, and multiprocessing behavior must work on both Windows and Linux.

5. **Python 3.9 compatibility**  
   The framework must remain compatible with Python 3.9.

6. **Simple user-facing APIs**  
   Users should normally call high-level functions such as `col.equipment.dmm.measure_voltage()` rather than raw SCPI commands.

7. **Low-level escape hatches**  
   Users must still be able to send raw SCPI, serial, or transport commands for custom or vendor-specific cases.

8. **Persistent evidence**  
   Measurements, verifications, metadata, logs, and relevant artifacts are persisted so a run can be debugged or audited later.

9. **First-class extensions**  
   Built-in extensions and third-party extensions are handled through the same plugin mechanism.

10. **Minimal required project structure**  
    Users can run a single Python file with minimal setup. The repository examples should provide recommended folder structures, but the framework should not require one.

## 4. User Experience

### 4.1 Recommended Import Style

Examples and documentation should recommend:

```python
import colosseum as col
```

### 4.2 Test Case Definition

A test case is a Python file containing measurements and verifications. The file may be run directly with Python or through the Colosseum runner.

A test case may include:

- Configuration loading
- Equipment setup
- Stimulus/application of conditions
- Measurements
- Verifications
- Cleanup logic

### 4.3 Test Suite Definition

A test suite is a collection of Python test case files, optionally surrounded by setup and teardown scripts. Suites may be invoked from the command-line runner or from a higher-level Python file.

Suite definitions should support TOML.

Example:

```toml
name = "smoke_acceptance"

setup = [
  "setup/flash_firmware.py",
  "setup/prepare_bench.py"
]

tests = [
  "tests/test_power_rails.py",
  "tests/test_boot.py",
  "tests/test_ssh_health.py"
]

teardown = [
  "teardown/collect_logs.py",
  "teardown/power_down.py"
]
```

Setup and teardown are optional. Users may run tests directly when the environment is already prepared.

## 5. Package and Extension Model

Colosseum should be distributed through a top-level package named `colosseum`. The core framework lives inside that top-level package rather than being exposed to users as a separate import namespace.

First-party extensions may be separate distributions, but they should register under the same `colosseum` runtime and user-facing namespace.

```text
colosseum
  Core runtime context
  Config loading
  Output directory creation
  SQLite database management
  Logging setup
  Measurement and verification decorators
  Result model
  Plugin discovery
  Runner and suite orchestration
  Setup and teardown support
  Version capture
  Exit-code policy
  Public database read helpers

colosseum-equipment
  VISA / pyvisa support
  SCPI helpers
  Serial / pyserial support
  Power supply helpers
  DMM helpers
  Future JTAG, CAN, DAQ, logic analyzer, RTSA, etc.

colosseum-shared
  SSH / paramiko support
  File and filesystem checks
  Regex verifications
  Process/subprocess helpers
  Common measurements
  Common verifications
```

The distribution names may still be split, for example `colosseum`, `colosseum-equipment`, and `colosseum-shared`, but the primary user import remains:

```python
import colosseum as col
```

The user-facing namespace should expose these as:

```python
col.equipment.dmm.measure_voltage(...)
col.equipment.psu.set_output(...)
col.equipment.serial.write(...)
col.shared.ssh.read_stdout(...)
col.shared.regex.verify_match(...)
```

## 6. Third-Party Extension Handling

Third-party extensions should be treated no differently from first-party extensions such as `equipment` and `shared`.

A third-party extension should be able to:

- Register a namespace under `col`
- Register measurements
- Register verifications
- Register low-level adapters
- Register configuration schema expectations
- Write measurements and verification results into the active runtime database through supported core APIs
- Create output artifacts in the active output directory
- Participate in Sphinx documentation generation through ordinary function docstrings

Example future package names:

```text
colosseum-web
colosseum-desktop
colosseum-vendor-keysight
colosseum-vendor-rohde-schwarz
colosseum-product-alpha
```

Example future user-facing calls:

```python
col.web.browser.open_url(...)
col.desktop.window.verify_title(...)
col.vendor_keysight.rtsa.measure_trace(...)
```

The core plugin mechanism should avoid hard-coding special behavior for first-party packages. First-party extensions may be installed by default or developed in the same repository, but architecturally they should use the same registration pathway available to outside extension authors.

Open design question for later: whether namespace collisions should fail immediately, warn and override, or require explicit user selection.

## 7. Runtime Context

Colosseum v1 uses a global active runtime context.

The runtime context owns:

- Loaded configuration
- Output directory path
- SQLite database connection or database manager
- Logger configuration
- Active test case name
- Active suite name, if applicable
- Framework version information
- Plugin registry
- Result aggregation state

The global context should be initialized by one of the following:

```python
col.config.load_config("bench.toml")
```

or by the command-line runner:

```bash
colosseum run tests/test_power_rails.py --config configs/bench.toml
```

A context-manager API is a future TODO:

```python
with col.run(config="bench.toml") as run:
    run.equipment.dmm.measure_voltage(...)
```

This should not be required for v1.

## 8. Configuration Model

### 8.1 Format

Configuration files should use TOML.

Because Python 3.9 does not include `tomllib`, Colosseum should use a compatible TOML parser such as `tomli` for reading TOML files.

### 8.2 Single Configuration Items

If there is only one item of a given type, a normal TOML table may be used.

Example:

```toml
[equipment.psu]
psu_id = 1
driver = "visa"
resource = "COM1"
voltage = 3.3
ovp = 3.6
ocp = 1.0

[equipment.dmm]
dmm_id = 1
driver = "visa"
resource = "USB0::0x1234::0x5678::INSTR"

[equipment.serial]
serial_id = 1
port = "COM4"
baudrate = 115200
timeout = 2.0
```

### 8.3 Multiple Configuration Items of the Same Type

If there are multiple configuration items of the same type, TOML arrays of tables should be used.

Example:

```toml
[[equipment.psu]]
psu_id = 1
driver = "visa"
resource = "COM1"
voltage = 3.3
ovp = 3.6
ocp = 1.0

[[equipment.psu]]
psu_id = 2
driver = "visa"
resource = "GPIB::5::INSTR"
voltage = 5.0
ovp = 5.5
ocp = 2.0
```

The framework should normalize both forms internally so extension code can handle configuration consistently.

For example, internally:

```toml
[equipment.dmm]
dmm_id = 1
```

and:

```toml
[[equipment.dmm]]
dmm_id = 1
```

should both be accessible through the same configuration access pattern.

### 8.4 Configuration Responsibilities

The configuration system should support:

- Equipment definitions
- Resource strings
- Connection timeouts
- Default instrument settings
- Shared utility configuration, such as SSH targets
- Test bench configuration
- Optional project-specific extension configuration

The configuration layer should not require users to define every possible value. Extensions should support reasonable defaults where safe.

### 8.5 Instrument Interfaces

Many instruments support more than one valid control interface. For example, the same spectrum analyzer may support GPIB, Ethernet/LXI, USBTMC, and serial control.

Colosseum configuration should therefore distinguish the logical instrument from the transport/interface used to reach it.

Example:

```toml
[equipment.spectrum_analyzer]
sa_id = 1
model = "example-spectrum-analyzer"
interface = "ethernet"
resource = "TCPIP0::192.168.1.25::INSTR"
timeout = 10.0
```

The same logical kind of instrument may be configured with a different interface:

```toml
[equipment.spectrum_analyzer]
sa_id = 1
model = "example-spectrum-analyzer"
interface = "gpib"
resource = "GPIB0::18::INSTR"
timeout = 10.0
```

Higher-level instrument APIs should not change merely because the transport changes. A user should still call the same measurement or control function:

```python
col.equipment.spectrum_analyzer.measure_marker_power(sa_id=1, key="carrier_power")
```

The instrument implementation should select or construct the correct transport from configuration.

## 9. Output and Artifact Model

When a test case is run, Colosseum creates an `outputs/` directory in the directory from which the user invoked the script or runner.

The `outputs/` directory and timestamped test output directory are created lazily when first needed. This will usually occur when Colosseum first starts `debug.log` or initializes `execution.sqlite`.

Each test case run creates one timestamped output directory:

```text
outputs/
  2026-05-26_184233_test_power_rails/
    debug.log
    execution.sqlite
    summary.txt
    measurement_trace.csv
```

The output directory should be mostly flat by default.

Colosseum should not create `artifacts/` or `reports/` subdirectories automatically. Subdirectories should only be created when:

1. A specific function requires one
2. A plugin requires one
3. The user specifies a relative output path that includes a subdirectory

For example:

```python
col.equipment.rtsa.save_trace(path="traces/startup_trace.csv")
```

may produce:

```text
outputs/
  2026-05-26_184233_test_rf_startup/
    debug.log
    execution.sqlite
    traces/
      startup_trace.csv
```

### 9.1 Required Output Files

Minimum required outputs:

```text
debug.log
execution.sqlite
```

Initial summary output:

```text
summary.txt
```

A machine-readable `summary.json` may be added later, but `summary.txt` is the first summary format to implement.

Additional outputs may be created by measurements, verifications, plugins, or user code.

## 10. Logging Model

Colosseum should use Python's standard `logging` package.

The standard log file is:

```text
debug.log
```

The log should support debug, info, warning, error, and exception-level messages where appropriate.

The top of `debug.log` should include brief metadata:

```text
Colosseum version: 0.x.y
Python version: 3.9.x
Platform: Windows/Linux details
Test case: test_power_rails.py
Suite: smoke_acceptance, if applicable
Start time: ...
Config file: bench.toml
Output directory: ...
```

The logging system should be usable by core, first-party extensions, and third-party extensions.

## 11. Database Model

Colosseum uses a runtime SQLite database that is saved as an output artifact.

The database is primarily an internal implementation detail, but users should not be prevented from reading it at runtime or after execution for advanced workflows.

At a minimum, Colosseum should provide public read helpers that allow users to read all entries from the framework-owned database tables. These helpers should avoid requiring users to write raw SQL for common inspection tasks.

Example conceptual APIs:

```python
col.database.read_table("measurements")
col.database.read_table("verifications")
col.database.read_measurements()
col.database.read_verifications()
col.database.read_run_metadata()
```

The schema should be stable enough to be useful, but v1 should not promise permanent schema compatibility unless explicitly documented. Public read helpers provide a softer compatibility boundary than direct schema guarantees.

### 11.1 Conceptual Tables

A conceptual v1 schema may include:

```text
run_metadata
  key
  value

measurements
  id
  domain
  command
  key
  value_json
  units
  artifact_path
  status
  timestamp

verifications
  id
  domain
  command
  key
  expected_json
  actual_json
  status
  optional
  message
  timestamp

events
  id
  level
  source
  message
  timestamp

artifacts
  id
  kind
  path
  description
  timestamp
```

Plugin-specific tables should be allowed. A recommended naming convention is:

```text
plugin_<plugin_name>_<table_name>
```

### 11.2 Key Semantics

Repeated keys are allowed across different logical tables or domains.

For example, this is allowed:

```text
dmm voltage measurement key = "key"
ssh stdout measurement key = "key"
```

This is not allowed by default:

```text
dmm voltage measurement key = "vrail"
dmm voltage measurement key = "vrail"
```

unless the measurement command explicitly supports multiple rows for the same primary logical key.

Some measurements may naturally span multiple rows. For example, a third-party spectrum analyzer plugin might store multiple power values under the same logical measurement key, differentiated by frequency. The framework should not prevent this pattern, but commands that use it should declare and document the behavior clearly.

For Colosseum-owned spectrum or trace-style commands, the preferred pattern is:

1. Save the large trace data into an output artifact such as CSV
2. Store a pointer to that artifact in SQLite
3. Perform verifications against the artifact

This avoids turning the core measurement table into a high-volume time-series or trace-data store.

## 12. Measurement and Verification Model

### 12.1 Measurements

Measurements collect evidence and persist it.

Examples:

```python
col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")
```

A measurement should generally:

1. Log start of measurement
2. Interact with equipment, SUT, or host resource
3. Capture returned value or artifact
4. Store the result in SQLite
5. Return a useful Python value to the caller

### 12.2 Verifications

Verifications judge evidence against expectations.

Examples:

```python
col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)

col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
```

A verification should generally:

1. Log start of verification
2. Retrieve required measurement evidence from SQLite or an artifact
3. Compare actual behavior against expected behavior
4. Store the verification result in SQLite
5. Return a result object or status

### 12.3 Decorators

Decorators should be bare bones.

```python
from colosseum import measurement, verification


@measurement
def measure_voltage(...):
    """
    Measures voltage from a configured DMM channel.

    :param dmm_id: Configured DMM identifier.
    :param channel: DMM channel to measure.
    :param key: Measurement key used for later verification.
    :returns: Measured voltage as a float.
    """
    ...


@verification
def verify_voltage(...):
    """
    Verifies a previously measured voltage.

    :param key: Measurement key to verify.
    :param expected_val: Expected voltage.
    :param tolerance: Allowed absolute tolerance.
    :returns: Verification result.
    """
    ...
```

The decorators should handle framework behavior such as:

- Logging
- Timing
- Exception capture
- Runtime database persistence
- Result aggregation
- Registration for discovery/documentation

Documentation should live primarily in function docstrings using Sphinx-compatible conventions.

### 12.4 Missing Data

If a verification requires data that does not exist, the verification result is `ERROR`.

This may occur when:

- A measurement was never run
- The UUT failed to respond
- The instrument returned no usable value
- A required artifact is missing
- A plugin stored malformed data

`ERROR` counts as a failure in aggregate pass/fail metrics.

### 12.5 Optional Verifications

Colosseum should support optional verifications.

Optional verifications are useful when users want to collect engineering data or perform non-gating checks without affecting the overall pass/fail result.

An optional verification should still be:

- Logged
- Stored in SQLite
- Included in summaries
- Clearly marked as optional

Optional verifications should be expressed through an `optional=True` keyword argument supported by all verification functions. The default must be `optional=False`.

Example:

```python
col.equipment.dmm.verify_voltage(key="engineering_probe_point", expected_val=1.8, tolerance=0.1, optional=True)
```

Optional verification failures and errors should not affect the overall process exit code, unless the error is a framework/runtime error rather than a domain-specific verification result.

## 13. Result and Exit-Code Model

### 13.1 Result States

V1 result states:

```text
PASS
FAIL
ERROR
SKIP
```

Definitions:

```text
PASS
  The verification completed and the observed behavior met the expected condition.

FAIL
  The verification completed and the observed behavior did not meet the expected condition.

ERROR
  The verification could not be completed due to missing data, invalid data, equipment failure, runtime exception, or another execution problem.

SKIP
  The verification or test step was intentionally skipped.
```

### 13.2 Aggregation

Required verification aggregation:

```text
Overall PASS:
  No required verification has FAIL or ERROR.

Overall FAIL:
  At least one required verification has FAIL or ERROR.
```

`ERROR` counts as failure in aggregate metrics.

`SKIP` does not count as failure unless the skip itself indicates a required test could not be performed and the user/configuration chooses to treat that as failure.

Optional verifications are reported but do not affect the overall pass/fail result.

### 13.3 Exit Codes

Exit codes must be simple:

```text
0 = overall pass
1 = anything else
```

Detailed diagnostic information belongs in `debug.log`, `execution.sqlite`, and optional summary files.

## 14. Equipment Adaptation Layer

The equipment package should provide low-level drivers and higher-level convenience libraries.

### 14.1 Low-Level Layer

Low-level interfaces provide direct control and escape hatches.

Examples:

```python
col.equipment.visa.query(...)
col.equipment.scpi.write(...)
col.equipment.scpi.query(...)
col.equipment.serial.write(...)
col.equipment.serial.read_until(...)
```

Serial should be a user-accessible class or module, not just an internal implementation detail.

### 14.2 Higher-Level Equipment Libraries

Higher-level modules provide common bench operations.

Examples:

```python
col.equipment.psu.set_voltage(...)
col.equipment.psu.set_current_limit(...)
col.equipment.psu.set_output(...)
col.equipment.dmm.measure_voltage(...)
col.equipment.dmm.verify_voltage(...)
```

### 14.3 Vendor, Model, and Interface Variation

VISA and SCPI commands vary by vendor and equipment type. Many instruments also support multiple valid interfaces. For example, a spectrum analyzer may support GPIB, Ethernet/LXI, USBTMC, and serial control.

Colosseum should therefore separate:

```text
Transport
  How bytes/messages move to and from a device.
  Examples: serial, GPIB through VISA, USBTMC through VISA, TCP/IP through VISA, raw socket.

Protocol
  How command/response semantics are represented.
  Examples: SCPI, vendor-specific ASCII command protocol, binary protocol.

Instrument abstraction
  Common operations such as measuring voltage, setting PSU output, or measuring marker power.

Vendor/model implementation
  Specific command sets, response parsing, limits, quirks, and feature availability.
```

The same high-level instrument API should work across supported interfaces when the instrument capability is the same. Interface choice should primarily be a configuration concern, not a test-script concern.

A future structure may look like:

```text
colosseum_equipment/
  transports/
    visa.py
    serial.py
    socket.py
  protocols/
    scpi.py
    ascii.py
  dmm/
    generic.py
    keysight.py
    fluke.py
  psu/
    generic.py
    keysight.py
    rigol.py
  spectrum_analyzer/
    generic.py
    keysight.py
    rohde_schwarz.py
```

This structure keeps interface handling separate from instrument behavior. For example, a Keysight spectrum analyzer implementation could use the same high-level methods whether the configured transport is GPIB, Ethernet, or USBTMC, provided the command set is compatible across those interfaces.

V1 can start with generic implementations and explicit raw-command escape hatches.

The first concrete instrument examples should be based on the attached manuals:

- Keysight EDU34450A 5½ Digit Digital Multimeter
- TDK-Lambda Genesys programmable DC power supply

These manuals should be treated as examples for initial vendor/model-specific implementations, not as the public abstraction boundary. High-level Colosseum functions should remain equipment-purpose-oriented and should hide most vendor-specific command details from test authors.

For example, user code should prefer:

```python
col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
```

rather than direct command strings. Direct command strings should remain available for bespoke use cases through low-level SCPI/transport helpers.

## 15. Shared Utility Layer

The shared package contains cross-domain utilities that are not specific to laboratory equipment.

Initial targets:

```text
SSH helpers
File checks
Regex checks
Subprocess helpers
Common parsing utilities
Common measurement and verification helpers
```

Example calls:

```python
col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")

col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
```

The shared layer should use the same measurement, verification, logging, database, and plugin systems as the equipment layer.

## 16. Runner and Suite Execution

Colosseum should include the basic structure for a command-line runner early.

Initial examples:

```bash
colosseum run tests/test_power_rails.py --config configs/bench.toml
colosseum run-suite suites/smoke.toml --config configs/bench.toml
```

The runner should eventually support:

- Running a single test case
- Running a suite
- Selecting a config file
- Creating output directories
- Setting up logging
- Initializing the runtime database
- Running setup scripts
- Running test scripts
- Running teardown scripts
- Returning exit code `0` or `1`

Advanced features such as GUI support, richer log-level controls, filtering, retries, and test selection can be deferred.

## 17. Setup and Teardown

Setup and teardown are supported but not mandatory.

They may be used for:

- Flashing firmware
- Power cycling a DUT
- Starting simulators
- Starting services
- Preparing test data
- Collecting logs
- Returning equipment to a safe state
- Powering down outputs

Setup and teardown scripts should be ordinary Python files, so users can reuse the same Colosseum APIs available to test cases.

If setup fails, the test case or suite should produce an `ERROR` result and exit with code `1`.

If teardown fails, the failure should be logged clearly. Whether teardown failure affects final status should be configurable later; v1 may treat teardown failure as exit code `1`.

## 18. Multiprocessing and Concurrency

Colosseum should be multiprocessing friendly.

### 18.1 Parallel Test Cases and Parallel DUTs

Parallel test cases and parallel DUTs should use separate output directories and separate SQLite databases.

This avoids contention over:

- SQLite writes
- Log files
- Equipment handles
- Artifact paths
- Runtime context state

### 18.2 Parallel Work Within a Test Case

The main expected use case is CPU-heavy verification work within one test case, such as running multiple DSP-heavy verifications against an RTSA recording.

Recommended pattern:

1. Perform the measurement once
2. Save large data to an output artifact
3. Store the artifact path in SQLite
4. Run multiprocessing workers against the artifact
5. Merge verification results into the active runtime database

Runtime objects, database connections, loggers, live serial connections, VISA handles, and SSH sessions should not be passed directly between worker processes.

APIs and result objects should be designed to be pickleable where practical.

## 19. Documentation Strategy

Colosseum documentation should be generated with Sphinx.

Documentation should cover:

- Installation
- Quickstart
- Configuration file syntax
- Running test cases
- Running suites
- Output directory structure
- Database artifact expectations
- Exit codes
- Measurement APIs
- Verification APIs
- Equipment APIs
- Shared utility APIs
- Plugin development
- Windows/Linux notes
- Multiprocessing guidance

Function-level documentation should live in docstrings, not in heavy decorator metadata.

Example:

```python
@measurement
def example_measurement(example_param: str) -> str:
    """
    Performs an example measurement.

    :param example_param: Example input parameter.
    :returns: String containing the measured value.
    """
    ...
```

The decorators should remain bare:

```python
@measurement
@verification
```

Sphinx should use autodoc or a similar mechanism to generate command documentation from the function docstrings.

## 20. Compatibility Requirements

Colosseum must support:

```text
Python 3.9+
Windows
Linux
Offline execution
No cloud dependency
Multiprocessing-friendly APIs
Sphinx documentation
External plugins
SQLite runtime artifact database
Python logging-based debug logs
```

Dependencies should be kept minimal in `colosseum-core`.

Likely top-level/core dependency:

```text
tomli; python_version < "3.11"
```

Extension-specific dependencies should live in their extension packages.

Examples:

```text
colosseum-equipment
  pyserial
  pyvisa

colosseum-shared
  paramiko
```

This avoids forcing all users to install every hardware or protocol dependency.

## 21. Future Work

Future work may include:

- Context-managed runtime API
- Test generation layer
- Model-based testing support
- Requirement traceability
- HTML reports
- JUnit XML output
- Allure integration
- Jira/Xray/Zephyr integration
- Richer CLI filtering and selection
- Retry policies
- Parallel suite execution
- GUI runner
- Configuration schema validation
- Stable public database schema
- Vendor-specific instrument libraries
- Web and desktop application testing plugins
- Formal plugin collision handling
- Optional treatment of `SKIP` as failure for required tests

## 22. Open Design Questions

The following items should be resolved before implementation:

1. What exact distribution names should be used for first-party extensions?
   - `colosseum-equipment`
   - `colosseum-shared`

2. How should plugins register namespaces?
   - Python entry points
   - Explicit import registration
   - Config-declared plugins
   - Hybrid

3. How strict should v1 configuration validation be?

4. How should setup/teardown scripts share execution state?
   - Same database as the test case
   - Separate execution records in the same database
   - Separate output folders per setup/test/teardown phase

5. What should the first public database read helpers return?
   - Raw dictionaries
   - Dataclasses
   - Lists of typed result objects
   - Pandas-friendly records without depending on pandas

6. What minimum vendor-specific behavior should be implemented for the first DMM and PSU examples?
   - Keysight EDU34450A DMM
   - TDK-Lambda Genesys PSU

7. Should `summary.txt` be generated continuously during execution or only once at the end?

8. Should direct Python execution and CLI execution produce identical output folder naming?

